// WF-09 Comparison reporter.
// Builds "X vs Y" articles from existing catalog entries only — every compared
// field must trace to a real catalog field (no fabricated specs).
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';

const meta = {
  id: '09',
  slug: 'comparison',
  title: '比較記者',
  category: 'ツール比較',
  model: 'claude-haiku-4-5-20251001',
  trigger: 'weekly',
};

/** @param {{tools: Array<{name: string, fields: Record<string, string>}>}} raw */
function normalize(raw) {
  if (!raw || !Array.isArray(raw.tools) || raw.tools.length < 2) {
    throw new Error('comparison: rawSource.tools must have at least 2 entries');
  }
  return raw.tools.map((t) => {
    if (!t.name || !t.fields || typeof t.fields !== 'object') {
      throw new Error('comparison: each tool needs {name, fields}');
    }
    return { name: String(t.name).trim(), fields: t.fields };
  });
}

function buildClaudeRequest({ items, prompt, model }) {
  const names = items.map((t) => t.name).join(' vs ');
  const user = `${prompt}\n\n## 比較対象（${names}）— 下記フィールドのみ使用可・捏造禁止\n${JSON.stringify(items, null, 2)}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || 'ツール比較', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    tags: opts.tags || ['比較', 'AIツール'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
