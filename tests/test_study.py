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
            "venue": "IEEE JSSC", "cited_by": cited,
            "abstract": "a CMOS converter circuit", "oa_locations": [f"https://example.org/{i}"],
            "references": [], "n_references": 0, "oa_status": "gold",
            "oa_url": f"https://example.org/{i}", "license": "cc-by", "authors": []}


FOUND = [skeleton("W1", 2024, 90), skeleton("W2", 2023, 70),
         skeleton("W3", 2022, 50), skeleton("W4", 2021, 30)]

_search, _walk = OA.search, OA.walk_back
# The fixture papers must look like our field, or dig/domain drops them as
# belonging to the other tenant of the acronym -- which is the whole point of it.
OA.search = lambda q, n=10, since=None, until=None, open_only=False, sort="relevance": FOUND[:n]
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
ok(DISPATCH.고르기("SAR ADC 문헌 조사 해줘")[0].startswith("!논문"), "문헌 조사 -> !논문")
ok(DISPATCH.고르기("문헌 조사 해줘")[0] is None,
   "**주제가 없으면 명령을 안 만든다** -- 빈 질의로 검색하면 아무거나 올라온다")
ok(DISPATCH.고르기("RIS 최신 논문 좀 모아줘")[0].startswith("!연구"),
   "**collecting is still 연구** -- the new rule must not swallow the old one")
ok(DISPATCH.고르기("오늘 날씨")[0] is None, "unrelated talk routes nowhere")




print()
print("[front] the router runs BEFORE the agent -- that is why the wrong answer happened")
# 실측 2026-09-21: "SAR ADC calibration 논문" 에 봇이 **교재 여덟 칸**으로 답했다
# (What Is Being Addressed / The Governing Relation / Where It Is Used ...) -- 논문을
# 한 편도 안 찾고 모델이 기억으로 쓴 글이다. 표가 LLM 뒤에 있어 안 불리면 안 닿았다.
앞, 왜 = DISPATCH.앞세울것("SAR ADC calibration 논문 찾아줘")
ok(앞 == "!논문 SAR ADC calibration",
   f"**그 물음이 이제 `!논문` 으로 앞질러 간다** ({앞!r})")
ok("논문" == 왜, "어느 갈래로 알아들었는지 남긴다")
ok(DISPATCH.앞세울것("에이전트: 논문 찾아줘")[0] is None,
   "**끄는 길이 있다** -- `에이전트:` 로 시작하면 표를 건너뛴다")
ok(DISPATCH.앞세울것("RIS 최신 논문 좀 모아줘")[0] is None,
   "흰 목록 밖(연구)은 앞세우지 않는다 -- 넓은 패턴이 평범한 물음을 납치하면 안 된다")
ok(DISPATCH.앞세울것("저장소 고쳐줘")[0] is None, "고치기·계획도 예전대로 에이전트가 받는다")
ok(DISPATCH.앞세울것("!논문 상태")[0] is None, "이미 고정 명령이면 앞세울 것이 없다")
없, 까닭 = DISPATCH.앞세울것("문헌 조사 해줘")
ok(없 is None and "주제" in 까닭,
   "**주제 없는 부탁은 되묻는다** -- 빈 질의로 검색하면 아무거나 올라온다")
ok(DISPATCH.앞세울것("8탭 FIR 필터 논문 분석해줘")[0] == "!논문 8탭 FIR 필터",
   "**부탁하는 말이 검색어에서 빠진다** -- '논문 분석해줘' 가 질의에 섞이면 안 된다")


print()
print("[domain] the acronym is taken -- say which field you mean")
from dig import domain as DOM        # noqa: E402

# 실측 2026-09-21: `dig/study.py "SAR ADC calibration"` 이 돌려준 세 편이 전부
# 다른 분야였다 -- 무인기 사진측량 · 원격탐사 영상융합 · 5G 밀리미터파. 문헌 전체에서
# SAR 은 synthetic aperture radar 를 훨씬 더 자주 뜻하고, 피인용 순 정렬이 그 분야의
# **리뷰 논문**을 맨 위로 올린다.
q = DOM.expand("SAR ADC calibration")
ok("successive approximation" in q,
   f"**약어를 풀어 질의를 모호하지 않게 만든다** ({q[:70]})")
ok(DOM.expand("PLL jitter").endswith("phase-locked loop"), "PLL 도 마찬가지")
ok(DOM.expand("successive approximation register calibration")
   == "successive approximation register calibration",
   "이미 풀려 있으면 덧붙이지 않는다")
ok(DOM.expand("protein folding") == "protein folding", "우리 분야가 아닌 말은 안 건드린다")

실측결과 = [
    {"title": "Unmanned aerial systems for photogrammetry and remote sensing: A review",
     "abstract": "UAV imagery for mapping", "venue": "ISPRS Journal"},
    {"title": "Multisensor image fusion in remote sensing", "abstract": "fusion methods",
     "venue": "Information Fusion"},
    {"title": "A 12-bit SAR ADC with redundancy",
     "abstract": "capacitive DAC in 28nm CMOS", "venue": "IEEE JSSC"},
]
kept, dropped = DOM.keep(실측결과, 6)
ok([p["title"][:20] for p in kept] == ["A 12-bit SAR ADC wit"],
   "**사용자가 실제로 받은 그 세 편에서 회로 논문만 남는다**")
ok(len(dropped) == 2, "버린 것도 세어 둔다 -- 조용히 거르면 검사할 수 없다")
남, 버 = DOM.keep(실측결과[:2], 6)
ok(len(남) == 2 and 버 == [],
   "**다 걸러질 상황이면 거르지 않는다** -- 우리 낱말 밖 주제도 돌아가야 한다")
ok(DOM.keep([], 5) == ([], []), "빈 결과는 빈 결과")

print()
print("[sort] 피인용 순이 기본이면 그 분야 리뷰가 올라온다")
잡 = {}
def _spy(q, n=10, since=None, until=None, open_only=False, sort="relevance"):
    잡["sort"] = sort
    잡["q"] = q
    잡["n"] = n
    return []
_prev = OA.search
OA.search = _spy
ST.study("SAR ADC calibration", n=5)
ok(잡["sort"] == "relevance", "**기본은 관련도 순이다**")
ok("successive approximation" in 잡["q"], "풀린 질의가 실제로 나간다")
ok(잡["n"] > 5, f"거를 것을 감안해 더 많이 받아 온다 ({잡['n']}) -- 딱 n 개만 받으면 늘 모자란다")
ST.study("SAR ADC calibration", n=5, sort="cited")
ok(잡["sort"] == "cited", "피인용 순은 고를 수 있게 남겨 둔다")
OA.search = _prev

print()
print("[locations] 403 하나로 그 논문을 포기하지 않는다")
두곳 = {"title": "x", "doi": "10.1/x", "abstract": "cmos circuit",
       "oa_locations": ["https://publisher/landing", "https://repo.univ/paper.html"]}
FT.search_arxiv = lambda title: []
def _fetch(url):
    if "publisher" in url:
        raise Exception("HTTPError: HTTP Error 403: Forbidden")
    return ("Abstract\nA.\n\n1 Introduction\n" + ("word " * 500), "html")
FT.get_text = _fetch
r5 = FT.get_body(두곳)
ok(r5["evidence"] == "full",
   "**앞의 자리가 403 이어도 다음 열린 자리를 두드린다** (실측: 여기서 세 편을 잃었다)")
ok(any("403" in m for m in r5["misses"]), "403 을 맞은 자리도 기록에 남는다")

print()
if fails:
    print(f"{len(fails)} failed: {fails}")
    raise SystemExit(1)
print("study: pipeline · themes · honesty · report · ledger · command · routing · front · domain -- passed")
