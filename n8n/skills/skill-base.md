# SKILL-BASE — 共通ヘッダー・規約

すべての `n8n/skills/*.md` ファイルが継承する共通仕様。
個別スキルはこのファイルを上書きする形で差分のみ記述する。

---

## YAML フロントマター仕様

```yaml
---
skill: <kebab-case-name>           # ユニーク識別子
version: "1.0"                     # semver
agent: <claim-crew|claim-llm|claim-auditor|claim-builder|claim-evolve>
phase: <DEFINE|PLAN|BUILD|REVIEW|SHIP>  # このスキルが主に属するフェーズ
inputs:                             # n8n から受け取るフィールド
  - field_name: type               # 例: topic: string
outputs:                            # n8n へ返すフィールド
  - field_name: type
auditor_required: true|false        # true = Auditor PASS なしに SHIP 不可
memory_read:                        # 読み込む記憶層 (§19)
  - 会話層|事実層|シーン層|ペルソナ層
memory_write:                       # 書き込む記憶層
  - 会話層|事実層|シーン層|ペルソナ層
---
```

---

## フェーズ定義

| フェーズ | 説明 | 主な出力 |
|----------|------|----------|
| **DEFINE** | スキルの目的・制約・成功条件を明文化する | 仕様書 |
| **PLAN** | 実行手順・分岐・エラー処理を設計する | 実行計画 |
| **BUILD** | 情報収集・変換・生成を実行する | 中間成果物 |
| **REVIEW** | Auditor gate / 品質チェックを適用する | verdict |
| **SHIP** | WordPress 投稿 / 外部配信を実行する | 公開 URL |

フェーズは必ず上から順に実行する。REVIEW で FAIL が出た場合は
BUILD に差し戻し（最大 3 回）、それ以降は人間レビュー待ちとする。

---

## 共通ルール

1. **INV-R1**: 人間署名が信頼根拠。自動 SHIP は Auditor PASS 後のみ。
2. **INV-R2**: Auditor の verdict は LLM-free 決定論的ロジックのみ。
3. **著作権**: 引用文字数は要件 §17-1（生成/引用 > 2.0、引用 ≤ 1/3）に従う。blockquote タグ必須。出所 URL 明記。
4. **Rationalizations Table**: Auditor pre-flight で下記を確認する。
   - 「動くはず」で未テストのコード → FAIL
   - ハードコード認証情報 → FAIL
   - 引用比率超過 → FAIL
   - 翻訳ラベル欠落（他言語ソース） → FAIL
   - 本番呼び出しなし（LIBRARY_ONLY 未登録） → WARN
5. **確度スコア**: BUILD 出力には必ず `confidence: HIGH|MED|LOW|UNVERIFIABLE` を付与。
6. **記憶層**: 全 FAIL 理由は事実層に蓄積する（重複取材防止・学習基盤）。

---

## n8n 組み込みパターン

```
[Trigger] → [skill-BUILD node] → [Auditor HTTP Request]
                                       ↓ verdict
                                 [IF PASS] → [skill-SHIP node]
                                 [IF FAIL] → [retry / human-review]
```

Auditor HTTP Request:
- Method: POST
- URL: `{{ $env.CLAIM_AUDITOR_URL }}/audit`
- Body: `{ "content": "...", "claims": [...], "source_urls": [...] }`
- Response: `{ "verdict": "PASS|FAIL|UNVERIFIABLE", "reasons": [...], "confidence": "..." }`
