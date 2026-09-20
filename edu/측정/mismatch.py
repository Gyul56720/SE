# -*- coding: utf-8 -*-
"""전류거울의 **불일치를 몬테카를로로 잰다** -- T12 의 수가 나온 자리.

    python3 edu/측정/mismatch.py           면적 쓸기와 전류 쓸기
    python3 edu/측정/mismatch.py --자해    거울이 정말 1:1 을 내는지 (ngspice 필요)

문턱전압 불일치를 Pelgrom 꼴로 넣는다: σ(ΔV_th) = A_VT/√(W·L).  그 한 줄이
가정이고, 나머지는 회로가 만든다 -- **거울비의 분포는 잰 것이다.**
"""
import json
import math
import os
import random
import statistics
import subprocess
import sys

AVT = 5e-3            # V·µm -- 이 자리의 가정
임시 = os.environ.get("SE_MM_TMP", "/tmp/se_mismatch")


def 한판(W, L, dvt, Iref):
    os.makedirs(임시, exist_ok=True)
    d = f"""current mirror mismatch
.model NM  NMOS (LEVEL=1 VTO=0.4 KP=200u LAMBDA=0.0)
.model NM2 NMOS (LEVEL=1 VTO={0.4 + dvt:.6f} KP=200u LAMBDA=0.0)
Vdd vdd 0 1.8
Iref vdd d1 {Iref}
M1 d1 d1 0 0 NM  W={W}u L={L}u
Vd2 d2 0 0.9
M2 d2 d1 0 0 NM2 W={W}u L={L}u
.op
.print op i(Vd2)
.end
"""
    p = os.path.join(임시, "m.sp")
    open(p, "w").write(d)
    try:
        r = subprocess.run(["ngspice", "-b", p], capture_output=True, text=True,
                           timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    for l in r.stdout.splitlines():
        s = l.lower()
        if "vd2#branch" in s or "i(vd2)" in s:
            try:
                return abs(float(l.split()[-1]))
            except ValueError:
                pass
    return None


def 몬테카를로(W, L, Iref=10e-6, 판수=80, 씨=11):
    """(σ_Vt, [거울비...])  -- ngspice 가 없으면 (σ_Vt, [])."""
    rng = random.Random(씨)
    시그마 = AVT / math.sqrt(W * L)
    난것 = []
    for _ in range(판수):
        v = 한판(W, L, rng.gauss(0, 시그마), Iref)
        if v:
            난것.append(v / Iref)
    return 시그마, 난것


def 재기(판수=80):
    난것 = {"면적": {}, "전류": {}}
    for W, L in ((1, 0.2), (2, 0.4), (4, 0.8), (8, 1.6)):
        시그마, b = 몬테카를로(W, L, 판수=판수)
        if b:
            난것["면적"][f"{W}x{L}"] = [round(W * L, 3), round(시그마 * 1e3, 2),
                                      round(statistics.mean(b), 4),
                                      round(statistics.pstdev(b) * 100, 2)]
    for I in (1e-6, 10e-6, 100e-6):
        _, b = 몬테카를로(2, 0.4, Iref=I, 판수=판수)
        if b:
            난것["전류"][f"{I*1e6:g}u"] = round(statistics.pstdev(b) * 100, 2)
    return 난것


if __name__ == "__main__":
    if "--자해" in sys.argv:
        v = 한판(2, 0.4, 0.0, 10e-6)
        if v is None:
            print("ngspice 가 없거나 회로가 안 돌았다", file=sys.stderr)
            raise SystemExit(2)
        비 = v / 10e-6
        print(f"불일치 0 일 때 거울비 {비:.4f} (1.0 이라야 한다)")
        raise SystemExit(0 if abs(비 - 1.0) < 0.05 else 1)
    print(json.dumps(재기(), ensure_ascii=False, indent=1))
