"""IEEE-style line-art figures as self-contained SVG."""
import math

FONT = "Times New Roman, Nimbus Roman, serif"
MONO = "DejaVu Sans Mono, monospace"

def svg(w, h, body, vb=None):
    vb = vb or f"0 0 {w} {h}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
            f'width="100%" font-family="{FONT}">'
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="#000"/></marker>'
            f'<marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="none" stroke="#000" stroke-width="1.4"/>'
            f'</marker></defs>{body}</svg>')

def box(x, y, w, h, label, sub=None, fs=11, fill="#fff", dash=None, r=2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
         f'stroke="#000" stroke-width="1.1"{d}/>')
    if sub:
        s += (f'<text x="{x+w/2}" y="{y+h/2-3}" font-size="{fs}" text-anchor="middle">{label}</text>'
              f'<text x="{x+w/2}" y="{y+h/2+11}" font-size="{fs-2}" text-anchor="middle" '
              f'fill="#333">{sub}</text>')
    else:
        s += (f'<text x="{x+w/2}" y="{y+h/2+4}" font-size="{fs}" '
              f'text-anchor="middle">{label}</text>')
    return s

def txt(x, y, s, fs=10, anchor="start", style="", fill="#000", family=None):
    f = f' font-family="{family}"' if family else ""
    return (f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" '
            f'fill="{fill}" {style}{f}>{s}</text>')

def arr(x1, y1, x2, y2, dash=None, open_head=False, w=1.1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = "ao" if open_head else "a"
    return (f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#000" stroke-width="{w}" '
            f'fill="none" marker-end="url(#{m})"{d}/>')

def line(x1, y1, x2, y2, dash=None, w=1.1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#000" stroke-width="{w}" fill="none"{d}/>'

def poly(pts, dash=None, arrow=True, w=1.1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    p = " ".join(f"{x},{y}" for x, y in pts)
    m = ' marker-end="url(#a)"' if arrow else ""
    return f'<polyline points="{p}" stroke="#000" stroke-width="{w}" fill="none"{m}{d}/>'

def cap(x, y, s, fs=9):
    return txt(x, y, s, fs, "middle", 'font-style="italic"')
