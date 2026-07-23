#!/usr/bin/env python3
"""
make_podcast.py - 台本テキストからポッドキャスト音声を生成してRSS更新

Usage:
    uv run make_podcast.py <script_file> [--push]
    uv run make_podcast.py --rebuild [--push]   # feed.xmlを全件再構築

Example:
    uv run make_podcast.py exports_listening/20260723.txt --push
    uv run make_podcast.py --rebuild --push
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import edge_tts

EN_VOICE = "en-US-JennyNeural"
JA_VOICE = "ja-JP-NanamiNeural"
BASE_URL = "https://kohaku222.github.io/claude-english-coach"
DOCS_DIR = Path(__file__).parent / "docs"
AUDIO_DIR = DOCS_DIR / "audio"
SCRIPTS_DIR = DOCS_DIR / "scripts"
FEED_PATH = DOCS_DIR / "feed.xml"
PAUSE_SEC = 0.6

NS_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
NS_PODCAST = "https://podcastindex.org/namespace/1.0"

ET.register_namespace("itunes", NS_ITUNES)
ET.register_namespace("podcast", NS_PODCAST)


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
        tasks = []
        tmp_paths = []
        for i, line in enumerate(lines):
            voice = JA_VOICE if detect_lang(line) == "ja" else EN_VOICE
            tmp_path = os.path.join(tmpdir, f"{i:04d}.mp3")
            tmp_paths.append(tmp_path)
            tasks.append(line_to_speech(line, voice, tmp_path))

        print(f"  音声生成中... ({len(tasks)}行、並列実行)")
        await asyncio.gather(*tasks)

        silence_path = os.path.join(tmpdir, "silence.mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", str(PAUSE_SEC), "-q:a", "9", "-acodec", "libmp3lame", silence_path],
            check=True, capture_output=True,
        )

        list_path = os.path.join(tmpdir, "list.txt")
        with open(list_path, "w") as f:
            for tmp_path in tmp_paths:
                f.write(f"file '{tmp_path}'\n")
                f.write(f"file '{silence_path}'\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c", "copy", str(output_path)],
            check=True, capture_output=True,
        )

        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  音声保存: {output_path} ({size_mb:.1f} MB)")


def make_channel_root() -> tuple:
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "英語学習ポッドキャスト"
    ET.SubElement(channel, "link").text = f"{BASE_URL}/"
    ET.SubElement(channel, "description").text = "Claude.aiとの英語学習セッションから生成したポッドキャスト"
    ET.SubElement(channel, "language").text = "ja"
    return root, channel


def add_episode(channel: ET.Element, mp3_path: Path, script_name: str, pub_date: str) -> None:
    date_str = mp3_path.stem
    mp3_url = f"{BASE_URL}/audio/{mp3_path.name}"
    transcript_url = f"{BASE_URL}/scripts/{script_name}"

    script_path = SCRIPTS_DIR / script_name
    if script_path.exists():
        description = script_path.read_text(encoding="utf-8")
    else:
        description = f"台本: {transcript_url}"

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"英語学習 {date_str}"
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "enclosure", {
        "url": mp3_url,
        "length": str(mp3_path.stat().st_size),
        "type": "audio/mpeg",
    })
    ET.SubElement(item, "guid").text = mp3_url
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, f"{{{NS_PODCAST}}}transcript", {
        "url": transcript_url,
        "type": "text/plain",
    })


def save_feed(root: ET.Element) -> None:
    xml_str = ET.tostring(root, encoding="unicode")
    pretty = xml.dom.minidom.parseString(xml_str).toprettyxml(indent="  ")
    FEED_PATH.write_text(pretty, encoding="utf-8")
    print(f"  RSS更新: {FEED_PATH}")


def rebuild_feed() -> None:
    """docs/audio/ と docs/scripts/ を照合してfeed.xmlを全件再構築する"""
    root, channel = make_channel_root()

    mp3_files = sorted(AUDIO_DIR.glob("*.mp3"))
    count = 0
    for mp3_path in mp3_files:
        script_name = mp3_path.stem + ".txt"
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            print(f"  スキップ（台本なし）: {mp3_path.name}")
            continue

        mtime = mp3_path.stat().st_mtime
        pub_date = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        add_episode(channel, mp3_path, script_name, pub_date)
        count += 1

    save_feed(root)
    print(f"  再構築完了: {count}エピソード")


def update_feed(mp3_path: Path, script_name: str, pub_date: str) -> None:
    if FEED_PATH.exists():
        tree = ET.parse(str(FEED_PATH))
        root = tree.getroot()
        # namespaceが落ちている場合は再構築
        if "xmlns:podcast" not in root.attrib:
            print("  feed.xml を podcast namespace 対応に再構築します...")
            rebuild_feed()
            return
        channel = root.find("channel")
    else:
        root, channel = make_channel_root()

    add_episode(channel, mp3_path, script_name, pub_date)
    save_feed(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="台本テキストからポッドキャスト音声を生成")
    parser.add_argument("script", nargs="?", help="台本テキストファイルのパス")
    parser.add_argument("--push", action="store_true", help="生成後にGitHubへpushする")
    parser.add_argument("--rebuild", action="store_true", help="feed.xmlを全件再構築する")
    args = parser.parse_args()

    if args.rebuild:
        print("feed.xml を全件再構築中...")
        rebuild_feed()
        if args.push:
            print("  GitHubへpush中...")
            subprocess.run(["git", "add", str(FEED_PATH)], check=True)
            subprocess.run(["git", "commit", "-m", "podcast: rebuild feed with transcript support"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
        print("完了!")
        return

    if not args.script:
        parser.error("script または --rebuild を指定してください")

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"エラー: ファイルが見つかりません: {script_path}", file=sys.stderr)
        sys.exit(1)

    date_str = script_path.stem
    mp3_path = AUDIO_DIR / f"{date_str}.mp3"
    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

    raw_lines = script_path.read_text(encoding="utf-8").splitlines()
    lines = [l.strip() for l in raw_lines if l.strip() and not l.strip().startswith("#")]

    if not lines:
        print("エラー: 有効な行がありません", file=sys.stderr)
        sys.exit(1)

    print(f"台本: {script_path.name} ({len(lines)}行)")
    asyncio.run(generate_audio(lines, mp3_path))

    scripts_dir = DOCS_DIR / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_dest = scripts_dir / script_path.name
    script_dest.write_text(script_path.read_text(encoding="utf-8"), encoding="utf-8")

    update_feed(mp3_path, script_path.name, pub_date)

    if args.push:
        print("  GitHubへpush中...")
        subprocess.run(["git", "add", str(mp3_path), str(FEED_PATH), str(script_dest)], check=True)
        subprocess.run(["git", "commit", "-m", f"podcast: {date_str}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"  音声URL: {BASE_URL}/audio/{mp3_path.name}")
        print(f"  台本URL: {BASE_URL}/scripts/{script_path.name}")

    print("完了!")


if __name__ == "__main__":
    main()
