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
  localparam S_IDLE = 2'd0;
  localparam S_RUN  = 2'd1;
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

  always @(posedge wclk or negedge arst_n) begin
    if (!arst_n) st <= S_IDLE;
    else case (st)
      S_IDLE: st <= S_RUN;
      S_RUN:  st <= S_IDLE;
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

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("rtlscan: 클럭 · 리셋 · CDC · 래치 · FSM · 파라미터 · 산술 -- 통과")
