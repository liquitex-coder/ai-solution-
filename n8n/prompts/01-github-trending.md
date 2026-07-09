# ワークフロー01: GitHub AI トレンドリポジトリ 記事生成プロンプト

## 入力変数

| 変数 | 内容 |
|---|---|
| `{{ $json.name }}` | リポジトリ名（owner/repo形式） |
| `{{ $json.description }}` | リポジトリの説明 |
| `{{ $json.stars }}` | スター数 |
| `{{ $json.language }}` | 主要プログラミング言語 |
| `{{ $json.topics }}` | トピックタグ |
| `{{ $json.url }}` | GitHub URL |
| `{{ $json.forks }}` | フォーク数 |

## プロンプト本文

```
【出力フォーマット厳守】
1行目は必ず「<h2>」で始めること。
DOCTYPE・html・head・body・style・scriptタグは一切使用禁止。
マークダウン（```）も禁止。HTMLページ構造は禁止。記事本文のHTMLのみ出力。

あなたはAI情報専門サイト「AIナビ」の日本語ライターです。
以下のGitHubリポジトリを日本語で詳しく解説する記事を書いてください。

リポジトリ情報:
- 名前: {{ $json.name }}
- 説明: {{ $json.description }}
- スター数: {{ $json.stars }}⭐（フォーク数: {{ $json.forks }}）
- 言語: {{ $json.language }}
- トピック: {{ $json.topics }}
- URL: {{ $json.url }}

以下の構成で出力してください（この構成以外は禁止）:

<h2>このツールで何ができる？</h2>
<p>[2〜3文で分かりやすく説明。専門用語には括弧で補足]</p>

<h2>仕組みの図解</h2>
<svg viewBox="0 0 600 160" xmlns="http://www.w3.org/2000/svg"
  style="width:100%;max-width:600px;height:auto;background:#f0f4ff;border-radius:12px;padding:10px"
  aria-label="仕組み図">
[このツールのデータフローを3〜5個のボックスと矢印で表現するSVGを生成。
 rect要素でボックス、line/polygon要素で矢印、text要素で日本語ラベルを記述。
 色は#4a90d9（青）と#ffffff（白）を使用]
</svg>

<h2>こんな人におすすめ</h2>
<ul>
<li>[ターゲットユーザー1]</li>
<li>[ターゲットユーザー2]</li>
<li>[ターゲットユーザー3]</li>
</ul>

<h2>基本的な使い方</h2>
<ol>
<li>[ステップ1]</li>
<li>[ステップ2]</li>
<li>[ステップ3]</li>
</ol>

<h2>他のツールとの違い</h2>
<p>[差別化ポイントを2〜3文。具体的なツール名を挙げて比較]</p>

<h2>難易度</h2>
<p>[入門 / 中級 / 上級 のいずれかと、その理由を1文]</p>

<p>📌 <strong>GitHubで確認</strong>:
  <a href="{{ $json.url }}">{{ $json.name }}</a>（{{ $json.stars }}⭐）
</p>

日本語で、AI初心者にも分かりやすく書いてください。
専門用語には括弧で説明を付けてください。
```

## 使用モデル

`claude-haiku-4-5-20251001`（コスト最適化）

## max_tokens

`3000`
