# -*- coding: utf-8 -*-
"""6T SRAM 셀의 **정적 잡음 여유(SNM)를 실제로 잰다** -- T4 의 수가 나온 자리.

    python3 edu/측정/snm.py            셀비(β) 쓸기와 전압 쓸기 -- 표로 찍는다
    python3 edu/측정/snm.py --자해     추출기만 두 극한으로 확인한다 (ngspice 불필요)

## 왜 이 파일이 있나

교재에 수를 적으려면 **그 수가 어디서 나왔는지 돌려 볼 수 있어야 한다.**  붙여
넣은 수는 다음 사람이 확인할 길이 없고, 확인할 수 없는 수는 이 저장소에서
주장일 뿐이다.

## 두 번 틀렸다 -- 그리고 둘 다 그럴듯했다

1. 처음 추출기는 **가로 거리**를 쟀다(내접 정사각형이 아니라). hold SNM 이
   0.5·VDD 로 나왔다 -- 너무 크다.
2. 접근 트랜지스터를 `MACC vr bl 0` 으로 붙였다 -- 게이트가 워드라인이 아니라
   비트라인이었다. read SNM 이 **셀비가 커질수록 줄었다.** 거꾸로다.

**값이 아니라 경향이 버그를 잡았다.**  그래서 이 파일은 쓰기 전에 추출기를
두 극한으로 확인한다(`--자해`): 이득이 아주 큰 인버터는 VDD/2, 이득 1 은 0.

## 모델

`LEVEL=1` 제곱법칙이다(VTO=0.35, KP_n=200µ, KP_p=80µ).  **파운드리 셀의 절댓값이
아니다** -- 방법과 경향이 요점이고, 교재도 그렇게 적는다.
"""
import bisect
import json
import math
import os
import subprocess
import sys

VDD기본 = 1.0
임시 = os.environ.get("SE_SNM_TMP", "/tmp/se_snm")


def _보간(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_left(xs, x)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0


def snm(xs, ys, VDD=VDD기본, 칸=400):
    """나비곡선에 드는 **가장 큰 정사각형의 변**.

    아래 왼쪽 눈은 위로 A(x)=f(x), 아래로 거울곡선 B(x)=f⁻¹(x) 로 막힌다.
    둘 다 감소하므로 왼쪽 아래 모서리를 (x0, B(x0)) 에 두면 조건이 하나다:

        f(x0 + s) - s ≥ B(x0)

    s 에 대해 왼쪽이 단조감소라 이분법으로 가장 큰 s 를 찾고, x0 을 쓸어 최댓값을 
    취한다.
    """
    rx, ry = list(reversed(ys)), list(reversed(xs))      # f⁻¹
    큰것 = 0.0
    for k in range(칸):
        x0 = VDD * k / (칸 - 1)
        b = _보간(rx, ry, x0)
        lo, hi = 0.0, VDD
        for _ in range(50):
            s = (lo + hi) / 2
            if _보간(xs, ys, x0 + s) - s >= b:
                lo = s
            else:
                hi = s
        큰것 = max(큰것, lo)
    return 큰것


def 자해():
    """추출기가 옳은지 **두 극한으로** 본다.  돌려주는 것: (아주큰이득, 이득1)"""
    V = 1.0
    xs = [i / 2000 * V for i in range(2001)]
    급 = [V / (1 + math.exp((x - V / 2) * 400)) for x in xs]
    평 = [V - x for x in xs]
    return snm(xs, 급, V), snm(xs, 평, V)


def 덱(VDD=VDD기본, beta=2.0, 읽기=True, wacc=0.4, wpu=0.5):
    """6T 셀의 반쪽.  VL 을 쓸고 VR 을 읽는다.

    읽기=True 면 접근 트랜지스터가 켜져 있다(워드라인=VDD, 비트라인=VDD) --
    **게이트가 워드라인**이다.  여기를 틀리면 경향이 뒤집힌다.
    """
    acc = (f"MACC bl wl vr 0 NM W={wacc}u L=0.1u" if 읽기 else "* hold (word line low)")
    return f"""6T half cell (beta={beta}, {'read' if 읽기 else 'hold'})
.model NM NMOS (LEVEL=1 VTO=0.35 KP=200u LAMBDA=0.05 GAMMA=0)
.model PM PMOS (LEVEL=1 VTO=-0.35 KP=80u LAMBDA=0.05 GAMMA=0)
VDD vdd 0 {VDD}
VWL wl 0 {VDD}
VBL bl 0 {VDD}
VIN vl 0 0
MPU vdd vl vr vdd PM W={wpu}u L=0.1u
MPD vr vl 0 0 NM W={beta*wacc}u L=0.1u
{acc}
.dc VIN 0 {VDD} {VDD/250}
.print dc v(vr)
.end
"""


def 곡선(VDD=VDD기본, beta=2.0, 읽기=True):
    """ngspice 를 돌려 VTC 를 얻는다.  ngspice 가 없으면 (None, None)."""
    os.makedirs(임시, exist_ok=True)
    p = os.path.join(임시, "cell.sp")
    open(p, "w").write(덱(VDD, beta, 읽기))
    try:
        r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True,
                           timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, None
    xs, ys = [], []
    for l in r.stdout.splitlines():
        t = l.split()
        if len(t) == 3 and t[0].isdigit():
            try:
                xs.append(float(t[1]))
                ys.append(float(t[2]))
            except ValueError:
                pass
    return (xs, ys) if xs else (None, None)


def 재기():
    """교재 T4 에 실린 두 표를 만든다."""
    큰, 평 = 자해()
    난것 = {"자해": {"큰이득": round(큰, 4), "이득1": round(평, 4)}, "셀비": {}, "전압": {}}
    if not (0.45 < 큰 < 0.52 and 평 < 0.02):
        raise SystemExit(f"추출기 자해검사 실패: 큰이득 {큰:.4f}(≈0.5) · 이득1 {평:.4f}(≈0)")
    for 이름, 읽기 in (("hold", False), ("read", True)):
        for b in (1.0, 1.5, 2.0, 2.5, 3.0):
            xs, ys = 곡선(beta=b, 읽기=읽기)
            if xs:
                난것["셀비"][f"{이름} β={b}"] = round(snm(xs, ys), 4)
    for V in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        xs, ys = 곡선(VDD=V, beta=2.0, 읽기=True)
        if xs:
            난것["전압"][f"{V:.2f}"] = round(snm(xs, ys, V), 4)
    return 난것


if __name__ == "__main__":
    if "--자해" in sys.argv:
        큰, 평 = 자해()
        print(f"이득 큰 인버터 {큰:.4f} (≈0.5) · 이득 1 {평:.4f} (≈0)")
        raise SystemExit(0 if (0.45 < 큰 < 0.52 and 평 < 0.02) else 1)
    print(json.dumps(재기(), ensure_ascii=False, indent=1))
