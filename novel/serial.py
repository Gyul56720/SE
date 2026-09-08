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

def plan_prompt(gname: str, seed: str = "") -> str:
    """**디렉터에게 한 번만 묻는다.** 300토큰짜리 답 하나다.

    갈래 꾸러미의 머리와 관계 축을 얹는다 -- 지어내라고 하지 않고 **이 갈래의
    결말**을 내라고 한다. 인물 이름은 여기서 정하지 않는다: 아직 원고가 없어서
    누가 나올지 모르고, 이름은 `이름결` 이 첫 덩어리에서 정한다.

    **줄기 본보기**(space.ARCS)를 넷 보여 준다. 사용자(2026-09-08): "복수극도 좋고,
    거지가 왕궁 들어가서 권력 탈취하는 것도 좋고 -- 예시야, 하드코딩하지 마." 그래서
    복수와 왕좌는 열여덟 꼴 중 둘이고, 씨앗마다 다른 넷이 보인다. 고르거나 섞거나
    목록 밖을 지어도 된다 -- 지키는 것은 꼴(시작에서 못 하던 것을 끝에서 한다)이다.
    """
    from novel import space as SP
    pack = GENRE.get(gname) if gname else {}
    head = (pack.get("머리") or "").strip()
    rel = ", ".join(list(pack.get("관계") or {})[:8])
    return f"""이 소설이 **어디로 갈지**만 정한다. 줄거리는 정하지 않는다.

{f'[갈래] {pack.get("name", gname)}' if pack else ''}
{head}
{f'[이 갈래가 다루는 관계] {rel}' if rel else ''}

[줄기 본보기 -- 이 소설 전체의 꼴은 이런 것들이다. 하나를 고르거나 둘을 섞는다. 목록 밖을 지어도 된다]
{SP.render("줄기", seed or "씨", 0, 4)}

네 가지를 JSON 으로 낸다.

1. **줄기** -- 고른 꼴의 이름 한두 낱말. 본보기 중 하나이거나, 둘을 섞은 것이거나, 네가 지은 것.

2. **끝** -- 이 소설이 끝나는 자리 한 문장. 사건이 아니라 **상태**로 적어라.
   ("두 사람이 결혼한다" 가 아니라 "그 계약이 더는 두 사람을 묶지 못한다")
   **끝은 되찾고 · 편을 늘리고 · 누군가 그것을 인정하는 자리다.** 값을 치르고 물러나는
   끝이 아니다 -- 시작에서 못 하던 것을 끝에서 하고, 그것을 남들이 본다.

3. **시작** -- 주인공이 처음에 **못 하는 것 · 없는 것 · 당하는 것** 한 문장. 끝과 짝이
   되어야 한다: 시작에서 못 하던 것을 끝에서 한다. 이것이 성장이다.

4. **빚** -- 그 끝이 참이 되려면 **먼저 참이 되어야 하는 것** {DEBTS[0]}~{DEBTS[1]}개.
   - 각각 한 문장. **상태로 적어라.** 무슨 장면을 쓰라는 말이 아니다.
   - 순서대로 적어라 -- 앞엣것이 먼저 참이 되어야 뒤엣것이 가능하다.
   - **앞의 절반은 역경이다.** 주인공이 잃거나 당하거나 실패해야 참이 되는 것. 뒤의
     절반은 그 값으로 얻는 것. 처음부터 이기는 사람은 자라지 않는다.
   - 뒤의 절반에는 **되갚는 것 · 오르는 것 · 곁에 서는 사람**이 하나씩 들어 있어야 한다.
   - **어떻게** 참이 되는지는 적지 마라. 그건 쓰면서 정한다.

구체적으로 적어라. "권력을 얻는다" 가 아니라 무엇을 손에 쥐고 누가 그 앞에 무릎을 꿇는지다.
인물 이름을 정하지 마라. 아직 아무도 없다.

{{"줄기": "...", "끝": "...", "시작": "...", "빚": ["...", "...", "...", "..."]}}"""


def plan(book: dict, llm, gname: str = "", log=None) -> dict:
    """도착지를 세워 원고에 붙인다. **호출 한 번.** 이미 있으면 안 덮는다."""
    if planned(book):
        D._log("[연재] 도착지가 이미 있다 -- 그대로 간다")
        return arc(book)
    seed = str(book.get("seed_id") or book.get("first") or "")
    got = D.call_json(D._llm_for(llm, "director"),
                      plan_prompt(gname, seed), label="연재 도착지")
    end = str(got.get("끝") or "").strip()
    start = str(got.get("시작") or "").strip()
    shape = str(got.get("줄기") or "").strip()
    debts = [str(x).strip() for x in (got.get("빚") or []) if str(x).strip()]
    if not end or not debts:
        raise ValueError(f"도착지를 못 받았다: 끝={end!r} 빚={len(debts)}개")
    # **넘치면 자르되 모자라면 안 채운다.** 채우려면 지어내야 한다.
    debts = debts[:DEBTS[1]]
    book["arc"] = {"end": end, "start": start, "shape": shape,
                   "debts": [{"무엇": d, "갚음": 0} for d in debts],
                   "made": gname}
    if shape:
        D._log(f"[연재] 줄기: {shape}")
    if start:
        D._log(f"[연재] 시작: {start}")
    D._log(f"[연재] 끝: {end}")
    for i, d in enumerate(debts, 1):
        D._log(f"[연재]   빚 {i}. {d}")
    return book["arc"]


# ---------------------------------------------------------------- 어디쯤인가

def span(book: dict) -> int:
    """한 마디의 길이. **목표 분량을 알면 거기에 맞춘다.**

    빚 다섯에 마디 1만 자면 5만 자를 써야 마지막 빚을 지나고, 목표가 5만 자면 끝을
    향하는 마디가 **없다** -- 원고가 목표에 닿아 멈추는데 결말은 안 왔다. 그래서
    목표를 (빚 수 + 1) 로 나눈다: 빚마다 한 마디, 마지막 한 마디는 끝을 향한다.
    목표를 모르면(검사 · 옛 원고) SPAN 그대로다."""
    target = int(book.get("_target") or 0)
    ds = arc(book).get("debts") or []
    if target > 0 and ds:
        return max(1500, target // (len(ds) + 1))
    return SPAN


def where(book: dict) -> int:
    """지금 몇 번째 마디인가. **분량으로 센다 -- 호출이 안 든다.**"""
    n = sum(len(c) for c in (book.get("chunks") or []))
    return n // max(1, span(book))


def closing(book: dict) -> bool:
    """**마지막 덩어리인가.** 목표까지 남은 분량이 덩어리 하나 남짓이면 이번에 닫는다."""
    target = int(book.get("_target") or 0)
    if target <= 0:
        return False
    n = sum(len(c) for c in (book.get("chunks") or []))
    return done(book) and target - n <= 4000


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

# 성장 곡선. 마디가 어디쯤이냐로 **주인공이 지금 지는 중인지 이기는 중인지**를 정한다.
# 사용자 요구(2026-09-08): "주인공이 성장하지 않는다 -- 역경을 만나고 힘들어가다가
# 성장한다." 갚혔는지 판정을 안 하는 것(위)과 같은 이유로 이것도 **분량으로** 간다.
STAGES = (
    ("진다", "주인공은 이 대목에서 **진다.** 당하고, 잃고, 막힌다. 되받아치지 못한다 --"
             " 아직 그럴 힘도 사람도 없다. 그 무력함을 감추지 말고 보여라."),
    ("버틴다", "주인공은 이 대목에서 **값을 치른다.** 원하는 것을 얻으려면 무엇을 내놓아야"
               " 하고, 내놓는다. 이기지는 못하지만 처음처럼 당하지도 않는다."),
    ("이긴다", "주인공은 이 대목에서 **처음에 못 하던 것을 한다.** 앞에서 잃은 것 · 치른"
               " 값 · 데려온 사람이 여기서 돌아온다. 쉽게 이기지 마라 -- 값을 치른 만큼만."),
)


def stage(book: dict) -> "tuple | None":
    """지금 마디의 성장 단계. 빚 목록을 셋으로 나눠 앞 · 중간 · 뒤로 본다."""
    ds = arc(book).get("debts") or []
    if not ds:
        return None
    i = min(where(book), len(ds) - 1)
    return STAGES[min(2, i * 3 // len(ds))]


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
    if closing(book):
        return ("[어디로] **여기서 이야기를 닫는다.** 이것이 마지막 대목이다.\n"
                f"  · 이 이야기가 닿을 자리: {a['end']}\n"
                "  · 열려 있던 것에 답을 주고, 두 사람이 어디에 서 있는지 보이게 하고,"
                " **마지막 문장으로 끝내라.** 다음 대목을 예고하지 마라.\n"
                "  · 이 문장을 원고에 옮겨 적지 마라.")
    if done(book):
        return ("[어디로] **이제 끝을 향해 간다.**\n"
                f"  · 이 이야기가 닿을 자리: {a['end']}\n"
                "  · 서두르지 마라. 다만 이 대목의 일이 그 자리에서 **멀어지지는**"
                " 않게 해라.")
    st = stage(book)
    grow = f"  · {st[1]}\n" if st else ""
    if a.get("start") and st and st[0] == "진다":
        grow += f"  · 처음의 주인공: {a['start']}\n"
    return ("[어디로] **이 대목이 향하는 곳**\n"
            f"  · {cur['무엇']}\n"
            "  · 여기서 그것을 이루라는 말이 아니다. **한 걸음 가까워지면 된다** --"
            " 멀어지는 일이 벌어져도 좋다, 그것이 이 방향의 일이기만 하면.\n"
            + grow +
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
    return ((f"줄기: {a['shape']}\n" if a.get("shape") else "")
            + (f"시작: {a['start']}\n" if a.get("start") else "")
            + f"끝: {a['end']}\n"
            f"원고 {n:,}자 · 마디 {at + 1} (한 마디 {span(book):,}자)\n"
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

    if planned(book):
        # **안 쓴다.** 돌고 있는 런이 같은 파일을 쓰고 있을 수 있다 -- 읽은 것을 그대로
        # 되쓰면 그 사이에 저장된 덩어리를 지운다.
        print("도착지가 이미 있다 -- 그대로 간다")
        print(show(book))
        return 0
    plan(book, D.default_llm, a.genre)
    p.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(show(book))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
