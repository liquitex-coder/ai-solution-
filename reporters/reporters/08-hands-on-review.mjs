// WF-08 Hands-on review reporter.
// Reviews a tool from an ACTUAL sandbox/API run — the run output is evidence
// carried into the article (CLAUDE.md §1: no claim without proof).
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';
import { categoryNameFor, categorySlugFor } from '../categories.mjs';

const meta = {
  id: '08',
  slug: 'hands-on-review',
  title: '体験レビュー記者',
  category: categoryNameFor('WF-08'),
  categorySlug: categorySlugFor('WF-08'),
  model: 'claude-sonnet-5',
  trigger: 'weekly',
};

/** @param {{tool: {name: string, url?: string}, run: {command: string, output: string, exitCode: number}}} raw */
function normalize(raw) {
  if (!raw || !raw.tool || !raw.run) {
    throw new Error('hands-on-review: rawSource must have {tool, run}');
  }
  if (typeof raw.run.exitCode !== 'number') {
    throw new Error('hands-on-review: run.exitCode (proof of execution) is required');
  }
  return [{
    tool: String(raw.tool.name).trim(),
    url: raw.tool.url || null,
    command: String(raw.run.command).trim(),
    output: String(raw.run.output),
    exitCode: raw.run.exitCode,
    succeeded: raw.run.exitCode === 0,
  }];
}

function buildClaudeRequest({ items, prompt, model }) {
  const user = `${prompt}\n\n## 実行ログ（この出力のみを根拠にレビューすること）\n${JSON.stringify(items[0], null, 2)}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || '体験レビュー', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    categorySlug: meta.categorySlug,
    tags: opts.tags || ['レビュー', 'ハンズオン'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
