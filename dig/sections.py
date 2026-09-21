# -*- coding: utf-8 -*-
"""dig/sections -- split one paper's text into **sections**.

The user's method (2026-09-21), from the video they sent:

    "What we actually want to study is not the body -- it is the **Introduction and
     Background**. Those two sections tell you which techniques are hot right now,
     what is wrong with them, and what people are trying instead. Find that pattern
     across five or more papers."

But `dig/paper.py` hands back the body as **one blob**. There was no way to ask for
the introduction alone. That is what this module fixes.

## Why this is fiddly

Section headings are not written the same way twice:

    I. INTRODUCTION          (IEEE: roman numeral, all caps)
    1 Introduction           (numbered, normal case)
    1.1 Background
    II. RELATED WORK
    Introduction             (no number at all)
    3  BACKGROUND AND MOTIVATION

**Matching the literal string "Introduction" misses half of them.** So we match the
number prefix and the name separately, and the name against a bag of words. Anything
we cannot classify stays in `body` -- we never file an unknown chunk under
"introduction" just to have one.

## What this deliberately does not do

It does not ask a model to judge what a paragraph means. This is a *string shape*
problem; using a model would burn the per-minute quota and lose reproducibility
(the same paper must split the same way every time).
"""
from __future__ import annotations

import re

# Section key -> words that name it. First match wins, so order matters.
SECTION_WORDS = [
    ("abstract", ("abstract", "초록", "요약")),
    ("introduction", ("introduction", "서론", "개요")),
    ("background", ("background", "preliminaries", "preliminary", "배경", "기초")),
    ("related", ("related work", "related works", "prior work", "previous work",
                 "literature review", "관련 연구", "선행 연구")),
    ("method", ("method", "methodology", "proposed", "approach", "architecture",
                "design", "implementation", "system", "제안", "방법")),
    ("results", ("experiment", "evaluation", "result", "measurement", "measured",
                 "discussion", "실험", "결과", "측정")),
    ("conclusion", ("conclusion", "concluding", "summary", "future work", "결론")),
    ("references", ("references", "reference", "bibliography", "참고문헌")),
    ("ack", ("acknowledgment", "acknowledgement", "acknowledgments", "감사")),
]

# A heading line: an optional number prefix (roman or arabic, dotted) then the name.
_NUM = r"(?:(?:[IVXLC]+|\d+(?:\.\d+)*)[.)]?\s+)?"
_HEADING = re.compile(rf"^\s*{_NUM}([A-Za-z가-힣][A-Za-z가-힣 \-&/,]{{2,60}})\s*:?\s*$")

# Sections worth reading first, in the order the method prescribes.
STUDY_ORDER = ("abstract", "introduction", "background", "related")


def looks_like_heading(line: str) -> bool:
    """Headings are short. If we accept a long line, a sentence that merely contains
    the word "introduction" starts a bogus section and everything after it is
    filed wrong.

    **Careful with the name of this function.** It was first called `not길이맞나`,
    and Python read `not` as *part of the identifier* (a keyword is not broken by a
    following Hangul letter), so `if not길이맞나(line)` became a call instead of a
    negation. The whole judgement inverted, nothing split, and there was no syntax
    error to notice. Never glue an ASCII keyword to a non-ASCII identifier.
    """
    n = len(line.strip())
    return 3 <= n <= 80


def _classify(name: str) -> str:
    t = (name or "").strip().lower()
    if not t:
        return ""
    for key, words in SECTION_WORDS:
        for w in words:
            # "introduction" must match as a whole word; "BACKGROUND AND MOTIVATION"
            # must still resolve to background.
            if t == w or t.startswith(w + " ") or t.endswith(" " + w) or f" {w} " in f" {t} ":
                return key
    return ""


def heading_of(line: str) -> str:
    """Return the section key if this line is a heading, else ""."""
    line = (line or "").rstrip()
    if not looks_like_heading(line):
        return ""
    m = _HEADING.match(line)
    return _classify(m.group(1)) if m else ""


def split(text: str) -> dict:
    """text -> {section_key: text}. Whatever precedes the first heading is `head`.

    **Absent sections stay absent.** Plenty of papers have no Background section
    (the video says so too) -- we do not invent an empty one.
    """
    current = "head"
    bucket = {current: []}
    order = [current]
    for line in (text or "").splitlines():
        key = heading_of(line)
        if key:
            current = key
            if current not in bucket:
                bucket[current] = []
                order.append(current)
            continue
        bucket[current].append(line)
    out = {}
    for k in order:
        body = "\n".join(bucket[k]).strip()
        if body:
            out[k] = body
    return out


def study_text(sections: dict) -> str:
    """The part the method says to actually read: abstract + intro + background
    (+ related work)."""
    return "\n\n".join(s for s in (sections.get(k, "") for k in STUDY_ORDER) if s).strip()


# Cues for a sentence that states a limitation. The video: "what was wrong before,
# and why a new approach is needed".
LIMIT_CUES = (
    "however", "but ", "limitation", "limited", "bottleneck", "drawback", "challenge",
    "difficult", "infeasible", "intractable", "cannot", "fail to", "suffer", "degrade",
    "overhead", "expensive", "does not scale", "do not scale", "lack of",
    "한계", "문제", "어렵", "불가능", "병목",
)


def limitation_sentences(text: str, limit: int = 12) -> "list[str]":
    """Pick the sentences that state a limitation.

    This is the raw material for comparing papers: when five introductions keep
    naming the same limitation, that repetition *is* the pattern the method is
    after. Selection is done on strings -- no model call.
    """
    out = []
    for raw in re.split(r"(?<=[.!?])\s+|\n{2,}", text or ""):
        s = " ".join(raw.split())
        if not (40 <= len(s) <= 400):
            continue
        low = s.lower()
        if any(c in low for c in LIMIT_CUES):
            out.append(s)
        if len(out) >= limit:
            break
    return out
