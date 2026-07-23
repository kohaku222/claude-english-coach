#!/usr/bin/env python3
"""
make_podcast.py - 台本テキストからポッドキャスト音声を生成してRSS更新

Usage:
    uv run make_podcast.py <script_file> [--push]

Example:
    uv run make_podcast.py exports_listening/20260723.txt --push
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import edge_tts

EN_VOICE = "en-US-JennyNeural"
JA_VOICE = "ja-JP-NanamiNeural"
BASE_URL = "https://kohaku222.github.io/claude-english-coach"
DOCS_DIR = Path(__file__).parent / "docs"
AUDIO_DIR = DOCS_DIR / "audio"
FEED_PATH = DOCS_DIR / "feed.xml"
PAUSE_SEC = 0.6


def detect_lang(text: str) -> str:
    for ch in text:
        if "぀" <= ch <= "鿿":
            return "ja"
    return "en"


async def line_to_speech(line: str, voice: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(line, voice)
    await communicate.save(output_path)


async def generate_audio(lines: list, output_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        # 行ごとの音声を並列生成
        tasks = []
        tmp_paths = []
        for i, line in enumerate(lines):
            voice = JA_VOICE if detect_lang(line) == "ja" else EN_VOICE
            tmp_path = os.path.join(tmpdir, f"{i:04d}.mp3")
            tmp_paths.append(tmp_path)
            tasks.append(line_to_speech(line, voice, tmp_path))

        print(f"  音声生成中... ({len(tasks)}行、並列実行)")
        await asyncio.gather(*tasks)

        # 0.6秒の無音ファイルを生成
        silence_path = os.path.join(tmpdir, "silence.mp3")
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r=24000:cl=mono",
                "-t", str(PAUSE_SEC),
                "-q:a", "9", "-acodec", "libmp3lame",
                silence_path,
            ],
            check=True, capture_output=True,
        )

        # concatリストを作成（行音声と無音を交互に）
        list_path = os.path.join(tmpdir, "list.txt")
        with open(list_path, "w") as f:
            for tmp_path in tmp_paths:
                f.write(f"file '{tmp_path}'\n")
                f.write(f"file '{silence_path}'\n")

        # ffmpeg で結合
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-c", "copy", str(output_path),
            ],
            check=True, capture_output=True,
        )

        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  音声保存: {output_path} ({size_mb:.1f} MB)")


def update_feed(mp3_path: Path, title: str, pub_date: str) -> None:
    mp3_url = f"{BASE_URL}/audio/{mp3_path.name}"
    mp3_size = mp3_path.stat().st_size

    if FEED_PATH.exists():
        ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        tree = ET.parse(str(FEED_PATH))
        channel = tree.getroot().find("channel")
    else:
        root = ET.Element(
            "rss",
            {"version": "2.0", "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"},
        )
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = "英語学習ポッドキャスト"
        ET.SubElement(channel, "link").text = f"{BASE_URL}/"
        ET.SubElement(channel, "description").text = (
            "Claude.aiとの英語学習セッションから生成したポッドキャスト"
        )
        ET.SubElement(channel, "language").text = "ja"
        tree = ET.ElementTree(root)

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "enclosure", {
        "url": mp3_url,
        "length": str(mp3_size),
        "type": "audio/mpeg",
    })
    ET.SubElement(item, "guid").text = mp3_url
    ET.SubElement(item, "pubDate").text = pub_date

    xml_str = ET.tostring(tree.getroot(), encoding="unicode")
    pretty = xml.dom.minidom.parseString(xml_str).toprettyxml(indent="  ")
    FEED_PATH.write_text(pretty, encoding="utf-8")
    print(f"  RSS更新: {FEED_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="台本テキストからポッドキャスト音声を生成")
    parser.add_argument("script", help="台本テキストファイルのパス")
    parser.add_argument("--push", action="store_true", help="生成後にGitHubへpushする")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"エラー: ファイルが見つかりません: {script_path}", file=sys.stderr)
        sys.exit(1)

    date_str = script_path.stem
    mp3_path = AUDIO_DIR / f"{date_str}.mp3"
    title = f"英語学習 {date_str}"
    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

    raw_lines = script_path.read_text(encoding="utf-8").splitlines()
    lines = [l.strip() for l in raw_lines if l.strip() and not l.strip().startswith("#")]

    if not lines:
        print("エラー: 有効な行がありません", file=sys.stderr)
        sys.exit(1)

    print(f"台本: {script_path.name} ({len(lines)}行)")
    asyncio.run(generate_audio(lines, mp3_path))
    update_feed(mp3_path, title, pub_date)

    if args.push:
        print("  GitHubへpush中...")
        subprocess.run(["git", "add", str(mp3_path), str(FEED_PATH)], check=True)
        subprocess.run(["git", "commit", "-m", f"podcast: {date_str}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"  公開URL: {BASE_URL}/audio/{mp3_path.name}")

    print("完了!")


if __name__ == "__main__":
    main()
