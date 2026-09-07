"""**단조량** -- 사슬이 어디로 가는가. 호출 0회.

Perelman 이 Ricci 흐름에서 한 일의 열쇠는 **흐름을 따라 한 방향으로만 움직이는 양**
(𝒲 엔트로피)이었다. 그것이 있어야 압축성이 나오고, 압축성이 있어야 특이점을 분류할 수
있었다. Hamilton 은 1982년에 도약을 했고, 20년이 걸린 것은 그 다음이었다.

여기엔 그런 양이 하나도 없었다. 연산자를 걸어도 무엇이 반드시 줄거나 느는지가 없어서
**사슬이 어디로 가는지 말할 수가 없었다** -- 표류가 정말 표류였다.

## 무엇을 세나 -- 넷, 그리고 그중 하나만 정리다

    치수        점이 수 몇 개인가            (rec["치수"])
    정의역등급   3 연속 · 2 이산무한 · 1 유한  (정의역의 **기호**에서)
    제약수      식 안의 관계 기호 수          (= · ≤ · ≡ · ∀ ...)
    검산m       **왕복이 통과한 스킴의 곱셈 수**

앞의 셋은 **적어 낸 것을 세는 것**이다. 정리가 아니라 부기(簿記)다. 넷째만 다르다 --
왕복(부호화 → 해독 → Brent)이 통과했다면 그 공간은 곱셈 m 번짜리 스킴을 **실제로 들고
있고**, 그것은 `R(<n,n,n>) ≤ m` 이라는 정리다. 기계가 검산한 것이다.

## 방향은 선언이지 증명이 아니다

연산자마다 어느 양이 어느 쪽으로 움직여야 하는지를 적어 둔다(`DIR`). 이산화는 정의역을
좁히고, 대칭성 강제는 제약을 늘리고, 경계화는 ε 하나를 더한다. 사슬을 따라 그 선언대로
움직였는지 본다.

**그러나 이것은 그 양이 정말 단조라는 증명이 아니다.** 선언한 대로 움직였는지를 셀 뿐이다.
진짜로 하려면 Strassen 의 **점근 스펙트럼**이 있어야 한다 -- 퇴화 아래 단조이고 ⊕ 에
가법적, ⊗ 에 승법적인 범함수들. 경계 랭크가 퇴화 아래 단조인 것, ω 가 그 스펙트럼 위의
하한으로 결정되는 것이 그 이론이다. 여기서 하는 것은 그 자리에 놓을 **부기**다.

## 그리고 이것도 게이트가 아니다

선언과 어긋났다고 기각하지 않는다. **어긋난 자리를 짚는 것**이 일이다 -- 선언이 틀렸거나,
그 걸음이 연산자 이름과 다른 일을 했거나 둘 중 하나이고, 둘 다 알 만한 것이다.

    python3 mathdrift/spread.py --mono         # 사슬마다 궤적
    python3 mathdrift/spread.py --mono S17     # 하나만
"""
from __future__ import annotations

import re

from mathdrift import act as ACT
from mathdrift import space as SP

# ── 정의역 등급 ───────────────────────────────────────────────────────
# **기호로만 가른다.** 한국어를 보면 이 자도 두 번 뒤집힌 그 자리로 돌아간다.
# ℚ 는 셀 수 있지만 조밀하다 -- 탐색공간의 크기로는 이산 무한 쪽에 둔다(정직한 임의).
# `\mathbb{Z}/p\mathbb{Z}` 는 몫이라 **유한**이다. 그런데 "Z/" 로만 찾으면 여기 안 걸린다
# -- 사이에 `}` 가 끼어 있어서다. 그대로 두면 유한 몫환이 이산무한(2)으로 읽혔다(실측).
# 슬래시가 붙은 것만 잡는다: `\mathbb{Z}_p` (p 진 정수)는 몫이 아니고 유한도 아니다.
FINITE = (r"F_2", r"F_p", r"F_q", "GF", r"\mathbb{F}", "Z/", r"\mathbb{Z}/", r"\bmod",
          r"\{-1,0,1\}", r"\{0,1\}", "char")
DISCRETE = (r"\mathbb{Z}", r"\mathbb{N}", r"\mathbb{Q}", r"\Lambda", "lattice", "Z", "N")
CONTINUOUS = (r"\mathbb{R}", r"\mathbb{C}", "R", "C", r"\overline", "cont")

GRADE_NAME = {3: "연속", 2: "이산무한", 1: "유한", 0: "모름"}


def domain_grade(text: str) -> int:
    """3 연속 · 2 이산무한 · 1 유한 · 0 모름. **좁을수록 작다.**"""
    t = text or ""
    if any(k in t for k in FINITE):
        return 1
    if any(k in t for k in DISCRETE):
        return 2
    if any(k in t for k in CONTINUOUS):
        return 3
    return 0


# 관계 기호 -- 하나가 하나의 제약이다. `\in` 은 뺀다: "m \in \mathbb{N}" 처럼 자료형을
# 말하는 자리에 너무 흔해서, 세면 제약이 아니라 문법을 세게 된다.
REL = (r"\equiv", r"\leq", r"\geq", r"\le", r"\ge", r"\neq", r"\forall", r"\sim",
       r"\cong", "=", "<", ">")


def constraints(expr: str) -> int:
    toks = ACT.tokens(expr)
    named = {r"\leq", r"\geq", r"\le", r"\ge", r"\neq", r"\equiv", r"\forall",
             r"\sim", r"\cong"}
    n = 0
    for i, t in enumerate(toks):
        if t in named:
            n += 1
        elif t in ("<", ">", "!"):
            # `<=` `>=` `!=` 는 여기서 한 번 센다
            n += 1
        elif t == "=":
            # 앞이 `<` `>` `!` 면 이미 셌다 -- 두 번 세지 않는다.
            # (처음에 반대로 짜서 `a <= b` 가 0 이 됐다. 둘 다 건너뛴 것이다.)
            if not (i and toks[i - 1] in ("<", ">", "!")):
                n += 1
    return n


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def touchstone_m(got: dict) -> int | None:
    """왕복이 통과한 **그 시금석**의 곱셈 수. 원장이 적어 둔 것에서만 읽는다.

    처음엔 `got.get("m") or 7` 이었다. `recall` 이 m 을 적지 않으므로 그것은 늘 7 --
    **상수를 정리인 척 돌려주는 자리**였다. 시금석이 b=3 으로 바뀌면 7 이 그대로 남아
    거짓말이 된다. 그래서 원장의 `시금석`("strassen b=2 m=7")에서 읽고, 없으면 None 이다.
    """
    m = re.search(r"m\s*=\s*(\d+)", str(got.get("시금석") or ""))
    return int(m.group(1)) if m else None


def quants(rec: dict) -> dict:
    """이 공간의 넷. 모르면 None -- **모르는 것은 모른다고 한다.**"""
    g = domain_grade(str(rec.get("정의역") or ""))
    got = rec.get("재현") or {}
    return {
        "치수": _int(rec.get("치수")),
        "정의역등급": g or None,
        "제약수": constraints(str(rec.get("식") or "")) or None,
        # **이것만 정리다.** 왕복이 통과했을 때만 값이 있다.
        "검산m": touchstone_m(got) if got.get("판정") == "재현" else None,
    }


# ── 연산자가 어느 쪽으로 미는가 (선언) ───────────────────────────────
# 적지 않은 칸은 **모른다**는 뜻이다. 억지로 채우면 자가 뒤집힌다 -- 이 저장소가 자국
# 목록에서 망각을 비워 둔 것과 같은 이유다.
DIR = {
    "이산화":     {"정의역등급": "↓"},
    "표수 이동":   {"정의역등급": "↓"},
    "완비화":     {"정의역등급": "↑"},
    "경계화":     {"치수": "↑"},          # ε 하나가 는다
    "상대화":     {"치수": "↑"},          # 밑을 하나 깐다
    "대칭성 강제": {"제약수": "↑", "치수": "↓"},
    "국소화":     {"제약수": "↓"},        # 가역으로 만들면 조건이 준다
    "망각":       {"제약수": "↓"},        # 구조를 지운다
    "탈범주화":   {"치수": "↓"},          # 대상을 수 하나로 내린다
    "범주화":     {"치수": "↑"},
    # 매장 · 내부화 · 쌍대 · 점근화 · 불변량 이동 -- 방향을 모른다. 비워 둔다.
}

_ARROW = {"↑": 1, "↓": -1, "=": 0}


def step(parent: dict, child: dict, op: str) -> dict:
    """한 걸음에서 넷이 어떻게 움직였나, 그리고 선언과 맞는가."""
    a, b = quants(parent), quants(child)
    want = DIR.get(op, {})
    rows = {}
    for k in ("치수", "정의역등급", "제약수", "검산m"):
        x, y = a[k], b[k]
        if x is None or y is None:
            rows[k] = {"전": x, "후": y, "움직임": None, "선언": want.get(k), "어긋남": False}
            continue
        moved = (y > x) - (y < x)
        d = want.get(k)
        rows[k] = {"전": x, "후": y, "움직임": moved, "선언": d,
                   "어긋남": bool(d and _ARROW[d] and moved and _ARROW[d] != moved)}
    return rows


def chain(led: dict, sid: str) -> list:
    """씨앗까지의 사슬을 걸음으로 편다."""
    ids = SP.lineage(led, sid)
    out = []
    for i in range(len(ids) - 1):
        par, kid = SP.get(led, ids[i]), SP.get(led, ids[i + 1])
        if par is None or kid is None:
            continue
        op = (kid.get("계보") or {}).get("연산자", "")
        out.append({"id": kid["id"], "연산자": op, "칸": step(par, kid, op)})
    return out


def monotone(rows: list, key: str) -> str:
    """사슬 전체에서 그 양이 한 방향으로만 갔나. **이것이 있어야 궤적이다.**"""
    moves = [r["칸"][key]["움직임"] for r in rows if r["칸"][key]["움직임"] is not None]
    if not moves:
        return "모름"
    ups = sum(1 for m in moves if m > 0)
    downs = sum(1 for m in moves if m < 0)
    if ups and downs:
        return "오르내림"
    if ups:
        return "단조↑"
    if downs:
        return "단조↓"
    return "그대로"


def leaves(led: dict) -> list:
    """자식이 없는 공간 -- 사슬의 끝이다."""
    parents = {(s.get("계보") or {}).get("부모") for s in led["spaces"]}
    return [s["id"] for s in led["spaces"] if s["id"] not in parents]


def show(led: dict, sid: str) -> int:
    rows = chain(led, sid)
    if not rows:
        print(f"{sid} 는 씨앗이다 -- 사슬이 없다")
        return 0
    print(f"{' -> '.join(SP.lineage(led, sid))}\n")
    hdr = f"{'걸음':<6} {'연산자':<10}"
    for k in ("치수", "정의역등급", "제약수", "검산m"):
        hdr += f" {k:>10}"
    print(hdr)
    for r in rows:
        line = f"{r['id']:<6} {r['연산자']:<10}"
        for k in ("치수", "정의역등급", "제약수", "검산m"):
            c = r["칸"][k]
            if c["후"] is None:
                line += f" {'-':>10}"
            else:
                mark = {1: "↑", -1: "↓", 0: "="}.get(c["움직임"], " ")
                bad = "!" if c["어긋남"] else " "
                line += f" {str(c['후']) + mark + bad:>10}"
        print(line)
    print()
    for k in ("치수", "정의역등급", "제약수", "검산m"):
        print(f"  {k:<10} {monotone(rows, k)}")
    bad = [(r["id"], k, r["칸"][k]["선언"]) for r in rows
           for k in r["칸"] if r["칸"][k]["어긋남"]]
    if bad:
        print("\n  선언과 어긋난 걸음 (! 표시):")
        for sid2, k, d in bad:
            print(f"    {sid2}  {k} 가 {d} 여야 하는데 반대로 갔다")
        print("  -- 선언이 틀렸거나 그 걸음이 연산자 이름과 다른 일을 했다. 둘 다 알 만한 것이다")
    print("\n  **부기이지 정리가 아니다.** `검산m` 만 다르다 -- 왕복이 통과했으면 그 공간은")
    print("  곱셈 m 번짜리 스킴을 실제로 들고 있고, 그것은 R(<n,n,n>) <= m 이라는 정리다.")
    return 0


def report(led: dict, only: str = "") -> int:
    if only:
        return show(led, only)
    lv = leaves(led)
    if not lv:
        print("사슬이 없다 -- 씨앗뿐이다")
        return 0
    print(f"사슬 {len(lv)}개 (끝점 기준)\n")
    print(f"{'끝':<6} {'길이':>4}  {'치수':<8} {'정의역':<8} {'제약수':<8} {'검산m':<8} 어긋남")
    n_mono = {k: 0 for k in ("치수", "정의역등급", "제약수", "검산m")}
    for sid in lv:
        rows = chain(led, sid)
        if not rows:
            continue
        cells = []
        for k in ("치수", "정의역등급", "제약수", "검산m"):
            m = monotone(rows, k)
            cells.append(m)
            if m.startswith("단조"):
                n_mono[k] += 1
        bad = sum(1 for r in rows for k in r["칸"] if r["칸"][k]["어긋남"])
        print(f"{sid:<6} {len(rows):>4}  " + "".join(f"{c:<9}" for c in cells)
              + (f"{bad}개" if bad else ""))
    print("\n한 방향으로만 간 사슬:")
    for k, n in n_mono.items():
        print(f"  {k:<10} {n}/{len(lv)}")
    print("\n**이것이 있어야 사슬이 어디로 가는지 말할 수 있다.** 없으면 표류가 정말 표류다.")
    print("다만 부기다 -- 진짜로 하려면 Strassen 의 점근 스펙트럼(퇴화 아래 단조인 범함수)이")
    print("있어야 하고, 경계 랭크가 그 아래 단조인 것이 그 이론이다.")
    return 0
