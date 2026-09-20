# -*- coding: utf-8 -*-
"""T11·T12 에 박힌 아날로그 측정이 **지금 다시 재도 같은지** 본다.

교재가 인용하는 수는 `edu/측정/bandgap.py` 와 `edu/측정/mismatch.py` 에서 나왔다.
붙여 넣은 수는 회로나 모델이 바뀌면 조용히 낡는다 -- 그러면 교재는 있지도 않은
실험을 인용하게 된다.

ngspice 가 없는 자리에서는 **경향과 법칙**만 본다(그것도 검사다):
  · 밴드갭 -- 최적이 있고, 최적에서 V_ref 가 실리콘 밴드갭 근처다
  · 불일치 -- 면적 4배에 σ 절반 (펠그롬), 전류 100배에 σ 1/3 (√)
"""
import math
import os
import shutil
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, os.path.join(뿌리, "edu", "측정"))

import T11_bias                                            # noqa: E402
import T12_match                                           # noqa: E402

있나 = shutil.which("ngspice") is not None


# --------------------------------------------------------------- 밴드갭
def test_밴드갭에_최적이_있고_날카롭다():
    표 = T11_bias.잰PTAT
    최적 = min(표, key=lambda r: 표[r][1])
    assert 최적 == T11_bias.최적R3, (최적, T11_bias.최적R3)
    양쪽 = [표[r][1] for r in sorted(표) if r != 최적]
    assert all(v > 표[최적][1] for v in 양쪽), "최적이 최솟값이 아니다"
    # 날카로움 -- 2% 어긋나면 눈에 띄게 나빠진다
    assert 표[10.0][1] > 표[최적][1] * 2, (표[10.0][1], 표[최적][1])


def test_최적에서_실리콘_밴드갭_근처가_나온다():
    """설계자가 고른 값이 아니라 **물리가 정한 값**이라는 것이 이 장의 요점이다."""
    v = T11_bias.잰PTAT[T11_bias.최적R3][0]
    assert 1.10 < v < 1.30, f"최적 V_ref 가 {v} -- 밴드갭이 아니다"


def test_밴드갭을_다시_재면_같다():
    if not 있나:
        print("    (ngspice 가 없다 -- 재현 대조는 개발 자리에서만 돈다)")
        return
    import bandgap
    r = bandgap.쓸기(R3k=T11_bias.최적R3)
    assert r, "ngspice 가 있는데 안 돌았다"
    박힌V, 박힌TC = T11_bias.잰PTAT[T11_bias.최적R3]
    assert abs(r[0] - 박힌V) < 2e-3, (r[0], 박힌V)
    assert abs(r[2] - 박힌TC) < 2.0, (r[2], 박힌TC)


# --------------------------------------------------------------- 불일치
def test_펠그롬_면적_4배에_시그마_절반():
    표 = [T12_match.잰면적[k] for k in ("1x0.2", "2x0.4", "4x0.8", "8x1.6")]
    for 앞, 뒤 in zip(표, 표[1:]):
        assert abs(뒤[0] / 앞[0] - 4.0) < 0.01, "면적이 4배씩이 아니다"
        비 = 앞[3] / 뒤[3]
        assert 1.8 < 비 < 2.2, f"면적 4배에 σ 가 {비:.2f} 배로 줄었다 -- √ 가 아니다"


def test_불일치가_평균도_밀어낸다():
    """대칭인 V_th 오차가 **비대칭인 전류 오차**로 간다 -- 평균이 1 이 아니다."""
    표 = [T12_match.잰면적[k] for k in ("1x0.2", "2x0.4", "4x0.8", "8x1.6")]
    평균들 = [v[2] for v in 표]
    assert all(v < 1.0 for v in 평균들), 평균들
    assert 평균들 == sorted(평균들), f"면적이 커지는데 평균이 1 로 안 간다: {평균들}"


def test_전류를_키우면_정합이_좋아진다():
    t = T12_match.잰전류
    assert t["1u"] > t["10u"] > t["100u"], t
    비 = t["1u"] / t["100u"]
    assert 5 < 비 < 20, f"전류 100배에 σ 가 {비:.1f} 배 -- √ 꼴이 아니다"


def test_거울이_불일치_0_이면_1대1_이다():
    """자해검사 -- 하니스가 애초에 옳은 회로를 돌리는지."""
    if not 있나:
        print("    (ngspice 가 없다 -- 회로 확인은 개발 자리에서만 돈다)")
        return
    import mismatch
    v = mismatch.한판(2, 0.4, 0.0, 10e-6)
    assert v is not None, "회로가 안 돌았다"
    assert abs(v / 10e-6 - 1.0) < 0.05, f"불일치 0 인데 거울비가 {v/10e-6}"


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
