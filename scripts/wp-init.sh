#!/usr/bin/env bash
# WordPress auto-initialization: creates categories, tags, and verifies auth.
# Reads taxonomy from data/wp-taxonomy.json.
# Usage: bash scripts/wp-init.sh
#
# Auth + endpoint shape (requirements §24) — auto-selected by WP_BEARER_TOKEN:
#   - set:     WordPress.com production. Bearer OAuth2 access_token, and the
#              API is reached through public-api.wordpress.com/wp/v2/sites/{WP_SITE}
#              (a WordPress.com-hosted site's own /wp-json/wp/v2 is not the
#              REST entry point when two-step auth is active). Requires WP_SITE
#              (e.g. liquitex929aa21393-eyqci.wordpress.com — the unmapped_url,
#              not a mapped custom domain).
#   - unset:   self-hosted sandbox. Basic auth (WP_USERNAME + WP_APP_PASSWORD)
#              against {WP_URL}/wp-json/wp/v2.
set -euo pipefail

WP_URL="${WP_URL:-http://localhost:8080}"
WP_SITE="${WP_SITE:-}"
WP_USERNAME="${WP_USERNAME:-admin}"
WP_APP_PASSWORD="${WP_APP_PASSWORD:-}"
WP_BEARER_TOKEN="${WP_BEARER_TOKEN:-}"
TAXONOMY_FILE="$(dirname "$0")/../data/wp-taxonomy.json"

if [[ -n "$WP_BEARER_TOKEN" ]]; then
  if [[ -z "$WP_SITE" ]]; then
    echo "ERROR: WP_BEARER_TOKEN is set but WP_SITE is not." >&2
    echo "       WP_SITE must be the site's unmapped wordpress.com domain" >&2
    echo "       (e.g. liquitex929aa21393-eyqci.wordpress.com)." >&2
    exit 1
  fi
  AUTH_HEADER="Authorization: Bearer ${WP_BEARER_TOKEN}"
  AUTH_DESC="Bearer (WP_BEARER_TOKEN) — WordPress.com production"
  API_BASE="https://public-api.wordpress.com/wp/v2/sites/${WP_SITE}"
elif [[ -n "$WP_APP_PASSWORD" ]]; then
  AUTH_HEADER="Authorization: Basic $(printf '%s:%s' "$WP_USERNAME" "$WP_APP_PASSWORD" | base64 -w 0)"
  AUTH_DESC="Basic ($WP_USERNAME) — self-hosted sandbox"
  API_BASE="${WP_URL%/}/wp-json/wp/v2"
else
  echo "ERROR: no credentials set. Set WP_BEARER_TOKEN + WP_SITE (WordPress.com" >&2
  echo "       production) or WP_USERNAME + WP_APP_PASSWORD (self-hosted sandbox)." >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq is required. Install with: apt-get install -y jq" >&2
  exit 1
fi

check_auth() {
  local status
  status=$(curl -s -o /dev/null -w '%{http_code}' \
    -H "$AUTH_HEADER" \
    "${API_BASE}/users/me")
  if [[ "$status" != "200" ]]; then
    echo "ERROR: Authentication failed (HTTP $status) using $AUTH_DESC." >&2
    echo "       Basic auth on WordPress.com with two-step auth active returns 401" >&2
    echo "       (invalid_token) — use WP_BEARER_TOKEN instead (requirements §24)." >&2
    exit 1
  fi
  echo "[OK] Authentication verified."
}

create_category() {
  local name="$1" slug="$2" description="$3"
  local existing
  existing=$(curl -s \
    -H "$AUTH_HEADER" \
    "${API_BASE}/categories?slug=${slug}")
  if [[ $(echo "$existing" | jq 'length') -gt 0 ]]; then
    echo "[SKIP] Category already exists: $name ($slug)"
    return
  fi
  local result
  result=$(curl -s -X POST \
    -H "$AUTH_HEADER" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"${name}\",\"slug\":\"${slug}\",\"description\":\"${description}\"}" \
    "${API_BASE}/categories")
  local new_id
  new_id=$(echo "$result" | jq -r '.id // empty')
  if [[ -n "$new_id" ]]; then
    echo "[CREATED] Category: $name (id=$new_id)"
  else
    echo "[WARN] Failed to create category: $name" >&2
    echo "$result" | jq -r '.message // .' >&2
  fi
}

create_tag() {
  local name="$1" slug="$2"
  local existing
  existing=$(curl -s \
    -H "$AUTH_HEADER" \
    "${API_BASE}/tags?slug=${slug}")
  if [[ $(echo "$existing" | jq 'length') -gt 0 ]]; then
    echo "[SKIP] Tag already exists: $name ($slug)"
    return
  fi
  local result
  result=$(curl -s -X POST \
    -H "$AUTH_HEADER" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"${name}\",\"slug\":\"${slug}\"}" \
    "${API_BASE}/tags")
  local new_id
  new_id=$(echo "$result" | jq -r '.id // empty')
  if [[ -n "$new_id" ]]; then
    echo "[CREATED] Tag: $name (id=$new_id)"
  else
    echo "[WARN] Failed to create tag: $name" >&2
    echo "$result" | jq -r '.message // .' >&2
  fi
}

echo "=== WordPress Initialization ==="
echo "Target: $API_BASE"
echo "Auth:   $AUTH_DESC"
echo ""

check_auth
echo ""

echo "--- Creating categories ---"
cat_count=$(jq '.categories | length' "$TAXONOMY_FILE")
for i in $(seq 0 $((cat_count - 1))); do
  name=$(jq -r ".categories[$i].name" "$TAXONOMY_FILE")
  slug=$(jq -r ".categories[$i].slug" "$TAXONOMY_FILE")
  desc=$(jq -r ".categories[$i].description" "$TAXONOMY_FILE")
  create_category "$name" "$slug" "$desc"
done

echo ""
echo "--- Creating tags ---"
tag_count=$(jq '.tags | length' "$TAXONOMY_FILE")
for i in $(seq 0 $((tag_count - 1))); do
  name=$(jq -r ".tags[$i].name" "$TAXONOMY_FILE")
  slug=$(jq -r ".tags[$i].slug" "$TAXONOMY_FILE")
  create_tag "$name" "$slug"
done

echo ""
echo "=== Initialization complete ==="
