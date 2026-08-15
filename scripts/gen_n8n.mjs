#!/usr/bin/env node
// Generate importable n8n workflow JSON for native reporters (WF-07-13) from
// the tested modules. Code-node bodies are the modules' own function sources
// (via Function.prototype.toString), so the workflow cannot drift from the
// code that the test suite verifies. See docs/requirements.md §15-8.
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { NATIVE, fixturePathFor } from '../reporters/registry.mjs';
import { baseClaudeRequest, baseWpPayload, extractText, titleFromH2 } from '../reporters/core.mjs';
import {
  assertArticleHtml, assertDisclosure, assertWpPayload,
  FORBIDDEN_TAGS, FORBIDDEN_PHRASES,
  DISCLOSURE_KINDS, DISCLOSURE_NOTICES, DISCLOSURE_HEAD_WINDOW,
} from '../reporters/validators.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = 'liquitex-coder/ai-solution-';
const WP_URL = 'https://public-api.wordpress.com/wp/v2/sites/liquitex929aa21393-eyqci.wordpress.com/posts';

const CRON = { daily: '0 22 * * *', weekly: '0 1 * * 1', 'every-5-min': '*/5 * * * *' };

function metaOf(r) {
  return {
    id: r.id,
    slug: r.slug,
    title: r.title,
    category: r.category,
    categorySlug: r.categorySlug,
    model: r.model,
    trigger: r.trigger,
  };
}

function fnSrc(fn) {
  return fn.toString();
}

// Body of the "build Claude request" Code node: normalize + buildClaudeRequest,
// pulled verbatim from the reporter module.
function requestNodeCode(reporter) {
  const meta = metaOf(reporter);
  return [
    `// AUTO-GENERATED from reporters/reporters/${reporter.id}-${reporter.slug}.mjs — do not edit; run "npm run gen:n8n"`,
    `const meta = ${JSON.stringify(meta)};`,
    fnSrc(baseClaudeRequest),
    fnSrc(reporter.normalize),
    fnSrc(reporter.buildClaudeRequest),
    `const rawSource = $json.rawSource;`,
    `const prompt = $json.promptContent || '';`,
    `const items = normalize(rawSource);`,
    `const claudeBody = buildClaudeRequest({ items, prompt, model: meta.model });`,
    `return [{ json: { claudeBody } }];`,
  ].join('\n');
}

// Body of the "render article + WP payload" Code node: parseArticle +
// buildWpPayload + assertWpPayload (fail-closed before posting).
function renderNodeCode(reporter) {
  const meta = metaOf(reporter);
  return [
    `// AUTO-GENERATED from reporters/reporters/${reporter.id}-${reporter.slug}.mjs — do not edit; run "npm run gen:n8n"`,
    `const meta = ${JSON.stringify(meta)};`,
    `const FORBIDDEN_TAGS = ${JSON.stringify(FORBIDDEN_TAGS)};`,
    `const FORBIDDEN_PHRASES = ${JSON.stringify(FORBIDDEN_PHRASES)};`,
    `const DISCLOSURE_KINDS = ${JSON.stringify(DISCLOSURE_KINDS)};`,
    `const DISCLOSURE_NOTICES = ${JSON.stringify(DISCLOSURE_NOTICES)};`,
    `const DISCLOSURE_HEAD_WINDOW = ${JSON.stringify(DISCLOSURE_HEAD_WINDOW)};`,
    fnSrc(extractText),
    fnSrc(titleFromH2),
    fnSrc(baseWpPayload),
    fnSrc(assertArticleHtml),
    fnSrc(assertDisclosure),
    fnSrc(assertWpPayload),
    fnSrc(reporter.parseArticle),
    fnSrc(reporter.buildWpPayload),
    `const claudeResponse = $json;`,
    `const article = parseArticle(claudeResponse);`,
    `const wpPayload = buildWpPayload(article);`,
    `assertWpPayload(wpPayload); // reject malformed article before posting`,
    `return [{ json: wpPayload }];`,
  ].join('\n');
}

function promptNodeCode(reporter) {
  const file = `${reporter.id}-${reporter.slug}.md`;
  return [
    `const GITHUB_TOKEN = $env.GITHUB_TOKEN || '';`,
    `const PROMPT_FILE = '${file}';`,
    `const promptUrl = \`https://api.github.com/repos/${REPO}/contents/n8n/prompts/\${PROMPT_FILE}\`;`,
    `const headers = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'n8n-ai-navi/1.0' };`,
    `if (GITHUB_TOKEN) headers['Authorization'] = \`token \${GITHUB_TOKEN}\`;`,
    `let promptContent = '';`,
    `try {`,
    `  const res = await fetch(promptUrl, { headers });`,
    `  if (res.ok) { const data = await res.json(); promptContent = Buffer.from((data.content || '').replace(/\\n/g, ''), 'base64').toString('utf8'); }`,
    `} catch (e) { promptContent = '<!-- prompt fetch failed -->'; }`,
    `return [{ json: { ...$json, promptContent } }];`,
  ].join('\n');
}

function id(reporter, n) {
  return `wf${reporter.id}node${String(n).padStart(2, '0')}-0000-4000-8000-000000000000`;
}

function triggerNode(reporter) {
  if (reporter.trigger === 'on-submit') {
    return {
      parameters: { httpMethod: 'POST', path: `reporter-${reporter.slug}`, options: {} },
      id: id(reporter, 0),
      name: 'Webhook（読者投稿）',
      type: 'n8n-nodes-base.webhook',
      typeVersion: 2,
      position: [240, 300],
    };
  }
  const cron = CRON[reporter.trigger] || '0 0 * * *';
  return {
    parameters: { rule: { interval: [{ field: 'cronExpression', expression: cron }] } },
    id: id(reporter, 0),
    name: `トリガー（${reporter.trigger}）`,
    type: 'n8n-nodes-base.scheduleTrigger',
    typeVersion: 1.2,
    position: [240, 300],
  };
}

function codeNode(reporter, n, name, jsCode) {
  return {
    parameters: { jsCode },
    id: id(reporter, n),
    name,
    type: 'n8n-nodes-base.code',
    typeVersion: 2,
    position: [240 + n * 220, 300],
  };
}

export function buildWorkflow(reporter, fixtureRawSource) {
  const trigger = triggerNode(reporter);
  const source = codeNode(
    reporter, 1, 'ソース入力（例データ・要差し替え）',
    `// Example input so a manual run produces a real draft. Replace with your real source.\nreturn [{ json: { rawSource: ${JSON.stringify(fixtureRawSource)} } }];`,
  );
  const promptLoad = codeNode(reporter, 2, `プロンプト読込み (WF-${reporter.id})`, promptNodeCode(reporter));
  const buildReq = codeNode(reporter, 3, 'リクエスト生成 (normalize+buildClaudeRequest)', requestNodeCode(reporter));

  const claude = {
    parameters: {
      method: 'POST',
      url: 'https://api.anthropic.com/v1/messages',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpHeaderAuth',
      body: { contentType: 'json', jsonBody: '={{ $json.claudeBody }}' },
      headers: { parameters: [{ name: 'anthropic-version', value: '2023-06-01' }] },
    },
    id: id(reporter, 4),
    name: 'Claude API',
    type: 'n8n-nodes-base.httpRequest',
    typeVersion: 4.2,
    position: [240 + 4 * 220, 300],
    credentials: { httpHeaderAuth: { id: 'CLAUDE_API_CRED_ID', name: 'Claude API Key' } },
  };

  const render = codeNode(reporter, 5, '記事生成 (parseArticle+buildWpPayload+validate)', renderNodeCode(reporter));

  const wp = {
    parameters: {
      method: 'POST',
      url: WP_URL,
      authentication: 'genericCredentialType',
      genericAuthType: 'httpHeaderAuth',
      body: {
        contentType: 'json',
        jsonBody: { title: '={{ $json.title }}', content: '={{ $json.content }}', status: '={{ $json.status }}' },
      },
    },
    id: id(reporter, 6),
    name: 'WordPressに下書き投稿',
    type: 'n8n-nodes-base.httpRequest',
    typeVersion: 4.2,
    position: [240 + 6 * 220, 300],
    credentials: { httpHeaderAuth: { id: 'WORDPRESS_APP_PASSWORD_CRED_ID', name: 'WordPress App Password' } },
  };

  const errorTrigger = {
    parameters: {},
    id: id(reporter, 9),
    name: 'エラートリガー',
    type: 'n8n-nodes-base.errorTrigger',
    typeVersion: 1,
    position: [240, 600],
  };

  const chain = [trigger, source, promptLoad, buildReq, claude, render, wp];
  const connections = {};
  for (let i = 0; i < chain.length - 1; i++) {
    connections[chain[i].name] = { main: [[{ node: chain[i + 1].name, type: 'main', index: 0 }]] };
  }

  return {
    name: `${reporter.id} ${reporter.title}`,
    nodes: [...chain, errorTrigger],
    connections,
    active: false,
    settings: { executionOrder: 'v1' },
    tags: [{ name: 'AI記者' }, { name: reporter.category }],
    notes:
      `AUTO-GENERATED from reporters/reporters/${reporter.id}-${reporter.slug}.mjs. ` +
      `Do not edit Code nodes by hand — edit the module and run "npm run gen:n8n".\n\n` +
      `Required credentials: Claude API Key (httpHeaderAuth: x-api-key), ` +
      `WordPress App Password (httpHeaderAuth: Authorization Basic).\n` +
      `Prompt is loaded from n8n/prompts/${reporter.id}-${reporter.slug}.md at runtime.\n` +
      `The "ソース入力" node holds example data so a manual run yields a real draft; replace it with your real source.`,
  };
}

async function loadFixtureRawSource(reporter) {
  const abs = resolve(ROOT, 'reporters', fixturePathFor(reporter));
  const fixture = JSON.parse(await readFile(abs, 'utf8'));
  return fixture.rawSource;
}

export async function generateAll() {
  const out = [];
  for (const reporter of NATIVE) {
    const rawSource = await loadFixtureRawSource(reporter);
    const wf = buildWorkflow(reporter, rawSource);
    out.push({ reporter, wf });
  }
  return out;
}

async function main() {
  const generated = await generateAll();
  for (const { reporter, wf } of generated) {
    const file = resolve(ROOT, 'n8n/workflows', `${reporter.id}-${reporter.slug}.json`);
    await writeFile(file, JSON.stringify(wf, null, 2) + '\n', 'utf8');
    console.log(`wrote n8n/workflows/${reporter.id}-${reporter.slug}.json`);
  }
  console.log(`\nGenerated ${generated.length} workflow(s).`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
