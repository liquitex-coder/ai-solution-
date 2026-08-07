import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { scoreArticle, MAX_SCORE } from './quality.mjs';
import { NATIVE } from './registry.mjs';
import { dryRunReporter } from './dryrun.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

const GOOD = {
  content:
    '<h2>Claude と ChatGPT はどう違う？ 3つの観点で比較</h2>' +
    '<p>公開情報をもとに比較します。</p>' +
    '<h3>比較表</h3>' +
    '<table><tr><th>項目</th><th>Claude</th></tr><tr><td>料金</td><td>無料枠あり</td></tr></table>' +
    '<h3>参考</h3><p><a href="https://example.com">公式ドキュメント</a>を参照してください。</p>' +
    '<p>' + 'これは本文の続きです。'.repeat(80) + '</p>',
};

test('a well-formed evidence-rich article scores near max', () => {
  const { score, max, dimensions } = scoreArticle(GOOD);
  assert.equal(max, MAX_SCORE);
  assert.equal(score, MAX_SCORE, `dims: ${JSON.stringify(dimensions)}`);
});

test('score has one entry per dimension and points never exceed max', () => {
  const { dimensions } = scoreArticle(GOOD);
  assert.equal(dimensions.length, 5);
  for (const d of dimensions) assert.ok(d.points >= 0 && d.points <= d.max, `${d.key} out of range`);
});

test('a forbidden phrase zeroes the forbidden_phrases dimension', () => {
  const bad = { content: GOOD.content.replace('比較します。', 'おそらく比較できます。') };
  const dim = scoreArticle(bad).dimensions.find((d) => d.key === 'forbidden_phrases');
  assert.equal(dim.points, 0);
  assert.ok(scoreArticle(bad).score < scoreArticle(GOOD).score, 'bad article scores lower');
});

test('not starting with <h2> loses structure points', () => {
  const bad = { content: '<p>いきなり本文</p>' + GOOD.content };
  const dim = scoreArticle(bad).dimensions.find((d) => d.key === 'structure');
  assert.ok(dim.points < 40, 'structure penalized when h2 is not first');
});

test('markdown code fences lose structure points', () => {
  const bad = { content: GOOD.content + '```js\nconsole.log(1)\n```' };
  const dim = scoreArticle(bad).dimensions.find((d) => d.key === 'structure');
  assert.ok(dim.points <= 30, 'code fences penalized');
});

test('missing content throws (fail-closed)', () => {
  assert.throws(() => scoreArticle({}), /content .* required/);
});

// Regression guard inside node --test: every native reporter must still meet
// its frozen baseline. Mirrors scripts/check_quality_baseline.mjs so CI catches
// a regression even via the unit-test step alone.
test('every native reporter meets its quality baseline', async () => {
  const baseline = JSON.parse(await readFile(resolve(HERE, 'quality-baseline.json'), 'utf8'));
  for (const reporter of NATIVE) {
    const { payload } = await dryRunReporter(reporter);
    const { score } = scoreArticle(payload);
    const base = baseline.reporters?.[reporter.id]?.score;
    assert.notEqual(base, undefined, `WF-${reporter.id} has no baseline entry`);
    assert.ok(score >= base, `WF-${reporter.id} regressed: ${score} < baseline ${base}`);
  }
});
