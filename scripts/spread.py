"""**폭이 왜 그렇게 넓은지 본다.** 넓다고 조이면 안 되고, 왜 넓은지부터 봐야 한다.

A 를 25~75%로 좁혀 재도 문장 길이가 21.6~55.3자였다. 갈래로 갈라 묘사만 재도
21.4~55.8자였다 -- 갈래를 섞어서가 아니었다. 가운뎃값이 23인데 75%가 55라면 그건
넓은 분포가 아니라 **봉우리가 둘인 분포**다. 토막이 두 종류라는 뜻이고, 그렇다면
목표를 하나로 주는 것 자체가 틀렸다.

    python3 scripts/spread.py novel/corpus --only A --axis sent_len

토막마다 값을 내서 낮은 쪽 다섯과 높은 쪽 다섯을 이름과 함께 보여준다. 무엇이
두 무리를 가르는지는 사람이 그 파일을 열어 봐야 안다 -- 기계는 여기까지다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus, mode as MD, profile as PF                   # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--only", default="")
    ap.add_argument("--axis", default="sent_len")
    ap.add_argument("--mode", default="", help="이 갈래의 줄만 재서 본다")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args(argv)

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    rows = []
    for w, f in PF.unit_files(a.root):
        if only and w not in only:
            continue
        text = corpus.load(f)
        if a.mode:
            text = MD.split(text).get(a.mode, "")
        if len(text) < 400:
            continue
        m = PF.measure(text)
        if not m or a.axis not in m:
            continue
        rows.append((m[a.axis], f.name, m.get("dialog", 0.0), len(text)))
    if not rows:
        print(f"잰 것이 없다 ({a.axis})", file=sys.stderr)
        return 1

    rows.sort()
    v = [r[0] for r in rows]
    n = len(v)
    q1, med, q3 = v[n // 4], v[n // 2], v[min(n - 1, n * 3 // 4)]
    print(f"{a.axis}{' · ' + a.mode if a.mode else ''} -- 토막 {n}개")
    print(f"  25% {q1:.3f} · 가운데 {med:.3f} · 75% {q3:.3f} · "
          f"제일 낮은 것 {v[0]:.3f} · 제일 높은 것 {v[-1]:.3f}")

    # **봉우리가 둘인가.** 가운뎃값에서 25%까지의 거리와 75%까지의 거리가 몇 배나
    # 차이 나면 한 봉우리가 아니다. 한 봉우리면 두 거리가 엇비슷하다.
    lo_d, hi_d = med - q1, q3 - med
    if lo_d > 0 and hi_d / lo_d >= 3:
        print(f"  ⚠ 한쪽으로 몰려 있다 -- 가운데에서 아래로 {lo_d:.3f}, 위로 {hi_d:.3f} "
              f"({hi_d / lo_d:.1f}배). 봉우리가 둘일 수 있다.")
    elif hi_d > 0 and lo_d / hi_d >= 3:
        print(f"  ⚠ 한쪽으로 몰려 있다 -- 아래로 {lo_d:.3f}, 위로 {hi_d:.3f}.")

    print(f"\n  낮은 쪽 {a.top}개")
    for x, name, dl, ln in rows[:a.top]:
        print(f"    {x:>9.3f}  {name:<22} 대사 몫 {dl:.0%} · {ln:,}자")
    print(f"  높은 쪽 {a.top}개")
    for x, name, dl, ln in rows[-a.top:]:
        print(f"    {x:>9.3f}  {name:<22} 대사 몫 {dl:.0%} · {ln:,}자")

    half = n // 2
    d_lo = sum(r[2] for r in rows[:half]) / max(1, half)
    d_hi = sum(r[2] for r in rows[half:]) / max(1, n - half)
    print(f"\n  아래 절반의 대사 몫 {d_lo:.0%} · 위 절반 {d_hi:.0%}"
          + ("  ← 대사가 가른다" if abs(d_lo - d_hi) > 0.05 else "  ← 대사로는 안 갈린다"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
