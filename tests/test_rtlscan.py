# -*- coding: utf-8 -*-
"""**RTL 훑기가 회로를 안 가리는가 -- 답을 아는 회로로 잰다.**

사용자(2026-09-22): **"fir 만든걸 mera에 못쓰는건 제대로된 에이전트가 아니야."**

맞는 말이다. 다섯 에이전트에 `회로=` 를 뚫은 것은 **배관**이었고, 안에 든 분석은
여전히 `nsw_fir` 을 손으로 적어 둔 것이었다. 회로를 안 가리려면 **RTL 글에서
읽어 내야** 한다.

**여기서는 답을 미리 아는 회로를 지어 잰다.** `nsw_fir` 으로만 확인하면 그 회로에
맞춰 정규식을 맞춘 것인지, 정말로 읽는 것인지 못 가른다.

실행: python3 tests/test_rtlscan.py
"""
from __future__ import annotations

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


from house import rtlscan as S      # noqa: E402

# ------------------------------------------------------------------ 답을 아는 회로
#
# 일부러 이렇게 넣었다:
#   · 클럭 둘 (wclk · rclk)  -- CDC 가 있다
#   · 비동기 리셋 하나(arst_n) · 동기 리셋 하나(srst)
#   · `begin` 없는 `if/else` 사슬 -- 첫 판이 여기서 `else` 를 통째로 놓쳤다
#   · 조합 블록에 `else` 가 없는 `if` -- 래치 위험
#   · case 문 하나 -- FSM 후보
#   · 주석과 문자열 안의 미끼
답아는회로 = r"""
// 이 주석에는 posedge fake_clk 와 a * b 가 있다 -- 읽으면 안 된다
module tiny #(parameter W = 8, parameter DEPTH = 4) (
  input  wire              wclk,
  input  wire              rclk,
  input  wire              arst_n,
  input  wire              srst,
  input  wire [W-1:0]      din,
  output reg  [W-1:0]      dout
);
  localparam [1:0] S_IDLE = 2'd0,
                   S_RUN  = 2'd1,
                   S_HOLD = 2'd2;
  reg [1:0] st;
  reg [W-1:0] wptr;
  reg [W-1:0] wptr_sync;
  wire [W-1:0] prod = din * din;
  wire [W-1:0] diff = din - 1;

  // begin 이 없는 if/else 사슬 -- else 가지의 wptr 을 봐야 한다
  always @(posedge wclk or negedge arst_n)
    if (!arst_n) wptr <= 0;
    else         wptr <= wptr + 1;

  always @(posedge rclk)
    if (srst) wptr_sync <= 0;
    else      wptr_sync <= wptr;

  // 조합인데 else 가 없다 -- 래치 위험
  always @(*)
    if (st == S_RUN) dout = prod;

  // **콜론 앞에 공백을 둔다** -- 이 저장소의 RTL 이 그렇게 쓴다.
  // 첫 판은 `S_IDLE:` 로만 경계를 찾아 한 번도 안 맞았고, 그래서 각 가지가
  // case 문 끝까지 흘러 **없는 천이**를 만들었다.
  always @(posedge wclk or negedge arst_n) begin
    if (!arst_n) st <= S_IDLE;
    else case (st)
      S_IDLE : if (srst) st <= S_RUN;
      S_RUN  : if (wptr[0]) st <= S_HOLD;
      S_HOLD : st <= S_IDLE;
      default: st <= S_IDLE;
    endcase
  end
endmodule
"""

with tempfile.TemporaryDirectory() as _d:
    _p = Path(_d) / "tiny.sv"
    _p.write_text(답아는회로, encoding="utf-8")
    r = S.훑기([_p], "tiny")

ok(r["됐나"], "읽었다")
ok(r["모듈"] == ["tiny"], f"모듈 하나를 찾는다 ({r['모듈']})")
ok(sorted(r["클럭"]) == ["rclk", "wclk"],
   f"**클럭 둘을 찾는다** ({r['클럭']}) — 주석의 `fake_clk` 는 안 센다")
ok("fake_clk" not in str(r["클럭"]), "**주석 안의 클럭에 안 속는다**")
ok("arst_n" in r["비동기리셋"],
   f"비동기 리셋을 민감도 목록에서 찾는다 ({r['비동기리셋']})")
ok("srst" in r["동기리셋"],
   f"**동기 리셋은 몸통에서 찾는다** ({r['동기리셋']}) — 민감도에 없다")

# **`else` 가지를 봐야 CDC 가 보인다.** 첫 판은 `begin` 이 없으면 첫 `;` 에서
# 끊었고, 그래서 `else wptr <= wptr + 1;` 이 통째로 안 보였다. 그 결과
# nsw_fir(비동기 FIFO 가 빤히 있는 회로)의 CDC 건넘이 **0개**로 나왔다.
_건 = {x["신호"] for x in r["CDC건넘"]}
ok("wptr" in _건,
   f"**CDC 건넘을 찾는다: `wptr` 은 wclk 에서 쓰이고 rclk 에서 읽힌다** ({sorted(_건)})")
_w = next((x for x in r["CDC건넘"] if x["신호"] == "wptr"), None)
ok(_w and _w["보내는곳"] == ["wclk"] and _w["받는곳"] == ["rclk"],
   f"어느 쪽에서 어느 쪽으로 가는지까지 안다 ({_w})")

ok(r["순차블록"] == 3, f"순차 블록 3개 ({r['순차블록']})")
ok(r["조합블록"] == 1, f"조합 블록 1개 ({r['조합블록']})")
ok(len(r["래치위험"]) == 1,
   f"**`else` 없는 조합 블록을 래치 위험으로 짚는다** ({len(r['래치위험'])}개)")
ok(len(r["FSM"]) == 1, f"FSM 후보 하나 ({len(r['FSM'])})")
_f0 = r["FSM"][0]
# **한 `localparam` 이 이름을 여럿 선언한다.** 첫 이름만 잡으면 상태가 하나로 보인다.
ok(_f0["상태후보"] == ["S_IDLE", "S_RUN", "S_HOLD"],
   f"**상태 셋을 다 찾는다** ({_f0['상태후보']}) — 한 줄에 여럿 선언돼 있다")
# **라벨 뒤의 공백.** `S_IDLE : ...` 을 못 끊으면 가지가 case 끝까지 흘러
# 없는 천이(`S_IDLE -> S_HOLD`)가 그려진다. 그림은 사람이 믿는다.
_전 = {(a, b) for a, b, _ in _f0["전이"]}
ok(_전 == {("S_IDLE", "S_RUN"), ("S_RUN", "S_HOLD"), ("S_HOLD", "S_IDLE")},
   f"**천이를 정확히 셋만 찾는다** ({sorted(_전)}) — "
   "콜론 앞 공백을 못 읽으면 없는 천이가 생긴다")
ok(not any(b == "S_HOLD" for a, b, _ in _f0["전이"] if a == "S_IDLE"),
   "**`S_IDLE -> S_HOLD` 같은 없는 천이를 안 만든다**")
_조건 = {a: c for a, b, c in _f0["전이"]}
ok(_조건.get("S_IDLE") == "srst",
   f"**조건도 RTL 에서 읽는다** ({_조건.get('S_IDLE')!r}) — 지어내지 않는다")
ok(_조건.get("S_HOLD") == "",
   f"**조건이 없으면 빈 글이다** ({_조건.get('S_HOLD')!r}) — 없는 조건을 안 적는다")
ok(set(r["파라미터"]) == {"W", "DEPTH"}, f"파라미터 둘 ({sorted(r['파라미터'])})")
ok(r["파라미터"].get("W", "").strip() == "8", f"기본값도 읽는다 (W={r['파라미터'].get('W')})")
ok({p["이름"] for p in r["포트"]} == {"wclk", "rclk", "arst_n", "srst", "din", "dout"},
   f"포트 여섯 ({sorted(p['이름'] for p in r['포트'])})")

# **주석의 `a * b` 를 곱셈으로 세면 안 된다.** 실제 곱셈은 `din * din` 하나뿐이다.
ok(r["산술"]["곱셈"] == 1, f"곱셈 하나 ({r['산술']['곱셈']}) — 주석의 `a * b` 는 안 센다")
# **`[W-1:0]` 의 빼기를 데이터패스 뺄셈으로 세면 안 된다.** 실측: 첫 판이
# nsw_fir 에서 뺄셈 51개를 냈는데 거의 다 비트폭 계산이었다.
ok(r["산술"]["뺄셈"] == 1,
   f"**뺄셈 하나** ({r['산술']['뺄셈']}) — `[W-1:0]` 의 빼기는 데이터패스가 아니다")

# **다 읽은 척하지 않는다.**
ok(r["못보는것"], "못 보는 자리를 결과에 적는다 — 다 읽은 척하면 그 표를 믿게 된다")

# ------------------------------------------------------------------ 진짜 회로에서도
from house import designs as DES    # noqa: E402

_f = S.훑기(DES.NSW_FIR.RTL, DES.NSW_FIR.top)
ok(_f["됐나"] and len(_f["클럭"]) >= 2,
   f"nsw_fir: 클럭 여럿을 찾는다 ({_f['클럭']})")
ok(len(_f["CDC건넘"]) >= 1,
   f"**nsw_fir: CDC 건넘을 찾는다** ({len(_f['CDC건넘'])}개) — "
   "비동기 FIFO 가 있는 회로에서 0개가 나오면 안 읽은 것이다")
_ffsm = (_f.get("FSM") or [{}])[0]
ok(sorted(x[0] for x in _ffsm.get("전이", [])) ==
   ["S_DONE", "S_FLUSH", "S_IDLE", "S_LOAD", "S_RUN"],
   f"**nsw_fir: 다섯 상태에서 각각 나가는 천이를 찾는다** "
   f"({[(a, b) for a, b, _ in _ffsm.get('전이', [])]})")
ok(len(_f["래치위험"]) >= 1,
   "nsw_fir: 클럭게이팅 래치를 짚는다 (이 회로에서는 **일부러 넣은** 래치다)")

# 없는 파일에도 안 죽는다
ok(S.훑기([Path("/없다/없어.sv")], "x")["됐나"] is False, "못 읽으면 그렇게 말한다")
ok(S.훑기([], "x")["됐나"] is False, "빈 목록도 받는다")

# 데이터패스 식은 **크기만 흉내낸 것**이라고 doc 에 적혀 있어야 한다
ok("회로의 식이 아니다" in (S.데이터패스식.__doc__ or "")
   and "거짓말" in (S.데이터패스식.__doc__ or ""),
   "**`데이터패스식()` 이 제 한계를 제 문서에 적는다** — "
   "이 회로의 데이터패스라고 하면 거짓말이 된다")
ok(S.데이터패스식({"산술": {"곱셈": 4}}).count("*") == 4, "곱셈 수를 따라간다")
# **한 항짜리 식은 설계공간이 없다** -- 곱셈기 4개든 1개든 스케줄이 같아서
# 표 세 줄이 글자까지 똑같아진다. 아무 말도 안 하는 표를 내느니 최소 둘로 둔다.
ok(S.데이터패스식({"산술": {"곱셈": 0}}).count("*") >= 2,
   f"**0 이어도 두 항 이상** ({S.데이터패스식({'산술': {'곱셈': 0}})}) — 한 항이면 표가 퇴화한다")
ok(S.데이터패스식({"산술": {"곱셈": 99}}).count("*") == 4, "위로는 4개에서 멈춘다")


# ============================== 보고서가 훑기 결과로 서는가 (손으로 적은 글 걷어내기)
# **실측 2026-09-22.** `cdc점검()` 이 건넘 목록을 이렇게 만들고 있었다.
#
#     if "u_coef_fifo" in 글:
#         건넘.append({"신호": "cfg_coef[15:0] + cfg_we", ...})
#
# `nsw_fir` 의 **인스턴스 이름**이 코드에 박혀 있다. 다른 회로를 넘기면 건넘이
# 0개가 되고, 보고서는 "맨선 0개 · 판정 통과" 라고 적는다 -- **안 본 것을 통과로
# 적는 것**이다. 그것이 가장 나쁜 꼴이다.
print("\n[보고서가 회로를 따라가는가]")
from house.rtl import agent as AG      # noqa: E402

with tempfile.TemporaryDirectory() as _d3:
    _p3 = Path(_d3) / "tiny.sv"
    _p3.write_text(답아는회로, encoding="utf-8")
    _설계3 = DES.설계(키="tiny", 이름="TINY", top="tiny", RTL=[_p3])
    _훑3 = S.훑기(_설계3.RTL, _설계3.top)
    _c = AG.cdc점검(설계=_설계3, 훑기=_훑3)

ok(_c["도메인"] == {"wclk": 2, "rclk": 1},
   f"**클럭 도메인을 이 회로에서 센다** ({_c['도메인']})")
ok([x["신호"] for x in _c["건넘"]] == ["wptr"],
   f"**건넘도 이 회로에서 찾는다** ({[x['신호'] for x in _c['건넘']]}) — "
   "`u_coef_fifo` 같은 FIR 의 인스턴스 이름에 안 기댄다")
ok(_c["판정"] != "통과",
   f"**안 본 것을 '통과' 로 안 적는다** (판정: {_c['판정']})")
ok(all(x.get("안전") is None for x in _c["건넘"]),
   "**'안전하다' 고 안 적는다** — 이 훑기는 모양만 본다. "
   "다단이라고 안전한 것이 아니다(여러 비트가 같이 건너면 2FF 로도 깨진다)")
ok(_c.get("못보는것"), "못 보는 것을 같이 돌려준다")

# 건넘이 없는 회로에서는 '건넘 없음' 이라고 한다 -- '통과' 가 아니다
_민2 = "module one(input c, input d, output reg q);\n always @(posedge c) q <= d;\nendmodule\n"
with tempfile.TemporaryDirectory() as _d4:
    _p4 = Path(_d4) / "one.sv"
    _p4.write_text(_민2, encoding="utf-8")
    _c2 = AG.cdc점검(설계=DES.설계(키="one", 이름="one", top="one", RTL=[_p4]))
ok(_c2["건넘"] == [] and "없음" in _c2["판정"],
   f"**클럭이 하나면 '건넘 없음'** ({_c2['판정']}) — 검사했다는 뜻이 아니다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("rtlscan: 클럭 · 리셋 · CDC · 래치 · FSM · 파라미터 · 산술 -- 통과")
