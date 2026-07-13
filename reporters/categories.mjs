// Single source of truth for reporter categories: data/wp-taxonomy.json.
// Reporter modules resolve their category at module-load time via this file
// so `category`/`categorySlug` end up as plain data on `meta` — never as a
// function call baked into an inlinable function body (see docs §15-11 and
// the n8n generator in scripts/gen_n8n.mjs, which relies on function source
// being self-contained).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const TAXONOMY_PATH = resolve(HERE, '../data/wp-taxonomy.json');

const taxonomy = JSON.parse(readFileSync(TAXONOMY_PATH, 'utf8'));

/** All categories as defined in data/wp-taxonomy.json. */
export const CATEGORIES = taxonomy.categories;

function findBySourceWorkflow(workflowId) {
  const entry = CATEGORIES.find((c) => c.source_workflow === workflowId);
  if (!entry) {
    throw new Error(`No category registered in data/wp-taxonomy.json for ${workflowId}`);
  }
  return entry;
}

/** Category display name for a workflow id like "WF-07". */
export function categoryNameFor(workflowId) {
  return findBySourceWorkflow(workflowId).name;
}

/** Category slug (WordPress-stable identifier) for a workflow id like "WF-07". */
export function categorySlugFor(workflowId) {
  return findBySourceWorkflow(workflowId).slug;
}
