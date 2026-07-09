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

### 1-1. アプリ登録（未完了の場合）

1. https://developer.wordpress.com/apps/ にアクセス
2. "Create New Application" をクリック
3. 以下を入力:
   - **Name**: AIナビ n8n Connector
   - **Description**: n8nからの自動投稿用
   - **Website URL**: https://liquitex929aa21393-eyqci.wordpress.com
   - **Redirect URL**: https://liquitex-coder.app.n8n.cloud/oauth/callback
   - **Type**: Web
4. 数式CAPTCHAに答えて送信（例: 8+6=14）
5. **Client ID** と **Client Secret** をメモ

### 1-2. アクセストークン取得（テスト用）

ブラウザで以下のURLを開く（YOUR_CLIENT_IDを置き換え）:

```
https://public-api.wordpress.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https://liquitex-coder.app.n8n.cloud/oauth/callback&response_type=token&scope=posts
```

→ 認証後、URLに `#access_token=XXXXX` が含まれたページにリダイレクトされる

このアクセストークンをメモ。

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

### インポート手順

1. `liquitex-coder.app.n8n.cloud` にログイン
2. 左メニュー「Workflows」→ 右上「Add workflow」
3. 右上「...（3点メニュー）」→「Import from file」
4. 以下のJSONファイルを順番にインポート:

```
n8n/workflows/01-github-ai-trending-daily.json
n8n/workflows/02-rss-monitor.json
n8n/workflows/03-youtube-new-video.json
n8n/workflows/04-threads-influencer.json
n8n/workflows/05-note-monitor.json
n8n/workflows/06-weekly-trend-report.json
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

#### B. WordPress Application Password（推奨）

1. 「HTTP Header Auth」を選択
2. Name: `WordPress App Password`
3. **Name**: `Authorization`
4. **Value**: `Basic BASE64(username:app_password)` ← `echo -n 'admin:xxxx xxxx xxxx' | base64` で生成
5. 保存

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

## トラブルシューティング

### WordPress.com 投稿に失敗する場合

- トークンの有効期限切れ → Step 1-2 を再実行
- サイトURLの確認: `liquitex929aa21393-eyqci.wordpress.com`

### Claude APIでエラーが出る場合

- APIキーが正しいか確認
- レートリミット超過の可能性 → 少し待って再実行

### GitHub APIで403エラー

- トークンなしでもパブリックAPIは使えるが、レート制限が厳しい（60req/h）
- トークンを設定すると5,000req/hに増加

### RSS URLが404になる場合

- 各社のブログRSSのURLは変更されることがある
- 実際のサイトでRSSリンクを確認して更新

### Docker コンテナが起動しない場合

- `docker compose logs db` でMySQL ログを確認
- ポート競合: 8080/5678/3306 が既に使用中でないか確認
- `.env` の変数が正しく設定されているか確認
