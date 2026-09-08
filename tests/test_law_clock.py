"""소멸시효는 **계산이지 판단이 아니다.** 날짜만 주면 완성 여부가 정해진다.

실측: 답안이 "7년이 지났으니 10년 시효 미완성" 이라고만 적고 상사시효 5년을 보지 않았다.
LLM 에게 맡기면 초일불산입을 빼먹고 중단 뒤 재기산을 잊는다. 그래서 코드가 한다.

    python3 tests/test_law_clock.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import clock as CK                                           # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("[기산] 초일불산입 -- 변제기 다음날부터 센다 (민법 제157조·제166조)")
r = CK.prescription(date(2019, 2, 15), 5, date(2026, 7, 1))
ok(r.기산일 == date(2019, 2, 16), f"변제기 2019-02-15 -> 기산 2019-02-16 (얻은 값 {r.기산일})")
ok(r.만료일 == date(2024, 2, 15), f"5년이면 만료 2024-02-15 (얻은 값 {r.만료일})")

print()
print("[갈림] 민사 10년과 상사 5년은 같은 날짜에서 다른 답을 낸다 -- 어느 쪽인지는 요건표가 다툰다")
b = CK.both(date(2019, 2, 15), date(2026, 7, 1))
ok(b["상사 5년"].완성 and not b["민사 10년"].완성,
   f"2026-07-01 제소: 상사 5년 완성 · 민사 10년 미완성 (얻은 값 {b['상사 5년'].완성}/{b['민사 10년'].완성})")
ok(b["상사 5년"].남은날 < 0 < b["민사 10년"].남은날, "남은 날의 부호가 그것을 말한다")

print()
print("[중단] 승인·압류 뒤에는 새로 센다 (민법 제168조·제178조)")
r = CK.prescription(date(2019, 2, 15), 5, date(2026, 7, 1), interruptions=[date(2023, 11, 1)])
ok(r.기산일 == date(2023, 11, 2) and not r.완성,
   f"2023-11-01 승인 -> 기산 2023-11-02 · 2028-11-01 만료 · 미완성 (얻은 값 {r.기산일} {r.완성})")
r = CK.prescription(date(2019, 2, 15), 5, date(2026, 7, 1), interruptions=[date(2025, 1, 1)])
ok(r.완성, "이미 완성된 뒤(2024-02-15 이후)의 승인은 중단이 아니다 -- 그건 시효이익 포기의 문제다")

print()
print("[최고] 6개월 안에 후속이 없으면 중단이 아니다 (민법 제174조)")
r = CK.prescription(date(2019, 2, 15), 5, date(2026, 7, 1), demands=[date(2019, 2, 11)])
ok(r.완성 and any("후속 없음" in k for k, _ in r.중단),
   f"변제기 전 통지서 한 장으로는 시효가 안 선다 (얻은 값 {r.중단})")
r = CK.prescription(date(2023, 9, 1), 5, date(2024, 1, 15), demands=[date(2023, 12, 1)])
ok(any("후속 있음" in k for k, _ in r.중단), "최고 뒤 6개월 안에 제소하면 후속이 있는 것이다")

print()
if fails:
    print(f"시효 계산: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("시효 계산: 기산 · 민사/상사 갈림 · 중단 재기산 · 최고 -- 통과")
