"""**뉴스 원장 -- 여러 나라에서 받아 하나의 사건으로 뭉친다.**

    python3 coin/news.py --탐침                     어느 출처가 실제로 답하나
    python3 coin/news.py --하루                     최근 24시간 (물음에 붙는 것)
    python3 coin/news.py --과거 --부터 2017-01-01   GDELT 로 몇 년치를 캔다
    python3 coin/news.py --뭉치기                   글 -> 사건. **D0 가 여기서 정해진다**
    python3 coin/news.py --덮임                     나라·말·해마다 몇 건이나 있나

## 뭉치기 -- 왜 이것이 다국적 수집의 진짜 이유인가

같은 사건을 중국어 매체가 09:00 에, 영어 매체가 16:00 에 쓴다. 영어만 모으면 D0 가
일곱 시간 늦고, 그 일곱 시간이 대개 그 사건의 움직임 전부다. 그래서 **같은 사건의
기사들을 뭉쳐 제일 이른 시각을 D0 로 쓴다.**

뭉치는 자는 `(유형, 자산, 창)` 이다 -- 낱말이 아니라 **꼬리표와 시간창**. 뜻을 짐작하는
자리가 없으므로 되짚을 수 있다.

## 그런데 이 뭉치기는 틀릴 수 있다 -- 그래서 두 번 잰다

창 안에서 서로 상관없는 두 규제 기사가 붙을 수 있다. 그러면 미국 사건의 D0 가 그날
아침 중국 기사 때문에 앞으로 끌려간다. 이것은 **막을 수 없고 잴 수는 있다.**

    최초   모든 나라를 통틀어 제일 이른 보도
    주류   그 뭉치에서 기사가 제일 많은 나라의 제일 이른 보도

`event.py` 가 **둘 다로 재고 부호가 갈리면 그 잰 값을 '불안정' 으로 내린다.**
`brief` 의 B004(다시 셈해서 대조)와 같은 자리다 -- 한 번 재고 믿지 않는다.

## RSS 는 과거를 못 판다

대개 최근 24~72시간이다. 그래서 **과거의 밑감은 GDELT** 이고(2017~, 말·나라로 거름),
RSS 는 '지금 무슨 일이 있나' 를 맡는다. 이 둘은 섞이지 않게 `출처` 로 표시된다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import source as SRC                                        # noqa: E402
from coin import tag as TG                                            # noqa: E402
from coin.price import _때                                            # noqa: E402

# **받는 일은 `dig/` 가 한다.** 이 저장소에 이미 있는 스크레이퍼이고, 여기가 필요로
# 하는 것을 정확히 갖췄다 -- 헤더벌 돌려쓰기(막히면 다음 벌로), 곁문(모바일·AMP·
# 그 쪽 JSON 끝점), gzip 풀기, **charset 감지(cp949 포함)**, HTTP 오류에도 몸통 읽기,
# 그리고 병렬(`여럿`).
#
# 순진한 urllib 로 받으면 중국·일본·한국 매체에서 그대로 깨진다 -- 인코딩이 utf-8 이
# 아닌 곳이 아직 많고, 기본 User-Agent 를 막는 곳도 많다. 나라를 늘려 놓고 받는 자리를
# 안 고치면 **늘린 나라가 조용히 0건으로 들어온다.**
try:
    from dig import extract as DIGX                                   # noqa: E402
    from dig import fetch as DIG                                      # noqa: E402
except Exception:                                                     # noqa: BLE001
    DIG = DIGX = None

CORPUS = Path(__file__).resolve().parent / "corpus"
길 = CORPUS / "news.json"
사건길 = CORPUS / "events.json"
GDELT_말 = {"gdelt-en": "eng", "gdelt-zh": "chi", "gdelt-ja": "jpn", "gdelt-ko": "kor"}
질의 = "(bitcoin OR cryptocurrency OR 加密货币 OR 比特币 OR 暗号資産 OR 암호화폐)"


def _http(url: str, timeout: float = 25.0) -> bytes:
    """`dig` 가 있으면 그것으로. 없으면 맨 urllib 로 되돌린다."""
    if DIG is not None:
        r = DIG.받기(url)
        if not r.됐나:
            raise RuntimeError(r.왜 or f"HTTP {r.코드}")
        return r.몸통.encode("utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": "SE-coin/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _캐기(url: str, timeout: float = 25.0, 곁문수: int = 6):
    """**앞문이 안 되면 곁문까지.** 모바일 · AMP · 그 쪽 JSON 끝점 · 아카이브 · http.

    `dig/README.md` 가 적어 둔 그대로다 -- "한 번 해 보고 안 된다고 하지 않는다".
    중국·일본 매체는 앞문 피드가 막히거나 옮겨 간 일이 흔하고, 그때 열려 있는 것이
    대개 모바일 쪽이다. 이 한 걸음이 **나라를 늘린 값어치의 절반**이다.
    """
    if DIG is None:
        return _http(url, timeout)
    r = DIG.받기(url)
    if r.됐나:
        return r.몸통.encode("utf-8"), r.최종url or url
    for u in DIG.곁문(url)[:곁문수]:
        r2 = DIG.받기(u, 벌수=2)
        if r2.됐나:
            return r2.몸통.encode("utf-8"), r2.최종url or u
    raise RuntimeError(r.왜 or f"HTTP {r.코드}")


def _여럿(urls: list) -> dict:
    """**한꺼번에 받는다.** 스물세 곳을 하나씩 받으면 스물세 배 걸리고, 그러면
    결국 몇 곳만 보게 된다 -- `dig/README.md` 가 적어 둔 그 기울기다."""
    if DIG is None:
        out = {}
        for u in urls:
            try:
                out[u] = _http(u)
            except Exception as e:                                    # noqa: BLE001
                out[u] = e
        return out
    return {r.url: (r.몸통.encode("utf-8") if r.됐나
                    else RuntimeError(r.왜 or f"HTTP {r.코드}"))
            for r in DIG.여럿(urls, 동시=8)}


# ------------------------------------------------------------------ 받기
def _rss(raw: bytes, s) -> list:
    """RSS 2.0 과 Atom 을 둘 다 읽는다. 바깥 라이브러리를 안 쓴다."""
    out = []
    try:
        뿌리 = ET.fromstring(raw)
    except ET.ParseError:
        return out
    A = "{http://www.w3.org/2005/Atom}"
    글들 = 뿌리.iter("item")
    글들 = list(글들) or list(뿌리.iter(A + "entry"))
    for it in 글들:
        제목 = (it.findtext("title") or it.findtext(A + "title") or "").strip()
        때 = (it.findtext("pubDate") or it.findtext("published")
              or it.findtext(A + "published") or it.findtext(A + "updated")
              or it.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
        고리 = (it.findtext("link") or "").strip()
        if not 고리:
            e = it.find(A + "link")
            고리 = (e.get("href") if e is not None else "") or ""
        t = _때(때)
        if not 제목 or t is None:
            continue
        out.append(_글(제목, t, s, 고리))
    return out


def _html(raw: bytes, s, url: str = "") -> list:
    """**피드가 없는 쪽에서 글을 뽑는다.** `dig/extract.py` 가 캔 것에서 고른다.

    세 자리를 순서대로 본다 -- 뒤로 갈수록 시각을 못 믿는다:

        jsonld   schema.org NewsArticle 의 headline + datePublished. **제일 믿을 만하다**
        og       article:published_time + og:title
        링크     제목만 있고 시각이 없다 -> **본때(우리가 본 시각)를 쓴다**

    마지막이 위험해 보이지만 **안전한 쪽으로 틀린다.** 본때는 참 발행 시각의 상한이라
    그것으로 D0 를 잡으면 D0 가 참보다 **늦거나 같다.** 미리보기는 D0 가 앞설 때
    생기므로, 이 오차는 신호를 잃게 할 뿐 없는 신호를 만들지 않는다.

    그래도 `뭉치기` 는 **'최초' 후보로는 안 쓴다** -- 여러 나라 중 제일 이른 시각을
    고르는 자리에 믿을 수 없는 시각이 끼면 그 하나가 D0 를 통째로 끌고 간다.
    """
    if DIGX is None:
        return []
    got = DIGX.뽑기(raw.decode("utf-8", "replace"), "html", url)
    out, 본 = [], set()

    def 더(제목, 때, 출처칸, 고리=""):
        제목 = (제목 or "").strip()
        if not 제목 or len(제목) < 8 or 제목 in 본:
            return
        t = _때(때) if 때 else None
        if t is None:
            t, 출처칸 = datetime.now(timezone.utc), "본때"
        본.add(제목)
        g = _글(제목, t, s, 고리)
        g["시각출처"] = 출처칸
        out.append(g)

    for x in (got.get("묻힌표원본") or []):
        묶 = x if isinstance(x, list) else [x]
        for d in 묶:
            if not isinstance(d, dict):
                continue
            안 = d.get("@graph") if isinstance(d.get("@graph"), list) else [d]
            for e in 안:
                if not isinstance(e, dict):
                    continue
                꼴 = str(e.get("@type", ""))
                if "Article" not in 꼴 and "NewsArticle" not in 꼴 and "BlogPosting" not in 꼴:
                    continue
                더(e.get("headline") or e.get("name"),
                   e.get("datePublished") or e.get("dateCreated"),
                   "jsonld", str(e.get("url") or url))
    머 = got.get("머리표") or {}
    더(머.get("og:title") or 머.get("title"),
       머.get("article:published_time") or 머.get("datePublished"), "og", url)
    if not out:                                    # 마지막 -- 제목만 있는 링크
        for 고리 in (got.get("링크") or [])[:120]:
            글자 = 고리.get("글") if isinstance(고리, dict) else ""
            주소 = 고리.get("url") if isinstance(고리, dict) else ""
            if 글자 and TG.재기(글자):            # **꼬리표가 걸리는 것만** 담는다
                더(글자, "", "본때", 주소 or url)
    return out


def _gdelt(s, 부터: str, 까지: str, 최대쪽: int = 24) -> list:
    """GDELT DOC 2.0. 한 번에 250건까지라 **시간을 잘라 가며** 여러 번 묻는다."""
    말 = GDELT_말.get(s.이름, "eng")
    t0, t1 = _때(부터), _때(까지)
    if t0 is None or t1 is None:
        return []
    out, 칸 = [], max(timedelta(days=1), (t1 - t0) / max(1, 최대쪽))
    a = t0
    while a < t1:
        b = min(a + 칸, t1)
        q = urllib.parse.urlencode({
            "query": f"{질의} sourcelang:{말}", "mode": "artlist", "format": "json",
            "maxrecords": "250", "sort": "datedesc",
            "startdatetime": a.strftime("%Y%m%d%H%M%S"),
            "enddatetime": b.strftime("%Y%m%d%H%M%S")})
        try:
            got = json.loads(_http(f"{s.url}?{q}").decode("utf-8", "replace"))
        except Exception:                                             # noqa: BLE001
            got = {}
        for r in (got.get("articles") or []):
            t = _때(str(r.get("seendate", "")).replace("T", " ").replace("Z", ""))
            if t is None:
                t = _때(str(r.get("seendate", "")))
            if t is None:
                continue
            out.append(_글(r.get("title", ""), t, s, r.get("url", "")))
        a = b
    return out


def _json(s) -> list:
    import os
    url = s.url.replace("{key}", os.environ.get(s.열쇠, "") if s.열쇠 else "")
    try:
        got = json.loads(_http(url).decode("utf-8", "replace"))
    except Exception:                                                 # noqa: BLE001
        return []
    줄 = got.get(s.경로) if s.경로 else got
    out = []
    for r in (줄 or []):
        t = _때(r.get("published_at") or r.get("created_at") or "")
        if t is None:
            continue
        out.append(_글(r.get("title", ""), t, s, (r.get("url") or "")))
    return out


def _글(제목: str, t: datetime, s, url: str) -> dict:
    """`본때` 는 **우리가 본 시각**이다 -- 매체가 적은 `시각` 과 다른 물음이다.

    매체 시각은 거짓말을 한다(소급 수정 · 시간대 버그 · 아예 없는 곳). 본 시각을
    같이 남기면 **참 발행 시각 <= 본때** 라는 상한이 생기고, `시각 > 본때` 면 그
    피드의 시각이 미래라는 뜻이라 그 줄은 못 믿는다(`앞선시각`). 사건 연구가 D0 를
    시각에서 뽑으므로 이 한 칸이 미리보기를 막는 마지막 자물쇠다.
    """
    ts = TG.재기(제목)
    본때 = datetime.now(timezone.utc)
    t = t.astimezone(timezone.utc)
    return {"제목": 제목.strip(), "시각": t.isoformat(timespec="seconds"),
            "본때": 본때.isoformat(timespec="seconds"), "시각출처": "feed",
            "앞선시각": t > 본때 + timedelta(minutes=5),
            "출처": s.이름, "나라": s.나라, "말": s.말, "무게": s.무게, "url": url,
            "유형": [x.유형 for x in ts],
            "걸린것": [[m, w] for x in ts for m, w in x.걸린것][:8],
            "자산": list(TG.자산재기(제목))}


def 받기(출처들=None, 부터: str = "", 까지: str = "", 과거: bool = False) -> list:
    출처들 = 출처들 if 출처들 is not None else SRC.쓸수있는것(과거만=과거)
    쪽 = [s for s in 출처들 if s.꼴 in ("rss", "html")]
    out = []
    받은것 = _여럿([s.url for s in 쪽]) if 쪽 else {}
    for s in 쪽:
        got = 받은것.get(s.url)
        글 = []
        if not isinstance(got, Exception) and got is not None:
            글 = (_rss(got, s) if s.꼴 == "rss" else []) or _html(got, s, s.url)
        if not 글:
            # **앞문이 빈손이면 곁문을 두드린다.** 한 번 해 보고 안 된다고 하지 않는다
            try:
                raw, 최종 = _캐기(s.url)
                글 = (_rss(raw, s) if s.꼴 == "rss" else []) or _html(raw, s, 최종)
                if 글:
                    print(f"  곁문   {s.이름:<14} {s.나라} {len(글)}건 <- {최종[:60]}",
                          file=sys.stderr)
            except Exception as e:                                    # noqa: BLE001
                print(f"  못 받음 {s.이름:<14} {s.나라} {type(e).__name__}: "
                      f"{str(e)[:60]}", file=sys.stderr)
        if not 글:
            print(f"  빈손   {s.이름:<14} {s.나라} 앞문도 곁문도 글이 0개", file=sys.stderr)
        out += 글
    for s in 출처들:
        if s.꼴 in ("rss", "html"):
            continue
        try:
            if s.꼴 == "gdelt":
                out += _gdelt(s, 부터 or (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"),
                              까지 or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
            else:
                out += _json(s)
        except Exception as e:                                        # noqa: BLE001
            print(f"  못 받음 {s.이름:<14} {type(e).__name__}: {str(e)[:60]}", file=sys.stderr)
    return out


# ------------------------------------------------------------------ 원장
def 합치기(옛: dict, 새: list) -> dict:
    """**덮어쓰지 않고 쌓는다.** 같은 글(출처+url+제목)은 한 번만."""
    글 = {(g["출처"], g.get("url", ""), g["제목"]): g for g in (옛.get("글") or [])}
    더한것 = 0
    for g in 새:
        k = (g["출처"], g.get("url", ""), g["제목"])
        if k not in 글:
            글[k] = g
            더한것 += 1
    묶 = sorted(글.values(), key=lambda g: g["시각"])
    return {"받은때": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "글": 묶, "더한것": 더한것}


def 불러오기(경로=None) -> dict:
    p = Path(경로) if 경로 else 길
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"글": []}


def 저장(원장: dict, 경로=None) -> Path:
    p = Path(경로) if 경로 else 길
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(원장, ensure_ascii=False), encoding="utf-8")
    return p


# ------------------------------------------------------------------ 뭉치기
def 뭉치기(글들: list, 창시간: float = 12.0) -> list:
    """(유형, 자산) 마다 시간창으로 이어 붙인다. 사건 하나 = 뭉치 하나.

    돌려주는 것:
        유형 · 자산 · 최초(제일 이른 시각) · 주류(기사가 제일 많은 나라의 제일 이른 시각)
        나라들 · 출처들 · 글수 · 지연시간(최초와 주류의 차, 시간)
    """
    통 = {}
    for g in 글들:
        if g.get("앞선시각"):                    # **시각이 미래인 줄은 D0 를 못 정한다**
            continue
        자산들 = g.get("자산") or ["BTC"]        # 자산이 안 걸리면 시장 전체로 본다
        for 유형 in (g.get("유형") or []):
            for 자산 in 자산들:
                통.setdefault((유형, 자산), []).append(g)
    사건 = []
    for (유형, 자산), gs in 통.items():
        gs.sort(key=lambda x: x["시각"])
        묶, 지금 = [], []
        for g in gs:
            if not 지금:
                지금 = [g]
                continue
            벌어짐 = (_때(g["시각"]) - _때(지금[-1]["시각"])).total_seconds() / 3600.0
            if 벌어짐 <= 창시간:
                지금.append(g)
            else:
                묶.append(지금)
                지금 = [g]
        if 지금:
            묶.append(지금)
        for m in 묶:
            셈 = {}
            for g in m:
                셈[g["나라"]] = 셈.get(g["나라"], 0) + 1
            # **'최초' 후보는 믿을 만한 시각에서만 고른다.** 여러 나라 중 제일 이른
            # 것을 고르는 자리라, 못 믿을 시각 하나가 D0 를 통째로 끌고 간다.
            믿을것 = [g for g in m if g.get("시각출처", "feed") in ("feed", "jsonld")] or m
            # 기사가 제일 많은 나라. 같으면 **더 이른 쪽** (문자열은 음수화가 안 된다)
            주국 = sorted(셈, key=lambda k: (-셈[k], min(x["시각"] for x in m if x["나라"] == k)))[0]
            최초 = min(x["시각"] for x in 믿을것)
            같은나라 = [x for x in 믿을것 if x["나라"] == 주국] or 믿을것
            주류 = min(x["시각"] for x in 같은나라)
            사건.append({
                "유형": 유형, "자산": 자산, "최초": 최초, "주류": 주류, "주국": 주국,
                "나라들": sorted(셈), "나라수": len(셈), "글수": len(m),
                "출처들": sorted({x["출처"] for x in m})[:6],
                "지연": round((_때(주류) - _때(최초)).total_seconds() / 3600.0, 2),
                "본보기": m[0]["제목"][:120],
            })
    사건.sort(key=lambda e: e["최초"])
    return 사건


def 덮임(글들: list) -> dict:
    """**무엇이 안 들었는지를 보여 주는 자리.** 나라·말·해마다 몇 건인가."""
    나라, 말, 해 = {}, {}, {}
    for g in 글들:
        나라[g["나라"]] = 나라.get(g["나라"], 0) + 1
        말[g["말"]] = 말.get(g["말"], 0) + 1
        y = g["시각"][:4]
        해.setdefault(y, {}).setdefault(g["나라"], 0)
        해[y][g["나라"]] += 1
    구간 = (글들[0]["시각"][:10], 글들[-1]["시각"][:10]) if 글들 else ("", "")
    return {"글수": len(글들), "구간": 구간, "나라": 나라, "말": 말, "해나라": 해}


# ------------------------------------------------------------------ 탐침
def 탐침(출처들=None, 알림=None) -> list:
    """**어느 출처가 실제로 답하나.** 표의 `확인` 칸이 비어 있는 이유가 이것이다.

    ## 여기는 일부러 순차다 -- `받기()` 와 다르다

    `받기()` 는 병렬이다(`dig/README.md`: "하나씩 받으면 열 곳이 열 배 걸리고, 그러면
    결국 한두 곳만 보게 된다"). 그런데 **탐침은 그 규율이 거꾸로 걸린다.**

    백 곳에 한꺼번에 쏘면 그것이 버스트로 보여 막는 데가 생기고, 그러면 **멀쩡한
    출처가 '못함' 으로 찍힌다.** 탐침이 재는 것은 속도가 아니라 "이 문이 열리는가"
    이고, 거짓 음성은 그 답을 통째로 뒤집는다 -- 없는 빈틈을 있다고 하거나, 표에서
    멀쩡한 줄을 지우게 만든다. 백 곳이 몇십 분 걸려도 한 번 제대로 재는 편이 낫다.

    `알림` 을 주면 결과 하나가 날 때마다 부른다. **안 주면 다 끝날 때까지 화면이
    죽어 있어서**, 도는 중인지 멈춘 것인지 사람이 못 가른다 -- 이 저장소가 백그라운드
    작업에 대해 적어 둔 그 자리와 같다(프로세스가 살아 있는 것과 일을 하는 것은 다르다).
    """
    out = []
    쪽들 = 출처들 if 출처들 is not None else SRC.목록
    for i, s in enumerate(쪽들, 1):
        def 담기(r):
            out.append(r)
            if 알림:
                알림(i, len(쪽들), r)
            return r
        ok, 왜 = s.쓸수있나()
        if not ok:
            담기({"이름": s.이름, "나라": s.나라, "층": s.층, "산것": 0, "왜": 왜})
            continue
        try:
            if s.꼴 == "gdelt":
                got = _gdelt(s, (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
                             datetime.now(timezone.utc).strftime("%Y-%m-%d"), 최대쪽=1)
            elif s.꼴 == "json":
                got = _json(s)
            else:
                raw, 최종 = _캐기(s.url, timeout=15.0, 곁문수=2)   # 탐침은 곁문 둘만
                got = (_rss(raw, s) if s.꼴 == "rss" else []) or _html(raw, s, 최종)
            담기({"이름": s.이름, "나라": s.나라, "층": s.층, "산것": len(got),
                  "왜": "" if got else "답은 왔는데 글이 0개"})
        except Exception as e:                                        # noqa: BLE001
            담기({"이름": s.이름, "나라": s.나라, "층": s.층, "산것": 0,
                  "왜": f"{type(e).__name__}: {str(e)[:70]}"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--탐침", action="store_true")
    ap.add_argument("--격자", action="store_true", help="나라 x 층 표. 빈 칸을 짚는다")
    ap.add_argument("--기록", action="store_true",
                    help="탐침 결과를 적어 둔다. --격자 의 '확인' 칸이 이것으로 찬다")
    ap.add_argument("--하루", action="store_true")
    ap.add_argument("--과거", action="store_true")
    ap.add_argument("--부터", default="")
    ap.add_argument("--까지", default="")
    ap.add_argument("--뭉치기", action="store_true")
    ap.add_argument("--덮임", action="store_true")
    ap.add_argument("--창", type=float, default=12.0)
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)

    if a.격자:
        g = SRC.격자()
        확 = SRC.격자(확인된것만=True)
        print("     " + "".join(f"{층:^12}" for 층 in SRC.층들))
        for 나라 in SRC.나라들 + ("XX",):
            줄 = f"  {나라:<3}"
            for 층 in SRC.층들:
                n, c = len(g.get((나라, 층), [])), len(확.get((나라, 층), []))
                줄 += f"{(f'{n}' if not c else f'{c}/{n}'):^12}"
            print(줄)
        빈 = SRC.빈틈()
        print(f"\n출처 {len(SRC.목록)}곳 · 빈틈 " + (", ".join(f"{a}/{b}" for a, b in 빈)
                                                  if 빈 else "**없다**"))
        빈확 = SRC.빈틈(확인된것만=True)
        print(f"**실제로 답하는 것만 세면 빈틈 {len(빈확)}칸** -- 탐침을 안 돌렸으면 전부다: "
              + (", ".join(f"{a}/{b}" for a, b in 빈확[:8]) or "없다"))
        print("  (칸의 수는 '확인된것/전체'. 확인은 --탐침 이 채운다)")
        return 0

    if a.탐침:
        쪽수 = len(SRC.목록)
        print(f"출처 {쪽수}곳을 **하나씩** 두드린다 -- 한꺼번에 쏘면 버스트로 보여 "
              "멀쩡한 곳이 '못함' 으로 찍힌다. 오래 걸린다.\n", flush=True)

        def 찍기(i, n, x):
            print(f"  [{i:>3}/{n}] {'OK  ' if x['산것'] else '못함'} {x['이름']:<14} "
                  f"{x['나라']:<3} {x.get('층',''):<6} {x['산것']:>4}건  {x['왜'][:60]}",
                  flush=True)

        r = 탐침(알림=찍기)
        산것 = [x for x in r if x["산것"]]
        print()
        print(f"\n{len(산것)}/{len(r)} 출처가 답했다. "
              f"나라: {sorted({x['나라'] for x in 산것})}")
        찬칸 = {(x["나라"], x.get("층", "")) for x in 산것}
        빈 = [(나, 층) for 나 in SRC.나라들 for 층 in ("규제", "거시", "사법", "거래소", "매체")
              if (나, 층) not in 찬칸 and ("XX", 층) not in 찬칸]
        print("**답한 것만 세면 빈 칸**: " + (", ".join(f"{a}/{b}" for a, b in 빈) or "없다")
              + "  <- 이것이 진짜 덮임이다")
        if a.기록:
            p = SRC.탐침기록(r)
            print(f"적어 뒀다 -> {p}\n  이제 `--격자` 의 칸이 '확인된것/전체' 로 찬다")
        else:
            print("  (`--기록` 을 주면 적어 둬서 `--격자` 가 이 사실을 쓴다)")
        print("**여기(에이전트 컨테이너)에서는 프록시가 다 막는다 -- VM 에서 돌려라**")
        return 0 if 산것 else 3

    if a.하루 or a.과거:
        부터 = a.부터 or ((datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
                        if a.하루 else "2017-01-01")
        새 = 받기(부터=부터, 까지=a.까지, 과거=a.과거)
        원장 = 합치기(불러오기(a.원장 or None), 새)
        p = 저장(원장, a.원장 or None)
        d = 덮임(원장["글"])
        print(f"받은 것 {len(새)}건 · 새로 담은 것 {원장['더한것']}건 · 원장 {d['글수']}건")
        print(f"  구간 {d['구간'][0]} ~ {d['구간'][1]}")
        print("  나라 " + " · ".join(f"{k}:{v}" for k, v in sorted(d["나라"].items())))
        print(f"  -> {p}")
        return 0 if 새 else 3

    글들 = 불러오기(a.원장 or None).get("글", [])
    if a.덮임:
        d = 덮임(글들)
        print(f"글 {d['글수']}건 · {d['구간'][0]} ~ {d['구간'][1]}")
        print("  나라 " + " · ".join(f"{k}:{v}" for k, v in sorted(d["나라"].items())))
        print("  말   " + " · ".join(f"{k}:{v}" for k, v in sorted(d["말"].items())))
        for y in sorted(d["해나라"]):
            print(f"  {y}  " + " · ".join(f"{k}:{v}" for k, v in sorted(d["해나라"][y].items())))
        return 0

    if a.뭉치기:
        사건 = 뭉치기(글들, a.창)
        저장({"만든때": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "창시간": a.창, "사건": 사건}, 사건길)
        여럿 = [e for e in 사건 if e["나라수"] > 1]
        print(f"사건 {len(사건)}개 (글 {len(글들)}건에서) · 여러 나라가 함께 쓴 것 {len(여럿)}개")
        늦 = [e for e in 여럿 if e["지연"] > 1]
        if 늦:
            평 = sum(e["지연"] for e in 늦) / len(늦)
            print(f"  주류 나라가 최초보다 평균 {평:.1f}시간 늦다 "
                  "-- **영어만 모았으면 그만큼 늦게 쟀을 것이다**")
        print(f"  -> {사건길}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    # `| head` 로 잘라 볼 때 파이프가 끊기면 파이썬이 역추적을 뱉는다. 사용자가
    # 실제로 그렇게 부르는 명령이라(격자 · 탐침이 길다) 조용히 끝낸다.
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(0)
