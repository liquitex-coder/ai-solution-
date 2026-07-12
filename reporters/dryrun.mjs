// Offline dry-run: exercises a reporter end-to-end using its fixture, with NO
// network and NO API keys. This is the proof a reporter actually runs.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { assertWpPayload } from './validators.mjs';
import { fixturePathFor, promptPathFor } from './registry.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

async function loadJson(relPath) {
  const abs = resolve(HERE, relPath);
  return JSON.parse(await readFile(abs, 'utf8'));
}

async function loadText(relPath) {
  return readFile(resolve(HERE, relPath), 'utf8');
}

/**
 * Run one native reporter through normalize → buildClaudeRequest →
 * parseArticle → buildWpPayload using its fixture. Throws on any failure.
 * @returns {Promise<{id: string, slug: string, itemCount: number, requestModel: string, title: string, payload: object}>}
 */
export async function dryRunReporter(reporter) {
  const fixture = await loadJson(fixturePathFor(reporter));
  const prompt = await loadText(promptPathFor(reporter));

  const items = reporter.normalize(fixture.rawSource);
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error(`${reporter.id}: normalize produced no items`);
  }

  const request = reporter.buildClaudeRequest({ items, prompt, model: reporter.model });
  if (!request || !Array.isArray(request.messages) || request.messages.length === 0) {
    throw new Error(`${reporter.id}: buildClaudeRequest produced no messages`);
  }
  if (!request.messages[0].content || !request.messages[0].content.includes(prompt.slice(0, 20))) {
    throw new Error(`${reporter.id}: prompt not injected into Claude request`);
  }

  const article = reporter.parseArticle(fixture.claudeResponse);
  if (!article || !article.html) {
    throw new Error(`${reporter.id}: parseArticle produced no html`);
  }

  const payload = reporter.buildWpPayload(article);
  assertWpPayload(payload); // enforces article-base.md rules + safe-by-default

  return {
    id: reporter.id,
    slug: reporter.slug,
    itemCount: items.length,
    requestModel: request.model,
    title: payload.title,
    payload,
  };
}
