# -*- coding: utf-8 -*-
"""dig/fulltext -- **actually get the body text**, or say precisely why we could not.

The user, 2026-09-21: "most papers, the body text just could not be read."

That is accurate. `dig/paper.py` only knows arXiv. Papers from IEEE, Elsevier or
Springer have a different address and their body is usually behind a subscription.
But **the same paper is often open somewhere else** -- an author's arXiv preprint,
an institutional repository, PMC, a publisher OA copy. This module knocks on those
doors in order.

## Door order (fall through on failure)

    1. arxiv    DOI/id already points at arXiv -> dig/paper (equations and
                algorithms come along too)
    2. oa       the best_oa_location OpenAlex handed us
    3. twin     **search arXiv by title.** An IEEE paper very often has a preprint
                there. Only accepted when the titles overlap enough (0.8) --
                attaching the wrong paper's body makes every sentence after it false
    4. none     all doors shut -> we read the abstract and nothing more, and we
                record exactly that

## Why we do not log in with someone's subscription

The user offered their university account. Declined: scraping IEEE with it breaks
the terms of use and the suspended account would be theirs. **Where an email
address genuinely helps is elsewhere** -- the `mailto=` politeness parameter of
OpenAlex and Unpaywall. It is not a key; it says who is calling, and it buys a
faster queue. Set `OPENALEX_MAILTO`.

For papers readable on a campus network, a human can open them in a browser and
drop the PDF into `inbox/`; `from_file()` reads that. That route is inside the terms.

## The evidence level always ships with the text

Repo rule (`paper/출처.jsonl`): full | abstract | listing | snippet. Writing as if
we read the body when we only saw the abstract is exactly the false-green this repo
exists to prevent.
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import extract as X          # noqa: E402
from dig import sections as SEC       # noqa: E402

# Test seams -- swap these and the module runs with no network.
get_text = None        # (url) -> (text, kind) | None
search_arxiv = None    # (title) -> [(title, arxiv_id)]

TIMEOUT = 30
# Below this many characters we are looking at a landing page or an abstract, not
# a body. Measured against real OA landing pages, which run a few hundred chars.
BODY_MIN_CHARS = 1500
# Title overlap required before we treat an arXiv hit as the same paper.
TWIN_MIN_OVERLAP = 0.8


def _words(t: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def title_overlap(a: str, b: str) -> float:
    """How much two titles share, 0..1. **A low score means a different paper** --
    attaching its body would make everything downstream a lie."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def _fetch(url: str) -> "tuple[str, str]":
    if get_text is not None:
        return get_text(url) or ("", "")
    req = urllib.request.Request(url, headers={"User-Agent": "SE-agent (dig/fulltext)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:       # noqa: S310
        raw = r.read()
        ctype = r.headers.get("Content-Type", "")
    if "pdf" in ctype.lower() or raw[:4] == b"%PDF":
        from dig import paper as P
        text, why = P.pdf텍스트(raw)
        return text, ("pdf" if text else f"pdf-unreadable:{why}")
    got = X.뽑기(raw.decode("utf-8", "replace"), "html", url)
    return (got.get("글") or got.get("본문") or ""), "html"


def _arxiv_by_title(title: str, n: int = 5) -> "list[tuple[str, str]]":
    if search_arxiv is not None:
        return search_arxiv(title)
    q = urllib.parse.urlencode({"search_query": f'ti:"{title[:200]}"', "max_results": n})
    req = urllib.request.Request("http://export.arxiv.org/api/query?" + q,
                                 headers={"User-Agent": "SE-agent (dig/fulltext)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:       # noqa: S310
        feed = r.read().decode("utf-8", "replace")
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", feed, re.S):
        chunk = m.group(1)
        t = re.search(r"<title>(.*?)</title>", chunk, re.S)
        i = re.search(r"<id>https?://arxiv\.org/abs/([^<v]+)", chunk)
        if t and i:
            out.append((" ".join(t.group(1).split()), i.group(1)))
    return out


def _from_arxiv(arxiv_id: str) -> str:
    from dig import paper as P
    got = P.논문받기(f"https://arxiv.org/abs/{arxiv_id}")
    return (got.get("본문") or "").strip()


def get_body(paper: dict, try_twin: bool = True) -> dict:
    """One OpenAlex paper (dig.openalex.work shape) -> its body, plus **where it came
    from and how much we actually read**.

    Returns:
        text        the body ("" if none)
        source      arxiv | oa | twin | file | none
        evidence    full | abstract | listing      <- same scale as paper/출처.jsonl
        sections    {abstract, introduction, background, …}
        misses      why each door failed
        twin        arXiv id, when the body came from a preprint of the same paper
    """
    res = {"text": "", "source": "none", "evidence": "listing", "sections": {},
           "misses": [], "twin": ""}
    title = paper.get("title") or ""
    doi = (paper.get("doi") or "").lower()
    oa_url = paper.get("oa_url") or ""

    def accept(text, source, twin=""):
        res.update(text=text, source=source, evidence="full",
                   sections=SEC.split(text), twin=twin)
        return res

    # 1) already arXiv
    if "arxiv" in doi or "arxiv" in oa_url.lower():
        hit = re.search(r"(\d{4}\.\d{4,5})", f"{doi} {oa_url}")
        if hit:
            try:
                body = _from_arxiv(hit.group(1))
                if body:
                    return accept(body, "arxiv")
                res["misses"].append(f"arxiv {hit.group(1)}: body came back empty")
            except Exception as e:                            # noqa: BLE001
                res["misses"].append(f"arxiv: {type(e).__name__}: {e}"[:160])

    # 2) every open location OpenAlex knows, not just the best one.
    #
    # Measured 2026-09-21: three papers were lost to "HTTP Error 403: Forbidden"
    # from a publisher landing page while **other open copies were never tried**.
    # A repository or preprint copy of the same paper is often readable when the
    # publisher's page is not. (We do not dress the request up as a browser to get
    # past a 403 -- that block is deliberate, and going around it is not ours to do.)
    for url in (paper.get("oa_locations") or ([oa_url] if oa_url else [])):
        try:
            text, kind = _fetch(url)
            if len(text.strip()) > BODY_MIN_CHARS:
                return accept(text, "oa")
            res["misses"].append(
                f"oa({kind or '?'}): only {len(text.strip())} chars -- "
                f"landing page, not a body [{url[:60]}]")
        except Exception as e:                                # noqa: BLE001
            res["misses"].append(f"oa: {type(e).__name__}: {e} [{url[:60]}]"[:200])

    # 3) preprint twin, matched by title
    if try_twin and title:
        try:
            matched = False
            for cand_title, arxiv_id in _arxiv_by_title(title):
                if title_overlap(title, cand_title) < TWIN_MIN_OVERLAP:
                    continue
                matched = True
                body = _from_arxiv(arxiv_id)
                if body:
                    return accept(body, "twin", twin=arxiv_id)
                res["misses"].append(f"twin {arxiv_id}: body came back empty")
            if not matched:
                res["misses"].append("twin: no arXiv entry whose title overlaps enough")
        except Exception as e:                                # noqa: BLE001
            res["misses"].append(f"twin: {type(e).__name__}: {e}"[:160])

    # 4) shut out -- the abstract is all we have, and we say so
    if (paper.get("abstract") or "").strip():
        res["evidence"] = "abstract"
        res["sections"] = {"abstract": paper["abstract"]}
    return res


def from_file(path: "str | Path") -> dict:
    """Read a PDF a human downloaded on their campus network into `inbox/`.
    **This route is inside the terms of use.**"""
    from dig import paper as P
    text, why = P.pdf텍스트(Path(path).read_bytes())
    if not text.strip():
        return {"text": "", "source": "file", "evidence": "listing", "sections": {},
                "misses": [f"pdf has no text layer: {why}"], "twin": ""}
    return {"text": text, "source": "file", "evidence": "full",
            "sections": SEC.split(text), "misses": [], "twin": ""}
