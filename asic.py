"""**현대 실리콘의 잣대로 값을 매긴다** -- FPGA 패브릭이 아니라 ASIC 면적.

## 왜 iCE40 셈이 답이 아닌가

앞판은 "곱셈기 0개" 를 iCE40(하드 곱셈기가 없는 FPGA)에서 셌다. 지적이 맞다 --
현대 NPU·ASIC·주류 FPGA 에는 **하드 곱셈기가 널려 있다.** 같은 RTL 을 Xilinx 7 계열로
합성하면 순서가 뒤집힌다(표 1,316 셀 vs 망 391 셀 + DSP 12).

그런데 **112G/224G SerDes 는 FPGA 가 아니라 ASIC 이다.** 그러니 물어야 할 것은
"어느 FPGA 에서 싼가" 가 아니라 **"실리콘 면적이 얼마인가"** 다. 이 모듈이 그것을 잰다.

## 면적을 **어디서 가져오나** -- 라이브러리 자신에게서

숫자를 베껴 적지 않는다. sky130 표준셀 라이브러리(`sky130_fd_sc_hd`)는 셀마다

    .lef     `SIZE w BY h`        -> 실제 면적 (um^2)
    .spice   트랜지스터 넷리스트    -> 소자 수

를 싣고 있다. `pdk.py` 가 그 둘만 푼다(2.8 MB). 그러니 여기서 나오는 면적은
**PDK 가 말한 값**이지 내가 적은 상수가 아니다.

## 잇는 길 -- yosys 가 일반 게이트로 내리면 그것을 셀에 붙인다

Liberty(`.lib`) 파일은 이 휠에 없어서 `abc -liberty` 로 진짜 기술 매핑은 못 한다.
대신 yosys 로 **일반 게이트 집합**까지 내리고(`abc -g`), 게이트마다 sky130 셀을
하나씩 짝지어 그 셀의 LEF 면적을 더한다.

    $_NAND_ -> nand2_1     $_NOR_ -> nor2_1      $_AND_ -> and2_0
    $_XOR_  -> xor2_1      $_MUX_ -> mux2_1      $_NOT_ -> inv_1
    $_DFF_P_ -> dfxtp_1    ...

**이것은 배치배선 뒤의 면적이 아니다.** 셀 면적의 합이고, 실제 다이는 이용률
(보통 0.5~0.7)만큼 더 크다. 그래서 두 구조의 **비(比)** 로 읽어야 하고, 절대
면적으로 읽으면 안 된다 -- 그 한계를 `잰것()` 이 결과에 같이 싣는다.

## 드라이브 세기를 **가장 작은 것으로 고정한다**

`nand2_1` 과 `nand2_8` 은 면적이 몇 배 다르다. 어느 것을 고르느냐로 결론이 바뀌면
안 되므로 **모두 가장 작은 것**으로 고정하고, 그 가정을 결과에 적는다. 두 구조가
같은 가정을 쓰므로 비는 안 흔들린다.
"""
from __future__ import annotations

import os
import re
import subprocess

import pdk

# yosys 일반 게이트 -> sky130_fd_sc_hd 셀. 드라이브는 가장 작은 것으로.
짝 = {
    "$_NOT_": "inv_1", "$_BUF_": "buf_1",
    "$_AND_": "and2_0", "$_NAND_": "nand2_1",
    "$_OR_": "or2_0", "$_NOR_": "nor2_1",
    "$_XOR_": "xor2_1", "$_XNOR_": "xnor2_1",
    "$_ANDNOT_": "and2b_1", "$_ORNOT_": "or2b_1",
    "$_MUX_": "mux2_1", "$_NMUX_": "mux2i_1",
    "$_AOI3_": "a21oi_1", "$_OAI3_": "o21ai_0",
    "$_AOI4_": "a22oi_1", "$_OAI4_": "o22ai_1",
    "$_DFF_P_": "dfxtp_1", "$_DFF_N_": "dfxtp_1",
    "$_DFFE_PP_": "edfxtp_1",
    # 비동기 리셋 플립플롭. 이 저장소의 RTL 은 `negedge rst_n` 을 쓴다 --
    # 활성 낮은 비동기 리셋이라 sky130 의 `dfrtp` 와 **정확히 같은 것**이다.
    "$_DFF_PN0_": "dfrtp_1", "$_DFF_PP0_": "dfrtp_1",
    # **enable + 비동기 리셋은 sky130 에 단일 셀이 없다.** 실제로 그렇게 짓듯이
    # `dfrtp + mux2` 로 값을 매긴다 -- 빼고 세는 것보다 정확하고, 무엇으로 세는지가
    # 여기 적혀 있다. (`dfflegalize` 로 풀려 했더니 뒤의 `opt` 가 다시 묶어 버렸다.)
    "$_DFFE_PN0P_": ("dfrtp_1", "mux2_1"),
    "$_DFFE_PN0N_": ("dfrtp_1", "mux2_1"),
    "$_DLATCH_P_": "dlxtp_1",
}

_SIZE = re.compile(r"^\s*SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;", re.M)


def 있나() -> bool:
    return pdk.표준셀있나() or pdk.받기().get("표준셀") is not None


def _셀파일(셀: str, 확장: str) -> "str | None":
    뿌리 = pdk.표준셀자리()
    if not 뿌리:
        return None
    바탕 = 셀.rsplit("_", 1)[0]                  # nand2_1 -> nand2
    p = os.path.join(뿌리, 바탕, f"sky130_fd_sc_hd__{셀}{확장}")
    return p if os.path.exists(p) else None


def 셀면적(셀) -> float:
    """LEF 의 `SIZE w BY h` 에서 um^2. 여러 셀이면 합. 못 찾으면 nan."""
    if isinstance(셀, (tuple, list)):
        return float(sum(셀면적(c) for c in 셀))
    p = _셀파일(셀, ".lef")
    if not p:
        return float("nan")
    m = _SIZE.search(open(p, encoding="utf-8", errors="ignore").read())
    return float(m.group(1)) * float(m.group(2)) if m else float("nan")


def 셀소자수(셀) -> int:
    """`.spice` 넷리스트의 MOSFET 수. 여러 셀이면 합. 못 찾으면 -1."""
    if isinstance(셀, (tuple, list)):
        각 = [셀소자수(c) for c in 셀]
        return -1 if any(x < 0 for x in 각) else int(sum(각))
    p = _셀파일(셀, ".spice")
    if not p:
        return -1
    n = 0
    for 줄 in open(p, encoding="utf-8", errors="ignore"):
        t = 줄.strip()
        if t[:1] in ("X", "M") and "sky130_fd_pr__" in t:
            n += 1
    return n


def 표(): 
    """짝지은 셀 전부의 면적·소자수. **라이브러리가 답한 것**이다."""
    난것 = {}
    for g, c in 짝.items():
        난것[g] = {"셀": c, "면적um2": 셀면적(c), "소자수": 셀소자수(c)}
    return 난것


def 합성(verilog: str, 최상위: str, 초: int = 600) -> dict:
    """yosys 로 일반 게이트까지 내리고 게이트 수를 센다."""
    if not shutil_which("yosys"):
        return {"판정": "못잼", "왜": "yosys 가 없다"}
    import tempfile
    d = tempfile.mkdtemp()
    v = os.path.join(d, "in.v")
    open(v, "w").write(verilog)
    게이트 = " ".join(sorted(짝.keys()))
    # **플립플롭을 한 종류로 몰아 놓는다.** 안 그러면 비동기 리셋·enable 변종이
    # 여남은 가지로 나오고, 내가 짝 못 지은 것이 **조용히 면적에서 빠진다** --
    # 실측: `$_DFFE_PN0P_` 와 `$_DFF_PN0_` 가 그렇게 빠져 면적이 작게 나왔다.
    # `dfflegalize` 로 **`$_DFF_PN0_` 한 종류**로 몬다(이 RTL 의 리셋이 그 꼴이다).
    # enable 변종은 D 앞의 먹스로 풀리므로 **아무것도 안 사라진다.** 리셋을 지우려
    # 들면(`-cell $_DFF_P_`) yosys 가 거절한다 -- 비동기 리셋은 논리로 못 옮긴다.
    본 = (f"read_verilog {v}; hierarchy -top {최상위}; proc; opt; fsm; opt; "
         f"memory; opt; techmap; opt; dfflegalize -cell $_DFF_PN0_ 01; opt; "
         f"abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX,AOI3,OAI3,AOI4,OAI4; "
         f"opt; stat")
    r = subprocess.run(["yosys", "-p", 본], capture_output=True, text=True, timeout=초)
    if r.returncode != 0:
        return {"판정": "못잼", "왜": (r.stderr or r.stdout)[-400:]}
    수 = {}
    본문 = r.stdout
    구역 = 본문.rsplit("Number of cells:", 1)
    for 줄 in (구역[-1] if len(구역) > 1 else 본문).splitlines():
        m = re.match(r"\s+(\$_\w+_)\s+(\d+)", 줄)
        if m:
            수[m.group(1)] = int(m.group(2))
    return {"판정": "PASS", "게이트": 수, "로그": 본문[-2000:]}


def shutil_which(x):
    from shutil import which
    return which(x)


def 잰것(verilog: str, 최상위: str, 초: int = 600) -> dict:
    """**합성하고 sky130 면적으로 값을 매긴다.**"""
    if not 있나():
        return {"판정": "못잼", "왜": "sky130 표준셀을 못 구했다"}
    r = 합성(verilog, 최상위, 초)
    if r.get("판정") != "PASS":
        return r
    면적, 소자, 모름 = 0.0, 0, {}
    for g, n in r["게이트"].items():
        c = 짝.get(g)
        a, t = (셀면적(c), 셀소자수(c)) if c else (float("nan"), -1)
        if not c or a != a or t < 0:
            모름[g] = n
            continue
        면적 += a * n
        소자 += t * n
    if 모름:
        # **짝 못 지은 게이트가 있으면 면적을 내지 않는다.** 그것을 빼고 더한
        # 면적은 작게 나오고, 작게 나온 면적은 "표가 싸다" 쪽으로 새기 쉽다.
        return {"판정": "못잼", "왜": f"짝 못 지은 게이트가 있다: {모름}",
                "게이트": r["게이트"], "못붙인게이트": 모름}
    return {"판정": "PASS", "게이트": r["게이트"],
            "게이트수": sum(r["게이트"].values()),
            "셀면적um2": 면적, "소자수": 소자, "못붙인게이트": {},
            "한계": ("셀 면적의 합이다 -- 배치배선 뒤 다이는 이용률(0.5~0.7)만큼 "
                   "더 크다. **비(比)로 읽고 절대 면적으로 읽지 마라.** "
                   "드라이브는 전부 가장 작은 것으로 고정했다(가정)."),
            "라이브러리": "sky130_fd_sc_hd (LEF SIZE · SPICE 소자수)"}
