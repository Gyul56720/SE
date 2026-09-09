"""**회차 카드 -- 디렉터 한 번.** 무엇이 벌어지는가만 정한다. 산문은 안 쓴다.

앞 판에서 겪은 것 둘을 막는다:

1. **모델이 칸 설명을 값 대신 베껴 냈다.** "주인공이 이번 회차에 원하는 것 한 문장"
   이 그대로 값으로 왔고, 뼈대가 설명문이면 회차가 없다. `_echo` 가 그것을 잡는다.
2. **카드의 문장이 원고에 그대로 실렸다.** 그래서 카드를 '…한다' 대신 **짧은 명사구**
   로 받는다 -- 붙여넣어도 문장이 안 되게.
"""
from __future__ import annotations

import json
import re

FIELDS = ("원함", "막는것", "장면", "쾌감", "전투", "설정", "바뀜", "끝", "심음", "거둠")

_TMPL = {
    "원함": "주인공이 이번 회차에 손에 넣으려는 것. 눈에 보이는 것으로",
    "막는것": "누가 무엇으로 막는가. 사람이어야 한다",
    "장면": "셋. 각각 한 자리 · 한 때에서 벌어지는 일 (짧은 명사구)",
    "쾌감": "독자가 통쾌한 자리 하나 (벌어지는 일로)",
    "전투": "싸움이 있으면 누가 누구와 · 무엇으로 결착 · 무엇이 남는가. 없으면 빈 문자열",
    "설정": "이번 회차에 세우는 세계 설정 하나 -- 이름과 조건 한 줄",
    "바뀜": "회차가 끝났을 때 달라져 있는 것",
    "끝": "마지막 문단에서 실제로 벌어지는 일. 질문이나 예고가 아니라 벌어진 일",
    "심음": "지나가듯 심어 두는 것. 이번 회차에서 설명하지 않는다",
    "거둠": "앞에서 심은 것 중 이번에 거두는 것. 없으면 빈 문자열",
}


def ask(book: dict, arc: dict, prev_hook: str = "") -> str:
    from nv2 import bank
    n = int(book.get("회차") or 0)
    seed = str(book.get("씨앗") or "")
    eg = "\n".join(bank.line(p) for p in bank.draw("전개", seed, n, 3))
    joy = "\n".join(bank.line(p) for p in bank.draw("쾌감", seed, n, 3))
    return f"""이번 **회차**의 각본을 세운다. JSON 만 낸다 -- 산문을 쓰지 마라.

[이 이야기가 닿을 자리] {arc.get('끝', '')}
[처음의 주인공] {arc.get('시작', '')}
[아직 안 갚은 빚] {' · '.join(arc.get('빚') or []) or '(없음)'}
{f'[앞 회차의 끝] {prev_hook}' if prev_hook else ''}

[전개 본보기 -- 고르거나 섞거나 새로 지어라]
{eg}

[통쾌한 자리 본보기]
{joy}

**값을 넣어라. 아래 설명을 그대로 옮겨 적으면 그 카드는 버린다.**
{json.dumps({k: _TMPL[k] for k in FIELDS}, ensure_ascii=False, indent=1)}"""


def _echo(v) -> bool:
    """칸 설명을 베낀 것인가. 양쪽으로 본다 -- 통째로 베끼기도 하고 꼬리만 자르기도 한다."""
    t = str(v or "").strip().strip('"“”')
    if not t or t in ("...", "…", "-"):
        return True
    return any(t.startswith(e[:12]) or e in t or (len(t) >= 10 and t in e)
               for e in _TMPL.values())


def parse(raw: str) -> dict:
    """모델의 답에서 카드를 꺼낸다. 뼈대(원함 · 장면)가 베낌이면 **버린다**."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        raise ValueError("JSON 이 아니다")
    got = json.loads(m.group(0))
    want = str(got.get("원함") or "").strip()
    scenes = [str(x).strip() for x in (got.get("장면") or []) if str(x).strip()]
    if _echo(want) or not scenes or any(_echo(s) for s in scenes):
        raise ValueError(f"뼈대가 설명문이다 (원함={want[:24]!r} 장면={len(scenes)}개)")
    card = {"원함": want, "장면": scenes[:3]}
    for k in FIELDS:
        if k in ("원함", "장면"):
            continue
        v = got.get(k)
        card[k] = "" if _echo(v) else str(v).strip()
    return card


def make(book: dict, arc: dict, llm, prev_hook: str = "", tries: int = 2) -> dict:
    """호출 한 번(실패하면 한 번 더). 못 세우면 **빈 카드** -- 런은 계속 간다."""
    last = ""
    for _ in range(max(1, tries)):
        try:
            return parse(llm(ask(book, arc, prev_hook)))
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    return {"_실패": last}
