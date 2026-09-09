"""**주소를 모를 때의 첫 걸음.**

`dig/run.py --url` 은 주소가 있어야 시작한다. 그런데 사람이 주는 것은 대개 주소가
아니라 **말**이다 -- "중화역 근처 맛집", "3x3 텐서 랭크의 하한". 그래서 모델이 검색
주소를 **지어내야** 했고, 지어낸 것이 403 을 주면 거기서 "차단됐다" 로 끝났다
(실측 2026-09-09. 사용자가 같은 망에서 직접 확인하고 **"안막혔어"** 라고 했다 --
막힌 것이 아니라 **문을 하나밖에 안 두드린 것**이었다).

여기 있는 것은 **문 목록**이다. 답이 아니다. 어느 문이 열릴지 미리 알 수 없으니
**다 두드리고**, 열린 데서 바깥으로 나가는 주소를 거둔다. 안 열린 문은 왜 안
열렸는지 남긴다 -- `fetch.왜` 와 같은 규율이다. 빈손과 '403 이라 못 받았다' 는
다른 말이고, 뒤쪽만이 다음에 무엇을 할지 알려 준다.

## 무엇을 박고 무엇을 안 박나

**틀은 박는다.** 그럴 수밖에 없다 -- 검색 쪽 주소는 추론으로 지어낼 수 없다.
대신 **뜻은 안 박는다**: 어느 결과가 맛집이고 어느 것이 논문인지 여기서 안 정한다.
거두는 규칙은 꼴뿐이다(바깥으로 나가나 · 물음의 말이 들었나 · 얼마나 깊나).
그래서 맛집이든 논문이든 부품 값이든 같은 코드가 지나간다.
"""
from __future__ import annotations

import os
import re
import urllib.parse

from dig import extract as EX
from dig import fetch as FT

# **문 목록.** 로그인 없이 열려 있고, 자바스크립트 없이 읽히는 것만 둔다.
# 순서는 뜻이 없다 -- 한꺼번에 두드린다.
틀 = (
    # ── 두루 쓰는 검색 (HTML 을 그대로 준다) ─────────────────────────
    ("ddg-html",    "https://html.duckduckgo.com/html/?q={q}"),
    ("ddg-lite",    "https://lite.duckduckgo.com/lite/?q={q}"),
    ("mojeek",      "https://www.mojeek.com/search?q={q}"),
    ("marginalia",  "https://search.marginalia.nu/search?query={q}"),
    ("brave",       "https://search.brave.com/search?q={q}"),
    ("startpage",   "https://www.startpage.com/sp/search?query={q}"),
    ("bing",        "https://www.bing.com/search?q={q}&format=rss"),
    # ── 한국어 쪽 ───────────────────────────────────────────────────
    ("naver",       "https://search.naver.com/search.naver?query={q}"),
    ("naver-m",     "https://m.search.naver.com/search.naver?query={q}"),
    ("daum",        "https://search.daum.net/search?q={q}"),
    # ── 뜻풀이 · 사실 (JSON 을 그대로 준다) ──────────────────────────
    ("ddg-api",     "https://api.duckduckgo.com/?q={q}&format=json&no_html=1"),
    ("wiki-ko",     "https://ko.wikipedia.org/w/api.php?action=query&list=search"
                    "&srsearch={q}&srlimit=25&format=json"),
    ("wiki-en",     "https://en.wikipedia.org/w/api.php?action=query&list=search"
                    "&srsearch={q}&srlimit=25&format=json"),
    ("wikidata",    "https://www.wikidata.org/w/api.php?action=wbsearchentities"
                    "&search={q}&language=ko&uselang=ko&limit=20&format=json"),
    # ── 자리 ────────────────────────────────────────────────────────
    ("osm",         "https://nominatim.openstreetmap.org/search?q={q}&format=json"
                    "&addressdetails=1&extratags=1&namedetails=1&limit=20"),
    # ── 글 · 논문 · 책 · 코드 (열린 API) ─────────────────────────────
    ("crossref",    "https://api.crossref.org/works?query={q}&rows=20"),
    ("arxiv",       "http://export.arxiv.org/api/query?search_query=all:{q}"
                    "&max_results=20"),
    ("openalex",    "https://api.openalex.org/works?search={q}&per-page=20"),
    ("openlibrary", "https://openlibrary.org/search.json?q={q}&limit=20"),
    ("hn",          "https://hn.algolia.com/api/v1/search?query={q}&hitsPerPage=20"),
    ("github",      "https://api.github.com/search/repositories?q={q}&per_page=20"),
    ("stackex",     "https://api.stackexchange.com/2.3/search/advanced?q={q}"
                    "&site=stackoverflow&pagesize=20&order=desc&sort=relevance"),
)

# 검색 쪽 자기 집 주소는 결과가 아니다. 거둘 때 뺀다(꼴로만 -- 이름을 안 본다).
_주소꼴 = re.compile(r"https?://[^\s\"'<>\\)\]}]{6,300}")
_안볼꼬리 = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".css",
            ".js", ".woff", ".woff2", ".mp4", ".zip")
# 두드리지 않은 검색 쪽의 살림 주소. `_집` 은 **두드린 문**만 빼므로 이것이 따로
# 필요하다 -- bing 결과 안에 msn 이, ddg 안에 google 설정 쪽이 섞여 나온다.
# (`dig/find.py` 가 갖고 있던 것을 여기로 옮겼다. 두 벌로 두면 한쪽만 늘어난다.)
_살림 = re.compile(r"(duckduckgo|bing\.com|microsoft|msn\.com|mojeek|"
                   r"startpage\.com|search\.brave|marginalia|"
                   r"google\.[a-z.]+/(?:search|preferences|advanced|url)|"
                   r"/settings|/preferences)", re.I)


def 틀들() -> tuple:
    """박아 둔 틀 + `DIG_SEARCH_EXTRA` 에 적은 것. **닫아 두지 않는다.**

    쉼표로 잇는다. `{q}` 자리에 물음이 들어간다.
        DIG_SEARCH_EXTRA='https://example.com/s?q={q},https://b.org/api?t={q}'
    """
    더 = [u.strip() for u in os.getenv("DIG_SEARCH_EXTRA", "").split(",") if u.strip()]
    return 틀 + tuple((f"덧{i}", u) for i, u in enumerate(더, 1))


def 주소들(말: str, 고른것: list = None) -> list:
    """(이름, 주소) 목록. `고른것` 을 주면 그 이름만."""
    q = urllib.parse.quote(말.strip())
    골라 = {x.strip().lower() for x in (고른것 or []) if x.strip()}
    return [(이름, 꼴.format(q=q)) for 이름, 꼴 in 틀들()
            if not 골라 or 이름.lower() in 골라]


def _풀기(u: str) -> str:
    """리다이렉트 껍데기를 벗긴다.

    검색 쪽은 결과를 자기 주소로 감싼다(`//duckduckgo.com/l/?uddg=https%3A//...`).
    감싼 채로 두면 거둔 주소가 전부 그 검색 쪽 것이 되어 **바깥으로 못 나간다.**
    이름을 안 보고 꼴로만 푼다 -- 물음 값 중에 주소처럼 생긴 것이 있으면 그것이 속이다.
    """
    for _ in range(3):
        try:
            p = urllib.parse.urlsplit(u)
        except ValueError:
            return u
        속 = ""
        for _k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False):
            if v.startswith(("http://", "https://")):
                속 = v
                break
            if v.startswith("//") and len(v) > 10 and "." in v[2:20]:
                속 = "https:" + v
                break
        if not 속 or 속 == u:
            return u
        u = 속
    return u


def _집(host: str) -> str:
    """`html.duckduckgo.com` 과 `duckduckgo.com` 을 **같은 집**으로 본다.

    안 그러면 검색 쪽의 회사 소개· 도움말이 결과인 척 섞인다 -- 앞자리를 그것들이
    차지하면 `--파` 예산이 통째로 헛돈다.

    `co.kr` · `ne.jp` 처럼 **두 마디가 통째로 꼬리**인 데가 있다. 그냥 뒤 두 마디만
    보면 `naver.co.kr` 이 `co.kr` 이 되어 **모든 .co.kr 이 한집**이 된다 -- 한국 쪽이
    거의 다 그 꼴이라 결과가 통째로 사라진다. 그 꼬리들만 한 마디 더 본다.
    """
    ps = [p for p in (host or "").lower().split(".") if p]
    if len(ps) < 2:
        return host.lower()
    꼬리둘 = ("co", "ne", "or", "go", "ac", "com", "net", "org", "gov", "edu")
    if len(ps) >= 3 and ps[-2] in 꼬리둘 and len(ps[-1]) <= 3:
        return ".".join(ps[-3:])
    return ".".join(ps[-2:])


def _값(글: str, u: str, 낱말: list) -> int:
    """**어느 결과가 옳은지 여기서 안 정한다 -- 꼴만 센다.**

    문서 차례대로 집으면 검색 쪽 자기 메뉴(로그인 · 설정 · 도움말)가 앞을 다 차지한다.
    그 자리에 답은 없다. 그래서 차례 대신 꼴로 매긴다.
    """
    p = urllib.parse.urlsplit(u)
    낮 = (글 + " " + urllib.parse.unquote(u)).lower()
    마디 = [s for s in p.path.split("/") if s]
    점 = 40 * sum(1 for w in 낱말 if w and w.lower() in 낮)
    점 += min(len(마디), 5) * 4                 # 깊을수록 낱개 쪽
    if any(c.isdigit() for s in 마디 for c in s):
        점 += 10                                # /place/1234 · /2026/09/ -- 낱개를 가리킨다
    if p.query:
        점 += 4
    점 += min(len(글), 60) // 10                # 글이 붙은 링크가 대개 본문 쪽
    if len(글.strip()) <= 2:
        점 -= 12                                # '홈' · '≡' 같은 것
    return 점


def 거두기(응답들: list, 뽑은것들: list, 말: str, 몇: int = 40) -> list:
    """열린 문에서 **바깥으로 나가는 주소**를 거둔다.

    두 자리에서 거둔다 -- `<a>` 와 **몸통 글자 전체**. 뒤쪽이 없으면 JSON 으로
    답하는 문(위키 · crossref · arxiv)에서 한 줄도 못 건진다. 거기 주소는 태그가
    아니라 값 안에 들어 있다.
    """
    낱말 = [w for w in re.split(r"[\s,]+", 말.strip()) if len(w) >= 2]
    집 = {_집(urllib.parse.urlsplit(r.최종url or r.url).netloc) for r in 응답들}
    본, 나온것 = set(), []
    for x in 뽑은것들:
        바탕 = x.get("url") or ""
        후보 = [((L.get("글") or ""), L.get("href") or "")
                for L in (x.get("링크") or [])]
        # 몸통에 박힌 맨주소. 글이 없으니 값은 주소만으로 매겨진다.
        #
        # **`글` 만 보면 안 된다.** json 으로 답하는 문(위키· crossref· openalex·
        # github· osm)은 `뽑기` 가 {"갈래": "json", "칸": {...}} 로 내고 `글` 자리가
        # 아예 없다. 그런데 열린 API 는 대개 그 꼴이고, 거기 주소는 태그가 아니라
        # 값 안에 들어 있다 -- `글` 만 훑으면 그 문들에서 **한 줄도** 못 건진다.
        원본 = " ".join([x.get("글") or ""]
                       + [str(v) for v in (x.get("칸") or {}).values()])
        후보 += [("", m) for m in _주소꼴.findall(원본)]
        for 글, h in 후보:
            if not h or h.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                continue
            u = _풀기(urllib.parse.urljoin(바탕, h))
            try:
                p = urllib.parse.urlsplit(u)
            except ValueError:
                continue
            if p.scheme not in ("http", "https") or not p.netloc:
                continue
            if _집(p.netloc) in 집 or _살림.search(u):   # 검색 쪽 살림 -- 결과가 아니다
                continue
            if p.path.lower().endswith(_안볼꼬리):
                continue
            u = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
            열쇠 = (p.netloc, p.path.rstrip("/"))
            if 열쇠 in 본:
                continue
            본.add(열쇠)
            나온것.append({"주소": u, "글": 글.strip()[:120],
                          "어디서": 바탕[:60], "값": _값(글, u, 낱말)})
    나온것.sort(key=lambda d: (-d["값"], len(d["주소"])))
    return 나온것[:몇] if 몇 else 나온것


def 찾기(말: str, 틈: float = FT.기본틈, 고른것: list = None,
         몇: int = 40) -> tuple:
    """(응답들, 뽑은것들, 거둔것). **문을 다 두드린다.**

    하나씩 두드리면 스무 문이 스무 배 걸리고, 그러면 결국 두세 개만 보게 된다 --
    적게 모으는 쪽으로 저절로 기운다. 그래서 한꺼번에가 규율이다(`fetch.여럿`).
    """
    쌍 = 주소들(말, 고른것)
    if not 쌍:
        return [], [], []
    응답들 = FT.여럿([u for _, u in 쌍], 동시=min(12, len(쌍)), 틈=틈)
    for r, (이름, _u) in zip(응답들, 쌍):
        r.이름 = 이름                            # 어느 문이었는지 남긴다
    뽑은것들 = [EX.뽑기(r.몸통, r.꼴, r.최종url or r.url) for r in 응답들 if r.몸통]
    return 응답들, 뽑은것들, 거두기(응답들, 뽑은것들, 말, 몇)
