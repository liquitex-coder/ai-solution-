#!/usr/bin/env node
// Quality regression gate (docs/requirements.md §18-6).
// Scores every native reporter's dry-run output with the deterministic rubric
// (reporters/quality.mjs) and compares each against a frozen baseline. A prompt
// or reporter change that LOWERS any reporter's score fails the gate (exit 1),
// so quality can only hold or improve — never silently regress.
//
//   node scripts/check_quality_baseline.mjs                 # compare (default)
//   node scripts/check_quality_baseline.mjs --update-baseline
//
// The baseline is intentionally raised only on purpose (like check_test_count).
import { readFile, writeFile, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { NATIVE } from '../reporters/registry.mjs';
import { dryRunReporter } from '../reporters/dryrun.mjs';
import { scoreArticle, MAX_SCORE } from '../reporters/quality.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BASELINE_PATH = resolve(ROOT, 'reporters/quality-baseline.json');

async function exists(p) {
  try { await access(p); return true; } catch { return false; }
}

/** Score all native reporters. @returns {Promise<Record<string,{score:number,max:number}>>} */
async function scoreFleet() {
  const out = {};
  for (const reporter of NATIVE) {
    const { payload } = await dryRunReporter(reporter);
    const { score } = scoreArticle(payload);
    out[reporter.id] = { score, max: MAX_SCORE };
  }
  return out;
}

async function updateBaseline() {
  const scores = await scoreFleet();
  const baseline = { max: MAX_SCORE, reporters: scores };
  await writeFile(BASELINE_PATH, JSON.stringify(baseline, null, 2) + '\n', 'utf8');
  console.log(`Baseline written: reporters/quality-baseline.json (max ${MAX_SCORE})`);
  for (const id of Object.keys(scores).sort()) {
    console.log(`  WF-${id}: ${scores[id].score}/${MAX_SCORE}`);
  }
}

async function compare() {
  if (!(await exists(BASELINE_PATH))) {
    console.error('No baseline found. Run: node scripts/check_quality_baseline.mjs --update-baseline');
    process.exit(1);
  }
  const baseline = JSON.parse(await readFile(BASELINE_PATH, 'utf8'));
  const current = await scoreFleet();

  console.log('== Quality regression gate ==');
  let regressed = 0;
  let missing = 0;
  for (const reporter of NATIVE) {
    const id = reporter.id;
    const now = current[id].score;
    const base = baseline.reporters?.[id]?.score;
    if (base === undefined) {
      missing++;
      console.log(`  ⚠️  WF-${id} ${reporter.slug}: ${now}/${MAX_SCORE} — no baseline (run --update-baseline)`);
      continue;
    }
    if (now < base) {
      regressed++;
      console.log(`  ❌ WF-${id} ${reporter.slug}: ${now}/${MAX_SCORE} < baseline ${base} (regressed by ${base - now})`);
    } else if (now > base) {
      console.log(`  ⬆️  WF-${id} ${reporter.slug}: ${now}/${MAX_SCORE} > baseline ${base} (improved; raise baseline to lock in)`);
    } else {
      console.log(`  ✅ WF-${id} ${reporter.slug}: ${now}/${MAX_SCORE}`);
    }
  }

  if (regressed > 0 || missing > 0) {
    console.error(`\nGATE FAILED: ${regressed} regressed, ${missing} without baseline.`);
    process.exit(1);
  }
  console.log(`\nGATE PASSED: no reporter scored below baseline (${NATIVE.length} checked).`);
}

async function main() {
  if (process.argv.includes('--update-baseline')) await updateBaseline();
  else await compare();
}

main();
