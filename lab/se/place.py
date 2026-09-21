# -*- coding: utf-8 -*-
"""04 배치 -- 전역 배치(연속) 다음 합법화(이산).  T19.1 이 말한 그 두 걸음.

## 무엇을 재나

    HPWL    넷마다 경계상자의 반둘레 합.  배치의 목적함수이자 배선의 예보
    겹침    합법화가 끝나면 **0 이어야 한다.**  0 이 아니면 합법화가 거짓말이다
    이동    합법화가 셀을 얼마나 밀었나 -- T19.1 의 그 '뜀'

## 왜 이렇게 푸나

전역 배치는 셀을 실수 좌표에 놓는 **연속 문제**다.  여기서는 넷마다 그 넷에
달린 것들의 무게중심으로 셀을 당기고(스타 모형), 몰리는 것을 막으려고 칸마다
밀도를 재서 밀어낸다.  전역 최적을 찾지 않는다 -- 찾을 필요도 없다.  중요한
것은 **합법화가 얼마나 망가뜨리는가**이고, 그것이 점유율과 곧장 이어진다.
"""
from __future__ import annotations

import math
import random

자리폭, 행높이 = 0.660, 5.040


class 배치기:
    def __init__(self, nl, fp, 씨=7):
        self.nl, self.fp = nl, fp
        self.r = random.Random(씨)
        self.폭 = {}                       # 인스턴스이름 -> µm
        for 이름, inst in nl.인스턴스.items():
            c = nl.라이브러리.셀들[inst.종류]
            자리 = max(1, int(math.ceil(c.면적 / (자리폭 * 행높이) - 1e-9)))
            self.폭[이름] = 자리 * 자리폭
        self.핀자리 = {}                   # ("PI"/"PO", 포트) -> (x, y)
        self._포트놓기()
        self._처음놓기()

    # -----------------------------------------------------------------
    def _포트놓기(self):
        포트 = []
        for 이름, 비트 in self.nl.입력포트.items():
            for i in range(len(비트)):
                포트.append(("PI", 이름 if len(비트) == 1 else f"{이름}[{i}]"))
        for 이름, 비트 in self.nl.출력포트.items():
            for i in range(len(비트)):
                포트.append(("PO", 이름 if len(비트) == 1 else f"{이름}[{i}]"))
        n = max(1, len(포트))
        둘레 = 2 * (self.fp.코어폭 + self.fp.코어높이)
        for k, p in enumerate(포트):
            d = 둘레 * k / n
            if d < self.fp.코어폭:
                self.핀자리[p] = (d, 0.0)
            elif d < self.fp.코어폭 + self.fp.코어높이:
                self.핀자리[p] = (self.fp.코어폭, d - self.fp.코어폭)
            elif d < 2 * self.fp.코어폭 + self.fp.코어높이:
                self.핀자리[p] = (2 * self.fp.코어폭 + self.fp.코어높이 - d,
                                self.fp.코어높이)
            else:
                self.핀자리[p] = (0.0, 둘레 - d)

    def _처음놓기(self):
        for inst in self.nl.인스턴스.values():
            inst.x = self.r.uniform(0, self.fp.코어폭 - self.폭[inst.이름])
            inst.y = self.r.uniform(0, self.fp.코어높이 - 행높이)

    # -----------------------------------------------------------------
    def 넷점들(self, n):
        """이 넷에 달린 모든 점의 (x, y).  셀은 중심, 포트는 경계 좌표."""
        점 = []
        for 자리 in ([n.몰이] if n.몰이 else []) + list(n.싣기):
            인, 핀 = 자리
            if 인 in ("PI", "PO"):
                p = self.핀자리.get((인, 핀))
                if p:
                    점.append(p)
            else:
                inst = self.nl.인스턴스[인]
                점.append((inst.x + self.폭[인] / 2, inst.y + 행높이 / 2))
        return 점

    def HPWL(self):
        s = 0.0
        for n in self.nl.넷.values():
            if n.상수 or n.몰이 is None:
                continue
            점 = self.넷점들(n)
            if len(점) < 2:
                continue
            xs = [p[0] for p in 점]
            ys = [p[1] for p in 점]
            s += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return s

    # -----------------------------------------------------------------
    def 전역(self, 바퀴=80, 밀도칸=8, 밀도세기=0.80):
        """넷이 당기고 밀도가 민다.  두 힘의 균형이 전역 배치다.

        ## 기본값은 **재서** 골랐다 (실측 2026-09-20, 이 넷리스트)

            세기  칸   전역HPWL   합법HPWL   평균이동
            0.35   8     12391      34767     28.9
            0.35  24      7835      30379     34.1   <- 전역은 제일 좋은데
            0.80   8     16641      22951     13.5   <- 합법은 이쪽이 이긴다
            1.50   8     23192      26984      8.7
            2.50  16     27470      32108      9.2

        **전역 HPWL 이 좋은 설정이 합법 HPWL 도 좋은 것이 아니다.**  덜 밀면
        셀이 가운데로 뭉치고, 뭉친 것을 행에 흩는 일을 합법화가 대신 하면서
        배치가 찾아 놓은 것을 도로 버린다(0.35/24: 7,835 -> 30,379, 288 %).
        그래서 고를 때 보는 수는 **합법화가 끝난 뒤의 HPWL** 이다 -- 배선이
        보는 것이 그것이므로.
        """
        인접 = {이름: [] for 이름 in self.nl.인스턴스}
        for n in self.nl.넷.values():
            if n.상수 or n.몰이 is None or n.id == self.fp.nl.클럭넷():
                continue
            자리들 = ([n.몰이] if n.몰이 else []) + list(n.싣기)
            if len(자리들) < 2 or len(자리들) > 20:
                continue                       # 팬아웃 큰 넷은 스타로 안 푼다
            for 인, _ in 자리들:
                if 인 in self.nl.인스턴스:
                    인접[인].append(n.id)

        for it in range(바퀴):
            새 = {}
            for 이름, inst in self.nl.인스턴스.items():
                넷들 = 인접[이름]
                if not 넷들:
                    새[이름] = (inst.x, inst.y)
                    continue
                sx = sy = w = 0.0
                for nid in 넷들:
                    점 = [p for p in self.넷점들(self.nl.넷[nid])]
                    if len(점) < 2:
                        continue
                    무게 = 1.0 / (len(점) - 1)
                    cx = sum(p[0] for p in 점) / len(점)
                    cy = sum(p[1] for p in 점) / len(점)
                    sx += 무게 * cx
                    sy += 무게 * cy
                    w += 무게
                if w == 0:
                    새[이름] = (inst.x, inst.y)
                else:
                    새[이름] = (sx / w, sy / w)
            a = 0.6
            for 이름, (nx, ny) in 새.items():
                inst = self.nl.인스턴스[이름]
                inst.x += a * (nx - inst.x - self.폭[이름] / 2)
                inst.y += a * (ny - inst.y - 행높이 / 2)

            self._밀도밀기(밀도칸, 밀도세기)
            self._가두기()
        return self.HPWL()

    def _밀도밀기(self, 칸수, 세기):
        """칸마다 면적을 세고, 넘치는 칸의 셀을 이웃으로 민다."""
        W, H = self.fp.코어폭, self.fp.코어높이
        cw, ch = W / 칸수, H / 칸수
        통 = {}
        for 이름, inst in self.nl.인스턴스.items():
            i = min(칸수 - 1, max(0, int(inst.x / cw)))
            j = min(칸수 - 1, max(0, int(inst.y / ch)))
            통.setdefault((i, j), []).append(이름)
        목표 = self.nl.총면적() / (칸수 * 칸수)
        for (i, j), 것들 in 통.items():
            면적 = sum(self.폭[k] * 행높이 for k in 것들)
            if 면적 <= 목표 * 1.15:
                continue
            cx, cy = (i + 0.5) * cw, (j + 0.5) * ch
            넘침 = min(1.0, (면적 / 목표 - 1.15))
            for k in 것들:
                inst = self.nl.인스턴스[k]
                dx, dy = inst.x - cx, inst.y - cy
                d = math.hypot(dx, dy) + 1e-6
                inst.x += 세기 * 넘침 * cw * dx / d
                inst.y += 세기 * 넘침 * ch * dy / d

    def _가두기(self):
        for 이름, inst in self.nl.인스턴스.items():
            inst.x = min(max(0.0, inst.x), self.fp.코어폭 - self.폭[이름])
            inst.y = min(max(0.0, inst.y), self.fp.코어높이 - 행높이)

    # -----------------------------------------------------------------
    def 합법화(self):
        """두 걸음으로 푼다 -- **행 배정** 다음 **행 안에서 왼쪽 채우기**.

        한 걸음으로 (바라는 x 를 지키며 아무 행에나) 넣으려 하면 앞선 셀이
        만든 틈이 용량을 먹어서, 전체 용량이 남아 있는데도 자리가 없다고
        터진다.  실측으로 그랬다(점유율 0.70, 남은 용량 910 µm).  그래서
        행을 먼저 정하고 그 행 안에서는 **틈 없이** 채운다 -- 고전적인
        Tetris/Abacus 꼴이고, 총 용량이 넉넉하면 절대 안 터진다.

        돌려주는 것: (평균이동, 최대이동, 겹침수)
        """
        행용량 = self.fp.자리수 * 자리폭
        전 = {i.이름: (i.x, i.y) for i in self.nl.인스턴스.values()}

        # 1) 행 배정 -- y 가 가까운 행부터, 용량이 남은 곳에.
        남은 = [행용량] * self.fp.행수
        행목록 = [[] for _ in range(self.fp.행수)]
        for inst in sorted(self.nl.인스턴스.values(), key=lambda i: (i.y, i.x)):
            w = self.폭[inst.이름]
            바람 = min(self.fp.행수 - 1, max(0, int(round(inst.y / 행높이))))
            for r in sorted(range(self.fp.행수),
                            key=lambda r: (abs(r - 바람), r)):
                if 남은[r] >= w - 1e-9:
                    남은[r] -= w
                    행목록[r].append(inst)
                    break
            else:
                raise RuntimeError(
                    "행 용량이 모자라 합법화가 안 된다 -- 점유율을 낮춰라 "
                    f"(지금 {self.fp.점유율}, 셀 폭 합 "
                    f"{sum(self.폭.values()):.1f} µm, 용량 "
                    f"{self.fp.행수 * 행용량:.1f} µm)")

        # 2) 행 안에서 x 를 **최대한 지키며** 겹침만 푼다 -- 두 번 쓸기.
        #
        #    왼쪽 쓸기만 하면 틈이 남아 마지막 셀이 행 밖으로 나간다.  틈을
        #    아예 없애면(무조건 0 부터 채우기) 겹침은 사라지지만 **전역 배치가
        #    찾아 놓은 x 가 통째로 버려진다** -- 실측: HPWL 이 1만에서 3.4만으로
        #    227 % 늘었다.  그래서 왼쪽으로 한 번, 넘치면 오른쪽에서 한 번 쓸어
        #    넘친 만큼만 민다(고전적인 두 번 쓸기).
        for r, 것들 in enumerate(행목록):
            것들.sort(key=lambda i: i.x)
            끝 = 0.0
            for inst in 것들:
                w = self.폭[inst.이름]
                바람 = round(inst.x / 자리폭) * 자리폭
                x = max(끝, 바람)
                inst.x, inst.y, inst.행 = x, r * 행높이, r
                끝 = x + w
            if 끝 > 행용량 + 1e-9:                 # 넘쳤다 -- 오른쪽에서 민다
                커서 = round(행용량 / 자리폭) * 자리폭
                for inst in reversed(것들):
                    w = self.폭[inst.이름]
                    x = min(inst.x, 커서 - w)
                    inst.x = x
                    커서 = x

        이동 = [math.hypot(i.x - 전[i.이름][0], i.y - 전[i.이름][1])
              for i in self.nl.인스턴스.values()]
        return (sum(이동) / len(이동), max(이동), self.겹침수())

    def 겹침수(self):
        행별 = {}
        for inst in self.nl.인스턴스.values():
            행별.setdefault(inst.행, []).append(inst)
        셈 = 0
        for r, 것들 in 행별.items():
            것들.sort(key=lambda i: i.x)
            for a, b in zip(것들, 것들[1:]):
                if a.x + self.폭[a.이름] > b.x + 1e-9:
                    셈 += 1
        return 셈

    def 자리맞음(self):
        """모든 셀이 자리 격자에 놓였나.  하나라도 아니면 합법 배치가 아니다."""
        나쁨 = 0
        for inst in self.nl.인스턴스.values():
            if abs(inst.x / 자리폭 - round(inst.x / 자리폭)) > 1e-6:
                나쁨 += 1
            if inst.행 < 0 or abs(inst.y - inst.행 * 행높이) > 1e-9:
                나쁨 += 1
        return 나쁨 == 0

    def 돌리기(self, 바퀴=80):
        시작 = self.HPWL()
        전역후 = self.전역(바퀴=바퀴)
        평균, 최대, 겹침 = self.합법화()
        끝 = self.HPWL()
        return {
            "HPWL_처음_um": round(시작, 1),
            "HPWL_전역_um": round(전역후, 1),
            "HPWL_합법_um": round(끝, 1),
            "전역이_줄인비": round(1 - 전역후 / 시작, 4),
            "합법화가_늘린비": round(끝 / 전역후 - 1, 4),
            "이동_평균_um": round(평균, 3),
            "이동_최대_um": round(최대, 3),
            "겹침": 겹침,
            "자리맞음": self.자리맞음(),
        }
