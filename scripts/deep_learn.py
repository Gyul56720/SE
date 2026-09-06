"""**표본의 의미층을 뜯어 기록으로 만든다.** 토막당 호출 한 번.

    python3 scripts/deep_learn.py novel/corpus --only A

spine.py 가 칸 하나(무엇이 달라졌나)만 받던 것을 스물두 칸으로 넓힌 것이다.
호출 수는 같다 -- 토막당 한 번. A 는 67토막이니 예순일곱 번이고, 한 번 뽑아 두면
다시 안 뽑는다. **중간에 죽어도 이어서 돈다**(이미 뽑은 토막은 건너뛴다).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus, deep, profile as PF                         # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0, help="앞의 몇 토막만(시험용)")
    a = ap.parse_args(argv)

    from novel import drive as D
    call = D._extractor(None)

    out = Path(a.out or deep.PATH)
    old = deep.load(out)
    done = {r["from"]: r for r in (old.get("recs") or [])}

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    files = [(w, f) for w, f in PF.unit_files(a.root) if not only or w in only]
    if a.limit:
        files = files[:a.limit]
    if not files:
        print(f"잰 것이 없다: {a.root}", file=sys.stderr)
        return 1

    recs, fail = [], 0
    for i, (_w, f) in enumerate(files, 1):
        if f.name in done:                    # **다시 안 묻는다.** 이어 돌기.
            recs.append(done[f.name])
            continue
        text = corpus.load(f)
        if len(text) < PF.MIN_UNIT:
            continue
        try:
            got = D.call_json(call, deep.ask(text), tries=1,
                              label=f"뜯기 {i}/{len(files)}")
        except Exception as e:
            print(f"  {i}: 못 뽑았다 ({type(e).__name__})", file=sys.stderr)
            fail += 1
            continue
        if not isinstance(got, dict):
            fail += 1
            continue
        r = deep.clean(got)
        r["from"] = f.name
        r["n"] = len(recs)
        recs.append(r)
        # **한 토막마다 쓴다.** 예순일곱 번 도는 동안 한 번 죽으면 다 잃는다.
        out.write_text(json.dumps({"_": "표본의 의미층. 원문 문장은 안 들어 있다.",
                                   "_from": str(a.root), "recs": recs,
                                   "dist": deep.learn(recs)},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        if i % 10 == 0:
            print(f"  {i}/{len(files)} · 기록 {len(recs)}개", file=sys.stderr)

    data = {"_": "표본의 의미층. 원문 문장은 안 들어 있다.", "_from": str(a.root),
            "recs": recs, "dist": deep.learn(recs)}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}  <- 기록 {len(recs)}개" + (f" · 못 뽑은 것 {fail}개" if fail else ""))
    print(deep.table(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
