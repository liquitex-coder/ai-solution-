// WF-10 Breaking-news reporter.
// Short "速報" posts detected across sources in near-real-time.
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';
import { categoryNameFor, categorySlugFor } from '../categories.mjs';

const meta = {
  id: '10',
  slug: 'breaking-news',
  title: '速報記者',
  category: categoryNameFor('WF-10'),
  categorySlug: categorySlugFor('WF-10'),
  model: 'claude-haiku-4-5-20251001',
  trigger: 'every-5-min',
};

/** @param {{events: Array<{title: string, url: string, source: string, publishedAt: string}>}} raw */
function normalize(raw) {
  if (!raw || !Array.isArray(raw.events) || raw.events.length === 0) {
    throw new Error('breaking-news: rawSource.events must be a non-empty array');
  }
  // Take the single most relevant event (a 速報 is one item, not a digest).
  const e = raw.events[0];
  if (!e.title || !e.url || !e.source) {
    throw new Error('breaking-news: event needs {title, url, source}');
  }
  return [{
    headline: String(e.title).trim(),
    url: e.url,
    source: String(e.source).trim(),
    publishedAt: e.publishedAt || null,
  }];
}

function buildClaudeRequest({ items, prompt, model }) {
  const user = `${prompt}\n\n## 速報ネタ（短報・400字以内）\n${JSON.stringify(items[0], null, 2)}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user, maxTokens: 1024 });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || '【速報】AIニュース', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    categorySlug: meta.categorySlug,
    tags: opts.tags || ['速報', 'AIニュース'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
