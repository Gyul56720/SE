"""**셈은 코드가 한다. 그리고 셈한 값은 어디서 왔는지를 들고 다닌다.**

`law/METHOD.md` 의 분업 그대로다 -- LLM 은 조문에서 요건을 뽑고, **쟁점은 코드가
도출한다.** 여기서도 같다: 모델은 무엇을 물을지 정하고, **수는 여기서만 나온다.**

## 값 하나는 혼자 다니지 않는다

    Fact(이름="일간등락", 값=-1.24, 단위="%",
         근거=(("^kospi","Close"), ("^kospi","Open")),
         규칙="일간등락", 인자=("^kospi",))

`근거` 가 있어야 관문이 **원장의 그 줄로 되짚을 수 있고**, `규칙`·`인자` 가 있어야
관문이 **다시 셈해서 대조할 수 있다.** 이 둘이 없는 수는 보고서에 못 들어간다 --
그것이 `law/gate.py` L001(인용한 조문이 원장에 실재하는가)의 자리다.

## 못 세는 것은 안 센다

분모가 0 이면(`High == Low` 인 날처럼) 값을 만들지 않는다. 0 으로 채우거나 앞의 값을
끌어다 쓰면 그 칸이 조용히 틀린 채 보고서에 들어간다. **미검증은 통과가 아니다.**
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Fact:
    이름: str
    값: float
    단위: str = ""
    근거: tuple = ()       # ((줄id, 칸), ...) -- 원장의 어느 줄 어느 칸에서 왔나
    규칙: str = ""         # 어떤 규칙으로 셌나 -- 관문이 이것으로 다시 센다
    인자: tuple = ()
    셈: str = ""           # 사람이 읽을 식


def _div(a, b):
    """0 으로 안 나눈다. 못 세면 None."""
    return None if b in (0, 0.0, None) or a is None else a / b


# ── 줄 하나에서 나오는 값 ────────────────────────────────────────────
# (필요한 칸, 셈, 사람이 읽을 식). 새 셈을 붙이는 것은 여기 한 줄이다.
def _일간등락(r):
    return _div((r.get("Close") - r.get("Open")) if r.get("Close") is not None
                and r.get("Open") is not None else None, r.get("Open"))


def _폭(r):
    return _div((r.get("High") - r.get("Low")) if r.get("High") is not None
                and r.get("Low") is not None else None, r.get("Open"))


def _종가위치(r):
    hi, lo, cl = r.get("High"), r.get("Low"), r.get("Close")
    if None in (hi, lo, cl):
        return None
    return _div(cl - lo, hi - lo)


RULES = {
    "일간등락": (("Open", "Close"), _일간등락, 100.0, "(종가-시가)/시가"),
    "폭": (("Open", "High", "Low"), _폭, 100.0, "(고가-저가)/시가"),
    "종가위치": (("High", "Low", "Close"), _종가위치, 1.0, "(종가-저가)/(고가-저가)"),
}


def row_facts(led, rid: str, want: tuple, 단위: dict | None = None) -> list:
    """줄 하나에서 낼 수 있는 값들. **못 세는 것은 조용히 빠진다.**"""
    r = led.찾기(rid)
    if r is None:
        return []
    단위 = 단위 or {}
    out = []
    for name in want:
        spec = RULES.get(name)
        if not spec:
            continue
        cols, fn, scale, 식 = spec
        v = fn(r)
        if v is None:
            continue
        out.append(Fact(이름=name, 값=v * scale, 단위=단위.get(name, ""),
                        근거=tuple((rid, c) for c in cols),
                        규칙=name, 인자=(rid,), 셈=식))
    return out


def raw_facts(led, rid: str, cols: tuple, 단위: dict | None = None) -> list:
    """원장에 적힌 값 그대로. 근거는 자기 자신이다 -- 셈한 것이 아니므로 규칙이 없다."""
    r = led.찾기(rid)
    if r is None:
        return []
    단위 = 단위 or {}
    return [Fact(이름=c, 값=r[c], 단위=단위.get(c, ""), 근거=((rid, c),), 규칙="", 셈="원장 그대로")
            for c in cols if isinstance(r.get(c), (int, float))]


# ── 칸 하나를 세로로 훑는 값 ─────────────────────────────────────────
# **여기가 '범용' 이 사는 자리다.** 위의 RULES 는 시가·종가를 아는 셈이라 주식에만
# 쓰인다. 아래 것들은 **칸이 수이기만 하면** 무엇이든 센다 -- 티켓값이든 기온이든
# 논문 편수든. 처음 보는 출처를 요청 시점에 붙일 수 있는 것은 이것 덕이다.


def _중앙(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _표준편차(v):
    if len(v) < 2:
        return None                       # 하나짜리 표준편차는 없는 값이다
    m = sum(v) / len(v)
    return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5


ACROSS = {
    "개수": (len, "몇 줄에 이 값이 있나"),
    "최소": (min, "가장 작은 값"),
    "중앙": (_중앙, "가운데 값"),
    "평균": (lambda v: sum(v) / len(v), "산술평균"),
    "최대": (max, "가장 큰 값"),
    "합": (sum, "다 더한 것"),
    "표준편차": (_표준편차, "표본표준편차"),
}

# 기본으로 낼 것. 합은 뺀다 -- 기온이나 값의 '합' 은 뜻이 없는 경우가 많고,
# 뜻 없는 수를 화면에 올리면 읽는 사람이 뜻을 찾아내려 한다.
기본요약 = ("개수", "최소", "중앙", "평균", "최대", "표준편차")


def 값들(led, col: str) -> list:
    """그 칸의 수들. **수가 아닌 줄은 조용히 빠진다** -- 0 으로 안 채운다."""
    return [r[col] for r in led.줄 if isinstance(r.get(col), (int, float))]


def col_facts(led, col: str, want=기본요약, 단위: dict | None = None) -> list:
    """칸 하나에서 나오는 요약값들. 근거는 **그 칸을 가진 모든 줄**이다."""
    v = 값들(led, col)
    if not v:
        return []
    단위 = 단위 or {}
    근거 = tuple((r["id"], col) for r in led.줄
                if isinstance(r.get(col), (int, float)))
    out = []
    for name in want:
        spec = ACROSS.get(name)
        if not spec:
            continue
        fn, 식 = spec
        got = fn(v)
        if got is None:
            continue
        out.append(Fact(이름=f"{col}.{name}", 값=float(got),
                        단위="" if name == "개수" else 단위.get(col, ""),
                        근거=근거, 규칙=name, 인자=(col,), 셈=식))
    return out


# ── 여러 줄에 걸친 값 ────────────────────────────────────────────────
def 순위(facts: list, 이름: str) -> list:
    """그 이름의 값들을 큰 것부터. (줄id, 값) 목록 -- **동점은 동점으로 둔다.**"""
    got = [(f.인자[0] if f.인자 else (f.근거[0][0] if f.근거 else ""), f.값)
           for f in facts if f.이름 == 이름]
    return sorted(got, key=lambda kv: -kv[1])


def 흩어짐(facts: list, 이름: str) -> Fact | None:
    """값들이 한 방향인가 갈렸는가. **표본이 둘 미만이면 안 센다.**"""
    got = [f for f in facts if f.이름 == 이름]
    if len(got) < 2:
        return None
    vals = [f.값 for f in got]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    근거 = tuple(sorted({g for f in got for g in f.근거}))
    return Fact(이름=f"{이름}_흩어짐", 값=var ** 0.5, 단위=got[0].단위, 근거=근거,
                규칙="", 셈=f"{len(vals)}개의 표본표준편차")


def 한방향인가(facts: list, 이름: str) -> tuple:
    """(오른 것, 내린 것, 안 움직인 것). **판정이 아니라 셈이다.**"""
    vals = [f.값 for f in facts if f.이름 == 이름]
    return (sum(1 for v in vals if v > 0), sum(1 for v in vals if v < 0),
            sum(1 for v in vals if v == 0))
