"""`vcd.py` -- 파형을 그린다. 그리고 **x/z 를 0 으로 그리지 않는다.**

사용자(2026-09-15): 남은 구멍 중 첫째가 파형 보기였다.

## 이 검사가 붙드는 것 -- **전 구간 x 가 깨끗해 보이나**

실측 2026-09-15. 테스트벤치에서 `rst_n` 과 `en` 을 초기화하지 않고 돌렸다.

    x$   x#   bx !        <- rst_n · en · q 가 전 구간 x
    PASS
    끝값=0

설계는 한 번도 안 돌았는데 벤치는 PASS 를 찍었다. 이때 파형에서 x 를 0(거짓)으로
칠하면 **가지런한 낮은 선**이 나오고 사람은 "리셋이 잘 걸렸다" 고 읽는다. 그림은
말이 없으므로 거짓말이 더 잘 통한다.

그래서 `vcd.py` 는 x/z 를 따로 칠하고 **글로도 센다**. 이 검사는 그 글이 실제로
나오는지를 본다 -- 그림의 색을 검사할 수는 없어도, 세어 놓은 목록은 검사할 수 있다.

## 시간축이 1000배 어긋났었다

머리말의 `$timescale` 값은 **다음 줄**에 있다(Icarus). 한 줄로만 찾다가 기본값
`1ns` 가 그대로 남아 `1ps` 를 `1ns` 로 읽었다. 그림은 멀쩡히 그려졌다 -- 눈금만
천 배 틀린 채로. 그래서 눈금을 검사한다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import rtl                                                        # noqa: E402
import vcd                                                        # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


머리 = """$date
\tTue Sep 15 2026
$end
$timescale
\t1ps
$end
$scope module tb $end
$var wire 4 ! q [3:0] $end
$var reg 1 " clk $end
$var reg 1 # en $end
$var reg 1 & tie $end
$var parameter 32 % W $end
$upscope $end
$enddefinitions $end
"""
좋은VCD = 머리 + """#0
bx !
0"
0#
1&
#5000
b0 !
1"
1#
#10000
b1 !
0"
#15000
b10 !
1"
"""
# **전 구간 x** -- 벤치는 PASS 를 찍었는데 아무것도 안 돈 판.
죽은VCD = 머리 + """#0
bx !
0"
x#
#5000
1"
#10000
0"
"""

print("\n[읽기] 머리말")
d = vcd.읽기_글(좋은VCD) if hasattr(vcd, "읽기_글") else None
판 = tempfile.mkdtemp(prefix="vcdtest-")
좋은쪽 = os.path.join(판, "good.vcd")
죽은쪽 = os.path.join(판, "dead.vcd")
open(좋은쪽, "w", encoding="utf-8").write(좋은VCD)
open(죽은쪽, "w", encoding="utf-8").write(죽은VCD)

d = vcd.읽기(좋은쪽)
ok(d["눈금"] == "1ps",
   f"**`$timescale` 값이 다음 줄에 있어도 읽는다** (1ns 로 읽으면 시간축이 1000배 어긋난다): {d['눈금']}")
이름들 = [n for n, _, _ in d["신호"]]
ok("tb.q" in 이름들 and "tb.clk" in 이름들, f"신호를 읽는다: {이름들}")
ok(not any(n.endswith(".W") for n in 이름들),
   f"**파라미터는 파형이 아니다** -- W 가 빠진다: {이름들}")
ok(d["끝시각"] == 15000, f"끝시각 {d['끝시각']}")
ok([v for _, v in d["바뀜"]["!"]] == ["x", "0", "1", "10"], "여러 비트 값을 읽는다")

print("\n[헤아리기] **전 구간 x 를 글로 잡나**")
셈 = vcd.헤아리기(vcd.읽기(죽은쪽))
ok("tb.q" in 셈["전구간xz"] and "tb.en" in 셈["전구간xz"],
   f"**전 구간 x 인 신호를 집어낸다**: {셈['전구간xz']}")
ok("tb.clk" not in 셈["전구간xz"], "멀쩡히 토글한 clk 은 안 걸린다")
말 = vcd.말로(셈)
ok("x/z for the WHOLE run" in 말, f"**글로 말한다** (그림만 믿게 두지 않는다): {말[:60]}")

셈2 = vcd.헤아리기(vcd.읽기(좋은쪽))
ok(셈2["전구간xz"] == [], f"멀쩡한 판은 조용하다: {셈2['전구간xz']}")
ok(셈2["움직인것"] == 3, f"움직인 신호를 **정확히** 센다 (q·clk·en): {셈2['움직인것']}")
ok("tb.tie" in 셈2["안변한것"],
   f"**한 번도 안 변한 신호를 따로 센다** -- 움직인 것에 섞으면 붙박이가 숨는다: {셈2['안변한것']}")
ok("never toggles" in vcd.말로(셈2), "그것도 글로 말한다")

print("\n[끼우기] `$dumpfile` 이 없으면 끼우고 **끼웠다고 말한다**")
글, 끼웠나 = vcd.덤프끼우기("module tb;\ninitial $finish;\nendmodule\n", "tb")
ok(끼웠나 and "$dumpfile" in 글 and "$dumpvars(0, tb)" in 글, "없으면 끼운다")
ok(글.rstrip().endswith("endmodule"), "`endmodule` **앞에** 끼운다 (뒤면 문법 오류다)")
글2, 끼웠나2 = vcd.덤프끼우기('module tb;\ninitial $dumpfile("a.vcd");\nendmodule\n', "tb")
ok(not 끼웠나2 and 글2.count("$dumpfile") == 1,
   "**이미 있으면 안 끼운다** -- 두 번 뜨면 뒤엣것이 앞엣것을 덮는다")

print("\n[그리기]")
png = os.path.join(판, "w.png")
r = vcd.그리기(좋은쪽, png)
ok(r["그렸나"] and os.path.getsize(png) > 1000, f"PNG 를 만든다: {r.get('왜')}")
r2 = vcd.그리기(os.path.join(판, "없는.vcd"), os.path.join(판, "x.png"))
ok(not r2["그렸나"], "**없는 파일은 '그렸다' 고 하지 않는다**")
r3 = vcd.그리기(죽은쪽, os.path.join(판, "d.png"))
ok(r3["그렸나"] and "WHOLE run" in r3["왜"],
   f"**전 구간 x 는 그림과 함께 글로도 온다**: {r3.get('왜', '')[:50]}")

print("\n[끝까지] iverilog 로 실제로 돌려서 그린다")
if not shutil.which("iverilog"):
    print("  iverilog 가 없다 -- 건너뛴다 (배포는 깐다)")
else:
    설계 = ("module counter(input wire clk, input wire rst_n, input wire en,\n"
          "               output reg [3:0] q);\n"
          "    always @(posedge clk or negedge rst_n)\n"
          "        if (!rst_n) q <= 4'd0; else if (en) q <= q + 1'b1;\n"
          "endmodule\n")
    좋은벤치 = ("`timescale 1ns/1ps\nmodule tb;\n"
             "    reg clk=0, rst_n=0, en=0; wire [3:0] q;\n"
             "    counter dut(.clk(clk), .rst_n(rst_n), .en(en), .q(q));\n"
             "    always #5 clk = ~clk;\n"
             "    initial begin\n"
             "        #12 rst_n=1; en=1; #60;\n"
             "        if (q === 4'd6) $display(\"PASS\");\n"
             "        else $display(\"FAIL: q=%0d\", q);\n"
             "        $finish;\n    end\nendmodule\n")
    png2 = os.path.join(판, "real.png")
    r = rtl.시뮬(설계, 좋은벤치, "tb", 60, png2)
    ok(r["판정"] == rtl.PASS, f"멀쩡한 카운터: {r['판정']} -- {r['왜']}")
    ok(bool(r.get("파형")) and os.path.exists(png2), f"**파형이 나온다**: {r.get('파형말')}")
    ok("injected" in (r.get("파형말") or ""),
       "`$dumpfile` 이 없던 벤치라 끼웠고 **그렇게 말한다**")
    ok("WHOLE run" not in (r.get("파형말") or ""), "멀쩡한 판에는 x 경고가 안 뜬다")

    # **이 검사의 본체.** 입력을 초기화 안 한 벤치 -- PASS 를 찍는데 전 구간 x 다.
    죽은벤치 = ("`timescale 1ns/1ps\nmodule tb;\n"
             "    reg clk=0; reg rst_n; reg en; wire [3:0] q;\n"
             "    counter dut(.clk(clk), .rst_n(rst_n), .en(en), .q(q));\n"
             "    always #5 clk = ~clk;\n"
             "    initial begin #60; $display(\"PASS\"); $finish; end\n"
             "endmodule\n")
    png3 = os.path.join(판, "dead.png")
    r = rtl.시뮬(설계, 죽은벤치, "tb", 60, png3)
    ok(r["판정"] == rtl.PASS, f"(전제) 벤치가 PASS 를 찍는다 -- 판정만으로는 못 본다: {r['판정']}")
    ok("WHOLE run" in (r.get("파형말") or ""),
       f"**그런데 파형이 일러바친다**: {(r.get('파형말') or '')[:90]}")
    for 신호 in ("rst_n", "en", "q"):
        ok(신호 in (r.get("파형말") or ""), f"  x 인 신호로 {신호} 를 이름까지 댄다")

    파형없는 = rtl.시뮬(설계, 좋은벤치, "tb", 60, "")
    ok(not 파형없는.get("파형"), "파형을 안 시키면 안 그린다 (공짜가 아니다)")

shutil.rmtree(판, ignore_errors=True)

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
ok("waveform: bool = True" in 도구글, "run_rtl 이 기본으로 파형을 그린다")
ok("_그림남기기(r[\"파형\"])" in 도구글, "**그린 그림을 답에 붙인다**")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('- "vcd.py"' in 배포, "vcd.py 가 배포 트리거 paths 에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("vcd: 전 구간 x 를 글로 잡는다 · 눈금이 맞는다 · 파라미터는 뺀다 -- 통과")
