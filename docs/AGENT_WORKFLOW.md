# AGENT_WORKFLOW.md — Detailed Working Rules (ai-solution-)

`CLAUDE.md` の参照先。CLAUDE.md の A〜F が要約、当ファイルが詳細。矛盾したら CLAUDE.md が優先。

---

## 1. セッション開始の標準フロー（全プロダクト共通）

```
① CLAUDE.md 確認 → ② Auditor 自己適用 → ③ 要件定義書更新
       → ④ ロードマップ作成 → ⑤ TaskCreate 登録
```

### ② Auditor 自己適用の判定表

| チェック項目 | 判定 |
|---|---|
| 実装対象は「実装 ∧ テスト ∧ 本番呼び出し」が証明できる形か | PASS / FAIL |
| 設計文書に存在しない機能を実装しようとしていないか | PASS / FAIL |
| 「動くはず」「たぶん大丈夫」「おそらく」が計画に含まれていないか | PASS / FAIL |
| 認証情報・APIキーがハードコードされた計画になっていないか | PASS / FAIL |

1つでも FAIL → 要件定義書の更新に戻る。全て PASS になってから実装へ。

---

## 2. Anti-Hallucination 詳細

- **Cite before you claim**: 動くと主張する前に file+line またはツール出力を指す。
- 証拠なしの禁止表現: "should work" / "it's probably" / "I believe it's configured"。
- 不確実な場合は明示的にそう言い、検証が必要な項目を列挙する。
- 完了報告の前に必ず Local Gates（CLAUDE.md §D)を実行し、出力を報告に貼る。

---

## 3. Requirements-First / Roadmap / Task 詳細

1. 設計文書を更新 → 単独 `docs:` コミット（`docs: add/update <what changed>`）。
2. その後にコード実装。PR body は要件変更と実装の両方を参照する。
3. ロードマップ: PR description に `T-01`, `T-02`... を列挙。
4. TaskCreate で登録し in_progress → completed を追跡。
5. 進捗式: `% = completed / total × 100`（四捨五入）。

---

## 4. GitHub 言語規約 / コミット / PR フルテンプレート

| Artifact | Language |
|---|---|
| README.md | English primary; Japanese via switch (toggle / README.ja.md) |
| Commit messages | English (imperative: `add`, `fix`, `update`) |
| PR title | English |
| PR body | English primary; Japanese in `<details>` toggle |
| Code comments / identifiers | English |
| Daily chat replies | **日本語** |
| CLAUDE.md / this file | Bilingual |

### Commit message format

```
<type>: <short English summary>

- <bullet: what changed>
- <bullet: why>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HnkrZxy1ErLnP4eJwgm9Nx
```

注意（ラチェット由来）: 本文には **diff に含まれるファイル名だけ** を書く。
diff に無いファイル名（例: 表の行として言及したいだけのファイル）は
「a row for the repository README」のように普通名詞で書く。

### PR body format

```markdown
## Summary
- bullet

## Changes
- `file`: what changed

<details>
<summary>🇯🇵 日本語補足 / Japanese notes</summary>

- 変更の背景・実装上の判断

</details>

## Test plan
- [ ] gates green (output pasted below)
```

---

## 5. テスト規律 — No "Designed but not running"

```
実装 → テスト設計（実装と同時）→ テスト実行 → 出力確認 → DONE
```

- テストは実装と同時に設計する。後回しにしない。
- ゲート出力なしに "done" と報告しない。テストランナーの結果を貼る。
- 禁止: 「実装しました。動くはずです」— テスト出力なし → 未完了。

---

## 6. コスト / 効率規律

- **Model**: 既定は Sonnet。Opus は困難なアーキテクチャ判断のみ。
- 同一セッションで読んだファイルを再読しない。入力が変わらない限りパス済みゲートを再実行しない。
- 独立したツール呼び出しは1メッセージに束ねて並列実行。
- **Local green is the source of truth** — CI はネットワークポリシーで setup 中断することがある。
  まずローカルでゲートを回す。doc/data のみの編集で重い CI を回さない。

---

## 7. ハーネスエンジニアリング原則（コーディング時に常時意識）

1. **Worker-Evaluator 分離** — 生成と評価を分ける。自己評価は楽観に流れるため、
   判定は決定論的ゲート（Auditor / CI / テスト）に委ねる。
2. **ラチェット原則** — 失敗は一方向の改善に変える。ミスが起きたら CLAUDE.md §C に
   追記して二度と繰り返さない。Auditor が検出した違反は修正と同時に必ず追記。
3. **ルール階層** — CLAUDE.md §A（絶対）＞ §B〜F（標準）＞ 当ファイル（詳細）。
4. **コンテキスト管理** — 大きな探索はサブエージェントに分離。長期タスクは
   ロードマップ / STATUS 系ドキュメントに永続化。
5. **フィードバックループ** — テスト・リンター・CI・Auditor をセンサーとして
   すべての変更に通す。センサーのない変更は入れない。
6. **段階的ロールアウト** — 新しい自動化は Report-Only → Shadow → 人間承認付き →
   完全自動 の順で昇格。評価セットで FP を測ってから次段へ。

---

## 9. Claude Code × Codex 協業ルール（開発ツール連携・要件§26）

> このリポジトリの成果物の仕様ではなく、**開発者（操作者）のローカル環境**での
> ツール連携方針。クラウドサンドボックスセッション（Codex未インストール）には
> 適用不可 — MCP登録は操作者のローカルマシンで行う。

### 9-1. 役割分担

| 役割 | 担当 | 内容 |
|---|---|---|
| 司令塔（Orchestrator） | Claude Code | 要件整理・設計・作業分解・PRレビュー・リスク洗い出し・「本当にそれでいい？」の壁打ち |
| 実装者（Implementer） | Codex（MCP経由） | 実装・差分作成・リファクタの下ごしらえ・既存コードに沿った修正案生成・小さな修正の高速反復 |

Claude Codeは実装コードを直接書かず、Codexへの委譲・レビュー・統合に徹する
（§7-1 Worker-Evaluator分離をツール連携にも適用する形）。

### 9-2. Codexの登録（操作者のローカル環境で1回）

```bash
claude mcp add codex --scope user -- codex mcp-server
```

Windows で `codex` が PATH に無い場合は絶対パスを、npx 経由なら `cmd /c npx -y @openai/codex mcp-server` を使う。
登録確認: `claude mcp list` / セッション内で `/mcp`。

### 9-3. 呼び出し規律

1. `codex` 呼び出しは1回につき1サブタスクのみ。
2. 毎回明示的に渡す: `cwd`（絶対パス）・`approval-policy: never`・`sandbox: workspace-write`
   （Codexの承認プロンプトは MCP elicitation 経由のため、渡さないと非対話実行できない）。
3. プロンプトに必ず含める:
   ```
   GOAL: <一文>
   FILES: <対象ファイルを明示。それ以外は触らせない>
   ACCEPTANCE: <成功基準となるコマンド、例: pytest -q tests/test_x.py が exit 0>
   CONSTRAINTS: <禁止事項、例: 新規依存追加禁止・API シグネチャ変更禁止>
   ```
4. 呼び出し後は毎回 `git diff` を確認してからレビュー・次の指示。承認せずに積み上げない。
5. 同一サブタスクの継続は新規 `codex` セッションでなく、返却された thread id で
   `codex-reply` を使う。
6. 双方向登録（CodexからClaude Codeを呼ぶ設定）はループの危険があるため、
   明示的に必要な場合を除き登録しない。

---

## 10. 変更履歴

- 2026-07-10: CLAUDE.md を必須7項目中心に再構成し、詳細を当ファイルへ分離。
- 2026-09-12: §9 Claude Code × Codex 協業ルールを追加。
