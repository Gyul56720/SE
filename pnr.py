"""배치·배선과 타이밍. **진짜 칩에 얹어 Fmax 를 잰다** (yosys + nextpnr-ice40).

사용자(2026-09-15): design house 의 남은 구멍 중 셋째.

## 합성 다음에 오는 물음

`rtl.py` 가 "도는가", `synth_rtl` 이 "얼마나 큰가" 를 답했다. 남은 것이
**"얼마나 빠른가"** 이고, 그건 실제 소자에 배치하고 배선해 봐야 안다.
게이트 수만으로는 절대 안 나온다 -- 지연의 대부분이 배선이다.

## 목표 주파수를 안 주면 초록이 거짓말을 한다 -- 실측 2026-09-15

목표 없이 돌리면 이렇게 나온다.

    Info: Max frequency for clock 'clk': 194.33 MHz (**PASS at 12.00 MHz**)
    끝값=0

`12.00 MHz` 는 **사용자가 준 목표가 아니라 nextpnr 의 기본값**이다. 100MHz 로
쓸 설계가 12MHz 에 PASS 했다는 말을 초록으로 읽으면 그대로 속는다. 그래서
**목표를 안 주면 못잼**이다 -- 무엇에 견주어 통과인지 없는 통과는 통과가 아니다.

## 그리고 `--timing-allow-fail` 은 안 쓴다

    목표 250MHz            끝값 1   ERROR: ... (FAIL at 250.00 MHz)
    목표 250MHz + allow    끝값 0   Warning: ... (FAIL at 250.00 MHz)

한 깃발로 빨간불이 초록이 된다. 여기서는 절대 안 붙인다.

## Fmax 줄은 **두 번** 나온다

    Info: Max frequency ... : 190.33 MHz     <- 배치 중 추정
    Info: Max frequency ... : 194.33 MHz     <- 배선까지 끝난 최종

앞엣것을 읽으면 실제보다 낮게 본다. **마지막 것을 쓴다.**
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile

PASS, FAIL, 못잼 = "PASS", "FAIL", "못잼"
시한초 = 600

# 칩 -> (nextpnr 깃발, 기본 패키지, 사람이 읽는 이름)
칩들 = {
    "hx1k":  ("--hx1k",  "tq144", "iCE40 HX1K (1280 LC)"),
    "hx8k":  ("--hx8k",  "ct256", "iCE40 HX8K (7680 LC)"),
    "lp384": ("--lp384", "qn32",  "iCE40 LP384 (384 LC)"),
    "up5k":  ("--up5k",  "sg48",  "iCE40 UP5K (5280 LC)"),
}
기본칩 = "hx8k"

_Fmax = re.compile(
    r"Max frequency for clock\s+'([^']+)':\s+([\d.]+)\s*MHz\s+\((PASS|FAIL) at ([\d.]+) MHz\)")
_칸 = re.compile(r"^Info:\s+(\w+):\s+(\d+)/\s*(\d+)\s+(\d+)%", re.M)
_자리없음 = re.compile(r"Unable to find a placement location|Failed to place|out of", re.I)
_오류 = re.compile(r"^ERROR:\s*(.+)$", re.M)


def 없는도구(*도구들) -> "list[str]":
    return [t for t in 도구들 if shutil.which(t) is None]


def 첫모듈(글: str) -> str:
    m = re.search(r"^\s*module\s+([A-Za-z_]\w*)", 글 or "", re.M)
    return m.group(1) if m else ""


def _돌리기(argv, 판, 초):
    try:
        r = subprocess.run(argv, cwd=판, capture_output=True, text=True,
                           errors="replace", stdin=subprocess.DEVNULL, timeout=초)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 124, f"{초}초 안에 안 끝났다"
    except OSError as e:
        return 127, f"{type(e).__name__}: {e}"


def 클럭들(로그: str) -> "list[dict]":
    """`Max frequency` 줄을 읽는다. **클럭마다 마지막 것만** 남긴다."""
    마지막 = {}
    for 이름, f, 판, 목표 in _Fmax.findall(로그 or ""):
        # 같은 클럭이 두 번 나온다(배치 중 추정 -> 배선 후 최종). 뒤엣것이 진짜다.
        마지막[이름] = {"클럭": 이름, "Fmax": float(f), "판": 판, "목표": float(목표)}
    return list(마지막.values())


def 쓰임(로그: str) -> "list[dict]":
    난것 = []
    for 칸, 쓴것, 다, 퍼센트 in _칸.findall(로그 or ""):
        if int(쓴것) > 0:
            난것.append({"칸": 칸, "쓴것": int(쓴것), "다": int(다), "%": int(퍼센트)})
    return 난것


def 판정하기(로그: str, 목표MHz: float) -> "tuple[str, str, list]":
    로그 = 로그 or ""
    if _자리없음.search(로그):
        return 못잼, ("**칩에 안 들어간다** -- 설계가 소자보다 크다. 더 큰 칩(`hx8k`)을 "
                     "쓰거나 설계를 줄여라"), []
    클럭 = 클럭들(로그)
    if not 클럭:
        m = _오류.search(로그)
        if m:
            return 못잼, f"nextpnr 가 막혔다: {m.group(1)[:140]}", []
        return 못잼, ("**클럭이 하나도 안 잡혔다** -- 조합 논리뿐이거나 `posedge` 가 "
                     "없다. Fmax 는 클럭이 있어야 나온다"), []
    깨진것 = [c for c in 클럭 if c["판"] == "FAIL"]
    if 깨진것:
        c = 깨진것[0]
        모자람 = 100 * (c["목표"] - c["Fmax"]) / c["목표"]
        return FAIL, (f"**{c['클럭']} 이 {c['Fmax']:.2f} MHz 밖에 안 난다** "
                      f"(목표 {c['목표']:.2f} MHz, {모자람:.1f}% 모자람) -- "
                      "임계 경로를 쪼개거나 파이프라인을 넣어라"), 클럭
    말 = " · ".join(f"{c['클럭']}: {c['Fmax']:.2f} MHz (목표 {c['목표']:.2f})" for c in 클럭)
    return PASS, f"목표를 넘는다 -- {말}", 클럭


def 맞춰보기(design: str, top: str = "", 목표MHz: float = 0.0, 칩: str = 기본칩,
          패키지: str = "", 초: int = None) -> dict:
    """합성 -> 배치 -> 배선 -> 타이밍. {판정, Fmax, 목표, 클럭, 쓰임, 로그, 왜}."""
    빠진 = 없는도구("yosys", "nextpnr-ice40")
    if 빠진:
        return {"판정": 못잼, "Fmax": -1, "목표": 목표MHz, "클럭": [], "쓰임": [], "로그": "",
                "왜": f"도구가 없다: {' · '.join(빠진)} -- "
                     "`apt-get install -y yosys nextpnr-ice40 fpga-icestorm`"}
    if not (design or "").strip():
        return {"판정": 못잼, "Fmax": -1, "목표": 목표MHz, "클럭": [], "쓰임": [], "로그": "",
                "왜": "설계가 비었다"}
    if not 목표MHz or 목표MHz <= 0:
        # **이것이 이 모듈의 핵심 규칙이다.** 목표 없는 통과는 통과가 아니다.
        return {"판정": 못잼, "Fmax": -1, "목표": 0, "클럭": [], "쓰임": [], "로그": "",
                "왜": ("**목표 주파수를 줘라** -- 안 주면 nextpnr 는 제 기본값 12 MHz 에 "
                      "견주어 `PASS at 12.00 MHz` 를 낸다(실측). 그 초록은 네 설계가 "
                      "쓸 속도와 아무 상관이 없다")}
    if 칩 not in 칩들:
        return {"판정": 못잼, "Fmax": -1, "목표": 목표MHz, "클럭": [], "쓰임": [], "로그": "",
                "왜": f"모르는 칩 {칩!r} -- {' · '.join(칩들)}"}
    깃발, 기본패키지, 칩이름 = 칩들[칩]
    판 = tempfile.mkdtemp(prefix="pnr-")
    이름 = top or 첫모듈(design) or "top"
    with open(os.path.join(판, "design.v"), "w", encoding="utf-8") as f:
        f.write(design)
    끝값, 합성로그 = _돌리기(
        ["yosys", "-p", f"read_verilog -sv design.v; synth_ice40 -top {이름} -json design.json"],
        판, 초 or 시한초)
    if 끝값 != 0 or not os.path.exists(os.path.join(판, "design.json")):
        return {"판정": 못잼, "Fmax": -1, "목표": 목표MHz, "클럭": [], "쓰임": [],
                "로그": 합성로그[-4000:],
                "왜": "**합성에서 막혔다** -- 배치까지 가지도 못했다"}
    # **`--timing-allow-fail` 을 절대 안 붙인다.** 그 깃발 하나로 빨간불이 초록이 된다.
    끝값, 로그 = _돌리기(
        ["nextpnr-ice40", 깃발, "--package", 패키지 or 기본패키지,
         "--json", "design.json", "--asc", "out.asc",
         "--freq", str(목표MHz), "--pcf-allow-unconstrained"], 판, 초 or 시한초)
    판정, 왜, 클럭 = 판정하기(로그, 목표MHz)
    최저 = min((c["Fmax"] for c in 클럭), default=-1)
    return {"판정": 판정, "Fmax": 최저, "목표": 목표MHz, "클럭": 클럭,
            "쓰임": 쓰임(로그), "칩": 칩이름, "로그": 로그[-6000:], "왜": 왜}


def 말로(r: dict) -> str:
    줄 = []
    if r.get("Fmax", -1) > 0:
        줄.append(f"Fmax {r['Fmax']:.2f} MHz / target {r['목표']:.2f} MHz "
                  f"on {r.get('칩', '?')}")
    쓴 = r.get("쓰임") or []
    if 쓴:
        줄.append(" · ".join(f"{u['칸']} {u['쓴것']}/{u['다']} ({u['%']}%)" for u in 쓴))
    return "\n".join(줄)
