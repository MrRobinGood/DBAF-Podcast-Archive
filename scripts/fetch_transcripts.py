#!/usr/bin/env python3
"""Scarica da spoken.md le trascrizioni che ancora mancano in transcripts/.

La chiave arriva dalla variabile SPOKEN_API_KEY (un "secret" di GitHub).
Non va MAI scritta dentro questo repository, che e' pubblico.

Le puntate si abbinano per titolo (e per data se il titolo non basta),
perche' 145 puntate del 2019-2022 non hanno il numero nel titolo.

Uso: SPOKEN_API_KEY=... python3 scripts/fetch_transcripts.py [--max N]
Ogni trascrizione nuova costa 1 credito. Quelle gia' scaricate non si ripagano.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

PODCAST_ID = "1353129143"
BASE = "https://spoken.md"
ROOT = Path(__file__).resolve().parent.parent
TDIR = ROOT / "transcripts"
SOURCES = ROOT / "data" / "transcript_sources.json"
MAP = ROOT / "data" / "spoken_map.json"


def get(path, key):
    req = urllib.request.Request(BASE + path, headers={"x-api-key": key, "User-Agent": "dbaf-archivio/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8"), {k.lower(): v for k, v in r.headers.items()}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^\s*#\d+\s*[-–:.]?\s*", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=5, help="massimo di trascrizioni nuove per giro")
    args = ap.parse_args()
    key = os.environ.get("SPOKEN_API_KEY")
    if not key:
        print("Manca SPOKEN_API_KEY: salto spoken.md.")
        return 0

    eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
    by_title, by_date = {}, {}
    for e in eps:
        by_title.setdefault(norm(e["full_title"]), e["number"])
        by_date.setdefault(e["date"], []).append(e["number"])

    body, _ = get(f"/podcasts/{PODCAST_ID}/episodes", key)
    listing = json.loads(body).get("episodes", [])
    print(f"Puntate con trascrizione su spoken.md: {len(listing)}")

    TDIR.mkdir(exist_ok=True)
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    mapping, unmatched = {}, []
    for ep in listing:
        n = by_title.get(norm(ep.get("title")))
        if n is None:
            d = (ep.get("date") or "")[:10]
            if len(by_date.get(d, [])) == 1:
                n = by_date[d][0]
        if n is None:
            unmatched.append(ep.get("title"))
            continue
        mapping[str(n)] = {"spoken_id": str(ep.get("id")), "title": ep.get("title"), "date": ep.get("date")}

    # dalla piu' recente alla piu' vecchia
    fetched, failed, credits = 0, [], None
    for n in sorted(mapping, key=int, reverse=True):
        out = TDIR / f"{int(n):03d}.md"
        if out.exists() or fetched >= args.max:
            continue
        try:
            text, headers = get(f"/transcripts/{mapping[n]['spoken_id']}", key)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print("Crediti spoken.md finiti. Il resto lo fa Whisper.")
                break
            failed.append((n, e.code))
            continue
        out.write_text(text, encoding="utf-8")
        sources[n] = "spoken.md"
        credits = headers.get("x-credits-remaining", credits)
        fetched += 1
        time.sleep(0.3)

    MAP.write_text(json.dumps(dict(sorted(mapping.items(), key=lambda kv: -int(kv[0]))), ensure_ascii=False, indent=1))
    SOURCES.write_text(json.dumps(dict(sorted(sources.items(), key=lambda kv: -int(kv[0]))), indent=1))
    print(f"Abbinate: {len(mapping)}. Nuove scaricate: {fetched}. Crediti rimasti: {credits}")
    if unmatched:
        print(f"Non abbinate ({len(unmatched)}): {unmatched[:20]}")
    if failed:
        print(f"Errori: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
