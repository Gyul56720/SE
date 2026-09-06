"""**어떤 설정이 실제로 값을 움직였나** -- 한 런에서 수십 개 관측을 얻는다.

지시문을 한 번 고치고 런을 통째로 다시 돌리면 사이클마다 관측이 하나뿐이다. 그건
최적화가 아니라 생성이다. 대신 덩어리마다 다른 설정(팔)을 배정하고, 그 덩어리가 표본에서
얼마나 멀었는지를 팔과 함께 적는다. 서른 덩어리를 쓰면 서른 개의 관측이 공짜로 생긴다 --
**호출은 하나도 안 는다.**

팔이 흔드는 것: 몇 개나 싣는가 · 얼마나 벗어나야 말하는가 · 폭의 어디를 겨누는가.

실행:
    python3 novel/arms.py novel/drift.json          # 팔마다 평균 거리
    python3 novel/arms.py novel/drift.json --apply  # 이긴 팔을 기본값으로 굳힌다
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import dyn                                                 # noqa: E402

HERE = Path(__file__).resolve().parent
PICKED = Path(os.environ.get("DRIFT_ARM", HERE / "arm.json"))
# 이만큼은 봐야 말한다. 서너 번으로 이겼다고 하면 그건 우연이다.
MIN_SEEN = int(os.environ.get("DRIFT_ARM_MIN", "5"))


def rows(path) -> list:
    book = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(book.get("arms") or [])


def tally(rs: list) -> dict:
    out: dict = {}
    for r in rs:
        i = r["arm"]["id"]
        a = out.setdefault(i, {"n": 0, "sum": 0.0, "arm": r["arm"]})
        a["n"] += 1
        a["sum"] += r["gap"]
    for a in out.values():
        a["mid"] = a["sum"] / a["n"]
    return out


def best(t: dict):
    ok = [a for a in t.values() if a["n"] >= MIN_SEEN]
    return min(ok, key=lambda a: a["mid"]) if ok else None


def table(t: dict) -> str:
    if not t:
        return "적힌 것이 없다 -- 아직 덩어리를 안 썼거나 동적 프롬프트가 꺼져 있다."
    rows_ = ["팔  싣는 수  문턱   겨눔     본 횟수   평균 거리", "-" * 48]
    for i, a in sorted(t.items(), key=lambda kv: kv[1]["mid"]):
        m = a["arm"]
        rows_.append(f"{i:>2}  {m['asks']:>6}  {m['slack']:>5.2f}  {m['aim']:<7}"
                     f"{a['n']:>8}  {a['mid']:>9.3f}")
    b = best(t)
    rows_.append("")
    rows_.append(f"이긴 팔: {b['arm'] if b else '아직 모른다'}"
                 + (f" (평균 {b['mid']:.3f})" if b else f" -- {MIN_SEEN}번은 봐야 한다"))
    return "\n".join(rows_)


def apply(t: dict) -> int:
    b = best(t)
    if not b:
        print(f"이긴 팔을 아직 못 고른다 -- 팔마다 {MIN_SEEN}번은 봐야 한다.",
              file=sys.stderr)
        return 1
    PICKED.write_text(json.dumps({"arm": b["arm"], "평균 거리": b["mid"],
                                  "본 횟수": b["n"]}, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"굳혔다: {b['arm']} -> {PICKED}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="설정별 성적")
    ap.add_argument("path", nargs="?", default="novel/drift.json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    t = tally(rows(a.path))
    print(table(t))
    return apply(t) if a.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
