#!/usr/bin/env node
// End-to-end smoke test: run a reporter for real and post the result to
// WordPress. See docs/requirements.md §15-10.
//
// Usage:
//   node scripts/e2e_smoke.mjs --id 07            # real Claude (if key) -> real WP
//   node scripts/e2e_smoke.mjs --id 07 --offline  # skip Claude, use fixture -> real WP
//
// Env: ANTHROPIC_API_KEY (for live Claude), and WP_POSTS_URL or WP_URL,
//      WP_USERNAME, WP_APP_PASSWORD (for the WordPress post).
// Missing credentials cause a clearly-explained SKIP (exit 0), never a fake pass.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { NATIVE, fixturePathFor, promptPathFor } from '../reporters/registry.mjs';
import { assertWpPayload } from '../reporters/validators.mjs';
import { postDraft, resolvePostsUrl } from '../reporters/wp_client.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');

function parseArgs(argv) {
  const a = { id: '07', offline: false, publish: false };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--id') a.id = argv[++i];
    else if (argv[i] === '--offline') a.offline = true;
    else if (argv[i] === '--publish') a.publish = true;
  }
  return a;
}

async function readJson(p) {
  return JSON.parse(await readFile(p, 'utf8'));
}

async function callClaude(apiKey, claudeBody) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(claudeBody),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Claude API ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

async function main() {
  const args = parseArgs(process.argv);
  const reporter = NATIVE.find((r) => r.id === args.id);
  if (!reporter) {
    console.error(`No native reporter with id=${args.id}`);
    process.exit(2);
  }

  const fixture = await readJson(resolve(ROOT, 'reporters', fixturePathFor(reporter)));
  const prompt = await readFile(resolve(ROOT, 'reporters', promptPathFor(reporter)), 'utf8');

  console.log(`E2E smoke: WF-${reporter.id} ${reporter.title}`);

  // --- Claude stage ---
  const apiKey = process.env.ANTHROPIC_API_KEY;
  let claudeResponse;
  const items = reporter.normalize(fixture.rawSource);
  const claudeBody = reporter.buildClaudeRequest({ items, prompt, model: reporter.model });
  if (args.offline || !apiKey) {
    if (!apiKey && !args.offline) {
      console.log('  [Claude] ANTHROPIC_API_KEY not set → using fixture response (offline).');
    } else {
      console.log('  [Claude] offline mode → using fixture response.');
    }
    claudeResponse = fixture.claudeResponse;
  } else {
    console.log(`  [Claude] calling live API (${reporter.model})…`);
    claudeResponse = await callClaude(apiKey, claudeBody);
    console.log('  [Claude] live response received.');
  }

  // --- Render + validate ---
  const article = reporter.parseArticle(claudeResponse);
  const payload = reporter.buildWpPayload(article, args.publish ? { } : undefined);
  if (args.publish) payload.status = 'publish';
  assertWpPayload(payload);
  console.log(`  [Render] "${payload.title}" (${payload.status}) — validated.`);

  // --- WordPress stage ---
  const username = process.env.WP_USERNAME;
  const appPassword = process.env.WP_APP_PASSWORD;
  const postsUrl = process.env.WP_POSTS_URL
    ? process.env.WP_POSTS_URL
    : process.env.WP_URL
    ? resolvePostsUrl({ wpUrl: process.env.WP_URL })
    : null;

  if (!postsUrl || !username || !appPassword) {
    console.log('\nSKIP: WordPress credentials not fully set — cannot post.');
    console.log('  Need: (WP_POSTS_URL or WP_URL), WP_USERNAME, WP_APP_PASSWORD.');
    console.log('  Offline pipeline (normalize→render→validate) succeeded; WP post skipped.');
    process.exit(0);
  }

  console.log(`  [WordPress] POST ${postsUrl} …`);
  const result = await postDraft(postsUrl, { username, appPassword }, payload);
  if (result.status !== 201) {
    console.error(`  [WordPress] FAILED: HTTP ${result.status} — ${JSON.stringify(result.body)}`);
    process.exit(1);
  }
  console.log(`  [WordPress] 201 Created — post id=${result.id}`);
  console.log('\nE2E SMOKE PASSED.');
}

main().catch((err) => {
  console.error(`E2E SMOKE ERROR: ${err.message}`);
  process.exit(1);
});
