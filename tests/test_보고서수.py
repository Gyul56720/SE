# -*- coding: utf-8 -*-
"""**잘린 값이 잰 값처럼 보이지 않는가 -- 그리고 같은 양이 두 값이 아닌가.**

실측 2026-09-22, `20260922_EthanRoss_RTL.pdf` (RTL-RPT) 에서 난 두 가지:

    Table 12   단수 2·3·4 의 MTBF 가 전부 `1e+300`
    Fig 20     그 값을 그려서 2에서 4까지 **평평한 선**
               그 그림의 설명: «단수 하나가 MTBF 를 지수로 바꾼다»
               -- 설명이 제가 붙은 그림에게 반박당하고 있었다

    표지       `Report build 0.0 s`
    부록 A     `보고서 생성 시간 38.3 s`     <- 같은 양, 두 값

`1e+300` 은 잰 값이 아니라 **float64 를 넘어 잘린 자리를 가리키는 표지**다.
그런데 표에서는 잰 값과 똑같이 생겼다. MTBF 는 2단에서 이미 float64 를
넘는데 **지수는 안 넘는다** -- 지수로 셈하고 지수로 보인다.

실행: python3 tests/test_보고서수.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house.rtl.agent import mtbf, mtbf_log10      # noqa: E402

# ============================================ 1. 지수는 안 잘린다
_L = [mtbf_log10(n) for n in (1, 2, 3, 4)]
ok(len(set(round(x, 6) for x in _L)) == 4,
   f"**단수마다 다른 값이 난다** — 셋이 같던 자리다 ({[round(x,1) for x in _L]})")
_계단 = [round(_L[i + 1] - _L[i], 6) for i in range(3)]
ok(len(set(_계단)) == 1 and _계단[0] > 0,
   f"**자리수가 단수마다 같은 폭으로 오른다** — 지수로 바뀐다는 말이 "
   f"그림에서 보인다 (+{_계단[0]:.2f} 씩)")
ok(all(math.isfinite(x) for x in _L), "지수는 float64 안에 든다")

# ============================================ 2. 가짜 수를 안 돌려준다
ok(mtbf(1) > 0 and math.isfinite(mtbf(1)),
   f"작은 단수에서는 값이 난다 ({mtbf(1):.3g})")
ok(math.isinf(mtbf(2)),
   "**넘으면 `inf`** — `1e300` 같은 **그럴듯한 수**를 안 돌려준다")
ok(not math.isclose(mtbf(2), 1e300),
   "«1e+300» 은 잰 값이 아니었다 — 이제 안 난다")

_소스 = (뿌리 / "house" / "rtl" / "agent.py").read_text(encoding="utf-8")
ok("return 1e300" not in _소스, "**지웠다**: `return 1e300`")
ok(">= 1e300" not in _소스, "**지웠다**: `>= 1e300` 으로 잘린 자리를 가려내던 비교")
ok("mtbf_log10" in _소스 and 'x["log10"]' in _소스,
   "그림과 표가 **자리수**를 쓴다")

# ============================================ 3. 같은 양이 두 값이 아니다
from house import report as RPT                   # noqa: E402
from house import people                          # noqa: E402

_P = people.find("ethan")
ok(_P is not None, "사람을 찾는다 (보고서를 지으려면 필요하다)")
if _P is not None:
    from house import viz as V                 # noqa: E402

    def _보고서(업무초=None):
        # 이 저장소는 **그림 없는 보고서를 안 낸다** -- 한 장 넣어 준다.
        r = RPT.보고서(_P, "검사용 보고서", "검사 IP", "부제")
        r.그림(V.빈그림("검사용"), "검사용 그림.", "test")
        if 업무초 is not None:
            r.업무초 = 업무초
            r.잰것 = [("에이전트 실행 시간 (도구 포함)", 업무초, "s", "실측")]
        return r

    R = _보고서(38.3)
    h = R.html()
    ok("Tool runtime: 38.3 s" in h,
       "**업무초를 주면 표지가 「Tool runtime」으로 그 수를 적는다**")
    ok("Report build" not in h,
       "**「Report build」가 안 나온다** — 보고서 객체를 만든 뒤 흐른 시간은 "
       "아무것도 안 말한다")
    h2 = _보고서().html()
    ok("Report build" in h2 and "Tool runtime" not in h2,
       "안 주면 **「Report build」라고 이름을 바꿔** 적는다 — 도구 시간인 척하지 않는다")


# **글자가 아니라 「그 자리에」 있는지 본다.** 주석과 docstring 은 옛 이름을
# 기록으로 인용해 두므로(무엇이 틀렸었는지 남기려고) 그냥 찾으면 거짓 빨간불이 난다.
for _파 in ("house/rtl/agent.py", "house/dv/agent.py"):
    _글 = (뿌리 / _파).read_text(encoding="utf-8")
    ok('("보고서 생성 시간"' not in _글,
       f"**{_파}: 부록 줄의 이름을 고쳤다** — 「보고서 생성 시간」이 아니라 "
       f"「에이전트 실행 시간 (도구 포함)」이다")
    ok('R.업무초 = ' in _글, f"{_파}: 표지에 제 실행 시간을 넘긴다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("보고서수: 지수로 잰다 · 가짜 수 없다 · 같은 양이 한 값이다 -- 통과")
