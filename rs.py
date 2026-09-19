# -*- coding: utf-8 -*-
"""**RS(n,k) 부호기와 복호기** -- 신드롬 -> Berlekamp-Massey -> Chien -> Forney.

KP4 는 RS(544, 514) over GF(2^10), t = (544-514)/2 = **15 심볼**이다.

## 규격에서 아직 못 본 것 -- 상수를 박지 않는다

    필드 다항식        gf.py 참고.  **미확인**
    첫 근 지수 (fcr)   g(x) = prod (x - alpha^(fcr+i)).  **미확인**
    심볼 비트순서      MSB-first 인지.  **미확인**

셋 다 IEEE 802.3 Clause 91 이 정하고, 그 조문을 아직 못 봤다.  전부 **인자**로
두었다.  검사는 상수가 아니라 **성질**을 본다:

    t 개까지의 오류는 반드시 고쳐진다
    t+1 개부터는 **조용히 원본으로 복원되면 안 된다**

이 두 줄은 fcr 이 무엇이든 참이다.  규격이 오면 기본값만 바꾼다.

## 왜 이 검사가 무는가

RS 복호기 검사의 흔한 거짓초록은 **오류를 0개 넣고 통과**시키는 것이다.
그러면 복호기가 아무것도 안 해도 초록이다.  `측정()` 은 오류 개수를 명시적으로
받고, **0개 시험만으로는 통과했다고 말하지 않는다**.
"""
from gf import 필드


class RS:
    """RS(n, k) over GF(2^m).  n <= 2^m - 1."""

    def __init__(self, f: 필드, n: int, k: int, fcr: int = 0):
        if not 0 < k < n <= f.n:
            raise ValueError(f"0 < k < n <= {f.n} 이라야 한다: n={n}, k={k}")
        if (n - k) % 2:
            raise ValueError(f"n-k 는 짝수라야 한다 (t 가 정수): {n-k}")
        self.f, self.n, self.k, self.fcr = f, n, k, fcr
        self.t = (n - k) // 2
        self.g = self._생성다항식()

    def _생성다항식(self):
        """g(x) = prod_{i=0}^{2t-1} (x - alpha^(fcr+i)).  낮은 차수부터."""
        f = self.f
        g = [1]
        for i in range(2 * self.t):
            r = f.알파(self.fcr + i)
            새 = [0] * (len(g) + 1)
            for j, c in enumerate(g):
                새[j] = f.더하기(새[j], f.곱하기(c, r))   # c * r  (상수항 쪽)
                새[j + 1] = f.더하기(새[j + 1], c)        # c * x
            g = 새
        return g

    # ------------------------------------------------------------- 부호화
    def 부호화(self, 메시지):
        """조직적 부호화.  반환은 길이 n 의 코드워드 [메시지 | 패리티]."""
        if len(메시지) != self.k:
            raise ValueError(f"메시지 길이는 {self.k} 라야 한다: {len(메시지)}")
        f, t2 = self.f, 2 * self.t
        # 메시지를 x^(n-k) 만큼 올린 뒤 g 로 나눈 나머지가 패리티다.
        나머지 = [0] * t2
        for s in 메시지:                      # 높은 차수부터 들어온다
            되먹임 = f.더하기(s, 나머지[t2 - 1])
            for j in range(t2 - 1, 0, -1):
                나머지[j] = f.더하기(나머지[j - 1],
                                     f.곱하기(되먹임, self.g[j]))
            나머지[0] = f.곱하기(되먹임, self.g[0])
        return list(메시지) + 나머지[::-1]

    # ------------------------------------------------------------- 신드롬
    def 신드롬(self, r):
        """S_i = r(alpha^(fcr+i)), i=0..2t-1.  전부 0 이면 코드워드다."""
        f = self.f
        S = []
        for i in range(2 * self.t):
            x = f.알파(self.fcr + i)
            acc = 0
            for c in r:                       # r 은 높은 차수부터
                acc = f.더하기(f.곱하기(acc, x), c)
            S.append(acc)
        return S

    # ------------------------------------------- Berlekamp-Massey
    def _BM(self, S):
        """오류위치다항식 sigma 와 그 차수를 낸다.  낮은 차수부터."""
        f = self.f
        sigma, B = [1], [1]
        L, m = 0, 1
        b = 1
        for r in range(2 * self.t):
            d = S[r]
            for i in range(1, L + 1):
                if i < len(sigma):
                    d = f.더하기(d, f.곱하기(sigma[i], S[r - i]))
            if d == 0:
                m += 1
            elif 2 * L <= r:
                T = list(sigma)
                비 = f.나누기(d, b)
                자리 = [0] * m + [f.곱하기(비, x) for x in B]
                sigma = self._더하기다항(sigma, 자리)
                L, B, b, m = r + 1 - L, T, d, 1
            else:
                비 = f.나누기(d, b)
                자리 = [0] * m + [f.곱하기(비, x) for x in B]
                sigma = self._더하기다항(sigma, 자리)
                m += 1
        return sigma, L

    def _더하기다항(self, a, b):
        f = self.f
        긴, 짧 = (a, b) if len(a) >= len(b) else (b, a)
        결 = list(긴)
        for i, c in enumerate(짧):
            결[i] = f.더하기(결[i], c)
        return 결

    def _곱하기다항(self, a, b):
        f = self.f
        결 = [0] * (len(a) + len(b) - 1)
        for i, x in enumerate(a):
            if x:
                for j, y in enumerate(b):
                    if y:
                        결[i + j] = f.더하기(결[i + j], f.곱하기(x, y))
        return 결

    # ------------------------------------------------- Chien + Forney
    def _치엔(self, sigma):
        """sigma 의 근을 찾아 오류 위치(코드워드 색인)를 낸다."""
        f = self.f
        자리 = []
        for i in range(self.n):
            # X_j^-1 = alpha^-i 가 근이면 위치 i (높은차수=0 기준)
            x = f.알파(-i)
            acc = 0
            for e, c in enumerate(sigma):
                if c:
                    acc = f.더하기(acc, f.곱하기(c, f.거듭(x, e)))
            if acc == 0:
                자리.append(self.n - 1 - i)
        return 자리

    def _포니(self, S, sigma, 자리):
        """오류 크기.  omega = S*sigma mod x^2t, e = X^(1-fcr) * omega/sigma'."""
        f = self.f
        omega = self._곱하기다항(S, sigma)[: 2 * self.t]
        sigma미분 = [sigma[i] for i in range(1, len(sigma)) if i % 2]  # 홀수차만
        크기 = []
        for pos in 자리:
            i = self.n - 1 - pos
            Xinv = f.알파(-i)                 # X_j^-1
            X = f.알파(i)
            분자 = 0
            for e, c in enumerate(omega):
                if c:
                    분자 = f.더하기(분자, f.곱하기(c, f.거듭(Xinv, e)))
            분모 = 0
            for e, c in enumerate(sigma미분):  # sigma'(x) = sum odd i c_i x^(i-1)
                if c:
                    분모 = f.더하기(분모, f.곱하기(c, f.거듭(Xinv, 2 * e)))
            if 분모 == 0:
                return None                   # 복호 실패
            크기.append(f.곱하기(f.거듭(X, 1 - self.fcr),
                                 f.나누기(분자, 분모)))
        return 크기

    # ------------------------------------------------------------- 복호
    def 복호(self, r):
        """반환 dict.  `성공` 과 `고친수` 가 **반드시** 들어 있다.

        성공=False 는 '복호 실패를 검출했다' 는 뜻이고, 그것은 **조용히 틀린 답을
        내는 것보다 낫다**.  호출자는 이 칸을 봐야 한다.
        """
        f = self.f
        r = list(r)
        if len(r) != self.n:
            raise ValueError(f"길이는 {self.n} 라야 한다: {len(r)}")
        S = self.신드롬(r)
        if not any(S):
            return {"성공": True, "고친수": 0, "자리": [], "말": r,
                    "메시지": r[: self.k], "신드롬0": True}
        sigma, L = self._BM(S)
        if L > self.t:
            return {"성공": False, "고친수": 0, "자리": [], "말": r,
                    "메시지": r[: self.k], "신드롬0": False,
                    "이유": f"오류위치다항식 차수 {L} > t={self.t}"}
        자리 = self._치엔(sigma)
        if len(자리) != L:
            return {"성공": False, "고친수": 0, "자리": [], "말": r,
                    "메시지": r[: self.k], "신드롬0": False,
                    "이유": f"근 {len(자리)}개 != 차수 {L} -- 정정 불가"}
        크기 = self._포니(S, sigma, 자리)
        if 크기 is None:
            return {"성공": False, "고친수": 0, "자리": [], "말": r,
                    "메시지": r[: self.k], "신드롬0": False,
                    "이유": "Forney 분모가 0"}
        고침 = list(r)
        for p, e in zip(자리, 크기):
            고침[p] = f.더하기(고침[p], e)
        # 고친 결과가 정말 코드워드인지 **다시 잰다**.  이것이 없으면
        # 오정정(miscorrection)을 성공으로 보고하게 된다.
        if any(self.신드롬(고침)):
            return {"성공": False, "고친수": 0, "자리": 자리, "말": r,
                    "메시지": r[: self.k], "신드롬0": False,
                    "이유": "정정 후에도 신드롬이 0 이 아니다"}
        return {"성공": True, "고친수": len(자리), "자리": sorted(자리),
                "말": 고침, "메시지": 고침[: self.k], "신드롬0": False}


def KP4(poly: int = 0x409, fcr: int = 0) -> RS:
    """RS(544,514) over GF(2^10), t=15.  **상수 둘이 미확인이다** (모듈 설명 참고)."""
    from gf import KP4필드
    return RS(KP4필드(poly), 544, 514, fcr)


def 측정(code: RS, 오류수: int, 시행: int = 50, 씨앗: int = 0) -> dict:
    """오류 `오류수` 개를 **명시적으로** 넣고 복호 결과를 센다.

    오류수=0 만 돌려 놓고 '복호기가 동작한다' 고 말하지 않기 위해, 반환에
    `오류수` 를 그대로 넣고 0 일 때는 `무의미=True` 를 세운다.
    """
    import random
    rnd = random.Random(씨앗)
    f = code.f
    고침 = 실패 = 오정정 = 0
    for _ in range(시행):
        메시지 = [rnd.randrange(f.n + 1) for _ in range(code.k)]
        말 = code.부호화(메시지)
        받음 = list(말)
        자리 = rnd.sample(range(code.n), 오류수) if 오류수 else []
        for p in 자리:
            e = rnd.randrange(1, f.n + 1)       # 0 이면 오류가 아니다
            받음[p] = f.더하기(받음[p], e)
        r = code.복호(받음)
        if not r["성공"]:
            실패 += 1
        elif r["말"] == 말:
            고침 += 1
        else:
            오정정 += 1                          # 성공이라 했는데 원본이 아니다
    return {"오류수": 오류수, "시행": 시행, "t": code.t,
            "고침": 고침, "검출된실패": 실패, "**오정정**": 오정정,
            "무의미": 오류수 == 0}
