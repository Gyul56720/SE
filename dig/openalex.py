# -*- coding: utf-8 -*-
"""dig/openalex -- get a paper's **skeleton** (metadata, references, open full-text
location) with no API key.

Why this exists. The method the user handed over says:

    title -> abstract -> **introduction & background** -> (body only if needed)
    -> **walk the references backwards in time** -> five or more papers -> pattern

This repo had `dig/paper.py`, which downloads **one arXiv paper**. Two things were
missing: papers outside arXiv, and **a way to walk references into the past**.
Both are solved here.

## Why we do not scrape IEEE Xplore

Its full text is for subscribers. Logging in with the user's university account to
scrape it breaks the terms of use, and it is *their* account that gets suspended.
Instead:

  · **Metadata and references** come free from OpenAlex (IEEE papers land there via
    Crossref like everyone else).
  · **Full text** is read only where it is open -- an OA version, an arXiv preprint
    of the same paper, PMC.
  · What we cannot read, we **say we cannot read**. If we only got the abstract we
    record "abstract" as the evidence level (see `paper/출처.jsonl`). We never
    pretend otherwise.

## An email address here is politeness, not a key

OpenAlex and Unpaywall put callers who pass `mailto=` in a faster pool. It is not
a login -- it just says who is calling. Set `OPENALEX_MAILTO`; without it we simply
call anonymously.

Usage:
    python3 dig/openalex.py --search "data driven analog circuit design" --since 2023
    python3 dig/openalex.py --back 10.1109/JSSC.2020.1234567 --depth 2
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

API = "https://api.openalex.org"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
TIMEOUT = float(os.environ.get("OPENALEX_TIMEOUT", "30"))

# **Test seam.** Swap this and the module runs with no network -- this container
# cannot reach the outside (proxy policy), so tests run on fixtures and the real
# counts get measured on the VM.
get_json = None


def _call(path: str, **params) -> dict:
    if MAILTO:
        params.setdefault("mailto", MAILTO)
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    if get_json is not None:
        return get_json(url)
    req = urllib.request.Request(url, headers={"User-Agent": "SE-agent (dig/openalex)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:       # noqa: S310
        return json.loads(r.read().decode("utf-8", "replace"))


def unroll_abstract(inverted) -> str:
    """OpenAlex ships abstracts as an **inverted index** (word -> positions), for
    copyright reasons. Put it back in order; leave holes empty rather than guess."""
    if not inverted:
        return ""
    slot = {}
    for word, spots in inverted.items():
        for i in spots or []:
            slot[i] = word
    if not slot:
        return ""
    return " ".join(slot.get(i, "") for i in range(max(slot) + 1)).strip()


def _oa_locations(w: dict) -> "list[str]":
    urls = []
    for loc in (w.get("locations") or []):
        if not loc.get("is_oa"):
            continue
        for key in ("pdf_url", "landing_page_url"):
            u = loc.get(key)
            if u and u not in urls:
                urls.append(u)
    best = w.get("best_oa_location") or {}
    for key in ("pdf_url", "landing_page_url"):
        u = best.get(key)
        if u and u not in urls:
            urls.insert(0, u)
    return urls


def work(w: dict) -> dict:
    """One OpenAlex work -> our shape. **Missing fields stay missing.**"""
    loc = w.get("primary_location") or {}
    best = w.get("best_oa_location") or {}
    oa = w.get("open_access") or {}
    return {
        "id": (w.get("id") or "").rsplit("/", 1)[-1],
        "title": w.get("title") or w.get("display_name") or "",
        "year": w.get("publication_year"),
        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
        "venue": (loc.get("source") or {}).get("display_name") or "",
        "type": w.get("type") or "",
        "cited_by": int(w.get("cited_by_count") or 0),
        "abstract": unroll_abstract(w.get("abstract_inverted_index")),
        "references": [x.rsplit("/", 1)[-1] for x in (w.get("referenced_works") or [])],
        "n_references": len(w.get("referenced_works") or []),
        "oa_status": oa.get("oa_status") or "unknown",
        "oa_url": oa.get("oa_url") or best.get("pdf_url") or best.get("landing_page_url") or "",
        # **Every open location, not just the best one.** A publisher landing page
        # often answers 403 to anything that is not a browser, while the same paper
        # sits readable in an institutional repository or on arXiv. Using one
        # location threw those away (measured 2026-09-21: three papers lost to
        # "HTTP Error 403" with other locations never tried). pdf first -- a pdf is
        # a body, a landing page usually is not.
        "oa_locations": _oa_locations(w),
        "license": best.get("license") or loc.get("license") or "",
        "authors": [(a.get("author") or {}).get("display_name", "")
                    for a in (w.get("authorships") or [])][:12],
    }


def search(query: str, n: int = 10, since: "int | None" = None,
           until: "int | None" = None, open_only: bool = False,
           sort: str = "relevance") -> "list[dict]":
    """Search by topic. **Relevance first, citations only on request.**

    It started the other way round and that was wrong (measured 2026-09-21).
    Asking for "SAR ADC calibration" with `cited_by_count:desc` returned
    photogrammetry from unmanned aerial systems, multisensor image fusion in remote
    sensing, and millimetre-wave 5G -- **not one circuit paper.** Two things
    compounded:

      · In the literature at large, SAR means *synthetic aperture radar* far more
        often than *successive approximation register*.
      · Sorting a broad field by citations surfaces its review articles, which are
        the most-cited things in any field and the least specific.

    So relevance is the default. `sort="cited"` is still there, and it is the right
    choice once the query is already unambiguous.
    """
    filters = []
    if since:
        filters.append(f"from_publication_date:{int(since)}-01-01")
    if until:
        filters.append(f"to_publication_date:{int(until)}-12-31")
    if open_only:
        filters.append("is_oa:true")
    params = {"search": query, "per_page": max(1, min(int(n), 50))}
    if sort == "cited":
        params["sort"] = "cited_by_count:desc"
    # Relevance is OpenAlex's own default when `search` is present, so we send no
    # sort at all rather than guessing the name of its relevance key.
    if filters:
        params["filter"] = ",".join(filters)
    return [work(w) for w in (_call("works", **params).get("results") or [])]


def fetch_one(ref: str) -> dict:
    """Fetch one paper by DOI, OpenAlex id, or arXiv id."""
    t = (ref or "").strip()
    if t.lower().startswith(("10.", "doi:", "https://doi.org/")):
        path = "works/https://doi.org/" + t.split("doi.org/")[-1].removeprefix("doi:")
    else:
        path = "works/" + t
    return work(_call(path))


def fetch_many(ids: "list[str]", n: int = 50) -> "list[dict]":
    """Fetch several at once. One-by-one means 30 round trips for 30 references."""
    out = []
    ids = [x for x in ids if x]
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        d = _call("works", filter="openalex_id:" + "|".join(chunk), per_page=len(chunk))
        out += [work(w) for w in (d.get("results") or [])]
        if len(out) >= n:
            break
    return out[:n]


def walk_back(seed: str, depth: int = 1, per_level: int = 5) -> dict:
    """**Follow the references into the past.** This is the method's main lever:

        "A recent paper covers the current problem, but you cannot see how that
         problem developed. Follow the references and read the oldest ones."

    Each level is ordered **oldest first, then most cited**. Ordering by recency
    would just circle the same neighbourhood.

    Returns {"seed": …, "levels": [[…], …], "all": {id: paper}}
    """
    root = fetch_one(seed)
    seen = {root["id"]: root}
    levels = []
    front = [root]
    for _ in range(max(1, int(depth))):
        ids = []
        for p in front:
            ids += p["references"][:40]
        ids = [x for x in dict.fromkeys(ids) if x not in seen]
        if not ids:
            break
        want = per_level * max(1, len(front))
        papers = fetch_many(ids, n=want)
        papers.sort(key=lambda p: (p["year"] or 9999, -p["cited_by"]))
        papers = papers[:want]
        for p in papers:
            seen[p["id"]] = p
        levels.append(papers)
        front = papers
    return {"seed": root, "levels": levels, "all": seen}


def timeline_text(walked: dict) -> str:
    """One screen of the walk -- the backbone of the story you tell in an interview."""
    s = walked["seed"]
    out = [f"seed: {s.get('year')} · {s.get('title', '')[:80]} "
           f"(cited {s.get('cited_by', 0)}, refs {s.get('n_references', 0)})"]
    for i, level in enumerate(walked["levels"], 1):
        out.append(f"\n-- level {i} back ({len(level)} papers, oldest first) --")
        for p in level:
            open_ = "open" if p.get("oa_status") not in ("closed", "unknown", None) else "closed"
            out.append(f"  {p.get('year') or '????'} · cited {p.get('cited_by', 0):>5} · "
                       f"{open_:>6} · {p.get('title', '')[:66]}")
    return "\n".join(out)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="fetch paper skeletons from OpenAlex")
    ap.add_argument("--search", default="")
    ap.add_argument("--back", default="", help="seed DOI/id to walk backwards from")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.search:
        found = search(a.search, n=a.n, since=a.since)
        if a.json:
            print(json.dumps(found, ensure_ascii=False, indent=2))
        else:
            for p in found:
                print(f"{p['year']} · cited {p['cited_by']:>5} · {p['oa_status']:>8} · "
                      f"{p['title'][:78]}")
                print(f"        {p['venue'][:68]} · doi {p['doi'] or '-'}")
        return 0 if found else 3
    if a.back:
        walked = walk_back(a.back, depth=a.depth)
        print(json.dumps(walked, ensure_ascii=False, indent=2) if a.json
              else timeline_text(walked))
        return 0 if walked["levels"] else 3
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
