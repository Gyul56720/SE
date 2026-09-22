# -*- coding: utf-8 -*-
"""**관문이 보증을 하는가 -- 수를 찍기만 하는 칸을 없앴는지 본다.**

사용자(2026-09-22): "Testbench 도 고도화해줘. 강건성을 위해 더 많은 시나리오로
더 치밀한 검증을 통한 보증을 가능케 해줘. 기준은 AMD나 xillinx, 브로드컴 같은
펩리스 VLSI 기준으로."

그 업계가 커버리지만으로 서명하지 않는 까닭이 있다. **커버리지는 "자극이 거기를
지나갔다" 는 말이지 "검사기가 틀린 값을 알아본다" 는 말이 아니다.**

## 고치기 전의 관문이 무엇을 안 봤나 -- 실측

  · **커버리지에 문턱이 없었다.** 퍼센트를 찍기만 했다. 30% 여도 초록.
  · **씨앗이 둘이었다.** 씨앗을 타는 버그가 그대로 통과한다.
  · **X 를 안 봤다.** 2-state 로만 돌면 미초기화 레지스터가 0 으로 보인다.
  · **테스트벤치가 무는지 한 번도 안 봤다.** `printf("{...fail:0}")` 한 줄짜리
    테스트벤치도 관문 4를 통과한다.
  · **STA 가 수를 찍기만 했다.** `슬 is not None` -- nsw_fir 이 10 ns 에서
    최악 슬랙 **-3.15 ns** 인데 초록이었다.

여기서는 **글자를 안 본다.** 관문을 실제로 돌리고, 문턱을 넘기고 못 넘기는 두
경우를 다 만들어 **판정이 갈리는지** 본다.

실행: python3 tests/test_보증관문.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import gen as G          # noqa: E402
from house.dv import automut as A   # noqa: E402

# ================================================== 1. 변이 엔진이 옳은 데를 문다
_sv = """
module t #(parameter W = 8) (
  input wire clk, input wire rst_n,
  input wire [W-1:0] a, input wire [W-1:0] b,
  output reg [W-1:0] y
);
  // 이 주석의 a + b 는 건드리면 안 된다
  wire [W-1:0] s = a + b;
  wire hit = (a == b) && (a < b);
  always @(posedge clk) begin
    if (!rst_n) y <= 0;
    else        y <= s;
  end
endmodule
"""
_후보 = A.후보찾기(_sv, 최대=50)
_전후 = {(c["전"], c["후"]) for c in _후보}
ok(("+", "-") in _전후, f"`+` 를 `-` 로 바꾼다 ({sorted(_전후)[:4]})")
ok(("==", "!=") in _전후, "`==` 를 `!=` 로 바꾼다")
ok(("&&", "||") in _전후, "`&&` 를 `||` 로 바꾼다")
ok(("<", "<=") in _전후, "`<` 를 `<=` 로 바꾼다")

# **주석을 안 건드린다.** 주석의 `+` 를 바꾸면 RTL 은 그대로인데 변이를 심었다고
# 세게 되고, 그 변이는 영영 안 잡힌다 -- 점수가 거짓으로 내려간다.
_주석자리 = _sv.index("// 이 주석의")
_주석끝 = _sv.index("\n", _주석자리)
ok(not [c for c in _후보 if _주석자리 <= c["자리"] < _주석끝],
   "**주석 안은 안 건드린다** -- 심어도 RTL 이 안 바뀌어 영영 안 잡힌다")

# **`always @(*)` 의 별표와 비블로킹 `<=` 는 안 건드린다.**
# 첫 판이 둘 다 건드려 `always @(+)` 와 `y < s;` 를 냈다 -- 빌드가 깨지는 변이라
# 점수에서 빠지고, 그 자리를 검사하지도 못한다.
_sv2 = "module u(input c, output reg z);\n always @(*) z = c;\n always @(posedge c) z <= c;\nendmodule\n"
_후2 = A.후보찾기(_sv2, 최대=50)
ok(not [c for c in _후2 if c["전"].strip() == "*"],
   f"**`always @(*)` 의 별표를 안 건드린다** ({[c['전'] for c in _후2]})")
ok(not [c for c in _후2 if c["전"] == "<=" and c["후"] == "<"],
   "**비블로킹 `<=` 를 비교로 안 읽는다** -- 그것은 대입이다")

# 심기는 **그 자리 하나만** 바꾼다
_c = next(c for c in _후보 if (c["전"], c["후"]) == ("+", "-"))
_바뀐 = A.심기(_sv, _c)
ok(len(_바뀐) == len(_sv) and _바뀐 != _sv, "한 글자만 바뀐다")
ok(_바뀐.count("a + b") == 1 and "a - b" in _바뀐,
   "**주석의 `a + b` 는 그대로 있고 코드 쪽만 바뀌었다**")

# ================================================== 2. 관문에 문턱이 실제로 있다
_문 = G.기본문턱
ok(_문["커버리지_pct"] > 0, f"커버리지 문턱이 있다 ({_문['커버리지_pct']}%)")
ok(_문["회귀씨앗"] >= 8, f"**회귀 씨앗이 8개 이상이다** ({_문['회귀씨앗']}) — 둘은 회귀가 아니다")
ok(_문["변이점수"] > 0, f"변이 점수 문턱이 있다 ({_문['변이점수']:.0%})")
# **표본이 적으면 점수가 아니라 잡음이다.** 실측: 같은 테스트벤치가 변이 14개로는
# 69%, 6개로는 20% 였다. 6개짜리 수를 문턱에 대면 테스트벤치를 한 줄도 안 고쳤는데
# 초록과 빨강이 오간다.
ok(_문["변이수"] >= 12, f"**변이 표본이 12개 이상이다** ({_문['변이수']})")


class _가짜설계:
    키, 이름, top = "가짜", "가짜", "t"
    RTL, TB, 파라 = [], None, {}


_빠른문턱 = G.관문(_가짜설계(), 빠르게=True)["문턱"]
ok(_빠른문턱["변이수"] >= 12,
   f"**빠른 길에서도 12 밑으로 안 내린다** ({_빠른문턱['변이수']}) — "
   "잡음을 문턱에 대지 않는다")

# ================================================== 3. STA 가 슬랙을 실제로 본다
# 실측 2026-09-22: `슬 is not None` 만 봐서 **-3.15 ns 가 초록**이었다.
import house.synth as SYN          # noqa: E402

_옛sta, _옛합성 = SYN.sta, SYN.합성
_옛lint = None
try:
    from house import sim as SIM
    _옛lint, _옛iv, _옛빌드, _옛돌리기 = SIM.lint, SIM.iverilog_확인, SIM.빌드, SIM.돌리기
    SIM.lint = lambda **k: {"rc": 0, "전체": 0, "종류": {}, "글": ""}
    SIM.iverilog_확인 = lambda **k: {"됐나": True, "글": ""}
    SIM.빌드 = lambda *a, **k: Path("/tmp/x")
    SIM.돌리기 = lambda *a, **k: {"pass": 10, "fail": 0, "timeout": 0,
                              "cov_pct": 99.0, "errs": []}
    SYN.합성 = lambda *a, **k: {"됐나": True, "셀수": 10, "면적_um2": 1.0,
                             "셀종류": {}, "json": None}
    import house.dv.automut as _MUT
    _옛한바퀴 = _MUT.한바퀴
    _MUT.한바퀴 = lambda *a, **k: {"됐나": True, "점수": 1.0, "심은": 20, "잡힌": 20,
                                "놓친": 0, "못지은": 0, "센것": 20, "초": 0.1,
                                "놓친목록": []}

    for 슬랙, 바람 in ((0.5, True), (-3.15, False), (None, False)):
        SYN.sta = lambda 합, 주기=10.0, _s=슬랙: {"최악슬랙_ns": _s, "위반수": 0}
        r = G.관문(_가짜설계(), 벡터=8, 주기_ns=10.0, 빠르게=True)
        칸 = [x for x in r["단계"] if x["관문"].startswith("7.")]
        ok(bool(칸) and 칸[0]["됐나"] is 바람,
           f"**STA 슬랙 {슬랙} → {'통과' if 바람 else '빨강'}** "
           f"({'없다' if not 칸 else 칸[0]['됐나']})")
    SYN.sta = lambda 합, 주기=10.0: {"최악슬랙_ns": -1.0, "위반수": 3}
    r = G.관문(_가짜설계(), 벡터=8, 주기_ns=10.0, 빠르게=True)
    말 = "".join(x["말"] for x in r["단계"] if x["관문"].startswith("7."))
    ok("타이밍이 안 닫혔다" in 말 and "ns 이상으로" in 말,
       "**막기만 하지 않고 무엇을 하면 되는지 말한다** (주기를 얼마로 잡으라)")

    # 커버리지 문턱도 같은 꼴로 -- 낮으면 빨갛다
    SIM.돌리기 = lambda *a, **k: {"pass": 10, "fail": 0, "timeout": 0,
                              "cov_pct": 40.0, "errs": []}
    r = G.관문(_가짜설계(), 벡터=8, 주기_ns=10.0, 빠르게=True)
    칸 = [x for x in r["단계"] if x["관문"].startswith("4b")]
    ok(bool(칸) and not 칸[0]["됐나"],
       "**커버리지 40% 는 빨갛다** — 전에는 퍼센트를 찍기만 했다")
    ok(not r["통과"], "하나라도 빨가면 통과가 아니다")

    # 변이 점수가 낮으면 빨갛다 -- 테스트벤치가 안 무는 것이다
    SIM.돌리기 = lambda *a, **k: {"pass": 10, "fail": 0, "timeout": 0,
                              "cov_pct": 99.0, "errs": []}
    _MUT.한바퀴 = lambda *a, **k: {"됐나": True, "점수": 0.1, "심은": 20, "잡힌": 2,
                                "놓친": 18, "센것": 20, "못지은": 0, "초": 0.1,
                                "놓친목록": []}
    r = G.관문(_가짜설계(), 벡터=8, 주기_ns=10.0, 빠르게=True)
    칸 = [x for x in r["단계"] if x["관문"].startswith("5c")]
    ok(bool(칸) and not 칸[0]["됐나"],
       "**변이 점수 10% 는 빨갛다** — 검사기가 아무것도 안 보는 것이다")
finally:
    SYN.sta, SYN.합성 = _옛sta, _옛합성
    if _옛lint is not None:
        SIM.lint, SIM.iverilog_확인 = _옛lint, _옛iv
        SIM.빌드, SIM.돌리기 = _옛빌드, _옛돌리기
        _MUT.한바퀴 = _옛한바퀴

# ================================================== 4. 프롬프트가 시나리오를 요구한다
_글 = G.TB프롬프트.format(스펙="{}", top="t", 포트="[]",
                     변이문턱=G.기본문턱["변이점수"], 되먹임="")
for 말 in ("백프레셔", "--stall", "프로토콜", "proto", "에러 주입", "지시 시험",
         "경계값", "리셋", "back-to-back", "자해 검사"):
    ok(말 in _글, f"테스트벤치 프롬프트가 `{말}` 를 요구한다")
ok("세려던 빈 목록을 코드에 적어라" in _글,
   "**커버리지 분모를 자극에서 뽑지 말라고 못 박는다** — 그러면 100% 가 공짜다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("보증관문: 변이 엔진 · 문턱 · STA 슬랙 · 커버리지 · 시나리오 -- 통과")
