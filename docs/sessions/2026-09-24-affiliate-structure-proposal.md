---
date: 2026-09-24
tags: [ai-solution, affiliate, structure, proposal, auditor-self-apply]
status: proposal (not yet in requirements.md)
source: https://blogai.jp/ai-affiliate-complete-guide/ (2026-03-16)
---

# AIアフィリエイト記事を参照した ai-solution- 構成案

## 1. 参照記事の要点（採用候補）
- 収益記事（比較・ランキング・商標）と集客記事（〇〇とは・ロングテール）を分け、収益記事ほど人間比率を上げる
- 資産7：トレンド3
- 1日の公開上限は3本（1日10本公開 → 3週間で圏外、という実例あり）
- 使っていない商品のAIレビュー → 手動ペナルティ
- E-E-A-T：一次情報・著者・更新日・出典・内部リンク
- 定期リライト（月5本以上）、SNS／メルマガへの流入分散
- KPI：30記事 → 70記事 → 100記事

## 2. 現状（コードで確認済み）
- カテゴリ9つはすべてフロー型（`data/wp-taxonomy.json`）
- スケジュール：WF02 30分 / WF03・05 1時間 / WF04 3時間 / WF08 6時間
- Auditor Gate の既定値は `report_only`、全件が下書き保存（WF01〜06 の jsCode）
- `content_audit.py` が持つのは HYPE / 引用 / 構造 / 統計の出典チェック。アフィリエイト系のルールは無し
- `article-base.md` に著者・更新日・内部リンク・CTA への言及は無し（grep で0件）
- 収益化の設計は旧 §16（commit 5caa493）と disclosure gate（commit 4be8c51）にある。§27 のマージで削除済み

## 3. 提案：5層構成
- L1 集客（フロー）：WF01-06・08 はそのまま。公開上限を追加
- L2 資産（ストック）：ツールDB、ツール詳細、使い方ガイド（WF07）、深掘り（WF09）
- L3 収益：アフィリエイトリンクの台帳、PR表記と CTA の自動挿入、比較とランキング（人間の署名が必須）
- L4 品質：Auditor にアフィリエイト系ルール A1〜A5 を追加
- L5 計測・改善：GA4 と Search Console、鮮度チェックからのリライト、claim-evolve

## 4. Auditor に追加するルール案
- A1：アフィリエイトリンクがあるのに PR 表記が無い → FAIL
- A2：アフィリエイトリンクに `rel="sponsored"` が無い → FAIL
- A3：体験を主張しているのに、実行証拠（サンドボックスのログ）が無い → FAIL
- A4：料金・価格に出典も取得日も無い → UNVERIFIABLE
- A5：収益リンクを含む記事 → 自動公開を禁止し、常に人間の承認を通す

## 5. 未決事項
- 比較・ハンズオンのカテゴリを復活させるか（§27 で削除済み）
- 利用するASPと商材
- 公開上限の値
