"""유도의 걸음을 **격리해서** 판정한다. 부모는 이 코드를 임포트하지 않는다.

`sympify` 는 임의 코드를 실행한다(실측: `sympify('__import__("os").getcwd()')` 가 평가된다).
모델이 적어 낸 수식을 부모 프로세스에서 파싱하면 그것이 곧 코드 실행이다. 그래서
`mathdrift/_child.py` 와 같은 수를 쓴다 -- 여기서 돌고 **판정만** 표준출력으로 건너간다.

    python3 mathdrift/_prover.py --steps <json>

`steps` 는 수식 문자열의 목록이다. 이웃한 둘이 **같은 식인가**를 차례로 판정한다:
유도란 E0 = E1 = ... = En 의 사슬이고, 각 등호가 참인지가 물음이다.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys

TIMEOUT = 8


class _Bell(Exception):
    pass


def _under(sec, fn, *a, **kw):
    def _ring(*_):
        raise _Bell()
    old = signal.signal(signal.SIGALRM, _ring)
    signal.alarm(sec)
    try:
        return fn(*a, **kw)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def verdict(a_txt: str, b_txt: str, sec: int = TIMEOUT) -> dict:
    """**참 · 거짓 · 미정 셋이다.** 세 번째가 요점이다.

    극한을 걸거나 체를 바꾸거나 정의를 새로 하는 걸음은 대수 항등식이 아니다 -- sympy 가
    못 가르는 것이 정상이고, 그것을 거짓이라 부르면 진짜 유도가 기각된다. 모르는 것은
    모른다고 한다.
    """
    import sympy as sp

    def _p(t):
        return sp.sympify(t, rational=True)

    try:
        a = _under(sec, _p, a_txt)
        b = _under(sec, _p, b_txt)
    except _Bell:
        return {"판정": "미정", "왜": "읽는 데 시간이 걸린다"}
    except Exception as e:                                    # noqa: BLE001
        return {"판정": "미정", "왜": f"못 읽는다: {type(e).__name__}"}

    # 등식으로 왔으면 양변의 차로 바꾼다 -- 사슬은 식끼리 견주는 것이다.
    def _flat(x):
        return (x.lhs - x.rhs) if isinstance(x, sp.Equality) else x

    # **풀리지 않은 채로 두면 수치 대입이 막힌다.** Limit·Sum·Integral 이 그대로 있으면
    # subs 뒤에도 객체라 complex() 가 터지고, 그러면 멀쩡히 거짓인 걸음이 미정으로 샌다
    # (실측: lam*m 과 lam*m + 1 이 미정으로 나왔다). 못 풀리면 원래 것을 그대로 쓴다.
    def _do(x):
        try:
            return _under(sec, x.doit)
        except Exception:                                     # noqa: BLE001
            return x

    a, b = _do(_flat(a)), _do(_flat(b))
    try:
        d = _under(sec, lambda: sp.simplify(sp.expand_func(a - b)))
        if d == 0:
            return {"판정": "참", "왜": ""}
    except _Bell:
        return {"판정": "미정", "왜": "정리하는 데 시간이 걸린다"}
    except Exception as e:                                    # noqa: BLE001
        return {"판정": "미정", "왜": f"정리 못 함: {type(e).__name__}"}

    # **반례 사냥.** 자유 기호에 유리수를 넣어 한 점이라도 어긋나면 거짓이다.
    free = sorted((a - b).free_symbols, key=str)
    if not free:
        try:
            v = complex(_under(sec, lambda: sp.N(a - b, 20)))
            if abs(v) > 1e-12:
                return {"판정": "거짓", "왜": f"수로 재면 차이가 {abs(v):.3g}"}
            return {"판정": "미정", "왜": "수로는 같은데 기호로 못 줄였다"}
        except Exception:                                     # noqa: BLE001
            return {"판정": "미정", "왜": "수로도 못 잰다"}

    picks = (sp.Rational(2, 3), sp.Rational(3, 5), sp.Rational(5, 7),
             sp.Rational(7, 11), sp.Rational(4, 9))
    for k in range(len(picks)):
        sub = {s: picks[(i + k) % len(picks)] for i, s in enumerate(free)}
        try:
            v = complex(_under(sec, lambda: sp.N((a - b).subs(sub), 20)))
        except Exception:                                     # noqa: BLE001
            continue
        if v != v:                                            # NaN -- 그 점에서 미정
            continue
        if abs(v) > 1e-9:
            return {"판정": "거짓",
                    "왜": f"{', '.join(f'{s}={sub[s]}' for s in free)} 에서 차이 {abs(v):.3g}"}
    return {"판정": "미정", "왜": "기호로도 수로도 못 가른다"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", required=True, help="수식 문자열 목록 (JSON)")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    a = ap.parse_args()
    steps = json.loads(a.steps)
    out = [verdict(steps[i], steps[i + 1], a.timeout) for i in range(len(steps) - 1)]
    print(json.dumps({"status": "ok", "걸음": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
