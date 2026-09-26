"""**센서-불가지 능동탐색(물리 접지판)의 측정된 사실을 붙든다.** 실측 2026-09-26.

## 왜

`recon/sensor_agnostic.py` 는 paper/선행조사/센서불가지_능동탐색.md 의 개념검증이며,
센서모델을 문헌·실측 물리로 접지했다(ITU 안개감쇠·Koschmieder 소광·캡스톤 δ_az·레이다식).
정성 사실을 회귀로 잠근다. 값 자체가 아니라 **부호·순서·자릿수**를 넉넉한 허용오차로.

## 무엇을 붙드나

  1. 동작점 성함 -- 맑은 EO 성공률 높음(재기 전 성한 동작점).
  2. **정책_다음 은 센서 이름을 인자로 안 받는다**(sm 우도만) -- 불가지성의 구조적 증거.
  3. **standoff 교차(우도)**: 안개·30m 서 EO 탐지율 붕괴(<0.15) / SAR 유지(>0.8). 안개효과가
     '정책'이 아니라 '우도 p(z|x,m)'에서 나온다(누수② 죽음).
  4. **안개서 EO 느려지고 SAR 평평**: 접근 무제한이면 EO 도 성공하되 가까이 가야 해 ~2배 느림,
     SAR 는 거리 불변이라 평평. (성공률 아닌 탐색시간으로 갈린다)
  5. **SAR 정밀도 반전(정직한 정정)**: 물리상 SAR 방위해상도 δ_az=λR/2L_sa 는 sub-미터 --
     이전 양식화의 'SAR 굵음' 가정은 근거 없었다.
  6. **누수① 구조**: 사전(grounding)은 센서 이름을 안 받는다(중립좌표).
  7. **누수③ 구조**: belief 는 센서-무관 월드좌표 격자.
  8. 융합이 어디서나 최고·최속.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

import numpy as np

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))

from recon import sensor_agnostic as S

시드 = range(12)


def _평균스텝(sensor, w):
    return float(np.mean([S.한판(sensor, w, s) for s in 시드]))


# ── 1. 동작점 성함 ────────────────────────────────────────────────
def test_동작점_맑은EO_성함():
    sr = S.성공률("EO", 0.0, 시드)
    assert sr >= 0.8, f"맑은 EO 성공률 {sr:.2f} 낮음 -- 동작점 망가짐, 재보고 금지"


# ── 2. 정책은 센서 이름을 모른다 ─────────────────────────────────
def test_정책은_센서이름을_모른다():
    params = list(inspect.signature(S.정책_다음).parameters)
    assert params == ["logb", "d", "sm", "w", "cands"], f"정책 시그니처 바뀜: {params}"
    for 금지 in ("sensor", "name", "센서", "modality"):
        assert 금지 not in params, f"정책이 센서 식별자 '{금지}'를 받음 -- 불가지성 깨짐"


# ── 3. standoff 교차: 안개서 EO 탐지율 붕괴 / SAR 유지 (우도가 만든다) ──
def test_standoff_교차_탐지율_우도에서():
    eo = float(S.탐지율("EO", 30.0, 1.0))
    sar = float(S.탐지율("SAR", 30.0, 1.0))
    assert eo < 0.15, f"안개·30m EO 탐지율 {eo:.3f} -- 붕괴해야(우도가 만듦)"
    assert sar > 0.8, f"안개·30m SAR 탐지율 {sar:.3f} -- 유지해야(77GHz 관통)"


# ── 4. 안개서 EO 느려지고 SAR 평평 ───────────────────────────────
def test_안개서_EO느려지고_SAR평평():
    eo0, eo1 = _평균스텝("EO", 0.0), _평균스텝("EO", 1.0)
    sar0, sar1 = _평균스텝("SAR", 0.0), _평균스텝("SAR", 1.0)
    assert eo1 > 1.4 * eo0, f"EO 안개서 느려져야: 맑음{eo0:.1f}→안개{eo1:.1f}"
    assert sar1 < 1.3 * sar0, f"SAR 안개서 평평해야: 맑음{sar0:.1f}→안개{sar1:.1f}"


# ── 5. SAR 정밀도 반전(정직한 정정): 물리상 굵지 않다 ────────────
def test_SAR_정밀도_반전_sub미터():
    δ = S._LAM * 30.0 / (2 * S._L_SA)          # 방위해상도 @30m [m]
    assert δ < 1.0, f"SAR δ_az {δ:.3f}m -- sub-미터라야(SAR 는 굵지 않다)"


# ── 6. 누수① 구조: grounding 은 센서 이름을 안 받는다 ────────────
def test_누수1_grounding_센서중립():
    assert list(inspect.signature(S.사전).parameters) == ["cx", "cy"], "사전이 센서 식별자를 받음"


# ── 7. 누수③ 구조: belief 는 센서-무관 월드좌표 ──────────────────
def test_누수3_belief_좌표_센서무관():
    b = S.사전(1.0, 1.0)
    assert b.shape == (S.G, S.G), f"belief shape {b.shape} -- 센서 무관 월드좌표라야"


# ── 8. 융합이 어디서나 최고·최속 ─────────────────────────────────
def test_융합_안개서_최고최속():
    f = S.융합성공률(1.0, 시드)
    assert f >= 0.9, f"융합 안개 성공률 {f:.2f} -- 높아야"
    f_step = float(np.mean([S.융합한판(1.0, s) for s in 시드]))
    assert f_step <= _평균스텝("EO", 1.0), f"융합({f_step:.1f})이 EO 안개({_평균스텝('EO',1.0):.1f})보다 빨라야"


# ── 9. 통합정책: 센서선택이 창발한다(손코딩 규칙 아님) ──────────
def test_통합정책_센서선택_창발():
    # 맑음이면 EO, 짙은안개면 SAR 를 '고르게 된다' -- J 최대만으로. 손코딩 임계값 없음.
    assert S.고른센서(4.0, 0.0) == "EO", "맑음서 EO 안 고름 -- 창발 실패"
    assert S.고른센서(4.0, 1.0) == "SAR", "짙은안개서 SAR 안 고름 -- 창발 실패"


# ── 10. 통합정책이 안개서 최선 고정센서를 따라간다 ───────────────
def test_통합정책_안개서_최선센서추종():
    ji = np.mean([S.통합에피소드(1.0, s)[0] for s in 시드])
    je = np.mean([S.고정센서에피소드("EO", 1.0, s)[0] for s in 시드])
    js = np.mean([S.고정센서에피소드("SAR", 1.0, s)[0] for s in 시드])
    assert ji > je + 0.03, f"통합 J({ji:.3f})이 EO전용({je:.3f})을 안개서 크게 앞서야"
    assert ji >= js - 0.02, f"통합 J({ji:.3f})이 최선(SAR {js:.3f})을 따라가야"


# ── 11. RTA: 위협 keep-out 접근을 차단한다 ───────────────────────
def test_통합정책_RTA_keepout_차단():
    위협 = np.array([S.G * 0.55, S.G * 0.72])
    trips = sum(S.통합에피소드(1.0, s, 위협, 4.0)[4] for s in 시드)
    assert trips > 0, "RTA 가 한 번도 keep-out 접근을 차단 안 함"


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
