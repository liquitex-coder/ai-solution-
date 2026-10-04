#!/usr/bin/env python3
"""Tool DB -> WordPress tool detail pages (requirements §35-11, T-46).

data/tools.json is the single source of truth. Pages are plain HTML (no plugin),
audited with content_audit before anything is sent, and always sent as drafts.

Usage:
  python3 scripts/tool_pages.py check              # validate + audit every page (exit 1 on error)
  python3 scripts/tool_pages.py render --out DIR   # write <slug>.html files for review
  python3 scripts/tool_pages.py publish            # operator: send drafts to WordPress
Auth for publish (same selection as scripts/wp-init.sh, requirements §24):
  WP_BEARER_TOKEN + WP_SITE (WordPress.com)  or  WP_URL + WP_USERNAME + WP_APP_PASSWORD
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import pathlib
import re
import sys
from typing import Any, Callable, Mapping
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from content_audit import audit  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS_FILE = ROOT / "data" / "tools.json"
TAXONOMY_FILE = ROOT / "data" / "wp-taxonomy.json"

INDEX_SLUG = "tools"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
REQUIRED_TEXT = ("slug", "name", "vendor", "summary", "official_url")
PAGE_STATUSES = "publish,future,draft,pending,private"


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _https(value: object) -> bool:
    return isinstance(value, str) and value.startswith("https://") and len(value) > len("https://")


def validate(data: Any, tag_slugs: set[str]) -> list[str]:
    """§35-11 schema; returns human-readable errors (empty = valid)."""
    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        return ["tools.json must be an object with a 'tools' list"]
    errors: list[str] = []
    seen: set[str] = set()
    for i, tool in enumerate(data["tools"]):
        where = f"tools[{i}]"
        if not isinstance(tool, dict):
            errors.append(f"{where}: must be an object")
            continue
        slug = tool.get("slug")
        if isinstance(slug, str) and slug.strip():
            where = slug
        for field in REQUIRED_TEXT:
            if not isinstance(tool.get(field), str) or not tool[field].strip():
                errors.append(f"{where}: {field} is required")
        if isinstance(slug, str) and slug.strip():
            if slug in seen:
                errors.append(f"{slug}: duplicate slug")
            seen.add(slug)
            if slug == INDEX_SLUG:
                errors.append(f"{slug}: reserved for the index page")
            if slug not in tag_slugs:
                errors.append(f"{slug}: not a tag in wp-taxonomy.json (R1/R2 need a tag)")
        if "official_url" in tool and not _https(tool.get("official_url")):
            errors.append(f"{where}: official_url must start with https://")
        pricing = tool.get("pricing")
        if not isinstance(pricing, list):
            errors.append(f"{where}: pricing must be a list (empty is allowed)")
            pricing = []
        for j, row in enumerate(pricing):
            if not isinstance(row, dict):
                errors.append(f"{where}: pricing[{j}] must be an object")
                continue
            for field in ("plan", "price"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    errors.append(f"{where}: pricing[{j}].{field} is required")
            if not _https(row.get("source_url")):
                errors.append(f"{where}: pricing[{j}].source_url must start with https://")
            if not (isinstance(row.get("retrieved_at"), str)
                    and DATE_RE.fullmatch(row["retrieved_at"])):
                errors.append(f"{where}: pricing[{j}].retrieved_at must be YYYY-MM-DD")
        affiliate = tool.get("affiliate")
        if affiliate is not None:
            if not isinstance(affiliate, dict) or not _https(affiliate.get("url")) \
                    or not isinstance(affiliate.get("program"), str) \
                    or not affiliate["program"].strip():
                errors.append(f"{where}: affiliate needs an https url and a program")
    return errors


def render_tool(tool: Mapping[str, Any]) -> str:
    e = html.escape
    name, slug = e(tool["name"]), e(tool["slug"])
    affiliate = tool.get("affiliate")
    parts = []
    if affiliate:
        # §35-6 A1: the PR label must come before the first h2.
        parts.append("<p>【PR】本ページにはアフィリエイト広告を含みます。</p>")
    parts.append(f"<h2>{name}とは</h2>")
    parts.append(f"<p>{e(tool['summary'])}</p>")

    parts.append("<h2>料金</h2>")
    pricing = tool.get("pricing") or []
    if pricing:
        rows = "".join(
            f"<tr><td>{e(r['plan'])}</td><td>{e(r['price'])}</td>"
            f'<td><a href="{e(r["source_url"])}">出典</a>（{e(r["retrieved_at"])} 時点）</td></tr>'
            for r in pricing)
        parts.append("<table><thead><tr><th>プラン</th><th>料金</th><th>出典</th></tr></thead>"
                     f"<tbody>{rows}</tbody></table>")
        parts.append("<p>料金は変わることがあります。最新の情報は公式サイトで確認してください。</p>")
    else:
        parts.append("<p>料金情報は未登録です。公式サイトで確認してください。</p>")

    parts.append("<h2>公式サイト</h2>")
    parts.append(f'<p><a href="{e(tool["official_url"])}">{name} 公式サイト</a></p>')
    if affiliate:
        # §35-6 A2: affiliate links carry rel="sponsored".
        parts.append(f'<p><a href="{e(affiliate["url"])}" rel="sponsored nofollow">'
                     f"{name}を申し込む（{e(affiliate['program'])}）</a></p>")

    parts.append("<h2>関連ニュース</h2>")
    # §35-4 R2 without a plugin: link to the tag archive that lists the news posts.
    parts.append(f'<p><a href="/tag/{slug}/">{name}の最新ニュース一覧</a></p>')
    parts.append('<p><a href="/tools/">AIツール一覧に戻る</a></p>')
    return "".join(parts)


def render_index(tools: list[Mapping[str, Any]]) -> str:
    e = html.escape
    items = "".join(
        f'<li><a href="/tools/{e(t["slug"])}/">{e(t["name"])}</a>（{e(t["vendor"])}）</li>'
        for t in tools)
    return ("<h2>掲載ツール一覧</h2>"
            f"<ul>{items}</ul>"
            "<h2>掲載方針</h2>"
            "<p>各ページの内容は編集部のデータベースから生成し、公開前に自動の監査と人の確認を経ています。</p>"
            "<h2>料金情報について</h2>"
            "<p>料金は出典と取得日を併記したものだけを掲載しています。</p>")


def build_pages(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Index page first, then one page per tool (children of the index)."""
    tools = data["tools"]
    pages = [{"slug": INDEX_SLUG, "title": "AIツール一覧", "parent": None,
              "content": render_index(tools)}]
    for tool in tools:
        pages.append({"slug": tool["slug"], "title": f"{tool['name']}とは｜料金と公式情報",
                      "parent": INDEX_SLUG, "content": render_tool(tool)})
    return pages


def audit_pages(pages: list[dict[str, Any]]) -> list[str]:
    """CLAUDE.md §A-5: every page must PASS content_audit before it may be sent."""
    errors = []
    for page in pages:
        result = audit(page["content"])
        if result["verdict"] != "PASS":
            errors.append(f"{page['slug']}: {result['verdict']} {result['reasons'][:3]}")
    return errors


def check(tools_file: pathlib.Path = TOOLS_FILE,
          taxonomy_file: pathlib.Path = TAXONOMY_FILE) -> tuple[list[str], list[dict[str, Any]]]:
    data = load_json(tools_file)
    tag_slugs = {tag.get("slug") for tag in load_json(taxonomy_file).get("tags", [])}
    errors = validate(data, tag_slugs)
    if errors:
        return errors, []
    pages = build_pages(data)
    return audit_pages(pages), pages


# ---------------------------------------------------------------- publish (operator)

Transport = Callable[[str, str, dict[str, Any] | None], Any]


def wp_target(env: Mapping[str, str]) -> tuple[str, str]:
    """(api_base, Authorization header) with the same selection as wp-init.sh (§24)."""
    token = env.get("WP_BEARER_TOKEN", "")
    if token:
        site = env.get("WP_SITE", "")
        if not site:
            raise SystemExit("WP_BEARER_TOKEN is set but WP_SITE is not (requirements §24)")
        return f"https://public-api.wordpress.com/wp/v2/sites/{site}", f"Bearer {token}"
    password = env.get("WP_APP_PASSWORD", "")
    if not password:
        raise SystemExit("set WP_BEARER_TOKEN + WP_SITE or WP_USERNAME + WP_APP_PASSWORD")
    user = env.get("WP_USERNAME", "admin")
    basic = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return env.get("WP_URL", "http://localhost:8080").rstrip("/") + "/wp-json/wp/v2", \
        f"Basic {basic}"


def http_transport(api_base: str, auth: str) -> Transport:
    def send(method: str, path: str, body: dict[str, Any] | None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(api_base + path, data=data, method=method,
                          headers={"Authorization": auth, "Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    return send


def publish(pages: list[dict[str, Any]], send: Transport) -> list[str]:
    """Create or update draft pages by slug; never overwrite a changed published page."""
    log: list[str] = []
    ids: dict[str, int] = {}
    for page in pages:
        found = send("GET", f"/pages?slug={quote(page['slug'])}&context=edit"
                            f"&status={PAGE_STATUSES}", None)
        body: dict[str, Any] = {"title": page["title"], "slug": page["slug"],
                                "content": page["content"]}
        parent = ids.get(page["parent"]) if page["parent"] else None
        if page["parent"] and parent is None:
            log.append(f"[WARN] {page['slug']}: parent {page['parent']} unavailable, skipped")
            continue
        if parent:
            body["parent"] = parent
        if not found:
            created = send("POST", "/pages", {**body, "status": "draft"})
            ids[page["slug"]] = created["id"]
            log.append(f"[CREATED] {page['slug']} (draft, id={created['id']})")
            continue
        existing = found[0]
        ids[page["slug"]] = existing["id"]
        current = (existing.get("content") or {}).get("raw", "")
        if current == page["content"]:
            log.append(f"[SKIP] {page['slug']}: unchanged")
        elif existing.get("status") == "publish":
            # INV-R1: a signed (published) page is not rewritten without review.
            log.append(f"[HOLD] {page['slug']}: published page differs; human review needed")
        else:
            send("POST", f"/pages/{existing['id']}", {**body, "status": "draft"})
            log.append(f"[UPDATED] {page['slug']} (draft, id={existing['id']})")
    return log


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
    if args.cmd == "check":
        print(f"[OK] {len(pages)} pages valid and audit PASS")
    elif args.cmd == "render":
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for page in pages:
            (out / f"{page['slug']}.html").write_text(page["content"], encoding="utf-8")
        print(f"[OK] wrote {len(pages)} pages to {out}")
    else:
        for line in publish(pages, http_transport(*wp_target(os.environ))):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
