#!/usr/bin/env node
// CLI dry-run harness. Prints the WP draft payload a reporter would produce,
// entirely offline. Usage:
//   node reporters/run.mjs                 # dry-run all native reporters
//   node reporters/run.mjs --id 07         # dry-run a single reporter
//   node reporters/run.mjs --id 09 --json  # print the full WP payload as JSON
import { NATIVE } from './registry.mjs';
import { dryRunReporter } from './dryrun.mjs';

function parseArgs(argv) {
  const args = { id: null, json: false };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--id') args.id = argv[++i];
    else if (argv[i] === '--json') args.json = true;
  }
  return args;
}

async function main() {
  const { id, json } = parseArgs(process.argv);
  const targets = id ? NATIVE.filter((r) => r.id === id) : NATIVE;
  if (targets.length === 0) {
    console.error(`No native reporter with id=${id}`);
    process.exit(2);
  }

  let failures = 0;
  for (const reporter of targets) {
    try {
      const result = await dryRunReporter(reporter);
      console.log(`✅ WF-${result.id} ${reporter.title} → "${result.title}" (${result.requestModel}, ${result.itemCount} item(s))`);
      if (json) console.log(JSON.stringify(result.payload, null, 2));
    } catch (err) {
      failures++;
      console.error(`❌ WF-${reporter.id} ${reporter.title} — ${err.message}`);
    }
  }
  process.exit(failures === 0 ? 0 : 1);
}

main();
