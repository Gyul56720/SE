"""커버리지. **통과한 벤치가 설계의 얼마를 건드렸는지 센다.**

사용자(2026-09-15): "회로 설계는 IP design house 에서 실제로 사용하는 수준이어야 한다."

## 왜 있나 -- "벤치가 통과했다" 는 IP 급에서 아무 말도 아니다

상용 IP 딜리버러블은 RTL 만이 아니라 **검증 IP 와 커버리지 리포트**가 같이 간다.
커버리지 없는 통과는 이 저장소가 내내 쫓아온 그 초록이다 -- 아무도 안 본 초록.

실측 2026-09-15. `load` 를 안 건드리는 벤치로 카운터를 돌렸다.

    PASS
    끝값=0
    ...그런데 DUT 커버리지 52.9% (분기 1/2, 줄 2/3, 토글 6/12)
    `load` 는 **한 번도 안 흔들렸다**

벤치는 초록인데 설계의 절반이 어둡다. 그래서 여기서는 **커버리지 바닥을 못 넘으면
통과가 아니다.**

## Verilator 는 커버리지를 모으고 **버린다** -- 실측

`verilator --binary --coverage` 로 지으면 잘 돌고 `coverage.dat` 이 **안 생긴다.**
생성된 main 이 `coveragep()->write()` 를 안 부르기 때문이다. 조용한 무효과다.
그래서 `--cc --main` 으로 main 만 만들게 한 뒤 그 자리에 한 줄을 넣고 짓는다.
사용자의 HDL 은 안 건드린다.

## verilator_coverage 의 요약 수치를 안 쓴다

같은 판에서 그 도구는 `Total coverage (1/12) 8.00%` 를 냈는데, 내가 센 것은 52.9%
였다. 그것이 **테스트벤치까지 섞어** 다른 잣대로 세기 때문이다. IP 리포트에 적을
숫자는 **DUT 의** 커버리지이고, 줄·분기·토글을 갈라 적어야 쓸모가 있다.
그래서 `coverage.dat` 을 직접 읽는다.
"""
from __future__ import annotations

import collections
import os
import re
import shutil
import subprocess

# coverage.dat 의 칸 이름은 `\x01키\x02값` 으로 엮여 있다(눈에 안 보이는 구분자).
_줄 = re.compile(r"^C '(.*)' (\d+)\s*$")
갈래이름 = {"v_line": "line", "v_branch": "branch", "v_toggle": "toggle",
          "v_user": "user"}


def 있나() -> bool:
    return shutil.which("verilator") is not None


def _풀기(키: str) -> dict:
    d = {}
    for 조각 in 키.split("\x01"):
        if "\x02" in 조각:
            k, v = 조각.split("\x02", 1)
            d[k] = v
    return d


def 읽기(쪽: str, dut파일들=()) -> dict:
    """coverage.dat 을 읽어 **DUT 만** 갈래별로 센다.

    {전체:%, 칸수, 덮은수, 갈래:{line:(덮,전체), ...}, 어두운칸:[...]}
    """
    셈, 덮 = collections.Counter(), collections.Counter()
    어두움 = []
    if not os.path.exists(쪽):
        return {"됐나": False, "왜": "coverage.dat 이 없다"}
    with open(쪽, encoding="utf-8", errors="replace") as f:
        for l in f:
            m = _줄.match(l.rstrip("\n"))
            if not m:
                continue
            d, n = _풀기(m.group(1)), int(m.group(2))
            파일 = d.get("f", "?")
            if dut파일들 and os.path.basename(파일) not in dut파일들:
                continue                      # 벤치는 안 센다 -- IP 리포트는 DUT 것이다
            갈래 = 갈래이름.get(d.get("page", "?").split("/")[0], "other")
            셈[갈래] += 1
            if n:
                덮[갈래] += 1
            else:
                어두움.append(f"{파일}:{d.get('l','?')} {갈래} {d.get('o', '')}".strip())
    전체칸 = sum(셈.values())
    if not 전체칸:
        return {"됐나": False,
                "왜": "DUT 에서 커버리지 칸을 하나도 못 찾았다 -- 파일 이름이 맞나"}
    덮은수 = sum(덮.values())
    return {"됐나": True, "칸수": 전체칸, "덮은수": 덮은수,
            "전체": 100.0 * 덮은수 / 전체칸,
            "갈래": {k: (덮[k], 셈[k]) for k in sorted(셈)},
            "어두운칸": 어두움}


def 말로(r: dict) -> str:
    if not r.get("됐나"):
        return str(r.get("왜", ""))
    조각 = " · ".join(f"{k} {a}/{b} ({100*a/b:.0f}%)" for k, (a, b) in r["갈래"].items())
    말 = f"DUT coverage {r['전체']:.1f}% ({r['덮은수']}/{r['칸수']}) — {조각}"
    if r["어두운칸"]:
        말 += "\ndark: " + " · ".join(r["어두운칸"][:8])
        if len(r["어두운칸"]) > 8:
            말 += f" … +{len(r['어두운칸'])-8}"
    return 말


def _돌리기(argv, 판, 초):
    try:
        r = subprocess.run(argv, cwd=판, capture_output=True, text=True,
                           errors="replace", stdin=subprocess.DEVNULL, timeout=초)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 124, f"{초}초 안에 안 끝났다"
    except OSError as e:
        return 127, f"{type(e).__name__}: {e}"


def 재기(판: str, 설계파일들, 벤치파일: str, top: str = "tb", 초: int = 300) -> dict:
    """Verilator 로 지어 돌리고 커버리지를 읽는다. {됐나, 로그, 커버리지, 왜}."""
    if not 있나():
        return {"됐나": False, "왜": "verilator 가 없다 -- `apt-get install -y verilator`"}
    파일들 = list(설계파일들) + [벤치파일]
    끝값, 로그 = _돌리기(
        ["verilator", "--cc", "--main", "--timing", "--coverage", "--exe",
         "-Wno-DECLFILENAME", "-Wno-WIDTH", "-Wno-fatal",
         "--top-module", top, "-o", "simcov"] + 파일들, 판, 초)
    if 끝값 != 0:
        return {"됐나": False, "로그": 로그, "왜": "verilator 가 모델을 못 만들었다"}
    메인 = os.path.join(판, "obj_dir", f"V{top}__main.cpp")
    if not os.path.exists(메인):
        return {"됐나": False, "로그": 로그, "왜": f"생성된 main 이 없다: V{top}__main.cpp"}
    with open(메인, encoding="utf-8") as f:
        글 = f.read()
    if "coveragep" not in 글:
        # **여기가 핵심이다.** 안 넣으면 커버리지를 모으고 버린다(실측).
        글 = 글.replace('#include "verilated.h"',
                       '#include "verilated.h"\n#include "verilated_cov.h"', 1)
        i = 글.rindex("return 0;")
        글 = 글[:i] + 'contextp->coveragep()->write("coverage.dat");\n    ' + 글[i:]
        with open(메인, "w", encoding="utf-8") as f:
            f.write(글)
    끝값, 로그2 = _돌리기(["make", "-C", "obj_dir", "-f", f"V{top}.mk"], 판, 초)
    if 끝값 != 0:
        return {"됐나": False, "로그": 로그2[-3000:], "왜": "C++ 빌드가 막혔다"}
    끝값, 나온것 = _돌리기([os.path.join(판, "obj_dir", "simcov")], 판, 초)
    dut = {os.path.basename(p) for p in 설계파일들}
    커 = 읽기(os.path.join(판, "coverage.dat"), dut)
    return {"됐나": True, "끝값": 끝값, "로그": 나온것, "커버리지": 커,
            "왜": 말로(커)}
