#!/usr/bin/env python3
"""Scarica da spoken.md le trascrizioni che ancora mancano in transcripts/.

La chiave arriva dalla variabile SPOKEN_API_KEY (un "secret" di GitHub).
Non va MAI scritta dentro questo repository, che e' pubblico.

Uso: SPOKEN_API_KEY=... python3 scripts/fetch_transcripts.py [--max N]
Ogni trascrizione nuova costa 1 credito. Quelle gia' scaricate non si ripagano.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PODCAST_ID = "1353129143"
BASE = "https://spoken.md"
ROOT = Path(__file__).resolve().parent.parent
TDIR = ROOT / "transcripts"
MAP = ROOT / "data" / "spoken_map.json"


def get(path, key):
    req = urllib.request.Request(BASE + path, headers={"x-api-key": key, "User-Agent": "dbaf-archivio/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8"), dict(r.headers)


def number_of(title):
    m = re.match(r"\s*#?(\d+)", title or "")
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=60, help="massimo di trascrizioni nuove per giro")
    args = ap.parse_args()
    key = os.environ.get("SPOKEN_API_KEY")
    if not key:
        print("Manca SPOKEN_API_KEY: salto le trascrizioni.")
        return 0

    body, _ = get(f"/podcasts/{PODCAST_ID}/episodes", key)
    listing = json.loads(body).get("episodes", [])
    print(f"Puntate con trascrizione su spoken.md: {len(listing)}")

    TDIR.mkdir(exist_ok=True)
    mapping = json.loads(MAP.read_text()) if MAP.exists() else {}
    fetched, missing, credits = 0, [], None
    for ep in listing:
        n = number_of(ep.get("title"))
        if n is None:
            continue
        mapping[str(n)] = {"spoken_id": str(ep.get("id")), "title": ep.get("title"), "date": ep.get("date")}
        out = TDIR / f"{n:03d}.md"
        if out.exists():
            continue
        if fetched >= args.max:
            continue
        try:
            text, headers = get(f"/transcripts/{ep['id']}", key)
        except urllib.error.HTTPError as e:
            if e.code == 402:
                print("Crediti finiti. Mi fermo qui.")
                break
            missing.append((n, e.code))
            continue
        out.write_text(text, encoding="utf-8")
        credits = headers.get("X-Credits-Remaining") or headers.get("x-credits-remaining")
        fetched += 1
        time.sleep(0.5)

    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps(dict(sorted(mapping.items(), key=lambda kv: -int(kv[0]))), ensure_ascii=False, indent=1))
    print(f"Trascrizioni nuove scaricate: {fetched}. Crediti rimasti: {credits}")
    if missing:
        print(f"Non disponibili: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
