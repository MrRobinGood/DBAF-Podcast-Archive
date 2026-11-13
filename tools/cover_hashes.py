#!/usr/bin/env python3
"""Scarica una miniatura di ogni copertina del feed e calcola un'impronta (average hash 16x16).
Copertine uguali (es. l'immagine generica del podcast) hanno impronte uguali o quasi.
Scrive data/cover_hashes.json. Gira su GitHub (serve internet)."""
import io, json, urllib.request
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
out = {}
for e in eps:
    url = (e["image"] or "").replace("t_rss_itunes_square_1400", "t_square_limited_160")
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dbaf"}), timeout=60).read()
        im = Image.open(io.BytesIO(data)).convert("L").resize((16, 16))
        px = list(im.getdata()); avg = sum(px) / len(px)
        out[str(e["number"])] = "".join("1" if p > avg else "0" for p in px)
    except Exception as ex:
        out[str(e["number"])] = f"error: {ex}"
(ROOT / "data" / "cover_hashes.json").write_text(json.dumps(out, indent=0))
print("fatte", len(out))
