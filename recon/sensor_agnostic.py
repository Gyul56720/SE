#!/usr/bin/env python3
# 센서-불가지 능동탐색 정책 -- 측정 가능한 골든(float) 모형. (물리 접지판, 2026-09-26)
#
# 이 파일은 paper/선행조사/센서불가지_능동탐색.md 의 개념검증을 코드화한 것이다.
# 핵심 주장: "탐색 정책 자체를 센서-불가지로" -- 정책을 픽셀이 아니라 모달리티-독립
# belief 위에 쓰고, 관측모델 p(z|x,m) 만 갈아끼우면 EO↔IR↔SAR 가 정책 코드를 한 줄도
# 안 바꾸고 돈다.
#
# 센서모델을 '문헌·실측 물리'로 접지했다(각 출처 수준이 다름 -- 정직히 표기):
#   · SAR 방위해상도 δ_az = λ·R/(2·L_sa): 캡스톤 실측 공식(77GHz λ=3.9mm, L_sa=0.26m;
#     z=0.6m 서 FWHM 5.97mm 로 검증). [출처: 캡스톤 실측 + 표준 SAR 공식]
#   · 77GHz 안개 감쇠 γ≈0.25·w dB/km (ITU-R P.840, 짙은안개 LWC 0.5 g/m³·K_l≈0.5). [출처: 문헌]
#   · 광학 안개 소광 β_vis = 3.912/V (Koschmieder), V(w): 맑음 10km→짙은안개 50m. [출처: 문헌]
#   · 거리 의존: 레이다 SNR∝1/R⁴, 광학 신호∝1/R²×투과. [표준 물리]
#
# 측정 결과(실측 2026-09-26):
#   1) 정책_다음() 은 센서 이름을 인자로 안 받는다(sm=우도만). => 센서-불가지의 구현부.
#   2) 안개서 EO 는 pd 붕괴(30m서 0.09), SAR 는 유지(0.90). 접근 무제한이면 EO 도 가까이 가
#      성공하되 ~2배 느림; standoff(≈30m) 고정이면 EO 실패·SAR 유지 = 하드 교차.
#   3) 안개 효과는 '정책'이 아니라 '우도 p(z|x,m)'가 만든다(센서모델만 w 를 안다).
#   4) belief 는 센서-무관 월드좌표 격자(카메라 깊이격자였다면 SAR 를 못 담음 -- GoalSwarm 함정).
#
# 과장방지 (ctrl/과장방지.md) -- 내 이전 양식화 가정을 스스로 잡았다:
#   · **정정**: 이전판은 'SAR σs 굵음(2.3셀)'을 줬는데 근거 없는 페널티였다. 물리상 SAR
#     방위해상도는 sub-셀(0.045셀 @30m)이다. SAR 는 굵지 않다.
#   · SAR 의 진짜 약점은 '해상도'가 아니라 (a) 개구를 만들려면 플랫폼이 움직여야(정지 스냅샷
#     불가) (b) 스페클/분류모호 이다. (a)는 탐색 중 드론이 늘 이동하므로 정량엔 안 넣고
#     정성 한계로 둔다.
#   · 캡스톤은 '해상도'를 60cm 근접장서 쟀지 '수십m 탐지율·날씨'는 안 쟀다. 거리/야외 탐지는
#     물리 외삽, 날씨는 문헌 -- 캡스톤 실측 아님. 정량은 이 접지의 가정에 의존.
from __future__ import annotations

import numpy as np

G = 24                                  # 월드 격자(센서-중립 좌표: 지상 위치)
CELL_M = 5.0                           # 격자 한 칸 = 5 m  (G=24 → 120 m 월드)
R_MAX = 9.0                             # 관측 반경 [셀] = 45 m
STEP_BUDGET = 45
_YY, _XX = np.mgrid[0:G, 0:G]
MOVES = [(4, 0), (-4, 0), (0, 4), (0, -4), (3, 3), (-3, 3), (3, -3), (-3, -3), (5, 0), (0, 5), (0, 0)]

# ── 물리 상수(출처 위 헤더) ──
_LAM = 3e8 / 77e9                       # 77 GHz 파장 = 3.9 mm
_L_SA = 0.26                            # 캡스톤 합성개구 [m]
_THETA = 1e-3                           # EO/IR 화소 각분해능 [rad]
_SIG_FLOOR = 0.7                        # 격자보다 미세하겐 국소화 못함 → σs 바닥[셀]


def _가시거리(w):  return 10000.0 * (50.0 / 10000.0) ** w          # 맑음10km→짙은안개50m
def _beta_vis(w):  return 3.912 / _가시거리(w)                      # 가시광 소광 [1/m]
def _beta_ir(w):   return 0.30 * _beta_vis(w)                       # LWIR: 가시보다 나음(대략)
def _gamma_sar(w): return (0.25 * w) / 4343.0                       # 77GHz 안개 [Np/m]


def 탐지율(이름: str, R_m, w):
    """물리 접지 탐지확률 p(detect | 표적 R_m[미터], 날씨 w). 거리 단위 = 미터."""
    R0 = 40.0
    if 이름 == "SAR":
        return 0.9 * np.minimum(1.0, (R0 / np.maximum(R_m, 1)) ** 4) * np.exp(-2 * _gamma_sar(w) * R_m)
    if 이름 == "EO":
        return 0.95 * np.minimum(1.0, (R0 / np.maximum(R_m, 1)) ** 2) * np.exp(-_beta_vis(w) * R_m)
    if 이름 == "IR":
        return 0.90 * np.minimum(1.0, (R0 / np.maximum(R_m, 1)) ** 2) * np.exp(-_beta_ir(w) * R_m)
    raise ValueError(f"모르는 센서: {이름}")


def _정밀도셀(이름, R_m=30.0):
    """측정 정밀도[셀]. SAR=방위해상도(캡스톤 공식), EO/IR=각분해능. 격자 바닥으로 클립."""
    s = (_LAM * R_m / (2 * _L_SA)) if 이름 == "SAR" else (_THETA * R_m)
    return max(_SIG_FLOOR, s / CELL_M)


def 센서모델(이름: str):
    """유일한 센서-특정 조각 = (pd(r_셀,w), σs[셀], pfa). pd 는 셀거리 받아 m 로 환산(물리 접지)."""
    pfa = {"EO": 0.01, "IR": 0.02, "SAR": 0.03}[이름]
    return (lambda r, w: 탐지율(이름, np.asarray(r) * CELL_M, w), _정밀도셀(이름), pfa)


def 융합모델():
    """세 센서 우도 합성(1-∏(1-pd)). 같은 정책에 그대로 꽂힘."""
    pds = [센서모델(n) for n in ("EO", "IR", "SAR")]
    pd = lambda r, w: 1 - np.prod([1 - p(r, w) for p, _, _ in pds], axis=0)
    return (pd, _SIG_FLOOR, 0.01)


def 사전(cx: float, cy: float) -> np.ndarray:
    """NL 공간 사전(센서-중립 좌표). belief 초기화 -- 절대 EO 전용이 아니다(누수① 방지)."""
    p = np.exp(-((_XX - cx) ** 2 + (_YY - cy) ** 2) / (2 * (G / 4) ** 2)) + 0.04
    return np.log(p / p.sum())


def 관측(logb, d, sm, w, target, rs):
    """한 관측 → 베이즈 갱신. 안개 효과는 전부 pd(r,w) 안에서(누수② 방지)."""
    pd, sgs, pfa = sm
    rt = np.hypot(target[0] - d[0], target[1] - d[1])
    detect = (rt <= R_MAX) and (rs.random() < pd(rt, w))
    if detect:
        m = np.array(target) + rs.normal(0, sgs, 2)                       # 측정 = 표적 + 잡음(정밀도)
        L = np.exp(-((_XX - m[0]) ** 2 + (_YY - m[1]) ** 2) / (2 * sgs ** 2)) + pfa
    else:
        R = np.sqrt((_XX - d[0]) ** 2 + (_YY - d[1]) ** 2)
        L = 1 - 0.85 * (R <= R_MAX).astype(float) * pd(R, w)              # 본 곳(표적 없음) 감쇠
    logb = logb + np.log(L / L.max() + 1e-9)
    logb -= logb.max()
    return logb, detect


def 정책_다음(logb, d, sm, w, cands):
    """정보이득 NBV. ★ 센서 이름을 모른다 -- sm(우도)만 받는다. 이것이 불가지성의 구현부.
    누가 여기에 센서별 분기를 넣으면 이 함수 시그니처(sm 만)가 깨진다 -- 검사가 붙든다."""
    b = np.exp(logb - logb.max()); b = b / b.sum()
    pd, sgs, pfa = sm
    best, bg = np.array(cands[0], float), -1.0
    for c in cands:
        R = np.sqrt((_XX - c[0]) ** 2 + (_YY - c[1]) ** 2)
        cover = (R <= R_MAX).astype(float) * pd(R, w)
        eig = (b * cover).sum() / (1 + 0.05 * np.hypot(c[0] - d[0], c[1] - d[1]))
        if eig > bg:
            bg, best = eig, np.array(c, float)
    return best


def 한판(sensor: str, w: float, seed: int, prior: str = "NE") -> int:
    """한 에피소드 → 표적 찾은 스텝(못 찾으면 STEP_BUDGET). prior='NE'=중립, 'EObias'=EO편향(누수① 시연)."""
    rs = np.random.default_rng(seed)
    target = (rs.uniform(G * 0.55, G * 0.9), rs.uniform(G * 0.55, G * 0.9))
    sm = 센서모델(sensor)
    logb = 사전(G * 0.72, G * 0.72) if prior == "NE" else 사전(G * 0.25, G * 0.25)
    return _주행(logb, sm, w, target, rs)


def 융합한판(w: float, seed: int) -> int:
    rs = np.random.default_rng(seed)
    target = (rs.uniform(G * 0.55, G * 0.9), rs.uniform(G * 0.55, G * 0.9))
    return _주행(사전(G * 0.72, G * 0.72), 융합모델(), w, target, rs)


def _주행(logb, sm, w, target, rs) -> int:
    d = np.array([G * 0.15, G * 0.15])
    for t in range(STEP_BUDGET):
        cands = [np.clip(d + m, 0, G - 1) for m in MOVES]
        d = 정책_다음(logb, d, sm, w, cands)
        logb, _ = 관측(logb, d, sm, w, target, rs)
        b = np.exp(logb - logb.max()); b = b / b.sum()
        est = np.array([_XX.flatten()[b.argmax()], _YY.flatten()[b.argmax()]])
        if b.max() > 0.4 and np.hypot(est[0] - target[0], est[1] - target[1]) < 2.5:
            return t + 1
    return STEP_BUDGET


def 성공률(sensor: str, w: float, seeds=range(16), prior: str = "NE"):
    fs = [한판(sensor, w, s, prior) for s in seeds]
    return float(np.mean([f < STEP_BUDGET for f in fs]))


def 융합성공률(w: float, seeds=range(16)):
    fs = [융합한판(w, s) for s in seeds]
    return float(np.mean([f < STEP_BUDGET for f in fs]))


if __name__ == "__main__":
    import inspect
    print(f"[정책 불변] 정책_다음 인자 = {list(inspect.signature(정책_다음).parameters)} (센서 이름 없음)")
    print(f"[동작점] 맑은 EO 성공률 = {성공률('EO', 0.0)*100:.0f}%")
    print(f"{'w':>5}{'EO':>7}{'IR':>7}{'SAR':>7}{'융합':>7}  (성공률%)")
    for w in (0.0, 0.5, 1.0):
        print(f"{w:>5.1f}{성공률('EO',w)*100:>7.0f}{성공률('IR',w)*100:>7.0f}"
              f"{성공률('SAR',w)*100:>7.0f}{융합성공률(w)*100:>7.0f}")
    print(f"[누수①] SAR·안개 중립사전 {성공률('SAR',0.9)*100:.0f}% vs EO편향 {성공률('SAR',0.9,prior='EObias')*100:.0f}%")
