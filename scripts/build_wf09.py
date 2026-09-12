#!/usr/bin/env python3
"""Build n8n/workflows/09-multi-source-research.json (requirements §WF09).

9-media cross-source research: GitHub / RSS / YouTube / Threads / note /
Reddit / Hacker News / ZH / NoimosAI → confidence scoring (§19-6) →
combined prompt (00-copyright + 09) → Claude → Auditor Gate → WordPress.

Sources without credentials are skipped gracefully and recorded in
`coverage` so the article never silently pretends full coverage.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from patch_workflows import combined_prompt_code, auditor_gate_code  # noqa: E402

WF_DIR = pathlib.Path(__file__).parent.parent / "n8n" / "workflows"

RESEARCH_CODE = r"""// 9-media sweep — public APIs directly; credentialed sources skip gracefully.
const topic = $json.topic;
const query = encodeURIComponent(topic);
const GITHUB_TOKEN = $env.GITHUB_TOKEN || '';
const YOUTUBE_API_KEY = $env.YOUTUBE_API_KEY || '';
const sinceIso = $json.sinceIso;
const items = [];      // { medium, title, url, snippet, publishedAt }
const coverage = {};   // medium -> 'ok' | 'skipped:no-credential' | 'error:...'

async function safeJson(url, headers) {
  const res = await fetch(url, { headers: headers || {} });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// 1. GitHub
try {
  const gh = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'n8n-ai-navi/1.0' };
  if (GITHUB_TOKEN) gh['Authorization'] = `token ${GITHUB_TOKEN}`;
  const d = await safeJson(`https://api.github.com/search/repositories?q=${query}+pushed:>${sinceIso.slice(0,10)}&sort=stars&order=desc&per_page=5`, gh);
  for (const r of d.items || []) {
    items.push({ medium: 'github', title: r.full_name, url: r.html_url,
      snippet: (r.description || '').slice(0, 300), publishedAt: r.updated_at,
      stars: r.stargazers_count });
  }
  coverage.github = 'ok';
} catch (e) { coverage.github = `error:${e.message}`; }

// 2. Hacker News (Algolia)
try {
  const d = await safeJson(`https://hn.algolia.com/api/v1/search?query=${query}&tags=story&numericFilters=created_at_i>${Math.floor(new Date(sinceIso).getTime()/1000)}&hitsPerPage=5`);
  for (const h of d.hits || []) {
    items.push({ medium: 'hackernews', title: h.title || '',
      url: h.url || `https://news.ycombinator.com/item?id=${h.objectID}`,
      snippet: (h.story_text || '').slice(0, 300), publishedAt: h.created_at,
      points: h.points });
  }
  coverage.hackernews = 'ok';
} catch (e) { coverage.hackernews = `error:${e.message}`; }

// 3. Reddit (public JSON)
try {
  const d = await safeJson(`https://www.reddit.com/search.json?q=${query}&sort=top&t=week&limit=5`,
    { 'User-Agent': 'n8n-ai-navi/1.0' });
  for (const c of (d.data && d.data.children) || []) {
    const p = c.data;
    items.push({ medium: 'reddit', title: p.title || '',
      url: `https://www.reddit.com${p.permalink}`,
      snippet: (p.selftext || '').slice(0, 300),
      publishedAt: new Date(p.created_utc * 1000).toISOString(), score: p.score });
  }
  coverage.reddit = 'ok';
} catch (e) { coverage.reddit = `error:${e.message}`; }

// 4. RSS (official AI blogs — same set as WF02)
const RSS_FEEDS = [
  { url: 'https://openai.com/blog/rss.xml', label: 'OpenAI' },
  { url: 'https://www.anthropic.com/blog.rss', label: 'Anthropic' },
  { url: 'https://blog.google/technology/ai/rss/', label: 'Google AI' }
];
let rssOk = 0;
for (const feed of RSS_FEEDS) {
  try {
    const res = await fetch(feed.url, { headers: { 'User-Agent': 'n8n-ai-navi/1.0' } });
    if (!res.ok) continue;
    const xml = await res.text();
    const entries = xml.split(/<item>|<entry>/).slice(1, 4);
    for (const en of entries) {
      const t = (en.match(/<title[^>]*>([\s\S]*?)<\/title>/) || [])[1] || '';
      const l = (en.match(/<link[^>]*>([\s\S]*?)<\/link>/) || [])[1]
        || (en.match(/<link[^>]*href="([^"]+)"/) || [])[1] || '';
      const pd = (en.match(/<pubDate>([\s\S]*?)<\/pubDate>/) || [])[1]
        || (en.match(/<published>([\s\S]*?)<\/published>/) || [])[1] || '';
      if (pd && new Date(pd) < new Date(sinceIso)) continue;
      if (t) items.push({ medium: 'rss', source: feed.label,
        title: t.replace(/<!\[CDATA\[|\]\]>/g, '').trim(), url: l.trim(),
        snippet: '', publishedAt: pd });
    }
    rssOk++;
  } catch (e) { /* per-feed failure tolerated */ }
}
coverage.rss = rssOk > 0 ? `ok (${rssOk}/${RSS_FEEDS.length} feeds)` : 'error:all-feeds-failed';

// 5. note (hashtag RSS)
try {
  const res = await fetch('https://note.com/hashtag/%E7%94%9F%E6%88%90AI/rss',
    { headers: { 'User-Agent': 'n8n-ai-navi/1.0' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const xml = await res.text();
  for (const en of xml.split('<item>').slice(1, 6)) {
    const t = (en.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || '';
    const l = (en.match(/<link>([\s\S]*?)<\/link>/) || [])[1] || '';
    const pd = (en.match(/<pubDate>([\s\S]*?)<\/pubDate>/) || [])[1] || '';
    if (pd && new Date(pd) < new Date(sinceIso)) continue;
    if (t) items.push({ medium: 'note',
      title: t.replace(/<!\[CDATA\[|\]\]>/g, '').trim(), url: l.trim(),
      snippet: '', publishedAt: pd });
  }
  coverage.note = 'ok';
} catch (e) { coverage.note = `error:${e.message}`; }

// 6. YouTube — needs API key
if (YOUTUBE_API_KEY) {
  try {
    const d = await safeJson(`https://www.googleapis.com/youtube/v3/search?part=snippet&q=${query}&type=video&order=relevance&publishedAfter=${sinceIso}&maxResults=5&key=${YOUTUBE_API_KEY}`);
    for (const v of d.items || []) {
      items.push({ medium: 'youtube', title: v.snippet?.title || '',
        url: `https://www.youtube.com/watch?v=${v.id?.videoId}`,
        snippet: (v.snippet?.description || '').slice(0, 300),
        publishedAt: v.snippet?.publishedAt });
    }
    coverage.youtube = 'ok';
  } catch (e) { coverage.youtube = `error:${e.message}`; }
} else { coverage.youtube = 'skipped:no-credential (YOUTUBE_API_KEY)'; }

// 7-9. Credentialed / dedicated-WF sources — covered by their own workflows
coverage.threads = 'skipped:covered-by-WF04';
coverage.zh = 'skipped:covered-by-WF08';
coverage.noimosai = 'skipped:covered-by-WF07';

return [{ json: { topic, sinceIso, items, coverage,
  mediaCovered: Object.values(coverage).filter(v => String(v).startsWith('ok')).length } }];"""

CONFIDENCE_CODE = r"""// Confidence scoring (§19-6): cross-source corroboration via keyword overlap.
const KNOWN_MEDIA = ['OpenAI', 'Anthropic', 'Google AI'];
const data = $json;
const items = data.items || [];

function keywords(s) {
  return new Set((s || '').toLowerCase()
    .replace(/[^a-z0-9぀-ヿ一-鿿\s]/g, ' ')
    .split(/\s+/).filter(w => w.length >= 3));
}
function overlap(a, b) {
  const ka = keywords(a), kb = keywords(b);
  if (!ka.size || !kb.size) return 0;
  let n = 0;
  for (const w of ka) if (kb.has(w)) n++;
  return n / Math.min(ka.size, kb.size);
}

const scored = items.map((item, i) => {
  // corroborated = similar title reported by a DIFFERENT medium
  const corroborated = items.some((other, j) =>
    j !== i && other.medium !== item.medium && overlap(item.title, other.title) >= 0.5);
  let confidence;
  if (corroborated) confidence = 'HIGH';
  else if (item.medium === 'rss' && KNOWN_MEDIA.includes(item.source)) confidence = 'MED';
  else if (item.medium === 'github' && (item.stars || 0) >= 500) confidence = 'MED';
  else confidence = 'LOW';
  return { ...item, confidence };
});

// fetch failures surface as UNVERIFIABLE coverage notes for the article
const failures = Object.entries(data.coverage || {})
  .filter(([, v]) => String(v).startsWith('error'))
  .map(([medium, v]) => ({ medium, status: v, confidence: 'UNVERIFIABLE' }));

return [{ json: { ...data, items: scored, coverageFailures: failures } }];"""

WP_FORMAT_CODE = r"""const content = $json.content[0].text;
const research = $('確度スコア付与').item.json;
const now = new Date();
const monthDay = `${now.getMonth() + 1}月${now.getDate()}日`;
const sourceUrls = (research.items || []).map(i => i.url).filter(Boolean);
return [{ json: {
  title: `【横断調査】${research.topic} — 9媒体クロスリサーチ（${monthDay}）`,
  content,
  wp_status: 'draft',
  source_url: sourceUrls[0] || '',
  source_urls: sourceUrls
} }];"""


def build() -> None:
    wf = {
        "name": "09 9媒体横断調査（週次・確度スコア付き）",
        "nodes": [
            {
                "parameters": {"rule": {"interval": [
                    {"field": "cronExpression", "expression": "0 22 * * 4"}]}},
                "id": "wf09aa01-0000-4009-8009-000000000001",
                "name": "毎週金曜7時 (JST) トリガー",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [240, 300]
            },
            {
                "parameters": {"jsCode": (
                    "// Research topic — override via manual execution input\n"
                    "const topic = $json.topic || 'AI agents LLM';\n"
                    "const sinceIso = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();\n"
                    "return [{ json: { topic, sinceIso } }];")},
                "id": "wf09aa02-0000-4009-8009-000000000002",
                "name": "調査テーマ設定",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300]
            },
            {
                "parameters": {"jsCode": RESEARCH_CODE},
                "id": "wf09aa03-0000-4009-8009-000000000003",
                "name": "9媒体横断取材",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [680, 300]
            },
            {
                "parameters": {"jsCode": CONFIDENCE_CODE},
                "id": "wf09aa04-0000-4009-8009-000000000004",
                "name": "確度スコア付与",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [900, 300]
            },
            {
                "parameters": {"jsCode": combined_prompt_code("09-multi-source-research.md")},
                "id": "p009wf09-aa00-4009-8009-000000000009",
                "name": "プロンプト読込み (WF-09)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1120, 300]
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "https://api.anthropic.com/v1/messages",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "body": {
                        "contentType": "json",
                        "jsonBody": {
                            "model": "claude-sonnet-5",
                            "max_tokens": 4000,
                            "messages": [{
                                "role": "user",
                                "content": "={{ $json.promptContent + '\\n\\n【調査データ（確度スコア付き）】\\nテーマ: ' + $json.topic + '\\n媒体カバレッジ: ' + JSON.stringify($json.coverage) + '\\n取材結果:\\n' + JSON.stringify($json.items) + '\\n取材失敗媒体: ' + JSON.stringify($json.coverageFailures) }}"
                            }]
                        }
                    },
                    "headers": {"parameters": [
                        {"name": "anthropic-version", "value": "2023-06-01"}]}
                },
                "id": "wf09aa06-0000-4009-8009-000000000006",
                "name": "Claude APIで深掘り記事生成",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1340, 300],
                "credentials": {"httpHeaderAuth": {
                    "id": "CLAUDE_API_CRED_ID", "name": "Claude API Key"}}
            },
            {
                "parameters": {"jsCode": WP_FORMAT_CODE},
                "id": "wf09aa07-0000-4009-8009-000000000007",
                "name": "WordPress投稿データ整形",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1560, 300]
            },
            {
                "parameters": {"jsCode": auditor_gate_code("09-multi-source-research")},
                "id": "ag09wf09-aa00-4009-8009-000000000010",
                "name": "Auditor Gate (WF-09)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1780, 300]
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "https://public-api.wordpress.com/wp/v2/sites/liquitex929aa21393-eyqci.wordpress.com/posts",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "body": {"contentType": "json", "jsonBody": {
                        "title": "={{ $json.title }}",
                        "content": "={{ $json.content }}",
                        "status": "={{ $json.wp_status }}"}}
                },
                "id": "wf09aa08-0000-4009-8009-000000000008",
                "name": "WordPressに下書き投稿",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [2000, 300],
                "credentials": {"httpHeaderAuth": {
                    "id": "WORDPRESS_APP_PASSWORD_CRED_ID",
                    "name": "WordPress App Password"}}
            },
            {
                "parameters": {},
                "id": "e009wf09-ee00-4009-8009-000000000009",
                "name": "エラートリガー",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [240, 600]
            }
        ],
        "connections": {
            "毎週金曜7時 (JST) トリガー": {"main": [[{"node": "調査テーマ設定", "type": "main", "index": 0}]]},
            "調査テーマ設定": {"main": [[{"node": "9媒体横断取材", "type": "main", "index": 0}]]},
            "9媒体横断取材": {"main": [[{"node": "確度スコア付与", "type": "main", "index": 0}]]},
            "確度スコア付与": {"main": [[{"node": "プロンプト読込み (WF-09)", "type": "main", "index": 0}]]},
            "プロンプト読込み (WF-09)": {"main": [[{"node": "Claude APIで深掘り記事生成", "type": "main", "index": 0}]]},
            "Claude APIで深掘り記事生成": {"main": [[{"node": "WordPress投稿データ整形", "type": "main", "index": 0}]]},
            "WordPress投稿データ整形": {"main": [[{"node": "Auditor Gate (WF-09)", "type": "main", "index": 0}]]},
            "Auditor Gate (WF-09)": {"main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]}
        },
        "active": False,
        "settings": {"executionOrder": "v1"},
        "tags": [{"name": "横断調査"}, {"name": "確度スコア"}, {"name": "AI情報収集"}],
        "notes": (
            "WF09: 9媒体横断調査（requirements §WF09 / §19-6 確度スコア）\n"
            "直接取材: GitHub / Hacker News / Reddit / RSS(公式ブログ3件) / note\n"
            "YOUTUBE_API_KEY 設定時: YouTube も取材（未設定なら skipped と記録）\n"
            "Threads/ZH/NoimosAI は専用WF (04/08/07) がカバー → coverage に明記\n"
            "確度スコア: 複数媒体で裏取り=HIGH / 公式ブログ・500★以上=MED / 他=LOW\n"
            "取材失敗媒体は UNVERIFIABLE として記事プロンプトに渡す（沈黙しない）\n"
            "Auditor Gate: CLAIM_AUDITOR_URL 未設定 → 下書き保存\n"
            "スケジュール: 毎週木曜 22:00 UTC (= 金曜 07:00 JST)\n"
            "必要な認証情報: Claude API Key / WordPress App Password\n"
            "任意: GITHUB_TOKEN, YOUTUBE_API_KEY (n8n 環境変数)"
        )
    }
    out = WF_DIR / "09-multi-source-research.json"
    out.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print(f"✅ WF09 written: {out}")


if __name__ == "__main__":
    build()
