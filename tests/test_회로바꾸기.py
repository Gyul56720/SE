# -*- coding: utf-8 -*-
"""**다섯 명이 회로를 바꿔 돌 수 있는가 -- 실제로 돌려서 본다.**

실측 2026-09-22. 사용자가 MERA 스펙을 넣고 다섯 명을 돌렸더니
`NSW-FIR v1.0 프런트엔드 설계 보고서` 13쪽이 왔다. 보고서 자체는 진짜였다 --
verilator · iverilog · yosys 가 실제로 돌았고 lint 가 진짜 버그를 잡았다.
**회로가 달랐을 뿐이다.**

끊긴 데가 세 겹이었고 마지막 겹이 이것이었다: 다섯 에이전트의 `돌리기()` 가
**`회로=` 를 아예 안 받았다**(다섯 다 `False`). 제목까지 `NSW-FIR v1.0` 으로
박혀 있어서, 받는 사람은 **무엇을 읽고 있는지 알 수 없었다.**

여기서는 **글자를 안 본다.** 붙박이와 같은 RTL 을 가리키되 이름만 다른 설계를
등록부에 넣고 **에이전트를 끝까지 돌려서**, 나온 문서의 제목이 그 이름을
따라가는지 본다. 서명에 `회로=` 가 있다는 것만으로는 아무것도 증명되지 않는다 --
첫 판이 그 인자를 받아 놓고 안 쓸 수도 있다.

느린 둘(dft · dv)은 여기서 안 돌린다. 80 초 · 70 초가 걸려 빠른 검사를 막는다.
그 둘은 `회로되는사람들()` 로 **받는지만** 보고, 실제 돌리기는 CI 가 한다.

실행: python3 tests/test_회로바꾸기.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import designs as DES     # noqa: E402
from house import run as RUN         # noqa: E402

# ---- 다섯이 회로를 받나 (서명) ----
받나 = RUN.회로되는사람들()
ok(set(받나) == {"rtl", "dv", "syn", "dft", "pd"}, "다섯 직무를 다 묻는다")
못받는 = sorted(k for k, v in 받나.items() if not v)
ok(not 못받는, f"**다섯 다 `회로=` 를 받는다** (못 받는 것: {못받는 or '없음'})")

# ---- 이름만 다른 설계를 넣고 **끝까지 돌린다** ----
가짜 = DES.설계(키="테스트회로", 이름="ZZTEST-9 v9.9",
             top=DES.NSW_FIR.top, RTL=list(DES.NSW_FIR.RTL),
             TB=DES.NSW_FIR.TB, 파라=dict(DES.NSW_FIR.파라),
             SDC=DES.NSW_FIR.SDC, UPF=DES.NSW_FIR.UPF)
옛등록부 = DES.등록부길
잰것 = {}
with tempfile.TemporaryDirectory() as d:
    DES.등록부길 = Path(d) / "designs.json"
    DES.등록부길.write_text(json.dumps([가짜.사전()], ensure_ascii=False, default=str),
                        encoding="utf-8")
    ok(DES.찾기("테스트회로").이름 == "ZZTEST-9 v9.9", "등록부에서 그 회로를 찾는다")

    import importlib                                          # noqa: E402
    for 키, 모듈, 인자 in (("rtl", "house.rtl.agent", (True,)),
                        ("syn", "house.syn.agent", (True,))):
        t0 = time.time()
        try:
            r = importlib.import_module(모듈).돌리기(*인자, 회로="테스트회로")
        except Exception as e:                                # noqa: BLE001
            ok(False, f"{키}: 돌다가 죽었다 -- {type(e).__name__}: {e}")
            continue
        잰것[키] = r
        html = Path(str(r["pdf"]).replace(".pdf", ".html"))
        글 = html.read_text(encoding="utf-8") if html.exists() else ""
        머리 = 글.split("</h1>")[0].split("<h1")[-1] if "<h1" in 글 else ""
        ok("ZZTEST-9 v9.9" in 머리,
           f"**{키}: 제목이 그 회로 이름을 따라간다** ({time.time()-t0:.1f}s · {머리[-52:]})")
        ok("NSW-FIR" not in 머리,
           f"**{키}: 딴 회로 이름이 안 남아 있다** -- 그것이 그날의 사고다")
        ok((r.get("쪽") or 0) >= 3 and (r.get("그림수") or 0) >= 1,
           f"{키}: 빈 보고서가 아니다 ({r.get('쪽')}쪽 · 그림 {r.get('그림수')})")
DES.등록부길 = 옛등록부

ok(DES.찾기(None).키 == "fir", "회로를 안 대면 붙박이로 돌아온다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("회로바꾸기: 다섯이 회로를 받는다 · 돌려서 제목이 따라간다 -- 통과")
