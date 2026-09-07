"""**①재현** -- 이 공간이 Strassen 을 품는가. 판정은 LLM 이 아니라 Brent 항등식이다.

    python3 mathdrift/recall.py --n 20          # 앞에서부터 스무 개
    python3 mathdrift/recall.py --only S6,S34   # 짚어서
    python3 mathdrift/recall.py --show          # 지금까지의 판정

## 왜 자를 버리고 이리로 왔나

낱말 겹침으로 인과를 재려 했더니 **자가 뒤집혀 있었다**(실측 2026-09-07, 85개):

  · 부모 이름에 연산자 어휘를 덧붙인 것이 최고점을 받았다 (S9 0.529 · S8 0.471)
  · 이름이 정말 바뀐 것 -- "지수 대역(Exponent Cone)", Strassen 의 점근 스펙트럼 --
    이 "남의 공간" 으로 깎였다 (S6 0.077)

카드를 펼치자 판별자가 이름이 아니라 **되사상**이라는 것이 드러났다:

    S34  "요네다 매몰을 통해 구체적인 텐서 공간과 스펙트럼 사상으로 재해석"   <- 아무 말도 안 한다
    S6   "최적 지수 2인 캔버스 위에서 역으로 텐서의 점근적 구성 방식을 복원"  <- 무엇을 하는지 말한다

되사상이 비었는지는 `space.grade` 가 이미 본다. 그러나 **차 있는데 공허한 것**은 못 본다.
그래서 되사상을 설명으로 받지 않고 **시켜 본다.**

## 무엇을 시키나

`DRIFT.md` 의 보존적 확장 조항이 그대로 시험이 된다 -- *새 설정이 옛 설정을 부정하면
그건 확장이 아니라 다른 체계다.* Strassen(b=2, m=7)을 못 적는 형식화는 행렬곱의 새
관점이 아니라 다른 문제다. 그리고 정답은 이미 저장소에 있다
(`mathmetics/matrix_exponent/benchmarks.json` 의 능력 비후퇴 래칫).

받은 (U, V, W, lambda) 를 `ExactArithVerifier` 로 검산한다 -- **LLM 이 한 방울도 안 들어가는
판정**이다. `mathgen/judge.py` 와 같은 규율이고, 심판은 이미 있는 것을 쓴다(새로 짜면
두 벌이 갈라진다).

## 통과는 약한 증거다 -- 실패가 강한 증거다

모델이 공간을 무시하고 **외운 Strassen 을 그대로 적어도 검산은 통과한다.** 막을 길이
없다. 그래서 이 축은 증명이 아니라 **필요조건 거르개**다:

  · 재현 못 함 -> 이 형식화는 Strassen 을 품지 못한다. **강한 신호**
  · 재현 함    -> 아직 아무것도 모른다. 다음 축(비자명성 · 압축)으로 넘어갈 자격만 생긴다

이 한계를 적어 두는 이유는, 통과율이 높게 나왔을 때 그것을 성과로 읽지 않기 위해서다.
확산 0.85 를 좋은 소식으로 읽었다가 겪은 일이 그것이다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mathmetics" / "matrix_exponent"))

from mathdrift import space as SP                                     # noqa: E402
from mathdrift import spread as SPR                                   # noqa: E402

# 시금석. b=2 m=7 은 래칫에 박혀 있는 능력이다(benchmarks.json).
B, M = 2, 7
N = B * B


def prompt(rec: dict) -> str:
    cells = "\n".join(f"    {f}: {rec.get(f) or '(비어 있음)'}" for f in SP.FIELDS)
    return f"""아래는 행렬곱 복잡도 문제의 한 **형식화(탐색공간)** 다.

{cells}

물음 하나. **이 공간에서 Strassen 의 2x2 곱셈 7회 스킴을 적을 수 있는가.**

적을 수 있으면 두 가지를 내라.

  1. `점` -- 이 공간의 **자기 표기로** 그 스킴에 해당하는 점
  2. `해독` -- 그 점을 되사상으로 되돌린 (U, V, W, lambda)

해독의 규약은 이렇다. b=2 이므로 첨자는 0..3 이다.

  · U 는 4x7. 행 a = i*2+l 이 A 의 (i,l) 성분. (A11,A12,A21,A22 = 0,1,2,3)
  · V 는 4x7. 행 a = l*2+j 가 B 의 (l,j) 성분. (B11,B12,B21,B22 = 0,1,2,3)
  · W 는 4x7. 행 a = i*2+j 가 C 의 (i,j) 성분. (C11,C12,C21,C22 = 0,1,2,3)
  · lambda 는 길이 7
  · 만족해야 하는 항등식:  sum_r lambda[r] * U[a][r] * V[b][r] * W[c][r]
    이것이 a=i*2+l, b=l'*2+j, c=i'*2+j' 에서 (l==l' and i==i' and j==j') 이면 1, 아니면 0

**못 적으면 못 적는다고 해라.** 지어내지 마라 -- 틀린 것보다 못 한다는 답이 낫다.
왜 못 하는지 한 줄로 적으면 그것이 이 공간에 대한 정보다.

JSON 하나만:

{{"가능": true/false,
 "점": "이 공간의 표기로",
 "해독": {{"U": [[..7개..] x 4행], "V": [[..]], "W": [[..]], "lambda": [..7개..]}},
 "못하는이유": "가능이 false 일 때만"}}

수는 정수·분수 문자열("1/2")·소수 아무거나 된다."""


def _frac(x):
    if isinstance(x, Fraction):
        return x
    if isinstance(x, bool):
        raise ValueError("bool")
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, float):
        return Fraction(x).limit_denominator(10 ** 6)
    if isinstance(x, str):
        return Fraction(x.strip())
    raise ValueError(f"수가 아니다: {x!r}")


def _matrix(raw, rows: int, cols: int):
    """받은 것을 (rows x cols) 로 맞춘다. 전치돼 와도 받는다 -- 규약을 적어 줘도
    행과 열을 바꿔 오는 일이 흔하고, 그것 때문에 멀쩡한 답을 버릴 이유는 없다."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("행렬이 아니다")
    m = [[_frac(x) for x in r] for r in raw]
    if len(m) == rows and all(len(r) == cols for r in m):
        return m
    if len(m) == cols and all(len(r) == rows for r in m):
        return [[m[j][i] for j in range(cols)] for i in range(rows)]
    raise ValueError(f"크기가 {len(m)}x{len(m[0])} 다 ({rows}x{cols} 여야 한다)")


def judge(ans: dict) -> tuple[str, str]:
    """**여기에 LLM 이 없다.** 받은 수를 Brent 항등식으로 검산한다."""
    if not ans.get("가능"):
        return "거절", (ans.get("못하는이유") or "")[:120]
    dec = ans.get("해독") or {}
    try:
        U = _matrix(dec.get("U"), N, M)
        V = _matrix(dec.get("V"), N, M)
        W = _matrix(dec.get("W"), N, M)
        lam = [_frac(x) for x in (dec.get("lambda") or [])]
        if len(lam) != M:
            raise ValueError(f"lambda 가 {len(lam)}개다")
    except (ValueError, TypeError, ZeroDivisionError) as e:
        return "못읽음", str(e)[:120]
    from verifier import ExactArithVerifier
    try:
        ok = ExactArithVerifier(B).verify(U, V, W, lam)
    except Exception as e:                                    # noqa: BLE001
        return "못읽음", f"{type(e).__name__}: {str(e)[:80]}"
    return ("재현" if ok else "틀림"), ""


def one(rec: dict, llm, log=print) -> dict:
    try:
        raw = llm(prompt(rec))
    except Exception as e:                                    # noqa: BLE001
        log(f"[재현] {rec['id']} 호출 실패({type(e).__name__})")
        return {}
    objs = SPR.objects(raw)
    if not objs:
        verdict, why = "못읽음", "JSON 이 아니다"
    else:
        verdict, why = judge(objs[0])
    out = {"시금석": f"strassen b={B} m={M}", "판정": verdict, "왜": why}
    rec["재현"] = out
    log(f"[재현] {rec['id']:<5} {verdict:<5} {rec.get('이름','')[:30]}"
        + (f"  -- {why[:60]}" if why else ""))
    return out


def report(led: dict) -> int:
    seen = [(s["id"], (s.get("재현") or {}).get("판정"), s.get("이름", ""))
            for s in led["spaces"] if s.get("재현")]
    if not seen:
        print("아직 아무것도 안 물었다. python3 mathdrift/recall.py --n 20")
        return 0
    tally = {}
    for _, v, _ in seen:
        tally[v] = tally.get(v, 0) + 1
    print(f"물어본 공간 {len(seen)}개 -- "
          + " · ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda x: -x[1])))
    for sid, v, name in sorted(seen, key=lambda r: r[1] or ""):
        print(f"  {sid:<5} {v:<5} {name[:44]}")
    print("\n**통과는 약한 증거다** -- 외운 Strassen 을 그대로 적어도 검산은 통과한다.")
    print("강한 신호는 '거절' 과 '틀림' 이다: 그 형식화는 Strassen 을 품지 못한다.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="앞에서부터 이만큼(아직 안 물은 것만)")
    ap.add_argument("--only", default="", help="쉼표로 짚어서 (예: S6,S34)")
    ap.add_argument("--again", action="store_true", help="이미 물은 것도 다시")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--dry", action="store_true", help="호출 없이 프롬프트만")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    led = SP.load(a.path or None)
    if a.show:
        return report(led)

    want = [x.strip() for x in a.only.split(",") if x.strip()]
    todo = [s for s in led["spaces"]
            if (s["id"] in want if want else True)
            and (s.get("계보") or {}).get("부모") != "-"
            and (a.again or not s.get("재현"))]
    if a.n:
        todo = todo[:a.n]
    if not todo:
        print("물을 것이 없다 (--again 으로 다시 물을 수 있다)")
        return 0

    if a.dry:
        print(prompt(todo[0]))
        return 0

    try:
        llm = SPR._live()
    except Exception as e:                                    # noqa: BLE001
        print(f"못 돌린다: {e}")
        return 1

    for i, rec in enumerate(todo, 1):
        one(rec, llm)
        SP.save(led, a.path or None)
    print()
    return report(led)


if __name__ == "__main__":
    raise SystemExit(main())
