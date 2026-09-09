"""**긁어서 다 내놓는다.**

    python3 dig/run.py --url '<주소>' [<주소> ...]     # 앞문 + 곁문, 뽑은 것 전부
    python3 dig/run.py --url '<주소>' --앞문만          # 곁문 안 두드린다 (빠르다)
    python3 dig/run.py --url '<주소>' --따라 12         # 안쪽 링크까지 판다
    python3 dig/run.py --url '<주소>' --json            # 통째로 JSON
    python3 dig/run.py --url '<주소>' --찾 가격,메뉴     # 그 말이 든 자리만 추려서도

    끝값 0  뭐라도 받았다    3  한 쪽도 못 받았다

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

따라기본 = 0
따라상한 = 40


def 안쪽링크(뽑은것: dict, 바탕url: str, 몇: int) -> list:
    """**같은 집 안**으로만 더 판다. 남의 집까지 가면 끝이 없다.

    고르는 규칙은 꼴뿐이다 -- 글자가 있고, 같은 host 이고, 파일이 아닌 것. 무엇이
    중요한지 여기서 안 정한다(정하면 그것이 하드코딩이다).
    """
    try:
        바탕 = urllib.parse.urlsplit(바탕url)
    except ValueError:
        return []
    나온것, 본것 = [], set()
    안볼것 = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".css", ".js",
              ".ico", ".woff", ".woff2", ".mp4", ".zip", ".pdf")
    for L in 뽑은것.get("링크") or []:
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
        나온것.append(u)
        if len(나온것) >= 몇:
            break
    return 나온것


def 캐기(urls: list, 앞문만: bool = False, 따라: int = 0, 틈: float = FT.기본틈) -> tuple:
    """(응답들, 뽑은것들). **하나가 터져도 나머지는 온다.**"""
    응답들: list = []
    for u in urls:
        응답들 += FT.캐기(u, 곁문까지=not 앞문만, 틈=틈) if not 앞문만 else [FT.받기(u, 틈)]
    뽑은것들 = [EX.뽑기(r.몸통, r.꼴, r.최종url or r.url) for r in 응답들 if r.몸통]

    if 따라 > 0 and 뽑은것들:
        더볼것: list = []
        for x, u in zip(뽑은것들, [r.최종url or r.url for r in 응답들 if r.몸통]):
            더볼것 += 안쪽링크(x, u, min(따라, 따라상한))
        더볼것 = list(dict.fromkeys(더볼것))[:min(따라, 따라상한)]
        if 더볼것:
            더받음 = FT.여럿(더볼것, 틈=틈, 벌수=1)
            응답들 += 더받음
            뽑은것들 += [EX.뽑기(r.몸통, r.꼴, r.최종url or r.url)
                        for r in 더받음 if r.몸통]
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
            print(f"  {이름:<5} ({len(목록)}) {' · '.join(str(v) for v in 목록[:40])}"
                  + (f"  … +{len(목록) - 40}" if len(목록) > 40 else ""))

    # ── 묻힌 표(JSON-LD). 메뉴· 값· 평점· 영업시간이 여기 있다 ──────────
    for i, 평 in enumerate(묶["묻힌표"], 1):
        if not 평:
            continue
        print(f"\n## 묻힌표 {i} (schema.org · {len(평)}칸)")
        for k, v in 평.items():
            print(f"  {k} = {str(v)[:200]}")

    for i, j in enumerate(묶["묻힌json"], 1):
        칸 = j.get("칸") or {}
        if not 칸:
            continue
        print(f"\n## 묻힌json {i} [{j.get('어디')}] ({len(칸)}칸)")
        for k, v in list(칸.items())[:400]:
            print(f"  {k} = {str(v)[:160]}")
        if len(칸) > 400:
            print(f"  … {len(칸) - 400}칸 더 (--json 으로 전부)")

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
            print(f"  {k} = {str(v)[:200]}")
    _찍기("링크", [f"{L['글'][:60]}  ->  {L['href'][:110]}" for L in 묶["링크"]], 60)

    if 찾을말:
        print(f"\n## 찾은 말: {', '.join(찾을말)}")
        본 = 0
        for x in 뽑은것들:
            글 = x.get("글") or ""
            for 말 in 찾을말:
                for m in [i for i in range(len(글)) if 글.startswith(말, i)][:12]:
                    print(f"  …{글[max(0, m - 90):m + 130]}…")
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
    ap.add_argument("--앞문만", dest="front", action="store_true",
                    help="곁문(m· amp· json· 아카이브)을 안 두드린다")
    ap.add_argument("--따라", dest="follow", type=int, default=따라기본,
                    help=f"안쪽 링크를 몇 개까지 더 팔지 (최대 {따라상한})")
    ap.add_argument("--찾", dest="find", default="", help="그 말이 나온 자리를 따로 보여 준다")
    ap.add_argument("--틈", dest="timeout", type=float, default=FT.기본틈)
    ap.add_argument("--json", dest="asjson", action="store_true", help="통째로 JSON")
    a = ap.parse_args(argv)

    if not a.urls:
        print("주소를 줘라.")
        print("  python3 dig/run.py --url '<주소>' [<주소> ...]")
        print("  python3 dig/run.py --url '<주소>' --따라 12 --찾 가격,메뉴")
        return 3

    응답들, 뽑은것들 = 캐기(a.urls, a.front, a.follow, a.timeout)
    if a.asjson:
        print(json.dumps({
            "받은곳": [{"url": r.url, "코드": r.코드, "꼴": r.꼴, "길이": len(r.몸통),
                      "쓴헤더": r.쓴헤더, "왜": r.왜} for r in 응답들],
            "쪽": 뽑은것들, "묶음": EX.합치기(뽑은것들) if 뽑은것들 else {},
        }, ensure_ascii=False, indent=1, default=str))
        return 0 if 뽑은것들 else 3

    내놓기(응답들, 뽑은것들, [w.strip() for w in a.find.split(",") if w.strip()])
    return 0 if 뽑은것들 else 3


if __name__ == "__main__":
    raise SystemExit(main())
