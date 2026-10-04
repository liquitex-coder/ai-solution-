#!/usr/bin/env python3
"""Trust pages generator (requirements §35-12, T-47).

data/trust_pages.json lists six pages (requirements §35-3). "ready" pages generate
from existing spec (no operator facts needed) and are audited + publishable. "pending"
pages carry an honest placeholder (real operator facts are not recorded anywhere in
this repo) and are audited for the record but are never sent as a draft.

Usage:
  python3 scripts/trust_pages.py check              # validate + audit every page
  python3 scripts/trust_pages.py render --out DIR   # write <slug>.html files for review
  python3 scripts/trust_pages.py publish            # operator: send "ready" pages as drafts
Auth for publish: same selection as scripts/wp-init.sh / scripts/tool_pages.py (§24).
"""

from __future__ import annotations

import argparse
import html
import os
import pathlib
import sys
from typing import Any, Mapping

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from content_audit import audit  # noqa: E402
from tool_pages import http_transport, publish as publish_pages, wp_target  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRUST_PAGES_FILE = ROOT / "data" / "trust_pages.json"
REQUIRED_SLUGS = {"operator", "editorial-policy", "ad-policy", "claim-platform",
                  "privacy", "contact"}
STATUSES = ("ready", "pending")


def load_json(path: pathlib.Path) -> Any:
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: Any) -> list[str]:
    """§35-12 schema: exactly the six §35-3 pages, each ready or pending."""
    if not isinstance(data, dict) or not isinstance(data.get("pages"), list):
        return ["trust_pages.json must be an object with a 'pages' list"]
    errors: list[str] = []
    slugs: list[str] = []
    for i, page in enumerate(data["pages"]):
        where = f"pages[{i}]"
        if not isinstance(page, dict):
            errors.append(f"{where}: must be an object")
            continue
        slug = page.get("slug")
        if isinstance(slug, str) and slug.strip():
            where = slug
            slugs.append(slug)
        for field in ("slug", "title", "status"):
            if not isinstance(page.get(field), str) or not page[field].strip():
                errors.append(f"{where}: {field} is required")
        if page.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        if page.get("status") == "pending" and not isinstance(page.get("pending_reason"), str):
            errors.append(f"{where}: pending pages need pending_reason")
    if set(slugs) != REQUIRED_SLUGS:
        missing = REQUIRED_SLUGS - set(slugs)
        extra = set(slugs) - REQUIRED_SLUGS
        if missing:
            errors.append(f"missing required pages: {sorted(missing)}")
        if extra:
            errors.append(f"unexpected pages: {sorted(extra)}")
    if len(slugs) != len(set(slugs)):
        errors.append("duplicate slug in pages")
    return errors


def _h2(title: str, body: str) -> str:
    return f"<h2>{html.escape(title)}</h2><p>{body}</p>"


def render_pending(title: str) -> str:
    e = html.escape(title)
    return (
        _h2("このページについて", f"「{e}」の内容は準備中です。確定次第、このページで公開します。")
        + _h2("公開時期", "内容が確定した時点で、このページを更新してお知らせします。")
        + _h2("お問い合わせ", "急ぎの確認が必要な場合は、運営者情報ページ公開後の窓口をご利用ください。")
    )


def render_editorial_policy() -> str:
    return (
        _h2("記事ができるまで", "本サイトの記事は、AIによる収集・要約・生成を経たのち、"
            "公開前に必ず自動の監査（Auditor Gate）を通します。監査を通らない記事は公開されません。")
        + _h2("Auditor Gateとは",
              "誇大表現・引用の分量・出所表示・数値主張の裏付けなどを機械的に検査する仕組みです。"
              "判定にAIモデルは使わず、決定論的なルールだけで判定します。")
        + _h2("判定基準",
              "監査の結果は3種類です。PASS（基準を満たす）、FAIL（基準に違反、公開しない）、"
              "UNVERIFIABLE（裏付けを確認できない、公開しない）。")
        + _h2("出所表示の方針",
              "他媒体からの引用・要約には、必ず出典元へのリンクを付けます。翻訳記事には翻訳である旨を明記します。")
    )


def render_ad_policy() -> str:
    return (
        _h2("広告の種類", "本サイトには、アフィリエイトリンクを含む記事が含まれる場合があります。")
        + _h2("PR表記",
              "アフィリエイトリンクを含む記事には、本文の見出しより前にPR表記を掲示します。")
        + _h2("リンクの扱い",
              "アフィリエイトサービス経由のリンクには、検索エンジン向けに広告リンクである旨を示す属性を付けます。")
        + _h2("収益記事の公開について",
              "アフィリエイトリンクを含む記事は、自動では公開しません。必ず人間が内容を確認したうえで公開します。")
    )


def render_claim_platform() -> str:
    return (
        _h2("Claim Platformとは",
            "本サイトの自動化パイプラインを支える一連のツール群です。記事のファクトチェック・生成・"
            "セキュリティ保護などを、それぞれ専用のプロダクトが担当します。")
        + _h2("各プロダクトの役割",
              "ファクトチェックと著作権チェックを行うゲート、複数のAIが協議して記事案を作る仕組み、"
              "APIを保護する仕組みなど、複数のプロダクトが連携しています。")
        + _h2("このサイトでの使われ方",
              "本サイト自体が、これらのプロダクトを実際に動かすデモを兼ねています。")
        + _h2("バッジ表示について",
              "監査を通過した記事には、その旨を示す表示を検討しています。")
    )


RENDER_READY = {
    "editorial-policy": render_editorial_policy,
    "ad-policy": render_ad_policy,
    "claim-platform": render_claim_platform,
}


def render_page(page: Mapping[str, Any]) -> str:
    if page["status"] == "pending":
        return render_pending(page["title"])
    renderer = RENDER_READY.get(page["slug"])
    if renderer is None:
        raise ValueError(f"no renderer registered for ready page {page['slug']!r}")
    return renderer()


def build_pages(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"slug": page["slug"], "title": page["title"], "status": page["status"],
             "parent": None, "content": render_page(page)} for page in data["pages"]]


def audit_pages(pages: list[dict[str, Any]]) -> list[str]:
    """§35-12 W16: every 'ready' page must PASS; 'pending' pages are audited for the
    record only and never block the gate."""
    errors = []
    for page in pages:
        result = audit(page["content"])
        page["audit_verdict"] = result["verdict"]
        if page["status"] == "ready" and result["verdict"] != "PASS":
            errors.append(f"{page['slug']}: {result['verdict']} {result['reasons'][:3]}")
    return errors


def check(trust_pages_file: pathlib.Path = TRUST_PAGES_FILE
          ) -> tuple[list[str], list[dict[str, Any]]]:
    data = load_json(trust_pages_file)
    errors = validate(data)
    if errors:
        return errors, []
    pages = build_pages(data)
    return audit_pages(pages), pages


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    render = sub.add_parser("render")
    render.add_argument("--out", required=True)
    sub.add_parser("publish")
    args = ap.parse_args(argv)

    errors, pages = check()
    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    ready = [p for p in pages if p["status"] == "ready"]
    pending = [p for p in pages if p["status"] == "pending"]
    if args.cmd == "check":
        print(f"[OK] {len(ready)} ready (audit PASS), {len(pending)} pending (not published)")
    elif args.cmd == "render":
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for page in pages:
            (out / f"{page['slug']}.html").write_text(page["content"], encoding="utf-8")
        print(f"[OK] wrote {len(pages)} pages to {out}")
    else:
        for line in publish_pages(ready, http_transport(*wp_target(os.environ))):
            print(line)
        print(f"[SKIP] {len(pending)} pending page(s) not published: "
              f"{', '.join(p['slug'] for p in pending)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
