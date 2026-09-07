"""**재는 축과 목표 축이 맞는지 본다.** 안 맞으면 조용히 빠진다.

compose 는 **재는 축만** 싣는다. 그래서 targets.json 에 예순 축이 있어도 집필 쪽이
열아홉만 재면 마흔한 축이 프롬프트에서 사라지는데, 아무 데도 빨간불이 안 뜬다.
반대로 재는데 목표가 없는 축도 마찬가지로 안 실린다.

    python3 scripts/axes_check.py          # 0=맞다 3=어긋난다
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import compose, deep, mode as MD, profile as PF, targets as TG  # noqa: E402


def main(argv=None) -> int:
    try:
        tg = set(json.loads(TG.PATH.read_text(encoding="utf-8"))["axes"])
    except (OSError, ValueError, KeyError):
        print(f"목표가 없다: {TG.PATH}", file=sys.stderr)
        return 3
    ax = set(PF.AXES)
    lost = sorted(tg - ax)
    idle = sorted(ax - tg)
    named = [k for k in compose.SAY if k in tg and k in ax]

    print(f"재는 축 {len(ax)} · 목표 축 {len(tg)} · 프롬프트에 실리는 축 {len(named)}")
    print(f"  낱낱 축(DRIFT_GRAIN): {'켜짐' if PF.GRAIN else '**꺼짐**'}")
    bad = False
    if lost:
        print(f"  ⚠ 목표는 있는데 안 재는 축 {len(lost)}개 -- 프롬프트에서 조용히 빠진다:")
        print("    " + " ".join(lost))
        bad = True
    if idle:
        print(f"  · 재는데 목표가 없는 축 {len(idle)}개(표본을 다시 재면 생긴다): "
              + " ".join(idle[:10]) + (" …" if len(idle) > 10 else ""))

    m = MD.load()
    print(f"  갈래 흐름(modes.json): {'있다' if m else '**없다**'}"
          + (f" · 갈래별 수 {len(MD.nums())}갈래" if MD.nums() else " · 갈래별 수 **없다**"))
    d = deep.load()
    n = len(d.get("recs") or [])
    print(f"  의미층(deep.json): 기록 {n}개"
          + ("  ⚠ 열 개도 안 된다 -- 뒤쪽 덩어리가 전부 같은 짜임을 받는다" if 0 < n < 10 else ""))
    if 0 < n < 10:
        bad = True
    return 3 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
