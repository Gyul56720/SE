# -*- coding: utf-8 -*-
"""house/dft/extra -- lab/se/dft 위에 얹는 것: 결정적 ATPG · MBIST · LBIST · 수율.

lab/se/dft 는 무작위 패턴으로 고장 시뮬을 돌린다. 무작위는 쉬운 고장을 빨리 잡고
**남은 것에는 영영 안 닿는다**(T21 의 희귀칸 문제가 시험의 꼴로 나타난 것). 여기서
남은 것을 결정적으로 친다.

Tessent·TetraMAX 가 없다. D 알고리즘 전체를 짓는 대신, 고장마다
**활성화(activation)와 전파(propagation)를 점수로 삼는 언덕 오르기**를 쓴다.
D 알고리즘처럼 완결적이지 않다 -- 못 닿는 고장이 남고, 그것을 "결정적으로도
못 잡았다" 로 적는다. 그 정직함이 이 파일의 목적이다.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

집 = Path(__file__).resolve().parent.parent
저장소 = 집.parent
sys.path.insert(0, str(저장소 / "lab" / "se"))

W = 64
마스크 = (1 << W) - 1


# ------------------------------------------------------------------ 결정적 ATPG

def 결정적(스캔, 남은고장, 씨=7, 상한=400, 초예산=120.0, 바퀴=14) -> dict:
    """남은 고장을 **64갈래 병렬 언덕 오르기**로 친다.

    ## 왜 병렬인가 -- 한 갈래로는 고장 하나에 20초가 걸렸다

    실측 2026-09-21: 한 벡터를 한 비트씩 뒤집는 판은 고장 2개를 치는 데 41.6 초를
    썼다.  한 번 미는 데 조합 셀 4,308개를 다 도는데, 이웃 하나를 재려고 두 번
    밀어야 했기 때문이다.

    그런데 시뮬레이터는 이미 **64비트 병렬**이다 -- 넷마다 64칸짜리 낱말을 들고
    있고 지금까지 그 64칸에 같은 값을 복제해 넣고 있었다.  그래서 칸마다 다른
    이웃을 넣는다: 0번 칸은 지금 벡터, 1~63번 칸은 한 비트씩 다르게 뒤집은 것.
    **두 번 밀면 이웃 63개가 한꺼번에 재어진다.**

    ## 점수를 무엇으로 삼나 -- 잡혔나/아닌가만으로는 기울기가 없다

    출력에서 보이나만 보면 점수가 거의 늘 0 이라 오를 데가 없다.  그래서
    **정상 시뮬과 고장 시뮬이 다른 넷의 수**를 센다 -- 고장의 영향이 얼마나
    멀리 퍼졌나다(D 프런티어의 크기).  그 수가 큰 칸으로 옮겨 간다.

    완결적이지 않다.  '못 잡았다' 는 '잡을 수 없다(redundant)' 가 아니고,
    예산에 걸려 **아예 못 쳐 본 것**은 또 다른 칸으로 낸다.
    """
    r = random.Random(씨)
    입력 = 스캔._시험입력()
    출력 = 스캔._시험출력()
    n = len(입력)
    t0 = time.time()
    잡은, 못잡은, 쓴패턴 = [], [], []
    안쳐본 = 0
    민횟수 = 0
    목록 = list(남은고장)[:상한]
    for 자리, f in enumerate(목록):
        if time.time() - t0 > 초예산:
            안쳐본 = len(목록) - 자리
            break
        바탕 = [r.randint(0, 1) for _ in range(n)]
        됐나 = False
        for _ in range(바퀴):
            뒤집 = [r.randrange(n) for _ in range(63)]          # 칸 1~63 이 뒤집을 자리
            값 = {}
            for i, b in enumerate(입력):
                값[b] = 마스크 if 바탕[i] else 0
            for 칸, i in enumerate(뒤집, start=1):
                값[입력[i]] ^= (1 << 칸)
            정상 = 스캔.밀기(값, 고장=None)
            이상 = 스캔.밀기(값, 고장=f)
            민횟수 += 2
            보임 = 0
            for b in 출력:
                보임 |= 정상.get(b, 0) ^ 이상.get(b, 0)
            if 보임:
                칸 = (보임 & -보임).bit_length() - 1          # 잡힌 칸 중 가장 낮은 것
                v = list(바탕)
                if 칸 >= 1:
                    v[뒤집[칸 - 1]] ^= 1
                잡은.append(f)
                쓴패턴.append(tuple(v))
                됐나 = True
                break
            # 칸마다 '정상과 다른 넷의 수' 를 센다 -- 이것이 기울기다
            점수 = [0] * 64
            for b, 값정상 in 정상.items():
                d = 값정상 ^ 이상.get(b, 0)
                while d:
                    낮 = (d & -d).bit_length() - 1
                    점수[낮] += 1
                    d &= d - 1
            최고 = max(range(1, 64), key=lambda k: 점수[k])
            if 점수[최고] >= 점수[0]:
                바탕[뒤집[최고 - 1]] ^= 1
        if not 됐나:
            못잡은.append(f)
    return {"시도한고장": len(잡은) + len(못잡은), "잡은": len(잡은), "못잡은": len(못잡은),
            "안쳐본": 안쳐본, "상한": 상한, "초": round(time.time() - t0, 1),
            "바퀴": 바퀴, "갈래": 64, "민횟수": 민횟수, "예산_초": 초예산,
            "새패턴": len(set(쓴패턴)), "남은고장예": [f"넷 {b} SA{s}" for b, s in 못잡은[:6]]}


# ------------------------------------------------------------------ MBIST

March알고리즘 = {
    "March C-": [("↕", "w0"), ("↑", "r0,w1"), ("↑", "r1,w0"),
                 ("↓", "r0,w1"), ("↓", "r1,w0"), ("↕", "r0")],
    "March B": [("↕", "w0"), ("↑", "r0,w1,r1,w0,r0,w1"), ("↑", "r1,w0,w1"),
                ("↓", "r1,w0,w1,w0"), ("↓", "r0,w1,w0")],
    "MATS+": [("↕", "w0"), ("↑", "r0,w1"), ("↓", "r1,w0")],
}

결함모형 = {
    "SAF (고착)": {"March C-": True, "March B": True, "MATS+": True},
    "TF (천이)": {"March C-": True, "March B": True, "MATS+": False},
    "CFin (결합-반전)": {"March C-": True, "March B": True, "MATS+": False},
    "CFid (결합-유휴)": {"March C-": True, "March B": True, "MATS+": False},
    "AF (주소)": {"March C-": True, "March B": True, "MATS+": True},
    "LF (연결)": {"March C-": False, "March B": True, "MATS+": False},
}


def mbist(깊이=1024, 폭=32, 이름="March C-", 클럭_MHz=100.0) -> dict:
    """March 알고리즘의 연산 수와 시험 시간.  N 은 주소 수다."""
    단계 = March알고리즘[이름]
    연산 = sum(len(op.split(",")) for _, op in 단계)
    주기 = 연산 * 깊이
    시간 = 주기 / (클럭_MHz * 1e6)
    덮는것 = [k for k, v in 결함모형.items() if v.get(이름)]
    못덮는것 = [k for k, v in 결함모형.items() if not v.get(이름)]
    return {"이름": 이름, "단계": 단계, "단계수": len(단계), "연산_N배": 연산,
            "깊이": 깊이, "폭": 폭, "클럭_MHz": 클럭_MHz,
            "주기": 주기, "시간_ms": round(시간 * 1e3, 4),
            "덮는결함": 덮는것, "못덮는결함": 못덮는것,
            "외부패턴_비트": 깊이 * 폭 * 2,
            "BIST면적_게이트": 220 + 12 * (깊이 - 1).bit_length() + 6 * 폭}


# ------------------------------------------------------------------ LBIST

def lfsr(폭=23, 탭=(23, 18), 길이=2000, 씨=1) -> list:
    """최대길이 LFSR 수열.  LBIST 의 패턴 발생기다."""
    st = 씨 & ((1 << 폭) - 1) or 1
    out = []
    for _ in range(길이):
        out.append(st)
        비트 = 0
        for t in 탭:
            비트 ^= (st >> (t - 1)) & 1
        st = ((st << 1) | 비트) & ((1 << 폭) - 1)
    return out


def misr(값들, 폭=16, 탭=(16, 15, 13, 4)) -> int:
    """MISR 서명.  여러 출력을 한 수로 압축한다 -- 그것이 BIST 의 판정이다."""
    st = 0
    for v in 값들:
        비트 = 0
        for t in 탭:
            비트 ^= (st >> (t - 1)) & 1
        st = (((st << 1) | 비트) ^ (v & ((1 << 폭) - 1))) & ((1 << 폭) - 1)
    return st


def 앨리어싱확률(폭=16, 패턴수=10000) -> float:
    """MISR 이 다른 오류를 같은 서명으로 압축할 확률 ≈ 2^-폭."""
    return 2.0 ** (-폭)


def lbist요약(폭=23, 패턴=4096, misr폭=16, 클럭_MHz=100.0, 체인길이=200) -> dict:
    수열 = lfsr(폭=폭, 길이=min(패턴, 4096))
    서명 = misr(수열, 폭=misr폭)
    주기 = 패턴 * (체인길이 + 1)
    return {"LFSR폭": 폭, "패턴수": 패턴, "MISR폭": misr폭, "서명": f"0x{서명:04X}",
            "주기": 주기, "시간_ms": round(주기 / (클럭_MHz * 1e6) * 1e3, 3),
            "앨리어싱": 앨리어싱확률(misr폭),
            "외부패턴대비": "테스터 메모리 0 — 패턴이 칩 안에서 만들어진다"}


# ------------------------------------------------------------------ 수율 / DPPM

def 결함수준(Y: float, T: float) -> float:
    """Williams-Brown: DL = 1 − Y^(1−T)."""
    return 1.0 - Y ** (1.0 - T)


def 결함수준_몬테카를로(Y: float, T: float, 다이=200000, 씨=3) -> float:
    """같은 수를 **다른 길로**.  다이를 하나씩 지어 결함을 뿌리고 새는 것을 센다."""
    import math
    r = random.Random(씨)
    람다 = -math.log(max(Y, 1e-12))          # 다이당 평균 결함 수 (푸아송)
    샌것 = 0
    나간것 = 0
    for _ in range(다이):
        k = _푸아송(r, 람다)
        if k == 0:
            나간것 += 1
            continue
        놓침 = all(r.random() > T for _ in range(k))
        if 놓침:
            나간것 += 1
            샌것 += 1
    return (샌것 / 나간것) if 나간것 else 0.0


def _푸아송(r, 람다):
    import math
    L, k, p = math.exp(-람다), 0, 1.0
    while True:
        p *= r.random()
        if p <= L:
            return k
        k += 1


def 수율(면적_mm2: float, 결함밀도_cm2: float) -> float:
    import math
    return math.exp(-면적_mm2 * 1e-2 * 결함밀도_cm2)
