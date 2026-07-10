#!/usr/bin/env python3
"""
Patch all WF01-06 workflows:
1. Combined prompt loading (00-copyright-transform.md + per-WF prompt)
2. WP整形 node: output wp_status instead of status, add source_url
3. Insert Auditor Gate node between WP整形 and WP投稿
4. WP投稿 node: use wp_status dynamic field
5. WF06 critical fix: was status:'publish', now wp_status:'draft' (Auditor decides)
Create WF07 and WF08 skeleton workflows.
"""

import json
import copy
import pathlib

WF_DIR = pathlib.Path(__file__).parent.parent / "n8n" / "workflows"

# ── helpers ─────────────────────────────────────────────────────────────────

def combined_prompt_code(wf_file: str) -> str:
    return (
        "const GITHUB_TOKEN = $env.GITHUB_TOKEN || '';\n"
        "const BASE = 'https://api.github.com/repos/liquitex-coder/ai-solution-/contents/n8n/prompts/';\n"
        "const headers = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'n8n-ai-navi/1.0' };\n"
        "if (GITHUB_TOKEN) headers['Authorization'] = `token ${GITHUB_TOKEN}`;\n"
        "async function fetchPrompt(file) {\n"
        "  try {\n"
        "    const res = await fetch(BASE + file, { headers });\n"
        "    if (!res.ok) return '';\n"
        "    const data = await res.json();\n"
        "    return Buffer.from((data.content || '').replace(/\\n/g, ''), 'base64').toString('utf8');\n"
        "  } catch(e) { return ''; }\n"
        "}\n"
        "const [copyright, wfPrompt] = await Promise.all([\n"
        "  fetchPrompt('00-copyright-transform.md'),\n"
        f"  fetchPrompt('{wf_file}')\n"
        "]);\n"
        "return [{ json: { ...$json, promptContent: copyright + '\\n\\n---\\n\\n' + wfPrompt } }];"
    )


def auditor_gate_code(skill_ref: str) -> str:
    return (
        "// Auditor Gate — graceful degrade (INV-R2: LLM-free verdict)\n"
        "const auditorUrl = $env.CLAIM_AUDITOR_URL || '';\n"
        "const content = $json.content || '';\n"
        "const sourceUrl = $json.source_url || '';\n"
        "if (!auditorUrl) {\n"
        "  return [{ json: { ...$json, verdict: 'SKIP', wp_status: 'draft',\n"
        "    audit_note: 'CLAIM_AUDITOR_URL未設定 → 下書き保存' } }];\n"
        "}\n"
        "try {\n"
        "  const res = await fetch(`${auditorUrl}/audit`, {\n"
        "    method: 'POST',\n"
        "    headers: { 'Content-Type': 'application/json' },\n"
        "    body: JSON.stringify({\n"
        "      content,\n"
        "      source_urls: sourceUrl ? [sourceUrl] : [],\n"
        f"      skill_ref: '{skill_ref}'\n"
        "    })\n"
        "  });\n"
        "  if (!res.ok) {\n"
        "    return [{ json: { ...$json, verdict: 'UNVERIFIABLE', wp_status: 'draft',\n"
        "      audit_note: `Auditor HTTP ${res.status}` } }];\n"
        "  }\n"
        "  const result = await res.json();\n"
        "  return [{ json: { ...$json, ...result,\n"
        "    wp_status: result.verdict === 'PASS' ? 'publish' : 'draft' } }];\n"
        "} catch(e) {\n"
        "  return [{ json: { ...$json, verdict: 'UNVERIFIABLE', wp_status: 'draft',\n"
        "    audit_note: e.message } }];\n"
        "}"
    )


def auditor_gate_node(node_id: str, name: str, x: int, y: int, skill_ref: str) -> dict:
    return {
        "parameters": {"jsCode": auditor_gate_code(skill_ref)},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y]
    }


# ── WF01 ─────────────────────────────────────────────────────────────────────

def patch_wf01():
    path = WF_DIR / "01-github-ai-trending-daily.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        # 1. Combined prompt loading
        if nid == "p001wf01-aa00-4001-8001-000000000001":
            node["parameters"]["jsCode"] = combined_prompt_code("01-github-trending.md")

        # 2. WP整形: use wp_status + add source_url
        elif nid == "f6a7b8c9-d0e1-2345-fabc-456789012345":
            node["parameters"]["jsCode"] = (
                "const claudeJson = $json.content[0].text;\n"
                "const currentItem = $('上位5件を整形').item.json;\n"
                "const rank = currentItem.rank || 1;\n"
                "const repoName = currentItem.name || '';\n"
                "const shortName = repoName.split('/').pop();\n"
                "const title = `【AIツール】${shortName} - 注目のAIリポジトリ第${rank}位 | GitHubトレンド`;\n"
                "return [{ json: { title, content: claudeJson, wp_status: 'draft', source_url: currentItem.url || '' } }];"
            )

        # 4. WP投稿: dynamic wp_status, shift right
        elif nid == "a7b8c9d0-e1f2-3456-abcd-567890123456":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2000, 300]

    # 3. Insert Auditor Gate node
    gate = auditor_gate_node(
        "ag01wf01-aa00-4001-8001-000000000010",
        "Auditor Gate (WF-01)",
        1780, 300,
        "01-github-trending"
    )
    wf["nodes"].append(gate)

    # 5. Update connections
    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-01)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-01)"] = {
        "main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF01 patched")


# ── WF02 ─────────────────────────────────────────────────────────────────────

def patch_wf02():
    path = WF_DIR / "02-rss-monitor.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        if nid == "p002wf02-aa00-4002-8002-000000000002":
            node["parameters"]["jsCode"] = combined_prompt_code("02-rss-monitor.md")

        elif nid == "1e2f3a4b-5c6d-7890-1234-456789012345":
            node["parameters"]["jsCode"] = (
                "const claudeContent = $json.content[0].text;\n"
                "const rssItem = $('新記事フィルタリング（重複除外）').item.json;\n"
                "const link = rssItem.link || '';\n"
                "let source = 'AIニュース';\n"
                "if (link.includes('openai.com')) source = 'OpenAI';\n"
                "else if (link.includes('anthropic.com')) source = 'Anthropic';\n"
                "else if (link.includes('google')) source = 'Google AI';\n"
                "else if (link.includes('meta.ai') || link.includes('ai.meta')) source = 'Meta AI';\n"
                "return [{ json: { title: `【${source}】${rssItem.title}`, content: claudeContent, wp_status: 'draft', source_url: link } }];"
            )

        elif nid == "2f3a4b5c-6d7e-8901-2345-567890123456":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2240, 220]

    gate = auditor_gate_node(
        "ag02wf02-aa00-4002-8002-000000000010",
        "Auditor Gate (WF-02)",
        2020, 220,
        "02-rss-monitor"
    )
    wf["nodes"].append(gate)

    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-02)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-02)"] = {
        "main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF02 patched")


# ── WF03 ─────────────────────────────────────────────────────────────────────

def patch_wf03():
    path = WF_DIR / "03-youtube-summary.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        if nid == "p003wf03-aa00-4003-8003-000000000003":
            node["parameters"]["jsCode"] = combined_prompt_code("03-youtube-summary.md")

        elif nid == "wf03aa08-0000-4003-8003-000000000008":
            node["parameters"]["jsCode"] = (
                "const content = $json.content[0].text;\n"
                "const videoData = $('新動画フィルタリング').item.json;\n"
                "return [{ json: { title: `【YouTube要約】${videoData.title} - ${videoData.channelTitle}`, content, wp_status: 'draft', source_url: videoData.videoUrl || '' } }];"
            )

        elif nid == "wf03aa09-0000-4003-8003-000000000009":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2220, 180]

    gate = auditor_gate_node(
        "ag03wf03-aa00-4003-8003-000000000010",
        "Auditor Gate (WF-03)",
        2000, 180,
        "03-youtube-summary"
    )
    wf["nodes"].append(gate)

    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-03)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-03)"] = {
        "main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF03 patched")


# ── WF04 ─────────────────────────────────────────────────────────────────────

def patch_wf04():
    path = WF_DIR / "04-threads-influencer.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        if nid == "p004wf04-aa00-4004-8004-000000000004":
            node["parameters"]["jsCode"] = combined_prompt_code("04-threads-influencer.md")

        elif nid == "7788aa11-2233-4455-6677-889900112233":
            node["parameters"]["jsCode"] = (
                "const content = $json.content[0].text;\n"
                "const threadsData = $('AI関連投稿をフィルタリング').item.json;\n"
                "const firstPermalink = (threadsData.posts && threadsData.posts[0]) ? (threadsData.posts[0].permalink || '') : '';\n"
                "return [{ json: { title: `【Threads】@${threadsData.username}のAIノウハウまとめ（${threadsData.postCount}件）`, content, wp_status: 'draft', source_url: firstPermalink } }];"
            )

        elif nid == "8899bb22-3344-5566-7788-990011223344":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2220, 180]

    gate = auditor_gate_node(
        "ag04wf04-aa00-4004-8004-000000000010",
        "Auditor Gate (WF-04)",
        2000, 180,
        "04-threads-influencer"
    )
    wf["nodes"].append(gate)

    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-04)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-04)"] = {
        "main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF04 patched")


# ── WF05 ─────────────────────────────────────────────────────────────────────

def patch_wf05():
    path = WF_DIR / "05-note-monitor.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        if nid == "p005wf05-aa00-4005-8005-000000000005":
            node["parameters"]["jsCode"] = combined_prompt_code("05-note-monitor.md")

        elif nid == "aaaa7777-bbbb-8888-cccc-999900001111":
            node["parameters"]["jsCode"] = (
                "const content = $json.content[0].text;\n"
                "const noteData = $('新記事フィルタリング').item.json;\n"
                "return [{ json: { title: `【note】${noteData.title}`, content, wp_status: 'draft', source_url: noteData.link || '' } }];"
            )

        elif nid == "bbbb8888-cccc-9999-dddd-000011112222":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2220, 180]

    gate = auditor_gate_node(
        "ag05wf05-aa00-4005-8005-000000000010",
        "Auditor Gate (WF-05)",
        2000, 180,
        "05-note-monitor"
    )
    wf["nodes"].append(gate)

    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-05)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-05)"] = {
        "main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]
    }

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF05 patched")


# ── WF06 (CRITICAL FIX: status:'publish' → Auditor-controlled) ──────────────

def patch_wf06():
    path = WF_DIR / "06-weekly-trend-report.json"
    wf = json.loads(path.read_text())

    for node in wf["nodes"]:
        nid = node.get("id", "")
        if nid == "p006wf06-aa00-4006-8006-000000000006":
            node["parameters"]["jsCode"] = combined_prompt_code("06-weekly-report.md")

        # CRITICAL FIX: was status:'publish'
        elif nid == "66667777-8888-9999-0000-111122223333":
            node["parameters"]["jsCode"] = (
                "const content = $json.content[0].text;\n"
                "const weekStr = $('トレンドデータ集約').first().json.weekStr;\n"
                "const now = new Date();\n"
                "const monthDay = `${now.getMonth()+1}月${now.getDate()}日`;\n"
                "// wp_status is draft; Auditor Gate decides publish vs draft\n"
                "return [{ json: { title: `【週次AIトレンド】${monthDay}週 - 注目のAIニュース・ツールまとめ`, content, wp_status: 'draft' } }];"
            )

        # Was "WordPressに即時公開" with dynamic status from json — still need to update
        elif nid == "77778888-9999-0000-1111-222233334444":
            node["parameters"]["body"]["jsonBody"]["status"] = "={{ $json.wp_status }}"
            node["position"] = [2000, 300]

    gate = auditor_gate_node(
        "ag06wf06-aa00-4006-8006-000000000010",
        "Auditor Gate (WF-06)",
        1780, 300,
        "06-weekly-report"
    )
    wf["nodes"].append(gate)

    wf["connections"]["WordPress投稿データ整形"] = {
        "main": [[{"node": "Auditor Gate (WF-06)", "type": "main", "index": 0}]]
    }
    wf["connections"]["Auditor Gate (WF-06)"] = {
        "main": [[{"node": "WordPressに即時公開", "type": "main", "index": 0}]]
    }

    # Update notes to reflect fix
    wf["notes"] = (
        wf.get("notes", "") +
        "\n\n[FIXED 2026-07-10] WordPress投稿データ整形: status:'publish' → wp_status:'draft'.\n"
        "Auditor Gate now controls publish vs draft (INV-R2 compliance)."
    )

    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF06 patched (CRITICAL: publish→draft fix applied)")


# ── WF07 — NoimosAI Article Writer ──────────────────────────────────────────

def create_wf07():
    path = WF_DIR / "07-article-writer.json"
    wf = {
        "name": "07 NoimosAI記事ライター（手動トリガー）",
        "nodes": [
            {
                "parameters": {},
                "id": "wf07aa01-0000-4007-8007-000000000001",
                "name": "手動トリガー",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [240, 300]
            },
            {
                "parameters": {
                    "jsCode": (
                        "// Input: topic, angle, keywords (set by caller or defaults)\n"
                        "const topic = $json.topic || 'AI最新動向';\n"
                        "const angle = $json.angle || '実務活用';\n"
                        "const keywords = $json.keywords || 'AI,自動化,Claude';\n"
                        "return [{ json: { topic, angle, keywords, requestedAt: new Date().toISOString() } }];"
                    )
                },
                "id": "wf07aa02-0000-4007-8007-000000000002",
                "name": "記事パラメータ設定",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300]
            },
            {
                "parameters": {
                    "jsCode": combined_prompt_code("article-base.md")
                },
                "id": "p007wf07-aa00-4007-8007-000000000007",
                "name": "プロンプト読込み (WF-07)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [680, 300]
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
                                "content": "={{ $json.promptContent + '\\n\\n【記事パラメータ】\\nトピック: ' + $json.topic + '\\n切り口: ' + $json.angle + '\\nキーワード: ' + $json.keywords }}"
                            }]
                        }
                    },
                    "headers": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]}
                },
                "id": "wf07aa04-0000-4007-8007-000000000004",
                "name": "Claude APIで記事生成",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [900, 300],
                "credentials": {"httpHeaderAuth": {"id": "CLAUDE_API_CRED_ID", "name": "Claude API Key"}}
            },
            {
                "parameters": {
                    "jsCode": (
                        "const content = $json.content[0].text;\n"
                        "const params = $('記事パラメータ設定').item.json;\n"
                        "return [{ json: { title: `【AI解説】${params.topic} — ${params.angle}`, content, wp_status: 'draft', source_url: '' } }];"
                    )
                },
                "id": "wf07aa05-0000-4007-8007-000000000005",
                "name": "WordPress投稿データ整形",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1120, 300]
            },
            {
                "parameters": {
                    "jsCode": auditor_gate_code("07-article-writer")
                },
                "id": "ag07wf07-aa00-4007-8007-000000000010",
                "name": "Auditor Gate (WF-07)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1340, 300]
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "https://public-api.wordpress.com/wp/v2/sites/liquitex929aa21393-eyqci.wordpress.com/posts",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "body": {
                        "contentType": "json",
                        "jsonBody": {
                            "title": "={{ $json.title }}",
                            "content": "={{ $json.content }}",
                            "status": "={{ $json.wp_status }}"
                        }
                    }
                },
                "id": "wf07aa06-0000-4007-8007-000000000006",
                "name": "WordPressに投稿",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1560, 300],
                "credentials": {"httpHeaderAuth": {"id": "WORDPRESS_APP_PASSWORD_CRED_ID", "name": "WordPress App Password"}}
            },
            {
                "parameters": {},
                "id": "e007wf07-ee00-4007-8007-000000000007",
                "name": "エラートリガー",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [240, 600]
            }
        ],
        "connections": {
            "手動トリガー": {"main": [[{"node": "記事パラメータ設定", "type": "main", "index": 0}]]},
            "記事パラメータ設定": {"main": [[{"node": "プロンプト読込み (WF-07)", "type": "main", "index": 0}]]},
            "プロンプト読込み (WF-07)": {"main": [[{"node": "Claude APIで記事生成", "type": "main", "index": 0}]]},
            "Claude APIで記事生成": {"main": [[{"node": "WordPress投稿データ整形", "type": "main", "index": 0}]]},
            "WordPress投稿データ整形": {"main": [[{"node": "Auditor Gate (WF-07)", "type": "main", "index": 0}]]},
            "Auditor Gate (WF-07)": {"main": [[{"node": "WordPressに投稿", "type": "main", "index": 0}]]}
        },
        "active": False,
        "settings": {"executionOrder": "v1"},
        "tags": [{"name": "記事生成"}, {"name": "Claude"}],
        "notes": (
            "NoimosAI記事ライター — 手動またはWebhookで起動。\n"
            "入力: topic (トピック), angle (切り口), keywords (キーワード)\n"
            "プロンプト: n8n/prompts/article-base.md + 00-copyright-transform.md\n"
            "Auditor Gate: CLAIM_AUDITOR_URL が未設定の場合は下書き保存。\n"
            "必要な認証情報:\n"
            "1. Claude API Key (httpHeaderAuth): x-api-key: YOUR_CLAUDE_API_KEY\n"
            "2. WordPress App Password (httpHeaderAuth): Authorization: Basic base64(username:app_password)"
        )
    }
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF07 created")


# ── WF08 — Kimi ZH Translation ───────────────────────────────────────────────

def create_wf08():
    path = WF_DIR / "08-kimi-zh.json"
    wf = {
        "name": "08 Kimi ZH→JA 中国語AI記事翻訳",
        "nodes": [
            {
                "parameters": {
                    "rule": {"interval": [{"field": "hours", "hoursInterval": 6}]}
                },
                "id": "wf08aa01-0000-4008-8008-000000000001",
                "name": "6時間ごとトリガー",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [240, 300]
            },
            {
                "parameters": {
                    "jsCode": (
                        "// Chinese AI news sources (RSS/Atom)\n"
                        "const zhSources = [\n"
                        "  { url: 'https://www.jiqizhixin.com/rss', label: '机器之心' },\n"
                        "  { url: 'https://syncedreview.com/feed/', label: 'Synced Review' },\n"
                        "  { url: 'https://www.leiphone.com/feed', label: '雷锋网AI' }\n"
                        "];\n"
                        "const sixHoursAgo = new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString();\n"
                        "return zhSources.map(src => ({ json: { ...src, since: sixHoursAgo } }));"
                    )
                },
                "id": "wf08aa02-0000-4008-8008-000000000002",
                "name": "ZH記事ソース設定",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [460, 300]
            },
            {
                "parameters": {"url": "={{ $json.url }}"},
                "id": "wf08aa03-0000-4008-8008-000000000003",
                "name": "ZH RSS取得",
                "type": "n8n-nodes-base.rssFeedRead",
                "typeVersion": 1.1,
                "position": [680, 300]
            },
            {
                "parameters": {
                    "jsCode": (
                        "const processedUrls = $getWorkflowStaticData('global').zhProcessedUrls || [];\n"
                        "const items = $input.all();\n"
                        "const newItems = [];\n"
                        "for (const item of items) {\n"
                        "  const url = item.json.link || item.json.url;\n"
                        "  if (!url) continue;\n"
                        "  const pubDate = item.json.pubDate || item.json.isoDate;\n"
                        "  if (pubDate && (Date.now() - new Date(pubDate).getTime()) > 6 * 60 * 60 * 1000) continue;\n"
                        "  if (!processedUrls.includes(url)) {\n"
                        "    newItems.push({ json: {\n"
                        "      title_zh: item.json.title || '',\n"
                        "      link: url,\n"
                        "      pubDate: item.json.pubDate || new Date().toISOString(),\n"
                        "      summary_zh: (item.json.contentSnippet || '').slice(0, 800),\n"
                        "      source_label: $('ZH記事ソース設定').item.json.label || '中国語AI'\n"
                        "    } });\n"
                        "  }\n"
                        "}\n"
                        "const allUrls = [...processedUrls, ...newItems.map(i => i.json.link)];\n"
                        "$getWorkflowStaticData('global').zhProcessedUrls = allUrls.slice(-300);\n"
                        "return newItems.length > 0 ? newItems : [{ json: { skip: true } }];"
                    )
                },
                "id": "wf08aa04-0000-4008-8008-000000000004",
                "name": "新ZH記事フィルタリング",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [900, 300]
            },
            {
                "parameters": {
                    "conditions": {
                        "conditions": [{"leftValue": "={{ $json.skip }}", "rightValue": True, "operator": {"type": "boolean", "operation": "notEquals"}}],
                        "combinator": "and"
                    }
                },
                "id": "wf08aa05-0000-4008-8008-000000000005",
                "name": "新ZH記事あり？",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [1120, 300]
            },
            {
                "parameters": {
                    "jsCode": combined_prompt_code("08-kimi-zh.md")
                },
                "id": "p008wf08-aa00-4008-8008-000000000008",
                "name": "プロンプト読込み (WF-08)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1340, 180]
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "https://api.moonshot.cn/v1/chat/completions",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "body": {
                        "contentType": "json",
                        "jsonBody": {
                            "model": "moonshot-v1-128k",
                            "max_tokens": 3000,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "{{ $json.promptContent }}"
                                },
                                {
                                    "role": "user",
                                    "content": "={{ '【翻訳元記事】\\nタイトル (ZH): ' + $json.title_zh + '\\nURL: ' + $json.link + '\\n概要 (ZH): ' + ($json.summary_zh || '') }}"
                                }
                            ]
                        }
                    },
                    "headers": {"parameters": [{"name": "Content-Type", "value": "application/json"}]}
                },
                "id": "wf08aa07-0000-4008-8008-000000000007",
                "name": "Kimi APIでZH→JA翻訳・記事生成",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [1560, 180],
                "credentials": {"httpHeaderAuth": {"id": "KIMI_API_CRED_ID", "name": "Kimi API Key"}}
            },
            {
                "parameters": {
                    "jsCode": (
                        "const content = $json.choices[0].message.content;\n"
                        "const zhData = $('新ZH記事フィルタリング').item.json;\n"
                        "return [{ json: { title: `【中国AI翻訳】${zhData.source_label}: ${zhData.title_zh}`, content, wp_status: 'draft', source_url: zhData.link || '' } }];"
                    )
                },
                "id": "wf08aa08-0000-4008-8008-000000000008",
                "name": "WordPress投稿データ整形",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [1780, 180]
            },
            {
                "parameters": {
                    "jsCode": auditor_gate_code("08-kimi-zh")
                },
                "id": "ag08wf08-aa00-4008-8008-000000000010",
                "name": "Auditor Gate (WF-08)",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [2000, 180]
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": "https://public-api.wordpress.com/wp/v2/sites/liquitex929aa21393-eyqci.wordpress.com/posts",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "body": {
                        "contentType": "json",
                        "jsonBody": {
                            "title": "={{ $json.title }}",
                            "content": "={{ $json.content }}",
                            "status": "={{ $json.wp_status }}"
                        }
                    }
                },
                "id": "wf08aa09-0000-4008-8008-000000000009",
                "name": "WordPressに下書き投稿",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [2220, 180],
                "credentials": {"httpHeaderAuth": {"id": "WORDPRESS_APP_PASSWORD_CRED_ID", "name": "WordPress App Password"}}
            },
            {
                "parameters": {},
                "id": "wf08aa10-0000-4008-8008-000000000010",
                "name": "新ZH記事なし（スキップ）",
                "type": "n8n-nodes-base.noOp",
                "typeVersion": 1,
                "position": [1340, 420]
            },
            {
                "parameters": {},
                "id": "e008wf08-ee00-4008-8008-000000000008",
                "name": "エラートリガー",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [240, 600]
            }
        ],
        "connections": {
            "6時間ごとトリガー": {"main": [[{"node": "ZH記事ソース設定", "type": "main", "index": 0}]]},
            "ZH記事ソース設定": {"main": [[{"node": "ZH RSS取得", "type": "main", "index": 0}]]},
            "ZH RSS取得": {"main": [[{"node": "新ZH記事フィルタリング", "type": "main", "index": 0}]]},
            "新ZH記事フィルタリング": {"main": [[{"node": "新ZH記事あり？", "type": "main", "index": 0}]]},
            "新ZH記事あり？": {
                "main": [
                    [{"node": "プロンプト読込み (WF-08)", "type": "main", "index": 0}],
                    [{"node": "新ZH記事なし（スキップ）", "type": "main", "index": 0}]
                ]
            },
            "プロンプト読込み (WF-08)": {"main": [[{"node": "Kimi APIでZH→JA翻訳・記事生成", "type": "main", "index": 0}]]},
            "Kimi APIでZH→JA翻訳・記事生成": {"main": [[{"node": "WordPress投稿データ整形", "type": "main", "index": 0}]]},
            "WordPress投稿データ整形": {"main": [[{"node": "Auditor Gate (WF-08)", "type": "main", "index": 0}]]},
            "Auditor Gate (WF-08)": {"main": [[{"node": "WordPressに下書き投稿", "type": "main", "index": 0}]]}
        },
        "active": False,
        "settings": {"executionOrder": "v1"},
        "tags": [{"name": "Kimi"}, {"name": "ZH翻訳"}, {"name": "AI情報収集"}],
        "notes": (
            "Kimi ZH→JA 中国語AI記事翻訳ワークフロー\n"
            "Sources: 机器之心, Synced Review, 雷锋网AI (RSS)\n"
            "LLM: Kimi API (moonshot-v1-128k) — 年契約済み\n"
            "プロンプト: n8n/prompts/08-kimi-zh.md + 00-copyright-transform.md\n"
            "Auditor Gate: CLAIM_AUDITOR_URL が未設定の場合は下書き保存。\n"
            "必要な認証情報:\n"
            "1. Kimi API Key (httpHeaderAuth): Authorization: Bearer YOUR_KIMI_API_KEY\n"
            "   → 環境変数 KIMI_API_KEY として設定\n"
            "2. WordPress App Password (httpHeaderAuth): Authorization: Basic base64(username:app_password)\n"
            "スケジュール: 6時間ごと"
        )
    }
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2))
    print("✅ WF08 created")


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    patch_wf01()
    patch_wf02()
    patch_wf03()
    patch_wf04()
    patch_wf05()
    patch_wf06()
    create_wf07()
    create_wf08()
    print("\n✅ All done — 6 patched, 2 created")
