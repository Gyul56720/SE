# -*- coding: utf-8 -*-
"""**요구사항과 시나리오가 이어지는가 -- 답을 아는 포트 목록으로 잰다.**

업계 사슬의 첫 화살표다.

    요구사항(REQ-ID) --여기--> 시나리오 -> 커버 빈 -> PASS/FAIL -> 되짚기

**여기서 가장 중요한 것은 거짓 링크를 안 내는 것이다.** 두 쪽 다 출처에 포트
이름을 적으므로 낱말로 이으면 `in_vld` 물음 하나가 `in_vld` 시나리오 **전부**에
걸린다 -- "리셋 중 valid 가 0인가" 가 "백프레셔 최대" 에 걸리는 식이다.
그러면 사람은 그 요구사항이 시험된다고 믿는다. **검사하지 않은 초록불이
검사한 빨간불보다 나쁘다.** 그래서 두 쪽을 다 잰다:
짝이 있는 물음은 **걸리는가**, 짝이 없는 물음은 **안 걸리는가**.

실행: python3 tests/test_요구사항추적.py
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


from house import spec as SPEC          # noqa: E402
from house import specq as SPECQ        # noqa: E402
from house import req as REQ            # noqa: E402
from house.dv import plan as PLAN       # noqa: E402
from house.dv import trace as TRACE     # noqa: E402

# **짝이 다 있는 포트 목록.** valid 와 ready 가 짝이라 `hs_*_hold` 가 난다.
_포트 = [{"이름": n, "방향": d, "폭": w} for n, d, w in (
    ("aclk", "input", 1), ("aresetn", "input", 1),
    ("s_axis_tvalid", "input", 1), ("s_axis_tready", "output", 1),
    ("s_axis_tdata", "input", "[255:0]"), ("s_axis_tlast", "input", 1),
    ("s_axis_tkeep", "input", "[31:0]"), ("ovf_sticky", "output", 1),
)]
# **표에 네 갈래를 다 둔다.** 걸리는 것 둘(개수 · 깊이) · 관문이 재는 것 하나
# (주파수) · **아무것도 못 하는 것 하나**(`헤더 서식 CRC32` -- 수가 있지만
# 무슨 수인지 모른다). 넷째 줄이 이 검사의 자물쇠다: 수가 있다고 시나리오를
# 지어내기 시작하면 커버리지 분모가 뜻 없이 부푼다.
_요청 = ("# REC-1 기록기\n\n| 항목 | 값 |\n|---|---|\n"
       "| 채널 수 | 4 |\n| PRE 깊이 | 4096 sample |\n| 헤더 서식 | CRC32 |\n\n"
       "AXI4-Stream 256-bit 입력. 500 MHz. 누산기를 쓴다.")
_s = SPEC.읽기(_요청)
_s.이름 = "REC-1"
_s.포트 = _포트
_미 = SPECQ.세우기(_s)
_요 = REQ.붙이기(_s, _미)
_계획 = PLAN.세우기(훑기={"포트": _포트, "비동기리셋": ["aresetn"]}, 스펙=_s)
t = TRACE.걸기(_요, _계획)

_걸린 = {r["id"]: r["검증"] for r in t["요구사항"]}
_물음별 = {}
for r in t["요구사항"]:
    q = TRACE._물음에서(r)
    if q:
        _물음별[q] = r["검증"]

# ============================================ 1. 짝이 있는 물음은 걸린다
ok(t["됐나"] and t["걸린수"] >= 5, f"시나리오가 걸린다 ({t['걸린수']}개)")
for q, 꼴 in (("q_valid_hold", "_hold"), ("q_reset_valid", "_rstvalid"),
            ("q_pkt_len", "pkt_"), ("q_partial", "strb_"),
            ("q_err_clear", "err_inject")):
    ok(any(꼴 in i for i in _물음별.get(q) or []),
       f"`{q}` 가 `{꼴}` 시나리오에 걸린다 ({_물음별.get(q)})")

# ============================================ 2. **거짓 링크를 안 낸다**
# 같은 포트에서 나왔다고 거는 것이 이 파일이 가장 조심하는 것이다.
ok(not any("stall" in i for i in _물음별.get("q_reset_valid") or []),
   "**«리셋 중 valid=0» 이 «백프레셔» 에 안 걸린다** — 같은 포트지만 다른 물음이다")
ok(not any("_hold" in i for i in _물음별.get("q_reset_valid") or []),
   "**«리셋 중 valid=0» 이 «valid 유지» 에 안 걸린다**")
ok(not any("rstvalid" in i for i in _물음별.get("q_valid_hold") or []),
   "**«valid 유지» 가 «리셋 중 valid» 에 안 걸린다**")

# 짝이 없는 물음은 **비어 있어야** 한다 -- 곁에 있다고 걸면 거짓 초록이다.
for q in ("q_overflow", "q_round", "q_accw", "q_throughput", "q_latency"):
    ok(not (_물음별.get(q) or []),
       f"`{q}` 는 **안 걸린 채로 둔다** — 그 물음을 가리는 시나리오가 없다")
ok("q_overflow" not in TRACE.이음표,
   "`q_overflow` 를 `err_inject` 에 **안 잇는다** — 그것은 플래그가 서는지만 본다")

# ============================================ 3. **요청 표가 못박은 수도 걸린다**
# 실측 2026-09-22: 처음에는 여섯 줄이 전부 «없다» 였다. 위의 시나리오가 전부
# 인터페이스에서 나오는데, 사람이 제 손으로 적은 수는 인터페이스에 안 나타난다.
_표줄 = {x["글"].split(":")[0].split(" = ")[0].strip(): x for x in t["요구사항"]
       if x["상태"] == "못박힘"}
ok(any("cnt_" in i for i in (_표줄.get("채널 수") or {}).get("검증") or []),
   f"**«채널 수 4» 가 걸린다** ({(_표줄.get('채널 수') or {}).get('검증')})")
ok(any("depth" in i for i in (_표줄.get("PRE 깊이") or {}).get("검증") or []),
   f"**«PRE 깊이 4096» 이 걸린다** ({(_표줄.get('PRE 깊이') or {}).get('검증')})")

# 시나리오 id 와 커버 빈은 **테스트벤치의 함수 이름**이 되는 자리다 -- ASCII 여야 한다
_표시나리오 = [x for x in _계획["시나리오"] if x.get("표항목")]
ok(_표시나리오 and all(x["id"].isascii() and all(b.isascii() for b in x["빈"])
                   for x in _표시나리오),
   f"**표에서 난 시나리오의 id·빈이 ASCII 다** ({[x['id'] for x in _표시나리오]})")

# ============================================ 3b. **없는 관문을 있다고 안 한다**
_주 = _표줄.get("주파수_Hz") or {}
ok((_주.get("관문") or "").startswith("관문 7"),
   f"**동작 주파수는 관문 7(STA)이 잰다** — 「시험 없음」으로 적으면 거짓 빨간불 "
   f"({_주.get('관문')})")
from house.dv import plan as _P                                     # noqa: E402
ok(_P.표줄갈래("샘플레이트", "2.5 GSPS")[0] == "속도"
   and _P.표줄갈래("주파수", "500 MHz")[0] == "클럭",
   "**샘플레이트와 주파수를 가른다** — 하나는 관문이 있고 하나는 없다")

# ============================================ 3c. **수가 있다고 지어내지 않는다**
# `헤더 서식 CRC32` 에는 수 32 가 있다. 그렇다고 시나리오를 지으면 안 된다.
ok(_P.표줄갈래("헤더 서식", "CRC32")[0] == "",
   "**«헤더 서식 CRC32» 는 갈래가 없다** — 수가 있다고 시나리오를 지어내지 않는다")
_헤 = _표줄.get("헤더 서식") or {}
ok(_헤 and not _헤.get("검증") and not _헤.get("관문"),
   "못 가르는 줄은 **안 걸린 채로 남는다** — 그것이 사람에게 갈 말이다")

# ============================================ 3d. 안 걸린 것을 말한다
ok(all(x["상태"] != "TBD" for x in t["안걸린"]),
   "**«시험이 없는 요구사항» 에 TBD 를 안 섞는다** — 섞으면 그 수가 물음 수가 된다")
ok(isinstance(t["안걸린TBD"], list), "아직 TBD 인 것은 따로 센다")
ok(any(x["상태"] == "못박힘" for x in t["안걸린"]),
   f"못 가른 못박힌 수를 드러낸다 ({[x['글'][:18] for x in t['안걸린']][:3]})")
ok(t["떠있는수"] >= 1 and all(x["id"] for x in t["떠있는시나리오"]),
   f"거꾸로, 요구사항에 안 걸린 시나리오도 센다 ({t['떠있는수']}개)")
ok(t["걸린수"] + t["안걸린수"] + len(t["안걸린TBD"]) + len(t["관문이잰다"])
   == len(t["요구사항"]),
   "네 수를 더하면 요구사항 수가 된다 — 어느 줄도 안 샌다")

# ============================================ 4. 요구 줄에 칸이 실제로 박힌다
ok(all("검증" in r for r in t["요구사항"]), "줄마다 `검증` 칸이 박힌다")
_빈있는 = [r for r in t["요구사항"] if r["검증"]]
ok(_빈있는 and all(r["빈"] for r in _빈있는),
   "걸린 줄은 **커버 빈**까지 들고 온다 — 사슬의 다음 칸이다")

# ============================================ 5. 포트가 없어도 자리를 만든다
_포트없음 = SPEC.읽기("AXI4-Stream 입력, AXI4-Lite 제어, sticky flag. 500 MHz. aresetn.")
_세운것 = TRACE.포트세우기(_포트없음, SPECQ.세우기(_포트없음))
ok(_세운것 and any("tvalid" in p["이름"] for p in _세운것),
   f"**포트가 아직 없으면 요청 글에서 세운다** ({len(_세운것)}개)")
ok(TRACE.포트세우기(_s, _미)[0]["이름"] == "aclk",
   "포트가 있으면 그것을 쓴다 — 지어낸 것으로 덮지 않는다")

# ============================================ 6. 제안서가 이 표를 낸다
_소스 = (뿌리 / "house" / "arch.py").read_text(encoding="utf-8")
ok("from house.dv import trace as TRACE" in _소스 and "TRACE.걸기" in _소스,
   "**제안서가 이것을 실제로 부른다**")
ok("걸린 시나리오" in _소스 and "시험할 시나리오가 하나도 없는 요구사항" in _소스,
   "제안서가 **걸린 시나리오 열**과 **안 걸린 요구사항 경고**를 낸다")
ok(t["못하는것"] and any("검증된 것이 아니다" in x for x in t["못하는것"]),
   "«걸렸다» 가 «검증됐다» 가 아니라고 같이 말한다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("요구사항추적: 걸린다 · 거짓 링크 없음 · 안 걸린 것을 말한다 -- 통과")
