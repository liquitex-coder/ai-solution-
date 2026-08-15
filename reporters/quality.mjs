// Deterministic article quality rubric (docs/requirements.md §18-5).
// Pure, dependency-free, NO LLM: the score is what the quality regression gate
// (scripts/check_quality_baseline.mjs) compares against a frozen baseline, so
// it must be reproducible without a model (mirrors INV-R2: verdict is
// deterministic, LLM is a proposer only).
//
// scoreArticle() grades a WordPress payload the reporter would ship. Unlike
// validators.mjs (which throws on the first hard violation and gates publish),
// this produces a graded 0..100 score across dimensions so improvements and
// regressions are measurable, not just pass/fail.
import { FORBIDDEN_TAGS, FORBIDDEN_PHRASES } from './validators.mjs';

// Strip HTML tags to get the visible text length (rough, deterministic).
function textOf(html) {
  return String(html || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// Each dimension returns points in [0, max]. Sum of maxes is 100.
// Weights encode n8n/prompts/article-base.md priorities (structure first,
// no forbidden phrases, SEO depth, evidence, non-trivial length).
const DIMENSIONS = [
  {
    key: 'structure',
    max: 40,
    score(html) {
      let p = 0;
      const detail = [];
      if (/^<h2[\s>]/i.test(html.trim())) p += 20;
      else detail.push('does not start with <h2>');
      const hasForbiddenTag = FORBIDDEN_TAGS.some((t) => new RegExp(`<${t}[\\s>/]`, 'i').test(html));
      if (!hasForbiddenTag) p += 10;
      else detail.push('contains a forbidden structural tag');
      if (!html.includes('```')) p += 10;
      else detail.push('contains markdown code fences');
      return { points: p, detail: detail.join('; ') };
    },
  },
  {
    key: 'forbidden_phrases',
    max: 20,
    score(html) {
      const hit = FORBIDDEN_PHRASES.find((ph) => html.includes(ph));
      return hit
        ? { points: 0, detail: `forbidden phrase: ${hit}` }
        : { points: 20, detail: '' };
    },
  },
  {
    key: 'subheadings',
    max: 15,
    score(html) {
      // article-base.md: H2 headings carry keywords; sub-structure (<h3>) helps
      // scannability and SEO depth.
      return /<h3[\s>]/i.test(html)
        ? { points: 15, detail: '' }
        : { points: 0, detail: 'no <h3> subheadings' };
    },
  },
  {
    key: 'evidence',
    max: 15,
    score(html) {
      // Evidence-first (INV DNA): a source link or a structured comparison
      // table is the minimum machine-checkable evidence signal.
      const hasLink = /<a\s[^>]*href=/i.test(html);
      const hasTable = /<table[\s>]/i.test(html);
      if (hasLink || hasTable) return { points: 15, detail: '' };
      return { points: 0, detail: 'no source link or comparison table' };
    },
  },
  {
    key: 'length',
    max: 10,
    score(html) {
      // article-base.md SEO target: 800–2000 chars. Graded so short demo
      // fixtures still register a floor without claiming full marks.
      const len = textOf(html).length;
      if (len >= 800) return { points: 10, detail: `${len} chars` };
      if (len >= 300) return { points: 6, detail: `${len} chars (below 800 target)` };
      return { points: 0, detail: `${len} chars (too short)` };
    },
  },
];

export const MAX_SCORE = DIMENSIONS.reduce((s, d) => s + d.max, 0);

/**
 * Score an article's WordPress payload deterministically.
 * @param {{content?: string, title?: string}} payload
 * @returns {{score: number, max: number, dimensions: Array<{key: string, points: number, max: number, detail: string}>}}
 */
export function scoreArticle(payload) {
  if (!payload || typeof payload.content !== 'string') {
    throw new Error('scoreArticle: payload.content (article html) is required');
  }
  const html = payload.content;
  const dimensions = DIMENSIONS.map((d) => {
    const { points, detail } = d.score(html);
    return { key: d.key, points, max: d.max, detail };
  });
  const score = dimensions.reduce((s, d) => s + d.points, 0);
  return { score, max: MAX_SCORE, dimensions };
}
