"""**연재 오케스트레이션 — 도착지를 주되 줄거리는 안 준다.**

## 무엇을 고치려는 것인가

DRIFT(`flow.py`)는 문체를 얻고 스토리를 잃었다. 집필 프롬프트에 이렇게 적혀 있다:

    **줄거리를 미리 정하지 마라.** 지금 문장에서 다음 문장이 나오게 하라.

그래서 스토리에 관해 가진 것이 전부 **뒤를 본다**:

    turned()      지난 덩어리가 세계에 무엇을 바꿔 놨나        뒤
    owed_brief()  안 갚은 빚 하나                              뒤
    payoff        열린 것이 얼마나 묵었나                       뒤
    turn.brief()  판이 한 방향으로만 간다                       뒤

**앞을 보는 것이 하나도 없다.** 갈 곳이 없으니 사건이 쌓이기만 하고 도착하지 않는다.

## 그런데 조립 경로로 돌아가지는 않는다

`episode.py` 는 줄거리를 세운다. 그것이 두 가지를 망쳤다 -- 화당 18~25호출이었고,
화자에게 "이 씬을 1,666자로 쓰라" 고 시키니 **분량 할당량이 곧 희석 지시**가 됐다.
채우라고 하면 채운다.

진단은 이것이다. **DRIFT 의 문제는 자유롭게 쓰는 것이 아니라, 어디로 가는지 모르고
자유롭게 쓰는 것이다.** 도착지를 주는 것은 문장의 자유를 안 뺏는다. 두 결정이
별개인데 지금 한 덩어리로 묶여 있다.

## 그래서 결말만 세우고 줄거리는 안 세운다

    결말   시작에 한 번   호출 1회   결말 한 줄 + 그게 참이 되려면 먼저 참이어야
                                     할 것 넷~여섯 (**빚 목록**)
    마디   약 1만 자마다  호출 0회   남은 빚 중 하나를 코드가 고른다
    덩어리 3,200자마다    호출 3회   flow.step 그대로. 프롬프트에 한 줄이 더 붙는다

**각본이 아니라 빚 목록이다.** "3화에서 이런 일이 일어난다" 가 아니라 "끝나기 전에
이것이 참이 되어야 한다" 다. 순서도 방법도 화자가 정한다.

`world_romance.OUTCOMES` 를 쓰지 않는다 -- 그것은 **특정 음대 로맨스의 15화 각본**이지
갈래의 결말 목록이 아니다. 여기서 쓰면 모든 원고가 그 이야기가 된다.

## 갚혔는지 자동으로 판정하지 않는다

빚이 갚혔는지 기계가 보려면 호출이 하나 더 들거나(비싸다) 낱말 맞추기를 해야 한다
(틀린다). **둘 다 안 한다.** 마디는 **분량으로** 넘어가고, 빚은 차례로 배정된다.
갚혔는지는 사람이 읽으면 알고, 일반적인 회수는 `payoff.py` 가 이미 잰다.

지어낸 판정을 넣는 것보다 판정을 안 하는 편이 낫다 -- 틀린 판정은 원고를 엉뚱한
데로 민다.

    python3 novel/serial.py plan --book novel/drift.json --genre ropan
    python3 novel/serial.py show --book novel/drift.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel import genre as GENRE                                      # noqa: E402

# 한 마디의 길이. 이만큼 쓰면 다음 빚으로 넘어간다.
#
# 왜 1만 자인가. **정한 값이지 잰 값이 아니다.** 표본 4편의 회차 길이를 재서 정할
# 수도 있었지만, 회차 경계는 원고에 표시가 없어서 못 잰다. 1만 자면 덩어리 서넛이고,
# 그 정도가 한 사건이 서고 닫히는 크기다. 실측이 생기면 이 줄을 고친다.
SPAN = int(os.environ.get("SERIAL_SPAN", "10000"))

# 빚의 개수. 넷보다 적으면 도착지가 너무 가깝고, 여섯보다 많으면 한 마디에 하나씩
# 배정해도 원고가 그만큼 길어져야 한다(여섯 x 1만 자 = 6만 자).
DEBTS = (4, 6)


def _blank() -> dict:
    return {"end": "", "debts": [], "made": ""}


def arc(book: dict) -> dict:
    """원고에 붙은 도착지. 없으면 빈 것."""
    return book.get("arc") or _blank()


def planned(book: dict) -> bool:
    a = arc(book)
    return bool(a.get("end") and a.get("debts"))


# ---------------------------------------------------------------- 세우기

def plan_prompt(gname: str) -> str:
    """**디렉터에게 한 번만 묻는다.** 300토큰짜리 답 하나다.

    갈래 꾸러미의 머리와 관계 축을 얹는다 -- 지어내라고 하지 않고 **이 갈래의
    결말**을 내라고 한다. 인물 이름은 여기서 정하지 않는다: 아직 원고가 없어서
    누가 나올지 모르고, 이름은 `이름결` 이 첫 덩어리에서 정한다.
    """
    pack = GENRE.get(gname) if gname else {}
    head = (pack.get("머리") or "").strip()
    rel = ", ".join(list(pack.get("관계") or {})[:8])
    return f"""이 소설이 **어디로 갈지**만 정한다. 줄거리는 정하지 않는다.

{f'[갈래] {pack.get("name", gname)}' if pack else ''}
{head}
{f'[이 갈래가 다루는 관계] {rel}' if rel else ''}

두 가지를 JSON 으로 낸다.

1. **끝** -- 이 소설이 끝나는 자리 한 문장. 사건이 아니라 **상태**로 적어라.
   ("두 사람이 결혼한다" 가 아니라 "그 계약이 더는 두 사람을 묶지 못한다")

2. **빚** -- 그 끝이 참이 되려면 **먼저 참이 되어야 하는 것** {DEBTS[0]}~{DEBTS[1]}개.
   - 각각 한 문장. **상태로 적어라.** 무슨 장면을 쓰라는 말이 아니다.
   - 순서대로 적어라 -- 앞엣것이 먼저 참이 되어야 뒤엣것이 가능하다.
   - **어떻게** 참이 되는지는 적지 마라. 그건 쓰면서 정한다.

인물 이름을 정하지 마라. 아직 아무도 없다.

{{"끝": "...", "빚": ["...", "...", "...", "..."]}}"""


def plan(book: dict, llm, gname: str = "", log=None) -> dict:
    """도착지를 세워 원고에 붙인다. **호출 한 번.** 이미 있으면 안 덮는다."""
    if planned(book):
        D._log("[연재] 도착지가 이미 있다 -- 그대로 간다")
        return arc(book)
    got = D.call_json(D._llm_for(llm, "director"),
                      plan_prompt(gname), label="연재 도착지")
    end = str(got.get("끝") or "").strip()
    debts = [str(x).strip() for x in (got.get("빚") or []) if str(x).strip()]
    if not end or not debts:
        raise ValueError(f"도착지를 못 받았다: 끝={end!r} 빚={len(debts)}개")
    # **넘치면 자르되 모자라면 안 채운다.** 채우려면 지어내야 한다.
    debts = debts[:DEBTS[1]]
    book["arc"] = {"end": end,
                   "debts": [{"무엇": d, "갚음": 0} for d in debts],
                   "made": gname}
    D._log(f"[연재] 끝: {end}")
    for i, d in enumerate(debts, 1):
        D._log(f"[연재]   빚 {i}. {d}")
    return book["arc"]


# ---------------------------------------------------------------- 어디쯤인가

def where(book: dict) -> int:
    """지금 몇 번째 마디인가. **분량으로 센다 -- 호출이 안 든다.**"""
    n = sum(len(c) for c in (book.get("chunks") or []))
    return n // max(1, SPAN)


def current(book: dict) -> "dict | None":
    """이번 마디가 향하는 빚. 빚을 다 지나갔으면 마지막 것에 머문다.

    **마지막에 머무는 것이 맞다.** 빚이 끝났다고 당김을 놓으면 그 뒤로는 다시
    도착지 없는 글이 된다 -- 고치려던 것 그대로다."""
    ds = arc(book).get("debts") or []
    if not ds:
        return None
    return ds[min(where(book), len(ds) - 1)]


def done(book: dict) -> bool:
    """마지막 빚까지 지나갔는가. 끝을 향해 갈 때다."""
    ds = arc(book).get("debts") or []
    return bool(ds) and where(book) >= len(ds)


# ---------------------------------------------------------------- 프롬프트

def brief(book: dict) -> str:
    """**프롬프트에 얹을 당김. 한 줄이다.**

    길게 쓰지 않는다 -- 한 덩어리에 실리는 지시가 넷 상한이라, 여기가 길면 다른
    것을 밀어낸다. 그리고 **어떻게 하라고 말하지 않는다.** 방향만 준다.

    자를 시키지 않는다는 계약(`turn.py`)이 여기도 그대로다: 마디 번호도, 남은
    빚의 개수도, 분량도 싣지 않는다. 그것을 실으면 원고가 진도표를 맞추러 간다.
    """
    a = arc(book)
    if not a.get("end"):
        return ""
    cur = current(book)
    if not cur:
        return ""
    if done(book):
        return ("[어디로] **이제 끝을 향해 간다.**\n"
                f"  · 이 이야기가 닿을 자리: {a['end']}\n"
                "  · 서두르지 마라. 다만 이 대목의 일이 그 자리에서 **멀어지지는**"
                " 않게 해라.")
    return ("[어디로] **이 대목이 향하는 곳**\n"
            f"  · {cur['무엇']}\n"
            "  · 여기서 그것을 이루라는 말이 아니다. **한 걸음 가까워지면 된다** --"
            " 멀어지는 일이 벌어져도 좋다, 그것이 이 방향의 일이기만 하면.\n"
            "  · 이 문장을 원고에 옮겨 적지 마라. 인물이 이것을 입 밖에 내지도 마라.")


# ---------------------------------------------------------------- 사람이 보는 것

def show(book: dict) -> str:
    a = arc(book)
    if not a.get("end"):
        return "도착지가 없다 -- serial.py plan 을 먼저 돌려라."
    n = sum(len(c) for c in (book.get("chunks") or []))
    at = where(book)
    rows = []
    for i, d in enumerate(a["debts"]):
        mark = "→" if i == min(at, len(a["debts"]) - 1) and not done(book) else \
               ("·" if i > at else "지남")
        rows.append(f"  {mark:4} {i + 1}. {d['무엇']}")
    tail = "\n  → 빚을 다 지났다. 끝을 향해 간다." if done(book) else ""
    return (f"끝: {a['end']}\n"
            f"원고 {n:,}자 · 마디 {at + 1} (한 마디 {SPAN:,}자)\n"
            + "\n".join(rows) + tail)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("plan", "show"))
    ap.add_argument("--book", default="novel/drift.json")
    ap.add_argument("--genre", default=os.environ.get("GENRE", ""))
    a = ap.parse_args()

    p = Path(a.book)
    if not p.exists():
        print(f"원고가 없다: {p}", file=sys.stderr)
        return 1
    book = json.loads(p.read_text(encoding="utf-8"))

    if a.cmd == "show":
        print(show(book))
        return 0

    plan(book, D.default_llm, a.genre)
    p.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(show(book))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
