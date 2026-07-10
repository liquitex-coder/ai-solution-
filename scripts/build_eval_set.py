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


def add(cid, category, expected, content, source_urls=None, note=""):
    cases.append({
        "id": cid, "category": category, "expected": expected,
        "content": content, "source_urls": source_urls or [], "note": note,
    })


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

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=1))
by_cat = {}
for c in cases:
    by_cat.setdefault(c["category"], []).append(c)
print(f"wrote {OUT.name}: {len(cases)} cases "
      f"({', '.join(f'{k}={len(v)}' for k, v in by_cat.items())})")
