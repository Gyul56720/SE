"""**표본에서 목표를 다시 뽑아 targets.json 에 쓴다.**

사람이 표를 읽고 손으로 옮기면 두 가지가 어긋난다: 옮기다 틀리고, 새 축을 더해도
안 옮겨진다. 여기서는 profile.py 가 낸 요약을 그대로 파일로 만든다.

    python3 scripts/targets_update.py novel/corpus
    DRIFT_PROFILE_STRIDE=0.5 python3 scripts/targets_update.py novel/corpus

**수만 쓴다.** 원문은 profile.py 에서 끝난다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import profile as PF, targets as TG                        # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="corpus.py --write 로 만든 폴더")
    ap.add_argument("--out", default=str(TG.PATH))
    ap.add_argument("--only", default="",
                    help="쉼표로 나눈 작품 이름만 쓴다 -- 갈래가 다른 것을 섞지 않으려고")
    # **한 작품을 겨눌 때는 폭을 좁힌다.** 10~90% 는 여러 작품을 아우르려고 넓힌
    # 것이고, 그 안에 들기는 쉽다. 한 작품을 흉내 내는 것이 목적이면 25~75% 로
    # 조인다 -- 통과하기 어려워야 자가 일을 한다.
    ap.add_argument("--tight", action="store_true",
                    help="폭을 25~75% 로 조인다(한 작품을 겨눌 때)")
    a = ap.parse_args(argv)

    only = [x.strip() for x in a.only.split(",") if x.strip()]
    works = PF.profile(a.root, only or None)
    if not works:
        print(f"잰 것이 없다: {a.root}", file=sys.stderr)
        return 1
    dig = PF.digest(works)
    n = sum(dig["works"][w][PF.AXES[0]]["n"] for w in dig["works"])
    if a.tight:
        pool = {k: [] for k in PF.AXES}
        for axmap in works.values():
            for k in PF.AXES:
                pool[k] += axmap.get(k, [])
        axes = {}
        for k, vs in pool.items():
            if not vs:
                continue
            v = sorted(vs)
            n = len(v)
            axes[k] = {"lo": round(v[n // 4], 4), "mid": round(v[n // 2], 4),
                       "hi": round(v[min(n - 1, n * 3 // 4)], 4)}
    else:
        axes = {k: {"lo": round(v["lo"], 4), "mid": round(v["mid"], 4),
                    "hi": round(v["hi"], 4)}
                for k, v in dig["all"].items()}
    # **폭이 0이거나 0에 붙은 축은 뺀다.** lo 도 hi 도 mid 도 0 이면 표본에 한 번도
    # 안 나타난 것이고(A: talk_len · repeat · close_t · open_t · dash · ex_rate ·
    # ell_rate · hanja), 0.000~0.002 처럼 0 에 붙은 몫도 마찬가지다 -- "숫자의 몫
    # 0.1%" 같은 요구는 맞출 수도 어길 수도 없다. 그런 축은 원고를 못 가르면서
    # 설명 여덟 줄 가운데 한 자리를 먹고, 원고가 어쩌다 넘기면 영영 어긋난 축으로
    # 남아 매 덩어리 그 자리를 차지한다.
    dead = [k for k, v in axes.items()
            if v["hi"] <= v["lo"] or (v["hi"] < 0.005 and v["mid"] < 0.005)]
    for k in dead:
        del axes[k]

    out = {"_": "표본 소설에서 나온 수. 손으로 적지 마라 -- 이 스크립트가 쓴다.",
           "_source": f"{a.root} ({n}토막 · {len(dig['works'])}편"
                      + (f" · {'·'.join(sorted(dig['works']))}" if only else "")
                      + (f" · 겹쳐 훑음 {PF.STRIDE}" if PF.STRIDE < 1.0 else "")
                      + (" · 좁힌 폭 25~75%" if a.tight else "")
                      + (" · 낱낱까지" if PF.GRAIN else " · **낱낱 축 없음**") + ")",
           "axes": axes}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(f"{a.out} 에 축 {len(axes)}개를 썼다 -- {out['_source']}")
    if dead:
        print(f"  뺀 축 {len(dead)}개(표본에서 늘 0이라 원고를 못 가른다): "
              + " ".join(dead))
    for k, v in axes.items():
        print(f"  {k:<10} {v['lo']:>8.3f} ~ {v['hi']:<8.3f} (가운데 {v['mid']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
