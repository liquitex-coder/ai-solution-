---
skill: video-reporter
version: "1.0"
agent: claim-crew
phase: BUILD
inputs:
  - video_urls: list[string]
  - keywords: list[string]
  - lang: "ja|en"
outputs:
  - transcripts: list[Transcript]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
  - source_urls: list[string]
auditor_required: true
memory_read:
  - シーン層
memory_write:
  - 事実層
---

# 03-video-reporter — YouTube 取材スキル (yt-dlp)

WF03 で使用。YouTube 動画の字幕をyt-dlpで抽出し、
キーワードマッチ箇所を切り出して要約付き取材結果を返す。

---

## DEFINE

**目的**: YouTube URL のリストから自動字幕 (auto-generated captions) を取得し、
keywords に関連するセグメントを抽出・要約する。

**制約**:
- yt-dlp: n8n Execute Command ノードまたはサイドカー Python スクリプトで実行
- 字幕なし動画は `confidence: UNVERIFIABLE` で返し、スキップ
- 著作権: 字幕テキストは 30% ルール適用。要約のみ提供
- 同一 video_id はシーン層で 30 日間ブロック

**成功条件**:
- 1 件以上の字幕抽出成功
- Auditor verdict = PASS

---

## PLAN

```
1. シーン層クエリ → 過去 30 日取材済み video_id 一覧
2. 各 URL から video_id を抽出 (YouTube URL パース)
3. シーン層既出を除外
4. yt-dlp コマンド実行:
   yt-dlp --write-auto-sub --sub-lang {lang} --skip-download
           --output /tmp/%(id)s -f best {url}
5. .vtt ファイルをパース → テキスト化
6. keywords 含むセグメント (±60秒) を抽出
7. Claude に要約依頼 (claim-llm 経由) → 300 字以内
8. 確度スコア:
   - 公式チャンネル (検証済みバッジ相当) → HIGH
   - 一般チャンネル → MED
   - 字幕取得失敗 → UNVERIFIABLE
9. 事実層に { video_id, url, title, scraped_at } を書き込む
10. シーン層に { video_id, researched_at } を書き込む
```

---

## BUILD

yt-dlp 実行 (n8n Execute Command ノード):

```bash
yt-dlp \
  --write-auto-sub \
  --sub-lang {{ $json.lang }} \
  --skip-download \
  --output "/tmp/yt/%(id)s" \
  --quiet \
  "{{ $json.video_url }}"
```

VTT パース (Function ノード):

```javascript
const vttText = $json.vtt_content || '';
// VTT タイムスタンプ行を除去してテキスト抽出
const lines = vttText.split('\n')
  .filter(l => !l.match(/^\d{2}:/) && !l.match(/^WEBVTT/) && l.trim())
  .join(' ')
  .replace(/<[^>]+>/g, '')  // HTMLタグ除去
  .replace(/\s+/g, ' ')
  .trim();
return { transcript_text: lines, char_count: lines.length };
```

---

## REVIEW

Auditor gate チェック項目:
- [ ] 字幕テキスト引用 ≤ 全体の 30%
- [ ] 出所 URL (YouTube URL) 明記
- [ ] video_id シーン層重複なし
- [ ] 字幕なし動画が UNVERIFIABLE で記録されている

---

## SHIP

後続の `10-article-writer` に `transcripts` を渡す。単体 SHIP なし。
