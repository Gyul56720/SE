# -*- coding: utf-8 -*-
"""**RDC(관문 2b) 가 새 건넘을 잡는가 -- RTL 을 실제로 건드려 본다.**

`house/flow.py` 도 `house/tapeout.py` 도 **RDC 없음**이라고 적고 있었다.
CDC 는 세는데 리셋은 안 셌다.

## 실측 2026-09-23 (nsw_fir)

순차 블록 10개에 리셋 묶음이 다섯이고(rst_n · wrst_n · rrst_n · rst_n_i ·
**리셋없음**) 건넘이 넷 나왔다.

    wgray  wrst_n -> rrst_n        FIFO 그레이 포인터
    rgray  rrst_n -> wrst_n        반대 방향
    wbin   wrst_n -> (리셋없음)     메모리 배열은 리셋이 없다
    cnt    rst_n  -> (리셋없음)     MAC 파이프라인은 리셋이 없다

**리셋이 없는 블록도 한 도메인으로 센다.** 리셋 걸린 플롭이 리셋 없는 플롭을
먹이는 자리가 고전적인 RDC 이고, 그것을 빼면 **가장 위험한 것을 빼는 것**이
된다 -- 넷 중 둘이 그 자리다.

## 이 관문은 안전을 증명하지 않는다

텍스트로는 못 한다. 잡는 것은 **새로 생겼는데 아무도 안 본 건넘**이다.
그래서 이 검사의 심장은 [5] -- **RTL 에 리셋 도메인을 하나 더 만들어** 넣고
관문이 빨개지는지 본다. 선언 파일을 안 고쳤으니 빨개야 한다.

실행: python3 tests/test_RDC관문.py
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
from house import rtlscan as SCAN      # noqa: E402
from house import tapeout as TO        # noqa: E402

문턱 = GEN.기본문턱

print("\n[1] 훑기가 RDC 를 내는가")
훑 = SCAN.훑기([str(x) for x in DES.NSW_FIR.RTL], DES.NSW_FIR.top)
ok("RDC건넘" in 훑, "훑기 결과에 RDC건넘 칸이 있다")
rdc = 훑["RDC건넘"]
ok(len(rdc) == 4, f"nsw_fir 에서 건넘 4개가 나온다 ({len(rdc)})")
이름들 = {x["신호"] for x in rdc}
ok(이름들 == {"cnt", "rgray", "wbin", "wgray"}, f"잰 그대로다 ({sorted(이름들)})")
리셋없음 = [x for x in rdc if x["받는곳"] == "(리셋없음)"]
ok(len(리셋없음) == 2,
   f"**리셋 없는 도메인으로 가는 건넘 2개를 센다** ({[x['신호'] for x in 리셋없음]}) "
   "— 그것을 빼면 가장 위험한 것을 빼는 것이다")
ok(len(훑["CDC건넘"]) == 2, f"CDC 는 그대로 2개다 ({len(훑['CDC건넘'])}) — 다른 물음이다")

print("\n[2] 선언과 대조하는가")
R = GEN.rdc점검(DES.NSW_FIR, 문턱)
ok(not R.get("오류"), f"rdc점검()이 돌았다 ({R.get('오류','')})")
ok(R["선언있나"], f"선언 파일이 있다 ({Path(R['선언파일']).name})")
ok(R["찾은수"] == 4 and R["선언수"] == 4, f"찾은 {R['찾은수']} · 선언 {R['선언수']}")
ok(not R["안선언"], f"선언에 없는 건넘이 0개다 ({[x['신호'] for x in R['안선언']]})")
ok(not R["낡은선언"], f"낡은 선언이 없다 ({len(R['낡은선언'])}개)")
ok(not R["까닭없음"], f"까닭이 빈 선언이 없다 ({R['까닭없음']})")
ok(GEN.rdc판정(R, 문턱)[0][1], "관문이 초록이다")

print("\n[3] **관문이 무는가** -- 판정만 따로")
성 = {"찾은수": 4, "찾은것": rdc, "선언수": 4, "안선언": [], "낡은선언": [],
     "까닭없음": [], "선언파일": R["선언파일"], "선언있나": True,
     "선언오류": "", "리셋도메인수": 4, "초": 0.01}
ok(not GEN.rdc판정({**성, "안선언": [rdc[0]]}, 문턱)[0][1],
   "선언에 없는 건넘이 하나라도 있으면 빨갛다")
ok(not GEN.rdc판정({**성, "까닭없음": ["wgray"]}, 문턱)[0][1],
   "**까닭이 빈 선언이 있으면 빨갛다** — 줄만 채우면 통과하는 자리를 막는다")
ok(not GEN.rdc판정({**성, "선언오류": "못 읽었다"}, 문턱)[0][1],
   "선언 파일을 못 읽으면 빨갛다 — 못 쟀는데 통과시키지 않는다")
ok(not GEN.rdc판정({"오류": "RTL 이 없다"}, 문턱)[0][1], "못 돌리면 빨갛다")
ok(GEN.rdc판정({**성, "낡은선언": [{"신호": "옛것"}]}, 문턱)[0][1],
   "낡은 선언은 적기만 하고 안 막는다 — 건넘이 사라진 것은 좋은 소식이다")
ok("옛것" in GEN.rdc판정({**성, "낡은선언": [{"신호": "옛것"}]}, 문턱)[0][2],
   "그래도 이름은 적는다 — 이름이 바뀐 건넘을 가릴 수 있다")

print("\n[4] 관문 글이 한계를 적는가")
말 = GEN.rdc판정(성, 문턱)[0][2]
ok("안전을 증명하지 않는다" in 말, "안전을 증명하지 않는다고 먼저 말한다")
ok("아무도 안 본 건넘" in 말, "무엇을 잡는지 말한다")
ok("리셋이 없는 블록도" in 말, "리셋 없는 도메인을 왜 세는지 적는다")

print("\n[5] **RTL 에 리셋 도메인을 더해 보면 빨개지는가** -- 이 파일의 심장")
# 앞은 전부 '이미 있는 것' 을 본 것이다. 관문이 **새 건넘**을 잡는지는
# 회로를 실제로 건드려서만 알 수 있다.
원본 = Path(DES.NSW_FIR.RTL[0]).read_text(encoding="utf-8")
with tempfile.TemporaryDirectory() as 방:
    방 = Path(방)
    새RTL = 방 / "nsw_fir.sv"
    # 새 리셋(aux_rst_n)으로 도는 플롭을 더하고, 그것이 rst_n 쪽 신호를 먹게 한다
    더함 = '''
module nsw_rdc_trap (input wire clk, input wire aux_rst_n, input wire [11:0] cnt,
                     output reg [11:0] q);
    always @(posedge clk or negedge aux_rst_n)
        if (!aux_rst_n) q <= 12'd0; else q <= cnt;
endmodule
'''
    새RTL.write_text(원본 + 더함, encoding="utf-8")
    # 선언 파일은 **그대로 복사한다** -- 새 건넘은 선언에 없다
    (방 / "nsw_fir.rdc.json").write_text(
        Path(DES.NSW_FIR.RTL[0]).with_name("nsw_fir.rdc.json")
        .read_text(encoding="utf-8"), encoding="utf-8")

    class _가짜:
        top = "nsw_fir"
        RTL = [새RTL]

    R2 = GEN.rdc점검(_가짜(), 문턱)
    ok(not R2.get("오류"), f"건드린 RTL 로도 돌았다 ({R2.get('오류','')})")
    ok(R2["찾은수"] > R["찾은수"],
       f"**건넘이 늘었다** ({R['찾은수']} → {R2['찾은수']})")
    ok(any(x["받는곳"] == "aux_rst_n" for x in R2["안선언"]),
       f"새 리셋 도메인으로 가는 건넘이 **선언에 없다**고 잡힌다 "
       f"({[(x['신호'], x['받는곳']) for x in R2['안선언']]})")
    판 = GEN.rdc판정(R2, 문턱)
    ok(not 판[0][1], "**관문이 빨갛다** — 선언 안 한 건넘이 생겼다")
    ok("선언에 없다" in 판[0][2], "어느 것이 선언에 없는지 표에 적는다")
    print(f"       (건넘 {R2['찾은수']}개 · 선언에 없는 것 {len(R2['안선언'])}개)")

    # **선언을 채우면 다시 초록이어야 한다** -- 늘 빨간 관문이 아니다
    d = json.loads((방 / "nsw_fir.rdc.json").read_text(encoding="utf-8"))
    for x in R2["안선언"]:
        d["건넘"].append({"신호": x["신호"], "보내는곳": x["보내는곳"],
                        "받는곳": x["받는곳"], "까닭": "검사가 지어 넣은 덫이다"})
    (방 / "nsw_fir.rdc.json").write_text(json.dumps(d, ensure_ascii=False),
                                       encoding="utf-8")
    R3 = GEN.rdc점검(_가짜(), 문턱)
    ok(not R3["안선언"] and GEN.rdc판정(R3, 문턱)[0][1],
       "선언을 채우면 다시 초록이다 — 늘 빨간 관문이 아니다")

print("\n[6] 선언 파일이 없으면")
with tempfile.TemporaryDirectory() as 방2:
    방2 = Path(방2)
    (방2 / "nsw_fir.sv").write_text(원본, encoding="utf-8")

    class _선언없음:
        top = "nsw_fir"
        RTL = [방2 / "nsw_fir.sv"]

    R4 = GEN.rdc점검(_선언없음(), 문턱)
    ok(not R4["선언있나"] and R4["선언수"] == 0, "선언 0개로 친다")
    ok(len(R4["안선언"]) == R4["찾은수"] and not GEN.rdc판정(R4, 문턱)[0][1],
       f"건넘이 전부 '선언에 없다' 가 되고 빨갛다 ({R4['찾은수']}개) — "
       "아무도 안 본 건넘이 있다는 뜻이다")

print("\n[7] 테이프아웃과 흐름표")
이름별 = {x["이름"]: x for x in TO.표(주인="rtl")}
x = 이름별.get("RDC (리셋 도메인 건넘)")
ok(x is not None and x["상태"] == TO.있다, "「RDC」 가 「있다」 로 올라왔다")
from house import flow as FLOW                                # noqa: E402
줄 = [y for y in FLOW.표() if y["단계"] == "Lint / CDC / RDC"][0]
ok("RDC 없음" not in 줄["우리"] and "RDC 없음" not in 줄["메모"],
   "house/flow.py 가 더는 'RDC 없음' 이라고 적지 않는다")
ok("2b" in 줄["우리"], f"흐름표가 관문 2b 를 가리킨다 ({줄['우리']})")
ok(TO._관문있나("2b") and "2b" in GEN.관문번호들(), "관문 2b 가 있다")
ok(not TO.검사() and not TO.거짓증거() and not TO.안걸린붙듦(),
   f"계획에 흠이 없다 ({TO.검사()})")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
