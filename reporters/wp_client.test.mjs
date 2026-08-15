import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { NATIVE } from './registry.mjs';
import { dryRunReporter } from './dryrun.mjs';
import { postDraft, basicAuthHeader, resolvePostsUrl, resolveCategoryId, categoriesUrlFromPosts } from './wp_client.mjs';

// Spin up a mock WordPress that emulates POST /wp-json/wp/v2/posts and
// GET /wp-json/wp/v2/categories?slug=... (as created ahead of time by
// scripts/wp-init.sh from data/wp-taxonomy.json).
async function startMockWp({ knownCategories = { factcheck: 501 } } = {}) {
  const received = [];
  let nextId = 100;
  const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://mock');
    if (req.method === 'GET' && url.pathname.endsWith('/wp-json/wp/v2/categories')) {
      const slug = url.searchParams.get('slug');
      const id = knownCategories[slug];
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(id ? [{ id, slug, name: slug }] : []));
      return;
    }
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', () => {
      if (req.method === 'POST' && url.pathname.endsWith('/wp-json/wp/v2/posts')) {
        const auth = req.headers['authorization'] || '';
        if (!auth.startsWith('Basic ')) {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ code: 'unauthorized' }));
          return;
        }
        const body = JSON.parse(raw);
        received.push({ auth, body });
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id: nextId++, ...body, link: `http://mock/${nextId}` }));
        return;
      }
      res.writeHead(404);
      res.end();
    });
  });
  server.listen(0);
  await once(server, 'listening');
  const { port } = server.address();
  return { server, received, base: `http://127.0.0.1:${port}` };
}

test('resolvePostsUrl prefers explicit URL, else builds REST path', () => {
  assert.equal(resolvePostsUrl({ postsUrl: 'https://x/y' }), 'https://x/y');
  assert.equal(resolvePostsUrl({ wpUrl: 'http://localhost:8080/' }), 'http://localhost:8080/wp-json/wp/v2/posts');
});

test('categoriesUrlFromPosts derives the sibling categories endpoint', () => {
  assert.equal(categoriesUrlFromPosts('https://x/wp-json/wp/v2/posts'), 'https://x/wp-json/wp/v2/categories');
});

test('resolveCategoryId resolves a known slug to its id over a real socket', async () => {
  const mock = await startMockWp({ knownCategories: { factcheck: 501 } });
  try {
    const postsUrl = `${mock.base}/wp-json/wp/v2/posts`;
    const id = await resolveCategoryId(postsUrl, { username: 'admin', appPassword: 'x' }, 'factcheck');
    assert.equal(id, 501);
  } finally {
    mock.server.close();
  }
});

test('resolveCategoryId fails closed on an unknown slug', async () => {
  const mock = await startMockWp({ knownCategories: {} });
  try {
    const postsUrl = `${mock.base}/wp-json/wp/v2/posts`;
    await assert.rejects(
      () => resolveCategoryId(postsUrl, { username: 'admin', appPassword: 'x' }, 'nonexistent-slug'),
      /category not found.*nonexistent-slug.*wp-init\.sh/,
    );
  } finally {
    mock.server.close();
  }
});

test('postDraft creates a draft over a real socket → 201 + id + real category attached', async () => {
  const mock = await startMockWp({ knownCategories: { factcheck: 501 } });
  try {
    const reporter = NATIVE.find((r) => r.slug === 'factcheck');
    const { payload } = await dryRunReporter(reporter);
    assert.equal(payload.categorySlug, 'factcheck', 'reporter payload carries the category slug to resolve');
    const postsUrl = `${mock.base}/wp-json/wp/v2/posts`;

    const result = await postDraft(postsUrl, { username: 'admin', appPassword: 'test pass' }, payload);

    assert.equal(result.status, 201, 'WordPress returns 201 Created');
    assert.equal(typeof result.id, 'number', 'response carries a post id');

    // The server actually received our real payload, as a draft, with auth,
    // and — the actual bug this fixes — a resolved real category id attached.
    assert.equal(mock.received.length, 1);
    assert.equal(mock.received[0].body.status, 'draft');
    assert.equal(mock.received[0].body.title, payload.title);
    assert.equal(mock.received[0].body.content, payload.content);
    assert.deepEqual(mock.received[0].body.categories, [501]);
    assert.equal(mock.received[0].auth, basicAuthHeader('admin', 'test pass'));
  } finally {
    mock.server.close();
  }
});

test('postDraft fails closed when the category is not registered on WordPress', async () => {
  const mock = await startMockWp({ knownCategories: {} }); // simulates wp-init.sh not having run
  try {
    const reporter = NATIVE.find((r) => r.slug === 'factcheck');
    const { payload } = await dryRunReporter(reporter);
    const postsUrl = `${mock.base}/wp-json/wp/v2/posts`;

    await assert.rejects(() => postDraft(postsUrl, { username: 'admin', appPassword: 'x' }, payload));
    assert.equal(mock.received.length, 0, 'never posts an article with an unresolved category');
  } finally {
    mock.server.close();
  }
});

test('mock WP rejects missing auth with 401', async () => {
  const mock = await startMockWp();
  try {
    const postsUrl = `${mock.base}/wp-json/wp/v2/posts`;
    const noAuthFetch = (url, opts) => {
      const headers = { ...opts.headers };
      delete headers.Authorization;
      return fetch(url, { ...opts, headers });
    };
    const result = await postDraft(
      postsUrl,
      { username: 'admin', appPassword: 'x' },
      { title: 't', content: '<h2>x</h2>' },
      { fetchImpl: noAuthFetch },
    );
    assert.equal(result.status, 401);
  } finally {
    mock.server.close();
  }
});
