"""`ipflow.py` -- IP 사인오프 관문. **못 잰 관문을 통과로 세지 않는다.**

사용자(2026-09-15): "IP & design house 의 실제 현업 process 를 담당해야 해."

## 이 검사가 붙드는 것

사인오프 리포트는 관문 일곱 개를 한 낱말로 줄인다. 그 줄이는 자리가
`ipflow.모으기()` 이고, **거기서 못잼을 통과로 세면 리포트 전체가 거짓말이 된다.**
도구를 안 돌리는 순수 함수라 검사가 곧바로 붙든다.

## 첫 판이 낸 거짓 빨강 둘 -- 실측 2026-09-15

*하나.* `$past` 를 쓴 설계를 넣었더니 **SIM 이 FAIL** 로 찍혔다.

    iverilog exit=0
    vvp:  design.v:15: Error: System task/function $past() is not defined by any module.
          sim.vvp: Program not runnable, 1 errors.          vvp exit=1

**시뮬레이션은 한 걸음도 안 갔는데 "설계가 틀렸다" 고 말한 것이다.** 판정이 출력의
`Error` 글자에 걸렸다. 거짓 초록의 거울상이고, 사인오프에서는 더 나쁘다 -- 고칠 데가
아닌 곳을 가리킨다. `$fatal` 도 끝값 1 이라 **끝값으로는 못 가른다.**

*둘.* `assert` 를 단 설계가 **TIMING 을 영영 못 지났다.**

    ERROR: cell type '$assert' is unsupported
           (instantiated as 'rst_n_SB_LUT4_I3_1_O_SB_DFF_D_Q_$assert_EN')

성질을 단 IP 는 타이밍을 못 재는 셈이었다. 현업에서도 어서션은 합성 대상이 아니다 --
`chformal -remove` 로 걷어내고 **걷어냈다고 말한다.**
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(뿌리))

import ipflow
import pnr
import rtl

FAIL_목록 = []


def ok(참, 말):
    print(("  통과 " if 참 else "  실패 ") + 말)
    if not 참:
        FAIL_목록.append(말)


P, F, M = ipflow.PASS, ipflow.FAIL, ipflow.못잼


def 문(이름, 판정):
    return {"관문": 이름, "판정": 판정, "값": "", "왜": ""}


print("[모으기 -- 못 잰 것을 통과로 세지 않는다]")
ok(ipflow.모으기([문("A", P), 문("B", P)])[0] == P, "다 통과면 PASS")
ok(ipflow.모으기([문("A", P), 문("B", M)])[0] == M,
   "**하나라도 못 재면 전체가 못잼** -- 통과가 아니다")
ok(ipflow.모으기([문("A", P), 문("B", F)])[0] == F, "하나라도 깨지면 FAIL")
ok(ipflow.모으기([문("A", F), 문("B", M)])[0] == F, "깨진 것이 못 잰 것보다 앞선다")
ok(ipflow.모으기([])[0] == M, "**빈 것은 통과가 아니다** -- 안 돌린 것도 못잼")
ok("B" in ipflow.모으기([문("A", P), 문("B", M)])[1],
   "어느 관문이 못 잰 것인지 이름을 댄다")
# 못잼이 하나라도 있으면 PASS 가 나오면 안 된다 -- 모든 자리에서
for i in range(7):
    문들 = [문(f"G{j}", P) for j in range(7)]
    문들[i]["판정"] = M
    ok(ipflow.모으기(문들)[0] != P, f"{i}번째 관문이 못잼이면 PASS 가 아니다")

print("\n[딜리버러블 -- 있는 것만 센다]")
d = ipflow.딜리버러블점검(["rtl", "testbench"])
ok(d["가진수"] == 2 and d["모두"] == 6, f"2/6: {d['가진수']}/{d['모두']}")
ok({k for k, _ in d["빠진것"]} == {"sdc", "register_map", "trm", "version"},
   f"빠진 것을 이름으로 댄다: {[k for k, _ in d['빠진것']]}")
ok(ipflow.딜리버러블점검(["RTL", " Testbench "])["가진수"] == 2, "대소문자·공백을 봐준다")
ok(ipflow.딜리버러블점검([])["가진수"] == 0, "빈 것은 0")
ok(ipflow.딜리버러블점검(["sdc", "made_up_thing"])["가진수"] == 1,
   "**목록에 없는 이름은 안 센다** -- 아무 낱말이나 주면 채워지면 안 된다")

print("\n[못 재는 것을 숨기지 않는다]")
# **이 목록을 데이터 밖에 못 박는다.** `ipflow.못재는것` 을 순회하며 검사하면 항목을
# 지우거나 이름을 바꿔도 검사가 그것을 따라가 버려 영영 안 걸린다 -- 실측으로
# `"DFT / ATPG"` 를 `"DFT / ATPG_x"` 로 바꾼 돌연변이가 살아남았다. 사인오프에서
# 이것이 조용히 비면 리포트가 **못 재는 것을 안 말하게 된다.**
꼭있어야 = ["DFT / ATPG", "MBIST", "CDC / RDC sign-off", "Power / IR drop",
         "DRC / LVS", "MCMM"]
난것 = {"판정": P, "관문": [문("LINT", P)], "왜": "다 지났다", "못재는것": ipflow.못재는것}
글 = ipflow.말로(난것)
있는이름 = {k for k, _ in ipflow.못재는것}
for 이름 in 꼭있어야:
    ok(이름 in 있는이름, f"못재는것 목록에 `{이름}` 이 있다")
    ok(이름 in 글, f"리포트가 `{이름}` 을 못 잰다고 적는다")
ok(len(ipflow.못재는것) >= len(꼭있어야),
   f"못 재는 것이 {len(꼭있어야)}가지 이상: {len(ipflow.못재는것)}")

print("\n[거짓 빨강 하나 -- 안 돈 시뮬을 불합격으로 세지 않는다]")
안돔 = ("design.v:15: Error: System task/function $past() is not defined by any "
       "module.\nsim.vvp: Program not runnable, 1 errors.")
ok(rtl.판정하기(안돔)[0] == M,
   f"**vvp 가 거부한 것은 못잼이다** (첫 판은 FAIL 이었다): {rtl.판정하기(안돔)[0]}")
ok("$past" in rtl.판정하기(안돔)[1], "어느 시스템 함수 때문인지 이름을 댄다")
ok("ifdef FORMAL" in rtl.판정하기(안돔)[1], "어디로 옮기라고 말해 준다")
ok(rtl.판정하기("FAIL: q=8 expected 4")[0] == F, "진짜 불합격은 그대로 FAIL")
ok(rtl.판정하기("FAIL: broken\nFATAL: f.v:1: bad")[0] == F,
   "**$fatal 은 FAIL 이다** -- 끝값이 같은 1 이라 글로 갈라야 한다")
ok(rtl.판정하기("PASS: all checks ok")[0] == P, "진짜 통과는 그대로 PASS")
ok(rtl.판정하기("nothing printed")[0] == M, "아무 표시도 없으면 못잼")

print("\n[거짓 빨강 둘 -- 어서션이 P&R 을 막지 않는다]")
ok("chformal -remove" in (뿌리 / "pnr.py").read_text(encoding="utf-8"),
   "**pnr 이 형식 셀을 걷어낸다** -- 안 걷으면 nextpnr 가 `$assert` 에서 통째로 막힌다")
ok(pnr.걷어낸형식셀("   $assert                         1\n") == {"$assert": 1},
   "합성 로그에서 걷어낸 형식 셀을 센다")
ok(pnr.걷어낸형식셀("   $assert   2\n   $cover    3\n") == {"$assert": 2, "$cover": 3},
   "여러 종류를 따로 센다")
ok(pnr.걷어낸형식셀("   SB_DFFER                        4\n") == {},
   "**보통 셀을 형식 셀로 세지 않는다**")
ok(pnr.걷어낸형식셀("") == {}, "빈 로그면 빈 것")

어서션단설계 = """module counter4 (
    input wire clk, input wire rst_n, input wire en, input wire load,
    input wire [3:0] d, output reg [3:0] q);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)    q <= 4'd0;
        else if (load) q <= d;
        else if (en)   q <= q + 4'd1;
    end
    always @(posedge clk) if (rst_n && !load && !en) assert (q == q);
endmodule
"""
if shutil.which("yosys") and shutil.which("nextpnr-ice40"):
    r = pnr.맞춰보기(어서션단설계, "counter4", 100.0, "hx8k", 초=400)
    ok(r["판정"] == pnr.PASS,
       f"**어서션을 단 설계도 타이밍이 나온다** (첫 판은 못잼이었다): {r['판정']} / {r['왜'][:80]}")
    ok(r["Fmax"] > 100, f"진짜 Fmax 가 나온다: {r['Fmax']}")
    ok(r.get("걷어낸형식셀"), f"무엇을 걷어냈는지 센다: {r.get('걷어낸형식셀')}")
    ok("걷어냈다" in r["왜"],
       "**조용히 지우지 않는다** -- 배치한 것이 소스 그대로가 아니면 그렇게 말한다")
else:
    print("  건너뜀 yosys/nextpnr 가 없다")

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
ok("def ip_signoff(" in 도구글, "bot_tools 에 ip_signoff")
ok("ip_signoff" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에")
ok("ip_signoff" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], "PUBLIC_TOOLS 에")
ok("ip_signoff" in (뿌리 / "eda_prompt.py").read_text(encoding="utf-8"),
   "**두 프롬프트가 함께 쓰는 갈래규칙에 있다** -- 물려 놓고 쓰라고 안 하면 안 쓴다")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('- "ipflow.py"' in 배포, "**ipflow.py 가 배포 paths 에 있다** -- 없으면 서버에 안 간다")

print()
if FAIL_목록:
    print(f"실패 {len(FAIL_목록)}개 -- {FAIL_목록}")
    sys.exit(1)
print("ipflow: 못 잰 관문을 통과로 안 센다 · 안 돈 시뮬을 불합격으로 안 센다 · "
      "어서션이 타이밍을 안 막는다 -- 통과")
