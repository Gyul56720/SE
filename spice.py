"""아날로그를 **실제로 돌린다.** ngspice 로 DC · AC · 트랜지언트.

사용자(2026-09-15): "아날로그 회로도 바꾸고, 아날로그 회로 설계하고."

## 왜 있나 -- 그리기만 하고 돌려 보지는 못했다

`circuitdraw.py` 가 회로도를 **그려** 줬지만 그 회로가 실제로 동작하는지는 아무도
검사하지 않았다. 디지털 쪽은 `rtl.py` 가 그 자리를 메웠는데 아날로그는 비어 있었다.
그림은 맞아 보이고 숫자는 없는 상태 -- 이 저장소가 내내 다뤄 온 그 꼴이다.

## 끝값을 믿으면 안 된다 -- 실측 2026-09-15 (ngspice 42)

| 넣은 것 | 끝값 | 실제 |
|---|---|---|
| 없는 모델 · 문법 오류 | 1 | 잡힌다 |
| 분석 줄이 없다 | 1 | 잡힌다 |
| **뜬 노드(DC 경로 없음)** | **0** | `Warning: singular matrix` · `gmin stepping failed` 셋 |
| **없는 노드를 print** | **0** | `vector nosuchnode is not available` -- **아무것도 안 찍는다** |
| **`.meas` 가 실패** | **0** | `meas ac nosuch ... failed!` |

아래 셋은 전부 **끝값 0** 이다. `vvp` 가 FAIL 에도 0 을 내던 것과 같은 병이고,
같은 처방을 쓴다 -- **출력을 읽어 판정한다.**

## 판정 낱말은 rtl.py 와 같은 것을 쓴다

    PASS  쟀고, 잰 것이 다 맞았다
    FAIL  잰 것 중 틀린 것이 있다 (`.meas ... failed!` 이거나 확인 범위 밖)
    못잼  안 돌았거나, 돌았어도 **아무것도 안 쟀다**

"돌긴 돌았다" 는 통과가 아니다. 파형을 눈으로 보는 것은 검사가 아니므로,
`.meas` 도 `확인` 도 없으면 **못잼**이다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

PASS, FAIL, 못잼 = "PASS", "FAIL", "못잼"
시한초 = 120
로그상한 = 4000          # 줄. 실측: 1p 스텝 트랜지언트가 105만 줄을 뱉었다

# --- 끝값 0 인데 사실은 안 된 것들. 위 표의 세 줄이 여기 있다. ---
_안됨 = [
    (re.compile(r"Error on line|could not find a valid modelname|Simulation interrupted",
                re.I),
     "**넷리스트에 오류가 있다**"),
    (re.compile(r"singular matrix", re.I),
     "**뜬 노드다** -- 모든 노드에 0 까지 DC 경로가 있어야 한다"),
    (re.compile(r"(gmin|source) stepping failed", re.I),
     "**DC 동작점을 못 찾았다** -- 숫자가 찍혔어도 믿으면 안 된다"),
    (re.compile(r"iteration limit reached|convergence problem|Timestep too small", re.I),
     "**수렴하지 않았다**"),
    (re.compile(r"vector\s+(\S+)\s+is not available", re.I),
     "**없는 노드를 출력했다** -- 이름을 틀렸다. 아무것도 안 찍혔다"),
    (re.compile(r"no simulations run", re.I),
     "**분석 줄이 없다** -- `.op` · `.dc` · `.ac` · `.tran` 중 하나를 넣어라"),
]
# `.meas` 결과. 성공은 `이름  =  값`, 실패는 `... failed!` 로 찍힌다(실측).
_잰것 = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*([-+0-9.eE]+)", re.M)
# `meas ... MAX` 는 `vpk = 3.77e+01 at= 1.58e+06` 처럼 **찾은 자리까지** 찍는다(실측).
# 그 자리가 곧 답인 경우가 많다(공진 주파수 · 최대 이득이 나는 주파수).
_잰것자리 = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*=\s*[-+0-9.eE]+\s+at=\s*([-+0-9.eE]+)", re.M)
_잰것실패 = re.compile(r"^\s*meas\b.*\bfailed!", re.M | re.I)
# 표로 찍히는 숫자(print · .op 노드 전압). "무엇이든 재긴 했나" 를 볼 때 쓴다.
_숫자 = re.compile(r"[-+]?\d+\.\d+e[-+]\d+", re.I)


# --- `save` 없이 스윕 안에서 `@소자[값]` 을 쓰면 **조용히 틀린 곡선**이 나온다 ---
# 실측 2026-09-15. `dc Vg ...` 안에서 `let gmid = @m1[gm]/@m1[id]` 을 썼더니 오류 없이
# 3점짜리 그럴듯한 곡선이 나왔다. 그런데 `@m1[gm]` 은 **스윕 벡터가 아니라 스칼라 한 점**
# 이었고, 그것이 스윕된 전류에 방송(broadcast)되어 값이 전부 틀렸다.
#
#     save 없이:  2.6956  2.5641  2.4390     <- 그럴듯하게 줄어드는 곡선. 전부 틀림
#     save 붙여:  2.5641  2.5000  2.4390     <- 2/Vov 와 네 자리까지 일치
#
# 곡선이 단조롭게 내려가 보여서 눈으로는 절대 못 잡는다. 그래서 여기서 막는다.
_소자값 = re.compile(r"@\w+\[\w+\]")
_스윕 = re.compile(r"^\s*(dc|ac|tran|noise)\s+\S", re.M | re.I)
_저장 = re.compile(r"^\s*save\b", re.M | re.I)


def 저장빠짐(netlist: str) -> "list[str]":
    """스윕 뒤에서 `save` 없이 쓰인 `@소자[값]` 들. 없으면 빈 목록."""
    글 = netlist or ""
    m = _스윕.search(글)
    if not m:
        return []                      # 스윕이 없으면 `op` 의 스칼라라 맞다
    뒤 = 글[m.start():]
    # **`alter`·`save`·`show` 줄은 읽기가 아니다.** `alter @Vid[acmag] = 0` 은 값을
    # 바꾸는 것이라 벡터가 될 일이 없는데, 처음엔 이것까지 걸어 **거짓 못잼**을 냈다.
    읽는줄 = [l for l in 뒤.splitlines()
            if not re.match(r"\s*(alter\w*|save|show|setplot|destroy)\b", l, re.I)]
    쓴것 = set(_소자값.findall("\n".join(읽는줄)))
    if not 쓴것:
        return []
    저장된 = " ".join(l for l in 글.splitlines() if _저장.match(l))
    if "all" in 저장된.split() and 저장된.count("@") == 0:
        저장된 = ""                     # `save all` 만으로는 소자값이 안 담긴다(실측)
    return sorted(x for x in 쓴것 if x not in 저장된)


def 있나() -> bool:
    return shutil.which("ngspice") is not None


def _자르기(글: str) -> str:
    줄 = (글 or "").splitlines()
    if len(줄) <= 로그상한:
        return "\n".join(줄)
    반 = 로그상한 // 2
    return "\n".join(줄[:반] + [f"... ({len(줄) - 로그상한}줄 줄임) ..."] + 줄[-반:])


def 잰것뽑기(로그: str) -> "dict[str, float]":
    """`.meas` 가 찍은 `이름 = 값` 을 모은다."""
    나온것 = {}
    # `fourier`/`.four` 는 `이름 = 값` 이 아니라 `THD: 2.55333 %` 로 찍는다(실측).
    # 그래도 그것은 **잰 값**이다 -- 안 담으면 왜곡 본보기가 "아무것도 안 쟀다" 가 된다.
    m = re.search(r"THD:\s*([-+0-9.eE]+)\s*%", 로그 or "")
    if m:
        try:
            나온것["thd_pct"] = float(m.group(1))
        except ValueError:
            pass
    for 무늬, 꼬리 in ((_잰것, ""), (_잰것자리, "_at")):
        for 이름, 값 in 무늬.findall(로그 or ""):
            try:
                나온것[이름 + 꼬리] = float(값)
            except ValueError:
                pass
    return 나온것


def 확인읽기(글) -> "list[tuple[str, float, float]]":
    """`이름 하한 상한` 줄들을 읽는다. 잘못된 줄은 조용히 버리지 않고 그냥 건너뛴다."""
    if not 글:
        return []
    if isinstance(글, (list, tuple)):
        return [tuple(x) for x in 글]
    나온것 = []
    for 줄 in str(글).splitlines():
        조각 = 줄.replace(",", " ").split()
        if len(조각) != 3:
            continue
        try:
            나온것.append((조각[0], float(조각[1]), float(조각[2])))
        except ValueError:
            continue
    return 나온것


def 판정하기(로그: str, 확인=None) -> "tuple[str, str, dict]":
    """출력만 보고 (판정, 까닭, 잰것). **끝값을 안 본다** -- 머리말의 까닭이다."""
    로그 = 로그 or ""
    for 무늬, 까닭 in _안됨:
        m = 무늬.search(로그)
        if m:
            return 못잼, f"{까닭} (`{m.group(0)}`)", {}
    잰것 = 잰것뽑기(로그)
    if _잰것실패.search(로그):
        return FAIL, "`.meas` 중 실패한 것이 있다 -- 로그의 `failed!` 줄을 봐라", 잰것
    if not _숫자.search(로그):
        return 못잼, "**숫자가 하나도 안 찍혔다** -- 돌긴 돌았다는 것은 통과가 아니다", 잰것

    범위들 = 확인읽기(확인)
    틀린것 = []
    for 이름, 아래, 위 in 범위들:
        if 이름 not in 잰것:
            return 못잼, (f"확인하려는 `{이름}` 을 **안 쟀다** -- `.meas` 로 그 이름을 "
                        f"재야 한다. 잰 것: {', '.join(잰것) or '없음'}"), 잰것
        v = 잰것[이름]
        if not (아래 <= v <= 위):
            틀린것.append(f"{이름}={v:.6g} (바란 것 {아래:.6g}~{위:.6g})")
    if 틀린것:
        return FAIL, "범위를 벗어났다: " + " · ".join(틀린것), 잰것
    if 범위들:
        return PASS, f"확인 {len(범위들)}건이 다 맞았다", 잰것
    if 잰것:
        return PASS, f"`.meas` {len(잰것)}건이 다 났다", 잰것
    return 못잼, ("돌긴 돌았는데 **아무것도 재지 않았다** -- `.meas` 를 넣거나 `확인` 을 "
                "줘라. 파형을 눈으로 보는 것은 검사가 아니다"), 잰것


def 돌리기(netlist: str, 확인=None, 초: int = None) -> dict:
    """넷리스트를 돌린다. {판정, 끝값, 로그, 잰것, 왜}."""
    if not 있나():
        return {"판정": 못잼, "끝값": -1, "로그": "", "잰것": {},
                "왜": "ngspice 가 없다 -- `apt-get install -y ngspice`"}
    if not (netlist or "").strip():
        return {"판정": 못잼, "끝값": -1, "로그": "", "잰것": {}, "왜": "넷리스트가 비었다"}
    빠진 = 저장빠짐(netlist)
    if 빠진:
        return {"판정": 못잼, "끝값": -1, "로그": "", "잰것": {},
                "왜": ("**`save` 없이 스윕 안에서 " + " · ".join(빠진[:4]) + " 를 쓴다** -- "
                      "그러면 ngspice 가 오류 없이 **틀린 곡선**을 낸다(스칼라 한 점이 "
                      "스윕 벡터에 방송된다). 스윕 앞에 `save " + " ".join(빠진[:4]) +
                      "` 를 넣어라")}
    글 = netlist
    if not re.search(r"^\s*\.end\s*$", 글, re.M | re.I):
        글 = 글.rstrip() + "\n.end\n"
    판 = tempfile.mkdtemp(prefix="spice-")
    쪽 = os.path.join(판, "run.cir")
    with open(쪽, "w", encoding="utf-8") as f:
        f.write(글)
    나온쪽 = os.path.join(판, "run.log")
    try:
        with open(나온쪽, "w", encoding="utf-8") as 나옴:
            r = subprocess.run(["ngspice", "-b", "run.cir"], cwd=판,
                               stdout=나옴, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, timeout=초 or 시한초)
        끝값 = r.returncode
    except subprocess.TimeoutExpired:
        return {"판정": 못잼, "끝값": 124, "로그": "", "잰것": {},
                "왜": f"{초 or 시한초}초 안에 안 끝났다 -- 스텝이 너무 잘거나 수렴을 못 한다"}
    except OSError as e:
        return {"판정": 못잼, "끝값": 127, "로그": "", "잰것": {},
                "왜": f"{type(e).__name__}: {e}"}
    with open(나온쪽, encoding="utf-8", errors="replace") as f:
        로그 = f.read()
    판정, 왜, 잰것 = 판정하기(로그, 확인)
    # 끝값은 **보태기만 한다.** 0 이라고 통과로 올리는 일은 없다.
    if 끝값 != 0 and 판정 == PASS:
        판정, 왜 = 못잼, f"ngspice 가 끝값 {끝값} 을 냈다"
    return {"판정": 판정, "끝값": 끝값, "로그": _자르기(로그), "잰것": 잰것, "왜": 왜}


# ---------------------------------------------------------------------------
# 본보기 -- 전부 **여기서 돌려 보고** 넣었다(2026-09-15, ngspice 42).
#
# MOS 는 LEVEL=1 을 쓴다. 낡은 모델이라서가 아니라 **그것이 교과서의 제곱법칙 자체**이고,
# 사용자가 물은 변수들(Vth · K' · W/L · lambda)이 모델 카드에 그 이름 그대로 있어서다.
#   Id = (KP/2)(W/L)(Vgs-VTO)^2 (1 + LAMBDA*Vds)     <- 포화
# BSIM 은 PDK 가 있어야 하고, 여기 목적은 원리를 보이는 것이다.
# ---------------------------------------------------------------------------

# **첫 줄은 제목으로 먹힌다.** 주석 한 줄이 없으면 `.model nch` 가 통째로
# 사라지고 "could not find a valid modelname" 이 난다(실측 2026-09-15).
_모델 = """\
* generic 0.18um-ish square-law models (LEVEL=1)
.model nch NMOS (LEVEL=1 VTO=0.5 KP=200u GAMMA=0.4 PHI=0.7 LAMBDA=0.05
+                CGSO=0.3n CGDO=0.3n CJ=1m)
.model pch PMOS (LEVEL=1 VTO=-0.5 KP=80u GAMMA=0.4 PHI=0.7 LAMBDA=0.08
+                CGSO=0.3n CGDO=0.3n CJ=1m)
"""

본보기: "dict[str, str]" = {}

본보기["rc_lowpass"] = """\
* RC low-pass -- the -3dB corner is 1/(2*pi*R*C)
V1 in 0 DC 0 AC 1 PULSE(0 1 0 1n 1n 10u 20u)
R1 in out 1k
C1 out 0 1n
.control
ac dec 50 10 100Meg
meas ac f3db WHEN vdb(out)=-3
tran 10n 5u
meas tran tau FIND v(out) AT=1u
.endc
"""

본보기["mosfet_iv"] = _모델 + """\
* NMOS output family Id-Vds -- saturation, and the slope that IS channel-length
* modulation. lambda = (1/Id) * dId/dVds in saturation.
Vd d 0 DC 1.8
Vg g 0 DC 1.0
M1 d g 0 0 nch W=10u L=1u
.control
dc Vd 0 1.8 0.01 Vg 0.6 1.8 0.3
meas dc id_lo FIND i(Vd) AT=0.9
meas dc id_hi FIND i(Vd) AT=1.8
let lambda_est = (id_hi-id_lo)/(id_lo*0.9)
print lambda_est
.endc
"""

본보기["nmos_vth"] = _모델 + """\
* Extract Vth: sqrt(Id) vs Vgs is a straight line in saturation; its x-intercept
* is VTO. Here we just find where Id crosses a small current.
Vd d 0 DC 1.8
Vg g 0 DC 0
M1 d g 0 0 nch W=10u L=1u
.control
dc Vg 0 1.8 0.005
meas dc vth_c WHEN i(Vd)=-1u
meas dc id_max FIND i(Vd) AT=1.79
.endc
"""

본보기["current_mirror"] = _모델 + """\
* NMOS current mirror. The copy is NOT exact: Id depends on Vds through lambda,
* so the output current tilts with the output voltage. That tilt is 1/ro.
Vdd vdd 0 DC 1.8
Iref vdd ref DC 50u
Vout vdd out DC 0.9
M1 ref ref 0 0 nch W=10u L=1u
M2 out ref 0 0 nch W=10u L=1u
.control
dc Vout 0 1.7 0.01
meas dc iout_sat FIND i(Vout) AT=0.9
meas dc iout_hi  FIND i(Vout) AT=1.5
.endc
"""

본보기["common_source"] = _모델 + """\
* Common-source amplifier with a resistive load.
* Av = -gm*(RD||ro). Run .op first, then .ac for the real gain.
Vdd vdd 0 DC 1.8
Vin in 0 DC 0.9 AC 1
RD vdd out 20k
M1 out in 0 0 nch W=3u L=1u
CL out 0 1p
.control
op
print v(out) @m1[gm] @m1[gds] @m1[id]
ac dec 50 1 10G
meas ac av_db FIND vdb(out) AT=1k
let t3 = av_db-3
meas ac f3db WHEN vdb(out)=t3 FALL=1
.endc
"""

본보기["cmos_inverter_vtc"] = _모델 + """\
* CMOS inverter DC transfer curve. The switching threshold Vm is where Vin=Vout;
* it moves with the beta ratio (Wp/Lp)/(Wn/Ln).
Vdd vdd 0 DC 1.8
Vin in 0 DC 0
M1 out in 0 0 nch W=2u L=0.5u
M2 out in vdd vdd pch W=5u L=0.5u
.control
dc Vin 0 1.8 0.005
meas dc vm WHEN v(out)=v(in)
meas dc voh FIND v(out) AT=0
meas dc vol FIND v(out) AT=1.79
.endc
"""

본보기["diff_pair"] = _모델 + """\
* NMOS differential pair with a tail current source and resistive loads.
* Differential gain Ad = -gm*RD. Sweep to see the tanh-like transfer.
Vdd vdd 0 DC 1.8
Vcm cm 0 DC 0.9
Vid id 0 DC 0 AC 1
Eip ip 0 VALUE={V(cm)+V(id)/2}
Ein in 0 VALUE={V(cm)-V(id)/2}
RD1 vdd op 20k
RD2 vdd om 20k
M1 op ip tail 0 nch W=20u L=1u
M2 om in tail 0 nch W=20u L=1u
Itail tail 0 DC 100u
.control
op
print v(op) v(om) @m1[gm]
ac dec 50 1 1G
let adiff = v(op)-v(om)
meas ac ad_db FIND vdb(adiff) AT=1k
.endc
"""

본보기["rlc_resonance"] = """\
* Series RLC -- resonance at f0 = 1/(2*pi*sqrt(L*C)), sharpness Q = (1/R)*sqrt(L/C).
V1 in 0 DC 0 AC 1
R1 in a 10
L1 a b 100u
C1 b 0 100p
.control
ac dec 2000 1Meg 3Meg
meas ac vpk MAX vdb(b)
let t3 = vpk-3
meas ac fhi WHEN vdb(b)=t3 FALL=1
.endc
"""

# ---------------------------------------------------------------------------
# 2차 -- 학부·석사 과정의 표준 회로들. **전부 손계산과 대조하고 넣었다**(2026-09-15).
# 대조는 `tests/test_spice.py` 가 매번 다시 한다.
# ---------------------------------------------------------------------------

본보기["cascode"] = _모델 + """\
* Cascode. The top device multiplies the output resistance by its own gm*ro, so Rout
* jumps from ro (a few hundred kohm) to tens of megohm. That is where gain comes from
* once you have run out of current. The price is one Vov of output swing.
Vdd vdd 0 DC 1.8
Vin in 0 DC 0.75
Vb  b  0 DC 1.3
Vout out 0 DC 1.2
M1 mid in  0   0 nch W=10u L=1u
M2 out b   mid 0 nch W=10u L=1u
.control
op
print @m1[id] @m1[gm] @m1[gds] @m2[gm] @m2[gds]
dc Vout 0.9 1.7 0.01
meas dc i_lo FIND i(Vout) AT=1.0
meas dc i_hi FIND i(Vout) AT=1.6
let rout = 0.6/(i_hi-i_lo)
print rout
.endc
"""

본보기["cascode_mirror"] = _모델 + """\
* Cascode current mirror. The copy is flat against output voltage because Rout is now
* ~gm*ro^2 instead of ro -- about 200x better than the plain mirror.
* Vb must sit at TWO gate-source drops. Set it too low and the upper device starves in
* triode and the mirror quietly copies the wrong current (measured: 15.8uA for 50uA).
Vdd vdd 0 DC 1.8
Iref vdd ref DC 50u
Vout vdd out DC 0.9
Vb b 0 DC 1.45
M1 r1  r1 0  0 nch W=10u L=1u
M2 ref b  r1 0 nch W=10u L=1u
M3 m1  r1 0  0 nch W=10u L=1u
M4 out b  m1 0 nch W=10u L=1u
.control
dc Vout 0 1.2 0.01
meas dc i_lo FIND i(Vout) AT=0.3
meas dc i_hi FIND i(Vout) AT=0.9
let rout_casc = 0.6/(i_hi-i_lo)
print rout_casc
.endc
"""

본보기["source_follower"] = _모델 + """\
* Source follower (common drain). Gain is below one and the body effect is why:
*   Av = gm/(gm+gmb+gds)
* What you buy is a low output resistance ~1/gm for driving a heavy load.
Vdd vdd 0 DC 1.8
Vin in 0 DC 1.2 AC 1
M1 vdd in out 0 nch W=20u L=1u
Ibias out 0 DC 100u
.control
op
print v(out) @m1[gm] @m1[gmbs] @m1[gds] @m1[id]
ac dec 20 1 1Meg
meas ac av_db FIND vdb(out) AT=1k
.endc
"""

본보기["common_gate"] = _모델 + """\
* Common gate. Input resistance is low (1/(gm+gmb)) and the gain is non-inverting:
*   Av = (gm+gmb)*(RD||ro)
* This is the upper half of a cascode, and the input stage of a current-mode receiver.
Vdd vdd 0 DC 1.8
Vb  b  0 DC 1.2
Vs  s  0 DC 0.4 AC 1
RD vdd out 20k
M1 out b s 0 nch W=10u L=1u
.control
op
print v(out) @m1[gm] @m1[gmbs] @m1[gds] @m1[id]
ac dec 20 1 10Meg
meas ac av_db FIND vdb(out) AT=1k
.endc
"""

본보기["body_effect"] = _모델 + """\
* Body effect. Two identical devices, one with Vsb=0 and one with Vsb=0.5. At the same
* drain current their gate voltages differ by exactly the threshold shift:
*   dVth = GAMMA*(sqrt(PHI+Vsb) - sqrt(PHI))
* Note SPICE's PHI *is* 2*phi_F, so with GAMMA=0.4 and PHI=0.7 this is 0.1035 V.
Vg  g  0 DC 0
Vd1 d1 0 DC 1.8
Vd2 d2 0 DC 1.8
Vs2 s2 0 DC 0.5
M1 d1 g 0  0 nch W=10u L=1u
M2 d2 g s2 0 nch W=10u L=1u
.control
dc Vg 0 1.8 0.002
meas dc vg1 WHEN i(Vd1)=-10u
meas dc vg2 WHEN i(Vd2)=-10u
let dvth = vg2-vg1-0.5
print dvth
.endc
"""

본보기["miller"] = _모델 + """\
* Miller effect, measured directly as INPUT CAPACITANCE rather than argued about.
* Two identical devices: M1 has a real load so it has gain, M2's drain is held by an
* ideal source so it has none. The gate current at 1 MHz gives Cin for each:
*   with gain   Cin = Cgs + Cgd(1+|Av|)
*   without     Cin = Cgs + Cgd
Vdd vdd 0 DC 1.8
V1 g1 0 DC 0.6225 AC 1
V2 g2 0 DC 0.6225 AC 1
RD vdd o1 20k
Vd2 o2 0 DC 0.9
M1 o1 g1 0 0 nch W=30u L=1u
M2 o2 g2 0 0 nch W=30u L=1u
.control
op
print v(o1) @m1[id] @m1[gm]
ac lin 1 1Meg 1Meg
let cin_gain = mag(i(V1))/(2*PI*1e6)
let cin_flat = mag(i(V2))/(2*PI*1e6)
let miller_ratio = cin_gain/cin_flat
print cin_gain cin_flat miller_ratio
ac dec 50 1k 1G
meas ac av_db FIND vdb(o1) AT=10k
.endc
"""

본보기["gm_id"] = _모델 + """\
* gm/ID -- the one knob that trades gain against speed. Square law gives gm/ID = 2/Vov,
* so a small overdrive buys transconductance per amp (gain, low power) and a large one
* buys fT. The intrinsic gain gm/gds follows the same trade in reverse.
* **`save` is not optional here.** Without it ngspice returns a plausible but WRONG
* curve: @m1[gm] stays a scalar and gets broadcast over the swept current.
Vd d 0 DC 1.2
Vg g 0 DC 0.7
M1 d g 0 0 nch W=10u L=1u
.control
save all @m1[gm] @m1[id] @m1[gds]
dc Vg 0.55 1.5 0.005
let gm_id = @m1[gm]/@m1[id]
let gain = @m1[gm]/@m1[gds]
meas dc gmid_vov100m FIND gm_id AT=0.6
meas dc gmid_vov400m FIND gm_id AT=0.9
meas dc gmid_vov800m FIND gm_id AT=1.3
meas dc gain_vov100m FIND gain AT=0.6
meas dc gain_vov800m FIND gain AT=1.3
.endc
"""

본보기["cmrr"] = _모델 + """\
* CMRR. Differential gain is gm*RD; common-mode gain is set by how good the tail is,
* Acm ~ -RD/(2*r_tail). A plain tail MOSFET has finite ro, so CMRR is finite -- which
* is exactly why a serious design cascodes the tail. Measured in two AC runs;
* CMRR(dB) = ad_db - acm_db.
Vdd vdd 0 DC 1.8
Vcm cm 0 DC 0.9
Vid id 0 DC 0 AC 1
Vic ic 0 DC 0 AC 0
Eip ip 0 VALUE={V(cm)+V(id)/2+V(ic)}
Ein in 0 VALUE={V(cm)-V(id)/2+V(ic)}
RD1 vdd op 20k
RD2 vdd om 20k
M1 op ip tail 0 nch W=20u L=1u
M2 om in tail 0 nch W=20u L=1u
Vbt bt 0 DC 0.75
M3 tail bt 0 0 nch W=20u L=2u
.control
op
print @m1[gm] @m3[id] @m3[gds]
ac dec 20 1 1Meg
let adiff = v(op)-v(om)
meas ac ad_db FIND vdb(adiff) AT=1k
alter @Vid[acmag] = 0
alter @Vic[acmag] = 1
ac dec 20 1 1Meg
meas ac acm_db FIND vdb(op) AT=1k
.endc
"""

본보기["inverter_delay"] = _모델 + """\
* Propagation delay is LINEAR in load: tp = t_intrinsic + 0.69*Req*CL. Two identical
* inverters with 10 fF and 40 fF show the slope and the intercept -- that intercept is
* the self-load, and it is why fan-out curves do not pass through the origin.
Vdd vdd 0 DC 1.8
Vin in 0 PULSE(0 1.8 1n 50p 50p 5n 10n)
M1 o1 in 0   0   nch W=2u L=0.5u
M2 o1 in vdd vdd pch W=5u L=0.5u
M3 o2 in 0   0   nch W=2u L=0.5u
M4 o2 in vdd vdd pch W=5u L=0.5u
C1 o1 0 10f
C2 o2 0 40f
.control
tran 5p 12n
meas tran tphl_10f TRIG v(in) VAL=0.9 RISE=1 TARG v(o1) VAL=0.9 FALL=1
meas tran tplh_10f TRIG v(in) VAL=0.9 FALL=1 TARG v(o1) VAL=0.9 RISE=1
meas tran tphl_40f TRIG v(in) VAL=0.9 RISE=1 TARG v(o2) VAL=0.9 FALL=1
meas tran tplh_40f TRIG v(in) VAL=0.9 FALL=1 TARG v(o2) VAL=0.9 RISE=1
.endc
"""

본보기["inverter_power"] = _모델 + """\
* Dynamic power. Each full cycle moves CL*VDD of charge out of the supply, so
*   P = CL * VDD^2 * f
* independent of how fast the devices are. The measured number lands a few percent
* ABOVE that -- the excess is short-circuit current while both devices are on.
Vdd vdd 0 DC 1.8
Vin in 0 PULSE(0 1.8 0 50p 50p 4.95n 10n)
M1 out in 0   0   nch W=2u L=0.5u
M2 out in vdd vdd pch W=5u L=0.5u
CL out 0 100f
.control
tran 2p 100n
meas tran iavg AVG i(Vdd) FROM=10n TO=100n
let pdyn = -iavg*1.8
print pdyn
.endc
"""

본보기["transmission_gate"] = _모델 + """\
* Transmission gate. An NMOS alone dies near VDD (a threshold drop) and a PMOS alone
* dies near ground; in parallel the on-resistance stays within about 2.5x across the
* whole input range. Measured as a divider against a 100k load.
Vdd vdd 0 DC 1.8
Vc  c  0 DC 1.8
Vcb cb 0 DC 0
Vin in 0 DC 0
MN out c  in 0   nch W=4u L=0.5u
MP out cb in vdd pch W=8u L=0.5u
RL out 0 100k
.control
dc Vin 0.05 1.75 0.01
let ron = (v(in)-v(out))/(v(out)/100k)
meas dc ron_lo  FIND ron AT=0.2
meas dc ron_mid FIND ron AT=0.9
meas dc ron_hi  FIND ron AT=1.6
.endc
"""

본보기["elmore"] = """\
* Wire delay grows as the SQUARE of length. Four INDEPENDENT ladders of 1, 2, 4 and 8
* equal RC segments, all driven from the same step. Doubling the length more than
* TRIPLES the delay -- a linear model would say 2x. That gap is why long wires get
* repeaters, which cut L^2 back to L.
Vin in 0 PULSE(0 1 0 1p 1p 100n 200n)
Ra1 in a1 1k
Ca1 a1 0 1p
Rb1 in b1 1k
Cb1 b1 0 1p
Rb2 b1 b2 1k
Cb2 b2 0 1p
Rc1 in c1 1k
Cc1 c1 0 1p
Rc2 c1 c2 1k
Cc2 c2 0 1p
Rc3 c2 c3 1k
Cc3 c3 0 1p
Rc4 c3 c4 1k
Cc4 c4 0 1p
Rd1 in d1 1k
Cd1 d1 0 1p
Rd2 d1 d2 1k
Cd2 d2 0 1p
Rd3 d2 d3 1k
Cd3 d3 0 1p
Rd4 d3 d4 1k
Cd4 d4 0 1p
Rd5 d4 d5 1k
Cd5 d5 0 1p
Rd6 d5 d6 1k
Cd6 d6 0 1p
Rd7 d6 d7 1k
Cd7 d7 0 1p
Rd8 d7 d8 1k
Cd8 d8 0 1p
.control
tran 20p 150n
meas tran t_len1 TRIG v(in) VAL=0.5 RISE=1 TARG v(a1) VAL=0.5 RISE=1
meas tran t_len2 TRIG v(in) VAL=0.5 RISE=1 TARG v(b2) VAL=0.5 RISE=1
meas tran t_len4 TRIG v(in) VAL=0.5 RISE=1 TARG v(c4) VAL=0.5 RISE=1
meas tran t_len8 TRIG v(in) VAL=0.5 RISE=1 TARG v(d8) VAL=0.5 RISE=1
.endc
"""

본보기["sram_read_disturb"] = _모델 + """\
* 6T SRAM read disturb. The cell holds 0 on QL. During a read the access device pulls
* QL up from the precharged bitline while the driver pulls it down -- a divider set by
* the CELL RATIO (driver W/L over access W/L, here 2). If QL climbs past the other
* inverter's trip point the cell flips and the data is gone. Shrink the ratio and watch
* v_disturb climb.
* The cell needs an initial state, and measurement (2026-09-15) says EITHER `.ic` or
* `uic` alone is enough -- they give bit-identical results here. Drop BOTH and the cell
* settles the other way round (QL=1.8, QR=0) and every number below describes the mirror
* image. A plain `op` with no transient parks both nodes at the metastable point
* (measured: both sat at 0.796 V) and the cell holds nothing at all.
Vdd vdd 0 DC 1.8
Vwl wl 0 PULSE(0 1.8 2n 100p 100p 6n 20n)
Vbl bl 0 DC 1.8
Vblb blb 0 DC 1.8
MNL ql qr 0   0   nch W=4u L=0.5u
MPL ql qr vdd vdd pch W=1u L=0.5u
MNR qr ql 0   0   nch W=4u L=0.5u
MPR qr ql vdd vdd pch W=1u L=0.5u
MAL ql wl bl  0 nch W=2u L=0.5u
MAR qr wl blb 0 nch W=2u L=0.5u
CL ql 0 1f
CR qr 0 1f
.ic v(ql)=0 v(qr)=1.8
.control
tran 10p 10n uic
meas tran v_hold FIND v(ql) AT=1.5n
meas tran v_disturb MAX v(ql) FROM=3n TO=7n
meas tran v_high FIND v(qr) AT=6n
.endc
"""


# ---------------------------------------------------------------------------
# 3차 -- 연산증폭기와 디지털 회로의 나머지. 역시 전부 손계산과 대조하고 넣었다.
# ---------------------------------------------------------------------------

본보기["twostage_ota"] = _모델 + """\
* Two-stage Miller-compensated OTA, measured OPEN LOOP with the standard SPICE trick:
* a 1 TH inductor closes the loop at DC (so the bias finds itself) and is an open at AC,
* while a 1 TF capacitor feeds the AC input in. No hand-tuned output bias needed.
* Cc splits the poles -- the first drops to 1/(gm6*ro6*ro1*Cc), the second climbs to
* gm6/CL -- so the loop looks single-pole out to wu = gm1/Cc.
* Watch the feedback POLARITY: wire it to the wrong input and the loop latches to a
* rail (measured: v(out) sat at 0.05 V and the gain read -29 dB).
Vdd vdd 0 DC 1.8
Vcm cm 0 DC 0.8
Vin in 0 DC 0 AC 1
Lfb out ip 1T
Cfb ip 0 1T
Cac in im 1T
Rcm cm im 1T
M1 n1 ip tail vdd pch W=40u L=1u
M2 n2 im tail vdd pch W=40u L=1u
M3 n1 n1 0 0 nch W=10u L=1u
M4 n2 n1 0 0 nch W=10u L=1u
Vbp bp 0 DC 0.95
M5 tail bp vdd vdd pch W=80u L=1u
M6 out n2 0 0 nch W=40u L=1u
Mb1 nb nb vdd vdd pch W=80u L=1u
Ib nb 0 DC 200u
M7 out nb vdd vdd pch W=160u L=1u
Cc n2 out 1p
CL out 0 2p
.control
op
print v(n2) v(out) @m1[gm] @m6[gm] @m1[id] @m6[id]
ac dec 30 0.1 1G
meas ac a0_db FIND vdb(out) AT=1
meas ac ugb WHEN vdb(out)=0 FALL=1
.endc
"""

본보기["slew_rate"] = _모델 + """\
* Slew rate. A step too big for the tail current makes the output RAMP instead of
* following the small-signal bandwidth. The classic formula is SR = I_tail/Cc, but here
* the second stage must charge CL as well, so the measured slope lands on I/(Cc+CL).
* Unity-gain buffer, 0.4 V step.
Vdd vdd 0 DC 1.8
Vin in 0 PULSE(0.6 1.0 100n 100p 100p 900n 2u)
M1 n1 out tail vdd pch W=40u L=1u
M2 n2 in  tail vdd pch W=40u L=1u
M3 n1 n1 0 0 nch W=10u L=1u
M4 n2 n1 0 0 nch W=10u L=1u
Vbp bp 0 DC 0.95
M5 tail bp vdd vdd pch W=80u L=1u
M6 out n2 0 0 nch W=40u L=1u
Mb1 nb nb vdd vdd pch W=80u L=1u
Ib nb 0 DC 200u
M7 out nb vdd vdd pch W=160u L=1u
Cc n2 out 1p
CL out 0 2p
.control
op
print v(out) @m5[id]
tran 200p 500n
meas tran t10 WHEN v(out)=0.65 RISE=1
meas tran t90 WHEN v(out)=0.95 RISE=1
let sr = 0.30/(t90-t10)
print sr
.endc
"""

본보기["distortion"] = _모델 + """\
* Distortion. A square-law common-source stage turns a sine into a sine plus a SECOND
* harmonic: for I ~ (Vov + A sin)^2 the second-order term gives HD2 = A/(4*Vov).
* A differential pair cancels the even orders, which is why analog front ends are
* differential and why HD3 is the one left to fight.
Vdd vdd 0 DC 1.8
Vin in 0 DC 0.9 SIN(0.9 0.05 1Meg)
RD vdd out 20k
M1 out in 0 0 nch W=3u L=1u
.control
tran 5n 20u
fourier 1Meg v(out)
.endc
"""

본보기["flicker_noise"] = """\
* Flicker (1/f) noise and its corner, measured as a BAND RATIO so it does not lean on
* the absolute KF. Two noise runs over the same circuit: one decade down low where 1/f
* rules, one decade up high where the thermal floor rules. The two totals come out
* nearly EQUAL even though the high band is a million times wider -- that is the 1/f
* law. Flicker goes as 1/(W*L), so the corner is pushed down with AREA, not current.
.model nchf NMOS (LEVEL=1 VTO=0.5 KP=200u LAMBDA=0.05 TOX=4n KF=1e-27 AF=1)
Vdd vdd 0 DC 1.8
Vin in 0 DC 0.9 AC 1
RD vdd out 20k
M1 out in 0 0 nchf W=3u L=1u
.control
noise v(out) Vin dec 40 1 10
let n_low_band = onoise_total
print n_low_band
noise v(out) Vin dec 40 1Meg 10Meg
let n_high_band = onoise_total
print n_high_band
.endc
"""

본보기["noise_margins"] = _모델 + """\
* Noise margins. VIL and VIH are the two points where the inverter's slope is exactly
* -1; the margins are NMH = VOH-VIH and NML = VIL-VOL. Inside them a disturbed input
* still gets restored, which is the whole reason digital logic is robust at all.
Vdd vdd 0 DC 1.8
Vin in 0 DC 0
M1 out in 0   0   nch W=2u L=0.5u
M2 out in vdd vdd pch W=5u L=0.5u
.control
dc Vin 0 1.8 0.002
let slope = deriv(v(out))
meas dc vil WHEN slope=-1 FALL=1
meas dc vih WHEN slope=-1 RISE=1
meas dc voh FIND v(out) AT=0.1
meas dc vol FIND v(out) AT=1.7
meas dc vm WHEN v(out)=v(in)
.endc
"""

본보기["nand_stack"] = _모델 + """\
* Stacking. A NAND2 puts two NMOS in series, so to match an inverter's pull-down each
* must be TWICE as wide. Here the NAND is built with the SAME width as the inverter --
* the series stack then shows up directly as a roughly 2x slower falling edge.
Vdd vdd 0 DC 1.8
Va a 0 DC 1.8
Vin in 0 PULSE(0 1.8 1n 50p 50p 5n 10n)
MI1 oi in 0   0   nch W=2u L=0.5u
MI2 oi in vdd vdd pch W=5u L=0.5u
CI oi 0 20f
MN1 on in  mid 0   nch W=2u L=0.5u
MN2 mid a  0   0   nch W=2u L=0.5u
MP1 on in  vdd vdd pch W=5u L=0.5u
MP2 on a   vdd vdd pch W=5u L=0.5u
CN on 0 20f
.control
tran 5p 12n
meas tran t_inv  TRIG v(in) VAL=0.9 RISE=1 TARG v(oi) VAL=0.9 FALL=1
meas tran t_nand TRIG v(in) VAL=0.9 RISE=1 TARG v(on) VAL=0.9 FALL=1
.endc
"""

본보기["charge_sharing"] = _모델 + """\
* Charge sharing in dynamic logic. The output is precharged high. When the clock
* evaluates and only the TOP input goes high, charge on CL redistributes onto the
* internal node X even though the path never reaches ground. Sharing stops when the
* pass device turns off, so the settled value is NOT the ideal divider but
*   CL*VDD = CL*Vout + Cx*(Vout - Vth)
* which for CL=20f, Cx=10f, Vth~0.6 gives 1.40 V (measured 1.46 V with body effect).
* That droop is why dynamic gates carry a keeper.
Vdd vdd 0 DC 1.8
Vclk clk 0 PULSE(0 1.8 2n 100p 100p 8n 20n)
Va a 0 PULSE(0 1.8 3n 100p 100p 6n 20n)
Vb b 0 DC 0
MP out clk vdd vdd pch W=4u L=0.5u
MA out a  x  0 nch W=4u L=0.5u
MB x   b  y  0 nch W=4u L=0.5u
ME y   clk 0  0 nch W=4u L=0.5u
CL out 0 20f
CX x 0 10f
.ic v(x)=0
.control
tran 10p 14n
meas tran v_pre FIND v(out) AT=1.9n
meas tran v_after MIN v(out) FROM=4n TO=8n
let droop = v_pre-v_after
print droop
.endc
"""


영어이름 = {
    "rc": "rc_lowpass", "lowpass": "rc_lowpass",
    "iv": "mosfet_iv", "output_family": "mosfet_iv", "clm": "mosfet_iv",
    "channel_length_modulation": "mosfet_iv", "lambda": "mosfet_iv",
    "vth": "nmos_vth", "threshold": "nmos_vth",
    "mirror": "current_mirror", "cm": "current_mirror",
    "cs": "common_source", "amp": "common_source", "gain": "common_source",
    "inverter": "cmos_inverter_vtc", "vtc": "cmos_inverter_vtc",
    "diff": "diff_pair", "differential": "diff_pair", "diffpair": "diff_pair",
    "rlc": "rlc_resonance", "resonance": "rlc_resonance", "q": "rlc_resonance",
}


def 본보기찾기(이름: str) -> str:
    """이름으로 본보기 넷리스트를 꺼낸다. 없으면 빈 문자열."""
    키 = (이름 or "").strip().lower().replace("-", "_").replace(" ", "_")
    키 = 영어이름.get(키, 키)
    return 본보기.get(키, "")


# ---------------------------------------------------------------------------
# 몬테카를로 -- 공정 산포. **흩어졌는지 세어서 말한다.**
#
# ngspice 안에서 `alterparam vtn = agauss(...)` 로 흔들려 했더니 42 에서
# `Formula() error` 로 죽었다(실측 2026-09-15). 그래서 **파이썬에서 뽑아** 넷리스트의
# `.param` 값을 바꿔 끼운다. 그 편이 나은 까닭이 하나 더 있다 --
#
#   **흔들었다고 믿는 것과 실제로 흔들린 것은 다르다.**
#
# 이름을 틀리거나 `.param` 이 없으면 바꿔 끼우기가 조용히 아무것도 안 하고, 같은 판을
# N 번 돌린 뒤 "30판 다 통과, 수율 100%" 가 나온다. 그것이 여기서 제일 큰 거짓 초록이다.
# 그래서 **바꿔 끼운 자리 수를 세고, 결과가 실제로 흩어졌는지도 센다.**
# ---------------------------------------------------------------------------

import random as _random
import math as _math
import statistics as _stat

_파람 = r"^([ \t]*\.param[ \t]+{이름}[ \t]*=[ \t]*)([^\s;$]+)"


def 산포읽기(글) -> "list[tuple[str, float]]":
    """`이름 시그마` 줄들. 시그마는 **절대값**이다(상대가 아니다)."""
    if not 글:
        return []
    if isinstance(글, dict):
        return [(k, float(v)) for k, v in 글.items()]
    나온것 = []
    for 줄 in str(글).splitlines():
        조각 = 줄.replace(",", " ").split()
        if len(조각) != 2:
            continue
        try:
            나온것.append((조각[0], float(조각[1])))
        except ValueError:
            continue
    return 나온것


def 파람값(netlist: str, 이름: str):
    m = re.search(_파람.format(이름=re.escape(이름)), netlist or "", re.M | re.I)
    if not m:
        return None
    try:
        return float(m.group(2))
    except ValueError:
        return None


def 파람바꾸기(netlist: str, 이름: str, 값: float) -> "tuple[str, int]":
    """`.param 이름 = ...` 의 값을 바꾼다. (바뀐 글, 바꾼 자리 수)."""
    새글, 수 = re.subn(_파람.format(이름=re.escape(이름)),
                     lambda m: m.group(1) + repr(값), netlist or "", flags=re.M | re.I)
    return 새글, 수


def 흩뿌리기(netlist: str, 산포, 횟수: int = 30, 확인=None, 씨: int = 1234,
          초: int = None) -> dict:
    """공정 산포를 넣고 `횟수` 만큼 돌린다. {판정, 판수, 흩어짐, 수율, 잰것, 왜}."""
    if not 있나():
        return {"판정": 못잼, "판수": 0, "흩어짐": {}, "수율": -1, "잰것": {},
                "왜": "ngspice 가 없다 -- `apt-get install -y ngspice`"}
    퍼짐 = 산포읽기(산포)
    if not 퍼짐:
        return {"판정": 못잼, "판수": 0, "흩어짐": {}, "수율": -1, "잰것": {},
                "왜": ("**흔들 것을 안 줬다** -- `이름 시그마` 를 한 줄씩 줘라. "
                      "산포 없는 몬테카를로는 같은 판을 N 번 돌리는 것이다")}
    횟수 = max(2, min(int(횟수 or 30), 300))
    없는이름 = [이름 for 이름, _ in 퍼짐 if 파람값(netlist, 이름) is None]
    if 없는이름:
        # **여기서 막는다.** 안 막으면 아무것도 안 흔들린 채 수율 100% 가 나온다.
        return {"판정": 못잼, "판수": 0, "흩어짐": {}, "수율": -1, "잰것": {},
                "왜": (f"넷리스트에 `.param {없는이름[0]} = ...` 이 없다 -- 바꿔 끼울 자리가 "
                      "없으면 **같은 판을 N 번 돌리게 된다**. 흔들 값은 `.param` 으로 "
                      f"빼 두고 모델에서 `{{{없는이름[0]}}}` 로 써라")}
    뽑기 = _random.Random(씨)
    본값 = {이름: 파람값(netlist, 이름) for 이름, _ in 퍼짐}
    모은것: "dict[str, list]" = {}
    뽑힌값: "dict[str, list]" = {이름: [] for 이름, _ in 퍼짐}
    센판, 깨진판, 첫탈 = 0, 0, ""
    for _ in range(횟수):
        글 = netlist
        for 이름, 시그마 in 퍼짐:
            v = 뽑기.gauss(본값[이름], 시그마)
            뽑힌값[이름].append(v)
            글, _ = 파람바꾸기(글, 이름, v)
        r = 돌리기(글, 확인, 초)
        if r["판정"] == 못잼:
            return {"판정": 못잼, "판수": 센판, "흩어짐": {}, "수율": -1, "잰것": {},
                    "왜": f"한 판이 못잼이라 멈춘다 -- {r['왜']}", "로그": r.get("로그", "")}
        센판 += 1
        if r["판정"] == FAIL:
            깨진판 += 1
            첫탈 = 첫탈 or r["왜"]
        for k, v in (r["잰것"] or {}).items():
            모은것.setdefault(k, []).append(v)

    흩어짐 = {}
    for k, vs in 모은것.items():
        if len(vs) >= 2:
            흩어짐[k] = {"평균": _stat.fmean(vs), "시그마": _stat.pstdev(vs),
                       "최소": min(vs), "최대": max(vs)}
    수율 = 100.0 * (센판 - 깨진판) / 센판 if 센판 else -1

    def _수율말(수율, 센판):
        """**수율에 오차를 붙인다.** 20판짜리 85% 는 ±8% 다 -- 소수점 한 자리로 적어 놓으면
        그 정밀이 있는 줄 안다. 판을 늘리는 것 말고 그 오차를 줄이는 길은 없다."""
        p = 수율 / 100.0
        if 깨진판 == 0:
            # **0 탈락에 ±0% 를 적으면 안 된다.** 이항 표준오차가 p=1 에서 0 이 되는데,
            # 40판에 0탈락이 "정확히 100%" 를 뜻하지는 않는다. 3의 규칙을 쓴다:
            # 95% 신뢰로 참 탈락률은 3/n 까지 갈 수 있다.
            return (f"수율 {수율:.1f}% -- {센판}판에 탈락 0. 그래도 참 탈락률은 "
                    f"{300.0 / 센판:.1f}% 까지 갈 수 있다(3의 규칙). "
                    f"**0 탈락은 0% 가 아니다**")
        오차 = 100.0 * _math.sqrt(max(p * (1 - p), 0.0) / 센판)
        말 = f"수율 {수율:.1f}% ±{오차:.1f}% ({센판}판)"
        if 센판 < 30:
            말 += " -- **판이 적어 이 숫자는 성글다**"
        return 말

    # **흔들었는데 결과가 안 흩어졌으면 말한다.** 아무것도 안 먹은 것일 수 있다.
    안흩어진것 = [k for k, v in 흩어짐.items() if v["최대"] == v["최소"]]
    if 흩어짐 and len(안흩어진것) == len(흩어짐):
        return {"판정": 못잼, "판수": 센판, "흩어짐": 흩어짐, "수율": 수율, "잰것": 모은것,
                "왜": ("**{}판을 돌렸는데 잰 값이 하나도 안 흩어졌다** -- 흔든 파라미터가 "
                      "결과에 안 닿는다. `.param` 이름이 모델 안에서 실제로 쓰이는지 "
                      "봐라. 안 흩어진 몬테카를로는 같은 판을 {}번 돌린 것이다"
                      .format(센판, 센판))}
    말 = " · ".join(f"{k}: {v['평균']:.4g} ±{v['시그마']:.3g} "
                   f"[{v['최소']:.4g}, {v['최대']:.4g}]" for k, v in 흩어짐.items())
    if 깨진판:
        return {"판정": FAIL, "판수": 센판, "흩어짐": 흩어짐, "수율": 수율, "잰것": 모은것,
                "왜": (f"**{센판}판 중 {깨진판}판이 범위를 벗어났다 ({_수율말(수율, 센판)})** -- "
                      f"{첫탈[:80]}. {말}")}
    if not 확인:
        return {"판정": 못잼, "판수": 센판, "흩어짐": 흩어짐, "수율": -1, "잰것": 모은것,
                "왜": (f"{센판}판이 다 돌았고 흩어짐은 이렇다 -- {말}. 그런데 **무엇을 "
                      "통과로 볼지 안 줬다**(`확인`). 수율을 말하려면 범위가 있어야 한다")}
    return {"판정": PASS, "판수": 센판, "흩어짐": 흩어짐, "수율": 수율, "잰것": 모은것,
            "왜": f"**{센판}판 전부 범위 안 ({_수율말(수율, 센판)})** -- {말}"}


본보기["mc_mirror"] = _모델 + """\
* Current-mirror MISMATCH -- the copy is only as good as the two Vth match.
* `vtn2` is the mirrored device's threshold; sweep it with Monte Carlo.
.param vtn2 = 0.5
.model nch2 NMOS (LEVEL=1 VTO={vtn2} KP=200u GAMMA=0.4 PHI=0.7 LAMBDA=0.05)
Vdd vdd 0 DC 1.8
Iref vdd ref DC 50u
Vout vdd out DC 0.9
M1 ref ref 0 0 nch  W=10u L=1u
M2 out ref 0 0 nch2 W=10u L=1u
.control
op
let iout = i(Vout)
let mismatch_pct = 100*(iout-50u)/50u
print iout mismatch_pct
.endc
"""

본보기["rc_noise"] = """\
* Thermal noise of an RC low-pass. The famous answer is sqrt(kT/C) -- **independent
* of R**: a bigger R makes more noise but also a narrower band, and the two cancel.
V1 in 0 DC 0 AC 1
R1 in out 1k
C1 out 0 1n
.control
noise v(out) V1 dec 40 1 100Meg
print inoise_total onoise_total
.endc
"""

영어이름.update({
    "mismatch": "mc_mirror", "montecarlo": "mc_mirror", "mc": "mc_mirror",
    "noise": "rc_noise", "ktc": "rc_noise", "kt_c": "rc_noise",
})
