#!/usr/bin/env python3
"""Fogli di provini: tutte le copertine del feed per le puntate senza covers/NNN.jpg.
Scrive tmp-provini/sheet-N.jpg (solo per controllo, poi si cancella). Gira su GitHub."""
import io, json, os, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent.parent
eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
local = {int(f[:3]) for f in os.listdir(ROOT / "docs" / "covers") if f[:3].isdigit()}
todo = [e for e in eps if e["number"] not in local]
out = ROOT / "tmp-provini"; out.mkdir(exist_ok=True)
T, COLS, ROWS = 150, 8, 8
for s in range(0, len(todo), COLS * ROWS):
    chunk = todo[s:s + COLS * ROWS]
    sheet = Image.new("RGB", (COLS * T, ROWS * (T + 18)), "white"); d = ImageDraw.Draw(sheet)
    for i, e in enumerate(chunk):
        x, y = (i % COLS) * T, (i // COLS) * (T + 18)
        url = (e["image"] or "").replace("t_rss_itunes_square_1400", "t_square_limited_160")
        try:
            im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dbaf"}), timeout=60).read())).convert("RGB").resize((T, T))
            sheet.paste(im, (x, y))
        except Exception:
            d.rectangle([x, y, x + T, y + T], outline="red")
        d.text((x + 4, y + T + 3), f"#{e['number']}", fill="black")
    sheet.save(out / f"sheet-{s // (COLS * ROWS) + 1}.jpg", quality=85)
print(len(todo), "copertine")
