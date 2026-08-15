#!/usr/bin/env node
// No-Dead-Reporter gate (docs/requirements.md §15-6).
// Exits non-zero if ANY registered reporter is not fully witnessed, making it
// impossible to merge a reporter that has never been proven to run.
import { readFile, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { NATIVE, LEGACY, promptPathFor, fixturePathFor } from '../reporters/registry.mjs';
import { dryRunReporter } from '../reporters/dryrun.mjs';
import { CATEGORIES } from '../reporters/categories.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

async function exists(absPath) {
  try {
    await access(absPath);
    return true;
  } catch {
    return false;
  }
}

async function checkNative(reporter) {
  const errors = [];
  const promptAbs = resolve(ROOT, 'reporters', promptPathFor(reporter));
  const fixtureAbs = resolve(ROOT, 'reporters', fixturePathFor(reporter));
  if (!(await exists(promptAbs))) errors.push(`missing prompt: ${promptPathFor(reporter)}`);
  if (!(await exists(fixtureAbs))) errors.push(`missing fixture: ${fixturePathFor(reporter)}`);
  if (errors.length === 0) {
    try {
      await dryRunReporter(reporter); // full offline run + payload validation
    } catch (err) {
      errors.push(`dry-run failed: ${err.message}`);
    }
  }
  return errors;
}

async function checkLegacy(entry) {
  const errors = [];
  const wfAbs = resolve(ROOT, 'n8n/workflows', entry.workflow);
  const promptAbs = resolve(ROOT, 'n8n/prompts', entry.prompt);
  if (!(await exists(promptAbs))) errors.push(`missing prompt: n8n/prompts/${entry.prompt}`);
  if (!(await exists(wfAbs))) {
    errors.push(`missing workflow: n8n/workflows/${entry.workflow}`);
    return errors;
  }
  let wf;
  try {
    wf = JSON.parse(await readFile(wfAbs, 'utf8'));
  } catch (err) {
    errors.push(`workflow JSON parse error: ${err.message}`);
    return errors;
  }
  const nodes = Array.isArray(wf.nodes) ? wf.nodes : [];
  const httpNodes = nodes.filter((n) => n.type === 'n8n-nodes-base.httpRequest');
  const blob = JSON.stringify(wf).toLowerCase();
  if (httpNodes.length < 2) errors.push('expected >=2 httpRequest nodes (source/Claude/WP)');
  if (!blob.includes('anthropic')) errors.push('no Claude/Anthropic call found in workflow');
  if (!blob.includes('wp-json') && !blob.includes('wp/v2')) errors.push('no WordPress REST call found in workflow');
  return errors;
}

// Category consistency gate (docs §15-11): data/wp-taxonomy.json must map
// 1:1 onto the registered reporters — no unused placeholders, no duplicates,
// no reporter left without a real WordPress category to post into.
function checkCategories() {
  const errors = [];
  const allWorkflowIds = [
    ...NATIVE.map((r) => `WF-${r.id}`),
    ...LEGACY.map((entry) => `WF-${entry.id}`),
  ];

  const bySourceWorkflow = new Map();
  for (const c of CATEGORIES) {
    if (c.source_workflow == null) {
      errors.push(`unused category placeholder: "${c.name}" (${c.slug}) — assign it to a reporter or remove it`);
      continue;
    }
    if (bySourceWorkflow.has(c.source_workflow)) {
      errors.push(
        `duplicate category for ${c.source_workflow}: "${bySourceWorkflow.get(c.source_workflow)}" and "${c.name}"`,
      );
      continue;
    }
    bySourceWorkflow.set(c.source_workflow, c.name);
  }

  for (const id of allWorkflowIds) {
    if (!bySourceWorkflow.has(id)) {
      errors.push(`missing category in data/wp-taxonomy.json for ${id}`);
    }
  }

  for (const reporter of NATIVE) {
    const wfId = `WF-${reporter.id}`;
    const expected = bySourceWorkflow.get(wfId);
    if (expected && reporter.category !== expected) {
      errors.push(`${wfId} reporter.category="${reporter.category}" does not match taxonomy "${expected}"`);
    }
  }

  return errors;
}

async function main() {
  let failed = 0;
  console.log('== No-Dead-Reporter gate ==');

  console.log('\nCategory consistency (data/wp-taxonomy.json ↔ reporters):');
  const categoryErrors = checkCategories();
  let categoryGateFailed = false;
  if (categoryErrors.length === 0) {
    console.log(`  ✅ ${CATEGORIES.length} categories, 1:1 with all reporters, no unused placeholders`);
  } else {
    categoryGateFailed = true;
    console.log('  ❌ category mismatch');
    categoryErrors.forEach((e) => console.log(`       - ${e}`));
  }

  console.log(`\nNative reporters (full offline dry-run): ${NATIVE.length}`);
  for (const reporter of NATIVE) {
    const errors = await checkNative(reporter);
    if (errors.length === 0) {
      console.log(`  ✅ WF-${reporter.id} ${reporter.slug}`);
    } else {
      failed++;
      console.log(`  ❌ WF-${reporter.id} ${reporter.slug}`);
      errors.forEach((e) => console.log(`       - ${e}`));
    }
  }

  console.log(`\nLegacy reporters (n8n JSON structure): ${LEGACY.length}`);
  for (const entry of LEGACY) {
    const errors = await checkLegacy(entry);
    if (errors.length === 0) {
      console.log(`  ✅ WF-${entry.id} ${entry.slug}`);
    } else {
      failed++;
      console.log(`  ❌ WF-${entry.id} ${entry.slug}`);
      errors.forEach((e) => console.log(`       - ${e}`));
    }
  }

  const total = NATIVE.length + LEGACY.length;
  console.log(`\n${total - failed}/${total} reporters witnessed.`);
  if (failed > 0 || categoryGateFailed) {
    const parts = [];
    if (failed > 0) parts.push(`${failed} reporter(s) not runnable/witnessed`);
    if (categoryGateFailed) parts.push('category consistency violated');
    console.error(`GATE FAILED: ${parts.join('; ')}.`);
    process.exit(1);
  }
  console.log('GATE PASSED: every registered reporter is witnessed and categories are consistent.');
}

main();
