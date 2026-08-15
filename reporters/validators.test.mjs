import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assertArticleHtml, assertDisclosure, assertWpPayload, DISCLOSURE_NOTICES } from './validators.mjs';

test('valid article passes', () => {
  assert.ok(assertArticleHtml('<h2>タイトル</h2><p>本文です。</p>'));
});

test('rejects empty html', () => {
  assert.throws(() => assertArticleHtml(''), /empty/);
});

test('rejects article not starting with h2', () => {
  assert.throws(() => assertArticleHtml('<p>本文</p>'), /start with an <h2>/);
});

test('rejects code fences', () => {
  assert.throws(() => assertArticleHtml('<h2>x</h2>```js```'), /code fences/);
});

test('rejects forbidden structural tags', () => {
  assert.throws(() => assertArticleHtml('<h2>x</h2><body>y</body>'), /<body>/);
});

test('rejects forbidden phrases', () => {
  assert.throws(() => assertArticleHtml('<h2>x</h2><p>おそらく動きます</p>'), /forbidden phrase/);
});

test('valid draft payload passes', () => {
  assert.ok(assertWpPayload({
    title: 't', status: 'draft', content: '<h2>x</h2><p>y</p>',
    meta: { disclosure: 'none' },
  }));
});

test('payload without a disclosure declaration is rejected (G1)', () => {
  assert.throws(
    () => assertWpPayload({ title: 't', status: 'draft', content: '<h2>x</h2><p>y</p>' }),
    /disclosure must be one of/,
  );
});

test('rejects empty title', () => {
  assert.throws(() => assertWpPayload({ title: '', status: 'draft', content: '<h2>x</h2>' }), /title is empty/);
});

test('rejects unknown status', () => {
  assert.throws(() => assertWpPayload({ title: 't', status: 'trash', content: '<h2>x</h2>' }), /status must be/);
});

// ---- Disclosure gate (docs/requirements.md §16-4 G1–G3) ---------------------

const AFF_URL = 'https://example.com/tool?aff=123';
const AFF_LINK_OK = `<a href="${AFF_URL}" rel="sponsored nofollow">ツールを見る</a>`;

function affiliateBody({ notice = true, link = AFF_LINK_OK } = {}) {
  const head = notice ? `<p>${DISCLOSURE_NOTICES.affiliate}</p>` : '<p>ご案内。</p>';
  return `<h2>タイトル</h2>${head}<p>本文です。</p>${link}`;
}

test('affiliate article with notice and attributed link passes (G1-G3)', () => {
  assert.ok(assertDisclosure({
    content: affiliateBody(),
    meta: { disclosure: 'affiliate', revenue_links: [AFF_URL] },
  }));
});

test('disclosure none forbids revenue links (undeclared monetization)', () => {
  assert.throws(
    () => assertDisclosure({ content: '<h2>x</h2>', meta: { disclosure: 'none', revenue_links: [AFF_URL] } }),
    /undeclared monetization/,
  );
});

test('affiliate without the opening notice is rejected (G2)', () => {
  assert.throws(
    () => assertDisclosure({
      content: affiliateBody({ notice: false }),
      meta: { disclosure: 'affiliate', revenue_links: [AFF_URL] },
    }),
    /opening notice/,
  );
});

test('affiliate with notice but no revenue_links is rejected (fail-closed)', () => {
  assert.throws(
    () => assertDisclosure({ content: affiliateBody(), meta: { disclosure: 'affiliate' } }),
    /non-empty meta\.revenue_links/,
  );
});

test('declared revenue link missing from the body is rejected', () => {
  assert.throws(
    () => assertDisclosure({
      content: affiliateBody({ link: '' }),
      meta: { disclosure: 'affiliate', revenue_links: [AFF_URL] },
    }),
    /not present as an <a> tag/,
  );
});

test('revenue link without rel="sponsored nofollow" is rejected (G3)', () => {
  assert.throws(
    () => assertDisclosure({
      content: affiliateBody({ link: `<a href="${AFF_URL}">ツールを見る</a>` }),
      meta: { disclosure: 'affiliate', revenue_links: [AFF_URL] },
    }),
    /rel="sponsored nofollow"/,
  );
});
