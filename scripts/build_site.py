#!/usr/bin/env python3
"""Costruisce il sito pubblico dell'archivio dentro docs/ (servito da GitHub Pages).

Legge:
  data/episodes.json    tutte le puntate (da fetch_feed.py)
  data/categories.json  le categorie e quali puntate vanno dove (scritto a mano o con Claude)
  data/summaries.json   riassunti brevi per puntata (facoltativo)
  config.json           titolo, testi, se mostrare o no le trascrizioni
  transcripts/NNN.md    trascrizioni (da fetch_transcripts.py)

Scrive:
  docs/index.html            pagina principale con ricerca e filtri per categoria
  docs/puntate/<slug>.html   una pagina per ogni puntata
  docs/sitemap.xml
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def esc(s):
    return html.escape(s or "", quote=True)


def short(text, n=260):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut + "…"


def fmt_date(iso):
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {mesi[int(m) - 1]} {y}"
    except Exception:
        return iso


CSS = """
:root{--bg:#faf8f4;--ink:#1d1b18;--muted:#6d665c;--line:#e4ded3;--accent:#c2410c;--card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,'Iowan Old Style',serif}
a{color:inherit}header.site{padding:48px 20px 24px;max-width:1180px;margin:0 auto}
header.site h1{font:700 clamp(30px,5vw,48px)/1.1 system-ui,-apple-system,sans-serif;margin:0 0 10px;letter-spacing:-.02em}
header.site p{max-width:720px;color:var(--muted);margin:0 0 6px}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 60px}
.tools{position:sticky;top:0;background:var(--bg);padding:14px 0;z-index:2;border-bottom:1px solid var(--line)}
.tools input{width:100%;padding:12px 14px;font:16px system-ui,sans-serif;border:1px solid var(--line);border-radius:10px;background:#fff}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{font:600 13px system-ui,sans-serif;padding:7px 12px;border-radius:99px;border:1px solid var(--line);background:#fff;cursor:pointer}
.chip[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
.count{font:13px system-ui,sans-serif;color:var(--muted);margin:14px 0}
.catdesc{font-style:italic;color:var(--muted);margin:4px 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none}
.card img{width:100%;aspect-ratio:1/1;object-fit:cover;background:#eee}
.card .b{padding:14px 16px 16px}
.meta{font:12px system-ui,sans-serif;color:var(--muted);letter-spacing:.02em;text-transform:uppercase}
.card h3{font:700 18px/1.25 system-ui,sans-serif;margin:6px 0 8px}
.card p{margin:0;font-size:15px;color:#3b372f}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{font:11px system-ui,sans-serif;color:var(--accent);border:1px solid #f1c7b0;border-radius:99px;padding:2px 8px}
article{max-width:760px;margin:0 auto;padding:36px 20px 60px}
article img.cover{width:100%;max-width:420px;border-radius:14px;display:block;margin:18px 0}
article h1{font:700 clamp(26px,4vw,38px)/1.15 system-ui,sans-serif;margin:8px 0}
.btns{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.btn{font:600 14px system-ui,sans-serif;padding:10px 14px;border-radius:10px;border:1px solid var(--ink);text-decoration:none}
.btn.p{background:var(--ink);color:#fff}
audio{width:100%;margin:10px 0}
.desc{white-space:pre-line}
details{margin-top:28px;border-top:1px solid var(--line);padding-top:16px}
footer{font:13px system-ui,sans-serif;color:var(--muted);text-align:center;padding:30px 20px}
"""


def page(title, body, desc="", canonical=""):
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ''}
<style>{CSS}</style></head><body>{body}</body></html>"""


def main():
    cfg = load(ROOT / "config.json", {})
    eps = load(DATA / "episodes.json", [])
    cats = load(DATA / "categories.json", {"categories": [], "assign": {}})
    sums = load(DATA / "summaries.json", {})
    base_url = cfg.get("base_url", "").rstrip("/")
    cat_by_id = {c["id"]: c for c in cats.get("categories", [])}

    shutil.rmtree(DOCS / "puntate", ignore_errors=True)
    (DOCS / "puntate").mkdir(parents=True, exist_ok=True)
    cards = []
    for e in eps:
        n = str(e.get("number") or "")
        e_cats = [c for c in cats.get("assign", {}).get(n, []) if c in cat_by_id]
        summary = sums.get(n) or short(e["description"])
        has_tr = (ROOT / "transcripts" / f"{int(n):03d}.md").exists() if n else False
        cards.append({
            "n": e.get("number"), "t": e["title"], "d": e["date"], "s": summary,
            "i": e["image"], "u": f"puntate/{e['slug']}.html", "c": e_cats,
            "k": " ".join(e.get("keywords", [])),
        })

        tags = "".join(f'<span class="tag">{esc(cat_by_id[c]["name"])}</span>' for c in e_cats)
        tr_block = ""
        if has_tr and cfg.get("show_transcripts"):
            tr = (ROOT / "transcripts" / f"{int(n):03d}.md").read_text(encoding="utf-8")
            tr_block = f"<details><summary>Trascrizione completa</summary><div class='desc'>{esc(tr)}</div></details>"
        elif has_tr and cfg.get("transcript_request_url"):
            tr_block = (f"<p class='meta' style='margin-top:24px'>Trascrizione disponibile su richiesta: "
                        f"<a href='{esc(cfg['transcript_request_url'])}'>scrivimi</a></p>")
        body = f"""<article>
<p class="meta"><a href="../index.html">← {esc(cfg.get('title', 'Archivio'))}</a></p>
<p class="meta">Puntata #{esc(n)} · {fmt_date(e['date'])} {('· ' + esc(e['duration'])) if e.get('duration') else ''}</p>
<h1>{esc(e['title'])}</h1>
<div class="tags">{tags}</div>
{f'<img class="cover" src="{esc(e["image"])}" alt="Copertina della puntata {esc(n)}" loading="lazy">' if e.get('image') else ''}
{f'<audio controls preload="none" src="{esc(e["audio"])}"></audio>' if e.get('audio') else ''}
<div class="btns">
  {f'<a class="btn p" href="{esc(e["link"])}">Ascolta su Spreaker</a>' if e.get('link') else ''}
  {''.join(f'<a class="btn" href="{esc(u)}">{esc(l)}</a>' for l, u in cfg.get('listen_links', {}).items())}
</div>
{f'<p><strong>{esc(sums[n])}</strong></p>' if n in sums else ''}
<div class="desc">{esc(e['description'])}</div>
{tr_block}
</article><footer>{esc(cfg.get('footer', ''))}</footer>"""
        canon = f"{base_url}/puntate/{e['slug']}.html" if base_url else ""
        (DOCS / "puntate" / f"{e['slug']}.html").write_text(
            page(f"#{n} {e['title']} · {cfg.get('show_name', 'da Brand a Friend')}", body, short(summary, 155), canon),
            encoding="utf-8")

    chips = '<button class="chip" data-c="" aria-pressed="true">Tutte</button>' + "".join(
        f'<button class="chip" data-c="{esc(c["id"])}" aria-pressed="false">{esc(c["name"])}</button>'
        for c in cats.get("categories", []))
    data_js = json.dumps({"eps": cards, "cats": {c["id"]: {"n": c["name"], "d": c.get("description", "")}
                                                  for c in cats.get("categories", [])}},
                         ensure_ascii=False).replace("</", "<\\/")
    body = f"""<header class="site"><h1>{esc(cfg.get('title', 'Archivio'))}</h1>
<p>{esc(cfg.get('intro', ''))}</p></header>
<div class="wrap"><div class="tools">
<input id="q" type="search" placeholder="Cerca per titolo, tema, parola…" aria-label="Cerca">
<div class="chips" id="chips">{chips}</div></div>
<p class="catdesc" id="catdesc"></p><p class="count" id="count"></p><div class="grid" id="grid"></div></div>
<footer>{esc(cfg.get('footer', ''))}</footer>
<script>
const D={data_js};
const MESI=["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];
const fd=s=>{{const[y,m,d]=s.split("-");return d?(+d)+" "+MESI[m-1]+" "+y:s}};
const norm=s=>(s||"").toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");
let cat=new URLSearchParams(location.search).get("c")||"";
const q=document.getElementById("q"),grid=document.getElementById("grid");
function esc(s){{return (s||"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]))}}
function render(){{
  const t=norm(q.value);
  const list=D.eps.filter(e=>(!cat||e.c.includes(cat))&&(!t||norm(e.t+" "+e.s+" "+e.k+" #"+e.n).includes(t)));
  document.getElementById("count").textContent=list.length+" puntate";
  document.getElementById("catdesc").textContent=cat&&D.cats[cat]?D.cats[cat].d:"";
  grid.innerHTML=list.map(e=>`<a class="card" href="${{e.u}}"><img src="${{esc(e.i)}}" alt="" loading="lazy">
   <div class="b"><div class="meta">#${{e.n}} · ${{fd(e.d)}}</div><h3>${{esc(e.t)}}</h3><p>${{esc(e.s)}}</p>
   <div class="tags">${{e.c.map(c=>`<span class="tag">${{esc(D.cats[c].n)}}</span>`).join("")}}</div></div></a>`).join("");
  document.querySelectorAll(".chip").forEach(b=>b.setAttribute("aria-pressed",b.dataset.c===cat));
}}
document.getElementById("chips").onclick=ev=>{{const b=ev.target.closest(".chip");if(!b)return;cat=b.dataset.c;
  history.replaceState(null,"",cat?"?c="+cat:location.pathname);render()}};
q.oninput=render;render();
</script>"""
    (DOCS / "index.html").write_text(page(cfg.get("title", "Archivio"), body, cfg.get("intro", ""),
                                          base_url + "/" if base_url else ""), encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    if base_url:
        urls = [base_url + "/"] + [f"{base_url}/puntate/{e['slug']}.html" for e in eps]
        (DOCS / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(f"<url><loc>{esc(u)}</loc></url>" for u in urls) + "\n</urlset>\n", encoding="utf-8")
    unassigned = [c["n"] for c in cards if not c["c"]]
    print(f"Sito costruito: {len(cards)} puntate. Senza categoria: {len(unassigned)}")


if __name__ == "__main__":
    main()
