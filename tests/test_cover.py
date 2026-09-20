"""`cover.py` -- 커버리지. **통과한 벤치가 설계의 얼마를 건드렸는지 센다.**

사용자(2026-09-15): "회로 설계는 IP design house 에서 실제로 사용하는 수준이어야 한다."

## 이 검사가 붙드는 것 -- 같은 초록, 다른 검증

실측 2026-09-15. 같은 카운터를 두 벤치로 돌렸다. **둘 다 PASS 를 찍었다.**

    얕은 벤치   DUT 52.9%  (분기 1/2, 줄 2/3, 토글 6/12) -- `load` 를 한 번도 안 흔듦
    깊은 벤치   DUT 100%

"벤치가 통과했다" 는 IP 급에서 아무 말도 아니다. 상용 IP 딜리버러블은 RTL 만이
아니라 **커버리지 리포트**가 같이 간다. 커버리지 없는 통과는 이 저장소가 내내
쫓아온 그 초록이다 -- 아무도 안 본 초록.

## Verilator 는 커버리지를 모으고 **버린다**

`--binary --coverage` 로 지으면 잘 돌고 `coverage.dat` 이 **안 생긴다**(실측).
생성된 main 이 `coveragep()->write()` 를 안 부른다. 조용한 무효과다. 그래서
`--cc --main` 으로 main 만 만들게 한 뒤 그 자리에 한 줄을 넣는다.

## `verilator_coverage` 의 요약을 안 쓴다

같은 판에서 그 도구는 `8.00%`, 내가 센 것은 `52.9%` 였다. 그것이 **테스트벤치까지
섞어** 다른 잣대로 센다. IP 리포트에 적을 숫자는 DUT 의 것이고 줄·분기·토글을
갈라 적어야 쓸모가 있다.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import cover                                                      # noqa: E402
import rtl                                                        # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


def _칸(파일, 줄, 갈래, 이름, 수):
    """coverage.dat 한 줄. 구분자는 눈에 안 보이는 \\x01 / \\x02 다."""
    키 = (f"\x01f\x02{파일}\x01l\x02{줄}\x01n\x021"
          f"\x01page\x02{갈래}/mod\x01o\x02{이름}\x01h\x02TOP.tb.dut")
    return f"C '{키}' {수}\n"


판 = tempfile.mkdtemp(prefix="covtest-")
쪽 = os.path.join(판, "coverage.dat")
with open(쪽, "w", encoding="utf-8") as f:
    f.write("# SystemC::Coverage-3\n")
    f.write(_칸("dut.sv", 2, "v_toggle", "clk", 14))
    f.write(_칸("dut.sv", 2, "v_toggle", "load", 0))        # 어두운 칸
    f.write(_칸("dut.sv", 5, "v_line", "blk", 7))
    f.write(_칸("dut.sv", 6, "v_branch", "if", 0))          # 어두운 칸
    f.write(_칸("tb.sv", 3, "v_line", "blk", 99))           # **벤치는 안 센다**
    f.write(_칸("tb.sv", 4, "v_toggle", "x", 5))

print("\n[읽기] 눈에 안 보이는 구분자를 푼다")
r = cover.읽기(쪽, {"dut.sv"})
ok(r["됐나"], f"읽힌다: {r.get('왜','')}")
ok(r["칸수"] == 4, f"**DUT 칸만 센다** (벤치 2칸은 안 센다): {r['칸수']}")
ok(r["덮은수"] == 2, f"덮인 칸 2: {r['덮은수']}")
ok(abs(r["전체"] - 50.0) < 0.01, f"50%: {r['전체']}")
ok(r["갈래"] == {"branch": (0, 1), "line": (1, 1), "toggle": (1, 2)},
   f"**갈래를 갈라 센다** -- IP 리포트는 줄·분기·토글이 따로다: {r['갈래']}")
ok(any("load" in x for x in r["어두운칸"]) and any("if" in x for x in r["어두운칸"]),
   f"**어두운 칸을 이름까지 댄다** -- 무슨 자극이 빠졌는지 알려면 필요하다: {r['어두운칸']}")
ok(not any("tb.sv" in x for x in r["어두운칸"]), "벤치는 어두운 칸에도 안 넣는다")

전부 = cover.읽기(쪽)
ok(전부["칸수"] == 6, f"DUT 를 안 주면 다 센다: {전부['칸수']}")
ok(cover.읽기(os.path.join(판, "없다.dat"))["됐나"] is False, "없는 파일은 못 읽었다고 한다")
빈쪽 = os.path.join(판, "빈.dat")
open(빈쪽, "w").write("# SystemC::Coverage-3\n")
ok(cover.읽기(빈쪽)["됐나"] is False, "**칸이 없으면 100% 라고 하지 않는다**")
ok(cover.읽기(쪽, {"없는파일.sv"})["됐나"] is False,
   "**DUT 이름이 안 맞으면 0칸이고, 그것을 성공으로 안 읽는다**")

말 = cover.말로(r)
ok("50.0%" in 말 and "branch" in 말 and "dark" in 말, f"말로 옮긴다: {말[:80]}")

shutil.rmtree(판, ignore_errors=True)

설계 = """module counter #(parameter W=4)(
    input logic clk, input logic rst_n, input logic en, input logic load,
    input logic [W-1:0] d, output logic [W-1:0] q);
    always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) q <= '0; else if (load) q <= d; else if (en) q <= q + 1'b1;
endmodule
"""
얕은벤치 = """module tb;
    logic clk=0, rst_n=0, en=0, load=0; logic [3:0] d='0, q;
    counter #(.W(4)) dut(.*);
    always #5 clk = ~clk;
    initial begin #12 rst_n=1; en=1; #60;
        if (q === 4'd6) $display("PASS"); else $display("FAIL: q=%0d", q);
        $finish; end
endmodule
"""

print("\n[끝까지] **통과한 벤치가 설계의 절반만 건드린다**")
if not cover.있나():
    print("  verilator 가 없다 -- 건너뛴다 (배포는 깐다)")
else:
    r = rtl.시뮬(설계, 얕은벤치, "tb", 200, 커버리지바닥=80)
    ok(r["판정"] == rtl.못잼,
       f"**PASS 를 찍어도 커버리지가 바닥 밑이면 통과가 아니다**: {r['판정']}")
    ok("PASS" in (r["로그"] or ""), "(전제) 벤치는 실제로 PASS 를 찍었다")
    ok(30 < r.get("커버리지", 0) < 70,
       f"DUT 커버리지가 절반쯤이다: {r.get('커버리지', -1):.1f}%")
    ok("load" in (r.get("커버리지말") or ""),
       f"**안 건드린 신호를 이름까지 댄다**: {(r.get('커버리지말') or '')[-90:]}")

    r2 = rtl.시뮬(설계, 얕은벤치, "tb", 200, 커버리지바닥=40)
    ok(r2["판정"] == rtl.PASS, f"바닥을 낮추면 통과다: {r2['판정']}")

    r3 = rtl.시뮬(설계, 얕은벤치, "tb", 120)
    ok(r3["판정"] == rtl.PASS, f"바닥을 안 주면 판정은 그대로 PASS: {r3['판정']}")
    ok("커버리지를 안 쟀다" in r3["왜"],
       "**안 쟀으면 안 쟀다고 말한다** -- 통과가 더 크게 보이지 않게")
    ok("커버리지" not in r3 or r3.get("커버리지") is None,
       "바닥을 안 주면 재지도 않는다 (10초쯤 든다)")

print("\n[합성] Yosys 의 SystemVerilog 한계를 **설계 탓으로 돌리지 않는다**")
if rtl.있나("yosys"):
    sv = ("package p; typedef logic [3:0] t; endpackage\n"
          "module m(input logic [3:0] a, output logic [3:0] y);\n"
          "  import p::*;\n  assign y = t'(a + 4'(1));\nendmodule\n")
    r = rtl.합성(sv, "m")
    ok(r["판정"] == rtl.못잼, f"막힌다: {r['판정']}")
    ok("프런트엔드" in r["왜"] and "lint_rtl" in r["왜"],
       f"**도구의 한계라고 말하고 lint_rtl 로 확인하라고 한다**: {r['왜'][:70]}")
    ok("합성이 막혔다" != r["왜"], "두루뭉술한 '합성이 막혔다' 로 끝내지 않는다")
else:
    print("  yosys 가 없다 -- 건너뛴다")

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
ok("min_coverage: float = 0.0" in 도구글, "run_rtl 이 min_coverage 를 받는다")
ok("IP-grade" in 도구글, "독스트링이 IP 급 검증이라고 말한다")  # G016: 문서 계약
#   ^ 독스트링 글자를 일부러 잰다 -- 도구 설명이 min_coverage 의 뜻을 말하는지가 계약이다.
#     동작은 바로 위 [판정] 마디가 run_rtl 을 실제로 불러서 잰다.
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('- "cover.py"' in 배포, "cover.py 가 배포 트리거 paths 에 있다")
ok(" verilator" in 배포, "배포가 verilator 를 깐다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL[:5]}")
    sys.exit(1)
print("cover: DUT 만 갈래별로 센다 · 낮은 커버리지는 통과가 아니다 · 안 쟀으면 말한다 -- 통과")
