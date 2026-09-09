"""**관문.** 보고서의 수가 원장에서 왔는지 본다. LLM 이 아니다.

    B001  근거가 붙어 있는가                       hard
    B002  그 근거가 원장에 **실재하는가**           hard
    B003  원장이 낡지 않았는가                      hard
    B004  **다시 셈해도 같은 값인가**                hard
    B005  근거 없이 단정하는가                      soft

`law/gate.py` 의 L001(인용한 조문이 원장에 실재하는가)을 수로 옮긴 것이다. 거기서
"판례가 실재하는가" 가 취향이 아니듯, 여기서도 **"이 수가 원장의 어느 줄에서 나왔는가"
는 취향이 아니다.**

## B004 가 이 파일의 요점이다

나머지 넷은 꼬리표를 보는 검사다. B004 는 **관문이 값을 직접 다시 센다** -- 생성 쪽
코드를 부르는 것이 아니라 원장의 줄에서 규칙을 다시 돌려 견준다. 그래서 셈하는 자리가
조용히 틀리면 여기서 걸린다.

`law/gate.py` 가 "법리가 타당한가" 를 안 보는 것과 같은 선을 여기서도 긋는다 --
**이 관문은 그 수가 옳은지를 보지, 그 수가 중요한지를 보지 않는다.** 무엇이 중요한가는
외적 정당화(METHOD 1-7)이고 기계의 관할이 아니다.
"""
from __future__ import annotations

from dataclasses import dataclass

from brief import derive as DV
from brief import infer as INFER

TOL = 1e-6          # 다시 센 값과 이만큼까지는 같은 것으로 본다 (부동소수 오차)

AIM = {
    "B001": "보고서의 모든 수에 근거가 붙어 있어야 한다",
    "B002": "그 근거가 원장에 실재해야 한다",
    "B003": "원장이 출처가 정한 신선도 안이어야 한다",
    "B004": "관문이 다시 셈해도 같은 값이어야 한다",
    "B005": "근거 없이 단정하지 않아야 한다",
}

# 근거 없이 쓰면 걸리는 말. **닫힌 목록이다** -- 뜻으로 잡으면 멀쩡한 문장을 잡는다.
# law/gate.py L005 와 같은 자리. 이것만은 soft 다: 문장은 사람이 고칠 수 있다.
단정어 = ("때문이다", "전망이다", "전망된다", "예상된다", "확실하다", "분명하다",
          "이 때문에", "덕분이다", "탓이다", "로 보인다", "할 것이다")


@dataclass
class Violation:
    rule: str
    severity: str          # hard · soft
    where: str
    msg: str

    def __str__(self) -> str:
        return f"[{self.rule}/{self.severity}] {self.where}: {self.msg}"


def check_facts(facts, led, src=None) -> list:
    """B001·B002·B004 -- 수 하나하나를 본다."""
    vs = []
    ids = {r.get("id") for r in led.줄}
    for f in facts:
        # B001 -- 근거가 없으면 그 수가 어디서 왔는지 아무도 모른다
        if not f.근거:
            vs.append(Violation("B001", "hard", f.이름,
                                "근거가 없다 -- 원장의 어느 줄에서 왔는지 알 수 없다"))
            continue
        # B002 -- 꼬리표는 붙었는데 가리키는 데가 없을 수 있다
        for rid, col in f.근거:
            if rid not in ids:
                vs.append(Violation("B002", "hard", f.이름,
                                    f"원장에 없는 줄을 가리킨다: {rid!r}"))
                continue
            r = led.찾기(rid)
            if col not in r:
                vs.append(Violation("B002", "hard", f.이름,
                                    f"{rid!r} 에 {col!r} 칸이 없다"))
        # B004 -- **다시 센다.** 꼬리표가 아니라 값을 본다.
        # 칸을 세로로 훑은 값(평균·중앙·최대…)도 같은 대접이다 -- 그 갈래가 빠져
        # 있으면 '범용' 으로 낸 수만 검사를 안 받게 되고, 그러면 새 출처를 붙일수록
        # 검사받지 않은 수가 는다.
        if f.규칙 in DV.ACROSS and f.인자:
            fn, _ = DV.ACROSS[f.규칙]
            v = DV.값들(led, f.인자[0])
            again = fn(v) if v else None
            if again is None:
                vs.append(Violation("B004", "hard", f.이름,
                                    f"관문은 이 값을 못 센다(그 칸에 수가 없다) -- "
                                    f"그런데 보고서에는 {f.값} 이 적혀 있다"))
            elif abs(float(again) - f.값) > TOL:
                vs.append(Violation("B004", "hard", f.이름,
                                    f"다시 세니 {float(again):.6f} 인데 보고서는 "
                                    f"{f.값:.6f} 다"))
            continue
        if f.규칙 and f.규칙 in DV.RULES and f.인자:
            r = led.찾기(f.인자[0])
            if r is None:
                continue
            cols, fn, scale, _ = DV.RULES[f.규칙]
            again = fn(r)
            if again is None:
                vs.append(Violation("B004", "hard", f.이름,
                                    f"관문은 이 값을 못 센다(분모 0 이거나 칸이 빔) -- "
                                    f"그런데 보고서에는 {f.값} 이 적혀 있다"))
            elif abs(again * scale - f.값) > TOL:
                vs.append(Violation("B004", "hard", f.이름,
                                    f"다시 세니 {again * scale:.6f} 인데 보고서는 "
                                    f"{f.값:.6f} 다"))
    return vs


def check_ledger(led, src=None) -> list:
    """B003 -- 원장이 낡았는가. **모르면 그것도 위반이다.**"""
    vs = []
    if not led.줄:
        vs.append(Violation("B003", "hard", led.출처 or "원장", "원장이 비어 있다"))
        return vs
    age = led.나이()
    limit = getattr(src, "신선", 3) if src else 3
    if age is None:
        vs.append(Violation("B003", "hard", led.출처,
                            "받은 날짜를 못 읽는다 -- 언제 것인지 모르는 원장은 못 쓴다"))
    elif age > limit:
        vs.append(Violation("B003", "hard", led.출처,
                            f"{age}일 낡았다 (이 출처의 신선도는 {limit}일)"))
    return vs


def check_prose(text: str, facts) -> list:
    """B005 -- 근거 없이 단정하는가. **soft 다.**

    수는 기계가 가르지만 문장은 못 가른다. 그래서 여기서는 **잡아서 보여 줄 뿐**
    기각하지 않는다 -- `law/gate.py` 가 L005 를 soft 로 둔 것과 같은 이유다.
    """
    vs = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        hit = [w for w in 단정어 if w in s]
        # 그 줄에 수가 하나라도 실려 있으면 근거를 댄 것으로 본다.
        has_num = any(str(round(f.값, 2)) in s or f.이름 in s for f in facts)
        if hit and not has_num:
            vs.append(Violation("B005", "soft", s[:40],
                                f"근거 없이 단정한다: {', '.join(hit)}"))
    return vs


AIM.update({
    "I001": "표본이 모자란 명제를 이례라고 하지 않아야 한다",
    "I002": "명제를 여러 개 세웠으면 그 수만큼 보정해야 한다",
    "I003": "명제의 근거가 원장에 실재해야 한다",
    "I004": "한 줄에 기대는 결론은 그렇다고 적어야 한다",
})


def check_claims(ms, led) -> list:
    """추론 층의 관문 I001~I004.

    수를 검사하는 관문(B00x)이 "이 값이 원장에서 왔는가" 를 보듯, 여기서는
    **"이 판정이 이 원장으로 가능한가"** 를 본다. 값은 맞는데 판정이 원장 크기를
    넘어서는 것 -- 그것이 시황이 늘 하는 일이고, 화면에서는 안 보인다.
    """
    vs = []
    ids = {r.get("id") for r in led.줄}
    m = len(ms)
    for c in ms:
        # I001 -- 못 잴 크기인데 이례라고 했는가
        if c.판정 == "이례":
            if c.n < INFER.MIN_N:
                vs.append(Violation("I001", "hard", c.말[:40],
                                    f"과거 표본이 {c.n}걸음뿐인데 이례라고 한다 "
                                    f"(최소 {INFER.MIN_N})"))
            elif min(1.0, m * INFER.최소p(c.n, c.이진)) >= INFER.ALPHA:
                vs.append(Violation("I001", "hard", c.말[:40],
                                    f"표본 {c.n}걸음 · 명제 {m}개로 도달 가능한 최소 p 는 "
                                    f"{min(1.0, m * INFER.최소p(c.n)):.3f} 라 "
                                    f"{INFER.ALPHA} 를 못 넘는다 -- 이례라고 할 수 없다"))
        # I002 -- 보정을 했는가
        if c.p is not None and c.p보정 is None:
            vs.append(Violation("I002", "hard", c.말[:40],
                                "단독 p 만 있고 보정 p 가 없다 -- 세운 개수만큼 "
                                "조이지 않으면 그중 하나는 반드시 놀랍다"))
        elif c.p is not None and c.p보정 is not None and c.p보정 + TOL < c.p:
            vs.append(Violation("I002", "hard", c.말[:40],
                                f"보정 p({c.p보정:.4f})가 단독 p({c.p:.4f})보다 작다 "
                                "-- 보정은 조이는 것이지 푸는 것이 아니다"))
        # I003 -- 근거가 실재하는가
        for rid, col in c.근거[:200]:
            if rid not in ids:
                vs.append(Violation("I003", "hard", c.말[:40],
                                    f"원장에 없는 줄을 가리킨다: {rid!r}"))
                break
        # I004 -- 한 줄에 기대는가 (soft)
        if c.판정 == "이례" and "약한 결론" in (c.뒤집기 or ""):
            vs.append(Violation("I004", "soft", c.말[:40],
                                "과거 한 걸음만 빼도 판정이 바뀐다"))
    return vs


def check(facts, led, src=None, prose: str = "", claims=None) -> list:
    return (check_ledger(led, src) + check_facts(facts, led, src)
            + check_prose(prose, facts)
            + (check_claims(claims, led) if claims else []))


def hard(vs) -> list:
    return [v for v in vs if v.severity == "hard"]


# 줄 하나가 아니라 **원장 전체**에 걸리는 관문. 이것이 걸리면 그 원장에서 나온 수는
# 하나도 성하지 않다.
LEDGER_RULES = ("B003",)


def 막힌것(vs, facts) -> set:
    """화면에서 빼야 할 수의 이름.

    **실측(검사가 잡았다):** 처음에는 위반의 `where` 만 모았다. 그런데 B003 의
    `where` 는 출처 이름("주식")이라 어느 수의 이름과도 안 맞았고, 그래서 **낡은
    원장인데 종가가 그대로 화면에 나왔다.** 관문은 걸렸다고 적으면서 수는 그대로
    보여 주는 꼴이었다 -- 읽는 사람은 수를 먼저 읽는다.
    """
    h = hard(vs)
    if any(v.rule in LEDGER_RULES for v in h):
        return {f.이름 for f in facts}
    return {v.where for v in h}


def report(vs) -> str:
    if not vs:
        return "관문 B001~B005: 위반 없음"
    lines = [f"관문 위반 {len(hard(vs))}건(hard) · {len(vs) - len(hard(vs))}건(soft)"]
    for v in vs:
        lines.append(f"  {v}")
    return "\n".join(lines)
