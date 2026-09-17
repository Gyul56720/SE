"""**규격 문턱으로 판정한다** -- KP4 RS(544,514) 를 기준으로.

## 왜 10^-12 가 아닌가

"상용 SerDes 는 BER 10^-12 를 요구한다" 는 **FEC 이전 시대(10G/25G NRZ)의 요구**다.
112G/224G 는 그렇지 않다. IEEE 802.3ck(100G/lane)·802.3bs 는 **KP4 RS(544,514)** 를
전제로 하고, 슬라이서가 내는 **pre-FEC BER 이 2e-4 근처**면 FEC 가 post-FEC 10^-15
를 만든다. 224G(802.3dj)는 더 강한/연접 부호를 보고 있어 문턱이 또 다르다.

그러니 판정할 자리는 **pre-FEC BER 대 문턱**이고, 이 모듈이 그것을 한다.

**이 정정이 지적을 무르게 하지 않는다.** 이 저장소가 잰 바닥을 그 문턱에 대면

    선형 baseline   1.13e-2    문턱의 47배    탈락
    표(LUT)         2.34e-3    문턱의 9.8배   탈락
    ADC 없음        4.25e-4    문턱의 1.8배   **아깝게** 탈락

**이기는 구간에서는 규격을 못 넘고, 규격을 넘는 구간에서는 안 이긴다.** 그것이
지금 상태이고, 이 모듈은 그것을 매번 숫자로 말하게 하려고 있다.

## 문턱을 **베껴 적지 않는다** -- 계산해서 낸다

"2.4e-4" 를 상수로 박아 두면 그것이 어디서 왔는지 아무도 못 본다. `문턱()` 은
부호 파라미터(n=544, k=514, GF(2^10))에서 **이분법으로 찾는다**:

    p_s = 1 - (1-p_b)^10                       10비트 심볼이 하나라도 틀릴 확률
    P_out = p_s · P(Bin(n-1, p_s) >= t)        경계거리 디코딩 뒤 남는 심볼오류율
    post-FEC BER = P_out · (나쁜심볼당 나쁜비트 / 10)

`j·C(n,j) = n·C(n-1,j-1)` 이라 합이 닫힌 꼴로 접힌다 -- 큰 n 에서 항을 하나씩
더하다 반올림으로 무너지는 것을 피한다.

## **묶임(burst)을 재는 것이 이 모듈의 진짜 일이다**

문턱 2.4e-4 는 **오류가 무작위일 때**의 값이다. 그런데 DFE 는 오류를 번지게 해서
오류를 **뭉친다.** 뭉치면 같은 비트오류 수가 더 적은 RS 심볼에 들어가므로 FEC 에
**유리**하다 -- 방향이 직관과 반대다. 그러니 무작위 가정으로 낸 post-FEC 를 그냥
싣는 것은 검사하지 않은 초록불이다.

`판정()` 은 **코드워드당 심볼오류 분포를 실측해서** 이항 예측과 견준다. 둘이
어긋나면 post-FEC 숫자에 `무작위가정깨짐` 을 달고, **그 숫자를 믿지 말라고 적는다.**
"""
from __future__ import annotations

import math

import numpy as np

try:
    from scipy.stats import binom as _binom
except Exception:                                # pragma: no cover
    _binom = None


# IEEE 802.3 의 두 RS 부호. `심볼비트` 는 GF(2^m) 의 m 이다.
부호들 = {
    "KP4": {"n": 544, "k": 514, "심볼비트": 10, "왜": "802.3ck/bs 100G·400G lane"},
    "KR4": {"n": 528, "k": 514, "심볼비트": 10, "왜": "802.3bj 25G lane"},
}


def 고치는수(부호: str = "KP4") -> int:
    c = 부호들[부호]
    return (c["n"] - c["k"]) // 2


def _sf(k: float, n: int, p: float) -> float:
    """P(Bin(n,p) > k). scipy 가 없으면 로그합으로 센다."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    if _binom is not None:
        return float(_binom.sf(k, n, p))
    s, q = 0.0, math.log1p(-p)
    lp = math.log(p)
    for j in range(int(math.floor(k)) + 1, n + 1):
        s += math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
                      + j * lp + (n - j) * q)
        if j > k + 1 and s > 0 and math.exp(
                math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1)
                + j * lp + (n - j) * q) < 1e-18 * s:
            break
    return s


def 남는심볼오류율(p_s: float, 부호: str = "KP4") -> float:
    """경계거리 디코딩 뒤 남는 심볼오류율.

        sum_{j>t} (j/n)·C(n,j) p^j q^(n-j) = p · P(Bin(n-1,p) >= t)

    (`j·C(n,j) = n·C(n-1,j-1)` 로 접은 것이다 -- 항을 하나씩 더하지 않는다.)
    """
    c = 부호들[부호]
    t = 고치는수(부호)
    return float(p_s) * _sf(t - 1, c["n"] - 1, float(p_s))


def post_BER(p_b: float, 부호: str = "KP4", 나쁜비트per심볼: float = 1.0) -> float:
    """pre-FEC 비트오류율 -> post-FEC 비트오류율 (**오류가 무작위라는 가정 아래**).

    `나쁜비트per심볼` 은 틀린 RS 심볼 하나에 든 나쁜 비트 수다. PAM4+그레이면
    심볼오류 하나가 비트오류 하나이므로 1 에 가깝고, 실측으로 바꿔 넣을 수 있다.
    """
    c = 부호들[부호]
    m = c["심볼비트"]
    p_s = 1.0 - (1.0 - float(p_b)) ** m
    return 남는심볼오류율(p_s, 부호) * (float(나쁜비트per심볼) / m)


def 문턱(목표post: float = 1e-15, 부호: str = "KP4",
       나쁜비트per심볼: float = 1.0, 걸음: int = 200) -> float:
    """`post_BER(p) = 목표post` 인 pre-FEC BER 을 이분법으로 찾는다."""
    lo, hi = 1e-9, 0.5
    for _ in range(int(걸음)):
        mid = math.sqrt(lo * hi)
        if post_BER(mid, 부호, 나쁜비트per심볼) < 목표post:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def 코드워드분포(비트오류자리, 총비트: int, 부호: str = "KP4") -> dict:
    """비트오류 **자리**에서 코드워드당 심볼오류 수를 센다.

    개수만 받으면 뭉쳐 있는지 흩어져 있는지를 잃으므로 **자리**를 받는다.
    """
    c = 부호들[부호]
    m, n = c["심볼비트"], c["n"]
    코드워드비트 = n * m
    총비트 = int(총비트)
    코드워드수 = 총비트 // 코드워드비트
    자리 = np.asarray(비트오류자리, dtype=np.int64)
    자리 = 자리[자리 < 코드워드수 * 코드워드비트]
    if 코드워드수 <= 0:
        return {"코드워드수": 0, "왜": "한 코드워드도 안 찬다"}
    심볼번호 = 자리 // m                       # 전체에서 몇 번째 RS 심볼인가
    나쁜심볼 = np.unique(심볼번호)
    코드워드 = 나쁜심볼 // n
    # 코드워드마다 나쁜 심볼이 몇 개인가
    개수 = np.bincount(코드워드, minlength=코드워드수)
    # 나쁜 심볼 하나에 나쁜 비트가 몇 개인가
    비트per심볼 = (len(자리) / len(나쁜심볼)) if len(나쁜심볼) else float("nan")
    t = 고치는수(부호)
    return {"코드워드수": int(코드워드수), "코드워드비트": int(코드워드비트),
            "나쁜심볼수": int(len(나쁜심볼)), "나쁜비트수": int(len(자리)),
            "심볼오류율": float(len(나쁜심볼)) / (코드워드수 * n),
            "나쁜비트per심볼": float(비트per심볼),
            "코드워드당평균": float(개수.mean()), "코드워드당분산": float(개수.var()),
            "코드워드당최대": int(개수.max()) if len(개수) else 0,
            "t": t, "넘은코드워드": int(np.sum(개수 > t)),
            "분포": 개수}


def 판정(비트오류자리, 총비트: int, 부호: str = "KP4",
       목표post: float = 1e-15) -> dict:
    """**규격 판정.** pre-FEC 을 문턱에 대고, 무작위 가정이 서는지 같이 본다.

    돌려주는 것 중 중요한 셋:

        통과          pre-FEC 이 문턱 아래인가 (이것이 규격 판정이다)
        여유dB        문턱까지 몇 dB 인가 (Q 로 옮겨서)
        무작위가정깨짐 실측 코드워드 분포가 이항과 어긋나나
                     -- 깨졌으면 `post_BER` 숫자를 **믿으면 안 된다**
    """
    d = 코드워드분포(비트오류자리, 총비트, 부호)
    if not d.get("코드워드수"):
        return {"판정": "못잼", "왜": d.get("왜", ""), **d}
    p_b = d["나쁜비트수"] / float(총비트)
    나쁜비트 = d["나쁜비트per심볼"] if np.isfinite(d["나쁜비트per심볼"]) else 1.0
    th = 문턱(목표post, 부호, 나쁜비트)
    # **무작위 가정이 서나**: 이항이면 분산이 n·p(1-p) 라야 한다. 뭉치면 더 크다.
    c = 부호들[부호]
    p_s = d["심볼오류율"]
    이항분산 = c["n"] * p_s * (1.0 - p_s)
    묶임비 = (d["코드워드당분산"] / 이항분산) if 이항분산 > 0 else float("nan")
    깨짐 = bool(np.isfinite(묶임비) and (묶임비 > 1.5 or 묶임비 < 0.5)
                and d["나쁜심볼수"] >= 30)
    # 여유를 dB 로: Q^-1 두 개의 비
    def Qinv(p):
        from scipy.special import erfcinv
        return float(math.sqrt(2.0) * erfcinv(2.0 * min(max(p, 1e-300), 0.5 - 1e-16)))
    여유 = float("nan")
    if 0 < p_b < 0.5 and 0 < th < 0.5:
        try:
            여유 = 20.0 * math.log10(Qinv(p_b) / Qinv(th))
        except Exception:
            pass
    return {"판정": "PASS", "부호": 부호, "pre_FEC_BER": float(p_b),
            "문턱": float(th), "통과": bool(p_b < th),
            "문턱대비": float(p_b / th) if th else float("nan"),
            "여유dB": 여유,
            "post_FEC_BER_무작위가정": post_BER(p_b, 부호, 나쁜비트),
            "묶임비": float(묶임비), "무작위가정깨짐": 깨짐,
            "나쁜비트per심볼": float(나쁜비트),
            "코드워드수": d["코드워드수"], "나쁜심볼수": d["나쁜심볼수"],
            "넘은코드워드": d["넘은코드워드"], "t": d["t"],
            "왜": ("" if not 깨짐 else
                 f"코드워드 분산이 이항의 {묶임비:.2f}배 -- post-FEC 숫자를 믿지 마라")}


def 말로(r: dict) -> str:
    if r.get("판정") != "PASS":
        return f"못 잼: {r.get('왜', '')}"
    구 = "통과" if r["통과"] else "탈락"
    s = (f"{r['부호']}: pre-FEC {r['pre_FEC_BER']:.3e} vs 문턱 {r['문턱']:.3e} "
         f"-> **{구}** (문턱의 {r['문턱대비']:.2f}배, 여유 {r['여유dB']:+.2f} dB)")
    if r["무작위가정깨짐"]:
        s += f"\n  주의: {r['왜']}"
    return s
