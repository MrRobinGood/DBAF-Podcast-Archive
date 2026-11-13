#!/usr/bin/env python3
"""Genera data/categories.json dalle assegnazioni scritte a mano (tools/assegnazioni.txt)
piu' le regole automatiche per serie ed epoche.

Quattro modi di sfogliare l'archivio:
  tema      - di cosa parla la puntata (1-2 temi)
  percorso  - a che punto e' chi ascolta
  serie     - le mini-serie (regole per numero)
  epoca     - i capitoli del podcast (per numero)
Piu' l'etichetta "Storia" per le puntate che sono soprattutto racconti di vita,
e la fila "Inizia da qui".

Uso: python3 tools/make_categories.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEMI = [
    ("fid", "Fiducia e credibilità", "Come farsi dare fiducia da chi ancora non ti conosce: credibilità, affidabilità, vicinanza."),
    ("cur", "Curation e fonti fidate", "Scegliere, raccogliere e organizzare il meglio per gli altri. Diventare una fonte a cui si torna."),
    ("cont", "Contenuti di valore e formati", "Cosa pubblicare oltre agli articoli: guide, directory, toolkit, newsradar, tool, calendari."),
    ("scr", "Scrivere e comunicare", "Scrivere chiaro, con la tua voce. Come iniziare un testo, che linguaggio usare, come raccontare."),
    ("soc", "Social media e newsletter", "Facebook, cosa postare, social media manager, newsletter: come usarli senza perderci la faccia."),
    ("pos", "Posizionamento, nicchia e sito web", "Chi sei, per chi lavori, come ti trovano: nicchia, nome, logo, sito, profilo su Google."),
    ("cli", "Clienti e relazioni", "Coltivare relazioni, ascoltare, rispondere, servire bene. Il cliente come un amico."),
    ("ia", "Intelligenza artificiale", "Come lavorare con l'IA senza farsi rimpiazzare: prompt, mini-app, knowledge base, rimanere rilevanti."),
    ("pod", "Podcasting", "Come fare un podcast: strumenti, interviste, strategia, monetizzazione."),
    ("ind", "Imprenditori indipendenti", "Strategie, costanza e scelte per chi vuole vivere della propria competenza."),
    ("sto", "Storie di vita e viaggi", "Holbox, la Thailandia, i set da DJ, la dengue, i visti. Racconti da cui spesso esce una lezione."),
]
PERCORSO = [
    ("parti", "Da dove partire", "Le basi per chi comincia o riparte: cosa fare prima, cosa evitare."),
    ("trov", "Farsi trovare", "Contenuti, social, newsletter e sito per farsi notare dalle persone giuste."),
    ("sceg", "Farsi scegliere", "Quando ti hanno trovato: come diventare la persona di cui fidarsi."),
    ("tieni", "Tenersi i clienti", "Relazioni, assistenza, feedback: come far tornare le persone."),
    ("guad", "Guadagnare con quello che sai", "Modelli, prezzi, storie di chi ce l'ha fatta con la propria competenza."),
    ("ia", "Lavorare con l'IA", "Come usare l'intelligenza artificiale e restare insostituibili."),
    ("vita", "Storie dall'isola", "Racconti di vita, da ascoltare quando vuoi solo compagnia."),
]
SERIE = [
    ("postare", "Cosa Postare sui Social", [50, 51, 52, 53, 54]),
    ("schermo", "Uscire dallo Schermo (tour)", [37, 38, 55]),
    ("posiz19", "Posizionamento e Project Brief", [71, 73, 74, 75, 76, 85]),
    ("logo", "Logo", [77, 78]),
    ("brain", "Brainstorming", [82, 83]),
    ("piano", "Piano dei Contenuti", [43, 86, 87, 88, 89]),
    ("immagini", "Immagini", [91, 92]),
    ("friends", "Storie di Friends", [94, 95]),
    ("spaccano", "Contenuti che Spaccano", list(range(97, 107))),
    ("custserv", "Customer Service", [67, 109, 110]),
    ("podcasting", "Podcasting", list(range(112, 124))),
    ("sino", "Sì o No? (copiare, imitare, prezzi)", [126, 127, 128]),
    ("tendenze", "Tendenze per chi pubblica online", [132, 133]),
    ("leggere", "Scrivere per chi legge online", [135, 136, 137, 138]),
    ("imprenditori", "Storie di piccoli imprenditori", list(range(141, 151))),
    ("futuro", "Strategie per il Futuro", list(range(151, 162))),
    ("cm", "La Miglior Strategia di Content Marketing", [164, 165]),
    ("holbox", "Diario di Holbox", list(range(171, 191))),
    ("newsletter", "Newsletter", list(range(191, 198))),
    ("faccio", "Faccio Faccio Ma...", [203, 204]),
    ("smm", "Social Media Manager", [226, 227, 228, 229]),
    ("ia23", "IA: Prime Riflessioni (2023)", [261, 262, 264, 268]),
    ("dengue", "Dengue", [286, 287, 288, 289]),
    ("knowhow", "Monetizzare il Know-How", [295, 296]),
    ("formula", "La Formula della Fiducia", [221, 299, 300, 301, 302, 303, 304]),
    ("scrfid", "Guadagnare Fiducia Scrivendo", [314, 315]),
    ("sentito", "Per Sentito Dire", [333, 334]),
    ("ricerca", "IA: Ricerca Assistita", [340, 343]),
    ("thai", "Diario dalla Thailandia", [337, 344, 345, 346, 347, 348, 349, 352, 354, 355, 356, 357]),
    ("muaythai", "Muay Thai", [363, 364]),
    ("miniapp", "Una App al Mese e Vibe Coding", [365, 368, 376, 377, 378]),
    ("rilevanti", "Rimanere Rilevanti", [367, 369, 379, 385]),
    ("prompt", "Prompt", [311, 395]),
    ("kb", "Knowledge Base e The Curator", [423, 425, 432, 433, 442]),
    ("liquid", "Liquid Content e Formati", [441, 443]),
    ("tool26", "Tool per la Credibilità (2026)", [444, 445, 446, 447, 449]),
]
EPOCHE = [
    ("e1", "2018–19 · Social e siti per piccole aziende", "Gli inizi: Facebook, siti, contenuti e clienti per piccole attività italiane.", 1, 93),
    ("e2", "2020–21 · Contenuti, podcast e imprenditori", "Contenuti che spaccano, podcasting, storie di imprenditori, strategie per il futuro.", 94, 170),
    ("e3", "2021–24 · Lezioni dall'isola di Holbox", "La vita in Messico, i set da DJ, e il marketing visto dalla spiaggia.", 171, 336),
    ("e4", "2024–25 · Thailandia e primi passi con l'IA", "Il trasloco a Koh Samui, i visti, le prime mini-app fatte con l'IA.", 337, 378),
    ("e5", "2025–26 · Curation e fiducia nell'era dell'IA", "Fonti fidate, knowledge base, tool: come farsi scegliere quando l'IA scrive per tutti.", 379, 10**6),
]
INIZIA = [24, 70, 129, 162, 171, 216, 300, 332, 367, 398]


def main():
    eps = json.loads((ROOT / "data" / "episodes.json").read_text(encoding="utf-8"))
    nums = {e["number"] for e in eps}
    raw = (ROOT / "tools" / "assegnazioni.txt").read_text(encoding="utf-8")
    raw = "\n".join(l for l in raw.splitlines() if not l.startswith("#"))
    manual = {}
    for n, temi, perc in re.findall(r"(\d+):([a-z,]+)/([a-z]+)", raw):
        manual[int(n)] = (temi.split(","), [perc])
    serie_of = {}
    for sid, _, members in SERIE:
        for n in members:
            serie_of.setdefault(n, []).append(sid)

    assign = {}
    for n in sorted(nums):
        temi, perc = manual.get(n, ([], []))
        epoca = [eid for eid, _, _, a, b in EPOCHE if a <= n <= b]
        assign[str(n)] = {
            "tema": temi, "percorso": perc, "serie": serie_of.get(n, []), "epoca": epoca,
            "storia": "sto" in temi or "vita" in perc,
        }
    missing = sorted(nums - set(manual))
    out = {
        "views": [
            {"id": "tema", "name": "Per tema", "groups": [{"id": a, "name": b, "description": c} for a, b, c in TEMI]},
            {"id": "percorso", "name": "Per percorso", "groups": [{"id": a, "name": b, "description": c} for a, b, c in PERCORSO]},
            {"id": "serie", "name": "Per serie", "groups": [{"id": a, "name": b, "description": f"{len(m)} puntate"} for a, b, m in SERIE]},
            {"id": "epoca", "name": "Per epoca", "groups": [{"id": a, "name": b, "description": c} for a, b, c, _, _ in EPOCHE]},
        ],
        "assign": assign,
        "start_here": INIZIA,
        "auto": missing,
    }
    (ROOT / "data" / "categories.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Assegnate a mano: {len(manual)}. Da classificare in automatico: {missing}")


if __name__ == "__main__":
    main()
