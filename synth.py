"""**한 소자 말고 여러 소자에서 재기** -- 곱셈기의 값은 소자가 정한다.

논문의 면적 표는 전부 iCE40 HX8K 에서 났다. 그 소자에는 **하드 곱셈기가 없어서**
곱셈이 전부 LUT 로 풀린다 -- 곱셈 기반 설계에 **가장 불리한 자리**다. 논문도 그것을
한계로 적어 두었는데, 적어 두는 것과 재는 것은 다르다.

여기서는 같은 RTL 을 여러 계열로 합성해 **셀 수**를 낸다. ECP5 · Xilinx 7 계열 ·
Intel ALM · Gowin 에는 DSP 가 있고, yosys 의 `mul2dsp` 가 곱셈을 그리로 보낸다.

## 낼 수 있는 것과 없는 것 -- 섞지 않는다

    낼 수 있다   합성 후 셀 수(LUT4 · DSP · FF · 캐리)와 기술 독립 게이트 수
    낼 수 없다   **Fmax · 배치 점유율 · 배선 혼잡** -- 배치·배선 도구가 없다
    낼 수 없다   **ASIC 면적 · 지연 · 전력** -- 표준셀 라이브러리(.lib)가 없다

이 컨테이너에 있는 배치·배선기는 `nextpnr-ice40` 하나뿐이다. ECP5 용 `nextpnr-ecp5`
도, 어떤 Liberty 파일도 없다. **없는 것을 있는 것처럼 적지 않는다** -- "ECP5 에서
82 MHz" 같은 줄을 합성 결과만 보고 쓰면 그것이 이 저장소가 내내 쫓은 거짓 초록이다.

기술 독립 게이트 수(`게이트`)는 2입력 게이트 집합으로 매핑한 뒤의 셀 수다. ASIC
면적이 아니라 **소자에 안 매인 복잡도 대리값**이고, 딱 그만큼만 말한다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

계열 = {
    "ice40": ("synth_ice40", "iCE40 (DSP 없음)"),
    "ecp5": ("synth_ecp5", "Lattice ECP5 (MULT18X18D)"),
    "xilinx": ("synth_xilinx", "Xilinx 7 계열 (DSP48E1)"),
    "intel_alm": ("synth_intel_alm", "Intel ALM (Cyclone V 급)"),
    "gowin": ("synth_gowin", "Gowin (ALU/DSP)"),
    "게이트": ("synth", "기술 독립 2입력 게이트"),
}

_셀 = re.compile(r"^\s+(\$?[A-Za-z_][\w$]*)\s+(\d+)\s*$", re.M)


def 있나() -> bool:
    return shutil.which("yosys") is not None


def 재기(design: str, top: str, 어디: str, 초: int = 600) -> dict:
    """한 계열로 합성하고 셀 수를 돌려준다. {셀, 합계, 곱셈기셀, 판정, 왜}."""
    if not 있나():
        return {"판정": "못잼", "왜": "yosys 가 없다", "셀": {}, "합계": 0}
    if 어디 not in 계열:
        return {"판정": "못잼", "왜": f"모르는 계열 {어디!r}", "셀": {}, "합계": 0}
    명령, _ = 계열[어디]
    판 = tempfile.mkdtemp(prefix="synth-")
    try:
        with open(os.path.join(판, "d.v"), "w", encoding="utf-8") as f:
            f.write(design)
        꼬리 = (f"{명령} -top {top}" if 어디 != "게이트" else
              f"synth -top {top}; abc -g AND,OR,XOR,MUX,NAND,NOR,XNOR; opt_clean")
        try:
            p = subprocess.run(["yosys", "-p",
                                f"read_verilog -sv d.v; proc; chformal -remove; {꼬리}; stat"],
                               cwd=판, capture_output=True, text=True, timeout=초)
        except subprocess.TimeoutExpired:
            return {"판정": "못잼", "왜": f"{초}초를 넘겼다", "셀": {}, "합계": 0}
        if p.returncode != 0:
            return {"판정": "못잼", "왜": "합성이 막혔다: " + p.stdout[-400:],
                    "셀": {}, "합계": 0}
        # **마지막 stat 블록만** 읽는다 -- synth 는 중간에도 stat 을 찍는다.
        덩이 = p.stdout.split("Printing statistics")[-1]
        덩이 = 덩이.split(f"=== {top} ===")[-1]
        셀 = {k: int(v) for k, v in _셀.findall(덩이)}
        m = re.search(r"Number of cells:\s+(\d+)", 덩이)
        합계 = int(m.group(1)) if m else sum(셀.values())
        곱 = sum(v for k, v in 셀.items()
                if any(t in k.upper() for t in ("MULT", "DSP", "MAC")))
        return {"판정": "PASS", "왜": "", "셀": 셀, "합계": 합계, "곱셈기셀": 곱}
    finally:
        shutil.rmtree(판, ignore_errors=True)


def 쓸기(설계들, 어디들=("ice40", "ecp5", "xilinx", "intel_alm", "게이트")) -> str:
    """`[(이름, top, verilog), ...]` 를 계열마다 합성해 표 하나로."""
    줄 = [f"{'설계':<26} " + " ".join(f"{a:>16}" for a in 어디들),
          "-" * (26 + 17 * len(어디들))]
    for 이름, top, v in 설계들:
        칸 = []
        for a in 어디들:
            r = 재기(v, top, a)
            if r["판정"] != "PASS":
                칸.append(f"{'못잼':>16}")
            elif r.get("곱셈기셀"):
                칸.append(f"{r['합계']:>11}+{r['곱셈기셀']:>3}D")
            else:
                칸.append(f"{r['합계']:>16}")
        줄.append(f"{이름:<26} " + " ".join(칸))
    줄.append("D = DSP/곱셈 전용 셀. 합계는 합성 후 셀 수이고 **배치 결과가 아니다**.")
    return "\n".join(줄)


if __name__ == "__main__":     # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import eqrtl
    설계 = [
        ("FFE 11", "ffe_eq", eqrtl.ffe(탭=11, W=7, DW=7)),
        ("FFE 11 + DFE 8 (파이프)", "ffe_dfe",
         eqrtl.ffe_dfe(ffe탭=11, dfe자리=(1, 2, 3, 4, 5, 6, 7, 8), W=7, DW=7, 파이프=True)),
        ("FFE 11 + 표 2x4 (파이프)", "ffe_tbl",
         eqrtl.ffe_tbl(ffe탭=11, 창=2, 색인비트=4, W=7, DW=7, 파이프=True)),
        ("FFE 11 + DA 3탭", "ffe_da", eqrtl.ffe_da(탭=11, DA탭=3, W=7, DW=7)),
        ("NN 5->2 (파이프)", "nneq_eq", eqrtl.nn(창=5, 은닉=2, 파이프=True)),
        ("NN 11->4 (파이프)", "nneq_eq", eqrtl.nn(창=11, 은닉=4, 파이프=True)),
        ("NN 11->16 (파이프)", "nneq_eq", eqrtl.nn(창=11, 은닉=16, 파이프=True)),
    ]
    print(쓸기(설계))
