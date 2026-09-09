"""**질의 -> 주소.** `dig/` 에 빠져 있던 첫 걸음.

## 속은 `dig/search.py` 다 (2026-09-09)

같은 날 같은 문제를 두 자리에서 각각 풀었다 -- 여기(jaso 쪽)와 `dig/search.py`
(공개 채널 쪽). 둘이 서로를 안 부르니 **문 목록이 두 벌**이 됐고, 한쪽에 문을
더해도 다른 쪽은 몰랐다. 사용자가 골랐다: `search.py` 로 모은다.

그래서 이 파일은 **껍데기만 남는다.** `찾기()` 는 `search.찾기()` 를 부르고 그
결과를 여기 꼴(`결과`/`찾은것`)로 옮긴다. 부르던 일곱 자리(jaso/crawl · keep ·
fetch · mine · learn + 검사 둘)는 한 줄도 안 고친다. 대신 공짜로 얻는 것:

    문      4개 -> 22개 (검색뿐 아니라 위키· 논문· 지도· github 까지)
    부르기  차례로 -> 한꺼번에 (하나가 느리면 다 느리던 것이 없어진다)
    거두기  <a> 만 -> <a> + json 값 안에 박힌 주소까지

`링크뽑기()` 는 여기 남는다 -- **차례를 지키는** 원시 도구이고(검사가 첫 결과의
제목을 본다) 몸통 하나만 받는 자리라 `search` 의 응답 꼴이 필요 없다.

    python3 dig/find.py "2026 자기소개서 문항 공기업"
    python3 dig/find.py "자소서 작성법" --몇 20 --json
    python3 dig/find.py "삼성전자 채용 자기소개서 문항" --창구 ddg

`run.py` 는 **주소를 받아** 캔다. 그런데 "자소서 문항을 찾아라" 는 주소가 아니라
질의다. 그 한 걸음이 없어서 지금까지 사람이 주소를 손으로 줘야 했고, 손으로 주는
동안은 **사람이 아는 데까지만 찾아진다.**

## 창구를 여럿 둔다 -- `llm_pool` 과 같은 수

검색 쪽은 봇을 막는다. 하나가 막혔다고 "못 찾는다" 고 하면, 다른 창구가 답하는데도
빈손으로 돌아오는 것이다. `orchestrator/llm_pool.py` 가 (키 x 모델) 을 돌려쓰는 것과
같은 배치다 -- 되는 것을 쓰고, 안 되는 것은 왜 안 됐는지 갈래를 남긴다.

`fetch.받기` 를 그대로 쓰므로 헤더벌 돌려쓰기(데스크톱 -> 모바일 -> 봇)를 물려받는다.

## 고르지 않는다

`dig/` 의 규율 그대로다 -- **받은 것을 다 내놓는다.** 무엇이 쓸모 있는지 여기서 안
정한다. 중복 주소만 접고, 순서는 창구가 준 순서를 지킨다.

## 못 하는 것

- **검색 결과의 순위를 믿지 않는다.** 광고와 도배가 섞인다. 위에서부터 좋은 것이
  아니라 그냥 위에 있는 것이다.
- **로그인·유료벽 뒤는 안 본다.** `run.py` 와 같은 선이다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dig import fetch as FT                                          # noqa: E402
from dig import search as SC                                         # noqa: E402

# **문 목록은 `search.틀들()` 하나뿐이다.** 여기 두면 두 벌이 된다.
# 예전 이름을 쓰던 자리가 안 깨지게 별명만 남긴다.
_별명 = {"ddg": "ddg-html"}


def 창구들() -> tuple:
    """(이름, 주소틀). 예전엔 튜플 상수였다 -- 부르는 꼴만 바뀌었다."""
    return SC.틀들()

_링크 = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                   re.I | re.S)
_태그 = re.compile(r"<[^>]+>")
_공백 = re.compile(r"\s+")

# 검색 쪽 자기 주소. 결과가 아니라 그 쪽 살림이다.
# **`search._살림` 로 옮겼다** -- 두 벌로 두면 한쪽만 늘어난다. 여기서 더 보는
# 것은 링크에만 있는 두 꼴뿐이다(맨주소에는 안 나온다).
_안볼앞 = re.compile(r"^\s*(javascript:|mailto:|tel:|#)", re.I)


@dataclass
class 찾은것:
    url: str
    제목: str = ""
    창구: str = ""

    def __str__(self) -> str:
        return f"{self.제목[:60] or '(제목 없음)'}\n    {self.url}"


@dataclass
class 결과:
    질의: str = ""
    것들: list = field(default_factory=list)
    창구별: dict = field(default_factory=dict)     # 이름 -> 몇 개 or 못 받은 까닭

    def __bool__(self) -> bool:
        return bool(self.것들)


def _풀린주소(href: str, 바탕: str) -> str:
    """검색 쪽이 감싼 주소를 푼다. **푸는 셈은 `search._풀기` 하나뿐이다.**

    여기서 더 하는 것은 상대 주소를 바탕에 붙이는 것뿐이다(`search` 쪽은 이미
    절대 주소가 된 것을 받는다).
    """
    href = (href or "").strip()
    if not href or _안볼앞.search(href):
        return ""
    if href.startswith("//"):
        href = "https:" + href
    elif href.startswith("/") and 바탕:
        href = urllib.parse.urljoin(바탕, href)
    u = SC._풀기(href)
    return u if u.startswith(("http://", "https://")) else ""


def 링크뽑기(몸통: str, 바탕: str = "", 창구: str = "") -> list:
    """한 쪽에서 결과 링크를 뽑는다. **창구마다 꼴이 달라도 `<a>` 는 같다.**

    창구별 CSS 선택자를 박아 두지 않는다 -- 그것이 바뀌면 말없이 0개가 되고, 0개는
    "못 찾았다" 와 구별이 안 된다. `<a href>` 를 다 훑고 그 쪽 살림 주소만 뺀다.
    """
    out, 본것 = [], set()
    집 = SC._집(urllib.parse.urlsplit(바탕).netloc) if 바탕 else ""
    for href, 속 in _링크.findall(몸통 or ""):
        u = _풀린주소(href, 바탕)
        if not u or u in 본것:
            continue
        if SC._살림.search(u) or (집 and SC._집(urllib.parse.urlsplit(u).netloc) == 집):
            continue
        본것.add(u)
        제목 = _공백.sub(" ", _태그.sub(" ", 속)).strip()
        out.append(찾은것(url=u, 제목=제목, 창구=창구))
    return out


def 찾기(질의: str, 몇: int = 12, 창구: str = "", 틈: float = FT.기본틈) -> 결과:
    """문을 **한꺼번에** 두드려 주소를 모은다. 속은 `dig/search.py` 다.

    예전에는 창구 넷을 **차례로** 돌면서 `몇` 개가 차면 멈췄다. 두 가지가 나빴다 --
    앞 창구가 느리면 뒤 창구는 시작도 못 했고, 앞 창구가 채워 버리면 뒤 창구가 줄
    다른 것을 아예 못 봤다(**다른 문이 다른 것을 준다**는 게 이 도구의 요점인데).

    이제 22개를 한꺼번에 두드리고, 거둔 것을 **물음의 말로 매겨** 위에서부터 준다.
    """
    골라 = [_별명.get(창구, 창구)] if 창구 else None
    응답들, 뽑은것들, 거둔것 = SC.찾기(질의, 틈, 골라, 몇 or 0)

    r = 결과(질의=질의)
    # 어느 문이 몇 개를 줬나. **못 받은 문은 까닭을 남긴다** -- 빈손과 '403 이라
    # 못 받았다' 는 다른 말이고, 뒤쪽만이 다음에 무엇을 할지 알려 준다.
    센것: dict = {}
    for d in 거둔것:
        센것[d.get("어디서") or ""] = 센것.get(d.get("어디서") or "", 0) + 1
    for 답 in 응답들:
        이름 = getattr(답, "이름", "") or 답.url[:40]
        if 답.됐나:
            r.창구별[이름] = f"{센것.get(답.최종url or 답.url, 0)}개"
        else:
            r.창구별[이름] = 답.왜
    for d in 거둔것:
        r.것들.append(찾은것(url=d["주소"], 제목=d.get("글", ""),
                            창구=d.get("어디서", "")))
    r.것들 = r.것들[:몇] if 몇 else r.것들
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="질의로 주소를 찾는다 (dig 의 첫 걸음)")
    ap.add_argument("질의", nargs="+")
    ap.add_argument("--몇", dest="몇", type=int, default=12)
    ap.add_argument("--창구", default="", help=f"{' · '.join(n for n, _ in 창구들())}")
    ap.add_argument("--틈", dest="틈", type=float, default=FT.기본틈)
    ap.add_argument("--json", dest="asjson", action="store_true")
    a = ap.parse_args(argv)

    r = 찾기(" ".join(a.질의), a.몇, a.창구, a.틈)
    if a.asjson:
        print(json.dumps({"질의": r.질의, "창구별": r.창구별,
                          "것들": [x.__dict__ for x in r.것들]},
                         ensure_ascii=False, indent=2))
        return 0 if r.것들 else 3

    print(f"# {r.질의}")
    for 이름, 말 in r.창구별.items():
        print(f"  [{이름}] {말}")
    print()
    for i, x in enumerate(r.것들, 1):
        print(f"{i:>2}. {x}")
    if not r.것들:
        print("\n**한 창구도 답하지 않았다.** 위의 까닭이 다음에 무엇을 할지 알려 준다 --")
        print("  프록시가 끊었다 -> 이 환경의 나가는 길이 막힌 것. 다른 데서 돌려라")
        print("  403/429       -> 그 창구가 막은 것. `--창구` 로 다른 데를 써 보라")
        return 3
    print(f"\n이제 캔다:  python3 dig/run.py --url '{r.것들[0].url}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
