# -*- coding: utf-8 -*-
"""03 플로어플랜과 전원계획 -- T18 의 계산을 **이 넷리스트에** 건다.

T18 은 10 만 인스턴스를 가정하고 수를 냈다.  여기서는 가정이 없다: 셀 면적은
라이브러리에서, 셀 수는 합성 결과에서 온다.  그래서 이 단계의 수는 **잰 것**이다.

내놓는 것
    코어 치수 · 행 수 · 자리 수
    파워링 / 스트라이프의 폭 (IR 예산과 EM 한계 중 무는 쪽)
    전원그리드를 실제로 풀어 낸 최대 강하
    SVG 한 장 -- 강의 화면의 그 그림을, 이 칩의 수로.
"""
from __future__ import annotations

import math

자리폭, 행높이 = 0.660, 5.040


class 플로어플랜:
    def __init__(self, nl, 점유율=0.70, 종횡비=1.0, VDD=1.8,
                 전력밀도=0.25, 스트라이프수=8, IR예산비=0.03,
                 Rs상층=0.040, Rs레일=0.400, 레일폭=0.600, Jmax=2.0,
                 최소폭=0.600, 패드수=32, 패드피치=50.0, 패드폭=40.0):
        """`전력밀도` 는 W/mm^2 (가정이고 그렇게 적는다 -- 전력은 아직
        스위칭 활동을 모르므로 잴 수가 없다.  DV 단계가 잰 토글률로
        나중에 고칠 수 있게 인자로 빼 둔다)."""
        self.nl = nl
        self.점유율 = 점유율
        self.VDD = VDD
        self.전력밀도 = 전력밀도
        self.스트라이프수 = 스트라이프수
        self.IR예산비 = IR예산비
        self.Rs상층, self.Rs레일, self.레일폭 = Rs상층, Rs레일, 레일폭
        self.Jmax = Jmax
        self.최소폭 = 최소폭
        self.패드수, self.패드피치, self.패드폭 = 패드수, 패드피치, 패드폭

        self.셀면적 = nl.총면적()
        self.코어면적 = self.셀면적 / 점유율
        self.코어높이 = math.sqrt(self.코어면적 / 종횡비)
        self.행수 = max(1, int(round(self.코어높이 / 행높이)))
        self.코어높이 = self.행수 * 행높이
        self.코어폭 = self.코어면적 / self.코어높이
        self.자리수 = int(self.코어폭 / 자리폭)
        self.코어폭 = self.자리수 * 자리폭
        self.코어면적 = self.코어폭 * self.코어높이

        self.전력 = self.전력밀도 * self.코어면적 / 1e6      # W
        self.전류 = self.전력 / VDD
        self.IR예산 = IR예산비 * VDD

        # 패드 링.  둘레가 코어를 못 감싸면 **패드 제한 다이**다.
        self.패드둘레 = self.패드수 * self.패드피치
        self.패드변 = self.패드둘레 / 4
        self.패드제한 = self.패드변 > max(self.코어폭, self.코어높이)
        변 = max(self.패드변, max(self.코어폭, self.코어높이))
        self.다이폭 = 변 + 2 * self.패드폭
        self.다이높이 = 변 + 2 * self.패드폭

    # -- 전원 ---------------------------------------------------------
    def 스트라이프폭_IR(self, N=None):
        N = N or self.스트라이프수
        return (self.Rs상층 * self.코어높이 * (self.전류 / N)
                / (8 * self.IR예산))

    def 스트라이프폭_EM(self, N=None):
        N = N or self.스트라이프수
        return (self.전류 / (2 * N)) * 1e3 / self.Jmax

    def 스트라이프폭(self, N=None):
        return max(self.스트라이프폭_IR(N), self.스트라이프폭_EM(N), self.최소폭)

    def 무는것(self, N=None):
        """셋 중 무엇이 폭을 정하나 -- **최소 배선폭도 후보다.**

        작은 블록에서는 IR 도 EM 도 한참 남아서 계산상 폭이 수십 nm 로 나온다.
        그 수를 그대로 보고하면 "아주 얇아도 된다" 로 읽히는데, 실제로는 공정의
        최소 폭 아래로는 못 그린다.  **사소한 설명(블록이 작다)을 죽이지 않고
        낸 수**가 되는 자리라서 여기서 셋을 나란히 본다.
        """
        # **이름은 영어로 돌려준다** -- 이 값이 영어판 교안(T23)의 표에 그대로
        # 찍힌다.  실측: "최소폭" 을 그대로 냈더니 사다리검사의 영어판 순수성
        # 항목이 빨개졌다.  한글은 주석과 독스트링에만 둔다.
        후보 = {"IR": self.스트라이프폭_IR(N), "EM": self.스트라이프폭_EM(N),
              "min-width": self.최소폭}
        return max(후보, key=후보.get)

    def 링폭(self):
        """링은 코어 전체를 두 변에서 먹이므로 EM 이 정한다."""
        return max((self.전류 / 2) * 1e3 / self.Jmax, self.최소폭)

    def 레일강하(self, N=None):
        N = N or self.스트라이프수
        p = self.코어폭 / N
        I행 = self.전류 * (행높이 * p) / self.코어면적
        return self.Rs레일 * p / self.레일폭 * I행 / 8

    def 그리드풀기(self, N=None, 조각=200):
        """**닫힌 꼴을 안 쓰고** 스트라이프를 저항 사다리로 풀어 최대 강하를 낸다.

        `스트라이프폭` 이 IR 식에서 나온 폭일 때는 결과가 예산과 같아야 하고,
        EM 이 무는 폭일 때는 예산보다 **작아야** 한다.  두 경우 모두 검사가 본다.
        """
        import numpy as np
        N = N or self.스트라이프수
        w = self.스트라이프폭(N)
        r = self.Rs상층 * (self.코어높이 / 조각) / w
        i = (self.전류 / N) / 조각
        n = 조각 - 1
        A = np.zeros((n, n))
        b = np.full(n, -i)
        for k in range(n):
            A[k, k] = -2 / r
            if k:
                A[k, k - 1] = 1 / r
            if k + 1 < n:
                A[k, k + 1] = 1 / r
        return float(abs(np.linalg.solve(A, b)).max())

    def 트랙공급(self, 배선피치=0.56, 신호층=4):
        """스트라이프가 가져간 몫을 **빼고** 남은 배선 길이 (µm)."""
        전체 = 신호층 * (self.코어폭 / 배선피치) * self.코어높이
        먹은폭 = self.스트라이프수 * self.스트라이프폭()
        남은비 = max(0.0, 1 - 먹은폭 / self.코어폭)
        # 스트라이프는 한 층만 쓴다고 본다 -- 그 층에서만 트랙이 준다.
        return 전체 * (1 - (1 - 남은비) / 신호층)

    def 요약(self):
        return {
            "셀면적_um2": round(self.셀면적, 2),
            "점유율": self.점유율,
            "코어_um": [round(self.코어폭, 2), round(self.코어높이, 2)],
            "행수": self.행수, "행당_자리수": self.자리수,
            "다이_um": [round(self.다이폭, 2), round(self.다이높이, 2)],
            "패드제한다이": self.패드제한,
            "전력_mW": round(self.전력 * 1e3, 3),
            "전류_mA": round(self.전류 * 1e3, 3),
            "IR예산_mV": round(self.IR예산 * 1e3, 2),
            "스트라이프수": self.스트라이프수,
            "스트라이프폭_um": round(self.스트라이프폭(), 4),
            "폭후보_um": {"IR": round(self.스트라이프폭_IR(), 4),
                       "EM": round(self.스트라이프폭_EM(), 4),
                       "min-width": self.최소폭},
            "무는것": self.무는것(),
            "링폭_um": round(self.링폭(), 4),
            "그리드해_mV": round(self.그리드풀기() * 1e3, 4),
            "레일강하_mV": round(self.레일강하() * 1e3, 4),
            "트랙공급_m": round(self.트랙공급() / 1e6, 4),
        }
