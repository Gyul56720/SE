"""형식 검증. yosys 의 `sat` 으로 **성질을 증명한다** -- 못 하면 못 했다고 한다.

사용자(2026-09-15): design house 의 남은 구멍 중 둘째.

## 시뮬과 무엇이 다른가

`rtl.py` 는 테스트벤치가 **가 본 자리**만 본다. 형식 검증은 솔버가 **모든 자리**를
뒤진다 -- 벤치가 못 만든 입력 조합까지. 그래서 200번째 클럭에야 깨지는 것도 잡는다.

## 여기에는 거짓 초록이 **셋**이다 -- 실측 2026-09-15 (yosys 0.33)

| 넣은 것 | 나온 것 | 끝값 |
|---|---|---|
| 성질이 성립한다 (원형 카운터) | `Induction step proven: SUCCESS!` | 0 |
| 성질이 깨진다 | `SAT proof finished - model found: FAIL!` | **0** |
| **`assert` 가 하나도 없는 설계** | `no model found: **SUCCESS!**` | **0** |
| **깊이 20 BMC, 버그는 200번째 클럭** | `no model found: **SUCCESS!**` | **0** |

1. 깨진 것도 끝값 0 이다 -- `vvp` · ngspice 와 같은 병. 출력을 읽는다.
2. **증명할 성질이 없으면 공허하게 SUCCESS 다.** 아무것도 증명 안 했는데 초록이다.
   형식 검증에서 제일 흔한 자기기만이고, 여기서는 **못잼**이다.
3. **유계(BMC)는 증명이 아니다.** `-seq 20` 은 "20 걸음 안에 반례가 없다" 일 뿐인데
   같은 글자 `SUCCESS` 로 나온다. 실측: 200번째 클럭에 깨지는 설계가 깊이 20 에서
   초록이었고, 귀납(`-tempinduct`)이 잡아냈다. 그래서 유계 통과도 **못잼**이다 --
   몇 걸음까지 봤는지 같이 말한다.

    PASS  성질이 있고 **무계 증명(귀납)** 이 났다
    FAIL  반례가 나왔다 (반례는 VCD 로 받아 파형으로 그린다)
    못잼  성질이 없다 · 유계까지만 봤다 · 안 돌았다

## 형식은 리셋이 없는 데서 시작한다

시뮬은 `initial` 부터 돌지만 솔버는 **아무 상태**에서 시작한다. 그래서 시뮬이
통과하던 설계가 여기서는 대뜸 깨진다 -- 그건 도구 탓이 아니라 그 상태가 실제로
도달 가능한지 아무도 안 따진 것이다. 초기값(`initial`/`= 0`)을 적거나 리셋을
가정으로 묶어라. `초기0` 은 그것을 대신 해 주는 손잡이다(`-set-init-zero`).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

PASS, FAIL, 못잼 = "PASS", "FAIL", "못잼"
시한초 = 300

# 실측한 글자들. **끝값이 아니라 이것으로 판정한다.**
_반례 = re.compile(r"model found(?: for base case)?: FAIL!", re.I)
_귀납성공 = re.compile(r"Induction step proven: SUCCESS!", re.I)
_유계성공 = re.compile(r"SAT proof finished - no model found: SUCCESS!", re.I)
_오류 = re.compile(r"^ERROR:", re.M)
# 성질이 실제로 SAT 판에 들어갔나. 없으면 증명한 것이 없다.
_성질들어감 = re.compile(r"Import proof for assert", re.I)
# 소스에 성질이 있나. **줄 앵커(`^`)를 안 쓴다** -- 그러면 한 줄에 여럿 있어도 하나로
# 센다(실측: `assume (x); cover (y); assert (z);` 가 1 로 나왔다). 대신 주석을 먼저 지운다.
_성질 = re.compile(r"\b(assert|assume|cover|restrict)\s*\(")
_주석 = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def 있나() -> bool:
    return shutil.which("yosys") is not None


def 성질세기(글: str) -> int:
    return len(_성질.findall(_주석.sub(" ", 글 or "")))


def 첫모듈(글: str) -> str:
    m = re.search(r"^\s*module\s+([A-Za-z_]\w*)", 글 or "", re.M)
    return m.group(1) if m else ""


def 판정하기(로그: str, 무계: bool, 깊이: int) -> "tuple[str, str]":
    """출력만 보고 (판정, 까닭). **끝값을 안 본다** -- 머리말의 까닭이다."""
    로그 = 로그 or ""
    if _오류.search(로그):
        m = _오류.search(로그)
        끝 = 로그[m.start():].splitlines()[0]
        return 못잼, f"yosys 가 막혔다: {끝[:120]}"
    if _반례.search(로그):
        return FAIL, ("**반례가 있다** -- 솔버가 성질을 깨는 입력을 찾았다. "
                      "아래 파형이 그 장면이다")
    if not _성질들어감.search(로그):
        # **공허한 통과.** 증명할 것이 없는데 SUCCESS 가 나온다(실측).
        return 못잼, ("**증명할 성질이 하나도 없다** -- `assert (...)` 를 쓰지 않으면 "
                     "솔버는 아무것도 안 하고 SUCCESS 를 낸다. 성질 없는 초록은 초록이 아니다")
    if _귀납성공.search(로그):
        return PASS, "**무계로 증명됐다** -- 어떤 걸음 수에서도 성질이 깨지지 않는다(귀납)"
    if _유계성공.search(로그):
        if 무계:
            return 못잼, ("귀납이 안 끝났다 -- 유계까지만 봤다. "
                         f"{깊이} 걸음 안에 반례가 없을 뿐, 증명은 아니다")
        return 못잼, (f"**{깊이} 걸음 안에 반례가 없다. 그것은 증명이 아니다** -- "
                     "실측으로 200번째 클럭에야 깨지는 설계가 깊이 20 에서 초록이었다. "
                     "`무계=True`(귀납)로 다시 돌려라")
    return 못잼, "솔버가 성공도 실패도 안 찍었다"


def 증명(design: str, top: str = "", 깊이: int = 20, 무계: bool = True,
       초기0: bool = True, 초: int = None, 반례낼곳: str = "") -> dict:
    """성질을 증명한다. {판정, 성질수, 깊이, 로그, 반례, 왜}."""
    if not 있나():
        return {"판정": 못잼, "성질수": 0, "깊이": 깊이, "로그": "", "반례": "",
                "왜": "yosys 가 없다 -- `apt-get install -y yosys`"}
    if not (design or "").strip():
        return {"판정": 못잼, "성질수": 0, "깊이": 깊이, "로그": "", "반례": "",
                "왜": "설계가 비었다"}
    성질수 = 성질세기(design)
    if 성질수 == 0:
        # 돌리기도 전에 안다. 돌려 봐야 공허한 SUCCESS 만 나온다.
        return {"판정": 못잼, "성질수": 0, "깊이": 깊이, "로그": "", "반례": "",
                "왜": ("**설계에 `assert` 가 하나도 없다** -- 증명할 것이 없으면 솔버는 "
                      "SUCCESS 를 낸다(실측). 검사하려는 성질을 `assert (...)` 로 써라")}
    판 = tempfile.mkdtemp(prefix="formal-")
    이름 = (top or 첫모듈(design) or "design")
    쪽 = os.path.join(판, 이름 + ".sv")
    with open(쪽, "w", encoding="utf-8") as f:
        f.write(design)
    cex = os.path.join(판, "cex.vcd")
    명 = [f"read_verilog -formal -sv {os.path.basename(쪽)}",
         f"prep -top {이름} -flatten", "async2sync",
         "sat -prove-asserts -seq %d" % max(1, 깊이)]
    if 무계:
        명[-1] += " -tempinduct"
    if 초기0:
        명[-1] += " -set-init-zero"
    # **`-show-all` 이 없으면 반례가 납작하다.** 실측 2026-09-15: 같은 반례가
    # 없으면 2걸음 6신호, 붙이면 15걸음 26신호였다. 2걸음짜리 그림은 아무 일도
    # 안 일어난 것처럼 보인다 -- 반례를 그려 놓고 멀쩡해 보이면 없느니만 못하다.
    명[-1] += f" -show-all -dump_vcd {os.path.basename(cex)}"
    try:
        r = subprocess.run(["yosys", "-p", "; ".join(명)], cwd=판,
                           capture_output=True, text=True, errors="replace",
                           timeout=초 or 시한초)
        로그 = ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return {"판정": 못잼, "성질수": 성질수, "깊이": 깊이, "로그": "", "반례": "",
                "왜": (f"{초 or 시한초}초 안에 안 끝났다 -- 깊이를 줄이거나 성질을 쪼개라. "
                      "**안 끝난 것은 통과가 아니다**")}
    except OSError as e:
        return {"판정": 못잼, "성질수": 성질수, "깊이": 깊이, "로그": "", "반례": "",
                "왜": f"{type(e).__name__}: {e}"}
    판정, 왜 = 판정하기(로그, 무계, 깊이)
    난것 = {"판정": 판정, "성질수": 성질수, "깊이": 깊이, "로그": 로그, "반례": "", "왜": 왜}
    if 판정 == FAIL and 반례낼곳 and os.path.exists(cex):
        import vcd as _vcd
        g = _vcd.그리기(cex, 반례낼곳)
        if g.get("그렸나"):
            난것["반례"] = g["경로"]
            난것["왜"] += f" ({g['왜'].splitlines()[0]})"
    return 난것
