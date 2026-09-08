"""소멸시효 -- **계산이지 판단이 아니다.**

변제기와 제소일이 사실로 주어지면 시효가 완성됐는지는 날짜 셈이다. LLM 에게 맡기면
초일불산입을 빼먹거나 중단 뒤 재기산을 잊는다(실측: 답안이 "7년이 지났으니 10년
시효 미완성" 이라고만 적고 상사시효 5년을 보지 않았다). 그래서 코드가 한다.

    python3 law/clock.py 2019-02-15 --년 5 --제소 2026-07-01
    python3 law/clock.py 2019-02-15 --년 5 --제소 2026-07-01 --중단 2023-11-01

규칙(민법):
  제157조  초일불산입 -- 기산일은 권리를 행사할 수 있는 날의 **다음날**
  제166조  권리를 행사할 수 있는 때부터 진행
  제168조  중단: 청구 · 압류/가압류/가처분 · 승인
  제174조  최고는 6개월 내 재판상 청구 등이 없으면 중단 효력이 없다
  제178조  중단되면 그때까지 경과한 기간은 산입하지 않고 중단 사유 종료 시부터 새로 진행

기간은 이 파일이 정하지 않는다 -- 민사 10년(제162조)인지 상사 5년(상법 제64조)인지는
**법률 쟁점**이라 요건표에서 다투고, 여기는 둘 다 셈해서 나란히 보여 준다.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta


def _plus_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:                       # 2월 29일
        return d.replace(year=d.year + years, day=28)


@dataclass
class Run:
    기산일: date
    만료일: date
    완성: bool
    남은날: int
    중단: list


def prescription(due: date, years: int, filed: date, interruptions=(),
                 demands=()) -> Run:
    """변제기 `due`, 기간 `years`, 제소일 `filed`. 중단 사유 날짜들을 반영해 완성 여부.

    `interruptions` -- 승인·압류·재판상 청구 같은 **확정적** 중단(제168조). 그날부터 새로 센다.
    `demands`       -- 최고(제174조). 6개월 안에 확정적 중단이나 제소가 따라야만 중단이다.
    """
    start = due + timedelta(days=1)                       # 초일불산입
    events = []
    for d in sorted(interruptions):
        if not (start <= d <= filed):
            continue
        # **이미 완성된 뒤의 승인은 중단이 아니다.** 중단은 진행 중인 시효를 멈추는
        # 것이고(제168조), 다 지나간 시효에 대한 승인은 시효이익 포기(제184조)의 문제다.
        # 둘은 요건도 증명책임도 다르다 -- 여기서 섞으면 요건표가 그것을 못 가른다.
        if d > _plus_years(start, years) - timedelta(days=1):
            events.append(("완성 뒤의 승인 -- 중단 아님 (시효이익 포기의 문제)", d))
            continue
        events.append(("중단", d))
        start = d + timedelta(days=1)
    for d in sorted(demands):
        follow = [x for x in list(interruptions) + [filed] if d <= x <= d + timedelta(days=183)]
        if follow:
            events.append(("최고(6개월 내 후속 있음)", d))
        else:
            events.append(("최고(후속 없음 -- 중단 아님)", d))
    end = _plus_years(start, years) - timedelta(days=1)    # 기간 말일
    done = filed > end
    return Run(기산일=start, 만료일=end, 완성=done,
               남은날=(end - filed).days, 중단=events)


def both(due: date, filed: date, interruptions=(), demands=()) -> dict:
    """민사 10년과 상사 5년을 나란히. 어느 쪽인지는 요건표가 다툰다."""
    return {"민사 10년": prescription(due, 10, filed, interruptions, demands),
            "상사 5년": prescription(due, 5, filed, interruptions, demands)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="소멸시효를 센다 -- 판단이 아니라 계산이다")
    ap.add_argument("due", help="변제기 YYYY-MM-DD")
    ap.add_argument("--제소", dest="filed", required=True, help="소 제기일")
    ap.add_argument("--년", dest="years", type=int, default=0, help="기간. 없으면 10년·5년 둘 다")
    ap.add_argument("--중단", dest="cuts", nargs="*", default=[], help="승인·압류 등 확정 중단일")
    ap.add_argument("--최고", dest="demands", nargs="*", default=[], help="최고일")
    a = ap.parse_args(argv)
    due, filed = date.fromisoformat(a.due), date.fromisoformat(a.filed)
    cuts = [date.fromisoformat(x) for x in a.cuts]
    dem = [date.fromisoformat(x) for x in a.demands]
    runs = {f"{a.years}년": prescription(due, a.years, filed, cuts, dem)} if a.years \
        else both(due, filed, cuts, dem)
    print(f"변제기 {due} · 제소 {filed}")
    for name, r in runs.items():
        상태 = f"**완성** ({-r.남은날}일 지남)" if r.완성 else f"미완성 ({r.남은날}일 남음)"
        print(f"  {name:8} 기산 {r.기산일} · 만료 {r.만료일} · {상태}")
        for kind, d in r.중단:
            print(f"           {d} {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
