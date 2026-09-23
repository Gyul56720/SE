# -*- coding: utf-8 -*-
"""**파형에 뽑을 신호를 역할로 고르는가 -- 아니면 이름을 박아 뒀나.**

실측 2026-09-23, `house/rtl/agent.py` 가 파형 네 장면의 신호를 이렇게 박아
두고 있었다.

    u_ctrl.state_o · u_mac.p_s1 · u_icg.en_lat · u_coef_fifo.wgray

nsw_fir 의 인스턴스 이름이다. 다른 회로에서는 하나도 못 찾아 **네 장면이
통째로 빠진다.** 틀린 파형을 그리는 것보다는 낫지만, 그림 넷이 없는 보고서다.

VCD 에는 계층 이름이 그대로 들어 있으니, **거기 실제로 있는 것 중에서**
역할에 맞는 것을 고르면 회로를 안 가린다.

실행: python3 tests/test_파형장면.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
sys.path.insert(0, str(뿌리 / "tests"))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import designs as DES                             # noqa: E402
from house import rtlscan as SCAN                            # noqa: E402
from house import sim as SIM                                 # noqa: E402
from house import report as RPT                              # noqa: E402
from house.dv import scenes as SC                            # noqa: E402
from house.dv import vcd as VCD                              # noqa: E402
import _소스보기                                              # noqa: E402

_소스보기.자기검사()

# **진짜 VCD 를 뜬다.** 파형 고르기는 파일을 봐야 잰다.
_d0 = DES.찾기("fir")
_훑 = SCAN.훑기(_d0.RTL, _d0.top)
_길 = str(RPT.내는곳 / "scenes_검사.vcd")
RPT.내는곳.mkdir(parents=True, exist_ok=True)
SIM.돌리기(None, 설계=_d0, seed=21, txn=6, cap=6000, cfg=3, maxlen=6, dir=2, vcd=_길)
_v = VCD.읽기(_길)
_s = SC.장면들(_v, _훑)

# ============================================ 1. 네 장면이 다 난다
for k in ("fsm", "파이프", "게이팅", "cdc"):
    ok(k in _s and len(_s[k]["신호"]) >= 3,
       f"**{k} 장면이 난다** ({len(_s.get(k, {}).get('신호', []))}개)")
ok(not _s["못찾은것"], f"못 찾은 장면이 없다 ({_s['못찾은것']})")

# ============================================ 2. **VCD 에 있는 이름만** 낸다
_있는것 = set(_v["신호"])
_전부 = [n for k in ("fsm", "파이프", "게이팅", "cdc") for n in _s[k]["신호"]]
ok(all(n in _있는것 for n in _전부),
   f"**고른 신호가 전부 VCD 에 실제로 있다** ({len(_전부)}개) — 지어내지 않는다")

# ============================================ 3. 안 바뀌는 것은 안 낸다
# 파라미터도 VCD 에 신호로 들어 있다(`u_mac.SAT_HI` 폭 40 · `u_ctrl.TAPS` 폭 32).
# 그것을 그리면 평평한 줄만 는다.
_안바뀜 = [n for n in _있는것 if len(_v["신호"][n] or []) <= 1]
ok(_안바뀜, f"VCD 에 **안 바뀌는 신호가 실제로 있다** ({len(_안바뀜)}개, "
   f"예: {sorted(_안바뀜)[:2]})")
ok(not (set(_전부) & set(_안바뀜)),
   "**안 바뀌는 신호(파라미터)를 안 뽑는다**")

# ============================================ 4. **부분문자열로 안 고른다**
# 첫 판은 FSM 이름 `st` 를 `fsm이름 in 잎` 으로 찾아서 **다른 인스턴스의
# `wrst_n`** 이 FSM 장면에 끼었다. `ack` 가 `backpressure` 속에 든 것과 같다.
ok(not any("rst_n" in n for n in _s["fsm"]["신호"]),
   f"**FSM 장면에 `wrst_n` 이 안 낀다** — `st` 가 그 안에 들어 있다 "
   f"({[n.rsplit('.', 1)[-1] for n in _s['fsm']['신호']]})")
_fsm자리 = {n.rsplit(".", 1)[0] for n in _s["fsm"]["신호"] if "clk" not in n}
ok(len(_fsm자리) == 1,
   f"FSM 장면의 신호가 **한 자리에서** 난다 ({_fsm자리})")

# ============================================ 5. 파이프라인 단이 다 나온다
_단 = [n.rsplit(".", 1)[-1] for n in _s["파이프"]["신호"]]
ok(sum(1 for x in _단 if x.endswith(("_s1", "_s2", "_s3"))) >= 6,
   f"**단 신호가 다 나온다** ({_단}) — 마지막 단이 빠지면 미는 것이 안 보인다")

# ============================================ 6. wclk 도 클럭이다
_클 = SC.클럭들(_v)
ok(any(n.endswith(".wclk") for n in _클),
   f"**`wclk` 를 클럭으로 본다** ({[n.rsplit('.', 1)[-1] for n in _클]}) — "
   f"첫 판은 `clk` 앞이 `w` 라 못 잡아 CDC 장면에 클럭이 없었다")

# 게이팅된 클럭은 **가장 적게 토글하는** 것이다
_게클럭 = [n for n in _s["게이팅"]["신호"] if "clk" in n.rsplit(".", 1)[-1].lower()]
_적은 = min(_클, key=lambda n: len(_v["신호"][n]))
ok(_적은 in _게클럭,
   f"**게이팅된 클럭(토글이 가장 적은 것)이 장면에 든다** "
   f"({_적은.rsplit('.', 1)[-1]}, 변화 {len(_v['신호'][_적은])})")

# ============================================ 7. 상태 이름표가 난다
_표 = SC.이름표(_훑)
ok(_표 and all(v.startswith("S_") for v in _표.values()),
   f"**상태 이름표를 스캔의 선언값에서 만든다** ({sorted(set(_표.values()))})")
ok(SC.띠신호(_v, _훑).endswith(".st"),
   f"띠에 그릴 상태 신호를 찾는다 ({SC.띠신호(_v, _훑)})")
ok(SC.이름표({}) == {} and SC.장면들(_v, {})["못찾은것"],
   "스캔이 비면 **빈 이름표와 못 찾은 목록** — 지어내지 않는다")

# ============================================ 8. 에이전트가 이것을 쓴다
_산 = _소스보기.산주장((뿌리 / "house" / "rtl" / "agent.py").read_text(encoding="utf-8"))
ok("from house.dv import scenes as SCENE" in _산 and "SCENE.장면들" in _산,
   "**rtl 에이전트가 이것을 실제로 부른다**")
for 없어야 in ('"u_ctrl.state_o"', '"u_mac.p_s1"', '"u_icg.en_lat"',
             '"u_coef_fifo.wgray"', '{"1": "IDLE"'):
    ok(없어야 not in _산, f"**지웠다**: 박혀 있던 {없어야}")
ok(_s["못하는것"], "못 하는 것을 같이 돌려준다 (게이팅 클럭은 구조가 아니라 셈이다)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("파형장면: 역할로 고른다 · VCD 에 있는 것만 · 부분문자열로 안 고른다 -- 통과")
