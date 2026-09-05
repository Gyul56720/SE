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

    # **후보 풀을 먼저 세운다.** 장부에는 **써 본 것만** 적힌다 -- 새 키를 넣어도 한 번도
    # 안 불렸으면 줄 자체가 없어서, 키가 들어왔는지 여기서 확인할 수가 없었다(실측:
    # "키 두 개밖에 안 찍혔다"). 풀을 세워 놓고 장부를 얹으면 안 쓴 것도 보인다.
    pool_labels = []
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
        import llm_pool
        llm_pool.ROSTER = ""                    # 명부에 걸러진 것도 다 보여 준다
        pool_labels = [lb for lb, _ in llm_pool.build_pool()]
    except Exception as e:                      # 키가 없으면 장부만 보여 준다
        print(f"(후보 풀을 못 세웠다: {type(e).__name__} -- 장부에 있는 것만 보여 준다)")

    data = q._load()
    today = q._today()
    cool = data.get("_rpm_cooldown", {}) or {}
    dead = data.get("_dead", {}) or {}
    now = time.time()

    labels = set(pool_labels) | {
        k for k, v in data.items()
        if not k.startswith("_") and isinstance(v, dict) and "count" in v}
    rows = []
    for label in sorted(labels):
        rec = data.get(label) if isinstance(data.get(label), dict) else {}
        left = q.remaining(label)
        wait = max(0.0, float(cool.get(label, 0)) - now)
        rows.append((label, rec.get("date", "-"), rec.get("count", 0), left, wait))

    keys = sorted({label.split(":", 1)[0] for label in labels})
    print(f"오늘 {today} · 상한 추정 {q.DEFAULT_DAILY_LIMIT} "
          f"(GEMINI_DAILY_LIMIT 로 바꾼다)")
    print(f"키 {len(keys)}개: {' · '.join(keys)}")
    if pool_labels:
        unused = [l for l in pool_labels if l not in data]
        print(f"후보 {len(pool_labels)}개 (아직 안 써 본 것 {len(unused)}개도 아래 함께)")
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
