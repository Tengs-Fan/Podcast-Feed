#!/usr/bin/env python3
"""Add an MP3 to this podcast feed and rebuild feed.xml and index.html.

    python3 publish.py episode.mp3 --title "What attention actually computes" --description "One or two sentences."
    python3 publish.py --rebuild          # only regenerate feed.xml / index.html from episodes.json

Then commit and push; GitHub Pages serves the feed at BASE_URL + "feed.xml".
"""
import argparse, json, re, shutil, subprocess, sys
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://tengs-fan.github.io/Podcast-Feed/"
SHOW = {"title": "Audio Overviews",
        "description": "Two-host audio overviews written by Claude and voiced by Gemini, made for personal listening.",
        "author": "AI generated", "language": "en"}


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return int(float(out or 0))


def rebuild(episodes):
    items = []
    for e in sorted(episodes, key=lambda e: e["published"], reverse=True):
        url = BASE_URL + "episodes/" + e["file"]
        pub = format_datetime(datetime.fromisoformat(e["published"]))
        h, rem = divmod(e["seconds"], 3600)
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <description>{escape(e['description'])}</description>
      <enclosure url="{escape(url)}" length="{e['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(e['guid'])}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{h:d}:{rem // 60:02d}:{rem % 60:02d}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(SHOW['title'])}</title>
    <link>{BASE_URL}</link>
    <atom:link href="{BASE_URL}feed.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(SHOW['description'])}</description>
    <language>{SHOW['language']}</language>
    <itunes:author>{escape(SHOW['author'])}</itunes:author>
    <itunes:image href="{BASE_URL}cover.jpg"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>yes</itunes:block>
    <itunes:category text="Education"/>
    <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")
    rows = "\n".join(
        f'<li><b>{escape(e["title"])}</b> <span>{e["published"][:10]} · {e["seconds"] // 60}:{e["seconds"] % 60:02d}</span>'
        f'<p>{escape(e["description"])}</p><audio controls preload="none" src="episodes/{escape(e["file"])}"></audio></li>'
        for e in sorted(episodes, key=lambda e: e["published"], reverse=True))
    (ROOT / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{escape(SHOW['title'])}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 16px;color:#222;background:#fafafa}}
li{{list-style:none;margin:1.5rem 0;padding-bottom:1rem;border-bottom:1px solid #ddd}}ul{{padding:0}}span{{color:#777;font-size:.85em}}
audio{{width:100%}}code{{background:#eee;padding:2px 6px;border-radius:4px;word-break:break-all}}
@media(prefers-color-scheme:dark){{body{{background:#161616;color:#eee}}code{{background:#333}}li{{border-color:#333}}}}</style></head>
<body><h1>{escape(SHOW['title'])}</h1><p>{escape(SHOW['description'])}</p>
<p>Subscribe in a podcast app with this address:<br><code>{BASE_URL}feed.xml</code></p><ul>
{rows}
</ul></body></html>
""", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp3", nargs="?")
    ap.add_argument("--title")
    ap.add_argument("--description", default="")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    manifest = ROOT / "episodes.json"
    episodes = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    if not a.rebuild:
        if not a.mp3 or not a.title:
            sys.exit("Usage: publish.py episode.mp3 --title '...' [--description '...']")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:60] or "episode"
        name = f"{now:%Y-%m-%d}-{slug}.mp3"
        dest = ROOT / "episodes" / name
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(a.mp3, dest)
        episodes = [e for e in episodes if e["file"] != name]  # re-publishing the same title on the same day replaces it
        episodes.append({"title": a.title, "description": a.description or a.title, "file": name,
                         "bytes": dest.stat().st_size, "seconds": duration(dest),
                         "published": now.isoformat(), "guid": f"{name}-{dest.stat().st_size}"})
        manifest.write_text(json.dumps(episodes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Added {name} ({dest.stat().st_size / 1e6:.1f} MB)")
    rebuild(episodes)
    print(f"Feed has {len(episodes)} episode(s): {BASE_URL}feed.xml")


if __name__ == "__main__":
    main()
