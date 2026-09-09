"""**점검 -- 무엇이 켜져 있나.**

앞 판은 갈래가 비면 이야기 층이 통째로 꺼지는데 **아무 말도 안 했다.** 원고는
멀쩡히 나오므로 아무도 못 알아챈다. 여기서는 켜짐/꺼짐을 늘 찍는다.
"""
from __future__ import annotations

import re

from nv2 import bank, ledger as LG, prompt as P, rules, ruler


def report(book: dict = None, card: dict = None) -> str:
    book = book or {"씨앗": "점검", "회차": 3, "회차분량": 5000, "원장": LG.blank()}
    card = card if card is not None else {
        "원함": "무엇을 얻는다", "막는것": "누가 막는다",
        "장면": ["하나", "둘", "셋"], "쾌감": "무릎", "전투": "둘이 붙는다",
        "바뀜": "자리가 생긴다", "끝": "문이 닫힌다"}
    p, dropped, spent = P.build(book, card, prev="앞 회차.\n")
    out = [f"[프롬프트]  통째 {len(p):,}자 · **지시 {spent:,}자** / 예산 {P.BUDGET:,}자"
           f" · 굵은 글씨 {len(re.findall(r'[*][*]', p)) // 2}군데",
           f"            블록 차례: {' → '.join(_blocks(p))}",
           f"            예산에 막혀 뺀 본보기: {' · '.join(dropped) or '없음'}"]

    out.append("\n[규칙]  잰다 · 부친다 · 고친다 셋을 갖춘 것만 산다")
    bad = rules.gate()
    out.append(f"        관문: {'이상 없음' if not bad else bad}")
    for r in rules.RULES:
        b = ruler.band(r.축)
        out.append(f"    {'산다' if b else '**죽었다**'}  {r.축:<10}"
                   + (f"밴드 {b[0]:.2f}~{b[1]:.2f}" if b else "표본이 없다 -- 규칙이 아니다")
                   + f"   ({r.왜})")
    out.append(f"        한 회차에 부치는 최대: {rules.MAX}개")

    out.append(f"\n[표본]  {len(ruler.samples())}편"
               f" ({' · '.join(s.get('이름', '?') for s in ruler.samples())})"
               "\n        밴드는 여기서만 나온다. 짐작한 수는 못 들어온다.")

    out.append(f"\n[은행]  칸 {len(bank.CATS)}개 · 항목 {bank.total()}개")
    out.append("        " + " · ".join(f"{c}(조건{len(bank.cond(c))}/본{len(bank.eg(c))})"
                                       for c in bank.CATS))

    led = book.get("원장") or {}
    out.append(f"\n[원장]  {LG.size(led)}개 · 주인공 «{LG.hero(led) or '아직 없다'}»")
    if not LG.hero(led):
        out.append("        * 이름이 없으면 수리가 '화자' 를 못 바꾼다 -- 첫 회차가 정한다.")
    return "\n".join(out)


def _blocks(p: str) -> list:
    return [l.strip().split("]")[0].lstrip("[").strip()
            for l in p.splitlines() if l.strip().startswith("[")]


if __name__ == "__main__":
    print(report())
