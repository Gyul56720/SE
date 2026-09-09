"""**질의 -> 주소 -> 문항 원장.** 망은 안 탄다.

    python3 tests/test_jaso_find.py

이 컨테이너는 나가는 길이 막혀 있다(프록시 CONNECT 403). `dig/fetch.한번` 을 갈아
끼워 받는 길을 검사하고, 뽑는 길은 진짜 쪽 꼴로 검사한다 -- `tests/test_dig.py` 와
같은 수다.

**붙드는 것이 둘이다.**

  1. **한 창구가 막혀도 다음으로 간다.** 하나 막혔다고 빈손으로 돌아오면, 다른 창구가
     답하는데도 "못 찾았다" 가 된다.
  2. **출처 없는 문항은 원장이 안 받는다.** 출처 없는 문항은 내가 지어낸 문항과
     구별이 안 되고, 지어낸 문항으로 만든 질문은 있지도 않은 공고에 맞춰 사용자의
     시간을 쓰게 한다.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import fetch as DF                                       # noqa: E402
from dig import find as FD                                        # noqa: E402
from jaso import corpus as CP                                     # noqa: E402
from jaso import fetch as JF                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


검색쪽 = """<html><body>
<a class="result__a" href="/l/?uddg=https%3A%2F%2Frecruit.example.com%2Fnotice%2F7">
  무봉테크 2026 상반기 신입 채용</a>
<a href="https://blog.example.net/jasoseo-guide">자소서 작성법 정리</a>
<a href="https://duckduckgo.com/settings">설정</a>
<a href="/about">이 사이트</a>
</body></html>"""

공고쪽 = """<html><body><h1>2026 상반기 신입 채용</h1>
<ul>
<li>1. 본인이 지원한 직무에 필요한 역량은 무엇이라고 생각하며, 이를 갖추기 위해
어떤 노력을 했는지 구체적인 경험을 바탕으로 기술해 주십시오. (1,000자 이내)</li>
<li>2. 팀으로 일하며 겪은 갈등과 그 해결 과정을 서술하시오. (700자)</li>
<li>쿠키 사용에 동의해 주십시오</li>
</ul></body></html>"""

진짜한번 = DF.한번


def 가짜(url, 헤더, 틈=20.0):
    if "duckduckgo" in url or "bing" in url or "mojeek" in url:
        if "lite" in url:                       # 한 창구는 막힌 것으로 둔다
            return DF.응답(url=url, 코드=429, 왜="HTTP 429 -- 너무 잦다")
        return DF.응답(url=url, 최종url=url, 코드=200, 몸통=검색쪽, 꼴="text/html")
    if "recruit.example.com" in url:
        return DF.응답(url=url, 최종url=url, 코드=200, 몸통=공고쪽, 꼴="text/html")
    return DF.응답(url=url, 코드=404, 왜="HTTP 404 -- 없다")


DF.한번 = 가짜
try:
    print("── 감싼 주소를 푼다 ──────────────────────────────────")
    got = FD.링크뽑기(검색쪽, "https://html.duckduckgo.com/html/", "ddg")
    urls = [x.url for x in got]
    ok("https://recruit.example.com/notice/7" in urls,
       "**DDG 가 `/l/?uddg=` 로 감싼 주소를 푼다** -- 안 풀면 검색 쪽 안으로만 돈다")
    ok("https://blog.example.net/jasoseo-guide" in urls, "맨 주소도 그대로 받는다")
    ok(not any("duckduckgo" in u for u in urls),
       "검색 쪽 자기 살림 주소는 뺀다")
    ok(got[0].제목.startswith("무봉테크"), "제목도 같이 가져온다")

    print("\n── 한 창구가 막혀도 다음으로 간다 ──────────────────────")
    r = FD.찾기("자기소개서 문항", 몇=5)
    ok(r.것들, f"주소 {len(r.것들)}개를 찾았다")
    ok("429" in str(r.창구별.get("ddg-lite", "")),
       f"막힌 창구는 까닭을 남긴다: {r.창구별.get('ddg-lite')}")
    ok(any("개" in str(v) for v in r.창구별.values()),
       "**답한 창구가 하나라도 있으면 빈손이 아니다**")
    ok(len({x.url for x in r.것들}) == len(r.것들), "같은 주소를 두 번 안 담는다")

    print("\n── 쪽에서 문항을 캔다 ─────────────────────────────────")
    문항, 왜 = JF.한쪽에서("https://recruit.example.com/notice/7", "무봉테크")
    ok(len(문항) == 2, f"문항 {len(문항)}개 (쿠키 안내문은 안 담긴다)")
    ok(all(q.출처 for q in 문항), "문항마다 출처가 붙는다")
    ok(any("1,000자" in q.글 or "1000자" in q.글 for q in 문항), "글자 수까지 딸려 온다")
    ok(문항[0].쪼갠것().상한 == 1000,
       f"쪼개면 상한이 읽힌다 ({문항[0].쪼갠것().상한})")

    print("\n── 안 받는 곳 ─────────────────────────────────────────")
    보고 = JF.받기(urls=["https://합격자소서.example.com/x"], 몇=1)
    ok("안 받는 곳" in str(보고["쪽별"]),
       "**남의 합격 자소서 본문이 있는 곳은 안 받는다** -- 표절이지 참고가 아니다")

    print("\n── 원장은 출처 없는 문항을 안 받는다 ────────────────────")
    with tempfile.TemporaryDirectory() as d:
        ok(CP.담기(CP.문항뽑기(공고쪽, ""), d) is None, "출처가 비면 안 담는다")
        p = CP.담기(문항, d)
        ok(p and p.exists(), f"출처가 있으면 담는다 ({p.name if p else '-'})")
        L = CP.읽기(d)
        ok(len(L) == 2, f"되읽으면 {len(L)}개")
        ok(all(q.출처 and q.받은날 for q in L.문항들), "출처와 받은날이 살아 있다")
        ok(set(L.갈래별()) & {"지목", "경험", "갈등"},
           f"요구 갈래로 갈린다: {sorted(L.갈래별())}")
    ok(len(CP.읽기("/그런/데는/없다")) == 0, "없는 디렉터리는 빈 원장 (안 죽는다)")

    print("\n── 망이 막히면 그렇게 말한다 ───────────────────────────")
    DF.한번 = lambda url, 헤더, 틈=20.0: DF.응답(
        url=url, 왜="프록시가 끊었다 -- 이 환경의 나가는 길이 막혔다")
    r = FD.찾기("무엇이든", 몇=3)
    ok(not r.것들 and all("프록시" in str(v) for v in r.창구별.values()),
       "**빈손과 '막혔다' 는 다른 말이다** -- 뒤쪽만 다음에 무엇을 할지 알려 준다")
finally:
    DF.한번 = 진짜한번

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
