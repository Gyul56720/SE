"""시간이 어디로 갔는가. **로그와 기록만 읽는다** -- 도는 런을 건드리지 않는다.

"느리다" 는 고칠 수 있는 말이 아니다. 어느 단계가 몇 초를 먹었고 그중 몇 초가 수리에
버려졌는지가 나와야 무엇을 고칠지 정해진다.

읽는 곳 셋:
  · <원고>.scenes.jsonl   씬마다 status/attempts/seconds. 집필 단계의 실측이다
  · 원고 JSON             씬의 attempts 기록 -- 어느 관문이 몇 번 되돌려보냈는지
  · 로그                  회차 조립 시작/끝 시각. 조립 시간은 여기서만 나온다

실행:
    python3 novel/profile.py                                  # 본편
    python3 novel/profile.py --path novel/probe.json          # 탐침
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
TS = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def rows(jsonl: Path) -> list:
    out = []
    try:
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def hhmm(sec: float) -> str:
    return f"{sec / 60:.1f}분" if sec >= 60 else f"{sec:.0f}초"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(HERE / "romance.json"))
    ap.add_argument("--log", default="", help="조립 시간을 잴 로그 (없으면 건너뛴다)")
    a = ap.parse_args()

    path = Path(a.path)
    if not path.exists():
        print(f"{path} 가 없다.")
        return 1

    from novel.state import Novel
    n = Novel.load(path)
    ev = rows(path.with_suffix(".scenes.jsonl"))
    scenes = [e for e in ev if e.get("event") == "scene"]

    print("=" * 64)
    print("집필 (씬 단위)")
    if not scenes:
        print("   기록이 없다 -- 아직 산문 단계에 못 갔다")
    else:
        total = sum(e.get("seconds", 0) for e in scenes)
        okrows = [e for e in scenes if e.get("status") == "verified"]
        bad = [e for e in scenes if e.get("status") != "verified"]
        wasted = sum(e.get("seconds", 0) for e in bad)
        print(f"   씬 {len(scenes)}개 · 합계 {hhmm(total)} · 평균 {hhmm(total/len(scenes))}")
        if okrows:
            once = [e for e in okrows if e.get("attempts", 1) == 1]
            print(f"   통과 {len(okrows)}개 (한 번에 {len(once)}개) · "
                  f"평균 {hhmm(sum(e.get('seconds',0) for e in okrows)/len(okrows))}")
        if bad:
            print(f"   막힘 {len(bad)}개 · {hhmm(wasted)} ({wasted/total:.0%}) 를 여기서 썼다")
        att = Counter(e.get("attempts", 1) for e in scenes)
        print(f"   시도 분포 {dict(sorted(att.items()))}  ← 1이 아니면 수리에 쓴 것이다")

    print()
    print("되돌려보낸 관문 (수리를 부른 것들)")
    rules = Counter()
    for s in n.scenes:
        for at in (getattr(s, "attempts", None) or []):
            for v in at.get("violations", []):
                m = re.match(r"\[(V\d+)", str(v))
                if m:
                    rules[m.group(1)] += 1
    if not rules:
        print("   없다 -- 수리 없이 통과했다")
    for rule, cnt in rules.most_common(8):
        print(f"   {rule}  {cnt}회")

    print()
    print("조립 (회차 단위)")
    log = Path(a.log) if a.log else None
    if not log or not log.exists():
        eps = [e for e in ev if e.get("event") == "episode"]
        if eps:
            for e in eps[-3:]:
                print(f"   {e.get('eps')}  척추 {e.get('spine')} · "
                      f"서브플롯 {e.get('subplot')} · 씬 {e.get('scenes')}")
        print("   조립 시간은 로그에서만 나온다 -- --log 로 지정하라")
    else:
        text = log.read_text(encoding="utf-8", errors="replace").splitlines()
        marks = [(m.group(1), ln) for ln in text
                 for m in [TS.match(ln)] if m and ("조립 시작" in ln or "화 " in ln)]
        for t, ln in marks[:8]:
            print(f"   {t}  {ln[len(t)+3:][:60]}")

    print()
    print("분량")
    chars = sum(len(s.prose or "") for s in n.scenes)
    ver = sum(1 for s in n.scenes if s.status == "verified")
    print(f"   씬 {len(n.scenes)} · verified {ver} · {chars:,}자")
    if scenes and chars:
        total = sum(e.get("seconds", 0) for e in scenes)
        print(f"   속도 {chars / max(1, total) * 60:,.0f}자/분 "
              f"-> 100만자에 {1_000_000 / max(1, chars / max(1, total)) / 3600:.0f}시간")
    return 0


if __name__ == "__main__":
    sys.exit(main())
