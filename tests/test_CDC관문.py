# -*- coding: utf-8 -*-
"""**CDC 관문(2c) -- 그리고 MTBF 수가 사소하다는 것을 숨기지 않는가.**

테이프아웃 지도 M2 의 남은 둘이었다. 둘 다 「시연뿐」 -- 수를 내는데 아무도
그 수로 막지 않았다.

## MTBF 에 문턱을 안 건 까닭 -- 재 보니 사소했다

실측 2026-09-23 (nsw_fir, 100 MHz, tau 25 ps):

    1단  log10(MTBF/s) = 168.55
    2단  log10(MTBF/s) = 342.26

우주 나이가 10^17 초다. **1단만으로 목표를 열 자리 넘게 넘는다.** 여기에
문턱을 세우면 **동기화기가 하나도 없어도 통과한다** -- 그것은 관문이 아니라
장식이다.

그 수가 사소한 까닭은 동작점이다. 뒤집히는 자리를 재 보았다.

    100 MHz  1단 168.55   ·  1 GHz  1단 10.20  ·  2 GHz  1단 0.91 (8초!)
    tau 800 ps (100 MHz)  1단 0.93

**가정 하나가 결론을 뒤집는다.** 그래서 관문이 죄는 것은 셋이다 --
선언 · 동기화 깊이(구조) · 가정의 출처. 그리고 뒤집히는 자리를 글에 적는다.

실행: python3 tests/test_CDC관문.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import designs as DES       # noqa: E402
from house import gen as GEN           # noqa: E402
from house import tapeout as TO        # noqa: E402
from house.rtl import agent as RA      # noqa: E402

문턱 = GEN.기본문턱

print("\n[1] **MTBF 가 이 동작점에서 사소한가** -- 문턱을 안 건 근거를 다시 잰다")
L1 = RA.mtbf_log10(1)
L2 = RA.mtbf_log10(2)
ok(L1 > 100, f"1단만으로 log10(MTBF/s) = {L1:.2f} — 우주 나이(10^17 s)보다 크다")
ok(L2 > L1, f"2단은 더 크다 ({L2:.2f}) — 단수 하나가 지수로 바꾼다")
ok(L1 > 20.0,
   "**목표 10^20 초를 1단이 이미 넘는다** — 여기에 문턱을 세우면 동기화기 "
   "없이도 통과한다")
# 뒤집히는 자리가 진짜 있나 -- 없으면 '사소하다' 는 말도 근거가 없다
빠름 = RA.mtbf_log10(1, f_clk=2e9, f_data=2e8, Tclk_ns=0.5)
ok(빠름 < 20.0, f"2 GHz 에서는 1단이 목표 아래다 ({빠름:.2f}) — 동작점이 정한다")
큰타우 = RA.mtbf_log10(1, tau_ps=800.0)
ok(큰타우 < 20.0, f"tau 800 ps 에서는 100 MHz 여도 목표 아래다 ({큰타우:.2f})")

print("\n[2] 관문이 선언과 대조하는가")
C = GEN.cdc점검(DES.NSW_FIR, 문턱)
ok(not C.get("오류"), f"cdc점검()이 돌았다 ({C.get('오류','')})")
ok(C["선언있나"], f"선언 파일이 있다 ({Path(C['선언파일']).name})")
ok(C["찾은수"] == 2 and C["선언수"] == 2, f"찾은 {C['찾은수']} · 선언 {C['선언수']}")
ok(not C["안선언"] and not C["빈칸"] and not C["얕은것"] and not C["출처없음"],
   f"깨진 것이 없다 (안선언 {len(C['안선언'])} · 빈칸 {len(C['빈칸'])} · "
   f"얕은것 {len(C['얕은것'])} · 출처없음 {C['출처없음']})")
ok(GEN.cdc판정(C, 문턱)[0][1], "관문이 초록이다")
ok(C["뒤집히는_MHz"] and C["뒤집히는_tau_ps"],
   f"뒤집히는 자리를 찾아 낸다 ({C['뒤집히는_MHz']} MHz · "
   f"tau {C['뒤집히는_tau_ps']} ps)")

print("\n[3] **관문이 무는가**")
성 = dict(C)


def 판정(**고침):
    return GEN.cdc판정({**성, **고침}, 문턱)


ok(not 판정(안선언=[C["찾은것"][0]])[0][1], "선언에 없는 건넘이 있으면 빨갛다")
ok(not 판정(빈칸=["wgray"])[0][1],
   "**방식이나 까닭이 빈 선언이 있으면 빨갛다** — 줄만 채우면 통과하는 자리를 막는다")
ok(not 판정(얕은것=[{"신호": "x", "단": 1}])[0][1],
   "최소 단수를 못 넘는 건넘이 있으면 빨갛다 — **이것이 진짜 구조 제약이다**")
ok(not 판정(출처없음=["tau_ps"])[0][1],
   "**출처 없는 가정이 있으면 빨갛다** — 가정 하나가 결론을 뒤집기 때문이다")
ok(not 판정(선언오류="못 읽었다")[0][1], "선언 파일을 못 읽으면 빨갛다")
ok(not GEN.cdc판정({"오류": "RTL 이 없다"}, 문턱)[0][1], "못 돌리면 빨갛다")
# **MTBF 가 작아도 그 자체로는 안 막는다** -- 문턱을 안 걸었으므로 그래야 한다
ok(판정(mtbf_log10=-5.0)[0][1],
   "MTBF 가 음수여도 그것만으로는 안 막는다 — 문턱을 안 걸었으니 그렇게 동작해야 한다")

print("\n[4] 관문 글이 사소함을 숨기지 않는가")
말 = GEN.cdc판정(C, 문턱)[0][2]
ok("문턱을 안 건다" in 말 and "사소하기 때문" in 말,
   "MTBF 에 문턱을 안 걸었다는 것과 그 까닭을 먼저 말한다")
ok("1단만 써도" in 말, "1단으로도 목표를 넘는다고 적는다 — 수가 사소한 증거다")
ok("뒤집히는 자리" in 말 and str(C["뒤집히는_MHz"]) in 말,
   f"뒤집히는 클럭을 수로 적는다 ({C['뒤집히는_MHz']} MHz)")
ok("파운드리 특성화 값이 아니다" in 말, "tau·Tw 가 가정이라고 적는다")

print("\n[5] **선언 파일을 건드려 보면** -- 늘 초록이 아니다")
원본 = Path(DES.NSW_FIR.RTL[0]).read_text(encoding="utf-8")
선언원본 = json.loads(Path(DES.NSW_FIR.RTL[0]).with_name("nsw_fir.cdc.json")
                  .read_text(encoding="utf-8"))
with tempfile.TemporaryDirectory() as 방:
    방 = Path(방)
    (방 / "nsw_fir.sv").write_text(원본, encoding="utf-8")

    class _가짜:
        top = "nsw_fir"
        RTL = [방 / "nsw_fir.sv"]
        클럭 = {"주기_ns": 10.0}

    # (가) 선언을 하나 지우면
    d = json.loads(json.dumps(선언원본))
    d["건넘"] = d["건넘"][:1]
    (방 / "nsw_fir.cdc.json").write_text(json.dumps(d, ensure_ascii=False),
                                       encoding="utf-8")
    C2 = GEN.cdc점검(_가짜(), 문턱)
    ok(len(C2["안선언"]) == 1 and not GEN.cdc판정(C2, 문턱)[0][1],
       f"선언을 하나 지우면 '선언에 없다' 하나가 나고 빨갛다 ({len(C2['안선언'])}개)")

    # (나) 가정의 출처를 지우면
    d = json.loads(json.dumps(선언원본))
    d["준안정"]["tau_ps"]["출처"] = ""
    (방 / "nsw_fir.cdc.json").write_text(json.dumps(d, ensure_ascii=False),
                                       encoding="utf-8")
    C3 = GEN.cdc점검(_가짜(), 문턱)
    ok("tau_ps" in C3["출처없음"] and not GEN.cdc판정(C3, 문턱)[0][1],
       f"가정의 출처를 지우면 빨갛다 ({C3['출처없음']})")

    # (다) tau 를 키우면 뒤집히는 자리가 따라 움직인다
    d = json.loads(json.dumps(선언원본))
    d["준안정"]["tau_ps"]["값"] = 400.0
    (방 / "nsw_fir.cdc.json").write_text(json.dumps(d, ensure_ascii=False),
                                       encoding="utf-8")
    C4 = GEN.cdc점검(_가짜(), 문턱)
    ok(C4["mtbf_log10"] < C["mtbf_log10"],
       f"tau 를 25 → 400 ps 로 키우면 MTBF 가 준다 "
       f"({C['mtbf_log10']} → {C4['mtbf_log10']}) — 가정이 수를 정한다")
    ok(C4["뒤집히는_MHz"] is None or C4["뒤집히는_MHz"] <= C["뒤집히는_MHz"],
       f"뒤집히는 클럭도 내려온다 ({C['뒤집히는_MHz']} → {C4['뒤집히는_MHz']})")

    # (라) 선언 파일이 아예 없으면
    (방 / "nsw_fir.cdc.json").unlink()
    C5 = GEN.cdc점검(_가짜(), 문턱)
    ok(not C5["선언있나"] and len(C5["안선언"]) == C5["찾은수"]
       and C5["출처없음"] and not GEN.cdc판정(C5, 문턱)[0][1],
       "선언 파일이 없으면 전부 '선언에 없다' 이고 가정도 출처가 없어 빨갛다")

print("\n[6] 테이프아웃 -- 못 하는 쪽이 남았나")
이름별 = {x["이름"]: x for x in TO.표(주인="rtl")}
for n in ("CDC 건넘 목록 · 동기화기 확인", "MTBF — 단수 근거와 가정의 출처"):
    x = 이름별.get(n)
    ok(x is not None and x["상태"] == TO.있다, f"{n} 이 「있다」 다")
t = 이름별.get("준안정 τ · Tw — 파운드리 특성화")
ok(t is not None and t["상태"] == TO.없다 and t["막나"],
   "「준안정 τ·Tw 파운드리 특성화」 는 **없는 채로 남고 여전히 막는다**")
ok("준안정 특성이 아예 없다" in (t or {}).get("메모", ""),
   "왜 없는지(우리 라이브러리에 준안정 특성이 없다) 적어 둔다")
ok(TO._관문있나("2c") and "2c" in GEN.관문번호들(), "관문 2c 가 있다")
ok(not TO.검사() and not TO.거짓증거() and not TO.안걸린붙듦(),
   f"계획에 흠이 없다 ({TO.검사()})")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
