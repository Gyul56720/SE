"""FF(flow formulation) -- 변수와 제약을 실제 행렬로 만든다. **작은 인스턴스용이다.**

변수 (이 순서로 한 벡터에 담는다)

    x[v,u]       v in V_R, u in V_S          가상 노드 v 를 바탕 노드 u 에 놓는가
    y[e,(u,w)]   e in E_R, (u,w) in A_S      가상 링크 e 의 흐름이 바탕 호 (u,w) 를 지나는가

바탕 링크는 무향인데 흐름은 방향이 있어 링크 하나가 **호 둘**이 된다. 대역 제약에서만
둘을 합친다.

제약

    배치     sum_u x[v,u] = 1                                   모든 v
    일대일   sum_v x[v,u] <= 1                                  모든 u   <- **이 모델의 가정**
    CPU      sum_v cpu(v) x[v,u] <= cap(u)                      모든 u
    흐름보존 sum_w y[e,(u,w)] - sum_w y[e,(w,u)] = x[a,u]-x[b,u] 모든 e=(a,b), 모든 u
    대역     sum_e bw(e) (y[e,(u,w)] + y[e,(w,u)]) <= cap(u,w)   모든 링크

목적      min sum_e bw(e) * sum_arc y[e,arc]        = 비용(대역 x 홉수)

**크기.** 변수는 |V_R||V_S| + |E_R| * 2|E_S| 다. 49노드/155링크 바탕에 10노드 요청이면
만 개가 넘는다 -- 여기 있는 것은 **작은 인스턴스에서 정확히 푸는** 판이고, 큰 판은 성긴
행렬과 상용 solver 가 필요하다. 그 한계를 숨기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class 판:
    """한 인스턴스의 FF. 변수 자리를 이름으로 찾을 수 있게 색인을 들고 있다."""
    바탕: object
    요청: object
    x자리: dict                    # (v, u) -> 열 번호
    y자리: dict                    # (e, (u,w)) -> 열 번호
    호들: list
    c: np.ndarray                  # 목적 계수
    A_eq: np.ndarray
    b_eq: np.ndarray
    A_ub: np.ndarray
    b_ub: np.ndarray

    @property
    def 변수수(self) -> int:
        return len(self.c)

    def 크기(self) -> dict:
        return {"변수": self.변수수, "x": len(self.x자리), "y": len(self.y자리),
                "등식": len(self.b_eq), "부등식": len(self.b_ub),
                "V_S": len(self.바탕.노드), "E_S": len(self.바탕.링크),
                "V_R": len(self.요청.노드), "E_R": len(self.요청.링크)}


def 짓기(바탕, 요청) -> 판:
    """FF 를 행렬로 만든다. **푸는 것은 여기서 안 한다** -- 짓기와 풀기를 가른다."""
    VS = sorted(바탕.노드)
    VR = sorted(요청.노드)
    ER = sorted(요청.링크)
    호들 = [(u, w) for (u, w) in 바탕.링크] + [(w, u) for (u, w) in 바탕.링크]

    x자리, y자리, n = {}, {}, 0
    for v in VR:
        for u in VS:
            x자리[(v, u)] = n
            n += 1
    for e in ER:
        for 호 in 호들:
            y자리[(e, 호)] = n
            n += 1

    c = np.zeros(n)
    for e in ER:
        for 호 in 호들:
            c[y자리[(e, 호)]] = 요청.링크[e]["대역"]        # 비용 = 대역 x 지나는 호 수

    등식, b_eq = [], []
    for v in VR:                                            # 배치: 정확히 하나
        줄 = np.zeros(n)
        for u in VS:
            줄[x자리[(v, u)]] = 1.0
        등식.append(줄)
        b_eq.append(1.0)
    for e in ER:                                            # 흐름 보존
        a, b = e
        for u in VS:
            줄 = np.zeros(n)
            for 호 in 호들:
                if 호[0] == u:
                    줄[y자리[(e, 호)]] += 1.0
                if 호[1] == u:
                    줄[y자리[(e, 호)]] -= 1.0
            줄[x자리[(a, u)]] -= 1.0
            줄[x자리[(b, u)]] += 1.0
            등식.append(줄)
            b_eq.append(0.0)

    부등, b_ub = [], []
    for u in VS:                                            # 일대일
        줄 = np.zeros(n)
        for v in VR:
            줄[x자리[(v, u)]] = 1.0
        부등.append(줄)
        b_ub.append(1.0)
    for u in VS:                                            # CPU
        줄 = np.zeros(n)
        for v in VR:
            줄[x자리[(v, u)]] = 요청.노드[v]["cpu"]
        부등.append(줄)
        b_ub.append(바탕.노드[u]["cpu"])
    for (u, w) in 바탕.링크:                                 # 대역 (양방향 합)
        줄 = np.zeros(n)
        for e in ER:
            줄[y자리[(e, (u, w))]] += 요청.링크[e]["대역"]
            줄[y자리[(e, (w, u))]] += 요청.링크[e]["대역"]
        부등.append(줄)
        b_ub.append(바탕.링크[(u, w)]["대역"])

    return 판(바탕=바탕, 요청=요청, x자리=x자리, y자리=y자리, 호들=호들, c=c,
             A_eq=np.array(등식) if 등식 else np.zeros((0, n)),
             b_eq=np.array(b_eq), A_ub=np.array(부등) if 부등 else np.zeros((0, n)),
             b_ub=np.array(b_ub))


def 풀기(p: 판, 정수: bool = True, 시한초: float = 60.0, 목적=None, 최대화: bool = False) -> dict:
    """{상태, 값, 해, 왜}. 상태는 **세 값이다** -- `최적` / `불능` / `못잼`.

    `못잼` 은 시한초과·solver 없음·수치오류다. **불능이 아니다.** 둘을 섞으면 "못 푼 것"이
    "배치할 수 없는 것"으로 읽히고, 그 순간 수용률이 방법이 아니라 시한의 함수가 된다."""
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as e:
        return {"상태": "못잼", "값": None, "해": None, "왜": f"scipy 가 없다: {e}"}

    목 = p.c if 목적 is None else np.asarray(목적, dtype=float)
    묶음 = [LinearConstraint(p.A_eq, p.b_eq, p.b_eq)] if len(p.b_eq) else []
    if len(p.b_ub):
        묶음.append(LinearConstraint(p.A_ub, -np.inf, p.b_ub))
    정수성 = np.ones(p.변수수) if 정수 else np.zeros(p.변수수)
    try:
        r = milp(c=(-목 if 최대화 else 목), constraints=묶음,
                 integrality=정수성, bounds=Bounds(0, 1),
                 options={"time_limit": 시한초})
    except Exception as e:                                          # noqa: BLE001
        return {"상태": "못잼", "값": None, "해": None, "왜": f"{type(e).__name__}: {e}"[:160]}

    if r.status == 0 and r.x is not None:
        값 = float(-r.fun if 최대화 else r.fun)
        return {"상태": "최적", "값": 값, "해": np.asarray(r.x), "왜": ""}
    if r.status == 2:
        return {"상태": "불능", "값": None, "해": None, "왜": "제약을 다 만족하는 해가 없다"}
    # status 1=시한초과, 3=무한, 4=기타. **모르는 것을 불능이라 하지 않는다.**
    return {"상태": "못잼", "값": None, "해": None,
            "왜": f"solver status={r.status}: {getattr(r, 'message', '')}"[:160]}
