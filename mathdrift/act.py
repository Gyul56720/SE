"""**연산자가 식에 자국을 남겼는가** -- 기호로 묻는다. 호출 0회, 아무것도 거르지 않는다.

낱말 겹침 자는 두 번 뒤집혔다. 이유는 하나였다: 연산자가 무슨 일을 했는지를 **한국어로**
물었기 때문이다. 부모 이름에 수식어를 덧붙인 것이 최고점을 받고(0.933), 진짜 이주
(ε-근사 · 그로텐디크)가 0 으로 깔렸다.

기호로 물으면 그 문제가 사라진다. 경계화면 `\\lim` 이나 `\\epsilon` 이 들어오고, 국소화면
`S^{-1}` 이 붙고, 쌍대면 `\\inf` 가 `\\sup` 이 된다. **그건 취향이 아니라 토큰이다.**

## 자국은 diff 의 양쪽에 있다

더한 것만 보면 안 된다. 쌍대는 `\\sup` 을 더하면서 `\\inf` 를 뺀다. 탈범주화는 구조를
지우고 수를 남긴다. 그래서 `spread.diff` 와 같은 토큰 diff 를 쓰되 **더한 쪽과 뺀 쪽을
따로** 본다.

## 모르는 것은 모른다고 한다

열다섯 연산자 전부에 믿을 만한 자국을 정할 수 없다. **망각**이 그렇다 -- 구조를 지우는
것이라 자국이 "없어짐" 인데, 무엇이 없어져야 하는지는 부모 식마다 다르다. 그런 것은
`미정` 으로 두고 판정하지 않는다. 억지로 목록을 채우면 그 자가 또 뒤집힌다.

    python3 mathdrift/spread.py --act        # 원장 전체
    python3 mathdrift/spread.py --diff S10   # 한 공간 (자국 한 줄이 함께 나온다)
"""
from __future__ import annotations

# (더해져야 할 것, 빠져야 할 것). 하나라도 맞으면 자국이 있다고 본다.
#
# **판정이 아니라 눈금이다.** 자국이 없다고 기각하지 않는다 -- 목록에 없는 방식으로
# 같은 일을 할 수 있고(경계화를 `\\overline{R}` 로 쓰는 것처럼), 그것을 벌하면 발산이
# 목록을 채우는 쪽으로 균질해진다. `novel/` 에서 이미 겪은 그것이다.
SIGNS = {
    "경계화":     ((r"\lim", r"\epsilon", r"\varepsilon", r"\overline", r"\to", "O", "eps"), ()),
    "완비화":     ((r"\hat", r"\widehat", r"\varprojlim", r"\overline", r"\lim", r"\infty"), ()),
    "표수 이동":   ((r"\bmod", r"\equiv", r"\mathbb", "F", "p", "char"), (r"\mathbb",)),
    "이산화":     ((r"\mathbb", r"\Lambda", r"\cap", r"\{", "Z", "lattice"), ()),
    "대칭성 강제": ((r"\sigma", r"\forall", r"\in", "G", r"\pi", "inv"), ()),
    "국소화":     (("S", r"\mathfrak", r"\otimes", "loc", "-1"), ()),
    "쌍대":       ((r"\sup", r"\vee", r"\ast", "op", r"\check", "*"), (r"\inf",)),
    "점근화":     ((r"\omega", r"\tau", r"\inf", r"\lim", r"\infty", "O", "n"), ()),
    "매장":       ((r"\rho", r"\hookrightarrow", r"\otimes", r"\mathbb", "k", "G"), ()),
    "범주화":     ((r"\mathcal", r"\Rightarrow", r"\simeq", r"\cong", "2"), ("=",)),
    "탈범주화":   ((r"\dim", r"\chi", r"\mathrm", r"\operatorname", "rank", "K"), ()),
    "내부화":     ((r"\mathcal", r"\underline", r"\mathrm", "Hom", "Ob"), ()),
    "상대화":     (("S", r"\times", r"\to", "_S", "/S"), ()),
    "불변량 이동": (("H", r"\chi", r"\dim", "c", r"\mathrm", "hom"), ()),
    # 망각 -- **자국을 정하지 않는다.** 구조를 지우는 것이라 자국이 "없어짐" 인데,
    # 무엇이 없어져야 하는지는 부모 식마다 다르다. 억지로 채우면 자가 뒤집힌다.
}


def marks(added: list, removed: list, op: str) -> dict:
    """더한 토큰과 뺀 토큰에서 연산자의 자국을 찾는다.

    `added` / `removed` 는 `spread.diff` 가 쓰는 것과 같은 LaTeX 토큰 목록이다.
    """
    if op not in SIGNS:
        return {"판정": "미정", "자국": [], "왜": f"{op} 은 자국을 정하지 않았다"}
    want_in, want_out = SIGNS[op]
    hit = []
    for t in added:
        for w in want_in:
            if w in t:
                hit.append("+" + t)
                break
    for t in removed:
        for w in want_out:
            if w in t:
                hit.append("-" + t)
                break
    if not (added or removed):
        return {"판정": "없음", "자국": [], "왜": "식이 글자 그대로 같다"}
    if hit:
        # 같은 토큰이 여러 번 나오면 한 번만 적는다 -- 세는 것이 아니라 보이는 것이 목적이다.
        seen, uniq = set(), []
        for h in hit:
            if h not in seen:
                seen.add(h)
                uniq.append(h)
        return {"판정": "있음", "자국": uniq[:8], "왜": ""}
    return {"판정": "없음", "자국": [],
            "왜": f"바뀐 토큰에 {op} 의 자국이 없다 (더함 {len(added)} · 뺌 {len(removed)})"}


def note(m: dict) -> str:
    if m["판정"] == "있음":
        return "자국 있음: " + " ".join(m["자국"])
    if m["판정"] == "미정":
        return "자국 미정 -- " + m["왜"]
    return "자국 없음 -- " + m["왜"]


def tally(rows: list) -> str:
    """연산자별로 자국이 몇 번 남았나. **연산자가 일을 하고 있는가**를 기호로 센 것이다."""
    by = {}
    for op, m in rows:
        d = by.setdefault(op, {"있음": 0, "없음": 0, "미정": 0})
        d[m["판정"]] += 1
    out = []
    for op in sorted(by, key=lambda k: -(by[k]["있음"] + by[k]["없음"] + by[k]["미정"])):
        d = by[op]
        n = d["있음"] + d["없음"] + d["미정"]
        mark = "미정" if d["미정"] == n else f"{d['있음']}/{d['있음'] + d['없음']}"
        out.append(f"  {op:<12} {mark:>7}  (본 것 {n})")
    return "\n".join(out)
