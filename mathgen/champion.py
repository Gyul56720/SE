"""거꾸로 만드는 씨앗 -- 답을 먼저 정하고 그 도함수를 문제로 낸다.

이 구성이 심판의 검증 비대칭성을 그대로 이용한다:

    F 를 고른다  ->  f = F' 를 문제로 낸다  ->  정답은 F (구성상 확실)

정당성은 **구성으로 보장된다** -- 심판이 답을 미분해 f 와 맞춰보면 반드시 통과한다.
남는 질문은 하나뿐이다: sympy 가 f 에서 F 를 **되찾을 수 있는가.** 미분은 기계적이고
적분은 아니라는 비대칭이 여기서 값어치를 낸다.

어느 F 가 그 틈에 떨어지는지는 재봐야 안다. 12개 족을 훑어 2개만 걸렸다(실측):
  · 근호 나눗셈  (x^2+c)/sqrt(x^4+ax+b) 꼴의 도함수 -> sympy 시간 초과
  · 이중 지수    exp(a*x*exp(b*x)) 꼴의 도함수     -> sympy 가 Integral 로 되돌려준다
나머지 10개(다항x지수, 로그 합성, 중첩 근호, 역삼각 합성 ...)는 sympy 가 전부 되찾는다.

**틈이 좁다는 것이 이 문제가 탐색 대상인 이유다.** 넓으면 손으로 열거하면 된다.
"""
import random

import sympy as sp

X = sp.Symbol("x")


def _radical_quotient(rng):
    """F = (x^2 + c) / sqrt(x^4 + a*x + b).  f = F' 는 타원적분 쪽으로 밀려난다."""
    a, b, c = rng.randint(1, 5), rng.randint(1, 6), rng.randint(1, 4)
    F = (X ** 2 + c) / sp.sqrt(X ** 4 + a * X + b)
    steps = [f"u = x**4 + {a}*x + {b}", f"F = (x**2 + {c})/sqrt(u)", str(F)]
    hint = f"분모의 근호 안을 u = x⁴ + {a}x + {b} 로 두고 몫의 미분을 거꾸로 읽는다"
    return F, steps, hint


def _double_exp(rng):
    """F = exp(a*x*exp(b*x)).  지수의 지수라 sympy 가 되돌리지 못한다."""
    a, b = rng.randint(1, 3), rng.randint(1, 3)
    F = sp.exp(a * X * sp.exp(b * X))
    steps = [f"u = {a}*x*exp({b}*x)", "F = exp(u)", str(F)]
    hint = f"지수 전체를 u = {a}x·e^({b}x) 로 두면 f = u'·e^u 꼴이 보인다"
    return F, steps, hint


FAMILIES = (_radical_quotient, _double_exp)


def generate(seed: int) -> dict:
    rng = random.Random(seed)
    F, steps, hint = FAMILIES[seed % len(FAMILIES)](rng)
    f = sp.simplify(sp.diff(F, X))
    return {
        "statement": ("다음 부정적분을 구하시오 (적분상수는 생략):\n\n"
                      f"    ∫ {sp.pretty(f, use_unicode=True)} dx\n\n"
                      f"[힌트] {hint}"),
        "spec": {"task": "integrate", "expr": str(f), "var": "x"},
        "answer": str(F),
        "solution": steps,
    }
