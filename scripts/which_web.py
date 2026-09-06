"""**어느 표본이 웹소설인가** -- 갈래를 섞으면 어느 쪽도 아닌 값이 나온다.

의미를 안 읽고 꼴로만 가른다. 웹소설은 대체로 이렇다: 대사가 많고, 주고받기가 길고,
문단이 짧고(모바일에서 읽힌다), 문장이 짧다. 번역 문학과 교양서는 반대쪽이다.

**판정하지 않는다 -- 늘어놓기만 한다.** 어느 것을 쓸지는 사람이 고른다.

    python3 scripts/which_web.py novel/corpus
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import profile as PF                                       # noqa: E402

# 웹소설 쪽으로 기우는 축과 그 방향(+1 이면 클수록 웹소설 쪽).
LEAN = {"dialog": +1, "rally": +1, "para_len": -1, "sent_len": -1, "askrate": +1}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    a = ap.parse_args(argv)
    works = PF.profile(a.root)
    if not works:
        print(f"잰 것이 없다: {a.root}", file=sys.stderr)
        return 1
    dig = PF.digest(works)
    names = sorted(dig["works"])
    print(f"{'작품':<8}{'대사':>8}{'주고받기':>10}{'문단':>8}{'문장':>8}{'물음':>8}"
          f"{'토막':>7}   웹소설 쪽인가")
    print("-" * 70)
    # **작품끼리 견준다.** 전체 가운뎃값은 토막이 많은 작품에 끌려간다.
    mids = {k: sorted(dig["works"][w][k]["mid"] for w in names)[len(names) // 2]
            for k in LEAN}
    rows = []
    for w in names:
        g = dig["works"][w]
        lean = sum(1 for k, sign in LEAN.items()
                   if (g[k]["mid"] - mids[k]) * sign > 0)
        rows.append((w, g, lean))
    for w, g, lean in rows:
        mark = "●" * lean + "○" * (len(LEAN) - lean)
        print(f"{w:<8}{g['dialog']['mid']:>8.2f}{g['rally']['mid']:>10.1f}"
              f"{g['para_len']['mid']:>8.0f}{g['sent_len']['mid']:>8.1f}"
              f"{g['askrate']['mid']:>8.2f}{g['dialog']['n']:>7}   {mark}")
    print()
    print("● 이 많을수록 웹소설 쪽이다. 판정은 안 한다 -- 눈으로 보고 골라라.")
    print("고른 뒤: python3 scripts/targets_update.py novel/corpus --only A,B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
