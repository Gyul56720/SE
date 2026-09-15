"""RTL 을 **실제로 돌린다.** 짓기(iverilog) · 돌리기(vvp) · 린트(verilator) · 합성(yosys).

사용자(2026-09-15): 작은 design house 와 IP 회사를 만든다.

## 왜 있나 -- "썼다" 와 "돌려서 통과했다" 는 다르다

봇은 Verilog 를 **쓸** 수 있었지만 **돌릴** 수가 없었다. 그러면 그 코드가 맞는지
아무도 검사하지 않는다 -- 이 저장소가 내내 다뤄 온 그 차이다.

## 끝값을 믿으면 안 된다 -- 실측 2026-09-15

일부러 틀린 카운터(`q <= q + 2`)를 테스트벤치에 물렸더니 이렇게 나왔다.

    FAIL: q=8 expected 4
    FAIL: 1 error(s)
    $finish called at 52000
    **끝값=0**

`$finish` 로 끝나면 `vvp` 는 **불합격이어도 0** 을 낸다. 끝값만 보면 깨진 RTL 이 전부
초록이다. 그래서 여기서는 **출력을 읽어 판정한다.** 그리고 합격 표시도 불합격 표시도
없으면 **통과가 아니라 못잼**이다 -- 안 찍은 것을 통과로 세면 그것이 거짓 초록이다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

PASS, FAIL, 못잼 = "PASS", "FAIL", "못잼"
시한초 = 120

# 불합격 표시. 흔한 꼴을 넓게 받는다 -- 못 잡으면 거짓 초록이 된다.
_불합격 = re.compile(
    r"\b(FAIL(ED|URE)?|ERROR|MISMATCH|ASSERT(ION)?\s+FAIL\w*)\b|\$error|\$fatal",
    re.I)
# 합격 표시. **이것이 있어야만** 통과다.
_합격 = re.compile(r"\b(PASS(ED)?|ALL\s+TESTS?\s+(OK|PASSED)|OK)\b", re.I)
# 컴파일러가 낸 진짜 오류(문법 등). 이건 못잼이지 불합격이 아니다.
_짓기오류 = re.compile(r"(syntax error|error:|Unable to bind|Cannot find)", re.I)


def 있나(도구: str) -> bool:
    return shutil.which(도구) is not None


def 없는도구(*도구들) -> "list[str]":
    return [t for t in 도구들 if not 있나(t)]


def 첫모듈(글: str) -> str:
    """첫 `module <이름>` 의 이름. 못 찾으면 빈 문자열."""
    m = re.search(r"^\s*module\s+([A-Za-z_]\w*)", 글 or "", re.M)
    return m.group(1) if m else ""


def _쓰기(판: str, 이름: str, 글: str) -> str:
    쪽 = os.path.join(판, 이름)
    with open(쪽, "w", encoding="utf-8") as f:
        f.write(글)
    return 쪽


def _돌리기(argv, 판, 초=None):
    try:
        r = subprocess.run(argv, cwd=판, capture_output=True, text=True,
                           errors="replace", timeout=초 or 시한초)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 124, f"{초 or 시한초}초 안에 안 끝났다 -- 무한 루프이거나 $finish 가 없다"
    except OSError as e:
        return 127, f"{type(e).__name__}: {e}"


def 판정하기(로그: str) -> "tuple[str, str]":
    """출력만 보고 (판정, 까닭). **끝값을 안 본다** -- 위 머리말의 까닭이다."""
    불 = _불합격.search(로그 or "")
    합 = _합격.search(로그 or "")
    if 불:
        return FAIL, f"불합격 표시가 있다: {불.group(0)!r}"
    if 합:
        return PASS, f"합격 표시가 있다: {합.group(0)!r}"
    return 못잼, ("테스트벤치가 합격도 불합격도 안 찍었다 -- `$display(\"PASS\")` / "
                "`$display(\"FAIL ...\")` 를 넣어라. **안 찍은 것을 통과로 세지 않는다**")


def 시뮬(design: str, testbench: str, top: str = "tb", 초: int = None) -> dict:
    """설계와 테스트벤치를 짓고 돌린다. {판정, 끝값, 로그, 왜}."""
    빠진 = 없는도구("iverilog", "vvp")
    if 빠진:
        return {"판정": 못잼, "끝값": -1, "로그": "",
                "왜": f"도구가 없다: {' · '.join(빠진)} -- `apt-get install -y iverilog`"}
    if not (design or "").strip():
        return {"판정": 못잼, "끝값": -1, "로그": "", "왜": "설계가 비었다"}
    if not (testbench or "").strip():
        return {"판정": 못잼, "끝값": -1, "로그": "",
                "왜": "테스트벤치가 없다 -- **돌려 보지 않은 코드는 통과가 아니다**"}
    판 = tempfile.mkdtemp(prefix="rtl-")
    _쓰기(판, "design.v", design)
    _쓰기(판, "tb.v", testbench)
    끝값, 로그 = _돌리기(["iverilog", "-g2012", "-o", "sim.vvp", "-s", top,
                       "design.v", "tb.v"], 판)
    if 끝값 != 0 or _짓기오류.search(로그):
        return {"판정": 못잼, "끝값": 끝값, "로그": 로그,
                "왜": "**짓기에서 막혔다** -- 돌려 보지도 못했다. 아래 오류를 고쳐라"}
    끝값, 로그 = _돌리기(["vvp", "sim.vvp"], 판, 초)
    if 끝값 == 124:
        return {"판정": 못잼, "끝값": 끝값, "로그": 로그, "왜": 로그}
    판정, 왜 = 판정하기(로그)
    return {"판정": 판정, "끝값": 끝값, "로그": 로그, "왜": 왜}


def 린트(design: str, 엄하게: bool = True) -> dict:
    """verilator 로 정적 점검. {판정, 경고수, 로그, 왜}."""
    if not 있나("verilator"):
        return {"판정": 못잼, "경고수": -1, "로그": "",
                "왜": "verilator 가 없다 -- `apt-get install -y verilator`"}
    판 = tempfile.mkdtemp(prefix="lint-")
    # **파일 이름을 모듈 이름에 맞춘다.** 안 맞추면 verilator 가 DECLFILENAME 경고를
    # 내는데, 그건 **우리가 만든 경고**다 -- 사용자 코드의 흠이 아니다. 실측 2026-09-15:
    # 멀쩡한 카운터가 그것 하나로 FAIL 로 찍혔다. 늘 우는 경보는 아무도 안 본다.
    이름 = (첫모듈(design) or "design") + ".v"
    _쓰기(판, 이름, design or "")
    argv = ["verilator", "--lint-only", 이름]
    if 엄하게:
        argv.insert(2, "-Wall")
    끝값, 로그 = _돌리기(argv, 판)
    경고 = len(re.findall(r"^%(Warning|Error)", 로그 or "", re.M))
    return {"판정": PASS if 끝값 == 0 and 경고 == 0 else FAIL,
            "경고수": 경고, "로그": 로그,
            "왜": "깨끗하다" if 끝값 == 0 and 경고 == 0 else f"경고·오류 {경고}건"}


def 합성(design: str, top: str = "") -> dict:
    """yosys 로 합성해 **셀 수**를 센다. {판정, 셀수, 로그, 왜}.

    게이트 수는 PPA 의 P 다 -- "돌아간다" 다음에 오는 물음이 "얼마나 크냐" 이다.
    """
    if not 있나("yosys"):
        return {"판정": 못잼, "셀수": -1, "로그": "",
                "왜": "yosys 가 없다 -- `apt-get install -y yosys`"}
    판 = tempfile.mkdtemp(prefix="synth-")
    이름 = (첫모듈(design) or "design") + ".v"
    _쓰기(판, 이름, design or "")
    명 = (f"read_verilog -sv {이름}; "
         + (f"synth -top {top}; " if top else "synth; ") + "stat")
    # **`-q` 를 안 쓴다.** 그것이 `stat` 출력까지 삼켜서 셀 수를 영영 못 읽었다
    # (실측 2026-09-15: 셀수 -1 이 나왔는데 합성은 성공한 것이었다).
    끝값, 로그 = _돌리기(["yosys", "-p", 명], 판)
    if 끝값 != 0:
        return {"판정": 못잼, "셀수": -1, "로그": 로그, "왜": "합성이 막혔다"}
    m = re.search(r"Number of cells:\s+(\d+)", 로그 or "")
    셀 = int(m.group(1)) if m else -1
    return {"판정": PASS, "셀수": 셀, "로그": 로그,
            "왜": f"셀 {셀}개" if 셀 >= 0 else "셀 수를 못 읽었다"}
