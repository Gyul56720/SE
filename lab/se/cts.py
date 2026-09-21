# -*- coding: utf-8 -*-
"""05 클럭 트리 합성 -- 배치된 플롭들 위에 버퍼 트리를 세운다.

## 어떻게 짓나

잎(플롭의 클럭 핀)을 **기하로 묶어** 올라간다.  한 버퍼가 `팬아웃` 개까지
받고, 묶음의 무게중심에 버퍼를 놓는다.  그 버퍼들이 다시 잎이 되어 한 단
위로 올라가고, 하나가 남을 때까지 되풀이한다.

## 무엇을 재나

    삽입지연   뿌리에서 잎까지.  잎마다 다르다
    스큐       가장 이른 잎과 가장 늦은 잎의 차
    OCV 스큐   T19 의 그 산술을 **이 트리의 실제 공통 경로 비**로 건다
    전력       뿌리부터 잎까지 매 클럭 뒤집히는 용량

공통 경로 비를 가정하지 않는다 -- 두 잎이 어디서 갈라지는지 트리를 보고 센다.
그래서 여기서 나오는 15 % 언저리의 수는 **잰 것**이지 인용이 아니다.
"""
from __future__ import annotations

import math

행높이 = 5.040


class 클럭트리:
    def __init__(self, nl, 배치, 팬아웃=8, 버퍼="BUFX2",
                 배선용량=0.00020, 배선저항=0.20, 늦은배수=1.07,
                 이른배수=0.93, 입력천이=0.020):
        """`배선용량` pF/µm, `배선저항` Ω/µm (가정 -- 상층 금속)."""
        self.nl, self.p = nl, 배치
        self.lib = nl.라이브러리
        self.팬아웃, self.버퍼 = 팬아웃, 버퍼
        self.배선용량, self.배선저항 = 배선용량, 배선저항
        self.늦은배수, self.이른배수 = 늦은배수, 이른배수
        self.입력천이 = 입력천이
        self.마디 = []            # [(x, y, 자식들, 종류)] -- 자식은 색인
        self.잎색인 = {}          # 인스턴스이름 -> 마디 색인
        self.뿌리 = None
        self._짓기()
        self.도착 = {}
        self._풀기()

    # ----------------------------------------------------------------
    def _짓기(self):
        층 = []
        for i in self.nl.플롭들:
            자리 = (i.x + self.p.폭[i.이름] / 2, i.y + 행높이 / 2)
            색인 = len(self.마디)
            self.마디.append([자리[0], 자리[1], [], "잎", i.이름])
            self.잎색인[i.이름] = 색인
            층.append(색인)
        if not 층:
            raise ValueError("플롭이 없다 -- 클럭 트리를 세울 것이 없다")

        while len(층) > 1:
            # 기하로 묶는다: x 로 줄 세우고 팬아웃 개씩.  띠(strip) 나누기다.
            줄 = sorted(층, key=lambda k: (self.마디[k][1], self.마디[k][0]))
            띠수 = max(1, int(round(math.sqrt(len(줄) / self.팬아웃))))
            띠크기 = max(1, math.ceil(len(줄) / 띠수))
            묶음 = []
            for b in range(0, len(줄), 띠크기):
                띠 = sorted(줄[b:b + 띠크기], key=lambda k: self.마디[k][0])
                for c in range(0, len(띠), self.팬아웃):
                    묶음.append(띠[c:c + self.팬아웃])
            새층 = []
            for g in 묶음:
                cx = sum(self.마디[k][0] for k in g) / len(g)
                cy = sum(self.마디[k][1] for k in g) / len(g)
                색인 = len(self.마디)
                self.마디.append([cx, cy, list(g), "버퍼", None])
                새층.append(색인)
            층 = 새층
        self.뿌리 = 층[0]

    # ----------------------------------------------------------------
    def _가지길이(self, 부모, 자식):
        a, b = self.마디[부모], self.마디[자식]
        return abs(a[0] - b[0]) + abs(a[1] - b[1])      # 맨해튼

    def _풀기(self):
        """뿌리에서 잎으로 내려가며 도착시각을 쌓는다."""
        self.도착 = {}
        self.가지 = {}

        def 부하(색인):
            """이 마디의 출력이 보는 부하 (pF)."""
            m = self.마디[색인]
            s = 0.0
            for c in m[2]:
                s += self._가지길이(색인, c) * self.배선용량
                cm = self.마디[c]
                if cm[3] == "잎":
                    inst = self.nl.인스턴스[cm[4]]
                    셀 = self.lib.셀들[inst.종류]
                    s += next(p.용량 for p in 셀.핀들.values() if p.클럭)
                else:
                    s += self.lib.셀들[self.버퍼].핀들["A"].용량
            return s

        def 내려가기(색인, t, 천이, 경로):
            self.도착[색인] = t
            self.가지[색인] = list(경로)
            m = self.마디[색인]
            if not m[2]:
                return
            c부하 = 부하(색인)
            d = self.lib.지연(self.버퍼, "Y", "A", c부하, 천이)
            s = self.lib.천이(self.버퍼, "Y", "A", c부하, 천이)
            for k in m[2]:
                L = self._가지길이(색인, k)
                # 엘모어: 가지 저항 × 가지 용량의 절반
                w = self.배선저항 * L * (self.배선용량 * L) / 2 * 1e-3
                내려가기(k, t + d + w, s, 경로 + [색인])

        import sys
        옛 = sys.getrecursionlimit()
        sys.setrecursionlimit(max(옛, 20000))
        try:
            내려가기(self.뿌리, 0.0, self.입력천이, [])
        finally:
            sys.setrecursionlimit(옛)

    # ----------------------------------------------------------------
    def 잎도착(self):
        return {이름: self.도착[k] for 이름, k in self.잎색인.items()}

    def 삽입지연(self):
        d = list(self.잎도착().values())
        return max(d)

    def 스큐(self):
        d = list(self.잎도착().values())
        return max(d) - min(d)

    def 공통경로(self, a, b):
        """두 잎이 갈라지기 전까지의 도착시각 (ns)."""
        ka, kb = self.잎색인[a], self.잎색인[b]
        pa, pb = self.가지[ka] + [ka], self.가지[kb] + [kb]
        공통 = None
        for x, y in zip(pa, pb):
            if x != y:
                break
            공통 = x
        return self.도착[공통] if 공통 is not None else 0.0

    def OCV스큐(self, 표본=400, 씨=5):
        """**공통 경로 비를 가정하지 않고** 잎 쌍을 표본해서 잰다.

        스큐 = launch × 늦은배수 − capture × 이른배수, 단 공통 경로는 양쪽에
        같은 길이만큼 들어 있다.  T19 의 식과 같은 것을 이 트리로 계산한다.
        """
        import random
        r = random.Random(씨)
        이름들 = list(self.잎색인)
        if len(이름들) < 2:
            return 0.0, 0.0
        최악, 최악비 = 0.0, 0.0
        for _ in range(표본):
            a, b = r.sample(이름들, 2)
            ta, tb = self.잎도착()[a], self.잎도착()[b]
            공통 = self.공통경로(a, b)
            s = (공통 * self.늦은배수 + (ta - 공통) * self.늦은배수) \
                - (공통 * self.이른배수 + (tb - 공통) * self.이른배수)
            # 공통 구간에 대해 서로 다른 배수를 거는 것이 비관이다.
            s비관 = (ta * self.늦은배수) - (공통 * self.이른배수
                                       + (tb - 공통) * self.이른배수)
            if s비관 > 최악:
                최악 = s비관
                최악비 = 공통 / ta if ta > 0 else 0.0
        return 최악, 최악비

    def 균형맞추기(self, 목표비=0.02):
        """이른 잎에 지연을 더해 스큐를 목표까지 줄인다 -- 진짜 CTS 가 하는 일.

        기하로만 세운 트리는 **균형이 안 맞는다** (실측: 이 블록에서 스큐가
        삽입지연의 14.7 %였다).  CTS 는 거기서 끝내지 않고 이른 가지에 버퍼를
        끼워 도착을 맞춘다.  그 값이 얼마인지 -- 버퍼 몇 개, 전력 얼마 -- 를
        여기서 잰다.  **스큐는 공짜가 아니다.**

        돌려주는 것: (끼운 버퍼 수, 맞춘 뒤 스큐)
        """
        단위 = self.lib.지연(self.버퍼, "Y", "A",
                          self.lib.셀들[self.버퍼].핀들["A"].용량,
                          self.입력천이)
        잎 = self.잎도착()
        늦음 = max(잎.values())
        목표 = 목표비 * 늦음
        끼움 = 0
        self.더한지연 = {}
        for 이름, t in 잎.items():
            모자람 = (늦음 - 목표) - t
            if 모자람 > 0:
                n = int(math.ceil(모자람 / 단위))
                self.더한지연[이름] = n * 단위
                끼움 += n
            else:
                self.더한지연[이름] = 0.0
        self.끼운버퍼 = 끼움
        return 끼움, self.맞춘스큐()

    def 맞춘잎도착(self):
        더 = getattr(self, "더한지연", {})
        return {n: t + 더.get(n, 0.0) for n, t in self.잎도착().items()}

    def 맞춘스큐(self):
        d = list(self.맞춘잎도착().values())
        return max(d) - min(d)

    def 버퍼수(self):
        return sum(1 for m in self.마디 if m[3] == "버퍼")

    def 총가지길이(self):
        s = 0.0
        for i, m in enumerate(self.마디):
            for c in m[2]:
                s += self._가지길이(i, c)
        return s

    def 전력(self, 주파수=100e6, VDD=1.8):
        C = self.총가지길이() * self.배선용량 * 1e-12
        C += self.버퍼수() * self.lib.셀들[self.버퍼].핀들["A"].용량 * 1e-12
        for i in self.nl.플롭들:
            셀 = self.lib.셀들[i.종류]
            C += next(p.용량 for p in 셀.핀들.values() if p.클럭) * 1e-12
        return C * VDD ** 2 * 주파수

    def 단수(self):
        return max(len(v) for v in self.가지.values())

    def 요약(self, 주파수=100e6):
        ocv, 비 = self.OCV스큐()
        삽 = self.삽입지연()
        전 = self.전력(주파수)
        끼움, 맞춘 = self.균형맞추기()
        추가전력 = 끼움 * self.lib.셀들[self.버퍼].핀들["A"].용량 * 1e-12 \
            * 1.8 ** 2 * 주파수
        return {
            "잎(플롭)": len(self.잎색인),
            "버퍼": self.버퍼수(),
            "단수": self.단수(),
            "삽입지연_ps": round(삽 * 1e3, 2),
            "스큐_ps": round(self.스큐() * 1e3, 2),
            "스큐/삽입지연": round(self.스큐() / 삽, 4) if 삽 else None,
            "OCV스큐_ps": round(ocv * 1e3, 2),
            "OCV/삽입지연": round(ocv / 삽, 4) if 삽 else None,
            "최악쌍_공통경로비": round(비, 4),
            "총가지길이_um": round(self.총가지길이(), 1),
            "클럭전력_uW": round(전 * 1e6, 2),
            "균형맞추기": {
                "끼운버퍼": 끼움,
                "맞춘뒤_스큐_ps": round(맞춘 * 1e3, 2),
                "맞춘뒤_스큐비": round(맞춘 / 삽, 4) if 삽 else None,
                "추가전력_uW": round(추가전력 * 1e6, 2),
                "전력_늘어난비": round(추가전력 / 전, 4) if 전 else None,
            },
        }
