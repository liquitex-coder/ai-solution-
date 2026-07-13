import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { NATIVE, fixturePathFor, promptPathFor } from './registry.mjs';
import { dryRunReporter } from './dryrun.mjs';
import { generateAll } from '../scripts/gen_n8n.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function nodeCode(wf, namePrefix) {
  const node = wf.nodes.find((n) => n.name.startsWith(namePrefix));
  if (!node) throw new Error(`node not found: ${namePrefix}`);
  return node.parameters.jsCode;
}

async function readJson(rel) {
  return JSON.parse(await readFile(resolve(HERE, rel), 'utf8'));
}

// (1) Freshness: on-disk JSON must equal a fresh generation. If a module
// changes without re-running gen:n8n, this fails loudly.
test('generated workflows are up to date with modules', async () => {
  const generated = await generateAll();
  for (const { reporter, wf } of generated) {
    const diskPath = `../n8n/workflows/${reporter.id}-${reporter.slug}.json`;
    const onDisk = await readJson(diskPath);
    assert.deepEqual(
      onDisk,
      wf,
      `n8n/workflows/${reporter.id}-${reporter.slug}.json is stale — run "npm run gen:n8n"`,
    );
  }
});

// (2) Execution parity: the embedded Code-node source actually runs and
// produces exactly what the tested module produces (no drift, and it runs).
for (const reporter of NATIVE) {
  test(`WF-${reporter.id} ${reporter.slug} embedded n8n code matches module`, async () => {
    const wf = await readJson(`../n8n/workflows/${reporter.id}-${reporter.slug}.json`);
    const fixture = await readJson(fixturePathFor(reporter));
    const prompt = await readFile(resolve(HERE, promptPathFor(reporter)), 'utf8');

    // Run the "build Claude request" node body exactly as n8n would.
    const reqCode = nodeCode(wf, 'リクエスト生成');
    const runReq = new Function('$json', reqCode);
    const reqOut = runReq({ rawSource: fixture.rawSource, promptContent: prompt });
    const claudeBody = reqOut[0].json.claudeBody;

    const items = reporter.normalize(fixture.rawSource);
    const expectedBody = reporter.buildClaudeRequest({ items, prompt, model: reporter.model });
    assert.deepEqual(claudeBody, expectedBody, 'Claude request body must match module output');

    // Run the "render article + WP payload" node body.
    const renderCode = nodeCode(wf, '記事生成');
    const runRender = new Function('$json', renderCode);
    const renderOut = runRender(fixture.claudeResponse);
    const payload = renderOut[0].json;

    const expected = await dryRunReporter(reporter);
    assert.deepEqual(payload, expected.payload, 'WP payload must match module dry-run');
    assert.equal(payload.status, 'draft', 'safe-by-default draft');
  });
}
