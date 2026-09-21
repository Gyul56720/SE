# -*- coding: utf-8 -*-
"""house/spec -- the intake that reads a circuit request.

This is the front door of `!회사 설계 <자연어>`. If it mis-reads, the bot designs
the wrong thing and nobody finds out until a proposal comes back wrong.

Measured 2026-09-21: a request to scale the FIR/MAC into an AXI-attached IP and
an NPU PE array came back with an **empty** use-case list, **CPU** falsely
matched (from the word 코어), NPU/PE/accelerator missed entirely, and the
configuration menu 32/64/128/256 reduced to a single number. Every one of
those is pinned below.
"""
import sys
from pathlib import Path

저장소 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(저장소))

from house import spec  # noqa: E402

FAIL = []


def ok(cond, msg):
    print(("  통과  " if cond else "  실패  ") + msg)
    if not cond:
        FAIL.append(msg)


NPU = ("8탭 FIR/MAC 가속기를 AXI4-Stream 데이터 + AXI4-Lite 제어로 감싸서 "
       "시스템 버스에 붙는 IP 로 만들고, 그 MAC 을 32/64/128/256 개 PE 어레이로 "
       "묶어 INT8 연산을 하는 NPU 코어로 확장해줘. 목표 500MHz, 엣지 저전력.")

print("== NPU scale-up request ==")
s = spec.읽기(NPU)
ok("엣지추론" in s.쓰임새,
   f"the edge-inference market is recognised ({s.쓰임새})")
ok("NPU" in s.회로 and "가속기" in s.회로,
   f"NPU and accelerator are recognised as circuits ({s.회로})")
ok("FIR" in s.회로 and "AXI" in s.회로,
   "the FIR core and the bus are still recognised")
ok("CPU" not in s.회로,
   "**'코어' does not falsely match CPU** -- in this repo it usually means IP core")
ok(s.수.get("주파수_Hz") == [500e6], f"500 MHz is read ({s.수.get('주파수_Hz')})")
ok(s.수.get("정밀도_비트") == [8.0], f"INT8 is read ({s.수.get('정밀도_비트')})")
ok(s.수.get("설정목록") == [32.0, 64.0, 128.0, 256.0],
   f"**the whole configuration menu survives** ({s.수.get('설정목록')})")

print("\n== the earlier request still reads ==")
t = spec.읽기("자동차 범퍼에 들어가는 TTD 회로의 전력 문제를 해결해줄 수 있는 회로를 구상해줘")
ok(t.쓰임새 == ["자동차"] and t.문제 == ["전력"] and t.회로 == ["TDC"],
   f"no regression on the first request this intake was built for "
   f"({t.쓰임새} {t.문제} {t.회로})")

print("\n== it still refuses to guess ==")
u = spec.읽기("뭔가 빠른 걸 만들어줘")
ok(not u.회로 and u.모른다,
   f"an unreadable request leaves 모른다 filled rather than guessing ({u.모른다[:1]})")
ok(any("회로" in x for x in u.모른다),
   "and it says specifically that it could not tell which circuit")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("spec intake: NPU vocabulary · configuration menu · no false CPU · no guessing -- 통과")
