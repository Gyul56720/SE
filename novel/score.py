"""**우리 원고가 표본에서 얼마나 먼가.**

이 수가 없으면 프롬프트를 고치고 나서 나아졌는지 나빠졌는지 알 길이 없다 -- 이 세션에서
되돌린 것들(예문 도배 · 번역투 · 늘어짐)이 전부 그래서 늦게 발견됐다.

재는 법. 축마다 표본의 10~90% 폭이 있다(targets.json). 그 안에 들면 **0**이다 --
가운뎃값에 붙으라고 하지 않는다. 표본 자체가 흩어져 있으니까. 폭을 벗어난 만큼만,
폭의 너비로 나눠서 센다. 그래서 축마다 단위가 달라도 더할 수 있다.

    거리 0.0  폭 안에 있다
    거리 1.0  폭의 너비만큼 벗어났다
    거리 3.0  세 배 벗어났다 -- 여기가 먼저 고칠 자리다

**재미는 재지 않는다.** 기계는 무모순만 판정한다는 원칙 그대로다. 여기서 재는 것은
"표본과 같은 꼴인가" 뿐이고, 그것은 재미의 필요조건이지 충분조건이 아니다.

실행:
    python3 novel/score.py novel/drift.json           # 원고 하나
    python3 novel/score.py novel/holdout              # 잘라 둔 폴더
    python3 novel/score.py novel/drift.json --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import profile as PF, targets as TG                        # noqa: E402

# 폭이 0 인 축(표본이 한 점으로 모인 것)에서 0 으로 나누지 않으려는 바닥값.
FLOOR = 0.02


def _gap(v: float, lo: float, hi: float) -> float:
    span = max(hi - lo, FLOOR)
    if v < lo:
        return (lo - v) / span
    if v > hi:
        return (v - hi) / span
    return 0.0


def chunks_of(path) -> list:
    """원고에서 덩어리를 꺼낸다. drift.json 이면 chunks, 폴더면 잘라 둔 토막."""
    p = Path(path)
    if p.is_dir():
        return [f.read_text(encoding="utf-8") for _, f in PF.unit_files(p)]
    book = json.loads(p.read_text(encoding="utf-8"))
    return list(book.get("chunks") or [])


# **최근 몇 덩어리만 잰다.** 원고 전체를 재면 학습 신호가 원고 길이에 반비례해
# 죽는다: 지금 2만 자인데 한 바퀴가 8천 자를 더한다. 스무 덩어리가 쌓이면 새로 쓴
# 세 덩어리는 가운뎃값을 거의 못 움직이고, 그러면 지시문을 어떻게 고치든 점수가
# 안 변한다(실측: 0.085 -> 0.085 가 네 바퀴). 10만 자에 이르면 아예 안 움직인다.
#
# 지시문을 고친 효과는 **고친 뒤에 쓴 글**에만 있다. 그러니 그것만 본다.
# 0 이면 전부 -- 홀드아웃이나 완성 원고를 잴 때는 그렇게 쓴다.
LAST = int(os.environ.get("DRIFT_SCORE_LAST", "6"))


def score(path, last: int | None = None) -> dict:
    """축마다 (우리 값, 표본 폭, 거리). 그리고 총점. **끝의 몇 덩어리만 본다.**"""
    texts = [t for t in chunks_of(path) if len(t) >= PF.MIN_UNIT]
    # **폴더는 안 자른다.** 홀드아웃의 바닥은 표본 전체를 재야 나온다 -- 끝의 여섯
    # 토막만 재면 그건 바닥이 아니라 그 여섯의 값이다.
    n = 0 if Path(path).is_dir() else (LAST if last is None else last)
    if n and len(texts) > n:
        texts = texts[-n:]
    if not texts:
        return {}
    per: dict = {k: [] for k in PF.AXES}
    for t in texts:
        m = PF.measure(t)
        if not m:
            continue
        # **없는 축은 안 담는다.** 자국이 하나도 없어 못 잰 축(voice 의 시제 · 인칭 ·
        # 감각)을 0 으로 채우면 "안 쓴다" 와 "알 수 없다" 가 같아진다. profile 은
        # 이미 이렇게 하는데 여기만 안 해서, 그런 덩어리를 만나면 통째로 터졌다.
        for k in PF.AXES:
            if k in m:
                per[k].append(m[k])
    out = {"n": len(texts), "axes": {}, "total": 0.0}
    tot = 0.0
    for k in PF.AXES:
        band = TG.band(k)
        if not band or not per[k]:
            continue
        got = PF.summary(per[k])["mid"]
        d = _gap(got, band[0], band[1])
        out["axes"][k] = {"got": got, "lo": band[0], "hi": band[1], "gap": d}
        tot += d
    out["total"] = tot / max(1, len(out["axes"]))
    return out


def table(s: dict) -> str:
    if not s:
        return "잰 것이 없다 -- 덩어리가 없거나 전부 너무 짧다."
    rows = [f"{'축':<10}{'우리':>9}{'표본 폭':>18}{'거리':>8}", "-" * 45]
    for k, a in sorted(s["axes"].items(), key=lambda kv: -kv[1]["gap"]):
        mark = "  <-- 여기" if a["gap"] >= 1.0 else ""
        rows.append(f"{k:<10}{a['got']:>9.2f}{a['lo']:>9.2f}~{a['hi']:<8.2f}"
                    f"{a['gap']:>7.2f}{mark}")
    rows.append("")
    rows.append(f"덩어리 {s['n']}개 · **총점 {s['total']:.3f}** (0 이면 전부 표본 폭 안)")
    worst = [k for k, a in s["axes"].items() if a["gap"] >= 1.0]
    if worst:
        rows.append(f"폭을 벗어난 축 {len(worst)}개: {' · '.join(worst)}")
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원고가 표본에서 얼마나 먼가")
    ap.add_argument("path", help="drift.json 또는 잘라 둔 폴더")
    ap.add_argument("--json", default="")
    ap.add_argument("--all", action="store_true",
                    help="원고 전체를 잰다(기본은 끝의 몇 덩어리만 -- 학습 신호용)")
    a = ap.parse_args(argv)
    s = score(a.path, last=0 if a.all else None)
    print(f"표본: {TG.source()}\n")
    print(table(s))
    if a.json and s:
        Path(a.json).write_text(json.dumps(s, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"\n-> {a.json}")
    return 0 if s else 1


if __name__ == "__main__":
    raise SystemExit(main())
