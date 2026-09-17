---
skill: fact-check
version: "1.0"
agent: claim-llm
phase: BUILD
inputs:
  - content: string              # article_draft (HTML)
  - source_urls: list[string]
  - source_text: string          # [S0]..[Sn] 索引付き連結ソース（ソースが無い WF は空）
  - source_lang: "ja|en|zh"
  - ground_truth: object         # WF01/09 の構造化実測値（任意）
outputs:
  - evidence: EvidencePack       # 要件 §34-4 v1
  - source_text: string          # verifier に渡したものと同一文字列（ゲートへ転送）
  - source_lang: "ja|en|zh"
auditor_required: false
memory_read: []
memory_write: []
---

# 15-fact-check — Evidence Pack 生成スキル（要件 §34）

BUILD の最終ステップ。記事生成後・Auditor Gate 前に実行し、ゲートに渡す**証拠**を作る。
**verdict は決めない**（INV-R2）。証拠は verdict を下げる方向にしか使われない（INV-R2a）。

---

## DEFINE

**目的**: 記事中の検証可能な主張について、(0) パイプラインの実測値、(1) URL / GitHub の実在確認、
(2) `claude-haiku-4-5` による主張抽出と逐語 evidence 付きの照合結果を、要件 §34-4 の JSON（Evidence Pack v1）にまとめる。

**モデル**: `claude-haiku-4-5`（操作者決定 2026-09-17、コスト理由、要件 §34-10。変更は操作者確認事項）。
**プロンプト**: `n8n/prompts/50-fact-check.md`（system）。
**制約**: web/fetch ツール無し。`thinking` 指定無し。`max_tokens: 4096`。`output_config.format` で JSON を強制。
Verifier 失敗時も出力を止めない（`verifier.ok=false`）。

**成功条件**: `evidence` が §34-4 のスキーマに適合し、`source_text` がゲート送信分と同一。

---

## PLAN

```
1. source_text を組む: 各ソースを "[S<i>] <title>\n<text>" とし "\n\n" で連結（i は source_urls の添字）。
   WF01/09: items[] の title + description(+ snippet) を text に、ground_truth に {"<owner>/<repo>": {"stars": N, "language": ...}}。
   WF02/03/05: 取得本文（先頭 6,000 字まで、超過は切る）。WF07: source_text は空、ground_truth は {}。
2. Tier 1 probes（Code ノード、マーカー文字列 EVIDENCE_PROBES を含める）:
   - 記事本文の https?:// URL を重複除去し最大 10 件を HEAD（405 なら GET）。404/410 → DEAD、200-399 → OK、それ以外/例外 → TIMEOUT、11 件目以降 → SKIPPED。
   - github.com/<owner>/<repo> は GET https://api.github.com/repos/<owner>/<repo>（$env.GITHUB_TOKEN があれば付与）。404 → NOT_FOUND、200 → OK（detail.stars = stargazers_count）、それ以外 → TIMEOUT。
3. Tier 2 verifier（HTTP Request ノード、credential = 既存 "Claude API Key"、Continue On Fail = on）。
4. Evidence Pack 整形（Code ノード）: verifier ノード（HTTP Request）の出力は入力 item を引き継がないため、
   `source_text` / `probes` / `ground_truth` は `$('Evidence Probes (WF-NN)').item.json` から、プロンプトの
   SHA-256 は `$('プロンプト読込み (WF-NN)').item.json.factcheckPromptSha256` から読む。`$json` は API 応答
   （または `{error}`）のみ。verifier 応答の content[0].text を JSON.parse → claims。失敗/HTTP エラー →
   ok=false, error=<message 先頭 200 字>, claims=[]。usage は応答の usage をそのまま。
   設定値は `cfg()`（`$vars` → `$env`、各 try/catch、要件 §32-1 D10）で読む。
5. 出力: { ...$json, source_text, source_lang, evidence }。
```

---

## BUILD

Verifier HTTP Request（n8n）:
```json
{
  "method": "POST",
  "url": "https://api.anthropic.com/v1/messages",
  "headers": { "anthropic-version": "2023-06-01" },
  "onError": "continueRegularOutput",
  "options": { "timeout": 120000 },
  "body": {
    "model": "claude-haiku-4-5",
    "max_tokens": 4096,
    "system": "={{ $('プロンプト読込み (WF-NN)').item.json.factcheckPrompt }}",
    "messages": [{
      "role": "user",
      "content": "<ARTICLE>\n{{ $json.content }}\n</ARTICLE>\n\n<SOURCES>\n{{ $('Evidence Probes (WF-NN)').item.json.source_text }}\n</SOURCES>\n\n<GROUND_TRUTH>\n{{ JSON.stringify($('Evidence Probes (WF-NN)').item.json.ground_truth || {}) }}\n</GROUND_TRUTH>"
    }],
    "output_config": {
      "format": {
        "type": "json_schema",
        "schema": {
          "type": "object",
          "properties": {
            "claims": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "id": {"type": "string"},
                  "text": {"type": "string"},
                  "type": {"type": "string", "enum": ["FACT", "NUMBER", "TECHNIQUE", "OPINION"]},
                  "status": {"type": "string", "enum": ["SUPPORTED", "CONTRADICTED", "NOT_IN_SOURCE", "UNCHECKABLE"]},
                  "evidence": {"type": ["string", "null"]},
                  "source_index": {"type": ["integer", "null"]},
                  "value": {"type": ["number", "null"]},
                  "gt_ref": {"type": ["string", "null"]},
                  "feasibility": {"type": ["string", "null"], "enum": ["PLAUSIBLE", "IMPLAUSIBLE", "UNKNOWN", null]},
                  "note": {"type": "string"}
                },
                "required": ["id", "text", "type", "status", "evidence", "source_index", "value", "gt_ref", "feasibility", "note"],
                "additionalProperties": false
              }
            }
          },
          "required": ["claims"],
          "additionalProperties": false
        }
      }
    }
  }
}
```

`factcheckPrompt` は「プロンプト読込み」ノードが `50-fact-check.md` を GitHub から取得して設定する（他 WF のプロンプト読込みと同じ方式）。
ノード列: `[Evidence Probes]`（EVIDENCE_PROBES）→ `[Fact-Check Verifier]` → `[Evidence Pack 整形]` → `[Auditor Gate]`。
ゲートの body に `source_text` / `source_lang` / `evidence` を追加する（`20-auditor-gate.md` BUILD）。

---

## REVIEW

このスキルは verdict を出さない。検証は次の2つで行う:
- `scripts/check_wired.py` W12（配線: プロンプト参照・モデル名・EVIDENCE_PROBES・ゲート body の source_text）
- `scripts/content_audit.py` の逐語照合（要件 §34-5 規則 2）が verifier の SUPPORTED/CONTRADICTED を再検証する

---

## SHIP

出力はそのまま `20-auditor-gate` へ。`evidence` の有無・内容で PASS が増えることはない（INV-R2a）。
全 `WARN:` は `warnings` テーブルに残り、T-37 の30日観察と T-38 の昇格判断に使われる（要件 §34-6, §34-9）。
