// Machine-enforced article + payload rules.
// Encodes n8n/prompts/article-base.md and CLAUDE.md §4 so violations fail the
// gate instead of silently shipping. Pure, dependency-free.

// Structural tags that must never appear in article body HTML.
// Exported so the n8n code generator can inline the exact same list.
export const FORBIDDEN_TAGS = ['html', 'body', 'head', 'script', 'style', 'doctype'];

// Low-confidence phrases banned by article-base.md ("使用禁止フレーズ").
export const FORBIDDEN_PHRASES = ['おそらく', 'かもしれません', 'と思われます', 'と思います'];

/**
 * Assert that a string is valid article-body HTML per article-base.md.
 * Throws Error with a specific reason on the first violation.
 * @param {string} html
 */
export function assertArticleHtml(html) {
  if (typeof html !== 'string' || html.trim().length === 0) {
    throw new Error('article html is empty');
  }
  const body = html.trim();
  if (!/^<h2[\s>]/i.test(body)) {
    throw new Error('article must start with an <h2> tag');
  }
  if (body.includes('```')) {
    throw new Error('article must not contain markdown code fences (```)');
  }
  for (const tag of FORBIDDEN_TAGS) {
    if (new RegExp(`<${tag}[\\s>/]`, 'i').test(body)) {
      throw new Error(`article must not contain a <${tag}> tag`);
    }
  }
  for (const phrase of FORBIDDEN_PHRASES) {
    if (body.includes(phrase)) {
      throw new Error(`article contains forbidden phrase: ${phrase}`);
    }
  }
  return true;
}

/**
 * Assert that a WordPress REST payload is well-formed and safe.
 * @param {{title?: unknown, content?: unknown, status?: unknown}} payload
 */
export function assertWpPayload(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('wp payload must be an object');
  }
  if (typeof payload.title !== 'string' || payload.title.trim().length === 0) {
    throw new Error('wp payload title is empty');
  }
  if (payload.status !== 'draft' && payload.status !== 'publish') {
    throw new Error(`wp payload status must be draft|publish, got: ${payload.status}`);
  }
  // Safe-by-default: anything not explicitly 'publish' must be a draft.
  assertArticleHtml(payload.content);
  return true;
}
