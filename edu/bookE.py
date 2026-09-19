# -*- coding: utf-8 -*-
"""English textbook framework."""
import html, json, os, re, subprocess, time
E = html.escape
D = "/home/user/edu"
ZOO = {"ip": "/home/user/ipzoo", "model": "/home/user/modelzoo", "hls": "/home/user/hls_study"}
_zoo = _byrepo = None

def zoo():
    global _zoo, _byrepo
    if _zoo is None:
        _zoo = json.load(open(f"{D}/zoo.json", encoding="utf-8"))
        _byrepo = json.load(open(f"{D}/zoo_by_repo.json", encoding="utf-8"))
    return _zoo, _byrepo

def find(z, sub):
    Z, _ = zoo()
    r = [f for f in Z[z] if sub in f["경로"]]
    if not r:
        raise KeyError(f"{z}: '{sub}' not found")
    return r

def lines(z, sub):
    return sum(f["줄"] for f in find(z, sub))

def read(z, rel):
    return open(os.path.join(ZOO[z], rel), encoding="utf-8", errors="replace").read()

def snip(z, rel, a, b, cap=""):
    L = read(z, rel).splitlines()
    body = "\n".join(f"{a+i:5d}  {l}" for i, l in enumerate(L[a-1:b]))
    head = f'<span class="cap">{E(rel)}:{a}-{b}'
    if cap: head += f"  &mdash; {E(cap)}"
    head += "</span>\n"
    return f'<pre class="code">{head}{E(body)}</pre>'

_fn, _tn, _FIG = [0], [0], None

def fig(svg_or_key, cap):
    global _FIG
    _fn[0] += 1
    if isinstance(svg_or_key, str) and svg_or_key.startswith("<svg"):
        body = svg_or_key
    else:
        if _FIG is None:
            _FIG = {}
            for f in ("figs_a.json", "figs_b.json", "figs_c.json"):
                p = f"/home/user/survey/{f}"
                if os.path.exists(p): _FIG.update(json.load(open(p)))
        body = _FIG.get(str(svg_or_key), "")
    return (f'<figure id="fig{_fn[0]}">{body}'
            f'<figcaption><b>Figure {_fn[0]}.</b> {cap}</figcaption></figure>')

def tab(cap, head, rows):
    _tn[0] += 1
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<table><caption>Table {_tn[0]}. {cap}</caption>'
            f'<thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>')

def toc(body):
    items = re.findall(r'<h([12])[^>]*id="([^"]+)"[^>]*>(.*?)</h[12]>', body, re.S)
    out = []
    for lvl, ident, t in items:
        t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ").strip()
        t = re.sub(r"\s+", " ", t)
        out.append(f'<div class="toc{lvl}"><a href="#{ident}">{t}</a></div>')
    return ('<div class="tocwrap"><h2 style="break-before:auto">Contents</h2>'
            + "\n".join(out) + "</div>")

def cover(num, title, sub, meta):
    return (f'<div class="cover"><div class="docno">{E(num)} &nbsp;&bull;&nbsp; '
            f'{time.strftime("%d %B %Y")}</div>'
            f'<h1 class="ctitle">{E(title)}</h1><div class="csub">{E(sub)}</div>'
            f'<div class="cline"></div><div class="cmeta">{meta}</div></div>')

def render(doc, out, css="/home/user/SE/edu/edu_style.css"):
    from weasyprint import HTML, CSS
    tmp = f"{D}/{os.path.basename(out)}.html"
    open(tmp, "w", encoding="utf-8").write(doc)
    t0 = time.time()
    HTML(filename=tmp).write_pdf(out, stylesheets=[CSS(filename=css)])
    info = subprocess.run(["pdfinfo", out], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", info)
    print(f"{os.path.basename(out)}: {m.group(1) if m else '?'} pages, "
          f"{os.path.getsize(out):,} B, {time.time()-t0:.0f}s")
    return int(m.group(1)) if m else 0
