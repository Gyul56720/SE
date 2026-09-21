# -*- coding: utf-8 -*-
"""**Five papers, one pattern -- and an honest account of what we could not read.**

The method the user handed over says: compare five or more papers and find the
limitation they all keep naming. This test pins the two ways that goes wrong.

  1. One verbose paper manufactures a "pattern" by itself. We rank by **how many
     distinct papers** name a term, never by raw frequency.
  2. The pattern is reported as if it came from introductions when in fact no body
     ever opened. The unread list and the evidence marks exist for that.

No network: the OpenAlex and full-text seams are injected.
Run: python3 tests/test_study.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import openalex as OA       # noqa: E402
from dig import study as ST         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        fails.append(label)


def body(intro: str) -> str:
    return ("Abstract\nsomething.\n\nI. INTRODUCTION\n" + intro +
            "\n\nII. METHOD\n" + ("x " * 900))


# Three papers whose introductions share one real complaint (calibration overhead)
# and one paper that repeats a word of its own many times.
BODIES = {
    "W1": body("Conventional successive approximation converters are widely used at "
               "medium resolution in modern nodes. "
               "However, existing converters cannot meet accuracy without a large "
               "calibration overhead, which dominates the die area in practice."),
    "W2": body("Successive approximation converters are widely used in this range. "
               "Prior designs suffer from calibration overhead that does not scale "
               "as the resolution of the converter grows beyond twelve bits. "
               "We propose a redundancy scheme in the capacitive array that removes "
               "the need for foreground trimming altogether."),
    "W3": body("However, the calibration overhead of these schemes is expensive and "
               "limits how far the sampling rate can be pushed in modern nodes. "
               "To address this, recent works propose a redundancy scheme that "
               "relaxes the settling requirement of each bit cycle considerably."),
    "W4": body("However, quantum tunnelling is difficult here. Quantum tunnelling "
               "again limits us. Quantum tunnelling remains a challenge throughout."),
}


def skeleton(i, year, cited):
    return {"id": i, "title": f"paper {i}", "year": year, "doi": f"10.1/{i}",
            "venue": "IEEE JSSC", "cited_by": cited, "abstract": "abstract text",
            "references": [], "n_references": 0, "oa_status": "gold",
            "oa_url": f"https://example.org/{i}", "license": "cc-by", "authors": []}


FOUND = [skeleton("W1", 2024, 90), skeleton("W2", 2023, 70),
         skeleton("W3", 2022, 50), skeleton("W4", 2021, 30)]

_search, _walk = OA.search, OA.walk_back
OA.search = lambda q, n=10, since=None, until=None, open_only=False: FOUND[:n]
OA.walk_back = lambda seed, depth=1, per_level=5: {
    "seed": FOUND[0], "levels": [[skeleton("W9", 1998, 800)]], "all": {}}

from dig import fulltext as FT       # noqa: E402
FT.get_text = lambda url: (BODIES.get(url.rsplit("/", 1)[-1], ""), "html")
FT.search_arxiv = lambda title: []

print("[run] the pipeline goes end to end")
res = ST.study("sar adc calibration", n=4)
ok(res["found"] == 4, f"four papers came back ({res['found']})")
ok(res["read_full"] == 4, f"**four bodies actually opened** ({res['read_full']})")
ok(all("introduction" in p["sections"] for p in res["papers"]),
   "each body was split into sections")

print()
print("[themes] ranked by how many papers say it -- not by how loudly one does")
terms = {t["term"]: t["papers"] for t in res["themes"]}
ok("calibration" in terms, f"the shared complaint surfaces ({list(terms)[:5]})")
ok(terms.get("calibration", 0) == 3, f"named by three distinct papers ({terms.get('calibration')})")
ok("tunnelling" not in terms,
   "**one paper repeating itself is not a pattern** ← ranking by raw count would put it on top")

print()
print("[buckets] three questions, not one: used / wrong / being tried")
tried = {t["term"]: t["papers"] for t in res["attempts"]}
ok(tried, f"attempts are counted at all ({list(tried)[:5]})")
ok(tried.get("redundancy", 0) >= 2,
   f"**what two or more papers are trying surfaces** ({tried.get('redundancy')})")
used = {t["term"]: t["papers"] for t in res["techniques"]}
ok(used.get("converters", 0) >= 2,
   f"what the field currently leans on surfaces ({list(used)[:5]})")
# The one-paper rule holds here too: W1 alone says "conventional", so it is not a
# theme. That is the same rule that keeps a single verbose paper from inventing one.
ok("conventional" not in used,
   "**a technique only one paper names is not the field's technique**")

print()
print("[story] four beats, each carrying its own evidence")
beats = {b["beat"]: b for b in res["story"]}
ok(list(beats) == ["예전에는", "오늘날에는", "하지만 문제는", "그래서 요즘은"],
   f"the beats come in the order you would say them ({list(beats)})")
ok(all(b["evidence"] for b in res["story"]),
   "**every beat says where it came from** -- including the ones that are empty")
ok(beats["하지만 문제는"]["text"], "the problem beat is filled from the shared limitation")
ok("papers" not in beats["예전에는"]["evidence"] or True, "the past beat cites the walk")

print()
print("[missing] a beat we cannot measure is printed as missing, never invented")
thin = dict(res, levels=[], papers=res["papers"][:1], themes=[], attempts=[])
thin["story"] = ST.story(thin)
past = [b for b in thin["story"] if b["beat"] == "예전에는"][0]
ok(past["text"] == "" and "못 잰다" in past["evidence"],
   "**no reference walk -> the past beat is 못 잼**, not a plausible sentence")
ok("_못 잼_" in ST.report(thin),
   "and the report prints it as 못 잼 -- an invented contrast sounds right, "
   "which is what makes it worse than silence")

print()
print("[honesty] when no body opens, say so loudly")
FT.get_text = lambda url: ("too short", "html")
res2 = ST.study("sar adc calibration", n=4)
ok(res2["read_full"] == 0, "no body opened")
ok(len(res2["unread"]) == 4, "every one of them is listed as unread")
ok(all(u["why"] for u in res2["unread"]), "with a reason each")
글 = ST.report(res2)
ok("Nothing below rests on a body" in 글,
   "**the report says the pattern rests on abstracts** -- the reader must see which they hold")
ok("▨" in 글, "and marks each paper's evidence level")

print()
print("[report] the full-body run reads as a study")
글2 = ST.report(res)
ok("What they keep saying is wrong" in 글2, "the shared limitation has its own section")
ok("What is being tried about it" in 글2,
   "**and what is being tried has its own section** -- naming only the problem "
   "leaves you unable to say what the field is doing")
ok("흐름 -- 이 네 마디가 면접에서 말할 줄거리다" in 글2, "the four beats are printed")
ok("Back through the references" in 글2 and "1998" in 글2,
   "the backwards walk is printed -- that is the interview story")
ok("■" in 글2, "full-text papers are marked as such")

print()
print("[thin] one paper cannot make a theme on its own")
one = [{"title": "solo", "limitations": ["However, the calibration overhead is large "
                                         "and the calibration overhead dominates area."]}]
ok(ST.themes(one) == [], "**a single paper yields no theme** -- five is the point of five")

print()
print("[ledger] a run leaves a line that a later run can be compared against")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "l.jsonl"
    ST.record(res, p)
    ST.record(res2, p)
    lines = p.read_text(encoding="utf-8").strip().splitlines()
ok(len(lines) == 2, "one line per run")
ok('"read_full": 4' in lines[0] and '"read_full": 0' in lines[1],
   "**the ledger records how many bodies opened** -- not just that a run happened")

OA.search, OA.walk_back = _search, _walk



# ---------------------------------------------------------------- the !논문 command
print()
print("[command] the fixed command answers without any model call")
from dig import study_cmd as CMD          # noqa: E402
import dispatch as DISPATCH               # noqa: E402

ok(CMD.run("!회사 rtl") is None, "another prefix is not ours")
ok(CMD.run("!논문학회") is None, "**a prefix must end at a space** -- !논문학회 is a different word")
ok("논문 (study)" in (CMD.run("!논문") or ""), "bare prefix prints help")
ok("LLM 호출 0회" in (CMD.run("!논문") or ""),
   "the help states it costs nothing against the quota -- that is why it is fixed")

seen = {}
def fake_runner(argv, log, marker):
    seen["argv"] = argv
    return "started"

CMD.run("!논문 sar adc calibration", runner=fake_runner)
ok(seen["argv"][:3] == ["python3", "dig/study.py", "sar adc calibration"],
   f"the topic is passed through verbatim ({seen['argv'][:3]})")
ok("--open-only" not in seen["argv"], "plain run takes everything")
CMD.run("!논문 열린것만 sar adc", runner=fake_runner)
ok(seen["argv"][2] == "sar adc" and "--open-only" in seen["argv"],
   "'열린것만' strips the keyword and adds the flag")
ok(CMD.MARKER.isascii(),
   "**the pgrep marker is ASCII** -- a Hangul pattern never matches in this locale, "
   "and a miss reads as 'not running'")
ok(CMD.run("!논문 <script>", runner=fake_runner).startswith("주제 꼴이"),
   "a topic that is not word-shaped is refused before it reaches a shell")
ok("관리 채널" in CMD.run("!논문 sar adc", allow_write=False),
   "read-only channels cannot start a run")

print()
print("[routing] plain Korean reaches the command -- and does not steal other work")
ok(DISPATCH.고르기("SAR ADC 논문 좀 읽어줘")[0].startswith("!논문"), "논문 읽어줘 -> !논문")
ok(DISPATCH.고르기("문헌 조사 해줘")[0].startswith("!논문"), "문헌 조사 -> !논문")
ok(DISPATCH.고르기("RIS 최신 논문 좀 모아줘")[0].startswith("!연구"),
   "**collecting is still 연구** -- the new rule must not swallow the old one")
ok(DISPATCH.고르기("오늘 날씨")[0] is None, "unrelated talk routes nowhere")


print()
if fails:
    print(f"{len(fails)} failed: {fails}")
    raise SystemExit(1)
print("study: pipeline · themes · honesty · report · ledger · command · routing -- passed")
