# -*- coding: utf-8 -*-
"""SE 실습 흐름 -- RTL 에서 테스터까지 한 번에.

    python3 lab/run.py                 전부
    python3 lab/run.py --stage sta     한 단계만 (synth sta fp place cts
                                       route signoff dft dv)
    python3 lab/run.py --json out.json 결과를 파일로

각 단계는 **수를 낸다.**  그 수를 `tests/test_lab.py` 가 다시 재서 붙든다 --
이 저장소의 규율(검사하지 않은 초록불이 검사한 빨간불보다 나쁘다)을 실습에도
그대로 건다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

뿌리 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(뿌리, "se"))

단계이름 = ["synth", "sta", "fp", "place", "cts", "route", "signoff",
        "dft", "dv"]


def 돌리기(단계=None, 주기=10.0, 조용히=False, 고장묶음=6):
    """`단계` 가 None 이면 전부.  앞 단계의 결과가 뒤로 넘어간다."""
    하나 = 단계
    할것 = 단계이름 if 하나 is None else 단계이름[: 단계이름.index(하나) + 1]
    결과, 잰시간 = {}, {}

    def 찍기(*a):
        if not 조용히:
            print(*a, flush=True)

    import liberty
    import netlist
    import synth
    import sta as sta_m
    import floorplan as fp_m
    import place as place_m
    import cts as cts_m
    import route as route_m
    import signoff as so_m
    import dft as dft_m
    import dv as dv_m

    t0 = time.time()
    찍기("== 01 합성 (yosys) ==")
    길 = synth.돌리기()
    L = liberty.라이브러리(길["lib"])
    nl = netlist.넷리스트(길["json"], L)
    결과["synth"] = nl.요약()
    잰시간["synth"] = round(time.time() - t0, 2)
    찍기(f"   {결과['synth']['인스턴스']} 셀 · "
        f"{결과['synth']['플롭']} 플롭 · "
        f"{결과['synth']['셀면적_um2']} um^2")
    if "sta" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 02 STA (배선 전) ==")
    a = sta_m.분석기(nl, 주기=주기)
    r = a.풀기()
    끝 = r.끝점들[0][1]
    블록, 경로 = a.마디[끝].도착, a.경로최대(끝)
    결과["sta"] = dict(r.요약(),
                     블록기반_ps=round(블록 * 1e3, 4),
                     경로기반_ps=round(경로 * 1e3, 4),
                     두길_차이_ps=round(abs(블록 - 경로) * 1e3, 6))
    잰시간["sta"] = round(time.time() - t0, 2)
    찍기(f"   Fmax {결과['sta']['Fmax_MHz']} MHz · "
        f"두 길 차이 {결과['sta']['두길_차이_ps']} ps")
    if "fp" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 03 플로어플랜 · 전원계획 ==")
    fp = fp_m.플로어플랜(nl)
    결과["fp"] = fp.요약()
    잰시간["fp"] = round(time.time() - t0, 2)
    찍기(f"   코어 {결과['fp']['코어_um']} · {결과['fp']['행수']}행 · "
        f"스트라이프 폭을 무는 것: {결과['fp']['무는것']}")
    if "place" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 04 배치 ==")
    p = place_m.배치기(nl, fp)
    결과["place"] = p.돌리기()
    잰시간["place"] = round(time.time() - t0, 2)
    찍기(f"   HPWL {결과['place']['HPWL_합법_um']} um · "
        f"겹침 {결과['place']['겹침']} · "
        f"자리맞음 {결과['place']['자리맞음']}")
    if "cts" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 05 CTS ==")
    t = cts_m.클럭트리(nl, p)
    결과["cts"] = t.요약()
    잰시간["cts"] = round(time.time() - t0, 2)
    찍기(f"   삽입지연 {결과['cts']['삽입지연_ps']} ps · "
        f"스큐 {결과['cts']['스큐_ps']} ps · "
        f"균형 맞추는 값: 버퍼 {결과['cts']['균형맞추기']['끼운버퍼']}개, "
        f"전력 +{100*결과['cts']['균형맞추기']['전력_늘어난비']:.1f} %")
    if "route" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 06 배선 ==")
    rt = route_m.배선기(nl, p, fp)
    rt.전역()
    결과["route"] = dict(rt.요약(), 탐색수리=rt.탐색수리())
    잰시간["route"] = round(time.time() - t0, 2)
    찍기(f"   배선길이 {결과['route']['총배선길이_um']} um "
        f"(우회비 {결과['route']['우회비_배선길이/HPWL']}) · "
        f"넘친칸 {결과['route']['넘친칸']}")
    if "signoff" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 07 사인오프 (배선 뒤 재STA) ==")
    맞춘 = t.맞춘스큐()
    so = so_m.사인오프(nl, p, fp, rt, 주기=주기, 클럭스큐=-맞춘)
    결과["signoff"] = so.돌리기()
    잰시간["signoff"] = round(time.time() - t0, 2)
    찍기(f"   Fmax {결과['signoff']['배선전']['Fmax_MHz']} -> "
        f"{결과['signoff']['배선후']['Fmax_MHz']} MHz "
        f"(표류 평균 {결과['signoff']['표류_평균_ps']} ps)")
    if "dft" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 08 DFT (스캔 · 고장 시뮬 · ATPG) ==")
    sc = dft_m.스캔(nl)
    f = sc.고장시뮬(묶음=고장묶음)
    결과["dft"] = dict(f, 시험표=sc.시험표(f["패턴수"]),
                     결함수준_DPPM_Y90=round(
                         1e6 * sc.결함수준(0.90, f["커버리지"]), 2))
    잰시간["dft"] = round(time.time() - t0, 2)
    찍기(f"   고장 {f['총고장']}개 · 패턴 {f['패턴수']}개로 "
        f"커버리지 {100*f['커버리지']:.2f} % · 남은 {f['남은수']}")
    if "dv" not in 할것:
        return 결과, 잰시간

    t0 = time.time()
    찍기("== 09 DV (UVM 꼴 환경 + 변이검사) ==")
    e = dv_m.환경()
    결과["dv"] = {"회귀": e.회귀(), "변이검사": e.변이검사()}
    잰시간["dv"] = round(time.time() - t0, 2)
    회 = 결과["dv"]["회귀"]
    찍기(f"   거래 {회['거래']} · 어긋남 {회['어긋남']} · "
        f"크로스 {회['커버리지']['크로스_a_x_b']} · "
        f"변이 구멍 {결과['dv']['변이검사']['구멍']}")
    return 결과, 잰시간


def 한장요약(결과):
    """단계마다 **한 줄**.  이 줄들이 교안의 수와 같아야 한다."""
    줄 = []
    g = 결과.get
    if g("synth"):
        s = 결과["synth"]
        줄.append(f"합성      {s['인스턴스']:5d} 셀 · {s['플롭']:3d} 플롭 · "
                 f"{s['셀면적_um2']:9.1f} um^2")
    if g("sta"):
        s = 결과["sta"]
        줄.append(f"STA       Fmax {s['Fmax_MHz']:7.2f} MHz · 임계 "
                 f"{s['임계경로_단수']:3d}단 · 두 길 차이 "
                 f"{s['두길_차이_ps']} ps")
    if g("fp"):
        s = 결과["fp"]
        줄.append(f"플로어플랜 코어 {s['코어_um'][0]:.1f} x "
                 f"{s['코어_um'][1]:.1f} um · {s['행수']}행 · "
                 f"폭을 무는 것 {s['무는것']} · "
                 f"패드제한 {s['패드제한다이']}")
    if g("place"):
        s = 결과["place"]
        줄.append(f"배치      HPWL {s['HPWL_전역_um']:.0f} -> "
                 f"{s['HPWL_합법_um']:.0f} um "
                 f"(+{100*s['합법화가_늘린비']:.1f} %) · 겹침 {s['겹침']}")
    if g("cts"):
        s = 결과["cts"]
        b = s["균형맞추기"]
        줄.append(f"CTS       삽입 {s['삽입지연_ps']:.0f} ps · 스큐 "
                 f"{s['스큐_ps']:.0f} ps ({100*s['스큐/삽입지연']:.1f} %) -> "
                 f"맞추면 {b['맞춘뒤_스큐_ps']:.0f} ps, 전력 "
                 f"+{100*b['전력_늘어난비']:.1f} %")
    if g("route"):
        s = 결과["route"]
        줄.append(f"배선      {s['총배선길이_um']:.0f} um · 우회비 "
                 f"{s['우회비_배선길이/HPWL']} · 넘친칸 {s['넘친칸']}")
    if g("signoff"):
        s = 결과["signoff"]
        줄.append(f"사인오프  Fmax {s['배선전']['Fmax_MHz']:.1f} -> "
                 f"{s['배선후']['Fmax_MHz']:.1f} MHz "
                 f"(-{100*s['Fmax_떨어진비']:.1f} %) · 표류 평균 "
                 f"{s['표류_평균_ps']:.0f} ps")
    if g("dft"):
        s = 결과["dft"]
        줄.append(f"DFT       고장 {s['총고장']} · 패턴 {s['패턴수']} · "
                 f"커버리지 {100*s['커버리지']:.2f} % · 남은 {s['남은수']} · "
                 f"Y=90 %면 {s['결함수준_DPPM_Y90']:.0f} DPPM")
    if g("dv"):
        회, 변 = 결과["dv"]["회귀"], 결과["dv"]["변이검사"]
        줄.append(f"DV        거래 {회['거래']} · 어긋남 {회['어긋남']} · "
                 f"커버포인트 {100*회['커버리지']['커버포인트_비']:.0f} % · "
                 f"크로스 {회['커버리지']['크로스_a_x_b']} · "
                 f"변이 {len(변['변이'])}개 중 구멍 {변['구멍']}")
    return "\n".join(줄)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SE 실습 흐름")
    ap.add_argument("--stage", "--단계", dest="stage", choices=단계이름,
                    help="여기까지만 돈다")
    ap.add_argument("--json", help="결과를 이 파일에 적는다")
    ap.add_argument("--period", "--주기", dest="period", type=float,
                    default=10.0, help="목표 주기 (ns)")
    ap.add_argument("--quiet", "--조용히", dest="quiet", action="store_true")
    a = ap.parse_args()

    결과, 시간 = 돌리기(단계=a.stage, 주기=a.period, 조용히=a.quiet)
    print()
    print("=" * 72)
    print(한장요약(결과))
    print("=" * 72)
    print("단계별 시간(초):", 시간, " 합계",
          round(sum(시간.values()), 2))
    if a.json:
        json.dump({"결과": 결과, "시간": 시간}, open(a.json, "w"),
                  ensure_ascii=False, indent=1)
        print("->", a.json)
