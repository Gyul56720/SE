"""**6-DOF 하이브리드 비행제어의 측정된 사실을 붙든다.** 실측 2026-09-26.

## 왜

`ctrl/model/hybrid6dof.py` 는 알려진 방법의 재현이다(신규성 없음 -- paper/선행조사/
6DOF_적응제어_MRAC_RTA.md). 재현이라도 **수가 맞는지**는 붙들어야 한다. 이 검사는
대화에서 실제로 잰 정직한 사실을 회귀로 잠근다:

  1. **명목·무불확실은 안정·정밀**하다(자세RMS 작다) -- 기준선이 성한 동작점인지 먼저 본다.
  2. **불확실이 명목을 악화**시킨다(무불확실보다 RMS 커진다) -- 불확실이 실제로 문다.
  3. **MRAC 가 명목보다 확실히 낫다**(불확실 하에서 최소 40% 개선; 실측은 2배).
     이게 이 저장소의 핵심 주장 -- 사용자 MRAC 연구가 6-DOF MIMO 로 확장돼 작동함.
  4. **RTA 가 안전집합을 지킨다**: 학습항에 반감쇠 명령을 주입하면 RTA 끄면 이탈(>0.7),
     켜면 유지(<0.7). 안전층이 실제로 뭘 막는지 -- 갈리는 점에서 시험한다.
  5. **독립대조(수가 시시한 이유로 안 나왔음)**: 적응률 γ 를 올리면 정합-only 추종
     RMS 가 **단조 감소**한다. MRAC 의 개선이 우연/설정 탓이 아니라 적응이 실제로
     정합 불확실을 잡아서임을 딴 길로 확인(과장방지 규칙 3: 독립대조).

## 무엇을 붙드나 -- 부호와 순서(회귀), 넉넉한 허용오차

값 자체가 아니라 **정성적 사실**(안정한가, 불확실이 무나, MRAC 가 이기나, RTA 가
갈리나, γ↑ 로 단조 개선되나)을 잠근다. 누가 조용히 모형을 바꿔 사실이 뒤집히면 빨개진다.

## 학습 SSM(Mamba)은 왜 안 붙드나

실측에서 학습 SSM 은 MRAC 대비 +5%로 **거의 잉여**였고(과장방지 -- 크게 포장 안 함),
그 값은 ES 시드·반복에 흔들린다. 정확도로 남기지 않으므로 검사도 정확도를 잠그지
않는다. 이 층은 FPGA 매핑(하드웨어) 근거로만 남긴다. ES 는 느려서 검사에서 안 돌린다.
"""
from __future__ import annotations

import pathlib
import sys

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))

from ctrl.model import hybrid6dof as H


# ── 1. 명목·무불확실은 안정·정밀(성한 동작점) ───────────────────────
def test_명목_무불확실_안정정밀():
    L = H.기준모델()
    rms, amax, _ = H.모의("nominal", 불확실=False, L=L)
    assert rms < 0.03, f"명목·무불확실 자세RMS={rms:.4f} 커서 기준선이 안 성함"
    assert amax < 0.5, f"명목·무불확실 최대자세={amax:.3f} 이상(±0.3 지령인데 과도)"


# ── 2. 불확실이 명목을 악화시킨다 ─────────────────────────────────
def test_불확실이_명목을_악화():
    L = H.기준모델()
    깨끗 = H.모의("nominal", 불확실=False, L=L)[0]
    불확 = H.모의("nominal", 불확실=True, L=L)[0]
    assert 불확 > 1.5 * 깨끗, f"불확실({불확:.4f})이 무불확실({깨끗:.4f})을 못 악화 -- 불확실이 안 묾"


# ── 3. MRAC 가 명목보다 확실히 낫다(핵심 주장) ─────────────────────
def test_MRAC가_명목을_이긴다():
    L = H.기준모델()
    명목 = H.모의("nominal", 불확실=True, L=L)[0]
    mrac = H.모의("mrac", 불확실=True, gamma=200.0, L=L)[0]
    assert mrac < 0.7 * 명목, f"MRAC({mrac:.4f})가 명목({명목:.4f}) 대비 40%도 개선 못 함"


# ── 4. RTA 가 안전집합을 지킨다(갈리는 점에서 시험) ─────────────────
def test_RTA가_안전집합을_지킨다():
    L = H.기준모델()
    _, 끔, _ = H.모의("hybrid", ssm파라미터=None, rta=False, 주입불량=True, L=L)
    _, 켬, tr = H.모의("hybrid", ssm파라미터=None, rta=True, 주입불량=True, L=L)
    assert 끔 > 0.7, f"RTA 끔 최대자세={끔:.3f} -- 주입이 안전집합을 안 넘어 시험 공허"
    assert 켬 < 0.7, f"RTA 켬 최대자세={켬:.3f} -- 안전집합 못 지킴"
    assert tr > 0, "RTA 가 한 번도 차단 안 함"


# ── 5. 독립대조: γ↑ 로 정합-only RMS 단조 감소(적응이 실제 작동) ────
def test_적응률_올리면_정합불확실_단조개선():
    """정합 불확실만 두고 γ 를 올린다. MRAC 개선이 우연이 아니라 적응 덕임을 딴 길로 확인.
    (커플링·공진을 끄기 위해 불확실=False 로 명목을 재고, 정합만 켠 판을 직접 만든다.)"""
    import numpy as np
    from ctrl.model import hybrid6dof as M

    def 정합만_모의(gamma, dt=0.005, 시간=24.0):
        L = M.기준모델(); a, b = M.A_계수
        Am, Bm, P, Kx, kr, B = L["Am"], L["Bm"], L["P"], L["Kx"], L["kr"], L["B"]
        N = M.축수; T = int(시간 / dt)
        x = np.zeros((N, 2)); xm = np.zeros((N, 2)); Th = np.zeros((N, 3)); se = 0.0
        for t in range(T):
            r = M.지령(t, dt); xm = xm + dt * (xm @ Am.T + np.outer(r, Bm.flatten())); e = x - xm
            u = x @ Kx + kr * r
            Phi = np.column_stack([x[:, 0], x[:, 1], np.ones(N)])
            u = u - np.einsum("nj,nj->n", Th, Phi)
            Th = np.clip(Th + dt * gamma * Phi * (e @ P @ B)[:, None], -15, 15)
            matched = M.W1 * x[:, 0] + M.W2 * x[:, 1] + M.BIAS          # 정합만(커플링·공진 없음)
            xdd = (-a * x[:, 0] - b * x[:, 1]) + M.LAM * (u + matched)
            x[:, 1] = x[:, 1] + dt * xdd; x[:, 0] = np.clip(x[:, 0] + dt * x[:, 1], -3, 3)
            se += float(np.sum(e[:, 0] ** 2))
        return float(np.sqrt(se / (T * N)))

    r8 = 정합만_모의(8.0); r80 = 정합만_모의(80.0); r400 = 정합만_모의(400.0)
    assert r80 < r8 and r400 < r80, f"γ↑ 로 단조개선 안 됨: γ8={r8:.4f} γ80={r80:.4f} γ400={r400:.4f}"


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
