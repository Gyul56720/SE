#!/usr/bin/env python3
# 센서-불가지 능동탐색 정책 -- 측정 가능한 골든(float) 모형.
#
# 이 파일은 paper/선행조사/센서불가지_능동탐색.md 의 개념검증을 코드화한 것이다.
# 핵심 주장: "탐색 정책 자체를 센서-불가지로" -- 정책을 픽셀이 아니라 모달리티-독립
# belief 위에 쓰고, 관측모델 p(z|x,m) 만 갈아끼우면 EO↔IR↔SAR 가 정책 코드를 한 줄도
# 안 바꾸고 돈다. 방산 ISR 논거: 안개서 EO 는 죽고 SAR 는 산다.
#
# 무엇을 재현/측정하나 (실측 2026-09-26):
#   1) 정책_다음() 은 센서 이름을 인자로 받지 않는다(sm=우도만). => 센서-불가지의 구현부.
#   2) 맑음→안개 쓸기: 안개서 EO 성공률 붕괴(100→0%), SAR 유지(~81%), 융합 100%. 교차 w≈0.8.
#   3) 안개 효과는 '정책'이 아니라 '우도 pd(r,w)'가 만든다(센서모델만 w 를 안다).
#   4) belief 는 센서-무관 월드좌표 격자(카메라 깊이격자였다면 SAR 레인지 우도를 못 담음).
#
# 과장방지 (ctrl/과장방지.md):
#   · 이건 2D 단순 시뮬 + 양식화된 센서모델(pd·σs 는 고른 값이지 실측 아님).
#     정성 결과(정책불변·안개교차·융합우위·누수 죽음)는 견고하나, 정량 수치는 모델 의존.
#     실제 SAR 우도는 캡스톤 실측으로 교체해야 참이 된다.
#   · 불가지성 ≠ "센서 다 동등". SAR 는 굵어서(σs 큼) 느리고 정밀도 낮다 -- 값은 '우아한
#     퇴화 + 융합이 최고'이지 SAR 단독 우수가 아니다. 미화하지 않는다.
from __future__ import annotations

import numpy as np

G = 24                                  # 월드 격자(센서-중립 좌표: 지상 위치)
R_MAX = 9.0                             # 관측 반경
STEP_BUDGET = 45
_YY, _XX = np.mgrid[0:G, 0:G]
MOVES = [(4, 0), (-4, 0), (0, 4), (0, -4), (3, 3), (-3, 3), (3, -3), (-3, -3), (5, 0), (0, 5), (0, 0)]


def 센서모델(이름: str):
    """유일한 센서-특정 조각 = (탐지확률 pd(range,weather), 측정정밀도 σs, 오경보 pfa).
    EO: 고해상(σs작), 안개에 죽음.  IR: 중간.  SAR: 저해상(σs큼), 날씨 무관(관통)."""
    if 이름 == "EO":
        return (lambda r, w: 0.95 * np.exp(-(r / R_MAX) ** 2 * 0.9) * (1 - w) ** 1.6, 0.9, 0.01)
    if 이름 == "IR":
        return (lambda r, w: 0.90 * np.exp(-(r / R_MAX) ** 2 * 0.9) * (1 - 0.55 * w), 1.4, 0.02)
    if 이름 == "SAR":
        return (lambda r, w: 0.82 * np.exp(-(r / R_MAX) ** 2 * 0.9) * (1 - 0.05 * w), 2.3, 0.03)
    raise ValueError(f"모르는 센서: {이름}")


def 융합모델():
    """세 센서 우도 합성(1-∏(1-pd)) + 가장 날카로운 정밀도. 같은 정책에 그대로 꽂힘."""
    pds = [센서모델(n) for n in ("EO", "IR", "SAR")]
    pd = lambda r, w: 1 - np.prod([1 - p(r, w) for p, _, _ in pds], axis=0)
    return (pd, 0.9, 0.01)


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
