# -*- coding: utf-8 -*-
"""밴드갭 기준의 **온도계수를 실제로 잰다** -- T11 의 수가 나온 자리.

    python3 edu/측정/bandgap.py            PTAT 이득 쓸기와 면적비 쓸기
    python3 edu/측정/bandgap.py --자해     회로가 정말 도는지만 (ngspice 필요)

회로는 고전 꼴이다: 면적비 N 인 두 다이오드 접속 BJT, 이상 연산증폭기(VCVS)가
두 가지의 전압을 같게 맞추고, R3 가 ΔV_BE 를 전류로 바꾼다.  출력은

    V_ref = V_BE + (R1/R3)·ΔV_BE,   ΔV_BE = (kT/q)·ln N

이고, 앞은 CTAT(음의 기울기) 뒤는 PTAT(양의 기울기)라 **비를 맞추면 서로
지운다.**  얼마나 지워지는지가 이 파일이 재는 것이다.

모델은 ngspice 의 기본 BJT(IS·BF·VAF만)다 -- 파운드리 소자가 아니다.  요점은
**최적이 있고 날카롭다**는 것과, 최적에서 나오는 값이 실리콘 밴드갭 근처라는 것.
"""
import json
import os
import subprocess
import sys

임시 = os.environ.get("SE_BG_TMP", "/tmp/se_bandgap")


def 덱(R3k=10.2, N=8, R1k=100.0, 시작=-40, 끝=125, 걸음=5):
    return f"""bandgap reference
.model QN NPN (IS=1e-16 BF=200 VAF=100)
Eamp out 0 a b 1e6
R1a out a {R1k}k
R1b out b {R1k}k
Q1 a a 0 QN 1
R3 b e2 {R3k}k
Q2 e2 e2 0 QN {N}
.dc TEMP {시작} {끝} {걸음}
.print dc v(out)
.end
"""


def 쓸기(R3k=10.2, N=8):
    """(평균 V_ref, 범위 V, 박스 TC ppm/°C, [(T, V)])  -- ngspice 없으면 None."""
    os.makedirs(임시, exist_ok=True)
    p = os.path.join(임시, "bg.sp")
    open(p, "w").write(덱(R3k, N))
    try:
        r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True,
                           timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    줄 = []
    for l in r.stdout.splitlines():
        t = l.split()
        if len(t) >= 3 and t[0].isdigit():
            try:
                줄.append((float(t[1]), float(t[2])))
            except ValueError:
                pass
    if not 줄:
        return None
    vs = [v for _, v in 줄]
    평균 = sum(vs) / len(vs)
    범위 = max(vs) - min(vs)
    폭 = 줄[-1][0] - 줄[0][0]
    return 평균, 범위, 범위 / 평균 / 폭 * 1e6, 줄


def 재기():
    난것 = {"PTAT이득": {}, "면적비": {}}
    for R3k in (6, 8, 9, 9.8, 10.0, 10.2, 10.3, 11, 12, 14):
        r = 쓸기(R3k=R3k)
        if r:
            난것["PTAT이득"][str(R3k)] = [round(r[0], 5), round(r[2], 1)]
    for N in (4, 8, 16, 32):
        r = 쓸기(R3k=10.0, N=N)
        if r:
            난것["면적비"][str(N)] = [round(r[0], 5), round(r[2], 1)]
    return 난것


if __name__ == "__main__":
    if "--자해" in sys.argv:
        r = 쓸기()
        if r is None:
            print("ngspice 가 없거나 회로가 안 돌았다", file=sys.stderr)
            raise SystemExit(2)
        print(f"V_ref {r[0]:.5f} V · 범위 {r[1]*1e3:.3f} mV · TC {r[2]:.1f} ppm/°C "
              f"· 점 {len(r[3])}개")
        # 밴드갭이면 1.0~1.3 V 사이라야 한다 -- 아니면 배선이 틀렸다
        raise SystemExit(0 if 1.0 < r[0] < 1.3 else 1)
    print(json.dumps(재기(), ensure_ascii=False, indent=1))
