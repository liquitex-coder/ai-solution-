// Machine-enforced article + payload rules.
// Encodes n8n/prompts/article-base.md and CLAUDE.md §4 so violations fail the
// gate instead of silently shipping. Pure, dependency-free.

// Structural tags that must never appear in article body HTML.
// Exported so the n8n code generator can inline the exact same list.
export const FORBIDDEN_TAGS = ['html', 'body', 'head', 'script', 'style', 'doctype'];

// Low-confidence phrases banned by article-base.md ("使用禁止フレーズ").
export const FORBIDDEN_PHRASES = ['おそらく', 'かもしれません', 'と思われます', 'と思います'];

// Disclosure kinds a payload may declare (docs/requirements.md §16-4 G1).
export const DISCLOSURE_KINDS = ['none', 'affiliate', 'sponsored', 'ad'];

// Mandatory opening notice per revenue kind (§16-4 G2, ステマ規制/景表法).
// The notice must appear near the top of the article body.
export const DISCLOSURE_NOTICES = {
  affiliate: '本記事にはアフィリエイトリンクを含みます',
  sponsored: '本記事はスポンサーの提供でお届けします',
  ad: '本記事には広告を含みます',
};

// How far into the body the notice must appear to count as "冒頭" (§16-4 G2).
export const DISCLOSURE_HEAD_WINDOW = 400;

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
 * Disclosure / conflict-of-interest gate (docs/requirements.md §16-4 G1–G3).
 * Fail-closed: an article that monetizes without declaring it — or declares it
 * without the mandatory opening notice and properly-attributed links — must
 * never reach WordPress.
 *
 * Contract (carried in payload.meta):
 * - `meta.disclosure` ∈ DISCLOSURE_KINDS is REQUIRED (G1).
 * - disclosure !== 'none' requires the matching DISCLOSURE_NOTICES text within
 *   the first DISCLOSURE_HEAD_WINDOW chars of the body (G2), and a non-empty
 *   `meta.revenue_links` list where every URL appears in the body as an <a>
 *   tag carrying rel with both "sponsored" and "nofollow" (G3).
 * - disclosure === 'none' forbids `meta.revenue_links` (undeclared monetization).
 * @param {{content?: string, meta?: {disclosure?: string, revenue_links?: string[]}}} payload
 */
export function assertDisclosure(payload) {
  const meta = payload.meta || {};
  const disclosure = meta.disclosure;
  if (!DISCLOSURE_KINDS.includes(disclosure)) {
    throw new Error(`meta.disclosure must be one of ${DISCLOSURE_KINDS.join('|')}, got: ${disclosure}`);
  }
  const links = Array.isArray(meta.revenue_links) ? meta.revenue_links : [];
  if (disclosure === 'none') {
    if (links.length > 0) {
      throw new Error('meta.revenue_links present but disclosure is "none" — undeclared monetization');
    }
    return true;
  }
  const body = String(payload.content || '');
  const notice = DISCLOSURE_NOTICES[disclosure];
  if (!body.slice(0, DISCLOSURE_HEAD_WINDOW).includes(notice)) {
    throw new Error(`disclosure "${disclosure}" requires the opening notice "${notice}" within the first ${DISCLOSURE_HEAD_WINDOW} chars`);
  }
  if (links.length === 0) {
    throw new Error(`disclosure "${disclosure}" requires a non-empty meta.revenue_links list`);
  }
  const allAnchors = body.match(/<a\s[^>]*>/gi) || [];
  for (const url of links) {
    const anchors = allAnchors.filter((a) => a.includes(`href="${url}"`));
    if (anchors.length === 0) {
      throw new Error(`revenue link ${url} is declared but not present as an <a> tag in the body`);
    }
    for (const a of anchors) {
      const rel = /rel="([^"]*)"/i.exec(a);
      const relVal = rel ? rel[1] : '';
      if (!/\bsponsored\b/.test(relVal) || !/\bnofollow\b/.test(relVal)) {
        throw new Error(`revenue link ${url} must carry rel="sponsored nofollow" (G3), got: ${relVal || '(no rel)'}`);
      }
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
  // Monetization must be declared and properly attributed (§16-4 G1–G3).
  assertDisclosure(payload);
  return true;
}
