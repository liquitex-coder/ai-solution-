// Single source of truth for the reporter fleet.
// The gate (scripts/check_reporters.mjs) walks this registry and refuses to
// pass if any entry lacks its witness (see docs/requirements.md §15-6).
import r07 from './reporters/07-factcheck.mjs';
import r08 from './reporters/08-hands-on-review.mjs';
import r09 from './reporters/09-comparison.mjs';
import r10 from './reporters/10-breaking-news.mjs';
import r11 from './reporters/11-reader-qa.mjs';
import r12 from './reporters/12-changelog-tracker.mjs';
import r13 from './reporters/13-deep-dive.mjs';

// Native reporters: testable modules that must pass a full offline dry-run.
export const NATIVE = [r07, r08, r09, r10, r11, r12, r13];

// Legacy reporters: still n8n-JSON only. The gate checks their JSON structure
// and prompt file until they are ported onto the module contract.
export const LEGACY = [
  { id: '01', slug: 'github-trending', workflow: '01-github-ai-trending-daily.json', prompt: '01-github-trending.md' },
  { id: '02', slug: 'rss-monitor', workflow: '02-rss-monitor.json', prompt: '02-rss-monitor.md' },
  { id: '03', slug: 'youtube-summary', workflow: '03-youtube-summary.json', prompt: '03-youtube-summary.md' },
  { id: '04', slug: 'threads-influencer', workflow: '04-threads-influencer.json', prompt: '04-threads-influencer.md' },
  { id: '05', slug: 'note-monitor', workflow: '05-note-monitor.json', prompt: '05-note-monitor.md' },
  { id: '06', slug: 'weekly-report', workflow: '06-weekly-trend-report.json', prompt: '06-weekly-report.md' },
];

/** Path (relative to reporters/) of a native reporter's prompt file. */
export function promptPathFor(reporter) {
  return `../n8n/prompts/${reporter.id}-${reporter.slug}.md`;
}

/** Path (relative to reporters/) of a native reporter's fixture file. */
export function fixturePathFor(reporter) {
  return `./fixtures/${reporter.id}-${reporter.slug}.json`;
}
