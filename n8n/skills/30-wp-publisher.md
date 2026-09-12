---
skill: wp-publisher
version: "1.0"
agent: claim-builder
phase: SHIP
inputs:
  - article_draft: string
  - title: string
  - meta_description: string
  - slug: string
  - featured_image_url: string
  - verdict: "PASS"
  - categories: list[string]
  - tags: list[string]
  - language: "ja|en"
outputs:
  - wp_post_id: integer
  - wp_url: string
  - published_at: string
auditor_required: true
memory_read:
  - シーン層
memory_write:
  - シーン層
---

# 30-wp-publisher — WordPress 投稿スキル

Auditor verdict = PASS の確認後にのみ実行。
REST API + Application Password で投稿する。

---

## DEFINE

**目的**: Auditor PASS 済みの記事を WordPress に投稿する。

**前提条件**:
- `verdict` フィールドが `"PASS"` でなければ即時 FAIL:AUDIT_REQUIRED
- Application Password は `WP_APP_PASSWORD` 環境変数から取得
- 投稿後に シーン層 に URL を記録 (重複投稿防止)

**制約**:
- `WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD` はすべて環境変数
- ハードコード認証情報は Auditor pre-flight で検出・ブロック
- 同一 slug の既存投稿はシーン層チェックで防ぐ

**成功条件**:
- HTTP 201 Created
- `wp_post_id` と `wp_url` が返る

---

## PLAN

```
1. verdict !== 'PASS' → FAIL:AUDIT_REQUIRED
2. シーン層クエリ → slug 既存チェック
3. featured_image_url が空 → Flux.1/fal.ai で生成
   (FAL_API_KEY 環境変数使用)
4. WordPress REST API POST /wp-json/wp/v2/posts
5. レスポンスから wp_post_id, wp_url を取得
6. シーン層に { slug, wp_post_id, wp_url, published_at } を書き込む
```

---

## BUILD

WordPress 投稿 (n8n HTTP Request):
```json
{
  "method": "POST",
  "url": "{{ $env.WP_URL }}/wp-json/wp/v2/posts",
  "authentication": "basicAuth",
  "basicAuth": {
    "user": "{{ $env.WP_USERNAME }}",
    "password": "{{ $env.WP_APP_PASSWORD }}"
  },
  "body": {
    "title": "{{ $json.title }}",
    "content": "{{ $json.article_draft }}",
    "slug": "{{ $json.slug }}",
    "status": "publish",
    "excerpt": "{{ $json.meta_description }}",
    "categories": "{{ $json.category_ids }}",
    "tags": "{{ $json.tag_ids }}",
    "featured_media": "{{ $json.featured_media_id }}",
    "meta": {
      "_yoast_wpseo_title": "{{ $json.title }}",
      "_yoast_wpseo_metadesc": "{{ $json.meta_description }}"
    }
  }
}
```

Featured image upload (Flux.1 / fal.ai):
```json
{
  "method": "POST",
  "url": "https://fal.run/fal-ai/flux/dev",
  "headers": { "Authorization": "Key {{ $env.FAL_API_KEY }}" },
  "body": {
    "prompt": "{{ $json.og_title }} — professional blog featured image",
    "image_size": "landscape_16_9"
  }
}
```

---

## REVIEW

Auditor gate チェック項目:
- [ ] `verdict === 'PASS'` の確認
- [ ] `WP_APP_PASSWORD` が環境変数から取得 (ハードコードなし)
- [ ] slug がシーン層に未登録
- [ ] `FAL_API_KEY` が環境変数から取得

---

## SHIP

HTTP 201 → シーン層に記録 → パイプライン完了。
`wp_url` を n8n ワークフロー完了通知 (Slack/メール) に渡す。
