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

/**
 * POST a draft to WordPress. Returns { status, id, body }.
 * Injectable fetch keeps it testable against a mock server.
 * @param {string} postsUrl
 * @param {{username: string, appPassword: string}} auth
 * @param {{title: string, content: string, status?: string}} payload
 */
export async function postDraft(postsUrl, auth, payload, { fetchImpl = fetch } = {}) {
  if (!payload || !payload.title || !payload.content) {
    throw new Error('payload requires title and content');
  }
  const res = await fetchImpl(postsUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: basicAuthHeader(auth.username, auth.appPassword),
    },
    body: JSON.stringify({
      title: payload.title,
      content: payload.content,
      status: payload.status || 'draft',
    }),
  });
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  return { status: res.status, id: body && body.id, body };
}
