# -*- coding: utf-8 -*-
"""AIM2 의 **역 Mersenne S-box** 를 Frobenius 가수로 펴면 곱이 몇 개로 주는가.

## 규격서에서 온 것 (AIMer v2.0, KpqC Round 2, 2024-02, §3.1 · Table 3)

    Mer[e](x)    = x^(2^e - 1)
    Mer[e]^-1(x) = x^e~     where  e~ = (2^e - 1)^-1 mod (2^n - 1),  gcd(e, n) = 1

    AIM2-I   n=128  l=2  e=(49, 91)      e*=3
    AIM2-III n=192  l=2  e=(17, 47)      e*=5
    AIM2-V   n=256  l=3  e=(11, 141, 7)  e*=3

## 여기서 보인 것

    d = e^-1 mod n  이라 하면   e~ = sum_{j=0}^{d-1} 2^(e*j mod n)

따라서  x^e~ = x * s(x) * s^2(x) * ... * s^(d-1)(x),   s(x) = x^(2^e).

s 는 Frobenius 거듭제곱이라 **선형**이다. 하드웨어에서 상수 GF(2) 행렬 하나이고,
**마스킹에서 몫별로 따로 하면 되므로 신선한 랜덤이 0비트**다. 그래서 비용은 곱에만 든다.

위 곱셈열은 반복제곱법(Itoh-Tsujii 꼴)으로 **floor(log2 d) + HW(d) - 1** 번의 곱이면 된다.
레퍼런스 C 의 gf_exp 는 이진법이라 **popcount(e~) - 1 = d - 1** 번을 쓴다.

## 주의 -- 이 배수는 **하드웨어 수**다

소프트웨어에서 s^k(x) = x^(2^(e*k)) 는 제곱을 e*k 번 도는 것이라 싸지 않다.
하드웨어에서만 상수 선형 회로 하나다. **그래서 소프트웨어에서는 이 이득이 안 난다.**
그리고 선형 회로가 늘어나는 **면적 대가는 여기서 재지 않았다.**

실행: python3 aim/mer역_가수.py
"""
from __future__ import annotations

기약 = {128: (1 << 128) | (1 << 7) | (1 << 2) | (1 << 1) | 1,
        192: (1 << 192) | (1 << 7) | (1 << 2) | (1 << 1) | 1,
        256: (1 << 256) | (1 << 10) | (1 << 5) | (1 << 2) | 1}
파라미터 = [("AIM2-I", 128, [49, 91], 3),
            ("AIM2-III", 192, [17, 47], 5),
            ("AIM2-V", 256, [11, 141, 7], 3)]


def 곱(a: int, b: int, n: int) -> int:
    f, r = 기약[n], 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if (a >> n) & 1:
            a ^= f
    return r


def 거듭(x: int, e: int, n: int) -> tuple[int, int]:
    """이진법 square-and-multiply. 곱 횟수를 함께 낸다."""
    r, t, c = 1, x, 0
    while e:
        if e & 1:
            r = 곱(r, t, n)
            c += 1
        t = 곱(t, t, n)
        e >>= 1
    return r, c


def 프로베니우스(x: int, k: int, n: int) -> int:
    """s^k(x) = x^(2^k). **선형이다** -- 곱으로 세지 않는다."""
    for _ in range(k):
        x = 곱(x, x, n)
    return x


def 가수(x: int, e: int, d: int, n: int) -> tuple[int, int]:
    """x * s(x) * ... * s^(d-1)(x) 를 반복제곱법으로. 곱 횟수를 함께 낸다."""
    acc, m, c = x, 1, 0                      # acc = prod_{j<m} s^j(x)
    for 비트 in bin(d)[3:]:                   # 최상위 비트는 초기값이 먹는다
        acc = 곱(acc, 프로베니우스(acc, e * m, n), n); c += 1
        m *= 2
        if 비트 == "1":
            acc = 곱(acc, 프로베니우스(x, e * m, n), n); c += 1
            m += 1
    assert m == d, f"가수가 d 에 안 닿는다: {m} != {d}"
    return acc, c


def 검사(표본: int = 3) -> int:
    import random
    random.seed(7)
    틀림 = 0
    print(f"{'':9}{'n':>5}{'e':>5}{'d':>5}{'이진법':>8}{'가수':>6}{'배수':>7}  대조")
    print("-" * 56)
    for 이름, n, es, _ in 파라미터:
        for e in es:
            d = pow(e, -1, n)
            물결 = sum(1 << ((e * j) % n) for j in range(d))
            # 구조 검증: (2^e - 1) * e~ = 1 (mod 2^n - 1)
            if ((1 << e) - 1) * 물결 % ((1 << n) - 1) != 1:
                print(f"  구조 검증 실패 n={n} e={e}"); 틀림 += 1; continue
            좋다 = True
            for _ in range(표본):
                x = random.getrandbits(n)
                r1, c1 = 거듭(x, 물결, n)
                r2, c2 = 가수(x, e, d, n)
                뒤, _ = 거듭(r2, (1 << e) - 1, n)     # Mer[e](결과) == x 여야 한다
                if r1 != r2 or 뒤 != x:
                    좋다 = False
            if not 좋다:
                틀림 += 1
            print(f"{이름 if e == es[0] else '':9}{n:>5}{e:>5}{d:>5}{c1:>8}{c2:>6}{c1/c2:>6.1f}x"
                  f"  {'맞다' if 좋다 else '**틀리다**'}")
    return 틀림


if __name__ == "__main__":
    import sys
    나쁨 = 검사()
    print()
    if 나쁨:
        print(f"결과: 실패 -- {나쁨} 개가 안 맞는다")
        sys.exit(1)
    print("결과: 통과 (가수 = 이진법, 그리고 Mer[e](x^e~) = x 왕복까지)")
