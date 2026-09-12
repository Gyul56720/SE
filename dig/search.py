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

import json
import os
import re
import time
import urllib.parse
from pathlib import Path

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


# ---------------------------------------------------------------- 문 원장: 세상 지식은 누적된 측정이다
# 사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 내가 앞서 틀린 자리 -- "구글이 봇을 막는다"
# 같은 세상 지식은 구조로 못 준다고 했다. 재서 쌓으면 된다. 망점검이 문마다 결과 수를 세는데, 그것을 원장에
# 적어 두면 다음에 같은 집을 문으로 넣는 패치를 코드가 거절한다: "전에 재 보니 결과 0 이었다."
# 원장은 덧붙이기만(append-only). 봇의 git_sync 가 커밋하므로 시뮬 판에도 같이 간다.
문원장상대 = "dig/door_ledger.jsonl"
REPO = Path(__file__).resolve().parent.parent


def _문적기(repo, 문들: "list[dict]", 말: str) -> None:
    p = Path(repo or REPO) / 문원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    때 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(p, "a", encoding="utf-8") as f:
        for d in 문들:
            f.write(json.dumps({"때": 때, "이름": d["이름"], "집": d.get("집", ""), "코드": d.get("코드", 0),
                                "결과": d.get("결과", 0), "왜": (d.get("왜") or "")[:80], "말": 말[:40]},
                               ensure_ascii=False) + "\n")


def 문원장읽기(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 문원장상대
    if not p.is_file():
        return []
    out = []
    for 줄 in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(줄))
        except ValueError:
            continue
    return out


def 문지식(repo=None) -> "dict[str, dict]":
    """집마다 {잰: n, 빈: 결과 0 이었던 수, 있음: 결과 >0 이었던 수, 마지막: 때}."""
    표: dict = {}
    for d in 문원장읽기(repo):
        집 = d.get("집") or ""
        if not 집:
            continue
        x = 표.setdefault(집, {"잰": 0, "빈": 0, "있음": 0, "마지막": ""})
        x["잰"] += 1
        if int(d.get("결과", 0) or 0) > 0:
            x["있음"] += 1
        else:
            x["빈"] += 1
        x["마지막"] = max(x["마지막"], str(d.get("때", "")))
    return 표


def 막힌집들(repo=None, 최소: int = 1) -> "dict[str, dict]":
    """잰 적이 있고 **한 번도 결과를 준 적이 없는** 집. 문으로 두드려 봐야 소용없는 곳이다."""
    return {집: x for 집, x in 문지식(repo).items() if x["잰"] >= 최소 and x["있음"] == 0}


def 틀검사(틀목록=None, repo=None) -> "list[str]":
    """문 목록이 성립하나 -- **망 없이 잴 수 있는 것만**. 어긴 것마다 한 줄(빈 목록이면 성립).

    무엇을 잡나: 물음 자리(`{q}`)가 없는 문 · http(s) 가 아닌 문 · 이름이 겹치는 문.

    **그리고 원장이 아는 것.** 실측 2026-09-12(VM): `!개선 수집망 url에 인스타그램, x, meta 추가해줘` 가
    문 셋을 `https://www.google.com/search?q=site:...` 로 넣었다. 꼴은 멀쩡하다. 그 문이 답을 주는지는
    두드려야 안다(`망점검(고른것=[...])`) -- 그런데 **한 번 두드려 본 뒤로는 안다.** 망점검이 문마다 결과 수를
    `dig/door_ledger.jsonl` 에 적고, 잰 적이 있는데 한 번도 결과를 준 적 없는 집을 문으로 넣으면 여기서
    잡는다. 세상 지식("구글은 봇을 막는다")이 누적된 측정이 된다. 문을 더하는 패치는 그 문 이름으로
    `!수집 망 <이름>` 을 한 번 돌려라 -- 그 한 번이 원장이 되고, 다음부터는 코드가 안다."""
    본 = list(틀목록 if 틀목록 is not None else 틀들())
    이름들 = [n for n, _ in 본]
    막힌 = 막힌집들(repo)
    탈 = []
    for 이름, 꼴 in 본:
        try:
            집 = _집(urllib.parse.urlsplit(꼴.replace("{q}", "q")).netloc)
        except ValueError:
            집 = ""
        if 집 and 집 in 막힌:
            x = 막힌[집]
            탈.append(f"{이름}: 이 집({집})은 **전에 재 보니 결과 0 이었다**({x['잰']}번, 마지막 {x['마지막'][:10]}) -- "
                      f"문으로 두드려도 소용없다. site: 로 좁히려면 결과를 주는 문에 얹어라(dig/door_ledger.jsonl)")
        if "{q}" not in 꼴:
            탈.append(f"{이름}: 물음 자리 `{{q}}` 가 없다 -- 무엇을 물어도 같은 쪽을 받는다")
        if not 꼴.startswith(("https://", "http://")):
            탈.append(f"{이름}: http(s) 가 아니다 ({꼴[:40]})")
        if 이름들.count(이름) > 1:
            탈.append(f"{이름}: 이름이 겹친다 -- `--문` 으로 고를 때 하나가 가려진다")
    return sorted(set(탈))


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


def 망점검(틈: float = 8.0, 말: str = "wikipedia", 고른것: list = None, repo=None, 적기: bool = True) -> dict:
    """**이 기계에서 바깥이 되나**를 코드가 잰다. {됐나, 열린문, 전체, 문들:[{이름,코드,왜}], 진단}.

    왜: 실측 2026-09-12, 봇이 "외부 망 접근을 시도했으나 시스템 내부의 인코딩 제한과 서비스 측
    차단으로 수집할 수 없었다" 고 보고했다. 셋 다 지어낸 원인이었다 -- 실제로는 (1) 날 한글 주소의
    UnicodeEncodeError(fetch.주소정규화 가 고쳤다) 였고, (2) dig 에는 구글 문이 아예 없다.
    **망이 되는지는 재면 알 수 있는 것이다.** 재는 길이 없으면 두뇌가 이야기를 지어낸다.

    아스키 질의로만 두드린다 -- 인코딩 문제와 망 문제를 섞지 않으려고."""
    쌍 = 주소들(말, 고른것)
    if not 쌍:
        return {"됐나": False, "닿았나": False, "열린문": 0, "닿은문": 0, "전체": 0, "문들": [],
                "진단": f"그런 이름의 문이 없다 ({고른것}) -- `python3 -m dig.run --문목록`"}
    응답들 = FT.여럿([u for _, u in 쌍], 동시=min(12, len(쌍)), 틈=틈)
    for r, (이름, _u) in zip(응답들, 쌍):
        r.이름 = 이름
    # **쓸 만한 결과가 몇 개인가.** HTTP 200 이어도 결과가 0 이면 그 문은 사실상 닫힌 것이다 --
    # 실측 2026-09-12(VM): 두뇌가 구글 문 셋을 넣었다. 200 을 받아도(또는 못 받아도) 결과는 안 나온다.
    # 코드만 보면 그것을 '된다' 로 읽는다. 문을 더하는 패치는 이 숫자로 판정해야 한다.
    센것: dict = {}
    for (이름, _u), r in zip(쌍, 응답들):
        if not r.몸통:
            센것[이름] = 0
            continue
        뽑 = EX.뽑기(r.몸통, r.꼴, r.최종url or r.url)
        센것[이름] = len(거두기([r], [뽑], 말, 몇=0))     # 문 하나씩 -- 그 문이 준 것만 센다
    문들 = [{"이름": 이름, "코드": r.코드, "왜": (r.왜 or "")[:80], "바이트": len(r.몸통 or ""),
           "결과": 센것.get(이름, 0), "집": _집(urllib.parse.urlsplit(_u).netloc)}
           for (이름, _u), r in zip(쌍, 응답들)]
    if 적기:
        try:
            _문적기(repo, 문들, 말)          # 잰 것은 남긴다 -- 다음 틀검사가 이것으로 안다
        except OSError:
            pass
    열린문 = sum(1 for r in 응답들 if r.됐나)
    막힘 = [d["왜"] for d in 문들 if d["왜"]]
    # **닿았나**와 **쓸 수 있나**를 가른다. 서버가 코드로 답했으면 망은 된 것이다 -- 그 문이 막았을 뿐이다.
    # 이 둘을 섞으면 "외부 망이 안 된다" 와 "그 검색엔진이 봇을 막는다" 가 같은 말이 되고, 그때 두뇌가
    # 원인을 지어낸다(실측 2026-09-12의 보고가 그랬다).
    닿은문 = sum(1 for r in 응답들 if r.코드)
    if 열린문:
        진단 = f"바깥이 된다 -- {열린문}/{len(쌍)} 문이 열렸다"
    elif 닿은문:
        진단 = (f"**망은 된다**({닿은문}/{len(쌍)} 문이 HTTP 로 답했다) -- 쓸 만한 답이 없을 뿐이다. "
              f"문이 봇을 막거나 주소가 옮겨졌다. 망 탓으로 적지 마라")
    elif any("프록시" in x for x in 막힘):
        진단 = "**이 기계의 나가는 길이 막혀 있다**(프록시가 CONNECT 를 끊는다) -- 코드 문제가 아니다"
    elif any("초 안에 답이 없다" in x for x in 막힘):
        진단 = "모든 문이 시간 초과 -- 나가는 길이 없거나 DNS 가 안 된다"
    else:
        진단 = "문이 다 닫혔다 -- 아래 까닭을 그대로 읽어라(지어내지 마라)"
    return {"됐나": 열린문 > 0, "닿았나": 닿은문 > 0, "열린문": 열린문, "닿은문": 닿은문,
            "전체": len(쌍), "문들": 문들, "진단": 진단}


def 망보고(r: dict) -> str:
    줄 = [f"dig 망점검: {r['진단']}"]
    for d in sorted(r["문들"], key=lambda x: (-x.get("결과", 0), x["코드"] != 200, x["이름"])):
        줄.append(f"  {d['이름']:<12} {d['코드'] or '-':>4} {d['바이트']:>7}바이트 "
                  f"결과 {d.get('결과', 0):>3}" + (f"  {d['왜']}" if d["왜"] else ""))
    return "\n".join(줄)


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
