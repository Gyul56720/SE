"""**긁어서 다 내놓는다.**

    python3 dig/run.py --찾기 '<물음>' --파 6 --따라 10  # **주소를 몰라도 여기서 시작**
    python3 dig/run.py --url '<주소>' [<주소> ...]     # 앞문 + 곁문, 뽑은 것 전부
    python3 dig/run.py --url '<주소>' --앞문만          # 곁문 안 두드린다 (빠르다)
    python3 dig/run.py --url '<주소>' --따라 12         # 안쪽 링크까지 판다
    python3 dig/run.py --url '<주소>' --따라 12 --깊이 3  # **층이 여럿이면 이것**
    python3 dig/run.py --url '<주소>' --json            # 통째로 JSON
    python3 dig/run.py --url '<주소>' --찾 가격,메뉴     # 그 말이 든 자리만 추려서도

    끝값 0  뭐라도 받았다    3  한 쪽도 못 받았다

## 한 번 부르면 끝까지 간다

    --찾기 '중화역 맛집' --파 6 --따라 10 --찾 가격,메뉴,영업시간

한 줄이 이만큼 한다: 스무 남짓한 문을 **한꺼번에** 두드리고 -> 열린 데서 바깥
주소를 거두어 물음의 말로 매기고 -> 위 여섯을 앞문·곁문 다 캐고 -> 그 안쪽
링크까지 열 개 더 판다. 예전에는 이것이 모델이 스스로 이어 붙여야 하는 네 번의
호출이었고, 첫 번째에서 막히면 거기서 끝났다.

## 층이 여럿이면 `--깊이` 를 준다

    목록 쪽 -> 대학별 목록 -> 수기 한 편        <- 두 홉이다

`--따라` 는 **한 홉에서 몇 개를 팔지**이고, `--깊이` 는 **몇 홉을 갈지**다. 둘은
다른 손잡이다 -- `--따라` 를 아무리 키워도 깊이가 1 이면 첫 층에서 멈추고, 그러면
**제목만 잔뜩 얻고 본문은 한 줄도 못 받는다.** 기본이 1 이므로 층이 있는 쪽을
팔 때는 반드시 준다. `--쪽상한`(기본 300)이 고삐다.

## 여기 규율은 `brief/` 와 **반대**다

    brief   검사에 통과하는 것만 원장에 넣는다. 수인 칸이 없으면 거절
    dig     받은 것을 **다 내놓는다.** 거절이 없다

`brief` 가 옳았던 것은 목적이 '이 수를 믿어도 되는가' 였기 때문이다. 여기 목적은
**'무엇이 있는가'** 다. 같은 거절을 여기서 하면 찾아 준 것이 없어진다.

그래서 **줄이지 않는다.** 길면 긴 대로 낸다 -- 줄이는 것은 부르는 쪽 일이고,
여기서 줄이면 줄인 것을 아무도 못 되찾는다.

## 안 하는 것

로그인·유료벽·접근 제어를 뚫지 않는다. 곁문은 **주인이 열어 둔 다른 문**뿐이다
(모바일 쪽· AMP· 그 쪽 JSON 끝점· 공개 아카이브).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dig import extract as EX                                  # noqa: E402
from dig import fetch as FT                                    # noqa: E402
from dig import search as SC                                   # noqa: E402

따라기본 = 0
따라상한 = 40
# **몇 홉까지 파고들 것인가.** 1 이면 예전과 같다(목록 -> 글 한 걸음).
# 실제 쪽은 대개 두세 층이라 1 로는 이름만 얻고 본문에 못 닿는다.
깊이기본 = 1
깊이상한 = 5
# 통틀어 이만큼 받으면 멈춘다. 깊이가 늘면 쪽수는 곱으로 커지므로 고삐가 필요하다 --
# 없으면 `--깊이 3 --따라 40` 한 줄이 한 집을 통째로 긁는다.
쪽상한기본 = 300


def 안쪽후보(뽑은것: dict, 바탕url: str, 찾을말: list = None) -> list:
    """[(값, 주소)] -- **값을 달고** 돌려준다. 자르지 않는다.

    `안쪽링크` 가 주소만 주던 때는 부르는 쪽이 쪽마다 몇 개씩 돌아가며 집을 수밖에
    없었다. 그러면 **좋은 쪽이 굶는다** -- 합격수기 마흔 개가 걸린 목록 쪽이나
    링크 여섯 개짜리 잡다한 쪽이나 한 홉에 하나씩만 가져간다. 값을 같이 주면
    부르는 쪽이 통틀어 견줄 수 있다.
    """
    return _안쪽(뽑은것, 바탕url, 찾을말)


def 안쪽링크(뽑은것: dict, 바탕url: str, 몇: int, 찾을말: list = None) -> list:
    """값 순으로 위에서 `몇` 개. (예전 쓰임 그대로 -- 주소만 준다)"""
    return [u for _v, u in _안쪽(뽑은것, 바탕url, 찾을말)[:몇]]


def _안쪽(뽑은것: dict, 바탕url: str, 찾을말: list = None) -> list:
    """**같은 집 안**으로만 더 판다. 남의 집까지 가면 끝이 없다.

    고르는 규칙은 꼴뿐이다 -- 글자가 있고, 같은 host 이고, 파일이 아닌 것. 무엇이
    중요한지 여기서 안 정한다(정하면 그것이 하드코딩이다).

    ## 차례대로 집지 않는다

    처음엔 문서에 나온 차례대로 앞에서 `몇` 개를 잘랐다. 실제 쪽에서 앞쪽 링크는
    거의 다 머리말이다 -- 홈 · 로그인 · 회사소개 · 이용약관. 그러면 `--따라 12` 가
    예산 열둘을 **통째로 꼬리말 파는 데** 쓴다. 메뉴 · 리뷰 · 상세는 그 뒤에 있는데
    거기까지 가지도 못했다.

    그래서 차례 대신 꼴로 매긴다. 여전히 뜻은 안 본다 -- 물음의 말이 들었나 ·
    얼마나 깊나 · 낱개를 가리키는 꼴인가뿐이다.
    """
    try:
        바탕 = urllib.parse.urlsplit(바탕url)
    except ValueError:
        return []
    낱말 = [w for w in (찾을말 or []) if len(w) >= 2]
    나온것, 본것 = [], set()
    # pdf 는 뺀다 -- 여기 뽑개가 글자로 못 푼다. 껍데기 바이트가 예산만 먹는다.
    안볼것 = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".css", ".js",
              ".ico", ".woff", ".woff2", ".mp4", ".zip", ".pdf")
    # **쪽이 스스로 알려 준 문을 먼저 본다.** `<link rel=alternate>` 은 피드고
    # (글 본문이 통째로 온다), `rel=next` 는 다음 쪽이다. 사람이 눈으로 보는
    # `<a>` 가 아니라 **기계에게 하는 말**이라 값이 높다. 읽어 놓고 안 가면
    # 읽으나 마나다.
    걸린것 = [{"href": v, "글": k[5:]}
             for k, v in (뽑은것.get("머리표") or {}).items()
             if k.startswith("link:") and isinstance(v, str)]
    for L in 걸린것 + (뽑은것.get("링크") or []):
        h = (L.get("href") or "").strip()
        if not h or h.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        u = urllib.parse.urljoin(바탕url, h)
        p = urllib.parse.urlsplit(u)
        if p.netloc != 바탕.netloc or p.scheme not in ("http", "https"):
            continue
        if p.path.lower().endswith(안볼것):
            continue
        u = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
        if u in 본것 or u == 바탕url:
            continue
        본것.add(u)
        # 쪽이 걸어 둔 문에는 얹어 준다 -- 다만 canonical 은 대개 자기 자신이라 뺀다.
        덤 = 30 if (L in 걸린것 and L.get("글") != "canonical") else 0
        나온것.append((SC._값(L.get("글") or "", u, 낱말) + 덤, len(u), u))
    # 값이 같으면 짧은 주소부터 -- 대개 그 쪽이 목록이고 거기서 또 갈래가 난다.
    나온것.sort(key=lambda t: (-t[0], t[1]))
    return [(v, u) for v, _l, u in 나온것]


def 캐기(urls: list, 앞문만: bool = False, 따라: int = 0, 틈: float = FT.기본틈,
        찾을말: list = None, 깊이: int = 깊이기본, 쪽상한: int = 쪽상한기본) -> tuple:
    """(응답들, 뽑은것들). **하나가 터져도 나머지는 온다.**

    `찾을말` 은 거르는 데 안 쓴다 -- 안쪽으로 더 팔 때 **차례를 정하는 데만** 쓴다.
    거르면 그 말이 안 든 자리가 없어지는데, 답은 자주 거기 있다.
    """
    응답들: list = []
    앞것 = [u for u in urls if u]
    if 앞문만:
        응답들 += FT.여럿(앞것, 틈=틈)
    else:
        # **한 주소씩 차례로 캐면 열 곳이 열 배 걸린다.** 곁문까지 치면 곱절이라
        # 결국 한두 곳만 보게 된다 -- 적게 모으는 쪽으로 저절로 기운다.
        for u in 앞것:
            응답들 += FT.캐기(u, 곁문까지=True, 틈=틈)
    뽑은것들 = [EX.뽑기(r.몸통, r.꼴, r.최종url or r.url) for r in 응답들 if r.몸통]

    # ── 안쪽으로 판다. **한 홉이 아니라 `깊이` 홉** ──────────────────
    #
    # 예전엔 이 자리가 `if 따라 > 0:` 한 번이었다. 그래서 `--따라` 를 아무리
    # 키워도 **깊이는 늘 1** 이었다 -- 목록 쪽에서 글 쪽으로 한 걸음이 끝이다.
    # 실제 쪽은 대개 두세 층이다(명예의 전당 -> 대학별 목록 -> 수기 한 편).
    # 그러면 이름만 잔뜩 얻고 본문은 한 줄도 못 받는다. 사용자가 물은 그 자리다:
    # "왜 dig 가 더 깊게 안 들어가지?" -- 못 들어간 것이 아니라 **안 들어가게
    # 짜여 있었다.**
    본주소 = {(r.최종url or r.url) for r in 응답들}
    앞선것, 앞선url = 뽑은것들, [r.최종url or r.url for r in 응답들 if r.몸통]
    for _홉 in range(max(0, 깊이) if 따라 > 0 else 0):
        if len(응답들) >= 쪽상한:
            break
        몫 = min(따라, 따라상한)
        쪽마다 = [안쪽후보(x, u, 찾을말) for x, u in zip(앞선것, 앞선url)]

        # ── 예산을 어떻게 나누나. **여기가 '깊이냐 너비냐' 를 가른다** ──────
        #
        # 처음엔 쪽마다 돌아가며 하나씩 집었다(칸 0 을 전부 -> 칸 1 을 전부 …).
        # 첫 쪽이 예산을 다 먹는 것을 막으려던 것인데 **반대로 지나쳤다**:
        # 합격수기 마흔 개가 걸린 목록 쪽이나 링크 여섯 개짜리 잡다한 쪽이나
        # 똑같이 하나씩 가져간다. 실측 -- 좋은 쪽 하나 + 잡다한 쪽 열아홉에
        # 예산 30 을 나눠 보면
        #
        #     돌아가며   좋은 것  2/30   평균값 13.7
        #     값 순으로  좋은 것 30/30   평균값 84.5
        #
        # 그래서 사용자가 "깊이 5 로 해도 깊이보단 너비가 넓어져" 를 보았다.
        # 깊이를 키워도 홉마다 사방으로 하나씩 퍼지니 좋은 가지를 끝까지 못 판다.
        #
        # 이제 **통틀어 값 순**으로 고르되, 굶김 방지로 예산의 1/4 만 쪽마다
        # 하나씩 떼어 둔다(그 쪽이 함정이면 나머지 3/4 을 안 버리게).
        바닥몫 = max(1, 몫 // 4)
        더볼것 = []
        for 줄 in sorted([r for r in 쪽마다 if r], key=lambda r: -r[0][0])[:바닥몫]:
            if 줄[0][1] not in 본주소:
                본주소.add(줄[0][1])
                더볼것.append(줄[0][1])
        for _v, u in sorted((c for 줄 in 쪽마다 for c in 줄), key=lambda t: -t[0]):
            if len(더볼것) >= 몫:
                break
            if u not in 본주소:
                본주소.add(u)
                더볼것.append(u)
        더볼것 = 더볼것[:max(0, 쪽상한 - len(응답들))][:몫]
        if not 더볼것:
            break
        더받음 = FT.여럿(더볼것, 틈=틈, 벌수=1)
        응답들 += 더받음
        # **다음 홉은 이번에 받은 것에서만 판다.** 앞 홉까지 다시 훑으면 같은
        # 링크를 되풀이해 고르고, 깊이를 늘려도 제자리를 돈다.
        이번것 = [EX.뽑기(r.몸통, r.꼴, r.최종url or r.url) for r in 더받음 if r.몸통]
        뽑은것들 += 이번것
        앞선것 = 이번것
        앞선url = [r.최종url or r.url for r in 더받음 if r.몸통]
        본주소 |= {(r.최종url or r.url) for r in 더받음}
    return 응답들, 뽑은것들


def _찍기(제목: str, 것: list, 최대: int = 0):
    if not 것:
        return
    print(f"\n## {제목} ({len(것)})")
    for x in (것 if not 최대 else 것[:최대]):
        print(f"  {x}")
    if 최대 and len(것) > 최대:
        print(f"  … {len(것) - 최대}개 더")


def 내놓기(응답들: list, 뽑은것들: list, 찾을말: list) -> None:
    print("# 받은 곳")
    for r in 응답들:
        print(f"  {r}")

    if not 뽑은것들:
        print("\n**한 쪽도 못 받았다.** 위의 까닭이 다음에 무엇을 할지 알려 준다 --")
        print("  프록시가 끊었다 -> 이 환경의 나가는 길이 막힌 것. 다른 데서 돌려라")
        print("  403             -> `--앞문만` 을 떼고 곁문을 두드려 보라")
        print("  404             -> 주소가 틀렸다. 그 쪽 검색 쪽부터 받아 보라")
        return

    묶 = EX.합치기(뽑은것들)
    print(f"\n# 뽑은 것  (쪽 {묶['쪽수']}개 · 글 {묶['글길이']}자)")
    if 묶["제목"]:
        print(f"  제목: {묶['제목']}")

    # ── 캔 값. **제일 먼저 낸다** -- 대개 이것을 물어본 것이다 ──────────
    if 묶["캔값"]:
        print("\n## 캔 값")
        for 이름, 목록 in 묶["캔값"].items():
            print(f"  {이름:<5} ({len(목록)}) {' · '.join(str(v) for v in 목록)}")

    # ── 묻힌 표(JSON-LD). 메뉴· 값· 평점· 영업시간이 여기 있다 ──────────
    for i, 평 in enumerate(묶["묻힌표"], 1):
        if not 평:
            continue
        print(f"\n## 묻힌표 {i} (schema.org · {len(평)}칸)")
        for k, v in 평.items():
            print(f"  {k} = {str(v)[:600]}")

    for i, j in enumerate(묶["묻힌json"], 1):
        칸 = j.get("칸") or {}
        if not 칸:
            continue
        print(f"\n## 묻힌json {i} [{j.get('어디')}] ({len(칸)}칸)")
        for k, v in list(칸.items())[:2000]:
            print(f"  {k} = {str(v)[:400]}")
        if len(칸) > 2000:
            print(f"  … {len(칸) - 2000}칸 더 (--json 으로 전부)")

    for i, t in enumerate(묶["표"], 1):
        if not t:
            continue
        print(f"\n## 표 {i} ({len(t)}줄)")
        for r in t:
            print(f"  {r}")

    for i, L in enumerate(묶["목록"], 1):
        if not L:
            continue
        print(f"\n## 목록 {i} ({len(L)})")
        for x in L:
            print(f"  · {x[:220]}")

    _찍기("제목들", 묶["제목들"])
    if 묶["머리표"]:
        print(f"\n## 머리표 ({len(묶['머리표'])})")
        for k, v in 묶["머리표"].items():
            print(f"  {k} = {str(v)[:400]}")
    _찍기("링크", [f"{L['글'][:60]}  ->  {L['href'][:110]}" for L in 묶["링크"]], 250)

    if 찾을말:
        print(f"\n## 찾은 말: {', '.join(찾을말)}")
        본 = 0
        for x in 뽑은것들:
            글 = x.get("글") or ""
            for 말 in 찾을말:
                for m in [i for i in range(len(글)) if 글.startswith(말, i)][:40]:
                    print(f"  …{글[max(0, m - 120):m + 200]}…")
                    본 += 1
        if not 본:
            print("  (받은 글에는 그 말이 없다 -- 다른 곁문이나 안쪽 링크를 보라)")

    # 글은 맨 뒤에. 길어도 자르지 않는다 -- 자르면 자른 것을 못 되찾는다.
    for x in 뽑은것들:
        글 = (x.get("글") or "").strip()
        if 글:
            print(f"\n## 글 [{x.get('url', '')[:70]}] ({len(글)}자)")
            print("  " + 글.replace("\n", "\n  "))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="되는 방법을 다 써서 긁어 온다")
    ap.add_argument("--url", dest="urls", nargs="+", default=[], help="주소 하나 이상")
    ap.add_argument("--찾기", dest="query", default="",
                    help="주소를 모를 때. 열린 검색·API 문을 한꺼번에 두드려 주소를 캔다")
    ap.add_argument("--파", dest="dig_top", type=int, default=0,
                    help="--찾기 로 캔 주소 중 위에서 몇 개를 이어서 팔지")
    ap.add_argument("--문", dest="doors", default="",
                    help="--찾기 에서 쓸 문만 고른다 (쉼표. 이름은 --문목록)")
    ap.add_argument("--망", dest="netcheck", action="store_true",
                    help="이 기계에서 바깥이 되나 -- 문마다 코드·까닭. 끝값 0 되면 된다")
    ap.add_argument("--문목록", dest="list_doors", action="store_true",
                    help="두드릴 문 이름을 낸다")
    ap.add_argument("--앞문만", dest="front", action="store_true",
                    help="곁문(m· amp· json· 아카이브)을 안 두드린다")
    ap.add_argument("--따라", dest="follow", type=int, default=따라기본,
                    help=f"한 홉에서 안쪽 링크를 몇 개나 팔지 (최대 {따라상한})")
    ap.add_argument("--깊이", dest="depth", type=int, default=깊이기본,
                    help=f"몇 홉까지 파고들지 (기본 {깊이기본}, 최대 {깊이상한}). "
                         "목록->대학별->수기 처럼 층이 있으면 2 이상이 필요하다")
    ap.add_argument("--쪽상한", dest="cap", type=int, default=쪽상한기본,
                    help=f"통틀어 이만큼 받으면 멈춘다 (기본 {쪽상한기본})")
    ap.add_argument("--찾", dest="find", default="", help="그 말이 나온 자리를 따로 보여 준다")
    ap.add_argument("--틈", dest="timeout", type=float, default=FT.기본틈)
    ap.add_argument("--json", dest="asjson", action="store_true", help="통째로 JSON")
    a = ap.parse_args(argv)

    if a.list_doors:
        for 이름, 꼴 in SC.틀들():
            print(f"  {이름:<12} {꼴}")
        return 0

    if a.netcheck:
        r = SC.망점검(틈=min(a.timeout, 10.0))
        print(SC.망보고(r))
        return 0 if r["됐나"] else 1

    찾을말 = [w.strip() for w in a.find.split(",") if w.strip()]
    urls = list(a.urls)
    찾은주소: list = []
    검색응답: list = []

    if a.query:
        문 = [x.strip() for x in a.doors.split(",") if x.strip()]
        검색응답, 검색뽑은것, 찾은주소 = SC.찾기(a.query, a.timeout, 문)
        # 물음의 말도 차례를 정하는 데 쓴다 -- 주소를 캔 그 말이 안쪽에서도 같은 말이다.
        찾을말 = 찾을말 or [w for w in a.query.split() if len(w) >= 2]
        열린문 = sum(1 for r in 검색응답 if r.됐나)
        if not a.asjson:
            print(f"# 두드린 문 ({len(검색응답)}개 중 {열린문}개 열림)")
            for r in 검색응답:
                print(f"  [{getattr(r, '이름', '?'):<12}] {r}")
            print(f"\n# 캔 주소 ({len(찾은주소)})")
            for d in 찾은주소:
                print(f"  {d['값']:>4}  {d['주소']}")
                if d["글"]:
                    print(f"        {d['글']}")
        if not 찾은주소 and not urls:
            print("\n**한 문도 안 열렸거나 주소를 한 줄도 못 캤다.** 위의 까닭이 "
                  "다음에 무엇을 할지 알려 준다 -- 그것을 그대로 옮겨라.")
            return 3
        urls += [d["주소"] for d in 찾은주소[:max(0, a.dig_top)]]
        if not urls:
            # 캐기는 했는데 팔지는 말라고 한 것(`--파` 없음). 주소는 이미 위에 냈다.
            if a.asjson:
                print(json.dumps({"물음": a.query, "찾은주소": 찾은주소,
                                  "두드린문": [{"이름": getattr(r, "이름", ""),
                                             "url": r.url, "코드": r.코드,
                                             "왜": r.왜} for r in 검색응답]},
                                 ensure_ascii=False, indent=1, default=str))
            else:
                print("\n**주소만 캤다.** 이어서 파려면 `--파 6` 을 붙여라 -- "
                      "그래야 메뉴· 값· 리뷰· 시간이 나온다.")
            return 0

    if not urls:
        print("주소나 물음을 줘라.")
        print("  python3 dig/run.py --url '<주소>' [<주소> ...]")
        print("  python3 dig/run.py --url '<주소>' --따라 12 --찾 가격,메뉴")
        print("  python3 dig/run.py --찾기 '<물음>' --파 6 --따라 10   # 주소를 모를 때")
        return 3

    응답들, 뽑은것들 = 캐기(urls, a.front, a.follow, a.timeout, 찾을말,
                          min(max(1, a.depth), 깊이상한), a.cap)
    if a.asjson:
        print(json.dumps({
            "받은곳": [{"url": r.url, "코드": r.코드, "꼴": r.꼴, "길이": len(r.몸통),
                      "쓴헤더": r.쓴헤더, "왜": r.왜} for r in 응답들],
            "찾은주소": 찾은주소,
            "쪽": 뽑은것들, "묶음": EX.합치기(뽑은것들) if 뽑은것들 else {},
        }, ensure_ascii=False, indent=1, default=str))
        return 0 if 뽑은것들 else 3

    내놓기(응답들, 뽑은것들, 찾을말)
    return 0 if 뽑은것들 else 3


if __name__ == "__main__":
    raise SystemExit(main())
