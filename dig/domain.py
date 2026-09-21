# -*- coding: utf-8 -*-
"""dig/domain -- **say which field you mean before you search.**

Measured 2026-09-21. `dig/study.py "SAR ADC calibration"` came back with:

    · Unmanned aerial systems for photogrammetry and remote sensing: A review
    · Review article: Multisensor image fusion in remote sensing
    · The Role of Millimeter-Wave Technologies in 5G/6G Wireless Communications

**Not one circuit paper.** Two causes compounded.

  1. **The acronym is taken.** In the literature at large, SAR means *synthetic
     aperture radar* far more often than *successive approximation register*. The
     same trap is set for CDR (clock-and-data recovery vs clinical data repository),
     PLL, LDO, DFE, PDK. Our field is a small tenant of these letters.
  2. **Sorting by citations surfaces reviews.** The most-cited thing in any broad
     field is a review article, and a review of the *other* field beats a specific
     paper from ours every time.

Cause 2 is fixed where the sort is chosen (`openalex.search`, relevance by default).
Cause 1 is fixed here, in two steps that are deliberately separate:

    expand()  add the words the acronym stands for, so the query itself is no
              longer ambiguous
    keep()    drop results whose title and abstract contain nothing from the
              field at all -- and **report how many were dropped**, because a
              filter that silently eats everything is worse than no filter

## Why a hand-written list and not a model

A model would answer "what does SAR mean here" correctly most of the time, and
this repo's bottleneck all day has been the per-minute quota. The list is twenty
lines, it is auditable, and it gives the same answer twice. When it is wrong it is
wrong in a way you can read and fix.

This list is **ours** -- it covers the circuits and semiconductor work this repo
does. It is not meant to be general, and `keep()` refuses to filter when it would
remove everything, so an off-domain topic still works.
"""
from __future__ import annotations

import re

# Ambiguous acronym -> the words that pin it to our field. Both go into the query.
EXPAND = {
    "sar adc": "successive approximation register analog-to-digital converter",
    "sar": "successive approximation register",
    "cdr": "clock and data recovery",
    "pll": "phase-locked loop",
    "dll": "delay-locked loop",
    "ldo": "low-dropout regulator",
    "dfe": "decision feedback equalizer",
    "ctle": "continuous time linear equalizer",
    "pdk": "process design kit",
    "dft": "design for test scan",
    "atpg": "automatic test pattern generation",
    "bist": "built-in self test",
    "sta": "static timing analysis",
    "cts": "clock tree synthesis",
    "drc": "design rule check layout",
    "lvs": "layout versus schematic",
    "upf": "unified power format low power",
    "esd": "electrostatic discharge protection circuit",
    "fir": "finite impulse response filter",
    "npu": "neural processing unit accelerator",
}

# Words that say "this is our field". A result containing none of these, anywhere
# in its title or abstract, is almost certainly the other tenant of the acronym.
FIELD_WORDS = (
    "circuit", "circuits", "cmos", "transistor", "vlsi", "asic", "fpga", "soc",
    "analog", "analogue", "mixed-signal", "rtl", "verilog", "systemverilog",
    "silicon", "die", "wafer", "foundry", "nm process", "technology node",
    "adc", "dac", "converter", "amplifier", "comparator", "oscillator",
    "phase-locked", "equalizer", "serdes", "transceiver", "ser/des",
    "semiconductor", "integrated circuit", "chip", "layout", "netlist",
    "synthesis", "timing", "testbench", "scan chain", "capacitor", "capacitive",
    "power consumption", "microwatt", "picojoule", "fj/conv", "enob", "sndr",
    "inl", "dnl", "jitter", "slew", "bandgap", "regulator",
)


def expand(topic: str) -> str:
    """Add the words an ambiguous acronym stands for. Idempotent-ish: if the
    expansion is already in the topic we do not repeat it."""
    t = (topic or "").strip()
    low = t.lower()
    added = []
    for key, words in sorted(EXPAND.items(), key=lambda kv: -len(kv[0])):
        if not re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", low):
            continue
        if words.split()[0] in low:          # already spelled out
            continue
        if any(words in a for a in added):
            continue
        added.append(words)
    return (t + " " + " ".join(added)).strip() if added else t


def in_field(paper: dict) -> bool:
    """Does this result contain any word from our field at all?"""
    blob = f"{paper.get('title', '')} {paper.get('abstract', '')} " \
           f"{paper.get('venue', '')}".lower()
    return any(w in blob for w in FIELD_WORDS)


def keep(papers: "list[dict]", want: int) -> "tuple[list[dict], list[dict]]":
    """Split results into (kept, dropped).

    **Never returns an empty kept list when there were results.** A filter that
    eats everything is worse than no filter: the run would report "no papers" for
    a topic that simply lies outside our vocabulary, and the reader could not tell
    the two apart. When nothing matches we keep everything and let the caller say
    the filter did not apply.
    """
    papers = list(papers or [])
    kept = [p for p in papers if in_field(p)]
    if not kept:
        return papers, []
    dropped = [p for p in papers if p not in kept]
    return kept[:want], dropped
