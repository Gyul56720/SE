"""**회차 하나를 한 번에 쓴다.**

앞 판은 3,200자 덩어리로 썼고 회차 비트와 계속 어긋났다 -- 회차가 일찍 끝나면
슬랙이 다음 회차에 얹혀 7,244자 / 11,502자로 벌어졌고, 걸친 비트는 같은 장면을
다시 열었다. 여기서는 **회차가 생성 단위**다.

쓰고 나서 셋을 한다: 무손실 수리 → 잰다 → 다음 회차에 넘길 말을 만든다.
**잡고도 안 고치는 자리를 두지 않는다.**
"""
from __future__ import annotations

from nv2 import ledger as LG, prompt as P, repair, rules, ruler


def once(book: dict, card: dict, llm, prev: str = "", owed=()) -> dict:
    text_in, dropped, spent = P.build(book, card, prev=prev, owed=owed)
    raw = (llm(text_in) or "").strip()
    if not raw:
        return {"상태": "빈 답", "글": "", "떨어뜨림": dropped, "지시": spent}

    hero = LG.hero(book.get("원장") or {})
    text, did, owe = repair.run(raw, who=hero, beats=(card or {}).get("장면") or [])
    m = ruler.measure(text)
    off = [(r.축, round(d, 2), round(g, 2)) for r, _s, d, g in rules.off(text)]
    return {
        "상태": "ok",
        "글": text,
        "잰것": m,
        "어긋남": off,
        "수리": did,
        "넘길말": list(owe),          # 다음 회차의 [반드시] 로 간다
        "떨어뜨림": dropped,
        "프롬프트": len(text_in), "지시": spent,
    }
