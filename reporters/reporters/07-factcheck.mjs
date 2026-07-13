// WF-07 Fact-check reporter.
// Extracts hype claims and reports a verdict. The verdict itself is intended to
// come from Claim-Auditor's LLM-free engine (INV-R2); the LLM only drafts prose.
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';
import { categoryNameFor, categorySlugFor } from '../categories.mjs';

const meta = {
  id: '07',
  slug: 'factcheck',
  title: 'ファクトチェック記者',
  category: categoryNameFor('WF-07'),
  categorySlug: categorySlugFor('WF-07'),
  model: 'claude-sonnet-5',
  trigger: 'daily',
};

/** @param {{claims: Array<{text: string, source: string, url?: string, verdict?: string, evidence?: string}>}} raw */
function normalize(raw) {
  if (!raw || !Array.isArray(raw.claims) || raw.claims.length === 0) {
    throw new Error('factcheck: rawSource.claims must be a non-empty array');
  }
  return raw.claims.map((c) => ({
    claim: String(c.text).trim(),
    source: String(c.source).trim(),
    url: c.url || null,
    verdict: c.verdict || 'UNVERIFIED', // supplied by Claim-Auditor upstream
    evidence: c.evidence || '',
  }));
}

function buildClaudeRequest({ items, prompt, model }) {
  const user = `${prompt}\n\n## 検証対象クレーム（判定は確定済み・改変禁止）\n${JSON.stringify(items, null, 2)}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || 'ファクトチェック', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    categorySlug: meta.categorySlug,
    tags: opts.tags || ['ファクトチェック', '検証'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
