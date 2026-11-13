#!/usr/bin/env python3
"""Classifica in automatico le puntate nuove che non hanno ancora tema e percorso.

Come funziona: confronta il testo della puntata nuova (titolo, descrizione,
trascrizione) con tutte le puntate gia' classificate a mano, prende le 7 piu'
simili e copia i temi e il percorso che compaiono piu' spesso fra loro.
Le puntate classificate cosi' finiscono nella lista "auto" di data/categories.json,
cosi' si possono ricontrollare.

Uso: python3 scripts/classify_new.py
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "data" / "categories.json"


def text_of(e):
    t = ROOT / "transcripts" / f"{e['number']:03d}.md"
    tx = t.read_text(encoding="utf-8") if t.exists() else ""
    tx = re.sub(r"\*\*[^*]+\*\*\s*\([\d:]+\)|\[[\d:]+\]", " ", tx)
    return f"{e['title']} {e['title']} {e['description']} {tx}".lower()


def main():
    cats = json.loads(CAT.read_text(encoding="utf-8"))
    eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
    assign = cats["assign"]
    auto = set(cats.get("auto", []))
    last_era = cats["views"][3]["groups"][-1]["id"]

    labeled = [e for e in eps if str(e["number"]) in assign and e["number"] not in auto and assign[str(e["number"])]["tema"]]
    new = [e for e in eps if str(e["number"]) not in assign or not assign[str(e["number"])]["tema"]]
    if not new:
        print("Nessuna puntata nuova da classificare.")
        return

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer(max_df=0.3, min_df=2, sublinear_tf=True, token_pattern=r"(?u)\b[a-zàèéìòù]{4,}\b")
    X = vec.fit_transform([text_of(e) for e in labeled + new])
    L, N = X[: len(labeled)], X[len(labeled):]
    sims = cosine_similarity(N, L)
    for i, e in enumerate(new):
        top = sims[i].argsort()[::-1][:7]
        temi, perc = Counter(), Counter()
        for j in top:
            a = assign[str(labeled[j]["number"])]
            for t in a["tema"]:
                temi[t] += sims[i][j]
            for p in a["percorso"]:
                perc[p] += sims[i][j]
        best = [t for t, _ in temi.most_common(2)]
        if len(best) == 2 and temi[best[1]] < 0.6 * temi[best[0]]:
            best = best[:1]
        p = [perc.most_common(1)[0][0]]
        assign[str(e["number"])] = {"tema": best, "percorso": p, "serie": [], "epoca": [last_era],
                                    "storia": "sto" in best or "vita" in p}
        auto.add(e["number"])
        print(f"#{e['number']} {e['title']} -> temi {best}, percorso {p}")

    cats["auto"] = sorted(auto)
    CAT.write_text(json.dumps(cats, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
