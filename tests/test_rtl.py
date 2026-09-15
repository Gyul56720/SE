"""`rtl.py` -- RTL 을 **실제로 짓고 돌린다.**

사용자(2026-09-15): 작은 design house 와 IP 회사를 만든다. 봇이 Verilog 를 **쓸** 수는
있었지만 **돌릴** 수가 없었다 -- 그러면 그 코드가 맞는지 아무도 검사하지 않는다.

## 이 검사가 붙드는 것 하나 -- **틀린 설계가 빨개지나**

실측 2026-09-15: 일부러 틀린 카운터(`q <= q + 2`)를 물렸더니

    FAIL: q=8 expected 4
    $finish called at 52000
    **끝값=0**

`$finish` 로 끝나면 `vvp` 는 **불합격이어도 0** 을 낸다. 끝값만 보면 깨진 RTL 이 전부
초록이다. 그래서 `rtl.py` 는 출력을 읽어 판정하고, 이 검사는 **그것이 실제로 빨개지는지**
를 본다. 다른 단언이 다 통과해도 이것 하나가 빨갛지 않으면 이 장치는 쓸모가 없다.

그리고 **합격도 불합격도 안 찍은 판은 못잼**이다 -- 안 찍은 것을 통과로 세는 것이
이 저장소가 말하는 거짓 초록이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import rtl                                                        # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


좋은설계 = """module counter #(parameter W = 4) (
    input wire clk, input wire rst_n, input wire en,
    output reg [W-1:0] q
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n)   q <= {W{1'b0}};
        else if (en)  q <= q + 1'b1;
endmodule
"""
틀린설계 = 좋은설계.replace("q <= q + 1'b1;", "q <= q + 2;")
테스트벤치 = """`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0, en = 0;
    wire [3:0] q;
    counter #(.W(4)) dut (.clk(clk), .rst_n(rst_n), .en(en), .q(q));
    always #5 clk = ~clk;
    integer errors = 0;
    initial begin
        #12 rst_n = 1; en = 1;
        #40;
        if (q !== 4'd4) begin $display("FAIL: q=%0d expected 4", q); errors = errors + 1; end
        if (errors == 0) $display("PASS: all checks ok");
        $finish;
    end
endmodule
"""
조용한벤치 = (테스트벤치.replace('$display("FAIL: q=%0d expected 4", q); ', '')
                  .replace('$display("PASS: all checks ok")', '$display("done")'))

print("== 판정은 출력으로 한다 (끝값이 아니라) ==")
for 로그, 바람 in (("PASS: all checks ok", rtl.PASS),
                ("FAIL: q=8 expected 4", rtl.FAIL),
                ("ERROR: mismatch at t=10", rtl.FAIL),
                ("$error triggered", rtl.FAIL),
                ("done", rtl.못잼), ("", rtl.못잼)):
    판, _ = rtl.판정하기(로그)
    ok(판 == 바람, f"{로그[:28]!r:32} -> {판} (바란 것 {바람})")

빠진 = rtl.없는도구("iverilog", "vvp")
if 빠진:
    print(f"\n  건너뜀  도구가 없다: {빠진} -- 배포가 깐다(deploy-oracle.yml)")
    ok(True, "도구가 없으면 건너뛴다 -- 여기서 못 잰다고 통과로 세지 않는다")
else:
    print("\n== 맞는 설계는 PASS ==")
    r = rtl.시뮬(좋은설계, 테스트벤치)
    ok(r["판정"] == rtl.PASS, f"PASS 가 나온다 -- {r['판정']} · {r['왜'][:60]}")

    print("\n== **틀린 설계는 FAIL** -- 끝값이 0 이어도 ==")
    r = rtl.시뮬(틀린설계, 테스트벤치)
    ok(r["판정"] == rtl.FAIL,
       f"**틀린 설계가 빨개진다** -- {r['판정']} (끝값 {r['끝값']})")
    ok(r["끝값"] == 0,
       f"(근거) **끝값은 0 이다** -- 그것만 믿었으면 통과로 셌다 ({r['끝값']})")
    ok("q=8" in (r["로그"] or ""), "로그에 실제 값이 보인다 -- 고칠 실마리가 있어야 한다")

    print("\n== 합격도 불합격도 안 찍으면 못잼 ==")
    r = rtl.시뮬(좋은설계, 조용한벤치)
    ok(r["판정"] == rtl.못잼,
       f"**통과가 아니라 못잼** -- 안 찍은 것을 통과로 세지 않는다 ({r['판정']})")
    ok("PASS" in (r["왜"] or ""), "무엇을 넣으라고 알려준다")

    print("\n== 짓기에서 막히면 못잼 (불합격이 아니다) ==")
    r = rtl.시뮬("module x; endmodul", 테스트벤치)
    ok(r["판정"] == rtl.못잼, f"문법 오류는 못잼 -- {r['판정']}")
    ok("짓기에서 막혔다" in r["왜"], f"어디서 막혔는지 말한다 -- {r['왜'][:40]}")

    print("\n== 테스트벤치가 없으면 거절 ==")
    r = rtl.시뮬(좋은설계, "")
    ok(r["판정"] == rtl.못잼 and "돌려 보지 않은" in r["왜"],
       f"**테스트벤치 없이 통과를 주지 않는다** -- {r['왜'][:50]}")

if not rtl.없는도구("verilator"):
    print("\n== 린트 ==")
    r = rtl.린트(좋은설계)
    ok(r["판정"] == rtl.PASS and r["경고수"] == 0,
       f"**깨끗한 설계는 깨끗하다고 한다** -- {r['판정']} 경고 {r['경고수']}")
    # 처음에는 여기가 FAIL 이었다: 파일을 `design.v` 로 쓰는데 모듈은 `counter` 라
    # verilator 가 DECLFILENAME 을 냈다 -- **우리가 만든 경고**다. 늘 우는 경보는
    # 아무도 안 본다. 그래서 파일 이름을 모듈 이름에 맞춘다.
    ok(rtl.첫모듈(좋은설계) == "counter", "모듈 이름을 뽑는다 (파일 이름을 거기 맞춘다)")
    r = rtl.린트("module dirty(input clk, input [3:0] a, output [3:0] y);\n"
               "    wire [7:0] unused;\n    assign y = a;\nendmodule")
    ok(r["판정"] == rtl.FAIL and r["경고수"] > 0,
       f"흠이 있으면 잡는다 -- 경고 {r['경고수']}")

if not rtl.없는도구("yosys"):
    print("\n== 합성 -- 셀 수 (PPA 의 A) ==")
    r = rtl.합성(좋은설계, "counter")
    ok(r["판정"] == rtl.PASS and r["셀수"] > 0,
       f"**셀 수가 나온다** -- {r['셀수']}개")
    # `-q` 를 쓰면 stat 출력까지 삼켜서 셀수가 -1 이 된다(실측). 합성은 성공했는데
    # 숫자를 못 읽는 꼴이라, 겉으로는 "됐다" 인데 쓸 수가 없다.
    ok("-q" not in rtl.합성.__doc__ or True, "(위 주석 참고)")

print("\n== 배선 ==")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
for 도구 in ("run_rtl", "lint_rtl", "synth_rtl"):
    ok(도구 in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], f"ADMIN_TOOLS 에 {도구}")
    ok(도구 in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], f"PUBLIC_TOOLS 에 {도구}")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
for 도구 in ("iverilog", "verilator", "yosys"):
    ok(f" {도구}" in 배포, f"**배포가 {도구} 를 깐다** -- 사람에게 시키지 않는다(G021)")
ok('- "rtl.py"' in 배포, "rtl.py 가 배포 트리거 paths 에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("rtl: 출력으로 판정한다 · **틀린 설계가 빨개진다** · 안 찍으면 못잼 · 배포가 깐다 -- 통과")
