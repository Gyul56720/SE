# -*- coding: utf-8 -*-
"""**어서션 관문(4d) 이 무는가 -- 그리고 어서션이 정말 터지는가.**

테이프아웃 지도의 M3:

    어서션 (SVA) · 형식 검증   없다   칸 자체가 없다

## 붙이면서 배운 것 셋 -- 전부 실측이다

**하나. verilator 5.020 은 부분집합만 받는다.**

    받는다   |->  |=>  $past  $rose/$fell/$stable  $onehot  cover/assume property
    거부한다  ##n (cycle delay)   [*n] (boolean abbrev)

**둘. 어서션은 다른 관문을 깨뜨린다.** `assert property` 를 그냥 두면

    iverilog -g2012        : Error in property_spec of concurrent assertion item
    yosys read_verilog -sv : syntax error, unexpected '@'

그 둘이 관문 2 와 관문 6 이다. 그래서 RTL 이 `` `ifdef SVA_ON `` 으로 감싸고
이 관문만 `-DSVA_ON` 으로 켠다.

**셋. 첫 리셋 어서션이 틀렸다.** `!rst_n |-> st == S_IDLE` 은 시간 0 에서 터졌다.

    [0] Assertion failed in ...sva_reset: 리셋 중인데 st=00000 cnt=0

`always @(posedge clk or negedge rst_n)` 은 **엣지로만** 돈다. rst_n 이 처음부터
0 이면 내려간 엣지가 없어 플롭이 초기값인 채로 첫 엣지를 맞는다. 어떤 설계든
그렇다 -- **그러니 그것을 흠이라 적은 어서션이 틀렸다.** 지금은 리셋을 놓는
순간을 적는다(`$rose(rst_n) |-> 초기상태`).

실행: python3 tests/test_어서션관문.py
"""
from __future__ import annotations

import subprocess
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

문턱 = GEN.기본문턱
성한것 = {"개수": 10, "갈래": {"동시": 10, "커버": 0, "가정": 0, "즉시": 0},
        "돈씨앗": [{"씨": 1, "rc": 0}, {"씨": 2, "rc": 0}, {"씨": 3, "rc": 0}],
        "터진것": [], "터진수": 0, "초": 0.1}


def 판정(**고침):
    return GEN.어서션판정({**성한것, **고침}, 문턱)


print("\n[1] 문턱이 있나")
for 열쇠 in ("어서션수", "어서션씨앗"):
    ok(열쇠 in 문턱, f"gen.기본문턱 에 {열쇠!r} 가 있다 ({문턱.get(열쇠)})")
ok(len(문턱["어서션씨앗"]) >= 2,
   f"씨앗을 여럿 돌린다 ({len(문턱['어서션씨앗'])}개) — 씨앗 하나는 회귀가 아니다")

print("\n[2] 성한 값은 통과한다")
r = 판정()
ok(len(r) == 1 and r[0][1], "잰 값 그대로면 초록이다")
ok(r[0][0].startswith("4d."), f"이름표가 4d 로 시작한다 ({r[0][0][:12]})")

print("\n[3] **관문이 무는가**")
ok(not 판정(개수=0, 갈래={"동시": 0, "커버": 0, "가정": 0, "즉시": 0})[0][1],
   "어서션이 0개면 빨갛다 — 칸이 비어 있는데 통과시키지 않는다")
ok(not 판정(개수=문턱["어서션수"] - 1)[0][1],
   f"어서션이 {문턱['어서션수'] - 1}개면(문턱보다 하나 적다) 빨갛다")
ok(not 판정(터진수=1, 터진것=[{"씨": 2, "글": "Assertion failed in ...sva_onehot"}])[0][1],
   "하나라도 터지면 빨갛다 — 개수가 넉넉해도")
ok(not GEN.어서션판정({"오류": "어서션을 켜고 못 지었다"}, 문턱)[0][1],
   "어서션을 켜고 못 지으면 빨갛다 — 못 쟀는데 통과시키지 않는다")
ok(판정(개수=문턱["어서션수"])[0][1], "문턱과 꼭 같으면 통과한다")

print("\n[4] 관문 글이 숨기지 않는가")
말 = 판정()[0][2]
ok("세는 것만으로는 관문이 아니" in 말,
   "개수만 보면 안 된다고 적고, 그래서 켜서 돌린다고 말한다")
ok("##n" in 말 and "거부" in 말, "verilator 가 안 받는 꼴을 적는다")
ok("iverilog" in 말 and "yosys" in 말, "왜 `ifdef 로 감싸야 하는지 적는다")
말터짐 = 판정(터진수=1, 터진것=[{"씨": 2, "글": "Assertion failed in X: 무엇"}])[0][2]
ok("씨2" in 말터짐 and "Assertion failed" in 말터짐,
   "터진 것은 씨앗과 원문을 그대로 적는다")

print("\n[5] **어서션이 정말 터지는가** -- 일부러 깨지는 것을 지어 돌린다")
# 이것이 이 파일의 심장이다. 위는 전부 '판정' 을 본 것이고, 여기서 보는 것은
# **배선**이다 -- 어서션이 깨졌을 때 우리가 그것을 실제로 알아보는가.
with tempfile.TemporaryDirectory() as 방:
    방 = Path(방)
    (방 / "f.sv").write_text('''module f (input logic clk, input logic rst_n,
                          input logic a, input logic b);
`ifdef SVA_ON
  ax: assert property (@(posedge clk) disable iff (!rst_n) a |-> b)
      else $error("AX 깨졌다 a=%0d b=%0d", a, b);
`endif
endmodule
''', encoding="utf-8")
    (방 / "m.cpp").write_text('''#include "Vf.h"
#include "verilated.h"
#include <cstdio>
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vf* d = new Vf;
    d->rst_n = 0; d->a = 0; d->b = 0; d->clk = 0;
    for (int i = 0; i < 4; i++) { d->clk = !d->clk; d->eval(); }
    d->rst_n = 1;
    for (int i = 0; i < 20; i++) {
        d->clk = 0; d->eval();
        d->a = (i > 4) ? 1 : 0; d->b = 0;
        d->clk = 1; d->eval();
    }
    printf("{\\"end\\":1}\\n");
    delete d; return 0;
}
''', encoding="utf-8")

    def 지어돌리기(sva_on: bool):
        cmd = ["verilator", "--cc", "--assert", "--exe", "--build",
               "-Mdir", str(방 / ("on" if sva_on else "off")), "-o", "fsim",
               str(방 / "f.sv"), str(방 / "m.cpp"), "-CFLAGS", "-O0", "-Wno-fatal"]
        if sva_on:
            cmd += ["-DSVA_ON"]
        b = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if b.returncode != 0:
            return None, b.stderr[-300:]
        실행 = 방 / ("on" if sva_on else "off") / "fsim"
        r = subprocess.run([str(실행)], capture_output=True, text=True, timeout=120)
        return r, ""

    켬, 왜 = 지어돌리기(True)
    ok(켬 is not None, f"SVA_ON 으로 지었다 ({왜})")
    if 켬 is not None:
        글 = 켬.stdout + 켬.stderr
        ok("Assertion failed" in 글,
           "깨지는 어서션이 **실제로 터진다** — 터지면 우리가 알아본다")
        ok(켬.returncode != 0,
           f"터지면 종료 코드가 0 이 아니다 (rc={켬.returncode}) — 관문이 이것도 본다")
        ok("AX 깨졌다 a=1 b=0" in 글,
           "$error 에 적은 값이 그대로 나온다 — 무엇이 깨졌는지 알 수 있다")
    끔, 왜2 = 지어돌리기(False)
    ok(끔 is not None, f"SVA_ON 없이도 지어진다 ({왜2})")
    if 끔 is not None:
        ok("Assertion failed" not in (끔.stdout + 끔.stderr) and 끔.returncode == 0,
           "SVA_ON 이 없으면 같은 자극에도 안 터진다 — `ifdef 가 실제로 막는다")

print("\n[6] 다른 도구가 우리 RTL 을 여전히 읽는가 (관문 2 · 6 을 안 깬다)")
rtl = [str(x) for x in DES.NSW_FIR.RTL]
iv = subprocess.run(["iverilog", "-g2012", "-o", "/dev/null"] + rtl,
                    capture_output=True, text=True, timeout=300)
ok(iv.returncode == 0, f"iverilog 가 읽는다 ({iv.stderr[-160:]})")
ys = subprocess.run(["yosys", "-p",
                     f"read_verilog -sv {' '.join(rtl)}; hierarchy -top {DES.NSW_FIR.top}"],
                    capture_output=True, text=True, timeout=300)
ok(ys.returncode == 0 and "ERROR" not in ys.stdout.upper(),
   f"yosys 가 읽는다 (rc={ys.returncode})")
# **감싸는 것을 안 빼먹었나** -- 감싸지 않은 어서션이 하나라도 있으면 위 둘이 깨진다
글 = Path(DES.NSW_FIR.RTL[0]).read_text(encoding="utf-8")
ok(글.count("`ifdef SVA_ON") >= 1 and 글.count("`endif") >= 글.count("`ifdef SVA_ON"),
   f"어서션이 `ifdef SVA_ON 으로 감싸여 있다 ({글.count('`ifdef SVA_ON')}묶음)")

print("\n[7] **진짜 RTL 로 재 본다**")
A = GEN.어서션(DES.NSW_FIR, 문턱)
ok(not A.get("오류"), f"어서션()이 돌았다 ({A.get('오류', '')[:120]})")
if not A.get("오류"):
    ok(set(성한것) <= set(A),
       f"손으로 만든 값과 칸이 같다 (빠진 칸 {sorted(set(성한것) - set(A))})")
    ok(A["개수"] >= 문턱["어서션수"],
       f"어서션이 문턱 이상 있다 ({A['개수']} ≥ {문턱['어서션수']})")
    ok(A["터진수"] == 0,
       f"돌려도 하나도 안 터진다 ({A['터진수']}개 · {len(A['돈씨앗'])} 씨앗)")
    ok(all(x["rc"] == 0 for x in A["돈씨앗"]),
       f"모든 씨앗이 정상 종료했다 ({[x['rc'] for x in A['돈씨앗']]})")
    ok(GEN.어서션판정(A, 문턱)[0][1], "잰 값으로 관문이 초록이다")
    print(f"       (어서션 {A['개수']}개 · {A['초']} s)")

print("\n[8] 짓는 RTL 에도 같은 것을 시키는가")
ok("SVA_ON" in GEN.RTL프롬프트 and "ifdef" in GEN.RTL프롬프트,
   "RTL 프롬프트가 `ifdef SVA_ON 으로 감싸라고 시킨다")
ok("##n" in GEN.RTL프롬프트 and "$rose(rst_n)" in GEN.RTL프롬프트,
   "안 받는 꼴과, 리셋은 탈출로 적으라는 것까지 시킨다")

print("\n[9] 테이프아웃 표")
이름별 = {x["이름"]: x for x in TO.표(주인="dv")}
x = 이름별.get("어서션 (SVA)")
ok(x is not None and x["상태"] == TO.있다, "「어서션 (SVA)」 이 「있다」 로 올라왔다")
f = 이름별.get("형식 검증 (formal property check)")
ok(f is not None and f["상태"] == TO.없다 and not f["막나"],
   "「형식 검증」 은 없는 채로 남고 막는 칸으로 안 센다 — 어서션과 증명은 다르다")
ok(TO._관문있나("4d") and "4d" in GEN.관문번호들(), "관문 4d 가 있다")
ok(not TO.검사() and not TO.거짓증거() and not TO.안걸린붙듦(),
   f"계획에 흠이 없다 ({TO.검사()})")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
