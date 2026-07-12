# n8n ワークフロー セットアップガイド

## Step 0: ローカルサンドボックス起動（Docker）

本番（n8n.cloud）に移行する前に、Docker でローカル環境を立ち上げて動作確認します。

### 0-1. 前提ツール

- Docker Desktop（または Docker Engine + Compose）
- Git

### 0-2. 環境変数ファイルの準備

```bash
cp .env.example .env
# .env を編集し、各 API キーを設定
```

### 0-3. サービス起動

```bash
docker compose up -d
```

| サービス | URL | 用途 |
|---|---|---|
| WordPress | http://localhost:8080 | 記事投稿先 |
| n8n | http://localhost:5678 | ワークフロー実行 |
| MySQL | localhost:3306 | WordPress DB |

### 0-4. WordPress 初期設定

1. http://localhost:8080/wp-admin/ にアクセス
2. インストールウィザードを完了（言語: 日本語 推奨）
3. 管理者アカウント作成後、**Application Password** を発行:
   - 「ユーザー」→「プロフィール」→「アプリケーションパスワード」
   - 名前: `n8n connector` → 「追加」
   - 表示されたパスワードを `.env` の `WP_APP_PASSWORD` に設定

### 0-5. n8n にワークフローをインポート

1. http://localhost:5678 にアクセス（Basic Auth: `admin` / `.env` の `N8N_PASSWORD`）
2. 左メニュー「Workflows」→「Add workflow」
3. 右上「…」→「Import from file」
4. `n8n/workflows/01〜06` を順番にインポート

### 0-6. e2e 動作確認チェックリスト

```
[ ] docker compose ps で全サービスが Up
[ ] http://localhost:8080 で WordPress トップページ表示
[ ] http://localhost:5678 で n8n ログイン成功
[ ] ワークフロー01 を手動実行 → WordPress に下書き記事が作成される
[ ] ワークフロー02 を手動実行 → RSS 取得 → Claude API → WordPress 下書き
[ ] wp-admin/edit.php?post_status=draft で記事一覧を確認
```

---

## 前提条件（クラウド環境）

- n8n.cloudアカウント: `liquitex-coder.app.n8n.cloud`（14日トライアル）
- WordPress.com サイト: `liquitex929aa21393-eyqci.wordpress.com`

---

## Step 1: WordPress.com APIトークン取得

> **重要（要件§24・2026-07-12実運用で確認）**: このサイトは二段階認証が有効なため、
> WordPress.com の `wp/v2` REST API は Application Password の直接利用（Basic認証）を
> `401 invalid_token` で拒否する。**OAuth2 の Bearer トークンが必須**。

### 1-1. 二段階認証 + Application Password 発行（未完了の場合）

1. https://wordpress.com/me/security にアクセス
2. Recovery Email を先に設定（推奨・紛失時の復旧用）
3. 「Two-Step Authentication」を有効化（認証アプリ or SMS）
4. 同ページに出現する「Application Passwords」で1つ発行（24文字、その場で控える）

### 1-2. アプリ登録（未完了の場合）

1. https://developer.wordpress.com/apps/new/ にアクセス
2. 以下を入力:
   - **Name**: AIナビ n8n Connector
   - **Description**: n8nからの自動投稿用（必須項目）
   - **Website URL**: https://liquitex-coder.app.n8n.cloud
   - **Redirect URLs**: https://liquitex-coder.app.n8n.cloud（password grantでは未使用だが必須項目）
   - **Type**: Web
3. 送信して **Client ID** と **Client Secret** をメモ

### 1-3. アクセストークン取得（password grant）

```bash
curl -s -X POST "https://public-api.wordpress.com/oauth2/token" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "grant_type=password" \
  -d "username=YOUR_WPCOM_USERNAME" \
  -d "password=YOUR_APPLICATION_PASSWORD" \
  -d "blog_url=liquitex929aa21393-eyqci.wordpress.com"
```

→ `{"access_token":"...","token_type":"bearer",...}` が返る。この `access_token` を
`.env` の `WP_BEARER_TOKEN` に設定する（原則失効しない・無期限）。

**検証**（`200` が返れば成功）:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://public-api.wordpress.com/rest/v1.1/me"
```

⚠️ PowerShellでは `curl` ではなく `curl.exe` を使い、トークンは変数に**シングルクォート**
`'...'` で代入すること（ダブルクォートは `$` 等を解釈し値が壊れる場合がある）。

---

## Step 2: 各API キー取得

| API | 取得場所 | 必須ワークフロー |
|---|---|---|
| Claude API | https://console.anthropic.com | 全ワークフロー |
| GitHub Token | https://github.com/settings/tokens | ワークフロー01 |
| YouTube Data API v3 | https://console.cloud.google.com | ワークフロー03 |
| Threads API | https://developers.facebook.com | ワークフロー04 |
| Perplexity API | https://www.perplexity.ai/settings/api | ワークフロー06 |

### GitHub Personal Access Token

1. https://github.com/settings/tokens → "Generate new token (classic)"
2. スコープ: **public_repo** のみチェック（読み取り専用でOK）
3. トークンをメモ

### Claude API Key

1. https://console.anthropic.com → API Keys
2. "Create Key" → キーをメモ

### YouTube Data API v3

1. https://console.cloud.google.com で新規プロジェクト作成
2. 「APIとサービス」→「ライブラリ」→ "YouTube Data API v3" を有効化
3. 「認証情報」→「APIキーを作成」→ キーをメモ

---

## Step 3: n8n.cloudへのワークフローインポート

### 自動インポート（Proプラン以降・推奨、要件§25）

無料トライアルではn8n公開APIが無効（`Upgrade to use API`と表示される）。Pro
プラン以降で `Settings → n8n API` からAPIキーを発行できる。発行後:

```powershell
$env:N8N_API_KEY = "発行したAPIキー"
$env:ANTHROPIC_API_KEY = "..."
$env:WP_BEARER_TOKEN = "..."
# 任意: GITHUB_TOKEN, PERPLEXITY_API_KEY, KIMI_API_KEY, THREADS_ACCESS_TOKEN, YOUTUBE_API_KEY
powershell -ExecutionPolicy Bypass -File scripts/n8n_deploy.ps1
```

Credential作成（環境変数が設定されている分のみ・冪等）とワークフロー9本の
インポートを自動実行する。**Active化は行わない**（Step 5で手動確認してから
ONにする、既存の段階的ロールアウト方針を維持）。

### 手動インポート手順（トライアル中 or APIを使わない場合）

1. `liquitex-coder.app.n8n.cloud` にログイン
2. 左メニュー「Workflows」→ 右上「Add workflow」
3. 右上「...（3点メニュー）」→「Import from file」
4. 以下のJSONファイルを順番にインポート:

```
n8n/workflows/01-github-ai-trending-daily.json
n8n/workflows/02-rss-monitor.json
n8n/workflows/03-youtube-summary.json
n8n/workflows/04-threads-influencer.json
n8n/workflows/05-note-monitor.json
n8n/workflows/06-weekly-trend-report.json
n8n/workflows/07-article-writer.json
n8n/workflows/08-kimi-zh.json
n8n/workflows/09-multi-source-research.json
```

---

## Step 4: n8nで認証情報（Credentials）を設定

各ワークフローをインポート後、赤くエラーになっているノードの認証情報を設定します。

### 共通で使う認証情報（1回だけ設定すれば全ワークフローで使い回し可能）

#### A. Claude API Key

1. n8n左メニュー「Credentials」→「Add credential」
2. 「HTTP Header Auth」を選択
3. Name: `Claude API Key`
4. **Name**: `x-api-key`
5. **Value**: `sk-ant-XXXXXXXXXX`（あなたのAPIキー）
6. 保存

#### B. WordPress App Password（本番: WordPress.com Bearer、要件§24）

> 二段階認証が有効な WordPress.com サイトでは Basic 認証（Application Password
> 直用）は `401 invalid_token` になる。credential 名は既存ワークフローとの
> 互換のため `WordPress App Password` のまま、**値だけ Bearer** に変更する。

1. 「HTTP Header Auth」を選択
2. Name: `WordPress App Password`（既存ワークフローが参照する名前のまま）
3. **Name**: `Authorization`
4. **Value**: `Bearer YOUR_ACCESS_TOKEN` ← Step 1-3 で取得した `access_token`
5. 保存

> ローカルの自己ホスト型サンドボックス（`docker-compose up`、二段階認証なし）
> のみを使う場合は、代わりに `Basic BASE64(username:app_password)` で構わない
> （`scripts/wp-init.sh` はどちらの環境変数が設定されているかで自動判定する）。

#### C. GitHub API Token

1. 「HTTP Header Auth」を選択
2. Name: `GitHub API Token`
3. **Name**: `Authorization`
4. **Value**: `token YOUR_GITHUB_TOKEN`
5. 保存

#### D. YouTube Data API v3 Key

1. 「HTTP Query Auth」を選択
2. Name: `YouTube Data API v3 Key`
3. **Name**: `key`
4. **Value**: `YOUR_YOUTUBE_API_KEY`
5. 保存

#### E. Perplexity API Key

1. 「HTTP Header Auth」を選択
2. Name: `Perplexity API Key`
3. **Name**: `Authorization`
4. **Value**: `Bearer YOUR_PERPLEXITY_API_KEY`
5. 保存

### GITHUB_TOKEN（Credentialではなく環境変数、要件§25-3）

各WFの「プロンプト読込み」Codeノードは `$env.GITHUB_TOKEN` を直接参照して
GitHub Contents APIからプロンプトを取得する。これはCredentialではなく
n8nの環境変数機能で設定する（`scripts/n8n_deploy.ps1` は対象外・別途手動設定）:

1. n8n左メニュー「Settings」→「Environments」（Proプラン以降）
2. 変数名 `GITHUB_TOKEN`、値に GitHub Personal Access Token（`public_repo` スコープ）を設定

---

## Step 5: ワークフロー動作確認

### テスト実行順序

1. **ワークフロー01**（GitHub AI Trending）を開く
2. 「Execute workflow」ボタンで手動実行テスト
3. エラーがないか確認
4. WordPress.com の下書き記事に記事が作成されているか確認
5. 問題なければ「Active」をONにする

### 推奨テスト順序

```
01 GitHub → 02 RSS Monitor → 05 note → 06 週次レポート → 03 YouTube → 04 Threads
```

※ Threads APIは認証が複雑なため最後に実施

---

## Step 6: WordPress.com の確認

各ワークフロー実行後、以下で投稿を確認:

1. https://liquitex929aa21393-eyqci.wordpress.com/wp-admin/
2. 「投稿」→「下書き」

週次レポート（ワークフロー06）のみ `status: publish` で即公開されます。

---

## ワークフロー一覧と実行スケジュール

| # | ワークフロー | スケジュール | 必須API |
|---|---|---|---|
| 01 | GitHub AI Trending | 毎朝8時 (JST) | GitHub, Claude, WordPress |
| 02 | RSS Monitor | 30分ごと | Claude, WordPress |
| 03 | YouTube新動画 | 1時間ごと | YouTube, Claude, WordPress |
| 04 | Threadsインフルエンサー | 3時間ごと | Threads, Claude, WordPress |
| 05 | note監視 | 1時間ごと | Claude, WordPress |
| 06 | 週次トレンドレポート | 毎週月曜9時 (JST) | Perplexity, Claude, WordPress |

---

## エラーハンドリング

### n8n Error Trigger ノードの設定（推奨）

全ワークフローに Error Trigger ノードを追加することでエラー為に通知を受け取れます。

1. n8n メニュー「Settings」→「Workflow settings」
2. "Error workflow": 専用のエラー通知ワークフローを設定
3. エラー通知ワークフローの例（将来追加予定）: Slack/メールにエラー内容を送信

### エラー別対応手順

#### 401 Unauthorized（WordPress 認証エラー）

**原因（本番・WordPress.com）**: `invalid_token` の場合、Basic認証（Application
Password直用）を二段階認証有効サイトに送っている可能性が最も高い（要件§24）。
Application Password自体の期限切れではなく、**認証方式そのものが違う**。

**対応手順（本番）**:
1. Step 1-3 の password grant を再実行し、新しい `access_token` を取得
2. n8n Credentials「WordPress App Password」の Value を
   `Bearer NEW_ACCESS_TOKEN` に更新
3. `curl -H "Authorization: Bearer NEW_ACCESS_TOKEN" https://public-api.wordpress.com/rest/v1.1/me`
   で `200` を確認してから再実行

**原因（ローカルサンドボックス・Basic認証運用時のみ）**: Application Password
の期限切れ / 誤入力 / アカウント変更

**対応手順（サンドボックス）**:
1. WordPress 管理画面 → 「ユーザー」→ 「プロフィール」
2. 「アプリケーションパスワード」内の旧パスワードを削除
3. 「新しいアプリケーションパスワード」を追加「追加」
4. 新しいパスワードで base64 を再生成

```bash
echo -n 'username:NEW_APP_PASSWORD' | base64
```

5. n8n Credentials 「WordPress App Password」の値を更新

#### 403 Forbidden（GitHub API レート制限）

**原因**: トークンなしで 60 req/h を超過 / トークン小で 5000 req/h を超過

**n8n でのレート制限対応**:
1. ワークフロー01 の "GitHub APIでAIリポジトリ取得" ノードの後に「**IF**」ノードを追加
2. 条件: `{{ $json.message }}` に "rate limit" を含む場合
3. はい側: 「**Wait**」ノードで 60分待機 → 再実行
4. いいえ側: 通常処理を続行

**レート制限残数の確認**:
```bash
# 現在のコア数確認
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

#### 529 Overloaded（Claude API 過負荷）

**原因**: Anthropic サーバーの一時的過負荷。数分待つことがほとんど。

**n8n での指数バックオフパターン**:
1. Claude API ノードの「**Settings**」→「**On Error**」に「**Retry on Fail**」を設定
2. Max Tries: `3`
3. Wait Between Tries: `60000`（ms）
4. または手動で Wait ノードをパイプラインに挿入:

```
Claude API ノード
  ↓（失敗時）
IF ノード: status == 529 ?
  ↓ Yes
Wait ノード: 60000ms
  ↓
Claude API ノード（再実行）
```

#### 410 Gone（WordPress REST API エンドポイント変更）

**原因**: WordPress バージョンアップで REST APIエンドポイントが変更

**対応**:
1. WordPress バージョンを確認: `wp-admin/about.php`
2. WP REST API エンドポイントを手動で確認:

```bash
# WordPress.com
curl https://public-api.wordpress.com/wp/v2/sites/YOUR_SITE/posts

# セルフホスト WordPress
curl http://localhost:8080/wp-json/wp/v2/posts
```

3. n8n ワークフロー内の HTTP ノードの URL を更新

#### n8n タイムアウト

**原因**: 1回の実行で全ノードを完了できない場合

**対応**:
1. ワークフローを分割する
   - 例: ワークフロー01 のリポジトリ取得エラーー→ リポジトリ取得「パート2」と分割
2. 高負荷な身辺ノード（Code ノード内の御丗いデータ）を減らす
3. n8n.cloud がタイムアウト設定内に収まるようパイプラインを短縮化

---

## トラブルシューティング（環境別）

### Docker コンテナが起動しない

```bash
# ログを確認
docker compose logs db
docker compose logs wordpress
docker compose logs n8n

# コンテナをリセット
docker compose down && docker compose up -d
```

**チェックリスト**:
- [ ] ポート 8080/5678/3306 が既に使用中でないか確認: `lsof -i :8080`
- [ ] `.env` の変数が正しく設定されているか確認
- [ ] Docker に十分なメモリがあるか確認（最低4GB推奨）

### WordPress.com 投稿に失敗する

- Application Password の Base64 エンコードを再生成して試す
- WordPress.com の REST API エンドポイント URL を再確認
- n8n Credentials の値が正しく保存されているか確認
- **セルフホスト WP で REST API が 404 になる場合**: 管理画面 → 設定 → パーマリンク → 「投稿名」等に変更して「変更を保存」（「基本」設定では REST API ルーティングが機能しない）

### Claude APIでエラーが出る

- `401`: APIキーが正しいか確認（コンソールでキーを再コピー）
- `429`: レート制限超過 → Wait ノードで待機して再実行
- `529`: 過負荷 → 60秒待機すると大多数解決する
- `model not found`: モデル ID が変更された可能性 → Anthropicドキュメントで最新のモデル ID を確認

### GitHub APIで403エラー

- トークンなしではパブリックAPIは使えるがレート制限が厳しい（60req/h）
- トークンを設定すると5000req/hに増加
- `X-RateLimit-Remaining: 0` の場合、`X-RateLimit-Reset` の Unixタイムスタンプまで待機

### RSS URLが404になる

- 各社のブログRSSのURLは変更されることがある
- 実際のサイトでRSSリンクを確認して更新
- note.com の RSS: `https://note.com/hashtag/{TAG}/rss`（TAGは URL エンコードする）

### n8n のワークフローが自動実行されない

- ワークフローの „Active" スイッチが ON か確認
- n8n クラウドのプランが有効か確認（トライアル期限切れ）
- Executions タブでエラーログを確認
