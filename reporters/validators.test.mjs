import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assertArticleHtml, assertWpPayload } from './validators.mjs';

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
  assert.ok(assertWpPayload({ title: 't', status: 'draft', content: '<h2>x</h2><p>y</p>' }));
});

test('rejects empty title', () => {
  assert.throws(() => assertWpPayload({ title: '', status: 'draft', content: '<h2>x</h2>' }), /title is empty/);
});

test('rejects unknown status', () => {
  assert.throws(() => assertWpPayload({ title: 't', status: 'trash', content: '<h2>x</h2>' }), /status must be/);
});
