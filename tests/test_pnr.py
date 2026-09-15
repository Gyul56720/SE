"""`pnr.py` -- 배치·배선·타이밍. **목표 없는 초록을 통과로 세지 않는다.**

사용자(2026-09-15): design house 의 남은 구멍 중 셋째.

## 이 검사가 붙드는 것 -- **기본값 12MHz 에 PASS 한 것**

실측 2026-09-15 (nextpnr-ice40 0.6). 목표를 안 주고 돌리면

    Info: Max frequency for clock 'clk': 194.33 MHz (**PASS at 12.00 MHz**)
    끝값=0

`12.00 MHz` 는 **사용자가 준 목표가 아니라 nextpnr 의 기본값**이다. 100MHz 로 쓸
설계가 12MHz 에 PASS 했다는 말을 초록으로 읽으면 그대로 속는다. 무엇에 견주어
통과인지 없는 통과는 통과가 아니다.

## 깃발 하나가 빨간불을 초록으로 만든다

    목표 250MHz                      끝값 1   ERROR: ... (FAIL at 250.00 MHz)
    목표 250MHz + --timing-allow-fail 끝값 0   Warning: ... (FAIL at 250.00 MHz)

그래서 그 깃발을 절대 안 붙인다. 이 검사가 명령줄을 들여다본다.

## Fmax 줄은 두 번 나온다

    190.33 MHz   <- 배치 중 추정
    194.33 MHz   <- 배선까지 끝난 최종

앞엣것을 읽으면 실제보다 **낮게** 본다 -- 그러면 멀쩡한 설계가 FAIL 로 찍힌다.
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import pnr                                                        # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


두번 = ("Info: Max frequency for clock 'clk$glb': 190.33 MHz (PASS at 100.00 MHz)\n"
       "Info: Device utilisation:\n"
       "Info: \t         ICESTORM_LC:    50/ 1280     3%\n"
       "Info: \t        ICESTORM_RAM:     0/   16     0%\n"
       "Info: \t               SB_IO:    10/  112     8%\n"
       "Info: Max frequency for clock 'clk$glb': 194.33 MHz (PASS at 100.00 MHz)\n")
깨짐 = ("Info: Max frequency for clock 'clk$glb': 190.33 MHz (FAIL at 250.00 MHz)\n"
       "ERROR: Max frequency for clock 'clk$glb': 194.33 MHz (FAIL at 250.00 MHz)\n")
안들어감 = "ERROR: Unable to find a placement location for cell 'q[930]$sb_io'\n"
클럭없음 = "Info: Device utilisation:\nInfo: Max delay <async> -> <async>: 1.2 ns\n"

print("\n[Fmax] **마지막 것을 쓴다**")
c = pnr.클럭들(두번)
ok(len(c) == 1, f"같은 클럭은 한 줄로: {len(c)}")
ok(c and c[0]["Fmax"] == 194.33,
   f"**배선 후 최종값을 쓴다** (배치 중 추정 190.33 을 쓰면 멀쩡한 설계가 FAIL 이 된다): "
   f"{c[0]['Fmax'] if c else None}")
ok(c and c[0]["목표"] == 100.0, "목표도 읽는다")

print("\n[쓰임] 0 인 칸은 안 적는다")
u = pnr.쓰임(두번)
칸들 = {x["칸"]: x for x in u}
ok("ICESTORM_LC" in 칸들 and 칸들["ICESTORM_LC"]["쓴것"] == 50, f"LC 50: {칸들.get('ICESTORM_LC')}")
ok(칸들["ICESTORM_LC"]["다"] == 1280, "소자 전체 칸 수도 읽는다")
ok("ICESTORM_RAM" not in 칸들, "안 쓴 칸은 안 적는다")

print("\n[판정]")
판, 왜, _ = pnr.판정하기(두번, 100)
ok(판 == pnr.PASS, f"목표를 넘으면 PASS: {판}")
판, 왜, _ = pnr.판정하기(깨짐, 250)
ok(판 == pnr.FAIL, f"목표에 모자라면 FAIL: {판}")
ok("22" in 왜 or "모자람" in 왜, f"얼마나 모자란지 말한다: {왜[:70]}")
판, 왜, _ = pnr.판정하기(안들어감, 100)
ok(판 == pnr.못잼 and "안 들어간다" in 왜, f"칩에 안 들어가면 못잼: {판} / {왜[:40]}")
판, 왜, _ = pnr.판정하기(클럭없음, 100)
ok(판 == pnr.못잼 and "클럭" in 왜, f"클럭이 없으면 못잼: {판} / {왜[:40]}")

print("\n[목표] **이 검사의 본체** -- 목표 없는 통과는 통과가 아니다")
설계 = """module top (input wire clk, input wire rst_n, output wire [7:0] led);
    reg [23:0] c; reg [7:0] acc;
    always @(posedge clk)
        if (!rst_n) begin c <= 0; acc <= 0; end
        else begin c <= c + 1; acc <= acc + c[7:0] + (c[15:8] ^ c[23:16]); end
    assign led = acc;
endmodule
"""
for 목표 in (0, -5, 0.0):
    r = pnr.맞춰보기(설계, "top", 목표, "hx1k", 초=20)
    ok(r["판정"] == pnr.못잼,
       f"**목표 {목표} -> 못잼** (nextpnr 는 기본값 12MHz 에 PASS 를 낸다): {r['판정']}")
r = pnr.맞춰보기(설계, "top", 0, "hx1k", 초=20)
ok("12" in r["왜"], f"까닭이 그 12MHz 를 짚는다: {r['왜'][:70]}")
ok(r["로그"] == "", "**돌리지도 않는다** -- 돌리면 초록이 돌아온다")

ok(pnr.맞춰보기("", "top", 100)["판정"] == pnr.못잼, "빈 설계 -> 못잼")
ok(pnr.맞춰보기(설계, "top", 100, "없는칩")["판정"] == pnr.못잼, "모르는 칩 -> 못잼")

print("\n[깃발] `--timing-allow-fail` 을 절대 안 붙인다")
소스 = (뿌리 / "pnr.py").read_text(encoding="utf-8")
쓴자리 = [l for l in 소스.splitlines()
        if "timing-allow-fail" in l and not l.strip().startswith("#")]
ok(not 쓴자리,
   f"**그 깃발 하나로 끝값 1 이 0 이 된다** (실측) -- 명령줄에 없다: {쓴자리}")
ok("--pcf-allow-unconstrained" in 소스, "핀 제약 없는 설계는 돌 수 있게 둔다(이건 타이밍과 무관)")

print("\n[끝까지] 진짜로 배치·배선한다")
if pnr.없는도구("yosys", "nextpnr-ice40"):
    print("  yosys/nextpnr 가 없다 -- 건너뛴다 (배포는 깐다)")
else:
    r = pnr.맞춰보기(설계, "top", 100, "hx1k", 초=400)
    ok(r["판정"] == pnr.PASS, f"100MHz 는 넘는다: {r['판정']} -- {r['왜'][:60]}")
    ok(r["Fmax"] > 100, f"Fmax 를 실제로 잰다: {r['Fmax']}")
    ok(any(u["칸"] == "ICESTORM_LC" for u in r["쓰임"]), f"쓰임을 읽는다: {r['쓰임']}")
    ok("Fmax" in pnr.말로(r) and "ICESTORM_LC" in pnr.말로(r), f"말로 옮긴다: {pnr.말로(r)[:70]}")

    r2 = pnr.맞춰보기(설계, "top", 250, "hx1k", 초=400)
    ok(r2["판정"] == pnr.FAIL, f"**250MHz 는 못 맞춘다 -- 빨개진다**: {r2['판정']}")
    ok(abs(r2["Fmax"] - r["Fmax"]) < 1,
       f"같은 설계면 목표가 달라도 Fmax 는 같다: {r['Fmax']} vs {r2['Fmax']}")

    r3 = pnr.맞춰보기("module c(input a, output b); assign b = ~a; endmodule\n",
                   "c", 50, "hx1k", 초=200)
    ok(r3["판정"] == pnr.못잼, f"클럭 없는 설계 -> 못잼: {r3['판정']}")

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
ok("def place_rtl(" in 도구글, "bot_tools 에 place_rtl")
ok("target_mhz: float," in 도구글,
   "**target_mhz 에 기본값이 없다** -- 안 주면 부를 수 없게 한다")
ok("place_rtl" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에")
ok("place_rtl" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], "PUBLIC_TOOLS 에")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok(" nextpnr-ice40" in 배포, "**배포가 nextpnr 를 깐다** -- 사람에게 시키지 않는다(G021)")
ok('- "pnr.py"' in 배포, "pnr.py 가 배포 트리거 paths 에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("pnr: 목표 없는 초록을 안 센다 · 최종 Fmax 를 쓴다 · allow-fail 을 안 쓴다 -- 통과")
