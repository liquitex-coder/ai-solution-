import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NATIVE } from './registry.mjs';
import { dryRunReporter } from './dryrun.mjs';

test('every native reporter has unique id/slug and required members', () => {
  const ids = new Set();
  const slugs = new Set();
  for (const r of NATIVE) {
    assert.ok(r.id && r.slug && r.title && r.category && r.model, `${r.id} missing meta`);
    for (const fn of ['normalize', 'buildClaudeRequest', 'parseArticle', 'buildWpPayload']) {
      assert.equal(typeof r[fn], 'function', `${r.id} missing ${fn}`);
    }
    assert.ok(!ids.has(r.id), `duplicate id ${r.id}`);
    assert.ok(!slugs.has(r.slug), `duplicate slug ${r.slug}`);
    ids.add(r.id);
    slugs.add(r.slug);
  }
});

// Each native reporter must run end-to-end offline and yield a valid draft.
for (const reporter of NATIVE) {
  test(`WF-${reporter.id} ${reporter.slug} dry-run produces a valid draft`, async () => {
    const result = await dryRunReporter(reporter);
    assert.ok(result.title.length > 0, 'title present');
    assert.equal(result.payload.status, 'draft', 'safe-by-default draft');
    assert.ok(result.payload.content.startsWith('<h2'), 'article starts with h2');
  });
}

test('normalize rejects malformed input (fail-closed)', () => {
  const factcheck = NATIVE.find((r) => r.slug === 'factcheck');
  assert.throws(() => factcheck.normalize({}), /non-empty array/);
  const review = NATIVE.find((r) => r.slug === 'hands-on-review');
  assert.throws(() => review.normalize({ tool: { name: 'x' } }), /\{tool, run\}/);
});
