# -*- coding: utf-8 -*-
"""08 DFT -- 스캔, 고장 시뮬, ATPG, 그리고 시험 시간과 값.

## 전스캔이면 조합회로만 남는다

모든 플롭이 스캔 체인에 들어가면, 시험할 때 플롭의 Q 는 **넣고 싶은 값을 넣을
수 있는 입력**이고 D 는 **읽어 낼 수 있는 출력**이다.  그래서 순차회로 시험이
조합회로 시험으로 바뀐다 -- 스캔이 사는 이유가 이 한 문장이다.

    시험 입력  = 기본 입력(PI) + 플롭 Q
    시험 출력  = 기본 출력(PO) + 플롭 D

## 어떻게 재나

**병렬 패턴 시뮬**을 쓴다.  파이썬 정수를 비트벡터로 삼아 한 번에 64 패턴을
민다.  고장 하나마다 넷리스트를 다시 밀어도 538 게이트 × 고장 수이므로 금방
끝난다.  느린 것을 참는 대신 **재는 것이 정확한 쪽**을 골랐다.

## 무엇이 나오나

    고장 목록      셀 핀마다 고착-0 / 고착-1
    커버리지 곡선  패턴 수에 따라 잡힌 고장의 비
    남은 고장      무작위로는 안 잡히는 것 -- T21 의 희귀칸과 같은 얘기
    시험 시간      체인 수 · 압축비를 바꿔 가며 (T22.2 의 그 표를 이 칩으로)
"""
from __future__ import annotations

import math
import random
import re

W = 64
마스크 = (1 << W) - 1


def _식(함수):
    """Liberty 의 함수 글자를 파이썬 식으로.  `!` -> `~` 만 바꾸면 된다."""
    return 함수.replace("!", "~")


class 스캔:
    def __init__(self, nl, 씨=11):
        self.nl = nl
        self.lib = nl.라이브러리
        self.r = random.Random(씨)
        self.플롭 = list(nl.플롭들)
        self._레벨화()
        self.고장 = self._고장목록()

    # ----------------------------------------------------------------
    def _레벨화(self):
        """조합 게이트를 위상 순서로 줄 세운다 (플롭 Q 는 원천)."""
        조합 = {i.이름: i for i in self.nl.조합들}
        몰이 = {}
        for n in self.nl.넷.values():
            if n.몰이 and n.몰이[0] in 조합:
                몰이[n.id] = n.몰이[0]
        진입 = {k: 0 for k in 조합}
        뒤 = {k: [] for k in 조합}
        for 이름, inst in 조합.items():
            c = self.lib.셀들[inst.종류]
            for p in c.입력핀:
                b = inst.연결.get(p.이름)
                src = 몰이.get(b)
                if src:
                    진입[이름] += 1
                    뒤[src].append(이름)
        큐 = [k for k, v in 진입.items() if v == 0]
        순서 = []
        while 큐:
            k = 큐.pop()
            순서.append(k)
            for m in 뒤[k]:
                진입[m] -= 1
                if 진입[m] == 0:
                    큐.append(m)
        if len(순서) != len(조합):
            raise ValueError("조합 논리에 고리가 있다")
        self.순서 = 순서
        self.조합 = 조합
        self.몰이 = 몰이

    def _시험입력(self):
        """PI 비트 + 플롭 Q 넷."""
        비트 = []
        for 이름, bs in self.nl.입력포트.items():
            for b in bs:
                if isinstance(b, int) and b != self.nl.클럭넷():
                    비트.append(b)
        for f in self.플롭:
            비트.append(f.연결["Q"])
        return sorted(set(비트))

    def _시험출력(self):
        비트 = []
        for 이름, bs in self.nl.출력포트.items():
            for b in bs:
                if isinstance(b, int):
                    비트.append(b)
        for f in self.플롭:
            b = f.연결["D"]
            if isinstance(b, int):
                비트.append(b)
        return sorted(set(비트))

    # ----------------------------------------------------------------
    def 밀기(self, 값, 고장=None):
        """한 번 민다.  `값` 은 {넷id: 비트벡터}.  `고장` 은 (넷id, 0|1)."""
        v = dict(값)
        if 고장:
            nid, s = 고장
            v[nid] = 마스크 if s else 0
        for 이름 in self.순서:
            inst = self.조합[이름]
            c = self.lib.셀들[inst.종류]
            환경 = {}
            for p in c.입력핀:
                b = inst.연결.get(p.이름)
                환경[p.이름] = v.get(b, 0) if isinstance(b, int) else (
                    마스크 if b == "1" else 0)
            out = c.출력핀[0]
            b = inst.연결[out.이름]
            if 고장 and b == 고장[0]:
                v[b] = 마스크 if 고장[1] else 0
                continue
            v[b] = eval(_식(out.함수), {"__builtins__": {}}, 환경) & 마스크
        return v

    # ----------------------------------------------------------------
    def _고장목록(self):
        """넷마다 고착-0 · 고착-1.  넷 하나가 곧 한 몰이와 여러 실림이므로,
        **넷 단위**로 센다 (핀 단위로 세면 같은 고장을 여러 번 센다)."""
        넷 = set()
        for inst in self.nl.인스턴스.values():
            for 핀, b in inst.연결.items():
                if isinstance(b, int):
                    넷.add(b)
        넷.discard(self.nl.클럭넷())
        return [(b, s) for b in sorted(넷) for s in (0, 1)]

    # ----------------------------------------------------------------
    def 패턴(self, n=W):
        입력 = self._시험입력()
        return {b: self.r.getrandbits(n) & ((1 << n) - 1) for b in 입력}

    def 고장시뮬(self, 묶음=8, 보고=None):
        """무작위 패턴으로 잡히는 고장을 센다 (고장 떨구기).

        돌려주는 것: {"패턴수": ..., "곡선": [(패턴수, 커버리지), ...],
                    "남은고장": [...]}
        """
        남 = list(self.고장)
        출력 = self._시험출력()
        곡선 = []
        총 = len(남)
        for k in range(묶음):
            값 = self.패턴()
            좋 = self.밀기(값)
            좋출 = [좋.get(b, 0) for b in 출력]
            새남 = []
            for f in 남:
                나쁨 = self.밀기(값, 고장=f)
                if any(a != 나쁨.get(b, 0) for a, b in zip(좋출, 출력)):
                    continue                  # 잡혔다 -- 떨군다
                새남.append(f)
            남 = 새남
            곡선.append(((k + 1) * W, round(1 - len(남) / 총, 4)))
            if 보고:
                보고(f"  패턴 {(k+1)*W:5d} -> 커버리지 "
                     f"{100*(1-len(남)/총):6.2f} %  (남은 고장 {len(남)})")
            if not 남:
                break
        return {"총고장": 총, "패턴수": len(곡선) * W,
                "커버리지": round(1 - len(남) / 총, 4),
                "곡선": 곡선, "남은고장": 남[:20], "남은수": len(남)}

    # ----------------------------------------------------------------
    def 시험시간(self, 체인수, 압축=1, 패턴수=None, 시프트클럭=50e6,
              포착=4):
        패턴수 = 패턴수 or 512
        길이 = len(self.플롭) / (체인수 * 압축)
        return 패턴수 * (길이 + 포착) / 시프트클럭

    def 패턴비트(self, 압축=1, 패턴수=None):
        패턴수 = 패턴수 or 512
        return 2 * 패턴수 * (len(self.플롭) / 압축)

    def 시험표(self, 패턴수, 목록=((1, 1), (2, 1), (4, 1), (4, 4))):
        초당 = 2_000_000.0 / (5 * 365 * 24 * 3600 * 0.70)
        줄 = []
        for 체인, 압축 in 목록:
            t = self.시험시간(체인, 압축, 패턴수)
            줄.append({"체인": 체인, "압축": 압축,
                       "시프트길이": round(len(self.플롭) / (체인 * 압축), 2),
                       "시간_ms": round(t * 1e3, 4),
                       "패턴메모리_kB": round(
                           self.패턴비트(압축, 패턴수) / 8e3, 2),
                       "다이당_값_달러": round(t * 초당, 8)})
        return 줄

    def 결함수준(self, Y, T):
        """윌리엄스–브라운.  T22.4 와 같은 식 -- 여기서는 **잰 T** 를 쓴다."""
        return 1 - Y ** (1 - T)
