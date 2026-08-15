// Shared helpers for reporter modules.
// Pure functions only — NO network, NO API keys, NO n8n. This is what makes
// every reporter runnable offline (see docs/requirements.md §15).

/**
 * Extract the concatenated text from an Anthropic Messages API response.
 * @param {{content?: Array<{type: string, text?: string}>}} claudeResponse
 * @returns {string}
 */
export function extractText(claudeResponse) {
  if (!claudeResponse || !Array.isArray(claudeResponse.content)) {
    throw new Error('claudeResponse.content must be an array');
  }
  return claudeResponse.content
    .filter((block) => block && block.type === 'text' && typeof block.text === 'string')
    .map((block) => block.text)
    .join('')
    .trim();
}

/**
 * Derive an article title from the first <h2> heading in the HTML body.
 * article-base.md requires every article to start with <h2>, so this is
 * always present in a valid article.
 * @param {string} html
 * @returns {string}
 */
export function titleFromH2(html) {
  const match = /<h2[^>]*>([\s\S]*?)<\/h2>/i.exec(html || '');
  if (!match) return '';
  return match[1].replace(/<[^>]+>/g, '').trim();
}

/**
 * Build an Anthropic Messages API request body (no transport, no key).
 * @param {{model: string, system: string, user: string, maxTokens?: number}} opts
 */
export function baseClaudeRequest({ model, system, user, maxTokens = 2048 }) {
  if (!model) throw new Error('model is required');
  if (!user) throw new Error('user content is required');
  return {
    model,
    max_tokens: maxTokens,
    system: system || '',
    messages: [{ role: 'user', content: user }],
  };
}

/**
 * Build a WordPress REST payload. Default status is 'draft' — a reporter must
 * opt in explicitly to publish (INV: safe by default).
 * categorySlug is the WordPress-stable identifier wp_client.mjs resolves to a
 * category id before posting; categoryName is carried for readability/tests.
 * @param {{title: string, html: string, category?: string, categorySlug?: string, tags?: string[], status?: string, reporterId?: string}} opts
 */
export function baseWpPayload({ title, html, category, categorySlug, tags = [], status = 'draft', reporterId, disclosure = 'none', revenueLinks = [] }) {
  return {
    title,
    content: html,
    status,
    categoryName: category || null,
    categorySlug: categorySlug || null,
    tagNames: tags,
    // disclosure/revenue_links feed the §16-4 gate (assertDisclosure); every
    // aggregation reporter defaults to 'none' — a monetized article must opt in.
    meta: {
      generated_by: 'ai-reporter',
      reporter_id: reporterId || null,
      disclosure,
      revenue_links: revenueLinks,
    },
  };
}
