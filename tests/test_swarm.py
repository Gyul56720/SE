"""**편대(스웜) 제어의 측정된 사실을 붙든다.** 실측 2026-09-26.

## 왜

`ctrl/model/swarm.py`·`tactical.py` 는 알려진 제어이론의 재현이다(신규성 없음 --
paper/선행조사/무인체계_편대제어_MPC.md). 재현이라도 **수가 맞는지**는 붙들어야
한다. 이 검사는 대화에서 실제로 잰 사실들을 회귀로 잠근다:

  1. 편대의 가장 약감쇠 집단모드는 **복소(σ±jω)** 다 -- 편대가 출렁이는 진동 모드.
  2. 다운워시가 **아래방향만(α=0)이면 안정**, **양방향이 세지면(α=0.4) 발산**.
     임계 α*≈0.225 (이 모형 안에서의 값 -- 실측 물리 아님, 과장방지).
  3. 임펄스 링잉 주파수가 **예측된 집단모드**와 맞는다(독립 대조 -- 수가 시시한
     이유로 나온 게 아니라 실제 그 모드임을 딴 길로 확인).
  4. 계획: 직선이 위협을 뚫으면 우회 웨이포인트가 삽입되고, MPC 중심궤적은 위협을
     피한다.
  5. **편대 footprint**: 계획이 중심만 피하면(또는 편대폭까지만 피해도) 바깥 드론이
     위협을 **관통**한다. 폭+실행마진까지 넣어야 **전원 회피**. 세 층이 얽힌다.

## 무엇을 붙드나 -- 부호와 순서(회귀), 넉넉한 허용오차

값 자체가 아니라 **정성적 사실**(복소인가, 안정→발산 전이, 관통→회피 전이)을 잠근다.
누가 모형을 조용히 바꿔 사실이 뒤집히면 빨개진다.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))

from ctrl.model import swarm, tactical


# ── 1. 집단모드는 복소(진동)다 ────────────────────────────────────
def test_가장_약감쇠_모드가_복소진동():
    K = swarm.그라운디드_라플라시안(6)
    m = swarm.가장_약감쇠_모드(K, kp=4.0, kd=3.0)
    assert m is not None
    lam, sig, w, zeta, 복소 = m
    assert 복소 is True                 # 복소쌍 σ±jω
    assert w > 0.1                      # 실제로 진동
    assert 0.05 < zeta < 0.4            # 약감쇠(잘 출렁임)
    assert sig < 0                      # 안정(감쇠)
    assert abs(w - 0.474) < 0.06        # 회귀: 측정된 ω


# ── 2. 다운워시: 아래방향만 안정, 양방향 세지면 발산 ──────────────
def test_다운워시_한방향_안정_양방향_발산():
    N, kp, kd = 6, 4.0, 3.0
    Wd = swarm.후류가중(N)
    # α=0 순수 아래방향 -> 결합행렬 삼각(멱영) -> 반드시 안정
    assert swarm.안정한가(swarm.결합행렬(Wd, 0.0), kp, kd)
    # α=0.4 양방향 -> 불안정(음강성 단조 발산)
    assert not swarm.안정한가(swarm.결합행렬(Wd, 0.4), kp, kd)


def test_불안정_임계_alpha():
    N, kp, kd = 6, 4.0, 3.0
    Wd = swarm.후류가중(N)
    a = swarm.불안정_임계_alpha(Wd, kp, kd)
    assert 0.15 < a < 0.30              # 회귀: α*≈0.225
    # 임계 바로 아래는 안정, 바로 위는 불안정
    assert swarm.안정한가(swarm.결합행렬(Wd, a - 0.03), kp, kd)
    assert not swarm.안정한가(swarm.결합행렬(Wd, a + 0.03), kp, kd)


def test_불안정은_단조발산_진동아님():
    # 이 모형의 다운워시 불안정은 음강성(실수 양극) -- 발산모드는 ω≈0.
    Wd = swarm.후류가중(6)
    ev = swarm.폐루프_고유값(swarm.결합행렬(Wd, 0.4), 4.0, 3.0)
    worst = ev[np.argmax(ev.real)]
    assert worst.real > 0
    assert abs(worst.imag) < 1e-3       # 단조(진동 아님)


# ── 3. 임펄스 링잉 = 예측 집단모드 (독립 대조) ────────────────────
def test_임펄스_링잉이_예측모드와_일치():
    w_meas = swarm.임펄스_링잉_주파수(N=8, kp=4.0, kd=2.0)
    K = swarm.그라운디드_라플라시안(8)
    m = swarm.가장_약감쇠_모드(K, 4.0, 2.0)
    assert w_meas is not None
    assert abs(w_meas - m[2]) / m[2] < 0.15   # 15% 이내 -> 관측=예측 모드


# ── 4. 계획 + MPC ─────────────────────────────────────────────────
def test_계획이_위협을_우회한다():
    # 직선이 위협을 뚫으면 웨이포인트 3개(우회 삽입)
    wps = tactical.계획((0, 0), (10, 0), (5, 0), 2.0)
    assert len(wps) == 3
    # 위협이 경로에서 멀면 우회 없음(2개)
    wps2 = tactical.계획((0, 0), (10, 0), (5, 50), 2.0)
    assert len(wps2) == 2


def test_mpc_중심궤적이_위협을_피한다():
    wps = tactical.계획((0, 0), (10, 0), (5, 0), 2.0)
    C = tactical.mpc_중심궤적(wps, (10, 0))
    d = np.linalg.norm(C - np.array([5.0, 0.0]), axis=1).min()
    assert d > 2.0                       # 중심궤적이 위협원 밖


# ── 5. 편대 footprint: 세 층이 얽힌다 ────────────────────────────
def test_편대는_유지되지만_중심계획만으론_관통():
    cases = tactical.스택_데모()
    이름 = [c[0] for c in cases]
    fe = {c[0]: c[2] for c in cases}
    clr = {c[0]: c[3] for c in cases}
    # 편대는 대형을 유지한다(유지오차 유계)
    for v in fe.values():
        assert v < 0.5
    # 중심만/편대폭까지는 바깥 드론이 관통(음수), 폭+실행마진이라야 전원 회피(양수)
    assert clr["중심만"] < 0
    assert clr["편대폭"] < 0
    assert clr["편대폭+실행마진"] > 0
    # 마진을 키울수록 여유가 단조 증가
    assert clr["중심만"] < clr["편대폭"] < clr["편대폭+실행마진"]


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
