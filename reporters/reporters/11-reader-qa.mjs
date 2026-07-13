// WF-11 Reader Q&A reporter.
// Turns a reader-submitted question (UGC) into an answer article.
import { extractText, titleFromH2, baseClaudeRequest, baseWpPayload } from '../core.mjs';
import { categoryNameFor, categorySlugFor } from '../categories.mjs';

const meta = {
  id: '11',
  slug: 'reader-qa',
  title: '読者Q&A記者',
  category: categoryNameFor('WF-11'),
  categorySlug: categorySlugFor('WF-11'),
  model: 'claude-haiku-4-5-20251001',
  trigger: 'on-submit',
};

/** @param {{question: {text: string, author?: string}}} raw */
function normalize(raw) {
  if (!raw || !raw.question || !raw.question.text) {
    throw new Error('reader-qa: rawSource.question.text is required');
  }
  const text = String(raw.question.text).trim();
  if (text.length < 5) {
    throw new Error('reader-qa: question is too short to answer');
  }
  return [{ question: text, author: raw.question.author || '匿名' }];
}

function buildClaudeRequest({ items, prompt, model }) {
  const user = `${prompt}\n\n## 読者からの質問\n${items[0].question}`;
  return baseClaudeRequest({ model: model || meta.model, system: prompt, user });
}

function parseArticle(claudeResponse) {
  const html = extractText(claudeResponse);
  return { title: titleFromH2(html) || '読者からの質問に回答', html };
}

function buildWpPayload(article, opts = {}) {
  return baseWpPayload({
    title: article.title,
    html: article.html,
    category: meta.category,
    categorySlug: meta.categorySlug,
    tags: opts.tags || ['Q&A', '初心者'],
    reporterId: meta.id,
  });
}

export default { ...meta, normalize, buildClaudeRequest, parseArticle, buildWpPayload };
