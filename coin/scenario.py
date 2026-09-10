"""**시나리오를 뽑는다 -- 확률은 원장이 정하고, 모델은 한 글자도 안 정한다.**

    python3 coin/scenario.py --자산 BTC --유형 규제금지 --지평 7
    python3 coin/scenario.py --지금            24시간 뉴스에서 지금 걸린 유형으로

## 무엇을 하나

"이번에 무슨 일이 날 수 있나" 에 답하는 자리다. 그런데 **답은 하나가 아니라 여럿**이고,
각각에 확률이 붙는다. 그 확률은 **그 유형의 과거 표본이 실제로 어디에 떨어졌는가**의
비율이다. 모델이 "가능성이 높다" 고 말해서 높은 것이 아니다.

## 칸을 어떻게 가르나 -- 여기에 숫자를 안 박는다

"+5% 넘게 오른다" 같은 칸을 손으로 정하면 그 5 가 어디서 왔는지 아무도 못 말한다.
그래서 칸은 **널 분포가 스스로 정한다**:

    아무 날이나 골랐을 때의 지평일 수익률을 모아 5등분한다
    -> 그 네 개의 경계가 칸이 된다

이렇게 하면 **아무 일도 안 일어났을 때 각 칸의 확률이 정확히 20%** 다. 그래서
"이 유형 뒤에는 맨 위 칸이 34% 났다" 는 곧 "기저율보다 14%p 잦다" 로 바로 읽힌다.
경계값은 시장이 정하지 내가 정하지 않는다.

## 확률에 오차막대를 붙인다

n=42 를 다섯 칸에 나누면 칸마다 여덟 개다. 여덟 개로 잰 34% 는 **34%가 아니라
15~58% 어디쯤**이다. 그것을 안 적으면 읽는 사람이 34 를 믿는다. Wilson 구간을
같이 낸다 -- 정규근사는 이런 작은 n 에서 구간이 0 아래로 내려간다.

## 여러 유형이 한꺼번에 걸렸을 때

곱하지 않는다. P(규제금지) x P(해킹) 은 **둘이 독립일 때만** 맞고 시장에서 그런 일은
없다. 대신 **둘 다 걸린 날만 골라 직접 잰다.** 표본이 모자라면 그때는 모자란다고
적는다 -- 곱해서 메우면 있지도 않은 정밀도가 생긴다.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import ledger as LG                                         # noqa: E402
from coin import null as NU                                           # noqa: E402


def 윌슨(k: int, n: int, z: float = 1.96) -> tuple:
    """이항 비율의 신뢰구간. n 이 작을 때 정규근사는 0 아래로 샌다."""
    if not n:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    가운데 = (p + z * z / (2 * n)) / d
    폭 = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, 가운데 - 폭), min(1.0, 가운데 + 폭))


def 칸경계(계열, 지평: int, 칸수: int = 5) -> list:
    """**널이 칸을 정한다.** 아무 날이나 골랐을 때의 수익률을 칸수 등분한 경계."""
    값 = [계열.수익(d, 지평) for d in 계열.살수있는날들(지평)]
    값 = sorted(v for v in 값 if v is not None)
    if len(값) < 칸수 * 4:
        return []
    return [값[int(i * len(값) / 칸수)] for i in range(1, 칸수)]


def _칸번호(v: float, 경계: list) -> int:
    for i, b in enumerate(경계):
        if v < b:
            return i
    return len(경계)


def _이름(i: int, 칸수: int, 경계: list) -> str:
    아래 = f"{경계[i-1]*100:+.1f}%" if i > 0 else "그 아래"
    위 = f"{경계[i]*100:+.1f}%" if i < len(경계) else "그 위"
    끝 = ("크게 내림", "내림", "제자리", "오름", "크게 오름")
    말 = 끝[min(i, len(끝) - 1)] if 칸수 == 5 else f"{i+1}번째 칸"
    if i == 0:
        return f"{말} ({위} 미만)"
    if i == len(경계):
        return f"{말} ({아래} 이상)"
    return f"{말} ({아래} ~ {위})"


def 뽑기(계열, 잰것: dict, 칸수: int = 5, 최소칸: int = 3) -> dict:
    """잰것 하나 -> 시나리오 목록. 확률은 표본 비율이고 오차막대가 붙는다."""
    수익 = [v for v in (잰것.get("수익들") or []) if v is not None]
    if not 수익:
        수익 = [계열.수익(d, 잰것["지평"]) for d in (잰것.get("날들") or [])]
        수익 = [v for v in 수익 if v is not None]
    n = len(수익)
    칸수 = max(최소칸, min(칸수, n // 6 or 최소칸))
    경계 = 칸경계(계열, 잰것["지평"], 칸수)
    if not 경계 or not n:
        return {"잰것": LG.열쇠(잰것), "n": n, "시나리오": [],
                "왜": "칸을 못 갈랐다 -- 가격 원장이 짧다"}
    통 = [0] * (len(경계) + 1)
    for v in 수익:
        통[_칸번호(v, 경계)] += 1
    널확률 = 1.0 / (len(경계) + 1)
    시나리오 = []
    for i, k in enumerate(통):
        p = k / n
        아래, 위 = 윌슨(k, n)
        속 = [v for v in 수익 if _칸번호(v, 경계) == i]
        시나리오.append({
            "칸": i, "이름": _이름(i, 칸수, 경계),
            "확률": p, "구간": (아래, 위), "표본": k, "n": n,
            "널확률": 널확률, "초과확률": p - 널확률,
            "그칸중앙": NU.중앙(속) if 속 else float("nan"),
            # **구간이 널확률을 품으면 '기저율과 다르다' 고 말할 수 없다**
            "널과다른가": not (아래 <= 널확률 <= 위),
        })
    시나리오.sort(key=lambda s: -s["확률"])
    return {"잰것": LG.열쇠(잰것), "유형": 잰것["유형"], "자산": 잰것["자산"],
            "지평": 잰것["지평"], "n": n, "칸수": len(통), "경계": 경계,
            "시나리오": 시나리오, "왜": ""}


def 겹친것(사건들: list, 유형들: list, 자산: str, 창시간: float = 48.0) -> list:
    """**여러 유형이 같이 걸린 날만.** 곱하지 않고 직접 고른다."""
    from coin.price import _때
    by = {}
    for e in 사건들:
        if e.get("자산") != 자산:
            continue
        by.setdefault(e.get("유형"), []).append(e)
    첫 = by.get(유형들[0]) or []
    out = []
    for e in 첫:
        t = _때(e["최초"])
        ok = True
        for u in 유형들[1:]:
            if not any(abs((_때(x["최초"]) - t).total_seconds()) / 3600 <= 창시간
                       for x in (by.get(u) or [])):
                ok = False
                break
        if ok:
            out.append(e)
    return out


def 줄(s: dict) -> str:
    별 = "*" if s["널과다른가"] else " "
    return (f"    {s['확률']*100:5.1f}%{별} [{s['구간'][0]*100:4.1f}~{s['구간'][1]*100:4.1f}%] "
            f"기저율 {s['널확률']*100:.0f}% ({s['초과확률']*100:+.1f}%p) "
            f"· 표본 {s['표본']}/{s['n']} · 그 칸 중앙 {s['그칸중앙']*100:+.2f}% "
            f"· {s['이름']}")


def 적기(뭉치: dict) -> str:
    if not 뭉치["시나리오"]:
        return f"  {뭉치.get('유형','?')}: {뭉치['왜']}"
    머 = (f"  {뭉치['유형']}/{뭉치['자산']}/D+{뭉치['지평']} · 표본 {뭉치['n']}개를 "
          f"{뭉치['칸수']}칸으로 (칸은 아무 날이나 골랐을 때의 분포가 정했다)")
    return "\n".join([머] + [줄(s) for s in 뭉치["시나리오"]])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--유형", default="")
    ap.add_argument("--지평", type=int, default=7)
    ap.add_argument("--칸수", type=int, default=5)
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)
    from coin import price as PR
    원장 = LG.불러오기(a.원장 or None)
    잰것 = LG.찾기(원장, a.유형, a.자산, a.지평)
    if not 잰것:
        print("그런 잰것이 없다 (미검증이거나 안 쟀다)", file=sys.stderr)
        return 3
    c = PR.계열(PR.불러오기(a.자산))
    if not len(c):
        print(f"가격 원장이 없다: {a.자산}", file=sys.stderr)
        return 3
    for r in 잰것:
        print(적기(뽑기(c, r, a.칸수)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
