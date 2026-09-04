"""429 가 **분당 한도인가 일일 한도인가**를 눈으로 확인한다.

llm_pool 의 실패 로그는 str(e)[:120] 로 자르는데, 그 둘을 가르는 quotaId 는 그 뒤에
나온다. 그래서 로그만 보고는 "1분이면 풀릴 것" 과 "자정까지 못 쓸 것" 이 구별되지 않는다
-- 2026-09-04 에 실제로 못 가렸다.

여기서는 자르지 않고 quotaId / retryDelay / quotaValue 를 뽑아 보여주고, llm_pool 의
분류기가 그것을 어떻게 판정하는지 나란히 찍는다. 분류기가 틀렸는지 아니면 정말 일일
소진인지가 이걸로 갈린다.

호출은 최소로 한다(프롬프트 "1"). 그래도 성공하면 쿼터를 하나 쓰므로 --limit 로 후보 수를
제한한다.

실행:
    python3 orchestrator/quota_probe.py              # 상위 3개 후보만
    python3 orchestrator/quota_probe.py --limit 12   # 풀 전체
    python3 orchestrator/quota_probe.py --state      # 호출 없이 기록만 본다
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "orchestrator"))

import llm_pool                                                       # noqa: E402
import quota_tracker                                                  # noqa: E402


def facts(text: str) -> dict:
    """429 본문에서 판정에 쓰이는 조각만 뽑는다."""
    out = {}
    for key, pat in (("quotaId", r"['\"]?quotaId['\"]?\s*[:=]\s*['\"]([^'\"]+)"),
                     ("retryDelay", r"['\"]?retryDelay['\"]?\s*[:=]\s*['\"]([^'\"]+)"),
                     ("quotaValue", r"['\"]?quotaValue['\"]?\s*[:=]\s*['\"]?(\d+)"),
                     ("quotaMetric", r"['\"]?quotaMetric['\"]?\s*[:=]\s*['\"]([^'\"]+)")):
        m = re.search(pat, text)
        if m:
            out[key] = m.group(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--state", action="store_true", help="호출 없이 기록만 본다")
    a = ap.parse_args()

    print("=" * 70)
    print("기록된 상태")
    pool = llm_pool.build_pool()
    if not pool:
        print("   풀이 비었다 -- GEMINI_API_KEY 를 찾지 못했다")
        return 1
    fresh = [c for c in pool if quota_tracker.remaining(c[0]) > 0
             and not quota_tracker.is_dead(c[0])]
    print(f"   후보 {len(pool)}개 · 잔량 있는 것 {len(fresh)}개")
    for label, _ in (pool if a.state else fresh[:a.limit]):
        dead = quota_tracker.is_dead(label)
        cool = quota_tracker.rpm_cooldown_remaining(label)
        rem = quota_tracker.remaining(label)
        mark = ("영구배제" if dead else
                f"RPM 쿨다운 {cool:.0f}초 남음" if cool > 0 else
                f"추정 잔량 {rem}")
        print(f"   {label:52} {mark}")
    if a.state:
        return 0

    print("\n" + "=" * 70)
    print(f"실제 호출 (프롬프트 '1', **잔량 있는** 후보 중 {a.limit}개)")
    if not fresh:
        print("   잔량 있는 후보가 없다. 전부 소진 또는 쿨다운 중이다.")
        return 1
    verdicts = {"성공": 0, "RPM": 0, "일일": 0, "영구": 0, "기타": 0}
    for label, llm in fresh[:a.limit]:
        print(f"\n   {label}")
        try:
            r = llm.invoke("1")
            print(f"      성공 -- {llm_pool._extract_text(r)[:40]!r}")
            verdicts["성공"] += 1
            continue
        except Exception as e:                                        # noqa: BLE001
            text = str(e)
        f = facts(text)
        is_q, is_rpm = llm_pool._is_quota(e), llm_pool._is_rpm(e)
        is_perm = llm_pool._is_permanent(e)
        if is_rpm:
            kind, verdicts["RPM"] = "RPM (60초면 풀린다)", verdicts["RPM"] + 1
        elif is_q:
            kind, verdicts["일일"] = "일일 소진 (자정까지)", verdicts["일일"] + 1
        elif is_perm:
            kind, verdicts["영구"] = "영구 사용불가", verdicts["영구"] + 1
        else:
            kind, verdicts["기타"] = "일시 장애", verdicts["기타"] + 1
        print(f"      판정: {kind}")
        for k in ("quotaId", "quotaMetric", "quotaValue", "retryDelay"):
            if f.get(k):
                print(f"      {k:12} {f[k]}")
        if not f:
            print(f"      (본문에서 quotaId 를 못 찾았다. 앞 300자:)")
            print(f"      {text[:300]}")

    print("\n" + "=" * 70)
    print(f"결과 {verdicts}")
    if verdicts["일일"] and not verdicts["RPM"]:
        print("   -> 진짜 일일 소진이다. UTC 자정까지 이 조합들은 못 쓴다.")
    elif verdicts["RPM"]:
        print("   -> 분당 한도가 섞여 있다. **기다리면 풀린다** -- 지금 llm_pool 은")
        print("      쿨다운을 기록만 하고 기다리지 않아서, 60초면 될 것을 실패로 끝낸다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
