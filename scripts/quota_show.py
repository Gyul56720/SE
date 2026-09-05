"""쿼터 장부를 사람이 읽게 펼친다 -- "소진" 이 정말 하루치인지 눈으로 대조하려고.

로그의 "오늘 치 소진 N개" 는 quota_tracker 의 **추정**이다. 추정은 429 를 맞은 순간
count 를 상한으로 올려 박는 방식이라, 구글이 보낸 429 가 사실 분당 한도였는데 이름을
못 알아본 경우에도 하루치로 남는다. 그 차이를 여기서 본다.

    python3 scripts/quota_show.py          # 오늘자 장부
    python3 scripts/quota_show.py --clear  # 오늘자 소진 표시만 지운다(죽은 모델은 남긴다)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import quota_tracker as q                                             # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true",
                    help="오늘자 소진 표시를 지운다 -- 추정이 틀렸다고 판단했을 때만")
    a = ap.parse_args()

    data = q._load()
    today = q._today()
    cool = data.get("_rpm_cooldown", {}) or {}
    dead = data.get("_dead", {}) or {}
    now = time.time()

    rows = []
    for label, rec in sorted(data.items()):
        if label.startswith("_") or not isinstance(rec, dict) or "count" not in rec:
            continue
        left = q.remaining(label)
        wait = max(0.0, float(cool.get(label, 0)) - now)
        rows.append((label, rec.get("date", "?"), rec.get("count", 0), left, wait))

    print(f"오늘 {today} · 상한 추정 {q.DEFAULT_DAILY_LIMIT} "
          f"(GEMINI_DAILY_LIMIT 로 바꾼다)")
    print("-" * 76)
    for label, date, count, left, wait in rows:
        mark = ("영구배제" if label in dead else
                f"분당쉼 {wait:.0f}s" if wait > 0 else
                "소진" if left <= 0 and date == today else "")
        print(f"  {label:46} {count:6}회  잔량 {left:6}  {mark}")
    if not rows:
        print("  (기록 없음 -- 아직 한 번도 안 불렀거나 장부를 지웠다)")
    print("-" * 76)
    print(f"영구배제 {len(dead)}개 · 분당쉼 {sum(1 for _, _, _, _, w in rows if w > 0)}개 "
          f"· 소진 {sum(1 for _, d, _, l, w in rows if l <= 0 and w <= 0 and d == today)}개")

    if a.clear:
        for label, rec in list(data.items()):
            if not label.startswith("_") and isinstance(rec, dict):
                rec["count"] = 0
        data["_rpm_cooldown"] = {}
        q._save(data)
        print("오늘자 소진·쿨다운 표시를 지웠다. 영구배제(_dead)는 남겼다 -- "
              "그건 자정에도 안 풀리는 것이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
