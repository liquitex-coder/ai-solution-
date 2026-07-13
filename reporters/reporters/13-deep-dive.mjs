// WF-13 Deep-dive reporter (SEO pillar content).
// Long-form explainer that weaves in internal links to existing articles.
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';

const meta = {
  id: '13',
  slug: 'deep-dive',
  title: '深掘り解説記者',
  category: '深掘り解説',
  model: 'claude-sonnet-5',
  trigger: 'weekly',
};

/** @param {{topic: string, internalLinks?: Array<{title: string, url: string}>, sources?: string[]}} raw */
function normalize(raw) {
  if (!raw || !raw.topic || String(raw.topic).trim().length === 0) {
    throw new Error('deep-dive: rawSource.topic is required');
  }
  const links = Array.isArray(raw.internalLinks) ? raw.internalLinks : [];
  return [{
    topic: String(raw.topic).trim(),
    internalLinks: links.filter((l) => l && l.title && l.url),
    sources: Array.isArray(raw.sources) ? raw.sources : [],
  }];
}

function buildClaudeRequest({ items, prompt, model }) {
  const it = items[0];
  const user = `${prompt}\n\n## トピック\n${it.topic}\n\n## 内部リンク候補（本文に自然に挿入）\n${JSON.stringify(it.internalLinks, null, 2)}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user, maxTokens: 4096 });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || '深掘り解説', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    tags: opts.tags || ['解説', 'まとめ'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
