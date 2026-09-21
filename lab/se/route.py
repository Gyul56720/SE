# -*- coding: utf-8 -*-
"""06 배선 -- 전역(gcell) → 상세(트랙) → 탐색 수리.  T19.4 의 그 세 걸음.

## 전역

코어를 gcell 격자로 나누고, 넷마다 핀들을 잇는 나무를 gcell 위에서 찾는다
(맨해튼 스타이너 근사: 가장 왼쪽-아래 핀을 뿌리로 L 자로 잇는다).  칸마다
**수요**를 세고 **공급**(트랙 수)과 견준다.  넘치는 칸이 있으면 그 칸을
비싸게 매기고 넘치는 넷만 다시 찾는다 -- 이것이 rip-up & reroute 다.

## 상세

칸 안에서 트랙을 실제로 배정한다.  같은 칸의 같은 층에서 트랙이 모자라면
**위반**이다.  층은 가로/세로를 번갈아 쓴다(진짜 흐름의 규칙 그대로).

## 왜 수리가 고리인가

한 넷을 옮기면 그 넷이 지나던 칸은 헐거워지고 새로 지나는 칸은 빡빡해진다.
그래서 한 바퀴에 다 안 풀리고, **바퀴마다 남는 비율**이 수렴하는지가 문제다
(T19.4 · T17.4 의 그 비 p).
"""
from __future__ import annotations

import math

행높이 = 5.040


class 배선기:
    def __init__(self, nl, 배치, fp, gcell=6.0, 배선피치=0.56, 신호층=4,
                 배선용량=0.00018, 배선저항=0.30, 씨=3):
        """`gcell` 은 칸 한 변 (µm).  `배선용량` pF/µm, `배선저항` Ω/µm."""
        self.nl, self.p, self.fp = nl, 배치, fp
        self.g = gcell
        self.피치, self.층 = 배선피치, 신호층
        self.배선용량, self.배선저항 = 배선용량, 배선저항
        self.씨 = 씨
        self.NX = max(1, int(math.ceil(fp.코어폭 / gcell)))
        self.NY = max(1, int(math.ceil(fp.코어높이 / gcell)))
        # 칸 하나의 한 방향 공급: (칸 변 / 피치) × (그 방향 층 수)
        self.공급 = (gcell / 배선피치) * (신호층 / 2)
        self.경로 = {}          # 넷id -> [(i,j), ...] 지나는 칸들
        self.벌점 = {}          # (i,j) -> 가산 비용
        self.기록 = []          # 바퀴마다 남은 위반 수

    # ----------------------------------------------------------------
    def _칸(self, x, y):
        return (min(self.NX - 1, max(0, int(x / self.g))),
                min(self.NY - 1, max(0, int(y / self.g))))

    def _넷핀칸(self, n):
        칸들 = []
        for 인, 핀 in ([n.몰이] if n.몰이 else []) + list(n.싣기):
            if 인 in ("PI", "PO"):
                자리 = self.p.핀자리.get((인, 핀))
                if 자리:
                    칸들.append(self._칸(*자리))
            else:
                inst = self.nl.인스턴스[인]
                칸들.append(self._칸(inst.x + self.p.폭[인] / 2,
                                    inst.y + 행높이 / 2))
        return 칸들

    def _L자(self, a, b, 먼저가로):
        """두 칸을 L 자로 잇는다.  지나는 칸을 전부 돌려준다."""
        (i1, j1), (i2, j2) = a, b
        길 = []
        if 먼저가로:
            for i in range(min(i1, i2), max(i1, i2) + 1):
                길.append((i, j1))
            for j in range(min(j1, j2), max(j1, j2) + 1):
                길.append((i2, j))
        else:
            for j in range(min(j1, j2), max(j1, j2) + 1):
                길.append((i1, j))
            for i in range(min(i1, i2), max(i1, i2) + 1):
                길.append((i, j2))
        return 길

    def _넷길(self, n, 벌점쓰기=True):
        """핀 칸들을 잇는 나무.  뿌리에서 L 자로 하나씩 붙인다(근사 스타이너).

        **L 자 두 방향 중 싼 쪽**을 고른다 -- 벌점이 걸린 칸을 피하게 된다.
        """
        칸들 = sorted(set(self._넷핀칸(n)))
        if len(칸들) < 2:
            return list(칸들)
        나무 = {칸들[0]}
        길 = [칸들[0]]
        남 = 칸들[1:]
        while 남:
            # 나무에서 가장 가까운 핀을 붙인다
            최선 = None
            for c in 남:
                for t in 나무:
                    d = abs(c[0] - t[0]) + abs(c[1] - t[1])
                    if 최선 is None or d < 최선[0]:
                        최선 = (d, c, t)
            _, c, t = 최선
            후보 = [self._L자(t, c, True), self._L자(t, c, False)]
            if 벌점쓰기:
                값 = [sum(self.벌점.get(k, 0.0) for k in p) for p in 후보]
                고름 = 후보[0] if 값[0] <= 값[1] else 후보[1]
            else:
                고름 = 후보[0]
            길 += 고름
            나무 |= set(고름)
            남.remove(c)
        return sorted(set(길))

    # ----------------------------------------------------------------
    def 수요(self):
        d = {}
        for nid, 길 in self.경로.items():
            for k in 길:
                d[k] = d.get(k, 0) + 1
        return d

    def 넘친칸(self):
        d = self.수요()
        return {k: v for k, v in d.items() if v > self.공급}

    def 혼잡최대(self):
        d = self.수요()
        return (max(d.values()) / self.공급) if d else 0.0

    # ----------------------------------------------------------------
    def 전역(self, 바퀴=12, 벌점증가=1.0):
        넷들 = [n for n in self.nl.넷.values()
               if not n.상수 and n.몰이 is not None
               and n.id != self.nl.클럭넷() and len(self._넷핀칸(n)) >= 2]
        for n in 넷들:
            self.경로[n.id] = self._넷길(n)
        self.기록 = []
        # **가장 좋았던 해를 붙들어 둔다.**  실측: 이 고리는 단조롭게 안 준다
        #   40 -> 21 -> 18 -> 7 -> 4 -> 2 -> 1 -> 2 -> 1 -> 1 -> 2 -> 5 -> 6
        # 마지막 해를 쓰면 **중간에 찾았던 1 을 버리고 6 을 내놓는다.**  진짜
        # 라우터도 그래서 best-so-far 를 들고 다닌다.  이것을 안 하면 "고리를
        # 더 돌릴수록 나빠진다" 는 거짓 결론까지 난다.
        최선 = None
        for it in range(바퀴):
            넘 = self.넘친칸()
            self.기록.append(len(넘))
            if 최선 is None or len(넘) < 최선[0]:
                최선 = (len(넘), dict(self.경로))
            if not 넘:
                break
            for k in 넘:
                self.벌점[k] = self.벌점.get(k, 0.0) + 벌점증가
            # 넘친 칸을 지나는 넷만 다시 찾는다 -- rip-up & reroute
            다시 = [n for n in 넷들
                  if any(k in 넘 for k in self.경로[n.id])]
            for n in 다시:
                self.경로[n.id] = self._넷길(n)
        끝 = len(self.넘친칸())
        self.기록.append(끝)
        if 최선 is not None and 최선[0] < 끝:
            self.경로 = 최선[1]
            self.되돌림 = (끝, 최선[0])
        else:
            self.되돌림 = None
        return self.기록

    # ----------------------------------------------------------------
    def 상세(self):
        """칸마다 트랙을 나눠 준다.  모자라면 위반.  층은 가로/세로 번갈아."""
        d = self.수요()
        트랙 = int(self.공급)
        위반 = {}
        for k, v in d.items():
            if v > 트랙:
                위반[k] = v - 트랙
        return 위반

    def 탐색수리(self, 바퀴=8):
        """남은 위반을 고치는 고리.  **바퀴마다 남는 비를 기록한다.**

        비가 1 로 가면 고치는 것이 아니라 **옮기고 있는 것**이다(T19.4).
        """
        열 = []
        최선 = None
        for it in range(바퀴):
            위반 = self.상세()
            남 = sum(위반.values())
            열.append(남)
            if 최선 is None or 남 < 최선[0]:
                최선 = (남, dict(self.경로))
            if 남 == 0:
                break
            for k in 위반:
                self.벌점[k] = self.벌점.get(k, 0.0) + 2.0
            넷들 = [n for n in self.nl.넷.values()
                   if n.id in self.경로
                   and any(k in 위반 for k in self.경로[n.id])]
            for n in 넷들:
                self.경로[n.id] = self._넷길(n)
        끝 = sum(self.상세().values())
        열.append(끝)
        # 전역과 같은 까닭으로 **가장 좋았던 해를 되돌린다.**  이 고리는
        # 단조롭지 않다 -- 실측 열 [2, 4, 15, 16, 13, 7, 10, 7, 9] 처럼 처음보다
        # 나빠진 채 끝나기도 한다.  그것이 T19.4 가 말한 "고치는 것이 아니라
        # 옮기고 있다" 이고, 그때 답은 한 바퀴 더 도는 것이 아니라 **위로 가서
        # 점유율이나 배치를 바꾸는 것**이다.
        되돌림 = None
        if 최선 is not None and 최선[0] < 끝:
            self.경로 = 최선[1]
            되돌림 = (끝, 최선[0])
        비 = [열[i + 1] / 열[i] for i in range(len(열) - 1) if 열[i] > 0]
        수렴 = all(b < 0.95 for b in 비) if 비 else True
        return {"열": 열, "비": [round(b, 3) for b in 비],
                "최선으로_되돌림": 되돌림, "수렴하나": 수렴,
                "최선": 최선[0] if 최선 else 0}

    # ----------------------------------------------------------------
    def 넷길이(self, nid):
        """배선 길이 (µm).  칸 수 × 칸 변 -- 전역 해에서 바로 나온다."""
        return len(self.경로.get(nid, ())) * self.g

    def 넷RC(self, nid):
        L = self.넷길이(nid)
        return self.배선저항 * L, self.배선용량 * L      # Ω, pF

    def 총배선길이(self):
        return sum(self.넷길이(n) for n in self.경로)

    def 지연함수(self):
        """STA 에 넣을 (배선지연, 배선부하) 짝.  엘모어 반쪽 모형."""
        def 지연(nid, 인, 핀):
            R, C = self.넷RC(nid)
            return 0.5 * R * (C * 1e-12) * 1e9 * 1e-3 * 1e3 * 1e-3 + \
                0.0        # 아래 주석 참고
        def 지연2(nid, 인, 핀):
            R, C = self.넷RC(nid)          # Ω, pF
            return 0.5 * R * C * 1e-3      # Ω·pF = ps -> ns 로 1e-3
        def 부하(nid):
            return self.넷RC(nid)[1]
        return 지연2, 부하

    def 요약(self):
        수 = self.수요()
        return {
            "gcell": [self.NX, self.NY],
            "칸당_공급트랙": round(self.공급, 1),
            "배선한_넷": len(self.경로),
            "총배선길이_um": round(self.총배선길이(), 1),
            "혼잡_최대": round(self.혼잡최대(), 3),
            "넘친칸": len(self.넘친칸()),
            "전역_바퀴별_넘친칸": self.기록,
            "최선으로_되돌림": self.되돌림,
            "우회비_배선길이/HPWL": round(self.총배선길이() / self.p.HPWL(), 3),
        }
