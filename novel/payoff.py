"""**갚는가.** 던져 놓고 안 닫은 것이 얼마나 묵었는지 센다.

절단(클리프행어)은 효과가 있다 -- 참가자 133명에게 자기보고와 피부전도·코르티솔까지
재서 즐거움 · 각성 · 계속 볼 의향이 다 올랐다. 그런데 같이 나온 것이 더 중요했다
(`EVIDENCE.md` 5절):

> **다음 화가 중심 질문을 합리적인 시간 안에 풀지 않으면 몰입이 떨어진다.**

그러니 절단만 세면 안 된다. 빚만 쌓는 원고는 절단을 잘 하는 원고가 아니라 갚지 않는
원고다. `flow` 는 이미 "열린 것이 아홉 개 넘으면 하나 닫아라" 를 시키는데, 그것은
**개수**만 본다 -- 곁가지 아홉을 여닫으며 핵심 하나를 마흔 덩어리째 묵혀도 통과한다.

## 그래서 무엇을 더 보나

**나이.** 언제 열렸는지 적어 두고, 제일 오래 묵은 것의 **이름을 짚어 준다.** PITQ
(`EVIDENCE.md` 4절)가 말하는 "답이 나면 탐구가 끝날 수도 있는 질문" 을 분류로
가르지 않는다 -- 분류는 판정이고 판정은 이 저장소가 기계에게 안 맡기는 것이다.
대신 **관찰되는 사실**로 대신한다: 오래 열려 있는 것이 곧 이 이야기가 갚지 않은 것이다.

**회수율.** 이 창에서 닫은 수 / 연 수. 1 보다 작으면 빚이 늘고 있다는 뜻이다. 초반에는
당연히 작다(열어야 닫을 것이 생긴다). 오래도록 작으면 나열이다.

## 모르는 것은 모른다고 한다

이어 쓰기 전에 이미 열려 있던 것은 **언제 열렸는지 알 길이 없다.** 원장에 그 기록이
없었다. 지금부터 세되 그 사실을 표시한다 -- 그것들의 나이는 **하한**이지 참값이 아니다.

실행:
    python3 novel/payoff.py novel/drift.json
    python3 novel/payoff.py novel/drift.json --last 12
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# **묵었다고 볼 나이.** 덩어리 하나가 3,200자 남짓이니 열둘이면 약 38,000자,
# 웹소설 회차로 일고여덟 화다. 한 질문이 그동안 한 번도 안 닫혔으면 짚을 만하다.
# **이것은 잰 값이 아니라 운영점이다** -- 문헌은 "합리적인 시간" 이라고만 한다.
# 실제 원고가 쌓이면 거기서 다시 정한다.
STALE = int(os.environ.get("DRIFT_PAYOFF_STALE", "12"))
# 되먹임에 이름을 몇 개나 짚을까. 다 늘어놓으면 그게 각본이 된다.
SHOW = int(os.environ.get("DRIFT_PAYOFF_SHOW", "2"))


def record(book: dict, before: dict, after: dict, at: int) -> dict:
    """한 덩어리가 무엇을 열고 무엇을 닫았나. **원장과 장부에 적는다.**

    `before` 는 이 덩어리 전의 open, `after` 는 뒤의 open. `at` 은 이 덩어리의 번호다.
    돌려주는 것은 이번에 연 것과 닫은 것 -- 부르는 쪽이 로그로 쓸 수 있게."""
    before, after = before or {}, after or {}
    opened = [k for k in after if k not in before]
    closed = [k for k in before if k not in after]

    age = book.setdefault("ledger", {}).setdefault("_open_age", {})
    # **이어 쓰기 전부터 열려 있던 것.** 언제 열렸는지 기록이 없다 -- 지금부터 센다.
    # 그러면 나이가 실제보다 어리게 나오므로, 우리는 짚어야 할 것을 놓칠 수는 있어도
    # 멀쩡한 것을 묵었다고 몰아붙이지는 않는다. 틀리는 방향이 안전한 쪽이다.
    unknown = [k for k in after if k not in age]
    for k in unknown:
        age[k] = at
    # **지우기 전에 나이를 꺼낸다.** 순서를 바꿨더니 lives 가 늘 비었다 -- 이미 지운
    # 칸을 조회하고 있었다.
    lives = sorted(at - age[k] for k in closed if k in age)
    for k in closed:
        age.pop(k, None)

    log = book.setdefault("payoff", [])
    log.append({"n": at, "opened": len(opened), "closed": len(closed),
                "lives": lives})          # 닫힌 것이 얼마나 묵었었나
    return {"opened": opened, "closed": closed, "backfilled": unknown}


def measure(book: dict, last: int = 0) -> dict:
    """{'ratio', 'opened', 'closed', 'oldest', 'stale', 'unknown_age', 'now'}"""
    now = len(book.get("chunks") or [])
    log = list(book.get("payoff") or [])
    if last:
        log = log[-last:]
    opened = sum(r.get("opened", 0) for r in log)
    closed = sum(r.get("closed", 0) for r in log)
    led = book.get("ledger") or {}
    op = led.get("open") or {}
    age = led.get("_open_age") or {}
    known = {k: now - age[k] for k in op if k in age}
    return {"now": now, "opened": opened, "closed": closed,
            "ratio": round(closed / opened, 2) if opened else None,
            "open_now": len(op),
            "unknown_age": len([k for k in op if k not in age]),
            "oldest": sorted(((v, k) for k, v in known.items()), reverse=True),
            "stale": sorted((k for k, v in known.items() if v >= STALE),
                            key=lambda k: -known[k])}


def brief(book: dict) -> str:
    """**프롬프트에 얹을 되먹임.** 묵은 것이 있을 때만 말한다.

    기각하지 않는다. 닫으라고 시키지도 않는다 -- `_open` 이 이미 "하나를 건드려라" 를
    시키고 있고, 여기서 더하는 것은 **어느 것을** 이다. 오래 묵은 것의 이름을 짚는다."""
    m = measure(book)
    if not m["stale"]:
        return ""
    age = (book.get("ledger") or {}).get("_open_age") or {}
    names = m["stale"][:SHOW]
    rows = "\n".join(f"  · **{k}** -- {m['now'] - age[k]}덩어리째 열려 있다"
                     for k in names)
    slow = ("\n  · 여는 것보다 닫는 것이 느리다"
            f"(연 것 {m['opened']} · 닫은 것 {m['closed']}). 빚이 쌓이는 중이다."
            if m["ratio"] is not None and m["ratio"] < 0.5 and m["opened"] >= 4 else "")
    return (f"""[갚을 것] **오래 묵은 것이 있다.**

{rows}{slow}

  * 위 중 **하나를 이번 대목에서 갚아라.** 시원할 필요는 없다 -- 김빠지는 답도 답이고,
    반쯤만 드러나도 갚은 것이다. 답이 다른 질문을 여는 것도 좋다.
  * 갚는 방식은 자유다. 누가 말해도 되고, 물건 하나가 답이 되어도 되고, 아무도 모르는
    채로 독자만 알게 되어도 된다.
  * **미루면 독자가 먼저 떠난다** -- 열어 두는 것이 힘인 것은 갚을 때까지다.""")


def table(m: dict) -> str:
    rows = [f"덩어리 {m['now']}개 · 지금 열린 것 {m['open_now']}개"
            + (f" (그중 {m['unknown_age']}개는 나이를 모른다 -- 이어 쓰기 전부터 열려 있었다)"
               if m["unknown_age"] else ""),
            f"연 것 {m['opened']} · 닫은 것 {m['closed']}"
            + (f" · 회수율 {m['ratio']}" if m["ratio"] is not None else " · 회수율 -- (장부가 비었다)")]
    if m["oldest"]:
        rows += ["", "  오래 묵은 것부터:"]
        for v, k in m["oldest"][:8]:
            rows.append(f"    {v:3d}덩어리째  {k}" + ("   ← 묵었다" if v >= STALE else ""))
    elif m["open_now"]:
        rows += ["", f"  나이를 아는 미결이 없다 -- payoff 장부는 다음 덩어리부터 쌓인다."]
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="던져 놓고 안 닫은 것이 얼마나 묵었나")
    ap.add_argument("path", help="drift.json")
    ap.add_argument("--last", type=int, default=0, help="끝의 몇 덩어리만 (0=전부)")
    a = ap.parse_args(argv)
    book = json.loads(Path(a.path).read_text(encoding="utf-8"))
    print(f"묵었다고 보는 나이: {STALE}덩어리 (운영점이지 잰 값이 아니다)\n")
    print(table(measure(book, a.last)))
    b = brief(book)
    if b:
        print("\n--- 프롬프트에 실릴 것 ---\n" + b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
