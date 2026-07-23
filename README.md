# claude-english-coach

Claudeのシステムプロンプトを使った、発音・会話・語彙を一気に鍛える英語学習メソッドです。
学習結果をAnki互換のCSVとして自動出力し、スペーシング学習と組み合わせることで定着率を高めます。

---

## 概要

このリポジトリで管理しているのは、Claude（AI）に渡すシステムプロンプト（`system_prmpt.md`）です。
このプロンプトをClaudeのシステムプロンプトに設定するだけで、以下のモードが使えるようになります。

---

## モード一覧

| コマンド | モード | 内容 |
|---|---|---|
| （デフォルト）| TRANSLATE MODE | 日本語→英語を3パターン（Casual / Professional / Super Native）＋IPA発音付きで出力 |
| `/talk` | SPEAK MODE | 英語入力を添削・ネイティブ代替表現を提示 |
| `/chat {話題}` | CHAT MODE | ネイティブとのフリー会話練習。`/end`でまとめてフィードバック |
| `/export` | EXPORT | セッション全コンテンツをAnki互換CSVとして出力 |

---

## 使い方

1. `system_prmpt.md` の内容をコピー
2. Claudeのシステムプロンプト欄に貼り付け
3. 日本語で話しかけるとTRANSLATE MODEが起動
4. セッション終了時に `/export` でAnkiカードを生成

---

## Ankiとの連携

`/export` を実行するとCSVが生成されます。Ankiへのインポート設定：

- ノートタイプ: 基本（Basic）
- フィールドの区切り文字: コンマ
- フィールドのHTMLを許可: OFF
- フィールド対応: フィールド1 → 表面 / フィールド2 → 裏面 / フィールド3 → タグ

インポート後は `tag:yyyymmdd` で検索すると、そのセッション分のカードだけを絞り込めます。

---

## ポッドキャスト自動生成

学習セッションの台本テキストを保存すると、1コマンドで音声mp3を生成しスマホのPodcastアプリに自動配信できます。

### 仕組み

```
① Claude.ai でセッション → 台本テキストを exports_listening/ に保存
        ↓
② uv run make_podcast.py exports_listening/20260723.txt --push
        ↓
③ edge-tts（Microsoft、無料・APIキー不要）で行ごとに音声生成
   ・英語行 → ネイティブ英語音声（en-US-JennyNeural）
   ・日本語行 → 日本語音声（ja-JP-NanamiNeural）
   ※ ひらがな・カタカナ・漢字の有無でUnicode判別（タグ不要）
        ↓
④ ffmpeg で行音声を結合 → docs/audio/20260723.mp3
        ↓
⑤ docs/feed.xml（RSS）に新エピソードとして追記
        ↓
⑥ GitHub Pages に push → スマホが自動ダウンロード
```

使用技術はすべて無料（edge-tts / ffmpeg / GitHub Pages）。APIキー不要。

### スマホで聴く方法

**1. GitHub Pages を有効化（初回のみ）**

`https://github.com/kohaku222/claude-english-coach/settings/pages` を開き、  
Source: `Deploy from a branch` → Branch: `main` / `/docs` に設定して Save。

数分後にフィード URL が有効になります：
```
https://kohaku222.github.io/claude-english-coach/feed.xml
```

**2. Podcastアプリに登録（初回のみ）**

| アプリ | 登録手順 |
|---|---|
| **Overcast**（推奨・無料） | `+` → `Add URL` に上記フィードURLを貼り付け |
| **Apple Podcasts**（標準） | `ライブラリ` → 右上 `...` → `URLでフォローする` |
| **Pocket Casts** | `+` → `Add podcast by URL` |

登録後は新エピソードがpushされるたびに自動ダウンロードされます。

### 台本フォーマット

フォーマットは自由です。`#` で始まる行はスキップされます。

```
# セクションタイトル（読み上げスキップ）
今日は「just about to」という表現を練習します。
I was just about to leave.
ちょうど出かけようとしていたところでした。
```

---

## リポジトリ構成

```
claude-english-coach/
├── system_prmpt.md        # システムプロンプト本体
├── make_podcast.py        # ポッドキャスト生成スクリプト
├── pyproject.toml         # Python依存関係（uv管理）
├── exports_listening/     # 台本テキスト置き場（.txt）
└── docs/
    ├── index.html         # GitHub Pages トップ
    ├── feed.xml           # RSSフィード（自動更新）
    └── audio/             # 生成済みmp3
```

※ 個人の学習データ（CSVファイル）はGitHubには含めていません。

---

## 更新履歴

| 時期 | 内容 |
|---|---|
| 2026年4月 | プロジェクト開始。TRANSLATE MODEの基本形を構築 |
| 2026年4月〜5月 | IPA（発音記号）の精度向上、connected speech対応 |
| 2026年6月 | SPEAK MODE・CHAT MODE追加。`/export`コマンド実装。Ankiカード仕様（バリエーション統合・意味単位分割ルール）を詳細化 |
| 2026年7月 | Ankiカード表面フォーマットを全カード共通形式に統一（頭文字ヒント導入）。ポッドキャスト自動生成パイプライン追加 |

---

## 今後の予定

- [ ] シャドーイング専用モードの検討
- [ ] 単語帳モード（頻出単語リストとの連携）
