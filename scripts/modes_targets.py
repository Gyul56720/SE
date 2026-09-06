"""**갈래별로 수를 따로 잰다.** 한 자로 다 재니 폭이 벌어졌다.

A 를 --tight(25~75%) 로 좁혀 재도 문장 길이가 21.6~55.3자로 나왔다. 두 배 반이다.
그 폭 안에 들기는 아무 글이나 든다. 원인은 **갈래를 섞어 재기 때문**이다 -- 대사
줄은 짧고 묘사 줄은 길다. 섞으면 어느 갈래의 것도 아닌 수가 나온다.

그래서 줄을 갈래로 가르고(mode.py) 갈래마다 따로 잰다. 이음 축(n2t · t2t · 대사
몫…)은 갈래를 섞어야 나오는 수라 여기서 빠진다(mode.BLIND).

    python3 scripts/modes_targets.py novel/corpus --only A

호출 0회. targets.json 은 그대로 두고 targets.modes.json 을 따로 쓴다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus, mode as MD, profile as PF                   # noqa: E402

# 갈래 글이 이보다 짧으면 안 잰다. 짧은 표본은 수가 아니라 잡음이다.
MIN = 400


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--wide", action="store_true", help="10~90%%로 넓힌다")
    a = ap.parse_args(argv)

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    files = [(w, f) for w, f in PF.unit_files(a.root) if not only or w in only]
    if not files:
        print(f"잰 것이 없다: {a.root} {sorted(only)}", file=sys.stderr)
        return 1

    solo = [k for k in PF.AXES if k not in MD.BLIND]
    pool = {m: {k: [] for k in solo} for m in MD.STATES}
    thin = 0
    for _w, f in files:
        for m, sub in MD.split(corpus.load(f)).items():
            if len(sub) < MIN:
                thin += 1
                continue
            vals = PF.measure(sub)
            if not vals:
                continue
            for k in solo:
                if k in vals:
                    pool[m][k].append(vals[k])

    q = (0.10, 0.90) if a.wide else (0.25, 0.75)
    modes = {}
    for m in MD.STATES:
        axes = {}
        for k, vs in pool[m].items():
            if len(vs) < 5:          # 다섯 토막도 못 모은 축은 폭을 못 만든다
                continue
            v = sorted(vs)
            n = len(v)
            lo, hi = v[int(n * q[0])], v[min(n - 1, int(n * q[1]))]
            if lo == hi == 0.0:      # 늘 0 인 축은 원고를 못 가른다
                continue
            axes[k] = {"lo": round(lo, 4), "mid": round(v[n // 2], 4),
                       "hi": round(hi, 4)}
        if axes:
            modes[m] = axes

    src = (f"{a.root} / {','.join(sorted(only)) or '전부'} / 토막 {len(files)}개 / "
           f"폭 {q[0]:.0%}~{q[1]:.0%}" + (" · 낱낱까지" if PF.GRAIN else " · 낱낱 축 없음"))
    out = Path(a.out or MD.NUMS)
    out.write_text(json.dumps({"_": "갈래마다 따로 잰 수. 손으로 적지 마라.",
                               "_source": src, "modes": modes},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}  <- {src}")
    for m, axes in modes.items():
        keep = [k for k in MD.WATCH.get(m, ()) if k in axes]
        print(f"  {m}: 축 {len(axes)}개 (이 갈래가 보는 것 {len(keep)}개)")
        for k in keep[:6]:
            v = axes[k]
            print(f"      {k:<10} {v['lo']:>8.3f} ~ {v['hi']:<8.3f} (가운데 {v['mid']:.3f})")
    if thin:
        print(f"  건너뛴 갈래 글 {thin}개 ({MIN}자 미만)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
