# -*- coding: utf-8 -*-
"""**DV 가 회로에서 시나리오를 설계하는가 -- 답을 아는 회로로 잰다.**

사용자(2026-09-22): 내가 *"DV 의 기준모델은 범용일 수 없다"* 고 적었더니 --
**"이건 DV agent 가 시나리오 설계하는 기능을 추가해야지."**

맞는 말이고, 내가 두 가지를 뭉쳐서 말했다.

    기준모델(무엇이 옳은 값인가)   -- 회로마다 다르다. 스펙에서 나온다
    시나리오(무엇을 시험할 것인가) -- **회로에서 기계로 뽑을 수 있다**

두 번째는 범용이다. 팹리스의 검증 계획이 실제로 그렇게 만들어진다 -- 사람이
창의적으로 지어내는 것이 아니라 **인터페이스에서 따라 나온다.**

**여기서도 답을 미리 아는 회로를 지어 잰다.** 그 회로에 없는 시나리오가 나오면
그것은 설계한 것이 아니라 지어낸 것이고, 있는데 안 나오면 못 읽은 것이다.

실행: python3 tests/test_dv계획.py
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


from house import designs as DES        # noqa: E402
from house import rtlscan as SCAN       # noqa: E402
from house.dv import plan as P          # noqa: E402

# ------------------------------------------------------------------ 답을 아는 회로
#
# 일부러 이렇게 넣었다:
#   · `s_axis_tvalid`/`s_axis_tready` 짝  -> 백프레셔 세 가지
#   · `m_axi_wvalid` 는 짝이 없다          -> "ready 짝 없음" 하나
#   · `s_axis_tlast`                      -> 패킷 경계 셋
#   · `s_axis_tkeep`                      -> 부분 바이트
#   · 클럭 둘 + CDC                       -> 클럭비 쓸기
#   · FSM 상태 셋 (한 줄에 여럿 선언)      -> 상태 빈 셋
#   · `DEPTH`(깊이) 와 `STAGES`(단수)      -> **서로 다른 시나리오**
#   · `ovf_sticky`                        -> 오류 주입
답아는회로 = r"""
module rec #(parameter DW = 32, parameter DEPTH = 16, parameter STAGES = 3) (
  input  wire              aclk,
  input  wire              cfg_clk,
  input  wire              aresetn,
  input  wire [DW-1:0]     s_axis_tdata,
  input  wire              s_axis_tvalid,
  output wire              s_axis_tready,
  input  wire              s_axis_tlast,
  input  wire [DW/8-1:0]   s_axis_tkeep,
  output wire [DW-1:0]     m_axi_wdata,
  output wire              m_axi_wvalid,
  output wire              ovf_sticky
);
  localparam [1:0] S_IDLE = 2'd0,
                   S_CAP  = 2'd1,
                   S_DRAIN= 2'd2;
  reg [1:0] st;
  reg [7:0] wptr;
  reg [7:0] wptr_x;

  always @(posedge aclk or negedge aresetn)
    if (!aresetn) wptr <= 0;
    else          wptr <= wptr + 1;

  always @(posedge cfg_clk)
    wptr_x <= wptr;

  always @(posedge aclk or negedge aresetn) begin
    if (!aresetn) st <= S_IDLE;
    else case (st)
      S_IDLE:  st <= S_CAP;
      S_CAP:   st <= S_DRAIN;
      S_DRAIN: st <= S_IDLE;
      default: st <= S_IDLE;
    endcase
  end
endmodule
"""

with tempfile.TemporaryDirectory() as _d:
    _p = Path(_d) / "rec.sv"
    _p.write_text(답아는회로, encoding="utf-8")
    _설계 = DES.설계(키="rec", 이름="REC", top="rec", RTL=[_p])
    계 = P.세우기(_설계)

ok(계["됐나"], f"시나리오를 세웠다 ({len(계['시나리오'])}개 · 빈 {len(계['빈'])}개)")
_id = {x["id"] for x in 계["시나리오"]}


def 있나(조각):
    return any(조각 in i for i in _id)


# ---- 핸드셰이크: 짝이 있는 것과 없는 것을 가른다
ok(있나("hs_s_axis_t_stall0") or 있나("stall0"),
   f"**백프레셔 없음 시나리오** ({sorted(i for i in _id if i.startswith('hs'))})")
ok(any("stall_high" in b for b in 계["빈"]), "**백프레셔 최대** 빈이 있다")
ok(any("hold_ok" in b for b in 계["빈"]),
   "**valid 유지 규칙** — AXI 의 기본 규칙을 시나리오로 세운다")
ok(있나("noready"),
   "**짝 없는 valid(`m_axi_wvalid`)는 따로 짚는다** — 받는 쪽이 항상 받는다는 "
   "가정이 스펙에 있는지 사람이 봐야 한다")

# ---- 패킷 경계와 바이트 마스크
ok(any("len1" in b for b in 계["빈"]), "`tlast` 에서 한 beat 패킷을 뽑는다")
ok(any("back2back" in b for b in 계["빈"]), "연속 패킷을 뽑는다")
ok(any("partial" in b for b in 계["빈"]), "`tkeep` 에서 부분 바이트를 뽑는다")

# ---- 리셋
ok(any("mid_txn" in b for b in 계["빈"]),
   "**트래픽 한가운데 리셋** — 가장 자주 빠지는 시나리오다")
ok(any("release" in b for b in 계["빈"]), "비동기 리셋의 해제 시점을 쓸어 본다")

# ---- CDC
ok(있나("cdc_wptr"),
   f"**CDC 건넘에서 클럭비 쓸기를 뽑는다** ({sorted(i for i in _id if 'cdc' in i)})")
_c = next((x for x in 계["시나리오"] if x["id"].startswith("cdc_")), None)
ok(_c and len(_c["빈"]) == 3, "느리게 · 같게 · 빠르게 세 빈")

# ---- FSM: **한 줄에 여럿 선언된 상태를 다 찾아야 한다**
# 실측 2026-09-22: `localparam [4:0] S_IDLE = ..., S_LOAD = ...` 에서 첫 이름만
# 잡아 **상태 다섯 중 하나만** 나왔다. "모든 상태 방문" 이라 적고 한 상태만 세는 꼴.
_f = next((x for x in 계["시나리오"] if x["id"].endswith("_all")), None)
ok(_f and len(_f["빈"]) == 3,
   f"**FSM 상태 셋을 다 찾는다** ({_f['빈'] if _f else '없다'}) — "
   "한 `localparam` 이 이름을 여럿 선언한다")

# ---- 깊이와 단수를 **가른다**
# 실측: `STAGES=3` 에 "가득참·비어있음·되돌이" 가 붙었다. 파이프라인 단수에는
# 가득참도 되돌이도 없다 -- 그럴듯하지만 뜻이 없는 줄이다.
ok(있나("depth_DEPTH"), "깊이 파라미터에서 가득참/비어있음/되돌이")
ok(있나("pipe_STAGES"), "**단수 파라미터는 채움/비움이지 되돌이가 아니다**")
ok(not any(b.startswith("STAGES_wrap") for b in 계["빈"]),
   "**`STAGES_wrap` 같은 뜻 없는 빈을 안 만든다**")

# ---- 오류 플래그
ok(any("err_set" in b for b in 계["빈"]),
   "**오류 플래그는 세우는 조건과 안 세우는 조건을 둘 다** — 서는 것만 보면 절반이다")

# ---- 데이터 경계: 파라미터 폭도 데이터다
# 실측: `[DW-1:0]` 은 `_폭수()` 가 None 을 내는데 `(None or 0) > 1` 이 거짓이라
# **데이터 포트가 전부 걸러졌다.**
ok(있나("data_s_axis_tdata"),
   f"**파라미터 폭(`[DW-1:0]`)도 데이터 포트로 본다** "
   f"({sorted(i for i in _id if i.startswith('data'))})")

# ---- 줄마다 출처가 있다
ok(all(x.get("출처") for x in 계["시나리오"]),
   "**시나리오마다 출처가 있다** — 출처가 없으면 설계한 것이 아니라 지어낸 것이다")
ok(all(x.get("빈") for x in 계["시나리오"]), "시나리오마다 커버 빈이 있다")
ok(len(계["빈"]) == len(set(계["빈"])), "커버 빈이 안 겹친다 (분모가 부풀면 안 된다)")

# ---- 못 뽑는 것을 적는다
ok(any("골든" in x or "기준모델" in x for x in 계["못뽑는것"]),
   "**기준모델은 여기서 못 뽑는다고 적는다** — 빈 목록을 '다 덮었다' 로 읽으면 안 된다")

# ---- 프롬프트 글에 분모가 박힌다
_글 = P.계획글(계)
ok(f"빈 {len(계['빈'])}개" in _글,
   "**커버리지 분모를 프롬프트에 못 박는다** — 자극에서 뽑으면 100% 가 공짜다")
ok(계["시나리오"][0]["왜"] in _글, "왜 필요한지까지 모델에게 준다")

# ---- 인터페이스가 없는 회로에서는 조용하다
_민 = "module bare(input c, output o); assign o = c; endmodule\n"
with tempfile.TemporaryDirectory() as _d2:
    _q = Path(_d2) / "bare.sv"
    _q.write_text(_민, encoding="utf-8")
    _계2 = P.세우기(DES.설계(키="bare", 이름="bare", top="bare", RTL=[_q]))
ok(not any(i.startswith("hs_") for i in {x["id"] for x in _계2["시나리오"]}),
   "**핸드셰이크가 없으면 백프레셔 시나리오를 안 지어낸다**")

# ---- 진짜 회로에서도
_f2 = P.세우기(DES.NSW_FIR)
ok(_f2["됐나"] and len(_f2["시나리오"]) >= 10,
   f"nsw_fir: 시나리오 {len(_f2['시나리오'])}개 · 빈 {len(_f2['빈'])}개")
_fsm = next((x for x in _f2["시나리오"] if x["id"].endswith("_all")), None)
ok(_fsm and len(_fsm["빈"]) == 5,
   f"**nsw_fir 의 FSM 상태 다섯을 다 찾는다** ({_fsm['빈'] if _fsm else '없다'})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("dv계획: 핸드셰이크 · 패킷 · 리셋 · CDC · FSM · 깊이/단수 · 오류 · 출처 -- 통과")
