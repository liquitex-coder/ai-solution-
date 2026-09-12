---
skill: evolve-loop
version: "1.0"
agent: claim-evolve
phase: SHIP
inputs:
  - audit_logs: list[AuditLog]
  - skill_path: string
  - performance_metrics: PerformanceMetrics
  - auto_pr: boolean
outputs:
  - updated_skill: string
  - change_summary: string
  - pr_url: string
  - verdict: "PASS|FAIL|SKIP"
auditor_required: true
memory_read:
  - 事実層
  - シーン層
memory_write:
  - 事実層
---

# 90-evolve-loop — SKILL.md 自律改善ループ

claim-evolve が Auditor FAIL ログと性能メトリクスを分析し、
`n8n/skills/*.md` を自律的に更新する。**auto_pr=true の場合は Draft PR を自動作成**。

---

## DEFINE

**目的**: Auditor FAIL パターンから学習し、対応する SKILL.md の
RATIONALIZATIONS チェックや PLAN を自律改善する。

**トリガー条件** (いずれか):
- 同一 `fail_reason` が 3 回以上発生した場合
- `performance_metrics.pass_rate` < 0.8 の場合
- `performance_metrics.avg_word_count` < 基準値の場合

**制約**:
- 改善提案は PLAN / REVIEW セクションのみ変更可
- フロントマターの `skill`・`version`・`agent` は変更不可
- `version` は semver パッチ自動インクリメント (1.0 → 1.1 → ...)
- 変更後は必ず Auditor self-check を通過すること
- INV-R2: evolve-loop 自体も LLM-free ルールで自己チェック

**成功条件**:
- 更新した SKILL.md が Auditor PASS
- `pr_url` が返る (auto_pr=true の場合)

---

## PLAN

```
1. 事実層クエリ → 過去 30 日の FAIL ログ (skill_path でフィルタ)
2. fail_reason ごとに頻度集計
3. 頻度 TOP 3 の FAIL パターンを抽出
4. 対応する改善アクションを決定:
   FAIL:QUOTE_RATIO_EXCEEDED  → REVIEW に引用比率の厳格化手順追加
   FAIL:MISSING_BLOCKQUOTE    → BUILD に blockquote テンプレ追加
   FAIL:INSUFFICIENT_SECTIONS → PLAN に見出し最小数チェック追加
   FAIL:MISSING_SOURCE_URL    → BUILD に URL 検証ステップ追加
   FAIL:INSUFFICIENT_LENGTH   → DEFINE の word_count 基準値を引き上げ
5. SKILL.md の該当セクションを更新 (LLM draft → Auditor check)
6. version パッチインクリメント
7. 事実層に { skill_path, old_version, new_version, change_reason, updated_at } を書き込む
8. auto_pr=true → GitHub API で Draft PR 作成
```

---

## BUILD

事実層クエリ (SQLite):
```sql
SELECT fail_reason, COUNT(*) as freq
FROM audit_facts
WHERE skill_ref = :skill_path
  AND audited_at >= datetime('now', '-30 days')
GROUP BY fail_reason
ORDER BY freq DESC
LIMIT 3;
```

claim-evolve 改善リクエスト (claim-llm 経由):
```json
{
  "task": "skill_improve",
  "skill_content": "{{ current SKILL.md content }}",
  "fail_patterns": "{{ top 3 fail reasons }}",
  "sections_to_modify": ["PLAN", "REVIEW"],
  "constraint": "do not modify frontmatter skill/version/agent fields"
}
```

改善後の Auditor self-check:
```json
{
  "method": "POST",
  "url": "{{ $env.CLAIM_AUDITOR_URL }}/audit",
  "body": {
    "content": "{{ updated_skill_content }}",
    "skill_ref": "90-evolve-loop",
    "check_type": "skill_self_check"
  }
}
```

---

## REVIEW

Auditor gate (self-check) チェック項目:
- [ ] フロントマターの `skill`・`agent` が変更されていない
- [ ] `version` が正しくインクリメントされている
- [ ] 変更セクションが PLAN / REVIEW のみ
- [ ] ハードコード認証情報なし
- [ ] 改善内容が FAIL パターンと対応している

---

## SHIP

auto_pr=true の場合:
- ブランチ `evolve/skill-{skill_name}-v{new_version}` を作成
- Draft PR を GitHub API で作成
- `pr_url` を事実層に記録

auto_pr=false の場合:
- 更新済み SKILL.md をローカルファイルに書き込み
- `change_summary` を通知

このループは cron (日次) または Auditor FAIL 閾値超過で自動トリガーされる。
