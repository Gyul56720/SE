# -*- coding: utf-8 -*-
"""**다섯 에이전트가 전부 회로를 가리는가 -- 기계가 훑는다.**

사용자: *"fir 만든걸 mera에 못쓰는건 제대로된 에이전트가 아니야"*

이 병은 **한 파일의 버그가 아니라 꼴**이다. 실측 2026-09-23 에 다섯 에이전트를
한꺼번에 훑어 보니 같은 것이 흩어져 있었다.

    rtl/agent.py   SIM.돌리기 4개 중 3개가 `설계=` 를 안 넘긴다
    syn/agent.py   SIM.돌리기 1개 · SYN.합성 1개가 안 넘긴다
                   그리고 `d = SIM.돌리기(...)` 가 **설계 객체 `d` 를 덮었다**
    여러 곳         `{"TAPS": 8, "STAGES": 3, "GATE_POLICY": 1}` 이 박혀 있다

`설계=` 를 안 넘기면 `sim.빌드()` 가 `DES.NSW_FIR` 로 떨어진다 -- **어떤 회로를
넘겨도 nsw_fir 을 돈다.** 그런데 보고서에는 그 회로 이름이 찍힌다.

**내가 눈으로 훑다가 Ethan 쪽을 놓쳤다**(PR #381 에서 스윕 라벨만 고쳤다).
그래서 사람이 아니라 기계가 훑는다. 새 에이전트가 생겨도 이 검사가 문다.

실행: python3 tests/test_에이전트범용.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
sys.path.insert(0, str(뿌리 / "tests"))

import _소스보기                                             # noqa: E402

_소스보기.자기검사()

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 호출들(글: str, 이름: str) -> list:
    """`이름(` 호출의 인자 글을 괄호를 세어 잘라 낸다."""
    난것 = []
    for m in re.finditer(re.escape(이름) + r"\(", 글):
        i, 깊이 = m.end(), 1
        while i < len(글) and 깊이:
            깊이 += (글[i] == "(") - (글[i] == ")")
            i += 1
        난것.append(글[m.end():i - 1])
    return 난것


# 이 함수들은 회로를 안 넘기면 **조용히 nsw_fir 로 떨어진다**.
_회로받는함수 = ("SIM.돌리기", "SIM.빌드", "SYN.합성")

# 이 회로의 파라미터 이름. 에이전트 코드에 **값과 함께 박혀** 있으면 안 된다.
_FIR이름 = ("TAPS", "STAGES", "GATE_POLICY", "CDC_STAGES", "ACCW", "CNTW")

_에이전트들 = sorted((뿌리 / "house").glob("*/agent.py"))
ok(len(_에이전트들) >= 5, f"에이전트를 찾는다 ({[f.parent.name for f in _에이전트들]})")

for f in _에이전트들:
    누구 = f.parent.name
    산 = _소스보기.산주장(f.read_text(encoding="utf-8"))

    # ---- 1. 회로를 넘기나
    빠진 = []
    for 이름 in _회로받는함수:
        for c in 호출들(산, 이름):
            if "설계" not in c:
                빠진.append(f"{이름}({' '.join(c.split())[:44]}…)")
    ok(not 빠진,
       f"**{누구}: 모든 `{'/'.join(_회로받는함수)}` 가 `설계=` 를 넘긴다**"
       + (f" — 빠진 것 {len(빠진)}개: {빠진[:2]}" if 빠진 else ""))

    # ---- 2. FIR 파라미터를 값과 함께 박아 두지 않았나
    #  `{"TAPS": 8}` · `{"GATE_POLICY": 정책}` 같은 꼴만 잡는다. 글 속의 이름
    #  (설명·열 제목)은 회로를 안 가리므로 건드리지 않는다.
    박힌 = re.findall(r'\{\s*"(' + "|".join(_FIR이름) + r')"\s*:', 산)
    ok(not 박힌,
       f"**{누구}: 파라미터 이름을 값과 함께 안 박는다**"
       + (f" — {sorted(set(박힌))}" if 박힌 else ""))

    # ---- 3. 표지 시간이 부록 시간과 같은가
    ok("R.업무초" in 산, f"{누구}: 표지에 제 실행 시간을 넘긴다")

    # ---- 4. 설계 변수를 덮어쓰지 않나
    #  `d = SIM.돌리기(...)` 가 설계 객체 `d` 를 가려서, 바로 그 줄에서
    #  `설계=d` 를 못 넘겼다 (syn/agent.py 에서 실제로 그랬다).
    #  **그 이름이 이 파일에서 설계로 쓰일 때만** 잡는다. `dv/agent.py` 는
    #  설계를 `d0` 에 담고 `d` 는 결과 변수로 쓴다 -- 그것은 버그가 아니다.
    #  (첫 판은 이름만 보고 `dv` 를 빨갛게 냈다. 거짓 빨간불도 검사를 못 믿게 만든다.)
    덮 = [n for n in set(re.findall(r"^\s*(\w+)\s*=\s*(?:SIM|SYN)\.", 산, re.M))
        if re.search(rf"설계\s*=\s*{re.escape(n)}\b", 산)]
    ok(not 덮, f"**{누구}: 설계 변수를 시뮬 결과로 안 덮는다**"
              + (f" — {덮}" if 덮 else ""))

# ============================================ 5. 공용 자리가 하나다
from house import designs as DES                             # noqa: E402

_d = DES.찾기("fir")
_기본 = DES.파라기본(_d)
ok(_기본.get("TAPS") == 8 and _기본.get("GATE_POLICY") == 1,
   f"`designs.파라기본()` 이 RTL 톱 파라미터를 읽는다 ({len(_기본)}개)")
ok(DES.정책파라(_기본) == "GATE_POLICY",
   f"`designs.정책파라()` 가 정책 깃발을 찾는다 ({DES.정책파라(_기본)})")
ok(DES.정책파라({"DW": 16, "TAPS": 8}) is None,
   "**정책 깃발이 없으면 None** — 없는 A/B 를 지어내지 않는다")
ok(DES.파라기본(type("X", (), {"파라": {}, "RTL": [], "top": ""})()) == {},
   "RTL 이 없으면 빈 dict — 되돌이값으로 FIR 을 넣지 않는다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("에이전트범용: 다섯 에이전트가 다 회로를 가린다 -- 통과")
