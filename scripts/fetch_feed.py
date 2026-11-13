#!/usr/bin/env python3
"""Legge il feed RSS di Spreaker e salva tutte le puntate in data/episodes.json.

Uso: python3 scripts/fetch_feed.py
Non serve nessuna chiave. Gira ogni settimana dentro GitHub Actions.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://www.spreaker.com/show/2653847/episodes/feed"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "episodes.json"

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def text_of(el):
    return (el.text or "").strip() if el is not None else ""


def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def slugify(s):
    s = s.lower()
    s = re.sub(r"[àáâä]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:80]


def main():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "dbaf-archivio/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    root = ET.fromstring(raw)
    channel = root.find("channel")

    episodes = []
    for item in channel.findall("item"):
        title = text_of(item.find("title"))
        m = re.match(r"\s*#?(\d+)\s*[-–:.]?\s*(.*)", title)
        number = int(m.group(1)) if m else None
        clean_title = m.group(2).strip() if m and m.group(2) else title
        desc_html = text_of(item.find("content:encoded", NS)) or text_of(item.find("description"))
        img = item.find("itunes:image", NS)
        enc = item.find("enclosure")
        pub = text_of(item.find("pubDate"))
        try:
            date = parsedate_to_datetime(pub).date().isoformat()
        except Exception:
            date = ""
        episodes.append({
            "number": number,
            "title": clean_title,
            "full_title": title,
            "slug": f"{number}-{slugify(clean_title)}" if number else slugify(title),
            "date": date,
            "description_html": desc_html,
            "description": strip_html(desc_html),
            "image": img.get("href") if img is not None else "",
            "audio": enc.get("url") if enc is not None else "",
            "duration": text_of(item.find("itunes:duration", NS)),
            "link": text_of(item.find("link")),
            "guid": text_of(item.find("guid")),
            "keywords": [k.strip() for k in text_of(item.find("itunes:keywords", NS)).split(",") if k.strip()],
        })

    episodes.sort(key=lambda e: (e["date"], e["number"] or 0), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(episodes, ensure_ascii=False, indent=1), encoding="utf-8")
    no_num = [e["full_title"] for e in episodes if e["number"] is None]
    print(f"Puntate nel feed: {len(episodes)}")
    if no_num:
        print(f"Senza numero nel titolo ({len(no_num)}): {no_num[:10]}")


if __name__ == "__main__":
    sys.exit(main())
