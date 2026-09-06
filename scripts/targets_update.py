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
    a = ap.parse_args(argv)

    only = [x.strip() for x in a.only.split(",") if x.strip()]
    works = PF.profile(a.root, only or None)
    if not works:
        print(f"잰 것이 없다: {a.root}", file=sys.stderr)
        return 1
    dig = PF.digest(works)
    n = sum(dig["works"][w][PF.AXES[0]]["n"] for w in dig["works"])
    axes = {k: {"lo": round(v["lo"], 4), "mid": round(v["mid"], 4),
                "hi": round(v["hi"], 4)}
            for k, v in dig["all"].items()}
    out = {"_": "표본 소설에서 나온 수. 손으로 적지 마라 -- 이 스크립트가 쓴다.",
           "_source": f"{a.root} ({n}토막 · {len(dig['works'])}편"
                      + (f" · {'·'.join(sorted(dig['works']))}" if only else "")
                      + (f" · 겹쳐 훑음 {PF.STRIDE}" if PF.STRIDE < 1.0 else "") + ")",
           "axes": axes}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(f"{a.out} 에 축 {len(axes)}개를 썼다 -- {out['_source']}")
    for k, v in axes.items():
        print(f"  {k:<10} {v['lo']:>8.3f} ~ {v['hi']:<8.3f} (가운데 {v['mid']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
