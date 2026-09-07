"""**표본에서 상태 흐름을 배워 modes.json 에 쓴다. LLM 호출 0회.**

targets.json 이 "얼마나"(문장 길이 41자, 대사 몫 34%) 라면 이쪽은 **"무엇 다음에
무엇"** 이다 -- 묘사 두 줄 뒤에 대사가 오는가, 대사는 몇 턴 이어지는가.

    python3 scripts/modes_update.py novel/corpus --only A

**--only 를 쓰라.** 갈래가 다른 작품을 섞으면 흐름이 평균으로 뭉개진다. 흉내 낼
작품 하나만 배우는 것이 목적이다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus, mode as MD, profile as PF                   # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="corpus.py --write 로 만든 폴더")
    ap.add_argument("--only", default="", help="쉼표로 나눈 작품 이름만")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    files = [(w, f) for w, f in PF.unit_files(a.root) if not only or w in only]
    if not files:
        print(f"잰 것이 없다: {a.root} {sorted(only)}", file=sys.stderr)
        return 1

    texts = [corpus.load(f) for _w, f in files]
    m = MD.learn(texts)
    m["_source"] = f"{a.root} / {','.join(sorted(only)) or '전부'} / 토막 {len(texts)}개"
    p = MD.save(m, a.out)

    print(f"{p}  <- {m['_source']}")
    for s in MD.STATES:
        nxt = " ".join(f"{b} {v:.0%}" for b, v in
                       sorted(m["trans"][s].items(), key=lambda kv: -kv[1]) if v >= 0.05)
        print(f"  {s}: {m['run'][s]:.1f}줄 머물고 → {nxt or '(없다)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
