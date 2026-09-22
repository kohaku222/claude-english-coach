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
| `/drill` または `/drill {数字}` | DRILL MODE | 日本語→英語の反射的即英訳を鍛える高速ドリル。デフォルト7〜8文をまとめて出題・添削し、DRILL HISTORYで弱点を追跡 |
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

## シャドーイング学習ワークフロー

毎朝1本の動画でシャドーイング＋録音を行い、その日のうちに元スクリプトと自分の発話を比較・整形した1ファイルをClaudeに送ることで、重要語句やミス箇所の解説をその日のうちに受け取るワークフローです。

### 仕組み

```
① 朝：好きな動画を1本選び、見ながらシャドーイング＋録音（ジャンル自由）
        ↓
② uv run yt-dlp --skip-download --write-auto-sub --write-sub \
     --sub-lang en --sub-format vtt \
     -o "shadowing/subs/%(id)s.%(ext)s" <動画URL>
   → 元動画の字幕を取得
        ↓
③ uv run whisper shadowing/recordings/<録音ファイル> \
     --language en --output_format txt \
     --output_dir shadowing/transcripts
   → 自分のシャドーイング音声を文字起こし（ローカルWhisper、オフライン動作）
        ↓
④ ②と③を1ファイルに統合 → shadowing/combined/20260923_shadowing.txt
   （動画タイトル・URL／元スクリプト全文／自分の発話全文）
        ↓
⑤ 統合ファイルをClaudeに送付 → 言えなかった部分・言い換え・重要語句を解説
        ↓
⑥ 気に入った表現だけ既存の /export ルールでAnkiカード化（全件は覚えない）
        ↓
⑦ 分析が終わった録音ファイルは shadowing/recordings/ から
   shadowing/recordings/done/ へ「日付_元ファイル名」の形で移動
   （例: shadowing/recordings/done/20260922_test.m4a）
```

`recordings/` 直下に残っているファイル＝まだ分析していない音声。分析が終わったら `done/` に移動することで、次回以降どれが未処理かひと目でわかるようにする。

使用技術はすべて無料・オフライン中心（yt-dlp / ローカルWhisper）。字幕取得（yt-dlp）はネットワーク制限のないローカルPCで実行する。

### ディレクトリ構成

```
shadowing/
├── recordings/    # 毎朝の録音音声（mp3等）。未処理はここ直下に置く
│   └── done/      # 分析完了した録音（日付_元ファイル名で移動）
├── subs/          # yt-dlpで取得した元動画字幕（vtt）
├── transcripts/   # Whisperの文字起こし結果
└── combined/      # Step④で統合した最終ファイル（Claudeに送付する用）
```

### 必要なツール

`uv add` でプロジェクトの仮想環境（`.venv/`）に導入済み。コマンドは `uv run <ツール名>` の形で実行する。

| ツール | 用途 |
|---|---|
| `yt-dlp` | 元動画の字幕（自動生成字幕含む）取得 |
| `openai-whisper` | 録音音声のローカル文字起こし（初回モデルDL後は完全オフライン） |
| `ffmpeg`（Homebrew） | Whisperの音声デコードに使用 |

---

## リポジトリ構成

```
claude-english-coach/
├── system_prmpt.md        # システムプロンプト本体
├── make_podcast.py        # ポッドキャスト生成スクリプト
├── pyproject.toml         # Python依存関係（uv管理）
├── exports_listening/     # 台本テキスト置き場（.txt）
├── shadowing/             # シャドーイング学習ワークフロー用
│   ├── recordings/        # 録音音声（未処理）
│   │   └── done/          # 分析完了した録音
│   ├── subs/              # 元動画字幕（yt-dlp）
│   ├── transcripts/       # 文字起こし（Whisper）
│   └── combined/          # 統合ファイル（Claudeに送付する用）
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
| 2026年8月 | MODE 4: DRILL MODE（`/drill`）を追加。即英訳の高速アウトプット練習とDRILL HISTORYによる弱点追跡を実装し、`/export`・`/listen`と連携（ミス訂正の読み上げルールを追加） |
| 2026年9月 | シャドーイング学習ワークフローの基盤を追加。`shadowing/`ディレクトリ（recordings/subs/transcripts/combined）を新設し、字幕取得用`yt-dlp`とローカル文字起こし用`openai-whisper`を導入 |

---

## 今後の予定

- [x] シャドーイング学習ワークフローの基盤構築（ディレクトリ・ツール導入）
- [ ] シャドーイング用：字幕取得〜文字起こし〜1ファイル統合の自動化スクリプト化
- [ ] 単語帳モード（頻出単語リストとの連携）
