# -*- coding: utf-8 -*-
"""**Did we read the body, and if not, do we say so?**

The user, 2026-09-21: "most papers, the body text just could not be read."
That sentence is what this test is about.

Runs with no network -- the fetch seams are injected. (This container cannot reach
the outside; the real counts get measured on the VM.)

Run: python3 tests/test_paper_reading.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import fulltext as FT        # noqa: E402
from dig import openalex as OA        # noqa: E402
from dig import sections as SEC       # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        fails.append(label)


BODY = """Abstract
We present a data-driven flow.

I. INTRODUCTION
Analog design is hard. However, existing methods cannot handle the amount of data
produced by modern simulation flows, which limits prediction accuracy in practice.

II. BACKGROUND AND MOTIVATION
Prior flows relied on SPICE sweeps. This is expensive and does not scale to large designs.

III. PROPOSED METHOD
We do X. """ + ("x " * 900) + """

V. CONCLUSION
Done.

REFERENCES
[1] someone
"""

print("[split] headings come in every shape -- do we catch them")
sec = SEC.split(BODY)
for key in ("abstract", "introduction", "background", "method", "conclusion", "references"):
    ok(key in sec, f"found {key}")
ok(len(sec.get("head", "")) < 5, "junk before the first heading does not leak into a section")

print()
print("[headings] roman, arabic, bare")
ok(SEC.heading_of("I. INTRODUCTION") == "introduction", "I. INTRODUCTION")
ok(SEC.heading_of("1 Introduction") == "introduction", "1 Introduction")
ok(SEC.heading_of("Introduction") == "introduction", "bare Introduction")
ok(SEC.heading_of("2.1 Background") == "background", "2.1 Background")
ok(SEC.heading_of("III. RELATED WORK") == "related", "III. RELATED WORK")
ok(SEC.heading_of("II. BACKGROUND AND MOTIVATION") == "background",
   "**'BACKGROUND AND MOTIVATION' is background too** -- literal matching misses half")
ok(SEC.heading_of(
    "In this introduction we argue that the proposed flow beats all prior art.") == "",
   "**a sentence containing 'introduction' is not a heading** -- it would split here")

print()
print("[absent] we do not invent sections that are not there")
thin = SEC.split("Abstract\nA.\n\n1 Introduction\nB.\n\n2 Method\nC.\n")
ok("background" not in thin, "no Background section -> no background key")
ok(SEC.study_text(thin).strip() != "", "abstract + introduction still come out")

print()
print("[limits] pull the sentences that state a problem -- raw material for the pattern")
lim = SEC.limitation_sentences(SEC.study_text(sec))
ok(any("cannot handle" in s for s in lim), "however/cannot is caught")
ok(any("does not scale" in s for s in lim), "does not scale is caught")
ok(all(40 <= len(s) <= 400 for s in lim), "fragments and whole pages are skipped")

print()
print("[abstract] OpenAlex ships an inverted index -- put it back in order")
ok(OA.unroll_abstract({"We": [0], "measure": [1], "slack": [2]}) == "We measure slack",
   "restored by position")
ok(OA.unroll_abstract(None) == "", "no abstract -> empty, never invented")
holed = OA.unroll_abstract({"A": [0], "C": [2]})
ok("A" in holed and "C" in holed, "a hole does not destroy the words we do have")

print()
print("[skeleton] one work -> our shape")
p = OA.work({
    "id": "https://openalex.org/W123", "title": "A 12-bit SAR ADC",
    "publication_year": 2021, "doi": "https://doi.org/10.1109/JSSC.2021.1",
    "cited_by_count": 42,
    "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"],
    "open_access": {"oa_status": "closed"},
    "primary_location": {"source": {"display_name": "IEEE JSSC"}},
})
ok(p["doi"] == "10.1109/JSSC.2021.1", "doi loses its URL wrapper")
ok(p["references"] == ["W1", "W2"] and p["n_references"] == 2, "reference ids only")
ok(p["venue"] == "IEEE JSSC", "IEEE papers are in OpenAlex too -- that is the point")
ok(p["abstract"] == "", "no abstract shipped -> empty string")

print()
print("[walk] **oldest first** -- the method's main lever")
fixture = {
    "W0": {"id": "W0", "title": "seed", "year": 2024, "cited_by": 10,
           "references": ["W1", "W2", "W3"], "n_references": 3},
    "W1": {"id": "W1", "title": "old-big", "year": 1999, "cited_by": 900,
           "references": [], "n_references": 0},
    "W2": {"id": "W2", "title": "mid", "year": 2012, "cited_by": 50,
           "references": [], "n_references": 0},
    "W3": {"id": "W3", "title": "new", "year": 2023, "cited_by": 5,
           "references": [], "n_references": 0},
}
_one, _many = OA.fetch_one, OA.fetch_many
OA.fetch_one = lambda ref: fixture["W0"]
OA.fetch_many = lambda ids, n=50: [fixture[i] for i in ids if i in fixture][:n]
walked = OA.walk_back("W0", depth=1, per_level=3)
years = [x["year"] for x in walked["levels"][0]]
ok(years == sorted(years), f"a level arrives **oldest first** ({years})")
ok(years[0] == 1999, "the oldest leads -- newest-first would circle the same neighbourhood")
line = OA.timeline_text(walked)
ok("level 1 back" in line and "1999" in line, "the walk prints as one screen")
OA.fetch_one, OA.fetch_many = _one, _many

print()
print("[body] knock on each open door in turn")
closed = {"title": "A 12-bit SAR ADC with calibration", "doi": "10.1109/JSSC.2021.1",
          "oa_url": "", "abstract": "We present a 12-bit SAR ADC."}
FT.search_arxiv = lambda title: []
r = FT.get_body(closed)
ok(r["evidence"] == "abstract",
   "**no body -> evidence is 'abstract'**, never 'full'")
ok(r["source"] == "none" and r["misses"], f"and we say why ({r['misses'][:1]})")

print()
print("[twin] find the preprint, but never attach the wrong paper")
ok(FT.title_overlap("A 12-bit SAR ADC with calibration",
                    "A 12-bit SAR ADC with background calibration") >= FT.TWIN_MIN_OVERLAP,
   "a real preprint has nearly the same title")
ok(FT.title_overlap("A 12-bit SAR ADC", "Deep learning for protein folding") < 0.3,
   "**the wrong paper's body would make every later sentence false**")
FT.search_arxiv = lambda title: [("Deep learning for protein folding", "2101.00001")]
r2 = FT.get_body(closed)
ok(r2["evidence"] == "abstract", "a non-overlapping arXiv hit is refused")
ok(any("overlaps" in m for m in r2["misses"]), "and the refusal is recorded")

print()
print("[oa] a landing page is not a body")
open_ = {"title": "X", "doi": "10.1/x", "oa_url": "https://example.org/p.html",
         "abstract": "ab"}
FT.get_text = lambda url: ("short blurb", "html")
FT.search_arxiv = lambda title: []
r3 = FT.get_body(open_)
ok(r3["evidence"] != "full",
   f"**under {FT.BODY_MIN_CHARS} chars is not a body** -- we only got the landing page")
FT.get_text = lambda url: ("Abstract\nA.\n\n1 Introduction\n" + ("word " * 500), "html")
r4 = FT.get_body(open_)
ok(r4["evidence"] == "full" and r4["source"] == "oa", "long enough -> accepted as the body")
ok("introduction" in r4["sections"], "and it is split into sections immediately")

print()
if fails:
    print(f"{len(fails)} failed: {fails}")
    raise SystemExit(1)
print("paper reading: split · limits · skeleton · walk · body · twin -- passed")
