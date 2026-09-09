"""**거꾸로 본다 -- 큰 움직임에서 시작해 뭐가 있었나를 센다.**

    python3 coin/hunt.py --자산 BTC --지평 7
    python3 coin/hunt.py --자산 BTC --지평 7 --아래   급락 쪽

## 이것은 잰 값이 아니라 **후보 목록**이다

`event.py` 는 앞으로 본다 -- "이 뉴스가 뜨면 뒤에 뭐가". 여기는 거꾸로다 --
"크게 오른 날 앞에 뭐가 있었나". 둘은 **다른 물음**이고, 거꾸로 보는 쪽에는
이 저장소가 내내 막아 온 바로 그 함정이 있다.

    앞으로 본다   P(급등 | 뉴스)   <- 우리가 알고 싶은 것
    거꾸로 본다   P(뉴스 | 급등)   <- 여기서 나오는 것

**이 둘은 전혀 다르다.** 급등 스무 번을 놓고 "열두 번 앞에 규제 뉴스가 있었다"
(60%)를 얻어도, 규제 뉴스가 원래 흔하면 그 60%는 아무 뜻이 없다. 규제 뉴스가 이틀에
한 번 뜨는 것이라면 **아무 날이나 골라도 60%** 다.

그래서 여기서 내는 것은 **들림(lift)** 이다:

    들림 = P(뉴스 | 큰 움직임) / P(뉴스 | 아무 날)

들림이 1 이면 아무 뜻이 없다. 그리고 들림이 2 여도 그것은 **아직 잰 값이 아니다** --
큰 움직임만 골라 본 것이라 사후 선택이 들어 있다.

## 그래서 무엇에 쓰나 -- 무엇을 잴지 고르는 데 쓴다

지금 `tag.py` 의 유형 열셋은 **내가 도메인 지식으로 적은 것**이다. 그것이 맞는다는
보장이 없고, 유형을 늘리면 다중비교 예산만 먹는다(유형 13 x 자산 5 x 지평 5 = 325).

거꾸로 보기는 **예산을 어디에 쓸지** 알려 준다. 큰 움직임 앞에 실제로 자주 있던
유형을 골라 `event.py` 로 **앞으로 다시 재면**, 사후 선택이 안 들어간다.

    거꾸로 본다  -> 후보 (여기)          가설을 만든다
    앞으로 잰다  -> 잰것 (event.py)      널 · 겹침 · BH 가 다 걸린다

이 파일이 내는 것은 `corpus/후보유형.json` 이고, **`ledger.py` 도 `gate.py` 도
이 파일을 안 읽는다.** 읽으면 사후 선택이 원장으로 새어 들어간다.

## 이 자가 언제 못 쓰는가 -- 천장

들림에는 **천장**이 있다. 그 유형이 아무 날에도 흔하면(p0 이 크면) 들림은 아무리
잘해도 `1/p0` 을 못 넘는다.

    실측: '고래이동' 이 아무 날의 90% 에 있으면 천장이 1.1 배다.
          그 유형이 완벽한 신호여도 들림은 1.1 로 찍힌다 -- 아무것도 못 가른다.

    실측: 신호를 +12% 로 심은 '규제금지' 도 들림 1.10 이었다.
          유형이 22일에 한 번(창 3일이면 아무 날의 18%)이라 천장이 5.5 였고,
          거기서 절반쯤 맞힌 것이 1.10 으로 보인 것이다.

**그래서 거꾸로 보기는 드문 유형에만 쓸모가 있다.** 흔한 유형은 `못믿음` 으로 찍고,
그 수를 근거로 아무것도 고르지 않는다. 이것이 이 파일의 제일 큰 한계이고, 숨기면
"들림 1.1 배" 가 뭔가 있는 것처럼 읽힌다.

## 문턱을 안 박는다

"급등 = +20%" 같은 것을 적으면 그 20 이 어디서 왔는지 아무도 못 말한다. 여기서
큰 움직임은 **그 계열 자기 분포의 위/아래 몫**이다(기본 10%). `regime.py` ·
`scenario.py` 와 같은 자다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin.price import _때                                            # noqa: E402

길 = Path(__file__).resolve().parent / "corpus/후보유형.json"


def 큰움직임(계열, 지평: int, 몫: float = 0.10, 아래: bool = False) -> list:
    """**문턱이 아니라 몫이다.** 자기 분포의 위(또는 아래) 몫에 드는 날."""
    쓸날 = 계열.살수있는날들(지평)
    값 = [(d, 계열.수익(d, 지평)) for d in 쓸날]
    값 = [(d, v) for d, v in 값 if v is not None]
    if len(값) < 30:
        return []
    값.sort(key=lambda x: x[1], reverse=not 아래)
    return [d for d, _ in 값[:max(1, int(len(값) * 몫))]]


def 앞선유형(사건들: list, 날들: list, 창일: int = 3) -> dict:
    """그 날들 **앞 창일 안에** 어느 유형이 있었나. 날마다 한 번씩만 센다."""
    묶 = {}
    for e in 사건들:
        d = (e.get("최초") or "")[:10]
        if d:
            묶.setdefault(d, set()).add(e.get("유형"))
    셈 = {}
    for d in 날들:
        t = _때(d)
        if t is None:
            continue
        본 = set()
        for k in range(창일 + 1):
            본 |= 묶.get((t - timedelta(days=k)).strftime("%Y-%m-%d"), set())
        for 유형 in 본:
            셈[유형] = 셈.get(유형, 0) + 1
    return 셈


def 들림(계열, 사건들: list, 지평: int = 7, 몫: float = 0.10,
        창일: int = 3, 아래: bool = False, 최소: int = 5) -> list:
    """(유형, 큰움직임 앞 비율, 아무 날 비율, 들림, n). **잰 값이 아니라 후보다.**"""
    큰날 = 큰움직임(계열, 지평, 몫, 아래)
    모든날 = 계열.살수있는날들(지평)
    if not 큰날 or not 모든날:
        return []
    앞 = 앞선유형(사건들, 큰날, 창일)
    바탕 = 앞선유형(사건들, 모든날, 창일)          # **대조군** -- 이것이 없으면 거짓말이다
    out = []
    for 유형, n in 앞.items():
        p1 = n / len(큰날)
        p0 = (바탕.get(유형, 0) / len(모든날)) if 모든날 else 0.0
        if 바탕.get(유형, 0) < 최소:
            continue
        # **천장 = 1/p0.** 그 유형이 아무 날에도 흔하면 들림이 아무리 커도 이 값을
        # 못 넘는다. 실측: 고래이동이 아무 날의 90% 에 있으면 천장이 1.1 이라, 완벽한
        # 신호여도 들림이 1.1 이다 -- 그 수로는 아무것도 못 가른다.
        천장 = (1.0 / p0) if p0 else float("inf")
        out.append({"유형": 유형, "큰움직임앞": p1, "아무날": p0,
                    "들림": (p1 / p0) if p0 else float("inf"), "천장": 천장,
                    "못믿음": 천장 < 2.0,
                    "n": n, "큰날수": len(큰날), "바탕n": 바탕.get(유형, 0)})
    out.sort(key=lambda x: -x["들림"])
    return out


def 적기(것들: list, 자산: str, 지평: int, 아래: bool, 경로=None) -> Path:
    p = Path(경로) if 경로 else 길
    p.parent.mkdir(parents=True, exist_ok=True)
    본 = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"후보": []}
    본["후보"] = [x for x in 본.get("후보", [])
                 if not (x["자산"] == 자산 and x["지평"] == 지평 and x["아래"] == 아래)]
    본["후보"] += [dict(x, 자산=자산, 지평=지평, 아래=아래) for x in 것들]
    본["적은때"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    본["경고"] = ("이것은 **잰 값이 아니라 후보**다. 큰 움직임만 골라 본 것이라 "
                 "사후 선택이 들어 있다. event.py 로 앞으로 다시 재야 잰 값이 된다.")
    p.write_text(json.dumps(본, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def 줄(x: dict) -> str:
    들 = x["들림"]
    if x.get("못믿음"):
        return (f"    {x['유형']:<14} 큰움직임 앞 {x['큰움직임앞']*100:5.1f}% · "
                f"아무 날 {x['아무날']*100:5.1f}% · 들림 {들:.2f}배 "
                f"-- **못 믿는다: 이 유형은 아무 날에도 흔해서 천장이 "
                f"{x['천장']:.2f}배다**")
    표 = "  " if 들 < 1.3 else ("* " if 들 < 2 else "**")
    return (f"  {표}{x['유형']:<14} 큰움직임 앞 {x['큰움직임앞']*100:5.1f}% · "
            f"아무 날 {x['아무날']*100:5.1f}% · **들림 {들:.2f}배** "
            f"(천장 {x['천장']:.1f}) · {x['n']}/{x['큰날수']}건")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--지평", type=int, default=7)
    ap.add_argument("--몫", type=float, default=0.10)
    ap.add_argument("--창일", type=int, default=3)
    ap.add_argument("--아래", action="store_true", help="급락 쪽을 본다")
    ap.add_argument("--사건", default="")
    a = ap.parse_args(argv)

    from coin import price as PR
    원 = PR.불러오기(a.자산)
    if not 원:
        print(f"가격 원장이 없다: {a.자산}", file=sys.stderr)
        return 3
    c = PR.계열(원)
    사건p = Path(a.사건) if a.사건 else Path(__file__).resolve().parent / "corpus/events.json"
    사건 = json.loads(사건p.read_text(encoding="utf-8")).get("사건", []) if 사건p.exists() else []
    if not 사건:
        print("사건 원장이 없다 -- coin/run.py --채우기", file=sys.stderr)
        return 3

    것들 = 들림(c, 사건, a.지평, a.몫, a.창일, a.아래)
    쪽 = "급락" if a.아래 else "급등"
    큰날 = 큰움직임(c, a.지평, a.몫, a.아래)
    if 큰날:
        극 = c.수익(큰날[-1], a.지평)
        print(f"{쪽} {len(큰날)}일 (자기 분포의 {'아래' if a.아래 else '위'} "
              f"{a.몫*100:.0f}% · 문턱 {극*100:+.1f}%) 앞 {a.창일}일에 무엇이 있었나\n")
    if not 것들:
        print("  셀 것이 없다 -- 사건 원장이 얇다")
        return 3
    for x in 것들:
        print(줄(x))
    p = 적기(것들, a.자산, a.지평, a.아래)
    print(f"\n  -> {p}")
    print("  **이것은 잰 값이 아니라 후보다.** 큰 움직임만 골라 본 것이라 사후 선택이")
    print("  들어 있다. 들림이 2배여도 그것은 P(뉴스|급등)이지 P(급등|뉴스)가 아니다.")
    print(f"  들림이 큰 유형을 골라 **앞으로 다시 재라**:")
    for x in 것들[:3]:
        print(f"      python3 coin/event.py --재기 --자산 {a.자산} --유형 {x['유형']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
