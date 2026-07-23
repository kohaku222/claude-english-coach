# claude-english-coach プロジェクト

## このリポジトリについて

Claude.ai との英語学習セッションを Anki カードとポッドキャスト音声に変換する個人学習システム。

## よく行う作業

### リスニング音声の生成・push

`exports_listening/` に `.txt` ファイルが追加されたら、以下を実行して音声化・push する：

```bash
uv run make_podcast.py exports_listening/<ファイル名>.txt --push
```

- 英語行 → en-US-JennyNeural（ネイティブ英語音声）
- 日本語行 → ja-JP-NanamiNeural（日本語音声）
- Unicode 自動判別のためタグ不要
- 実行すると `docs/audio/` に mp3、`docs/feed.xml` が更新されて GitHub に push される
- Overcast（RSS: `https://kohaku222.github.io/claude-english-coach/feed.xml`）に自動配信される

### system_prmpt.md の更新・push

変更内容を読んで意図を汲んだコミットメッセージを作成して push する。

### Anki CSV の exports/ への追加

必要に応じてコミット・push する。

## フォルダ構成

```
exports_listening/   台本テキスト（.txt）置き場
exports/             Anki CSV 置き場
docs/audio/          生成済み mp3
docs/feed.xml        RSS フィード（自動更新）
make_podcast.py      音声生成スクリプト
system_prmpt.md      Claude.ai に渡すシステムプロンプト
```

## 台本フォーマットの注意点

- 1行1発話
- 日本語と英語を同じ行に混ぜない
- `#` で始まる行は読み上げスキップ（セクション見出し用）
- 空行はスキップ（可読性のために自由に使ってよい）
