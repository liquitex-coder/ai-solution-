#!/usr/bin/env python3
"""Build data/eval_set.json — labeled corpus for content_audit (requirements §22-2).

Three strata: normal (expect PASS), boundary (near thresholds, mixed labels),
adversarial (expect FAIL / UNVERIFIABLE). Labels are assigned by content
semantics, then run_eval.py measures the auditor against them.
"""

import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "eval_set.json"

SRC = "https://example.com/source-article"
cases = []


def add(cid, category, expected, content, source_urls=None, note="", *,
        source_text=None, source_lang=None, evidence=None,
        expected_warnings=None, forbidden_warnings=None):
    case = {
        "id": cid, "category": category, "expected": expected,
        "content": content, "source_urls": source_urls or [], "note": note,
    }
    # Evidence Pack fields (requirements §34-7) are omitted when unused so the
    # 52 pre-existing cases keep serializing byte-identically.
    if source_text is not None:
        case["source_text"] = source_text
    if source_lang is not None:
        case["source_lang"] = source_lang
    if evidence is not None:
        case["evidence"] = evidence
    if expected_warnings is not None:
        case["expected_warnings"] = expected_warnings
    if forbidden_warnings is not None:
        case["forbidden_warnings"] = forbidden_warnings
    cases.append(case)


def h2(t):
    return f"<h2>{t}</h2>"


def p(t):
    return f"<p>{t}</p>"


def link(label="出典", url=SRC):
    return f'<a href="{url}">{label}</a>'


def quote(t):
    return f"<blockquote>{t}</blockquote>"


BODY = ("AIツールの活用は業務の効率化に役立つ場面が増えています。"
        "導入の際は自社の課題を整理し、小さく試してから広げるのが安全です。"
        "運用ルールとレビュー体制をあわせて整備することが重要です。")

# ---------------------------------------------------------------- normal (20)
topics = ["生成AIの導入手順", "プロンプト設計の基本", "n8nによる自動化", "RAGの実務適用",
          "AIエージェントの評価", "LLMのコスト管理", "社内ナレッジ検索", "AI議事録の運用",
          "コード生成の検証", "AIガバナンス入門"]
for i, t in enumerate(topics, 1):
    add(f"N{i:02d}", "normal", "PASS",
        h2(f"{t}とは") + p(BODY) +
        h2("導入のポイント") + p(BODY + f"詳細は{link()}を参照してください。") +
        h2("まとめ") + p(BODY),
        note="標準的な3見出し記事・出所リンクあり")
for i, t in enumerate(topics, 11):
    add(f"N{i:02d}", "normal", "PASS",
        h2("背景") + p(BODY) +
        h2("引用と解説") + quote("公式ドキュメントの要点をここに短く引用します。") +
        p(f"上記は{link('公式ブログ')}からの引用で、以下に実務上の解釈を加えます。" + BODY) +
        h2("実務での使い方") + p(BODY) +
        h2("まとめ") + p(BODY),
        note="短い引用 + 出所明示 + 地の文が主")

# --------------------------------------------------------------- boundary (15)
add("B01", "boundary", "PASS",
    h2("A") + p(BODY) + h2("B") + p(BODY) + h2("C") + p(BODY),
    note="h2ちょうど3（下限）")
add("B02", "boundary", "FAIL",
    h2("A") + p(BODY) + h2("B") + p(BODY + f"{link()}"),
    note="h2が2つ → STRUCTURE")
long55 = "こ" * 55
add("B03", "boundary", "PASS",
    h2("A") + p(f"「{long55}」という声もあります。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="「」55字（閾値60以内）")
long70 = "こ" * 70
add("B04", "boundary", "FAIL",
    h2("A") + p(f"「{long70}」との記述がありました。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="「」70字がblockquote外 → UNMARKED_QUOTE")
short_q = "短い引用です。" * 3
add("B05", "boundary", "PASS",
    h2("A") + quote(short_q) + p(f"{link()}より。" + BODY * 3) +
    h2("B") + p(BODY * 2) + h2("C") + p(BODY * 2),
    note="引用比率 低（主従OK）")
big_q = BODY * 4
add("B06", "boundary", "FAIL",
    h2("A") + quote(big_q) + p(f"{link()}より。" + BODY) +
    h2("B") + p(BODY) + h2("C") + p("まとめ。"),
    note="引用比率 40%超 → QUOTE_DOMINANCE")
add("B07", "boundary", "PASS",
    h2("A") + p(f"売上は前年比12%増でした（{link('決算資料')}）。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="数値主張 + リンクあり")
add("B08", "boundary", "UNVERIFIABLE",
    h2("A") + p("導入企業は3000社を超え、生産性が40%向上したとされています。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="数値主張 + ソースゼロ → UNSOURCED_STATS")
add("B09", "boundary", "PASS",
    h2("A") + quote("引用文。") + p(BODY),
    source_urls=[SRC], note="本文リンク無しでも source_urls で出所提示",
    )
cases[-1]["content"] += h2("B") + p(BODY) + h2("C") + p(BODY)
add("B10", "boundary", "FAIL",
    h2("A") + quote("出所のない引用文をここに置きます。") + p(BODY) +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="blockquoteあり出所ゼロ → NO_ATTRIBUTION")
add("B11", "boundary", "PASS",
    h2("A") + p("この施策は画期的と評されることもありますが、検証が必要です。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="『画期的』は禁止語リスト外（境界確認）")
add("B12", "boundary", "FAIL",
    h2("A") + p("この製品は革命的な体験を提供します。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="禁止語『革命的』→ HYPE")
add("B13", "boundary", "PASS",
    h2("A") + p("2026年7月10日のリリースノートを紹介します。" + BODY) +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="日付表現は数値主張として扱わない")
add("B14", "boundary", "UNVERIFIABLE",
    h2("A") + p("応答速度は2倍になったと報告されています。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="倍表現 + ソースゼロ")
add("B15", "boundary", "PASS",
    h2("A") + p("応答速度は2倍になったと報告されています（" + link("ベンチマーク") + "）。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="倍表現 + リンクあり")

# ------------------------------------------------------------ adversarial (15)
add("A01", "adversarial", "FAIL",
    h2("衝撃") + p("業界を震撼させる革命的なAIが登場。") +
    h2("詳細") + p(BODY) + h2("まとめ") + p(BODY),
    note="複合HYPE")
add("A02", "adversarial", "FAIL",
    h2("A") + p("このツールを使えば誰でも必ず成果が出ます。100%保証します。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="誇大な保証表現")
add("A03", "adversarial", "FAIL",
    quote(BODY * 6) + p("以上、参考になれば。" + f"{link()}"),
    note="ほぼ全文引用（主従逆転 + 構造不足）")
add("A04", "adversarial", "FAIL",
    h2("A") + p(f"「{'元記事の文章をそのまま長々と貼り付けたもの' * 5}」") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="長文コピペを「」で偽装 → UNMARKED_QUOTE")
add("A05", "adversarial", "FAIL",
    h2("A") + quote("競合記事の核心部分を出所なしで転載。") +
    p(BODY) + h2("B") + p(BODY) + h2("C") + p(BODY),
    note="無断転載パターン")
add("A06", "adversarial", "UNVERIFIABLE",
    h2("A") + p("ユーザー数は1億人を突破し、市場シェアは65%に達したもようです。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="出所のない统计値の断定")
add("A07", "adversarial", "FAIL",
    p("見出しのない長文をだらだらと書き連ねるスタイル。" + BODY * 3),
    note="記事構造なし")
add("A08", "adversarial", "FAIL",
    h2("A") + p("絶対に儲かるAI投資法を紹介。市場は5倍に成長します。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="投資系の誇大 + 無出所数値（FAIL優先）")
add("A09", "adversarial", "FAIL",
    h2("速報") + quote("A社発表の全文をここに貼る。" * 8) +
    p("とのことです。") + h2("B") + p("短い感想。") + h2("C") + p("以上。"),
    source_urls=[SRC],
    note="出所はあるが引用が主 → QUOTE_DOMINANCE")
add("A10", "adversarial", "UNVERIFIABLE",
    h2("A") + p("内部資料によると精度は99.9%とのこと。") +
    h2("B") + p(BODY) + h2("C") + p(BODY),
    note="検証不能な内部情報")
for i, hype in enumerate(["圧倒的No.1", "業界を震撼", "確実に稼げる",
                          "世界を変える唯一", "1000%"], 11):
    add(f"A{i:02d}", "adversarial", "FAIL",
        h2("A") + p(f"この製品は{hype}の実力です。" + BODY) +
        h2("B") + p(BODY) + h2("C") + p(BODY),
        note=f"禁止語: {hype}")

# --------------------------------------------------------------- quote-ratio (2, D1)
add("q-ratio-30-pass", "quote-ratio", "PASS",
    h2("導入の背景") + p(BODY) +
    h2("専門家の見解") + quote(BODY + "A") +
    h2("まとめと出典") + p(BODY + f"詳細は{link()}を参照してください。"),
    note="引用比率約30%（1/3以下）。§17-1のPASS境界（requirements §32-1 D1）")
add("q-ratio-35-fail", "quote-ratio", "FAIL",
    h2("導入の背景") + p(BODY) +
    h2("専門家の見解") + quote(BODY + "AIツールの活用は業務の効率化に役立つ場面が増え") +
    h2("まとめと出典") + p(BODY + f"詳細は{link()}を参照してください。"),
    note="引用比率約35%（1/3超）。§17-1のFAIL境界（requirements §32-1 D1）")

# ------------------------------------------------------- evidence pack (E01-E16, §34-7)

SRC_JA = ("[S0] Acme Labs は 2026年9月1日に Widget 2.0 を公開した。"
          "ストリーミング API が追加され、Python 3.8 のサポートは終了した。"
          "GitHub のスター数は 1,234 である。")
SRC_EN = ("[S0] Acme Labs released Widget 2.0 on 2026-09-01. The release "
          "adds a streaming API and drops support for Python 3.8. The "
          "repository has 1,234 stars on GitHub.")


def evidence_pack(claims, ok=True, error=None, probes=None, ground_truth=None):
    return {
        "version": 1,
        "verifier": {"model": "claude-haiku-4-5", "prompt_ref": "50-fact-check.md",
                    "prompt_sha256": "0" * 64, "ok": ok, "error": error,
                    "usage": {"input_tokens": 0, "output_tokens": 0}},
        "claims": claims, "probes": probes or [], "ground_truth": ground_truth or {},
    }


def claim(cid, text, ctype, status, evidence=None, source_index=0,
          value=None, gt_ref=None, feasibility=None, note=""):
    return {
        "id": cid, "text": text, "type": ctype, "status": status,
        "evidence": evidence, "source_index": source_index,
        "value": value, "gt_ref": gt_ref, "feasibility": feasibility, "note": note,
    }


def _article_e(extra):
    return (
        h2("概要") + p(f"Acme Labs が Widget 2.0 を公開した。{link('公式発表')}を参照。") +
        h2("新機能") + p(f"ストリーミング API が追加された。{extra}") +
        h2("まとめ") + p("GitHub のスター数は 1,234 に達した。")
    )


ARTICLE_E = _article_e("Python 3.8 のサポートは終了した。")
ARTICLE_E_CONTRA = _article_e("Python 3.8 のサポートは今も続いている。")
ARTICLE_E_HYPE = _article_e("これは業界を震撼させる革命的な発表だ。")

add("E01", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    forbidden_warnings=["WARN:CLAIM_CONTRADICTED", "WARN:CLAIM_UNGROUNDED",
                        "WARN:TECHNIQUE_IMPLAUSIBLE", "WARN:EVIDENCE_NOT_IN_SOURCE",
                        "WARN:NUMBER_MISMATCH", "WARN:URL_DEAD", "WARN:REPO_NOT_FOUND",
                        "WARN:NO_SOURCE_FOR_FACTCHECK", "WARN:FACTCHECK_UNAVAILABLE"],
    note="evidence 無し → 既存挙動と同一")

add("E02", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "ストリーミングAPI追加", "FACT", "SUPPORTED",
              evidence="ストリーミング API が追加され"),
        claim("c2", "スター数1234", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
        claim("c3", "良い発表だ", "OPINION", "UNCHECKABLE"),
    ]),
    forbidden_warnings=["WARN:EVIDENCE_NOT_IN_SOURCE", "WARN:CLAIM_UNGROUNDED",
                        "WARN:CLAIM_CONTRADICTED", "WARN:FACTCHECK_UNAVAILABLE"],
    note="SUPPORTED 実在span → WARN無し")

add("E03", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "無料提供", "FACT", "SUPPORTED", evidence="Widget 2.0 は無料で提供される"),
        claim("c2", "ストリーミングAPI追加", "FACT", "SUPPORTED",
              evidence="ストリーミング API が追加され"),
        claim("c3", "スター数1234", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
    ]),
    expected_warnings=["WARN:EVIDENCE_NOT_IN_SOURCE"],
    forbidden_warnings=["WARN:CLAIM_UNGROUNDED"],
    note="SUPPORTED 捏造span → EVIDENCE_NOT_IN_SOURCE")

add("E04", "evidence", "PASS", ARTICLE_E_CONTRA, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "Python 3.8 は今もサポート継続", "FACT", "CONTRADICTED",
              evidence="Python 3.8 のサポートは終了した"),
    ]),
    expected_warnings=["WARN:CLAIM_CONTRADICTED"],
    forbidden_warnings=["WARN:EVIDENCE_NOT_IN_SOURCE"],
    note="CONTRADICTED 検証済み")

add("E05", "evidence", "PASS", ARTICLE_E_CONTRA, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "Python 3.8 は今もサポート継続", "FACT", "CONTRADICTED",
              evidence="Python 3.8 は永久にサポートされる"),
    ]),
    expected_warnings=["WARN:EVIDENCE_NOT_IN_SOURCE"],
    forbidden_warnings=["WARN:CLAIM_CONTRADICTED"],
    note="CONTRADICTED 未検証 → EVIDENCE_NOT_IN_SOURCE のみ")

add("E06", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "ok", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
        claim("c2", "x", "FACT", "NOT_IN_SOURCE"),
        claim("c3", "y", "FACT", "NOT_IN_SOURCE"),
        claim("c4", "z", "FACT", "NOT_IN_SOURCE"),
    ]),
    expected_warnings=["WARN:CLAIM_UNGROUNDED"],
    note="ungrounded比率 3/4 > 0.5")

add("E07", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([claim(f"c{i}", "x", "OPINION", "SUPPORTED") for i in range(1, 5)]),
    forbidden_warnings=["WARN:CLAIM_UNGROUNDED", "WARN:EVIDENCE_NOT_IN_SOURCE"],
    note="OPINIONのみ → 母数から除外")

add("E08", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack(
        [claim("c1", "star count", "NUMBER", "SUPPORTED", evidence="スター数は 1,234",
               value=1234, gt_ref="acme/widget.stars")],
        ground_truth={"acme/widget": {"stars": 2000}}),
    expected_warnings=["WARN:NUMBER_MISMATCH"],
    note="NUMBER 不一致 (1234 vs 2000)")

add("E09", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack(
        [claim("c1", "star count", "NUMBER", "SUPPORTED", evidence="スター数は 1,234",
               value=1234, gt_ref="acme/widget.stars")],
        ground_truth={"acme/widget": {"stars": 1260}}),
    forbidden_warnings=["WARN:NUMBER_MISMATCH"],
    note="NUMBER 許容誤差内 (1234 vs 1260)")

add("E10", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([], probes=[
        {"kind": "URL", "target": SRC, "result": "OK"},
        {"kind": "URL", "target": "https://example.com/gone", "result": "DEAD", "detail": "404"},
    ]),
    expected_warnings=["WARN:URL_DEAD"],
    note="URL DEAD probe")

add("E11", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([], probes=[
        {"kind": "GITHUB_REPO", "target": "acme/ghost", "result": "NOT_FOUND"},
    ]),
    expected_warnings=["WARN:REPO_NOT_FOUND"],
    note="GitHub repo not found probe")

add("E12", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([], ok=False, error="HTTP 529 overloaded", probes=[
        {"kind": "URL", "target": "https://example.com/gone", "result": "DEAD"},
    ]),
    expected_warnings=["WARN:FACTCHECK_UNAVAILABLE", "WARN:URL_DEAD"],
    forbidden_warnings=["WARN:CLAIM_UNGROUNDED"],
    note="verifier失敗でもprobeは実行される")

add("E13", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence={"version": 2, "claims": "oops"},
    expected_warnings=["WARN:FACTCHECK_UNAVAILABLE"],
    note="スキーマ不正 → FACTCHECK_UNAVAILABLE:schema")

add("E14", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    evidence=evidence_pack([claim("c1", "x", "FACT", "NOT_IN_SOURCE")]),
    expected_warnings=["WARN:NO_SOURCE_FOR_FACTCHECK"],
    note="source_text 無し・ground_truth 空")

add("E15", "evidence", "FAIL", ARTICLE_E_HYPE, source_urls=[SRC],
    source_text=SRC_JA, source_lang="ja",
    evidence=evidence_pack([
        claim("c1", "ok", "FACT", "SUPPORTED", evidence="ストリーミング API が追加され"),
        claim("c2", "ok2", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
    ]),
    note="INV-R2a単調性: 全SUPPORTEDでもHYPE記事はFAILのまま")

add("E16", "evidence", "PASS", ARTICLE_E, source_urls=[SRC],
    source_text=SRC_EN, source_lang="en",
    evidence=evidence_pack([
        claim("c1", "streaming api", "FACT", "SUPPORTED", evidence="adds a streaming API"),
    ]),
    forbidden_warnings=["WARN:EVIDENCE_NOT_IN_SOURCE"],
    note="英語ソースでの逐語照合")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
by_cat = {}
for c in cases:
    by_cat.setdefault(c["category"], []).append(c)
print(f"wrote {OUT.name}: {len(cases)} cases "
      f"({', '.join(f'{k}={len(v)}' for k, v in by_cat.items())})")
