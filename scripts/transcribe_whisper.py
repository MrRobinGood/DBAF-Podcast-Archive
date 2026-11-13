#!/usr/bin/env python3
"""Trascrive con Whisper (gratis, sui computer di GitHub) le puntate che non hanno
ancora una trascrizione in transcripts/.

Uso:
  python3 scripts/transcribe_whisper.py --limit 2            # le piu' recenti senza testo
  python3 scripts/transcribe_whisper.py --shard 3 --shards 20 # una fetta dell'arretrato
  python3 scripts/transcribe_whisper.py --numbers 52 53 54

Serve: pip install faster-whisper
"""
import argparse
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TDIR = ROOT / "transcripts"
SOURCES = ROOT / "data" / "transcript_sources.json"
MODEL = "medium"


def ts(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--numbers", type=int, nargs="*")
    ap.add_argument("--out", default=str(TDIR))
    args = ap.parse_args()

    eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
    todo = [e for e in eps if e.get("audio") and not (TDIR / f"{e['number']:03d}.md").exists()]
    if args.numbers:
        todo = [e for e in eps if e["number"] in set(args.numbers)]
    todo.sort(key=lambda e: -e["number"])
    todo = [e for i, e in enumerate(todo) if i % args.shards == args.shard]
    if args.limit:
        todo = todo[: args.limit]
    print(f"Da trascrivere in questo giro: {[e['number'] for e in todo]}")
    if not todo:
        return 0

    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}

    for e in todo:
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            req = urllib.request.Request(e["audio"], headers={"User-Agent": "dbaf-archivio/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                f.write(r.read())
            f.flush()
            segments, _ = model.transcribe(f.name, language="it", vad_filter=True, beam_size=5)
            paras, cur, start = [], [], None
            for s in segments:
                if start is None:
                    start = s.start
                cur.append(s.text.strip())
                if s.end - start > 60 and s.text.strip().endswith((".", "?", "!")):
                    paras.append(f"[{ts(start)}] " + " ".join(cur))
                    cur, start = [], None
            if cur:
                paras.append(f"[{ts(start or 0)}] " + " ".join(cur))
        text = (f"# #{e['number']} - {e['title']}\n\n"
                f"da Brand a Friend · {e['date']} · trascrizione automatica (Whisper {MODEL})\n\n"
                + "\n\n".join(paras) + "\n")
        (out_dir / f"{e['number']:03d}.md").write_text(text, encoding="utf-8")
        if out_dir == TDIR:
            sources[str(e["number"])] = f"whisper-{MODEL}"
        print(f"Fatta #{e['number']} ({len(text)} caratteri)")

    if out_dir == TDIR:
        SOURCES.parent.mkdir(exist_ok=True)
        SOURCES.write_text(json.dumps(dict(sorted(sources.items(), key=lambda kv: -int(kv[0]))), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
