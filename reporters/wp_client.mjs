// Minimal WordPress REST client for posting reporter output.
// This is the real posting seam exercised by scripts/e2e_smoke.mjs and by
// reporters/wp_client.test.mjs (against a local mock HTTP server).

/** Build an HTTP Basic auth header from a WordPress Application Password. */
export function basicAuthHeader(username, appPassword) {
  const token = Buffer.from(`${username}:${appPassword}`).toString('base64');
  return `Basic ${token}`;
}

/**
 * Resolve the posts endpoint. Prefers an explicit full URL (e.g. the WordPress.com
 * public API), else appends the self-hosted REST path to a site base URL.
 */
export function resolvePostsUrl({ postsUrl, wpUrl }) {
  if (postsUrl) return postsUrl;
  if (!wpUrl) throw new Error('either postsUrl or wpUrl is required');
  return `${wpUrl.replace(/\/+$/, '')}/wp-json/wp/v2/posts`;
}

/** Derive the categories endpoint from a posts endpoint (both end in "/posts"). */
export function categoriesUrlFromPosts(postsUrl) {
  if (!/\/posts$/.test(postsUrl)) {
    throw new Error(`cannot derive categories URL from: ${postsUrl}`);
  }
  return postsUrl.replace(/\/posts$/, '/categories');
}

/**
 * Resolve a category slug to its WordPress category id. Throws a clear,
 * actionable error if the category doesn't exist yet (categories must be
 * created ahead of time by scripts/wp-init.sh from data/wp-taxonomy.json —
 * this never auto-creates one, so a typo'd slug fails loudly, not silently).
 */
export async function resolveCategoryId(postsUrl, auth, slug, { fetchImpl = fetch } = {}) {
  const url = `${categoriesUrlFromPosts(postsUrl)}?slug=${encodeURIComponent(slug)}`;
  const res = await fetchImpl(url, {
    headers: { Authorization: basicAuthHeader(auth.username, auth.appPassword) },
  });
  if (!res.ok) {
    throw new Error(`category lookup failed for slug="${slug}": HTTP ${res.status}`);
  }
  const list = await res.json();
  if (!Array.isArray(list) || list.length === 0) {
    throw new Error(`category not found on WordPress: slug="${slug}" — run scripts/wp-init.sh first`);
  }
  return list[0].id;
}

/**
 * POST a draft to WordPress. Returns { status, id, body }.
 * If payload.categorySlug is set, resolves it to a real WordPress category id
 * and attaches it — categories are not silently dropped (docs §15-11).
 * Injectable fetch keeps it testable against a mock server.
 * @param {string} postsUrl
 * @param {{username: string, appPassword: string}} auth
 * @param {{title: string, content: string, status?: string, categorySlug?: string}} payload
 */
export async function postDraft(postsUrl, auth, payload, { fetchImpl = fetch } = {}) {
  if (!payload || !payload.title || !payload.content) {
    throw new Error('payload requires title and content');
  }
  const body = {
    title: payload.title,
    content: payload.content,
    status: payload.status || 'draft',
  };
  if (payload.categorySlug) {
    body.categories = [await resolveCategoryId(postsUrl, auth, payload.categorySlug, { fetchImpl })];
  }
  const res = await fetchImpl(postsUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: basicAuthHeader(auth.username, auth.appPassword),
    },
    body: JSON.stringify(body),
  });
  let resBody = null;
  try {
    resBody = await res.json();
  } catch {
    resBody = null;
  }
  return { status: res.status, id: resBody && resBody.id, body: resBody };
}
