// WF-12 Changelog tracker reporter.
// Monitors release notes of major tools and explains "what changed and why".
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';

const meta = {
  id: '12',
  slug: 'changelog-tracker',
  title: 'アップデート追跡記者',
  category: 'アップデート',
  model: 'claude-haiku-4-5-20251001',
  trigger: 'daily',
};

/** @param {{release: {tool: string, version: string, notes: string, url?: string}}} raw */
function normalize(raw) {
  if (!raw || !raw.release) {
    throw new Error('changelog-tracker: rawSource.release is required');
  }
  const r = raw.release;
  if (!r.tool || !r.version || !r.notes) {
    throw new Error('changelog-tracker: release needs {tool, version, notes}');
  }
  return [{
    tool: String(r.tool).trim(),
    version: String(r.version).trim(),
    notes: String(r.notes).trim(),
    url: r.url || null,
  }];
}

function buildClaudeRequest({ items, prompt, model }) {
  const r = items[0];
  const user = `${prompt}\n\n## リリースノート（${r.tool} ${r.version}）\n${r.notes}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || 'アップデート情報', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    tags: opts.tags || ['アップデート', 'リリース'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
