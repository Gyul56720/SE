# -*- coding: utf-8 -*-
"""**GF(2^m) 산술** -- RS-FEC 의 바닥.  원시다항식을 **인자로 받는다.**

## 왜 상수를 박지 않았나

KP4 는 GF(2^10) 이고 IEEE 802.3 Clause 91 이 필드 다항식을 정한다.  **그 조문을
아직 못 봤다** -- `standards.ieee.org` 가 이 환경에서 닿지 않는다(Get IEEE 802 로
무료 배포되므로 사람이 받을 수 있다).  검색으로도 확인이 안 됐다.

그래서 **추측해서 박지 않는다.**  다항식을 인자로 받고, 검사는 *상수*가 아니라
*성질*을 본다 -- 필드 공리가 서는가.  규격이 오면 상수만 바꾸면 되고 검사는
그대로 산다.

    기본값 0x409 = x^10 + x^3 + 1 은 GF(2^10) 에서 흔히 쓰는 원시다항식이지만
    **KP4 의 것이라고 확인하지 않았다.**  `확인됨=False` 가 그것을 들고 있다.

## 표를 쓴다

곱셈을 매번 다항식 나눗셈으로 하면 느리다.  생성원 alpha 의 거듭제곱을 한 번
훑어 **지수표(antilog)와 로그표**를 만들고, 곱셈을 로그 덧셈으로 바꾼다.

    a * b = alpha^(log a + log b)      단 a,b != 0

이것이 성립하려면 alpha 가 **원시원**이어야 한다 -- 즉 거듭제곱이 0 이 아닌
원소 2^m-1 개를 **하나도 빠짐없이 한 번씩** 훑어야 한다.  `_표만들기` 가 그것을
확인하고, 아니면 예외를 던진다.  **원시가 아닌 다항식을 조용히 받아들이면
곱셈이 틀린 채로 돈다.**
"""


class 필드:
    """GF(2^m).  원시다항식 `poly` 는 최상위 비트를 포함한 정수로 준다."""

    def __init__(self, m: int, poly: int, 확인됨: bool = False, 이름: str = ""):
        if not 2 <= m <= 16:
            raise ValueError(f"m 은 2..16 이라야 한다: {m}")
        if poly >> m != 1:
            raise ValueError(
                f"poly 의 최고차항이 x^{m} 이어야 한다 (0x{poly:x} 는 아니다)")
        self.m = m
        self.poly = poly
        self.n = (1 << m) - 1          # 곱셈군의 크기
        self.확인됨 = 확인됨            # 규격 조문으로 확인했는가
        self.이름 = 이름
        self._지수, self._로그 = self._표만들기()

    # ---------------------------------------------------------------- 표
    def _표만들기(self):
        """alpha=2 의 거듭제곱을 훑는다.  원시가 아니면 예외."""
        지수 = [0] * (2 * self.n)      # 두 벌 이어 두면 로그합에 mod 가 필요없다
        로그 = [None] * (self.n + 1)
        x = 1
        for i in range(self.n):
            if 로그[x] is not None:
                raise ValueError(
                    f"0x{self.poly:x} 는 원시다항식이 아니다 -- alpha 의 위수가 "
                    f"{i} 로 {self.n} 보다 작다. 곱셈표를 못 만든다")
            지수[i] = x
            로그[x] = i
            x <<= 1
            if x >> self.m:
                x ^= self.poly
        if x != 1:
            raise ValueError(f"0x{self.poly:x}: alpha^{self.n} != 1")
        for i in range(self.n, 2 * self.n):
            지수[i] = 지수[i - self.n]
        return 지수, 로그

    # ------------------------------------------------------------ 산술
    def 더하기(self, a: int, b: int) -> int:
        """표수 2 이므로 덧셈과 뺄셈이 같다."""
        return a ^ b

    빼기 = 더하기

    def 곱하기(self, a: int, b: int) -> int:
        if a == 0 or b == 0:
            return 0
        return self._지수[self._로그[a] + self._로그[b]]

    def 역원(self, a: int) -> int:
        if a == 0:
            raise ZeroDivisionError("0 의 역원은 없다")
        return self._지수[self.n - self._로그[a]] if self._로그[a] else 1

    def 나누기(self, a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("0 으로 못 나눈다")
        if a == 0:
            return 0
        return self._지수[self._로그[a] + self.n - self._로그[b]]

    def 거듭(self, a: int, e: int) -> int:
        """a^e.  e 는 음수여도 된다."""
        if a == 0:
            if e == 0:
                return 1
            if e < 0:
                raise ZeroDivisionError("0 의 음수 거듭제곱")
            return 0
        return self._지수[(self._로그[a] * e) % self.n]

    def 알파(self, i: int) -> int:
        """alpha^i.  i 는 음수여도 된다."""
        return self._지수[i % self.n]

    def 로그(self, a: int) -> int:
        if a == 0:
            raise ValueError("0 의 로그는 없다")
        return self._로그[a]

    def __repr__(self):
        표 = "확인됨" if self.확인됨 else "**미확인**"
        return f"필드(GF(2^{self.m}), poly=0x{self.poly:x}, {표}{', '+self.이름 if self.이름 else ''})"


# ---------------------------------------------------------------- 미리 만든 것
# **주의: KP4 의 필드 다항식을 규격 조문으로 확인하지 못했다.**
# 아래는 GF(2^10) 에서 널리 쓰이는 원시다항식이고, 그것이 KP4 의 것이라는
# 확인은 **없다**.  `확인됨=False` 가 그 사실을 코드 안에 들고 있다.
def KP4필드(poly: int = 0x409) -> 필드:
    """KP4 용 GF(2^10).  기본 다항식은 **미확인**이다 -- 위 주석 참고."""
    return 필드(10, poly, 확인됨=False, 이름="KP4 후보")


def 검증(f: 필드, 표본: int = 0) -> dict:
    """필드 공리를 **재서** 확인한다.  '돌아간다' 가 아니라 '필드인가' 를 본다.

    표본=0 이면 전수(작은 필드용), 아니면 그만큼만 뽑아 본다.
    """
    import random
    원소 = list(range(1, f.n + 1))
    if 표본 and 표본 < len(원소):
        원소 = random.Random(12345).sample(원소, 표본)

    역원실패 = sum(1 for a in 원소 if f.곱하기(a, f.역원(a)) != 1)
    항등실패 = sum(1 for a in 원소 if f.곱하기(a, 1) != a)
    나눗셈실패 = sum(1 for a in 원소 for b in 원소[:16]
                     if f.곱하기(f.나누기(a, b), b) != a)
    # 지수표가 0 이 아닌 원소를 정확히 한 번씩 훑는가
    훑음 = len(set(f._지수[:f.n])) == f.n
    return {
        "원소수": f.n,
        "본원소": len(원소),
        "역원실패": 역원실패,
        "항등실패": 항등실패,
        "나눗셈실패": 나눗셈실패,
        "지수표전사": 훑음,
        "필드인가": (역원실패 == 0 and 항등실패 == 0
                     and 나눗셈실패 == 0 and 훑음),
    }
