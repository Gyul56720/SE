"""**센서-불가지 능동탐색의 측정된 사실을 붙든다.** 실측 2026-09-26.

## 왜

`recon/sensor_agnostic.py` 는 paper/선행조사/센서불가지_능동탐색.md 의 개념검증이다.
정성 사실(정책 불변·안개 교차·융합 우위·누수 셋 죽음)을 회귀로 잠근다. 누가 조용히
모형을 바꿔 사실이 뒤집히면 빨개진다. **값 자체가 아니라 부호·순서를 넉넉한 허용오차로**
잠근다(정량 수치는 양식화된 모델 의존 -- 과장방지).

## 무엇을 붙드나

  1. 동작점이 성하다 -- 맑은 EO 성공률 높음(재기 전 성한 동작점 확인).
  2. **정책_다음 은 센서 이름을 인자로 안 받는다**(sm 우도만) -- 불가지성의 구조적 증거.
  3. **절단선①**: 안개서 EO 붕괴 / SAR 유지 (같은 정책, 센서만 교체).
  4. **누수② 죽음**: 안개 효과가 우도 pd(r,w) 에서 나온다(센서모델만 w 를 안다).
  5. **누수① 죽음**: EO 편향 사전을 주면 SAR 도 붕괴 → 중립좌표 사전이라야 한다.
  6. **누수③ 죽음**: belief 는 센서-무관 월드좌표 격자.
  7. 융합이 어디서나 최고(우아한 퇴화 + 최고 정밀도).
"""
from __future__ import annotations

import inspect
import pathlib
import sys

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))

from recon import sensor_agnostic as S

시드 = range(12)


# ── 1. 동작점 성함 (재기 전 확인) ────────────────────────────────
def test_동작점_맑은EO_성함():
    sr = S.성공률("EO", 0.0, 시드)
    assert sr >= 0.8, f"맑은 EO 성공률 {sr:.2f} 낮음 -- 동작점 망가짐, 재보고 금지"


# ── 2. 정책은 센서 이름을 모른다 (불가지성 구조) ──────────────────
def test_정책은_센서이름을_모른다():
    params = list(inspect.signature(S.정책_다음).parameters)
    assert params == ["logb", "d", "sm", "w", "cands"], f"정책 시그니처 바뀜: {params}"
    for 금지 in ("sensor", "name", "센서", "모달", "modality"):
        assert 금지 not in params, f"정책이 센서 식별자 '{금지}'를 받음 -- 불가지성 깨짐"


# ── 3. 절단선①: 안개서 EO 붕괴 / SAR 유지 (같은 정책) ─────────────
def test_절단선_안개서_EO붕괴_SAR유지():
    eo = S.성공률("EO", 1.0, 시드)
    sar = S.성공률("SAR", 1.0, 시드)
    assert eo < 0.3, f"안개서 EO 성공률 {eo:.2f} -- 붕괴해야 함"
    assert sar > 0.5, f"안개서 SAR 성공률 {sar:.2f} -- 유지해야 함"
    assert sar > eo + 0.3, f"SAR({sar:.2f})가 EO({eo:.2f})를 크게 앞서야(안개 교차)"


# ── 4. 누수② 죽음: 안개 효과가 우도에서 ───────────────────────────
def test_누수2_안개효과는_우도에서():
    eo_pd = S.센서모델("EO")[0](5.0, 1.0)
    sar_pd = S.센서모델("SAR")[0](5.0, 1.0)
    assert eo_pd < 0.1, f"EO 우도 안개서 {eo_pd:.2f} -- 붕괴해야(정책 아닌 우도가 만듦)"
    assert sar_pd > 0.4, f"SAR 우도 안개서 {sar_pd:.2f} -- 생존해야"


# ── 5. 누수① 죽음: EO 편향 사전이 SAR 를 무너뜨린다 ───────────────
def test_누수1_grounding_편향이_전파된다():
    중립 = S.성공률("SAR", 0.9, 시드, prior="NE")
    편향 = S.성공률("SAR", 0.9, 시드, prior="EObias")
    assert 편향 < 중립 - 0.1, f"EO편향 사전({편향:.2f})이 중립({중립:.2f})보다 확실히 나빠야 -- 그래서 중립좌표 필수"


# ── 6. 누수③ 죽음: belief 는 센서-무관 월드좌표 ───────────────────
def test_누수3_belief_좌표_센서무관():
    b = S.사전(1.0, 1.0)
    assert b.shape == (S.G, S.G), f"belief shape {b.shape} -- 센서 무관 월드좌표라야"
    # 사전 함수 인자에 센서 식별자 없음
    assert list(inspect.signature(S.사전).parameters) == ["cx", "cy"]


# ── 7. 융합이 어디서나 최고 ───────────────────────────────────────
def test_융합_안개서_최고():
    f = S.융합성공률(1.0, 시드)
    eo = S.성공률("EO", 1.0, 시드)
    sar = S.성공률("SAR", 1.0, 시드)
    assert f >= 0.9, f"융합 안개 성공률 {f:.2f} -- 높아야"
    assert f >= sar and f >= eo, f"융합({f:.2f})이 단일센서(EO {eo:.2f}, SAR {sar:.2f}) 이상이어야"


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
