"""**질의 -> 주소.** `dig/` 에 빠져 있던 첫 걸음.

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

# 창구. (이름, 주소틀, 링크를 뽑는 자)
창구들 = (
    ("ddg", "https://html.duckduckgo.com/html/?q={q}"),
    ("ddg-lite", "https://lite.duckduckgo.com/lite/?q={q}"),
    ("bing", "https://www.bing.com/search?q={q}&setlang=ko"),
    ("mojeek", "https://www.mojeek.com/search?q={q}"),
)

_링크 = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                   re.I | re.S)
_태그 = re.compile(r"<[^>]+>")
_공백 = re.compile(r"\s+")

# 검색 쪽 자기 주소. 결과가 아니라 그 쪽 살림이다.
_자기집 = re.compile(r"(duckduckgo|bing\.com|microsoft|msn\.com|mojeek|"
                     r"google\.[a-z.]+/(?:search|preferences|advanced)|"
                     r"/settings|/preferences|javascript:|mailto:)", re.I)


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
    """검색 쪽이 감싼 주소를 푼다. DDG 는 `/l/?uddg=<주소>` 로 감싼다."""
    href = (href or "").strip()
    if href.startswith("//"):
        href = "https:" + href
    p = urllib.parse.urlsplit(href)
    for 이름 in ("uddg", "u", "url", "q", "r"):
        got = urllib.parse.parse_qs(p.query).get(이름)
        if got and got[0].startswith(("http://", "https://")):
            return urllib.parse.unquote(got[0])
    if href.startswith(("http://", "https://")):
        return href
    if href.startswith("/") and 바탕:
        b = urllib.parse.urlsplit(바탕)
        return f"{b.scheme}://{b.netloc}{href}"
    return ""


def 링크뽑기(몸통: str, 바탕: str = "", 창구: str = "") -> list:
    """한 쪽에서 결과 링크를 뽑는다. **창구마다 꼴이 달라도 `<a>` 는 같다.**

    창구별 CSS 선택자를 박아 두지 않는다 -- 그것이 바뀌면 말없이 0개가 되고, 0개는
    "못 찾았다" 와 구별이 안 된다. `<a href>` 를 다 훑고 그 쪽 살림 주소만 뺀다.
    """
    out, 본것 = [], set()
    for href, 속 in _링크.findall(몸통 or ""):
        u = _풀린주소(href, 바탕)
        if not u or _자기집.search(u) or u in 본것:
            continue
        본것.add(u)
        제목 = _공백.sub(" ", _태그.sub(" ", 속)).strip()
        out.append(찾은것(url=u, 제목=제목, 창구=창구))
    return out


def 찾기(질의: str, 몇: int = 12, 창구: str = "", 틈: float = FT.기본틈) -> 결과:
    """창구를 차례로 두드려 주소를 모은다. **하나가 막히면 다음으로 간다.**"""
    r = 결과(질의=질의)
    q = urllib.parse.quote_plus(질의)
    본주소 = set()
    for 이름, 틀 in 창구들:
        if 창구 and 창구 != 이름:
            continue
        응답 = FT.받기(틀.format(q=q), 틈=틈)
        if not 응답.됐나:
            r.창구별[이름] = 응답.왜
            continue
        got = [x for x in 링크뽑기(응답.몸통, 응답.최종url or 응답.url, 이름)
               if x.url not in 본주소]
        for x in got:
            본주소.add(x.url)
        r.것들.extend(got)
        r.창구별[이름] = f"{len(got)}개"
        if len(r.것들) >= 몇:
            break
    r.것들 = r.것들[:몇] if 몇 else r.것들
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="질의로 주소를 찾는다 (dig 의 첫 걸음)")
    ap.add_argument("질의", nargs="+")
    ap.add_argument("--몇", dest="몇", type=int, default=12)
    ap.add_argument("--창구", default="", help=f"{' · '.join(n for n, _ in 창구들)}")
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
