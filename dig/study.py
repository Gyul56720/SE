# -*- coding: utf-8 -*-
"""dig/study -- read a topic the way the method says: **five papers, one pattern.**

The method the user handed over (2026-09-21) ends like this:

    "Take one paper you have read, then get several similar ones. Compare five or
     more and **find the issue they all keep naming.** That repetition is the point
     -- it is what lets you say in an interview: it used to be done this way, today
     it is done that way, and here is what is still wrong with it."

The pieces for that already exist in this repo -- `dig/openalex` fetches skeletons
and walks references backwards, `dig/fulltext` gets the body where it is open,
`dig/sections` isolates the introduction and background and pulls the sentences
that state a limitation. This module is the assembly, and it is deliberately
**deterministic**: no model is called anywhere in it.

## Why no model

Three reasons, in order of how much they cost us.

  1. The per-minute quota is this bot's actual bottleneck (that is what the whole
     `rpmgate`/`poolpick` work was about). A study run touches 5-30 papers; routing
     that through an LLM would be the single most expensive thing the bot does.
  2. The same topic must give the same answer twice. A ranked list and a word count
     do; a model does not.
  3. There is nothing here a model is needed for. "Which sentences state a
     limitation" is a cue-word question, and "which limitation repeats across five
     papers" is counting.

A model is useful *after* this runs -- to phrase the paragraph you will say out
loud. That is a separate call the human can make, with the evidence in hand.

## What comes out

    papers    each with evidence level (full | abstract | listing) and its
              limitation sentences
    themes    limitation words ranked by **how many distinct papers** name them
              -- not by raw frequency: one wordy paper must not manufacture a theme
    timeline  the reference walk backwards from the most-cited paper
    unread    the papers whose body we could not open, and why

**The unread list is part of the output, not an error.** A pattern found across
five abstracts is weaker than one found across five introductions, and the reader
has to be able to see which they are holding.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import fulltext as FT       # noqa: E402
from dig import openalex as OA       # noqa: E402
from dig import sections as SEC      # noqa: E402

LEDGER = REPO / "dig" / "study_ledger.jsonl"

# Words that carry no topic information; they would top every theme list.
STOP = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "has",
    "have", "not", "但", "which", "their", "these", "those", "such", "can", "may",
    "our", "its", "it", "but", "however", "while", "when", "where", "than", "then",
    "also", "been", "being", "more", "most", "into", "over", "under", "using", "used",
    "use", "one", "two", "all", "any", "each", "both", "other", "others", "however",
    "paper", "papers", "work", "works", "method", "methods", "approach", "approaches",
    "result", "results", "show", "shows", "shown", "propose", "proposed", "present",
    "presented", "based", "however", "therefore", "thus", "hence", "due", "since",
    # Adverbs that ride along on the cue phrases themselves ("widely used",
    # "typically", "recently proposed") -- they are how the sentence was found, not
    # what it is about, so they would top every list without saying anything.
    "widely", "commonly", "typically", "recently", "generally", "often", "still",
    "usually", "especially", "particularly", "significantly", "considerably",
}
MIN_WORD = 4


def _terms(sentence: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z0-9-]{%d,}" % (MIN_WORD - 1),
                                  (sentence or "").lower())
            if w not in STOP}


def themes(papers: "list[dict]", top: int = 12, field: str = "limitations") -> "list[dict]":
    """Rank words in `field` by **how many distinct papers name them**.

    Counting raw occurrences instead would let a single verbose introduction invent
    a theme by itself -- which is exactly the failure the method warns about when it
    says to read five papers rather than one.

    `field` is one of techniques | limitations | attempts. The method wants all
    three and they answer different questions: what the field leans on now, what is
    wrong with it, and what is being tried instead. Only the middle one was being
    counted before -- that leaves you able to complain but not to say what anyone
    is doing about it.
    """
    per_paper = Counter()
    example = {}
    for p in papers:
        seen = set()
        for s in p.get(field) or []:
            for t in _terms(s):
                seen.add(t)
                example.setdefault(t, (p.get("title", "")[:60], s))
        for t in seen:
            per_paper[t] += 1
    out = []
    for term, n in per_paper.most_common(top * 3):
        if n < 2:                       # named by one paper only -- not a pattern
            continue
        title, sentence = example.get(term, ("", ""))
        out.append({"term": term, "papers": n, "from": title, "sentence": sentence})
        if len(out) >= top:
            break
    return out


def read_paper(p: dict, want_body: bool = True) -> dict:
    """One skeleton -> what we actually managed to read from it."""
    got = FT.get_body(p) if want_body else {
        "text": "", "source": "none", "evidence": "abstract" if p.get("abstract") else "listing",
        "sections": ({"abstract": p["abstract"]} if p.get("abstract") else {}),
        "misses": ["body not requested"], "twin": ""}
    study = SEC.study_text(got["sections"]) or (p.get("abstract") or "")
    return {
        "id": p.get("id", ""), "title": p.get("title", ""), "year": p.get("year"),
        "venue": p.get("venue", ""), "doi": p.get("doi", ""),
        "cited_by": p.get("cited_by", 0), "oa_status": p.get("oa_status", ""),
        "license": p.get("license", ""),
        "evidence": got["evidence"], "source": got["source"], "twin": got["twin"],
        "misses": got["misses"],
        "sections": sorted(got["sections"].keys()),
        "techniques": SEC.technique_sentences(study),
        "limitations": SEC.limitation_sentences(study),
        "attempts": SEC.attempt_sentences(study),
    }


def study(topic: str, n: int = 5, since: "int | None" = None, depth: int = 1,
          want_body: bool = True, open_only: bool = False) -> dict:
    """Run the whole method over one topic.

    n defaults to 5 because the method does: fewer than five and a repeated phrase
    is a coincidence rather than a pattern.
    """
    t0 = time.time()
    found = OA.search(topic, n=n, since=since, open_only=open_only)
    papers = [read_paper(p, want_body=want_body) for p in found]
    walked = {}
    if found:
        try:
            walked = OA.walk_back(found[0]["id"], depth=depth)
        except Exception as e:                                  # noqa: BLE001
            walked = {"error": f"{type(e).__name__}: {e}"[:160]}
    full = [p for p in papers if p["evidence"] == "full"]
    res = {
        "topic": topic, "asked": n, "found": len(papers),
        "read_full": len(full),
        "papers": papers,
        "techniques": themes(papers, field="techniques"),
        "themes": themes(papers, field="limitations"),      # kept name: the problems
        "attempts": themes(papers, field="attempts"),
        "timeline": OA.timeline_text(walked) if walked.get("levels") else "",
        "levels": walked.get("levels") or [],
        "unread": [{"title": p["title"][:70], "why": (p["misses"] or ["?"])[0]}
                   for p in papers if p["evidence"] != "full"],
        "seconds": round(time.time() - t0, 1),
    }
    res["story"] = story(res)
    return res


def _title_terms(papers) -> Counter:
    c = Counter()
    for p in papers or []:
        for t in _terms(p.get("title", "")):
            c[t] += 1
    return c


def story(res: dict) -> "list[dict]":
    """The four beats the method says you should be able to say out loud:

        "it used to be done this way | today it is done that way | the background
         is this | but today's problem is this, so people are trying that"

    **Every beat carries its own evidence and nothing else.** Where we cannot
    measure a beat we say the beat is missing rather than writing a plausible
    sentence -- an interview answer built on an invented contrast is worse than no
    answer, because it sounds right.

    The past/present contrast is measured, not guessed: terms that appear in the
    titles of the old papers the reference walk reached, against terms in the
    titles of the recent papers the search returned. Titles are all we have for the
    old ones (we do not fetch thirty more bodies), and that is stated.
    """
    recent = _title_terms(res.get("papers"))
    old_papers = [p for level in (res.get("levels") or []) for p in level]
    old = _title_terms(old_papers)
    years = [p.get("year") for p in old_papers if p.get("year")]
    beats = []

    gone = [w for w, _ in old.most_common(40) if w not in recent][:6]
    if gone and years:
        beats.append({"beat": "예전에는",
                      "text": ", ".join(gone),
                      "evidence": f"{min(years)}-{max(years)} 참고문헌 {len(old_papers)}편의 "
                                  f"제목에는 있고 지금 {res['found']}편 제목에는 없는 말"})
    else:
        beats.append({"beat": "예전에는", "text": "",
                      "evidence": "참고문헌을 못 받았거나 겹치는 말이 없다 -- 못 잰다"})

    now = [w for w, n in recent.most_common(40) if n >= 2 and w not in old][:6]
    beats.append({"beat": "오늘날에는", "text": ", ".join(now),
                  "evidence": f"지금 {res['found']}편 중 둘 이상의 제목에 있고 옛 논문 제목에는 없는 말"}
                 if now else
                 {"beat": "오늘날에는", "text": "",
                  "evidence": "두 편 이상이 공유하는 새 말이 없다 -- 주제가 좁거나 편수가 적다"})

    prob = res.get("themes") or []
    beats.append({"beat": "하지만 문제는",
                  "text": ", ".join(t["term"] for t in prob[:6]),
                  "evidence": (f"{prob[0]['papers']}편이 같이 말한다: "
                               f"\"{prob[0]['sentence'][:150]}\"") if prob else ""}
                 if prob else
                 {"beat": "하지만 문제는", "text": "",
                  "evidence": "두 편 이상이 같이 말하는 한계가 없다 -- 본문이 덜 열렸을 수 있다"})

    att = res.get("attempts") or []
    beats.append({"beat": "그래서 요즘은",
                  "text": ", ".join(t["term"] for t in att[:6]),
                  "evidence": (f"{att[0]['papers']}편이 같이 말한다: "
                               f"\"{att[0]['sentence'][:150]}\"") if att else ""}
                 if att else
                 {"beat": "그래서 요즘은", "text": "",
                  "evidence": "두 편 이상이 같이 말하는 시도가 없다"})
    return beats


def report(res: dict) -> str:
    """One screen. Every number here was counted, not estimated."""
    out = [f"**{res['topic']}** -- {res['found']} papers, "
           f"**body read for {res['read_full']}** ({res['seconds']}s)"]
    if res["found"] and not res["read_full"]:
        out.append("\n⚠ **Nothing below rests on a body** -- abstracts only. "
                   "A pattern across abstracts is weaker than one across introductions.")
    out.append("\n**Papers** (most cited first)")
    for p in res["papers"]:
        mark = {"full": "■", "abstract": "▨", "listing": "□"}.get(p["evidence"], "?")
        where = f" via {p['source']}" if p["source"] not in ("none", "") else ""
        out.append(f"  {mark} {p['year'] or '????'} · cited {p['cited_by']:>5} · "
                   f"{p['title'][:66]}{where}")
    # The three buckets, in the order the method asks for them: what is used, what
    # is wrong with it, what is being tried. One bucket alone is not a study --
    # naming only the problem leaves you unable to say what the field is doing.
    for key, head in (("techniques", "What the field currently leans on"),
                      ("themes", "What they keep saying is wrong"),
                      ("attempts", "What is being tried about it")):
        rows = res.get(key) or []
        if not rows:
            continue
        out.append(f"\n**{head}** (term -> how many of the papers say it)")
        for t in rows[:8]:
            out.append(f"  · **{t['term']}** -- {t['papers']} papers")
            if t["sentence"]:
                out.append(f"      \"{t['sentence'][:150]}\"")
    if not (res.get("themes") or res.get("attempts")):
        out.append("\n**No shared pattern found.** Either the topic is too broad, "
                   "or too few bodies opened to compare.")

    story_rows = res.get("story") or []
    if story_rows:
        out.append("\n**흐름 -- 이 네 마디가 면접에서 말할 줄거리다**")
        for b in story_rows:
            if b["text"]:
                out.append(f"  **{b['beat']}** {b['text']}")
                out.append(f"      _{b['evidence']}_")
            else:
                # **A missing beat is printed as missing.** An invented contrast
                # sounds right, which is exactly what makes it worse than silence.
                out.append(f"  **{b['beat']}** _못 잼_ -- {b['evidence']}")
    if res["timeline"]:
        out.append("\n**Back through the references**\n```\n" + res["timeline"] + "\n```")
    if res["unread"]:
        out.append("\n**Bodies we could not open** (this is output, not an error)")
        for u in res["unread"]:
            out.append(f"  · {u['title']} -- {u['why'][:90]}")
    out.append("\n_■ full text · ▨ abstract only · □ metadata only_")
    return "\n".join(out)


def record(res: dict, path: "Path | None" = None) -> None:
    """Append one line to the ledger, so a later run can be compared with this one."""
    path = Path(path or LEDGER)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "topic": res["topic"], "found": res["found"], "read_full": res["read_full"],
            "themes": [t["term"] for t in res["themes"]],
            "seconds": res["seconds"],
        }, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="study one topic across several papers")
    ap.add_argument("topic")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--open-only", action="store_true",
                    help="only papers with an open version -- fewer, but readable")
    ap.add_argument("--no-body", action="store_true", help="skeletons only, no fetching")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = study(a.topic, n=a.n, since=a.since, depth=a.depth,
                want_body=not a.no_body, open_only=a.open_only)
    print(json.dumps(res, ensure_ascii=False, indent=2) if a.json else report(res))
    record(res)
    return 0 if res["found"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
