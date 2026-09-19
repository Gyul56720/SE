# -*- coding: utf-8 -*-
"""Worked-example engine.

Every number printed by a worked example in this book is *computed here*, at
render time, by running the arithmetic.  Nothing is transcribed from memory.
That is the whole point of this module: the repository's rule is that a number
you cannot recompute is not a measurement, and a textbook that quotes numbers
it cannot recompute is teaching the same bad habit.

Each example carries four mandatory parts:

  given    the data, with units, that the example starts from
  method   the reasoning, written out, not just a formula reference
  numbers  the computed result, produced by real Python arithmetic
  trap     the way this calculation is most often got wrong

The ``trap`` field is not decoration.  Part of the discipline this book teaches
is that a plausible-looking number is the normal failure mode, not an unusual
one, so every worked example states the cheap explanation that has to be ruled
out before the number means anything.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import E, tab, fig

_n = [0]


def num(x, sig=4, unit=""):
    """Format a float with `sig` significant digits, engineering-friendly."""
    if isinstance(x, int):
        s = f"{x:,}"
    elif x == 0:
        s = "0"
    elif abs(x) >= 1e5 or abs(x) < 1e-3:
        m, e = f"{x:.{sig-1}e}".split("e")
        s = f"{m}&times;10<sup>{int(e)}</sup>"
    else:
        s = f"{x:.{max(0, sig - 1 - int(math.floor(math.log10(abs(x)))))}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
    return s + (f"&nbsp;{unit}" if unit else "")


def ex(title, given, method, numbers, trap, extra=""):
    """Render one worked example.

    given/method/trap are HTML strings; `numbers` is a list of
    (label, value_html) pairs or a pre-rendered HTML string.
    """
    _n[0] += 1
    if isinstance(numbers, str):
        nb = numbers
    else:
        nb = ('<table class="wexn"><tbody>' + "".join(
            f"<tr><td>{k}</td><td><b>{v}</b></td></tr>" for k, v in numbers)
            + "</tbody></table>")
    return (f'<div class="wex"><div class="wexh">Worked example {_n[0]}. {title}</div>'
            f'<div class="wexg"><b>Given.</b> {given}</div>'
            f'<div class="wexm"><b>Method.</b> {method}</div>'
            f'{nb}{extra}'
            f'<div class="wext"><b>How this is got wrong.</b> {trap}</div></div>')


def prob(q, sol):
    """A problem with its worked solution, kept adjacent (this is a reference
    text, not an exam paper; hiding the answer would only waste pages)."""
    return (f'<div class="prob"><b>Problem.</b> {q}'
            f'<div class="sol"><b>Solution.</b> {sol}</div></div>')


def derive(title, steps):
    """A derivation: a numbered list of steps, each a (statement, reason) pair.
    Writing the *reason* beside every line is deliberate -- a derivation whose
    steps carry no justification cannot be checked, only believed."""
    rows = "".join(
        f'<tr><td class="dn">{i}</td><td class="dstep">{s}</td>'
        f'<td class="dwhy">{w}</td></tr>'
        for i, (s, w) in enumerate(steps, 1))
    return (f'<div class="deriv"><div class="derh">{title}</div>'
            f'<table class="dtab"><thead><tr><th></th><th>Step</th>'
            f'<th>Justification</th></tr></thead><tbody>{rows}</tbody></table></div>')


def sweep(cap, head, rows, note=""):
    """A table whose rows were computed, with a reminder of what was swept."""
    t = tab(cap, head, rows)
    if note:
        t += f'<div class="swnote">{note}</div>'
    return t


def plot(xs, series, xlabel, ylabel, cap, w=430, h=200, logy=False, logx=False):
    """A small line plot drawn as inline SVG from real data.

    Kept deliberately primitive -- axes, ticks, polylines -- because the plot
    exists to show the *shape* of a computed relationship, and a dependency on
    a plotting library inside the book build is a dependency that can break the
    build for no editorial gain.
    """
    from figs import svg, txt, line
    ml, mr, mt, mb = 52, 12, 10, 34
    pw, ph = w - ml - mr, h - mt - mb
    allv = [v for _, ys in series for v in ys if v is not None]
    if not allv:
        return ""
    def fx(v):
        if logx:
            v = math.log10(max(v, 1e-300))
        return ml + (v - X0) / (X1 - X0) * pw if X1 > X0 else ml
    def fy(v):
        if logy:
            v = math.log10(max(v, 1e-300))
        return mt + ph - (v - Y0) / (Y1 - Y0) * ph if Y1 > Y0 else mt + ph
    xv = [math.log10(max(x, 1e-300)) if logx else x for x in xs]
    yv = [math.log10(max(v, 1e-300)) if logy else v for v in allv]
    X0, X1 = min(xv), max(xv)
    Y0, Y1 = min(yv), max(yv)
    if Y1 == Y0:
        Y1 = Y0 + 1
    pad = (Y1 - Y0) * 0.08
    Y0, Y1 = Y0 - pad, Y1 + pad
    b = [f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="#fff" '
         f'stroke="#000" stroke-width="1"/>']
    for k in range(5):
        yy = mt + ph * k / 4
        val = Y1 - (Y1 - Y0) * k / 4
        lab = f"10<tspan baseline-shift='super' font-size='7'>{val:.0f}</tspan>" if logy \
              else num(val, 3)
        b.append(line(ml, yy, ml + pw, yy, dash="2,3", w=0.4))
        b.append(txt(ml - 5, yy + 3, lab, 8, "end"))
    for k in range(5):
        xx = ml + pw * k / 4
        val = X0 + (X1 - X0) * k / 4
        lab = f"10<tspan baseline-shift='super' font-size='7'>{val:.0f}</tspan>" if logx \
              else num(val, 3)
        b.append(line(xx, mt, xx, mt + ph, dash="2,3", w=0.4))
        b.append(txt(xx, mt + ph + 13, lab, 8, "middle"))
    dashes = [None, "5,3", "2,2", "7,2,2,2", "1,3"]
    for i, (name, ys) in enumerate(series):
        pts = " ".join(f"{fx(x):.1f},{fy(y):.1f}"
                       for x, y in zip(xs, ys) if y is not None)
        d = f' stroke-dasharray="{dashes[i % len(dashes)]}"' if dashes[i % len(dashes)] else ""
        b.append(f'<polyline points="{pts}" fill="none" stroke="#000" '
                 f'stroke-width="1.3"{d}/>')
        yy = mt + 12 + i * 13
        b.append(f'<path d="M{ml+pw-70},{yy-4} l22,0" stroke="#000" '
                 f'stroke-width="1.3"{d}/>')
        b.append(txt(ml + pw - 45, yy, name, 8))
    b.append(txt(ml + pw / 2, h - 3, xlabel, 9, "middle"))
    b.append(f'<text x="12" y="{mt+ph/2}" font-size="9" text-anchor="middle" '
             f'transform="rotate(-90 12 {mt+ph/2})">{ylabel}</text>')
    return fig(svg(w, h, "".join(b)), cap)
