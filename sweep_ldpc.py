"""**비싼 검증.** 24시간 돌 것을 전제로 짠다 -- 이어 돌 수 있고, 한 줄씩 남긴다.

    python3 sweep_ldpc.py --단계 해저드     층 스케줄 탐색 (시뮬 없음, 싸다)
    python3 sweep_ldpc.py --단계 bler       (W, 스케일, 알파, 반복) 표면
    python3 sweep_ldpc.py                   해저드 -> bler 순서로 둘 다

## 왜 저장소 밖에 쓰나

`scripts/tests.sh` 가 검사 앞뒤로 `git status` 를 재서 **늘어난 파일을 실패로 낸다**
(검사는 재는 것이지 남기는 것이 아니다). 24시간 도는 것이 저장소 안에 쓰면 그동안의
모든 precheck 이 빨개진다. 그래서 기본 자리는 `SE_SWEEP_ROOT` 또는 `~/ldpc_sweep` 이고,
**결과를 저장소에 들일 때는 사람이 골라서 복사한다.**

## 이어 돌기

한 설정이 끝날 때마다 JSONL 한 줄을 쓰고 flush 한다. 다시 띄우면 이미 있는 열쇠는
건너뛴다. 죽어도 잃는 것은 돌던 설정 하나뿐이다.

## 첫 단계가 해저드인 까닭 -- **내 주장을 먼저 민다**

`paper/선행조사/LDPC계층복호_파이프라인.md` 에 "재배열로는 108->102 밖에 안 준다"
고 적었는데 그것은 **4000스텝 지역탐색**이었다. 최적이 훨씬 좋으면 그 말이 틀린
것이 된다. 그러니 제일 먼저, 제일 오래 민다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import sys
import time

import numpy as np

import nrldpc as F
import nrldpcfix as X

뿌리 = pathlib.Path(os.environ.get("SE_SWEEP_ROOT",
                                 pathlib.Path.home() / "ldpc_sweep"))


def _자리(이름: str) -> pathlib.Path:
    뿌리.mkdir(parents=True, exist_ok=True)
    return 뿌리 / 이름


def _이미(경로: pathlib.Path) -> set:
    본 = set()
    if 경로.exists():
        for 줄 in 경로.open(encoding="utf-8"):
            try:
                본.add(json.loads(줄)["열쇠"])
            except Exception:
                pass
    return 본


def _쓰기(f, 행: dict):
    f.write(json.dumps(행, ensure_ascii=False) + "\n")
    f.flush()
    os.fsync(f.fileno())


def 말(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ================================================================ 해저드 단계
def 지지목록(bg: str):
    표 = F.기저행렬(bg)
    R = max(r for r, _ in 표) + 1
    지 = [set() for _ in range(R)]
    for (r, c) in 표:
        지[r].add(c)
    return 지


def 멈춤수(지: list, 순서: list, D: int) -> int:
    s = 0
    for i in range(len(순서)):
        w = 0
        for back in range(1, D):
            j = i - back
            if j < 0:
                break
            if 지[순서[i]] & 지[순서[j]]:
                w = max(w, D - back)
        s += w
    return s


def 해저드단계(초: float):
    """층 순서를 오래 민다. **재배열이 정말 안 먹히는지**를 여기서 판정한다."""
    경로 = _자리("hazard.jsonl")
    본 = _이미(경로)
    끝 = time.time() + 초
    with 경로.open("a", encoding="utf-8") as f:
        for bg in ("BG1", "BG2"):
            지 = 지지목록(bg)
            R = len(지)
            for D in (2, 3, 4, 6, 8):
                열쇠 = f"hazard|{bg}|D{D}"
                if 열쇠 in 본:
                    말(f"건너뜀 {열쇠}")
                    continue
                자연 = list(range(R))
                기준 = 멈춤수(지, 자연, D)
                최선, 최선순 = 기준, 자연[:]
                rng = random.Random(0)
                시도 = 0
                조각끝 = min(끝, time.time() + max(30.0, 초 / 12))

                def 다듬기(순서):
                    """모든 쌍을 다 보는 내리막. 담금질이 멈춘 자리를 마저 내린다."""
                    nonlocal 시도
                    v = 멈춤수(지, 순서, D)
                    나아짐 = True
                    while 나아짐 and time.time() < 조각끝:
                        나아짐 = False
                        for a in range(R):
                            for b in range(a + 1, R):
                                순서[a], 순서[b] = 순서[b], 순서[a]
                                nv = 멈춤수(지, 순서, D)
                                시도 += 1
                                if nv < v:
                                    v = nv
                                    나아짐 = True
                                else:
                                    순서[a], 순서[b] = 순서[b], 순서[a]
                    return v

                v0 = 다듬기(최선순)            # 먼저 자연순서에서 끝까지 내려간다
                최선 = min(최선, v0)
                회 = 0
                while time.time() < 조각끝:
                    회 += 1
                    cur = 최선순[:] if 회 % 2 else [x for x in 자연]
                    if 회 % 2 == 0:
                        rng.shuffle(cur)
                    T = 0.5 + 2.0 * rng.random()
                    v = 멈춤수(지, cur, D)
                    for _ in range(2000):
                        a, b = rng.randrange(R), rng.randrange(R)
                        if a == b:
                            continue
                        cur[a], cur[b] = cur[b], cur[a]
                        nv = 멈춤수(지, cur, D)
                        시도 += 1
                        if nv <= v or rng.random() < pow(2.718, -(nv - v) / max(T, 1e-6)):
                            v = nv
                        else:
                            cur[a], cur[b] = cur[b], cur[a]
                        T *= 0.998
                    v = 다듬기(cur)            # 담금질 끝에서 내리막으로 마무리
                    if v < 최선:
                        최선, 최선순 = v, cur[:]
                _쓰기(f, {"열쇠": 열쇠, "종류": "해저드", "bg": bg, "D": D,
                       "층수": R, "자연순서멈춤": 기준, "최선멈춤": 최선,
                       "시도": 시도, "최선순서": 최선순,
                       "자연손실%": round(기준 / (R + 기준) * 100, 2),
                       "최선손실%": round(최선 / (R + 최선) * 100, 2)})
                말(f"{열쇠}: 자연 {기준} -> 최선 {최선} ({시도} 시도)")
                if time.time() >= 끝:
                    return


# ================================================================ BLER 단계
def 누적측정(부, snr, W, 스케일, 분자, 분모비트, 최대반복,
         목표오류=30, 최대블록=4000, 덩어리=100, 씨0=1000):
    """오류가 `목표오류` 만큼 쌓일 때까지 이어 잰다. **오류 0 이면 상한만 말한다.**"""
    블록 = 오류 = 비트오류 = 비트수 = 반복합 = 미수렴 = 0
    k = 0
    while 블록 < 최대블록 and 오류 < 목표오류:
        r = X.측정(부, snr, W=W, 스케일=스케일, 블록수=덩어리, 씨=씨0 + k,
                 최대반복=최대반복, 분자=분자, 분모비트=분모비트)
        블록 += 덩어리
        오류 += r["블록오류"]
        비트오류 += r["비트오류"]
        비트수 += 덩어리 * 부.K
        반복합 += r["평균반복"] * 덩어리
        미수렴 += r["미수렴"]
        k += 1
    return {"블록수": 블록, "블록오류": 오류, "BLER": 오류 / 블록,
            "BER": 비트오류 / max(비트수, 1), "평균반복": 반복합 / 블록,
            "미수렴": 미수렴, "상한만": 오류 == 0,
            "말": (f"오류 0 -- BLER < {3.0/블록:.2e}" if 오류 == 0
                  else f"{오류}/{블록}")}


def bler단계(초: float):
    경로 = _자리("bler.jsonl")
    본 = _이미(경로)
    끝 = time.time() + 초
    설정 = []
    # 싼 것부터. 앞쪽 결과만으로도 쓸모가 있어야 한다.
    for bg, Z in (("BG2", 16), ("BG1", 32)):
        for snr in (-2.5, -2.0, -1.5):
            for W in (4, 5, 6, 7, 8):
                for 스케일 in (1, 2, 3, 4, 6, 8):
                    설정.append((bg, Z, snr, W, 스케일, 3, 2, 20))
    # 알파와 반복은 워드폭 표면을 본 뒤에
    for bg, Z in (("BG2", 16),):
        for snr in (-2.5, -2.0):
            for W in (5, 6):
                for 스케일 in (2, 3):
                    for 분자, 분모비트 in ((1, 1), (3, 2), (7, 3), (1, 0)):
                        for 최대반복 in (8, 12, 20, 30):
                            설정.append((bg, Z, snr, W, 스케일, 분자, 분모비트, 최대반복))
    말(f"BLER 단계: 설정 {len(설정)}개, 이미 끝난 것 {len(본)}개")
    with 경로.open("a", encoding="utf-8") as f:
        for (bg, Z, snr, W, s, 분자, 분모비트, it) in 설정:
            열쇠 = f"bler|{bg}|Z{Z}|{snr}|W{W}|s{s}|a{분자}_{분모비트}|it{it}"
            if 열쇠 in 본:
                continue
            if time.time() >= 끝:
                말("시간이 다 됐다. 이어 돌면 여기서 이어간다.")
                return
            부 = F.부호(bg, Z)
            t0 = time.time()
            try:
                r = 누적측정(부, snr, W, s, 분자, 분모비트, it)
            except Exception as e:                      # 한 설정이 죽어도 계속
                _쓰기(f, {"열쇠": 열쇠, "종류": "bler", "오류": repr(e)})
                말(f"{열쇠} 실패: {e}")
                continue
            r.update({"열쇠": 열쇠, "종류": "bler", "bg": bg, "Z": Z, "snr": snr,
                      "W": W, "스케일": s, "알파": 분자 / (1 << 분모비트),
                      "최대반복": it, "걸린초": round(time.time() - t0, 1)})
            _쓰기(f, r)
            말(f"{열쇠}: BLER {r['BLER']:.4f} ({r['말']}) {r['걸린초']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--단계", default="전부", choices=["전부", "해저드", "bler"])
    ap.add_argument("--시간", type=float, default=24 * 3600, help="초")
    a = ap.parse_args()
    말(f"자리 {뿌리}   단계 {a.단계}   예산 {a.시간/3600:.1f}시간")
    시작 = time.time()
    if a.단계 in ("전부", "해저드"):
        해저드단계(min(a.시간 * 0.25, a.시간))
    if a.단계 in ("전부", "bler"):
        남 = a.시간 - (time.time() - 시작)
        if 남 > 0:
            bler단계(남)
    말(f"끝. 총 {(time.time()-시작)/3600:.2f}시간")


if __name__ == "__main__":
    main()
