#!/usr/bin/env python3
"""Costruisce il sito pubblico dell'archivio dentro docs/ (servito da GitHub Pages).

Legge:
  data/episodes.json    tutte le puntate (da fetch_feed.py)
  data/categories.json  quattro modi di sfogliare (tema, percorso, serie, epoca),
                        le etichette di ogni puntata e la fila "Inizia da qui"
  data/summaries.json   riassunti brevi per puntata (facoltativo, vincono sulla descrizione)
  config.json           titolo, testi, se mostrare o no le trascrizioni
  transcripts/NNN.md    trascrizioni

Scrive:
  docs/index.html            pagina principale: ricerca, scelta della vista, filtri
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

CUT_MARKERS = [
    "_____", "-----", "Info Utili", "Info utili", "Musica:", "Musica -", "Musica \"", "Diventa sostenitore",
    "Diventa supporter", "Sostieni questo podcast", "Fornisci feedback", "Per feedback", "Feedback, contributi",
    "Chiedi feedback", "Entra in contatto con me", "Diventa membro", "Link alle risorse",
]


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def esc(s):
    return html.escape(str(s or ""), quote=True)


def clean_description(e):
    """L'inizio della descrizione scritta da Robin, senza titolo ripetuto, link e note di servizio."""
    d = e.get("description") or ""
    for m in CUT_MARKERS:
        i = d.find(m)
        if i > 40:
            d = d[:i]
    d = re.sub(r"https?://\S+", "", d)
    d = d.replace("\u2063", " ")
    d = re.sub(r"^\s*Podcast #\d+\s*-[^\n]*?\d/\d\s*\w+\s*", "", d)
    d = re.sub(r"^\s*#?\d*\s*[-–]?\s*", "", d)
    t = re.escape(e["title"].strip(" *"))
    stripped = re.sub(rf"^\W*{t}\W*", "", d, flags=re.I)
    if stripped[:1].isupper() or stripped[:1].isdigit():
        d = stripped
    d = re.sub(r"\*+", "", d)
    d = re.sub(r"\.(\s+\.)+", ".", d)
    d = re.sub(r"\s+", " ", d).strip(" .-·")
    return d + ("." if d and d[-1] not in ".!?…»\"" else "")


def short(text, n=240):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end > n * 0.5:
        return cut[: end + 1]
    return cut.rsplit(" ", 1)[0] + "…"


def fmt_date(iso):
    mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {mesi[int(m) - 1]} {y}"
    except Exception:
        return iso


CSS = """
:root{--bg:#faf8f4;--ink:#1d1b18;--muted:#6d665c;--line:#e4ded3;--accent:#b4410b;--card:#fff;--soft:#f3efe7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,'Iowan Old Style',serif}
a{color:inherit}header.site{padding:44px 20px 18px;max-width:1180px;margin:0 auto}
header.site h1{font:700 clamp(30px,5vw,48px)/1.1 system-ui,-apple-system,sans-serif;margin:0 0 10px;letter-spacing:-.02em}
header.site p{max-width:720px;color:var(--muted);margin:0 0 6px}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 60px}
.start{margin:8px 0 26px}.start h2{font:700 15px system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin:0 0 10px}
.row{display:flex;gap:14px;overflow-x:auto;padding-bottom:8px;scroll-snap-type:x mandatory}
.row .card{min-width:200px;max-width:200px;scroll-snap-align:start}.row .card p{display:none}
.tools{position:sticky;top:0;background:var(--bg);padding:12px 0;z-index:2;border-bottom:1px solid var(--line)}
.tools input{width:100%;padding:12px 14px;font:16px system-ui,sans-serif;border:1px solid var(--line);border-radius:10px;background:#fff}
.views{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;align-items:center}
.views span{font:13px system-ui,sans-serif;color:var(--muted);margin-right:4px}
.view{font:600 13px system-ui,sans-serif;padding:7px 12px;border-radius:8px;border:1px solid transparent;background:none;cursor:pointer;color:var(--muted)}
.view[aria-pressed=true]{background:var(--soft);border-color:var(--line);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{font:600 13px system-ui,sans-serif;padding:7px 12px;border-radius:99px;border:1px solid var(--line);background:#fff;cursor:pointer}
.chip small{font-weight:400;color:var(--muted);margin-left:4px}
.chip[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}.chip[aria-pressed=true] small{color:#ddd}
.opts{font:13px system-ui,sans-serif;color:var(--muted);margin-top:10px;display:flex;gap:16px;flex-wrap:wrap}
.catdesc{font-style:italic;color:var(--muted);margin:12px 0 0}
.count{font:13px system-ui,sans-serif;color:var(--muted);margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none}
.card:hover{border-color:#cdbfa8}
.card img{width:100%;aspect-ratio:1/1;object-fit:cover;background:#eee}
.card .b{padding:14px 16px 16px}
.meta{font:12px system-ui,sans-serif;color:var(--muted);letter-spacing:.02em;text-transform:uppercase}
.card h3{font:700 18px/1.25 system-ui,sans-serif;margin:6px 0 8px}
.card p{margin:0;font-size:15px;color:#3b372f}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{font:11px system-ui,sans-serif;color:var(--accent);border:1px solid #f1c7b0;border-radius:99px;padding:2px 8px;text-decoration:none}
.tag.story{color:#2f5d50;border-color:#b8d4ca}.tag.serie{color:#4b4f9e;border-color:#c9cbee}
article{max-width:760px;margin:0 auto;padding:36px 20px 60px}
article img.cover{width:100%;max-width:420px;border-radius:14px;display:block;margin:18px 0}
article h1{font:700 clamp(26px,4vw,38px)/1.15 system-ui,sans-serif;margin:8px 0}
.btns{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}
.btn{font:600 14px system-ui,sans-serif;padding:10px 14px;border-radius:10px;border:1px solid var(--ink);text-decoration:none}
.btn.p{background:var(--ink);color:#fff}
audio{width:100%;margin:10px 0}
.desc{white-space:pre-line}
.nav{display:flex;justify-content:space-between;gap:12px;margin-top:36px;font:14px system-ui,sans-serif}
details{margin-top:28px;border-top:1px solid var(--line);padding-top:16px}
footer{font:13px system-ui,sans-serif;color:var(--muted);text-align:center;padding:30px 20px}
"""


def page(title, body, desc="", canonical="", image=""):
    og = (f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
          + (f'<meta property="og:image" content="{esc(image)}">' if image else ""))
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">{og}
{f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ''}
<style>{CSS}</style></head><body>{body}</body></html>"""


def main():
    cfg = load(ROOT / "config.json", {})
    eps = load(DATA / "episodes.json", [])
    cats = load(DATA / "categories.json", {"views": [], "assign": {}, "start_here": []})
    sums = load(DATA / "summaries.json", {})
    base_url = cfg.get("base_url", "").rstrip("/")
    views = cats.get("views", [])
    gname = {(v["id"], g["id"]): g["name"] for v in views for g in v["groups"]}
    by_num = {e["number"]: e for e in eps}

    shutil.rmtree(DOCS / "puntate", ignore_errors=True)
    (DOCS / "puntate").mkdir(parents=True, exist_ok=True)
    cards = []
    for e in eps:
        n = str(e["number"])
        a = cats.get("assign", {}).get(n, {})
        summary = sums.get(n) or short(clean_description(e)) or short(e["description"])
        cards.append({
            "n": e["number"], "t": e["title"], "d": e["date"], "s": summary,
            "i": (e["image"] or "").replace("t_rss_itunes_square_1400", "t_square_limited_480"),
            "u": f"puntate/{e['slug']}.html", "k": " ".join(e.get("keywords", [])),
            "g": {v["id"]: a.get(v["id"], []) for v in views}, "st": bool(a.get("storia")),
        })

        tags = "".join(f'<a class="tag" href="../index.html?v=tema&g={esc(t)}">{esc(gname.get(("tema", t), t))}</a>'
                       for t in a.get("tema", []))
        tags += "".join(f'<a class="tag serie" href="../index.html?v=serie&g={esc(s)}">Serie: {esc(gname.get(("serie", s), s))}</a>'
                        for s in a.get("serie", []))
        if a.get("storia"):
            tags += '<span class="tag story">Storia</span>'
        tpath = ROOT / "transcripts" / f"{e['number']:03d}.md"
        tr_block = ""
        if tpath.exists() and cfg.get("show_transcripts"):
            tr_block = f"<details><summary>Trascrizione completa</summary><div class='desc'>{esc(tpath.read_text(encoding='utf-8'))}</div></details>"
        elif tpath.exists() and cfg.get("transcript_request_url"):
            tr_block = (f"<p class='meta' style='margin-top:24px'>Trascrizione disponibile su richiesta: "
                        f"<a href='{esc(cfg['transcript_request_url'])}'>scrivimi</a></p>")
        prev_e, next_e = by_num.get(e["number"] - 1), by_num.get(e["number"] + 1)
        prev_link = (f'<a href="{esc(prev_e["slug"])}.html">← #{prev_e["number"]} {esc(prev_e["title"])}</a>'
                     if prev_e else "")
        next_link = (f'<a href="{esc(next_e["slug"])}.html">#{next_e["number"]} {esc(next_e["title"])} →</a>'
                     if next_e else "")
        nav = f"<div class='nav'><span>{prev_link}</span><span>{next_link}</span></div>"
        body = f"""<article>
<p class="meta"><a href="../index.html">← {esc(cfg.get('title', 'Archivio'))}</a></p>
<p class="meta">Puntata #{esc(n)} · {fmt_date(e['date'])}{(' · ' + esc(e['duration'])) if e.get('duration') else ''}</p>
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
{nav}
</article><footer>{esc(cfg.get('footer', ''))}</footer>"""
        canon = f"{base_url}/puntate/{e['slug']}.html" if base_url else ""
        (DOCS / "puntate" / f"{e['slug']}.html").write_text(
            page(f"#{n} {e['title']} · {cfg.get('show_name', 'da Brand a Friend')}", body, short(summary, 155), canon, e.get("image")),
            encoding="utf-8")

    data_js = json.dumps({
        "eps": cards,
        "views": [{"id": v["id"], "name": v["name"], "groups": [{"id": g["id"], "n": g["name"], "d": g.get("description", "")} for g in v["groups"]]} for v in views],
        "start": cats.get("start_here", []),
    }, ensure_ascii=False).replace("</", "<\\/")
    body = f"""<header class="site"><h1>{esc(cfg.get('title', 'Archivio'))}</h1>
<p>{esc(cfg.get('intro', ''))}</p></header>
<div class="wrap">
<section class="start" id="start"><h2>Inizia da qui</h2><div class="row" id="startrow"></div></section>
<div class="tools">
<input id="q" type="search" placeholder="Cerca per titolo, tema, parola, numero…" aria-label="Cerca">
<div class="views" id="views"><span>Sfoglia:</span></div>
<div class="chips" id="chips"></div>
<div class="opts"><label><input type="checkbox" id="nostory"> Nascondi le storie di vita</label>
<label><input type="checkbox" id="oldfirst"> Dalla prima puntata</label></div>
</div>
<p class="catdesc" id="catdesc"></p><p class="count" id="count"></p><div class="grid" id="grid"></div></div>
<footer>{esc(cfg.get('footer', ''))}</footer>
<script>
const D={data_js};
const MESI=["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];
const fd=s=>{{const[y,m,d]=s.split("-");return d?(+d)+" "+MESI[m-1]+" "+y:s}};
const norm=s=>(s||"").toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");
const P=new URLSearchParams(location.search);
let view=P.get("v")||"tema", grp=P.get("g")||"";
const $=id=>document.getElementById(id), q=$("q");
const byN=Object.fromEntries(D.eps.map(e=>[e.n,e]));
const gname={{}};D.views.forEach(v=>v.groups.forEach(g=>gname[v.id+":"+g.id]=g.n));
function esc(s){{return String(s||"").replace(/[&<>"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]))}}
function card(e){{const tags=(e.g.tema||[]).map(t=>`<span class="tag">${{esc(gname["tema:"+t])}}</span>`).join("")
  +(e.g.serie||[]).map(s=>`<span class="tag serie">${{esc(gname["serie:"+s])}}</span>`).join("")+(e.st?'<span class="tag story">Storia</span>':"");
  return `<a class="card" href="${{e.u}}"><img src="${{esc(e.i)}}" alt="" loading="lazy"><div class="b"><div class="meta">#${{e.n}} · ${{fd(e.d)}}</div>
  <h3>${{esc(e.t)}}</h3><p>${{esc(e.s)}}</p><div class="tags">${{tags}}</div></div></a>`}}
$("startrow").innerHTML=D.start.map(n=>byN[n]).filter(Boolean).map(card).join("");
$("views").insertAdjacentHTML("beforeend",D.views.map(v=>`<button class="view" data-v="${{v.id}}">${{esc(v.name)}}</button>`).join(""));
function chips(){{const v=D.views.find(x=>x.id===view)||D.views[0];
  const cnt=g=>D.eps.filter(e=>(e.g[v.id]||[]).includes(g)).length;
  $("chips").innerHTML='<button class="chip" data-g="">Tutte</button>'+v.groups.map(g=>`<button class="chip" data-g="${{g.id}}">${{esc(g.n)}}<small>${{cnt(g.id)}}</small></button>`).join("");
  document.querySelectorAll(".view").forEach(b=>b.setAttribute("aria-pressed",b.dataset.v===view));}}
function render(){{
  const t=norm(q.value), v=D.views.find(x=>x.id===view);
  let list=D.eps.filter(e=>(!grp||(e.g[view]||[]).includes(grp))&&(!t||norm(e.t+" "+e.s+" "+e.k+" #"+e.n).includes(t))&&!($("nostory").checked&&e.st));
  if($("oldfirst").checked||(view==="serie"&&grp))list=list.slice().sort((a,b)=>a.n-b.n);
  $("count").textContent=list.length+" puntate";
  const g=v&&v.groups.find(x=>x.id===grp); $("catdesc").textContent=g?g.d:"";
  $("start").style.display=(grp||t)?"none":"";
  $("grid").innerHTML=list.map(card).join("");
  document.querySelectorAll(".chip").forEach(b=>b.setAttribute("aria-pressed",b.dataset.g===grp));
  const u=new URLSearchParams();if(view!=="tema")u.set("v",view);if(grp)u.set("g",grp);history.replaceState(null,"",u.toString()?"?"+u:location.pathname);
}}
$("views").onclick=ev=>{{const b=ev.target.closest(".view");if(!b)return;view=b.dataset.v;grp="";chips();render()}};
$("chips").onclick=ev=>{{const b=ev.target.closest(".chip");if(!b)return;grp=b.dataset.g;render()}};
q.oninput=render;$("nostory").onchange=render;$("oldfirst").onchange=render;
chips();render();
</script>"""
    (DOCS / "index.html").write_text(page(cfg.get("title", "Archivio"), body, cfg.get("intro", ""),
                                          base_url + "/" if base_url else ""), encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    if base_url:
        urls = [base_url + "/"] + [f"{base_url}/puntate/{e['slug']}.html" for e in eps]
        (DOCS / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(f"<url><loc>{esc(u)}</loc></url>" for u in urls) + "\n</urlset>\n", encoding="utf-8")
    no_tema = [c["n"] for c in cards if not c["g"].get("tema")]
    print(f"Sito costruito: {len(cards)} puntate. Senza tema: {len(no_tema)}")


if __name__ == "__main__":
    main()
