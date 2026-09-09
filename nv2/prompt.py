"""**프롬프트 조립 -- 예산과 자리.**

## 앞 판이 죽은 자리

    프롬프트 8,455자 · 지시 줄 81개 · 굵은 글씨 88군데      (출력은 3,200자)
    "여기만 고쳐라" 가 앉은 자리: 8,238자 = **97% 지점**

사용자가 시킨 열여섯 가지가 **전부 실려 있었는데 원고는 한 줄도 안 지켰다.**
전부가 제일 중요하다고 하면 아무것도 제일 중요하지 않다.

## 그래서 둘을 강제한다

**자리.** 순서가 곧 우선순위다.

    1. [반드시]   잰 어긋남 셋까지        <- 맨 앞. **굵은 글씨는 여기서만 쓴다**
    2. [이번 회차] 카드 -- 무엇이 벌어지나
    3. [세계]     원장 -- 어긋나면 안 되는 것
    4. [본보기]   돌려 뽑은 문법           <- 지키라는 말이 아니다
    5. [이어서]   앞 회차의 꼬리

**예산.** 지시(1 · 4)는 `BUDGET` 자를 못 넘는다. 넘으면 **뒤에서부터 떨어뜨리고
무엇을 떨어뜨렸는지 돌려준다.** 조용히 다 싣지 않는다 -- 조용히 다 실었던 것이
앞 판이다.
"""
from __future__ import annotations

from nv2 import bank, ledger as LG, rules

# 지시 예산(자). 맥락([세계] · [이어서])은 안 센다 -- 그것은 지시가 아니라 사실이다.
BUDGET = 2400

# 회차마다 보여 줄 본보기 수. 칸마다 몇 개씩 돌려 뽑는다.
# **차례가 곧 우선순위다.** 예산에 막히면 뒤에서부터 떨어진다 -- 그래서 사용자가
# 힘줘 말한 것(전투 · 부상의 리얼리티 · 도파민)이 앞에 있다.
SHOW = {"전개": 2, "쾌감": 2, "전투": 2, "부상": 1, "대사": 2, "인물": 1,
        "시스템": 1, "연출": 1, "개그": 1, "빌드업": 1}
# 싸움이 없는 회차에는 안 싣는다 -- 안 쓸 규율을 지고 가지 않는다.
FIGHT_ONLY = ("전투", "부상")


def examples(seed: str, n: int, fight: bool, first: bool) -> list:
    """(칸, 글). 조건은 늘, 본보기는 돌려 뽑는다."""
    out = []
    cats = list(SHOW)
    if first:
        cats = ["첫회차", "여는꼴"] + cats
    for cat in cats:
        if cat in FIGHT_ONLY and not fight:
            continue
        k = 4 if cat == "여는꼴" else SHOW.get(cat, 1)
        rows = [bank.line(p) for p in bank.cond(cat)] + \
               [bank.line(p) for p in bank.draw(cat, seed, n, k)]
        if rows:
            out.append((cat, f"  [{cat}]\n" + "\n".join(rows)))
    return out


def build(book: dict, card: dict, prev: str = "", owed=()) -> tuple:
    """(프롬프트, 떨어뜨린 것, 지시 자수). **떨어뜨린 것도 쓴 예산도 숨기지 않는다.**

    예산은 **지시**에만 건다 -- [세계]와 [이어서]는 사실이지 지시가 아니라서 안 센다.
    그 둘을 예산에 넣으면 세계가 자랄수록 문법이 밀려난다."""
    seed = str(book.get("씨앗") or "")
    n = int(book.get("회차") or 0)
    first = n == 0
    fight = bool((card or {}).get("전투"))
    hero = LG.hero(book.get("원장") or {})

    must = list(owed) + (rules.says(prev) if prev else [])
    head = ["소설을 쓴다. **산문만** 낸다 -- 제목도 머리말도 표식도 쓰지 마라.",
            f"[분량] 이번 회차 약 {book.get('회차분량', 5000):,}자. 끊지 말고 이어라."]

    blocks, dropped = [], []
    if must:
        blocks.append(("반드시",
                       "[반드시] **이 셋만 고친다.** 나머지는 지금대로 좋다.\n"
                       + "\n".join(f"  {i}. {s}" for i, s in enumerate(must[:rules.MAX], 1))))
    if card:
        blocks.append(("이번 회차", _card(card, hero)))

    spent = sum(len(b) for _, b in blocks)
    for cat, text in examples(seed, n, fight, first):
        if spent + len(text) > BUDGET:
            dropped.append(cat)
            continue
        spent += len(text)
        blocks.append((cat, text))
    if dropped:
        blocks.append(("_", f"  (예산 {BUDGET:,}자에 막혀 이번 회차에 안 실은 본보기:"
                            f" {' · '.join(dropped)})"))

    world = LG.brief(book.get("원장") or {})
    tail = [f"[세계 -- 어긋나면 안 되는 것]\n{world}" if world else "",
            f"[이어서 -- 앞 회차의 끝]\n…{prev[-800:]}\n"
            "  * **이 마지막 문장 다음 순간부터 쓴다.** 위 글을 옮겨 적지 마라." if prev else ""]
    body = "\n\n".join(head + [b for _, b in blocks] + [t for t in tail if t])
    return body, dropped, spent


def _card(card: dict, hero: str) -> str:
    """[이번 회차]. **각본은 메모지 문장이 아니다** -- 앞 판은 이 말이 없어서
    카드의 '…한다' 가 원고에 그대로 실렸다(실측: 현재형 요약문 셋)."""
    rows = [f"[이번 회차] 원하는 것: {card.get('원함', '')}"]
    if card.get("막는것"):
        rows.append(f"  · 막는 것: {card['막는것']}")
    for i, b in enumerate(card.get("장면") or [], 1):
        rows.append(f"  · 장면 {i}: {b}")
    for k, label in (("쾌감", "통쾌한 자리"), ("전투", "싸움"), ("설정", "이 회차에 세우는 설정"),
                     ("바뀜", "회차가 닫힐 때 달라져 있는 것"), ("끝", "마지막 문단에 벌어지는 일")):
        if card.get(k):
            rows.append(f"  · {label}: {card[k]}")
    rows.append("  · **위는 무슨 일이 벌어지는지 적어 둔 메모다.** 그 문장을 옮겨 적지 마라 --"
                " 메모는 '…한다' 로 적혀 있고 원고는 그 일이 **벌어지는 장면**이다.")
    rows.append(f"  · 주인공은 «{hero}» 다. 이름으로 부른다."
                if hero else
                "  · 주인공의 이름을 **이 회차에서 정하고** 그 뒤로 안 바꾼다."
                " '화자' · '주인공' 은 우리끼리 쓰는 말이지 이 세계의 낱말이 아니다.")
    return "\n".join(rows)
