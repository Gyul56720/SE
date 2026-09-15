"""`formal.py` -- 형식 검증. **공허한 통과와 얕은 통과를 초록으로 세지 않는다.**

사용자(2026-09-15): design house 의 남은 구멍 중 둘째.

## 이 검사가 붙드는 것 -- 거짓 초록 **셋**

실측 2026-09-15 (yosys 0.33). 넷 다 **끝값 0** 이다.

    성질 성립(원형 카운터)   Induction step proven: SUCCESS!
    성질 깨짐                 SAT proof finished - model found: FAIL!
    **assert 가 하나도 없음** no model found: **SUCCESS!**
    **깊이 20, 버그는 200걸음** no model found: **SUCCESS!**

1. 깨진 것도 끝값 0 -- `vvp`·ngspice 와 같은 병.
2. **증명할 성질이 없으면 공허하게 SUCCESS 다.** 아무것도 증명 안 했는데 초록이다.
3. **유계는 증명이 아니다.** 실측으로 200번째 클럭에 깨지는 설계가 깊이 20 에서
   초록이었고 귀납이 잡아냈다. 같은 글자 `SUCCESS` 로 나온다.

2번과 3번이 이 검사의 본체다. 1번만 잡는 장치는 형식 검증에서 제일 흔한
자기기만을 그대로 통과시킨다.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import formal                                                     # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


# 실측한 yosys 출력 조각. 도구 없이도 판정은 늘 검사한다.
성질들어감 = "Import proof for assert: $formal$x.sv:5$1_CHECK when $formal$x.sv:5$1_EN.\n"
귀납성공 = 성질들어감 + "Base case for induction length 2 proven.\nInduction step proven: SUCCESS!\n"
유계성공 = 성질들어감 + "SAT proof finished - no model found: SUCCESS!\n"
반례 = 성질들어감 + "SAT proof finished - model found: FAIL!\n"
반례기저 = 성질들어감 + "SAT temporal induction proof finished - model found for base case: FAIL!\n"
성질없음 = "SAT proof finished - no model found: SUCCESS!\n"     # Import proof 가 없다
막힘 = "ERROR: Failed to import cell $procdff$40 (type $adff) to SAT database.\n"

print("\n[판정] 끝값이 아니라 출력을 읽는다")
ok(formal.판정하기(귀납성공, True, 20)[0] == formal.PASS, "귀납 증명 -> PASS")
ok(formal.판정하기(반례, False, 14)[0] == formal.FAIL, "반례 -> FAIL")
ok(formal.판정하기(반례기저, True, 20)[0] == formal.FAIL, "귀납 기저 반례 -> FAIL")
ok(formal.판정하기(막힘, True, 20)[0] == formal.못잼, "yosys 가 막히면 못잼")

print("\n[판정] **공허한 통과** -- 증명할 것이 없는데 SUCCESS")
판, 왜 = formal.판정하기(성질없음, True, 20)
ok(판 == formal.못잼, f"**성질이 SAT 판에 안 들어갔으면 못잼**: {판}")
ok("성질" in 왜, f"까닭이 그것을 말한다: {왜[:50]}")

print("\n[판정] **유계는 증명이 아니다**")
판, 왜 = formal.판정하기(유계성공, False, 20)
ok(판 == formal.못잼,
   f"**깊이 20 까지 반례가 없는 것은 PASS 가 아니다**(200걸음 버그가 여기 숨는다): {판}")
ok("20" in 왜 and "증명" in 왜, f"몇 걸음까지 봤는지 말한다: {왜[:60]}")
판2, 왜2 = formal.판정하기(유계성공, True, 20)
ok(판2 == formal.못잼, f"무계를 시켰는데 귀납이 안 끝나도 못잼: {판2}")
ok("귀납이 안 끝났다" in 왜2 and "그것은 증명이 아니다" in 왜,
   f"**둘 다 못잼이지만 까닭이 갈린다** -- 하나는 '귀납이 안 끝났다', 하나는 "
   f"'N 걸음까지만 봤다'. 섞이면 무엇을 고쳐야 하는지 알 수 없다: {왜2[:40]!r} vs {왜[:40]!r}")

print("\n[성질세기] 주석은 안 센다")
ok(formal.성질세기("always @(posedge clk) assert (a == b);") == 1, "assert 를 센다")
ok(formal.성질세기("// assert (a == b);\n") == 0, "**주석 속 assert 는 안 센다**")
ok(formal.성질세기("assume (x); cover (y); assert (z);") == 3, "assume·cover 도 성질이다")
ok(formal.성질세기("module m; endmodule") == 0, "없으면 0")

print("\n[증명] 돌리기 전에 막는다")
r = formal.증명("module m(input wire clk); endmodule\n", "m", 5, True, 초=30)
ok(r["판정"] == formal.못잼 and r["성질수"] == 0,
   f"**assert 가 없으면 못잼** -- 돌려 봐야 공허한 SUCCESS 다: {r['판정']}")
ok(r["로그"] == "",
   f"**돌리지도 않는다** -- 로그가 비었다(솔버를 부르면 SUCCESS 가 돌아온다): {r['로그'][:40]!r}")
ok(r["판정"] == formal.못잼, "빈 설계도 못잼")
ok(formal.증명("", "m", 5, 초=10)["판정"] == formal.못잼, "빈 글 -> 못잼")

print("\n[끝까지] yosys 로 실제로 증명한다")
if not formal.있나():
    print("  yosys 가 없다 -- 건너뛴다 (배포는 깐다)")
else:
    판 = tempfile.mkdtemp(prefix="fvtest-")
    원형 = """module ring (input wire clk, input wire rst_n, output reg [3:0] s);
    initial s = 4'b0001;
    always @(posedge clk)
        if (!rst_n) s <= 4'b0001;
        else begin
            s <= {s[2:0], s[3]};
            assert (s == 4'b0001 || s == 4'b0010 || s == 4'b0100 || s == 4'b1000);
        end
endmodule
"""
    r = formal.증명(원형, "ring", 20, True, 초기0=False, 초=280)
    ok(r["판정"] == formal.PASS, f"원형 카운터는 한 비트만 선다 -- 무계 증명: {r['판정']} / {r['왜'][:60]}")
    ok(r["성질수"] == 1, f"성질 1개: {r['성질수']}")

    # **이 검사의 본체 하나.** 200걸음째에 깨지는 설계.
    늦은버그 = """module late (input wire clk, input wire rst_n, output reg [7:0] c);
    initial c = 0;
    always @(posedge clk)
        if (!rst_n) c <= 0;
        else begin c <= c + 1; assert (c != 8'd200); end
endmodule
"""
    얕게 = formal.증명(늦은버그, "late", 20, False, 초=280)
    ok(얕게["판정"] == formal.못잼,
       f"**깊이 20 은 200걸음 버그를 못 본다 -- 그래도 PASS 가 아니다**: {얕게['판정']}")
    ok("증명이 아니다" in 얕게["왜"], f"왜: {얕게['왜'][:70]}")

    # 반례는 그림으로 온다.
    이른버그 = 늦은버그.replace("8'd200", "4'd9").replace("[7:0]", "[3:0]")
    png = os.path.join(판, "cex.png")
    r = formal.증명(이른버그, "late", 14, False, 초=280, 반례낼곳=png)
    ok(r["판정"] == formal.FAIL, f"9 에서 깨지는 설계: {r['판정']}")
    ok(bool(r["반례"]) and os.path.exists(png) and os.path.getsize(png) > 1000,
       f"**반례가 파형 그림으로 온다**: {r['반례']}")
    ok("signals" in r["왜"], f"반례가 몇 신호 몇 걸음인지 말한다: {r['왜'][-50:]}")
    # **반례가 납작하면 없느니만 못하다.** 실측 2026-09-15: `-show-all` 이 빠지면
    # 같은 반례가 2걸음 6신호로 나온다 -- 아무 일도 안 일어난 것처럼 보이는 그림이다.
    import re as _re
    m = _re.search(r"signals (\d+) . toggling (\d+) . span (\d+)", r["왜"])
    ok(m is not None, f"셈을 읽을 수 있다: {r['왜'][-60:]}")
    if m:
        신, 움, 폭 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ok(폭 >= 10, f"**반례가 여러 걸음이다** (`-show-all` 이 빠지면 2걸음이다): {폭}걸음")
        ok(움 >= 3, f"**반례 안에서 신호가 실제로 움직인다** (납작하면 볼 것이 없다): {움}개")
        ok(신 >= 8, f"신호가 충분히 보인다 (빠지면 6개다): {신}개")

    # 성질이 없는 진짜 설계 -- 돌리면 SUCCESS 가 나오지만 우리는 안 속는다.
    맨설계 = """module plain (input wire clk, input wire rst_n, output reg [3:0] g);
    always @(posedge clk) if (!rst_n) g <= 0; else g <= g + 1;
endmodule
"""
    r = formal.증명(맨설계, "plain", 14, False, 초=120)
    ok(r["판정"] == formal.못잼,
       f"**성질 없는 설계는 못잼** -- yosys 는 이것에 SUCCESS 를 낸다(실측): {r['판정']}")

    shutil.rmtree(판, ignore_errors=True)

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
ok("def prove_rtl(" in 도구글, "bot_tools 에 prove_rtl")
ok("prove_rtl" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에")
ok("prove_rtl" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], "PUBLIC_TOOLS 에")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('- "formal.py"' in 배포, "formal.py 가 배포 트리거 paths 에 있다")
ok(" yosys" in 배포, "배포가 yosys 를 깐다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("formal: 공허한 통과 · 얕은 통과를 초록으로 안 센다 · 반례는 그림으로 -- 통과")
