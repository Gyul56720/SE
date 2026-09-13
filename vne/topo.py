"""GT-ITM 꼴 위상 생성 -- **씨앗을 주면 같은 것이 나온다.**

GT-ITM(Georgia Tech Internetwork Topology Models)의 고전적 모델 가운데 VNE 논문이 실제로
쓰는 둘을 옮긴다.

    waxman   P(u,v) = a * exp(-d(u,v) / (b * L))   -- 거리에 따라 이어질 확률이 준다
    random   P(u,v) = p                            -- 거리와 무관 (pure random / flat)

원본 GT-ITM 은 C 로 된 `itm` 프로그램이고 transit-stub 까지 낸다. **여기 있는 것은 그
재구현이 아니라 같은 종류의 생성기다** -- 그 말을 흐리면, 뒤에 나올 수가 "GT-ITM 에서 쟀다"
로 읽히는데 실은 아니다. 원본과 대조하고 싶으면 `itm` 출력을 `읽기()` 로 받으면 된다.

자원 값은 사용자가 준 범위를 기본으로 둔다(2026-09-13): 바탕 노드 CPU 50~100, 링크 대역
20~50. 요청 쪽은 더 작다 -- 안 그러면 첫 요청이 바탕을 다 먹는다.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# 바탕망 기본값 -- 사용자가 준 범위
바탕노드수 = 50
바탕CPU범위 = (50, 100)
바탕대역범위 = (20, 50)
waxman_a, waxman_b = 0.5, 0.2          # a 가 크면 전체가 촘촘, b 가 크면 먼 것도 이어진다

# 요청망 기본값
요청노드범위 = (2, 10)
요청CPU범위 = (1, 20)
요청대역범위 = (1, 20)


@dataclass
class 망:
    """노드·링크와 그 자원. 좌표는 waxman 이 거리를 쓰므로 같이 들고 다닌다."""
    이름: str
    노드: dict = field(default_factory=dict)        # id -> {"cpu": float, "xy": (x, y)}
    링크: dict = field(default_factory=dict)        # (u, v) 오름차순 -> {"대역": float}

    def 이웃(self, u) -> list:
        return [v for (a, b) in self.링크 for v in ((b,) if a == u else (a,) if b == u else ())]

    def 링크키(self, u, v) -> tuple:
        return (u, v) if u <= v else (v, u)

    def 대역(self, u, v) -> float:
        return self.링크[self.링크키(u, v)]["대역"]

    def __repr__(self) -> str:
        return f"<망 {self.이름} 노드{len(self.노드)} 링크{len(self.링크)}>"


def _좌표(주사위, n, 크기=100.0) -> dict:
    return {i: (주사위.uniform(0, 크기), 주사위.uniform(0, 크기)) for i in range(n)}


def _거리(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def 바탕망(씨앗: int = 0, 노드수: int = 바탕노드수, 꼴: str = "waxman",
        cpu범위=바탕CPU범위, 대역범위=바탕대역범위, p: float = 0.5,
        a: float = waxman_a, b: float = waxman_b) -> 망:
    """바탕(물리)망 하나. **이어진 망만 돌려준다** -- 갈라진 망에서 잰 수용률은 위상 탓이지
    방법 탓이 아니다. 안 이어졌으면 가장 큰 덩이만 남기고 그 사실을 이름에 적는다."""
    주사위 = random.Random(씨앗)
    좌표 = _좌표(주사위, 노드수)
    g = 망(f"바탕:{꼴}:n{노드수}:s{씨앗}")
    g.노드 = {i: {"cpu": float(주사위.randint(*cpu범위)), "xy": 좌표[i]} for i in range(노드수)}
    L = math.hypot(100.0, 100.0)
    for u in range(노드수):
        for v in range(u + 1, 노드수):
            잇나 = (주사위.random() < p if 꼴 == "random"
                   else 주사위.random() < a * math.exp(-_거리(좌표[u], 좌표[v]) / (b * L)))
            if 잇나:
                g.링크[(u, v)] = {"대역": float(주사위.randint(*대역범위))}
    큰덩이 = _가장큰덩이(g)
    if len(큰덩이) < 노드수:
        g = _추리기(g, 큰덩이)
        g.이름 += f":덩이{len(큰덩이)}/{노드수}"
    return g


def 요청망(씨앗: int, 노드범위=요청노드범위, cpu범위=요청CPU범위,
        대역범위=요청대역범위, p: float = 0.5) -> 망:
    """가상망 요청 하나. 작은 망이라 pure random 으로 잇되 **이어진 것만** 낸다."""
    주사위 = random.Random(씨앗)
    for _ in range(50):
        n = 주사위.randint(*노드범위)
        g = 망(f"요청:n{n}:s{씨앗}")
        g.노드 = {i: {"cpu": float(주사위.randint(*cpu범위)), "xy": (0.0, 0.0)} for i in range(n)}
        for u in range(n):
            for v in range(u + 1, n):
                if 주사위.random() < p:
                    g.링크[(u, v)] = {"대역": float(주사위.randint(*대역범위))}
        if len(_가장큰덩이(g)) == n:
            return g
    # 쉰 번에 못 만들면 사슬로 잇는다 -- **비어 있는 요청을 돌려주지 않는다**
    for u in range(len(g.노드) - 1):
        g.링크.setdefault((u, u + 1), {"대역": float(주사위.randint(*대역범위))})
    g.이름 += ":사슬보정"
    return g


def _가장큰덩이(g: 망) -> set:
    남 = set(g.노드)
    가장 = set()
    while 남:
        시작 = next(iter(남))
        본것, 갈것 = set(), [시작]
        while 갈것:
            x = 갈것.pop()
            if x in 본것:
                continue
            본것.add(x)
            갈것 += [y for y in g.이웃(x) if y not in 본것]
        남 -= 본것
        if len(본것) > len(가장):
            가장 = 본것
    return 가장


def _추리기(g: 망, 남길: set) -> 망:
    새 = 망(g.이름)
    새.노드 = {k: v for k, v in g.노드.items() if k in 남길}
    새.링크 = {k: v for k, v in g.링크.items() if k[0] in 남길 and k[1] in 남길}
    return 새


def 요청흐름(씨앗: int = 0, 개수: int = 100, 도착률: float = 4.0,
         평균수명: float = 1000.0, 시간단위: float = 100.0) -> list:
    """요청이 오고 가는 흐름. [(들어온때, 나갈때, 요청망)] -- 때 순서다.

    도착은 포아송(시간단위당 `도착률` 개), 수명은 지수분포다. 온라인 VNE 논문이 쓰는 꼴이고,
    **수명이 있어야 자원이 돌아온다** -- 수명을 안 두면 뒤로 갈수록 전부 거절이 되어
    수용률이 방법이 아니라 요청 수의 함수가 된다."""
    주사위 = random.Random(씨앗 * 1000003 + 7)
    흐름, t = [], 0.0
    for i in range(개수):
        t += 주사위.expovariate(도착률 / 시간단위)
        흐름.append((t, t + 주사위.expovariate(1.0 / 평균수명), 요청망(씨앗 * 100000 + i)))
    return 흐름
