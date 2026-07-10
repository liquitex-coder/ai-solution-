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

## 8. 変更履歴

- 2026-07-10: CLAUDE.md を必須7項目中心に再構成し、詳細を当ファイルへ分離。
