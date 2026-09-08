"""쟁점 -- **생성하지 않는다. 도출한다.**

`law/METHOD.md` 에 출처를 달아 정리한 절차를 그대로 옮긴 것이다. 요지 한 줄:

    쟁점은 사람이 "중요해 보인다" 고 고르는 것이 아니라,
    같은 요건표를 원고 쪽에서 한 번 · 피고 쪽에서 한 번 돌렸을 때 결론이 갈리는 자리다.

독일 사법연수생이 배우는 Relationstechnik 이 그렇게 한다(METHOD 1-4): Klägerstation 은
**원고의 진술만으로** 청구가 서는가(Schlüssigkeit)를 보고, Beklagtenstation 은 **피고의
진술까지 넣으면** 무너지는가(Erheblichkeit)를 본다. 두 결론이 갈리는 자리가 쟁점이다.
그러면 쟁점 도출은 판단이 아니라 **계산**이 된다.

그래서 이 파이프라인에서 LLM 이 하는 일은 쟁점 뽑기가 아니다:

    LLM 이 한다   조문에서 요건 뽑기 · 사실에서 당사자 주장 뽑기 · 요건별 포섭 서술
    코드가 한다   두 정거장 돌리기 · 쟁점 도출 · 결과 의존성 검사

앞의 것은 조문과 사실에 근거가 있어 대조 가능한 일이고(Chain of Logic·Holzenberger 가
LLM 이 할 수 있다고 보고한 종류다), 뒤의 것은 정의상 계산이다. "쟁점을 잘 뽑았는가" 가
취향 논쟁이 되지 않는 이유가 이 분업에 있다.

**결과 의존성이 쟁점의 자격 요건인 근거**(METHOD 2-3, 3-3): 미국 판례론에서 holding 은
"판결에 이르는(lead to the judgment)" 명제들이고, 한국 민사소송법 제216조는 기판력을
주문에 한정하며 상계 항변만 대항액 한도에서 예외로 둔다. 두 법계가 같은 말을 한다 --
**결론을 움직이지 않은 판단은 다르게 대우한다.** 뒤집기 검사가 그것이다.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# 갈래별 단계. METHOD.md 3-6 의 표 그대로다.
STAGES = {
    "민사": ("권리근거", "권리장애", "권리소멸", "권리저지"),
    "형사": ("구성요건", "위법성", "책임"),
    "헌법": ("적법요건", "보호영역", "제한", "정당화"),
}

# 단계가 정해지면 증명책임자도 정해진다 -- 법률요건분류설(METHOD 3-2)이 그렇게 말한다.
# "각 당사자는 자기에게 유리한 법규의 요건사실을 증명한다."
BURDEN = {
    ("민사", "권리근거"): "원고",
    ("민사", "권리장애"): "피고",
    ("민사", "권리소멸"): "피고",
    ("민사", "권리저지"): "피고",
    # 형사는 조각사유의 부존재까지 검사가 진다(무죄추정). 조각사유를 '주장' 하는 것은
    # 피고인이지만 증명책임은 넘어가지 않는다 -- 그래서 아래가 전부 검사다.
    ("형사", "구성요건"): "검사",
    ("형사", "위법성"): "검사",
    ("형사", "책임"): "검사",
    ("헌법", "적법요건"): "청구인",
    ("헌법", "보호영역"): "청구인",
    ("헌법", "제한"): "청구인",
    ("헌법", "정당화"): "국가",
}

# **원용해야만 판단하는 단계**(Einrede / 권리저지). 직권으로 보지 않는다(METHOD 1-2, 3-2).
INVOKED_ONLY = {("민사", "권리저지")}

# 당사자 이름. 갈래마다 청구하는 쪽과 다투는 쪽이 다르다.
SIDES = {"민사": ("원고", "피고"), "형사": ("검사", "피고인"), "헌법": ("청구인", "국가")}

# Savigny 의 네 canones + 후대의 목적론(METHOD 1-6). 닫힌 목록이라 기계가 검사한다.
CANONS = ("문언", "체계", "역사", "목적")


@dataclass
class Element:
    """요건요소 하나(Tatbestandsmerkmal). 조문에 걸려 있어야 한다."""
    id: str
    text: str
    stage: str
    statute: str = ""
    article: str = ""
    invoked: bool = False        # 권리저지(항변사항)를 실제로 원용했는가
    kind: str = "사실"           # 사실 | 법률
    canon: str = ""              # kind 가 '법률' 일 때 쓴 해석기법
    evidence: list = field(default_factory=list)   # kind 가 '사실' 일 때 증거방법
    defeats: str = ""            # 재항변: 이 요건이 서면 저 요건(id)이 무너진다
    source: str = ""             # 어디서 왔나 -- '소장 2쪽' · '가능한 항변' (사람이 볼 것)


@dataclass
class Case:
    """사건 하나. **주장은 당사자별로 따로 담는다** -- 그래야 두 정거장을 돌릴 수 있다."""
    domain: str
    claim: str                   # Obersatz: 누가 무엇을 누구에게 무슨 근거로
    elements: list
    positions: dict = field(default_factory=dict)   # elem_id -> {당사자: bool}

    def element(self, eid):
        return next((e for e in self.elements if e.id == eid), None)

    def sides(self):
        return SIDES.get(self.domain, ("원고", "피고"))


@dataclass
class Issue:
    """쟁점. 도출된 것이지 지어낸 것이 아니다."""
    element: str
    question: str
    stage: str
    burden: str
    positions: dict
    kind: str
    statute: str = ""
    article: str = ""

    def __str__(self):
        p = " vs ".join(f"{k}:{'O' if v else 'X'}" for k, v in self.positions.items())
        return f"[{self.stage}] {self.question} ({p} · 증명책임 {self.burden})"


# ---------------------------------------------------------------- 결론 계산

def outcome(case: Case, assign: dict) -> str:
    """요건 배정 하나에서 결론을 낸다. **순서 의존성이 여기 들어 있다.**

    앞 단계가 무너지면 뒤 단계는 보지 않는다(METHOD 1-3, 3-1, 3-5). 그래서 뒤 단계 쟁점이
    결론을 못 바꾸는 상황이 자동으로 생기고, 뒤집기 검사가 그것을 '쟁점 아님' 으로 걸러낸다
    -- 순서 규칙을 따로 적을 필요가 없다.
    """
    live = effective(case, assign)

    def vals(stage):
        return [live[e.id] for e in case.elements if e.stage == stage and not e.defeats]

    def invoked_true(stage):
        return [live[e.id] and e.invoked
                for e in case.elements if e.stage == stage and not e.defeats]

    if case.domain == "민사":
        if not all(vals("권리근거")):
            return "기각"
        if any(vals("권리장애")) or any(vals("권리소멸")):
            return "기각"
        if any(invoked_true("권리저지")):        # 원용해야만 본다
            return "기각"
        return "인용"

    if case.domain == "형사":
        if not all(vals("구성요건")):
            return "무죄"
        if any(vals("위법성")):                  # 위법성조각사유
            return "무죄"
        if any(vals("책임")):                    # 책임조각사유
            return "무죄"
        return "유죄"

    if case.domain == "헌법":
        if not all(vals("적법요건")):
            return "각하"
        if not all(vals("보호영역")) or not all(vals("제한")):
            return "합헌"
        return "합헌" if all(vals("정당화")) else "위헌"

    raise ValueError(f"모르는 갈래: {case.domain!r}")


def effective(case: Case, assign: dict) -> dict:
    """요건이 **서 있는가.** 인정되어도(True) 그것을 무너뜨리는 재항변이 서 있으면 없다.

    Relationstechnik 의 사슬이다: 청구원인 <- 항변(Einrede) <- 재항변(Replik) <-
    재재항변(Duplik). 예: 소멸시효 항변이 인정되어도 '채무 승인으로 중단' 재항변이
    인정되면 시효는 없는 것이고, 그 재항변도 '그 승인은 승인이 아니다' 로 다시 무너질
    수 있다. **받아치기가 한 번으로 끝나지 않는다.** 이 함수가 그 사슬을 따라간다.

    순환(서로가 서로를 무너뜨림)은 요건표가 틀린 것이다 -- J 관문이 막을 일이고,
    여기서는 끝없이 돌지 않도록 본 것을 기억한다.
    """
    by_target: dict = {}
    for e in case.elements:
        if e.defeats:
            by_target.setdefault(e.defeats, []).append(e)
    memo: dict = {}

    def alive(eid, seen=()):
        if eid in memo:
            return memo[eid]
        if eid in seen:
            return False
        if not assign.get(eid, False):
            memo[eid] = False
            return False
        for d in by_target.get(eid, []):
            if alive(d.id, seen + (eid,)):
                memo[eid] = False
                return False
        memo[eid] = True
        return True

    return {e.id: alive(e.id) for e in case.elements}


def burden_of(case: Case, e: Element) -> str:
    """증명책임자. 단계에서 따라 나오되, **재항변은 그 상대의 반대편**이다.

    법률요건분류설(METHOD 3-2): 각 당사자는 자기에게 유리한 법규의 요건사실을 증명한다.
    시효 항변은 피고에게 유리하니 피고가, 그것을 무너뜨리는 중단 사유는 원고에게
    유리하니 원고가 증명한다. 재재항변은 다시 뒤집힌다.
    """
    if e.defeats:
        target = case.element(e.defeats)
        if target is not None:
            a, b = case.sides()
            return b if burden_of(case, target) == a else a
    return BURDEN.get((case.domain, e.stage), "?")


def _assign(case: Case, prefer: list) -> dict:
    """당사자 우선순위대로 주장을 채운다. 아무도 주장 안 한 요건은 False.

    False 가 기본인 이유: 주장하지 않은 권리근거는 없는 것이고(변론주의 -- 주요사실의
    주장책임은 당사자에게 있다, METHOD 3-3), 주장하지 않은 항변·조각사유도 없는 것이다.
    """
    out = {}
    for e in case.elements:
        pos = case.positions.get(e.id, {})
        for party in prefer:
            if party in pos:
                out[e.id] = bool(pos[party])
                break
        else:
            out[e.id] = False
    return out


def stations(case: Case) -> dict:
    """Relationstechnik 의 두 정거장을 돌린다(METHOD 1-4).

    Klägerstation  -- 청구하는 쪽 진술만으로 결론이 무엇인가 (Schlüssigkeit)
    Beklagtenstation -- 다투는 쪽 진술을 얹으면 결론이 무엇인가 (Erheblichkeit)

    둘이 갈리면 그 사이에 쟁점이 있다. 안 갈리면 둘 중 하나다: 청구원인이 애초에
    불충분하거나(kl 이 이미 진다), 상대 주장이 결론을 못 바꾸거나.
    """
    claimant, respondent = case.sides()
    kl = outcome(case, _assign(case, [claimant]))
    bk = outcome(case, _assign(case, [respondent, claimant]))
    return {"claimant": claimant, "respondent": respondent,
            "klaeger": kl, "beklagten": bk, "split": kl != bk}


# ---------------------------------------------------------------- 쟁점 도출

def contested(case: Case) -> list:
    """양측이 반대로 말한 요건. 한쪽만 말한 것은 다툼이 아니다."""
    out = []
    for e in case.elements:
        pos = case.positions.get(e.id, {})
        if len(pos) >= 2 and len(set(bool(v) for v in pos.values())) > 1:
            out.append(e)
    return out


def flips_outcome(case: Case, target: Element, others: list, cap: int = 14) -> bool:
    """이 요건의 답이 갈릴 때 결론이 갈리는 경우가 **하나라도** 있는가.

    다른 다툼들의 결말은 아직 모르므로 전부 훑는다. 하나라도 뒤집히면 이 요건은 결론에
    닿아 있다 -- Abramowicz & Stearns 의 holding 정의("lead to the judgment")를 검사
    가능한 형태로 옮긴 것이다(METHOD 2-3). 하나도 없으면 방론이다.

    others 가 많으면 2^n 이 커지므로 cap 에서 자른다. 자른 경우 남는 것은 '뒤집는 경우를
    못 찾았다' 이지 '없다' 가 아니므로, 그때는 True(쟁점으로 남김)로 답한다 -- **과잉
    기각하는 심판은 맞는 답도 버린다**(novel/gate.py 가 배운 것).
    """
    base = _assign(case, list(case.sides()))
    others = [e for e in others if e.id != target.id]
    if len(others) > cap:
        return True
    for combo in itertools.product([False, True], repeat=len(others)):
        assign = dict(base)
        for e, v in zip(others, combo):
            assign[e.id] = v
        assign[target.id] = False
        no = outcome(case, assign)
        assign[target.id] = True
        yes = outcome(case, assign)
        if no != yes:
            return True
    return False


def derive(case: Case) -> list:
    """쟁점 목록. **이 함수가 이 파일의 존재 이유다.**

    조건 둘을 다 넘겨야 쟁점이다:
      (1) 다투어지고 있다        -- 한쪽 주장만 있는 것은 설명이지 쟁점이 아니다
      (2) 결론에 닿아 있다        -- 답이 갈릴 때 결론이 갈리는 경우가 있다

    (1)은 미국 AI&Law 의 factor 대립 구조(METHOD 2-4), (2)는 holding 기준(2-3)과 민사소송법
    제216조의 태도(3-3)에서 왔다.
    """
    cs = contested(case)
    out = []
    for e in cs:
        if not flips_outcome(case, e, cs):
            continue
        out.append(Issue(
            element=e.id,
            question=f"{e.text}이(가) 인정되는가",
            stage=e.stage,
            burden=burden_of(case, e),
            positions={k: bool(v) for k, v in case.positions.get(e.id, {}).items()},
            kind=e.kind, statute=e.statute, article=e.article))
    return out


def moot(case: Case) -> list:
    """다투어지고는 있으나 결론을 못 바꾸는 요건. 방론이다 -- 보고는 한다."""
    cs = contested(case)
    return [e for e in cs if not flips_outcome(case, e, cs)]


# ---------------------------------------------------------------- 유·불리

def advantage(case: Case, cap: int = 14) -> dict:
    """**더 유리한 쪽.** 취향이 아니라 증명책임에서 계산한다.

    다투어지는 요건은 증거가 없으면(non liquet) 증명책임자가 진다(METHOD 3-2). 그러니
    "아무것도 증명되지 않았을 때의 결론" 이 곧 출발선이고, 거기서 지는 쪽이 무엇을
    증명해야 뒤집히는가가 곧 그 쪽의 부담이다. 그래서 세 가지를 낸다:

        출발선   -- 다툼 있는 요건을 전부 '증명 안 됨' 으로 놓았을 때의 결론
        부담     -- 쟁점마다 누가 증명해야 하는가
        최소승리 -- 각 쪽이 이기려면 최소 어느 쟁점들을 이겨야 하는가

    최소승리가 작은 쪽이 유리하다. 하나만 이기면 되는 쪽과 셋을 다 이겨야 하는 쪽은
    같은 자리에 서 있지 않다.
    """
    claimant, respondent = case.sides()
    base = _assign(case, [claimant, respondent])
    issues = derive(case)
    ids = [i.element for i in issues]
    for i in ids:
        base[i] = False                          # 증명 안 됨
    start = outcome(case, base)
    wins = {claimant: "인용", respondent: "기각"} if case.domain == "민사" else \
           {claimant: "유죄", respondent: "무죄"} if case.domain == "형사" else \
           {claimant: "위헌", respondent: "합헌"}

    def minimal(side):
        """이 쪽이 이기는 가장 작은 쟁점 조합들. 자기 부담인 쟁점을 이기는 것으로 센다."""
        mine = [i for i in issues if i.burden == side]
        if outcome(case, base) == wins[side]:
            return [[]]
        if len(mine) > cap:
            return None
        best = []
        for r in range(1, len(mine) + 1):
            for combo in itertools.combinations(mine, r):
                a = dict(base)
                for i in combo:
                    a[i.element] = True
                if outcome(case, a) == wins[side]:
                    best.append([i.element for i in combo])
            if best:
                break
        return best

    def minimal_given(side, won: str):
        """상대가 쟁점 `won` 을 이겼다고 치면 이 쪽은 최소 무엇을 이겨야 하는가.

        출발선의 최소승리는 "아무것도 증명 안 됐을 때" 라서, 날짜만으로 거의 서는
        항변(시효)도 '증명 안 됨' 으로 놓인다. 받아치기는 그 뒤에 있다 -- 상대가
        가장 센 것을 세웠을 때 무엇으로 받는가. 그래서 상대 쟁점마다 한 번씩 센다.
        """
        mine = [i for i in issues if i.burden == side]
        given = dict(base)
        given[won] = True
        if outcome(case, given) == wins[side]:
            return [[]]
        if len(mine) > cap:
            return None
        best = []
        for r in range(1, len(mine) + 1):
            for combo in itertools.combinations(mine, r):
                a = dict(given)
                for i in combo:
                    a[i.element] = True
                if outcome(case, a) == wins[side]:
                    best.append([i.element for i in combo])
            if best:
                break
        return best

    받아치기 = {}
    for side in (claimant, respondent):
        other = respondent if side == claimant else claimant
        받아치기[side] = {i.element: minimal_given(side, i.element)
                       for i in issues if i.burden == other}

    return {"출발선": start,
            "출발선에서 이기는 쪽": next((s for s, w in wins.items() if w == start), "?"),
            "부담": {i.element: i.burden for i in issues},
            "최소승리": {claimant: minimal(claimant), respondent: minimal(respondent)},
            "받아치기": 받아치기}


# ---------------------------------------------------------------- 입출력

def load(path) -> Case:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    els = [Element(**e) for e in d.get("elements", [])]
    return Case(domain=d["domain"], claim=d.get("claim", ""), elements=els,
                positions=d.get("positions", {}))


def dump(case: Case) -> str:
    return json.dumps(asdict(case), ensure_ascii=False, indent=1)


def report(case: Case) -> str:
    st = stations(case)
    lines = [f"[{case.domain}] {case.claim}",
             f"  Klägerstation({st['claimant']} 진술만): {st['klaeger']}",
             f"  Beklagtenstation(+{st['respondent']} 진술): {st['beklagten']}",
             f"  두 정거장이 갈리는가: {'예' if st['split'] else '아니오'}"]
    issues = derive(case)
    lines.append(f"\n쟁점 {len(issues)}개")
    for i, iss in enumerate(issues, 1):
        lines.append(f"  {i}. {iss}")
    mt = moot(case)
    if mt:
        lines.append(f"\n다투나 결론을 못 바꾸는 것 {len(mt)}개 (방론)")
        for e in mt:
            lines.append(f"  - [{e.stage}] {e.text}")
    adv = advantage(case)
    lines.append(f"\n유·불리 (증명책임에서 계산)")
    lines.append(f"  아무것도 증명 안 되면: {adv['출발선']} -> 유리한 쪽: **{adv['출발선에서 이기는 쪽']}**")

    def 조합(sets):
        if sets is None:
            return "쟁점이 너무 많아 못 셌다"
        if sets == [[]]:
            return "아무것도 더 증명 안 해도 이긴다"
        if not sets:
            return "**받아칠 것이 없다** -- 이것을 무너뜨릴 재항변이 요건표에 없다"
        return " 또는 ".join("+".join(s) for s in sets[:4])

    for side, sets in adv["최소승리"].items():
        lines.append(f"  {side}가 이기려면 최소: {조합(sets)}")
    lines.append(f"\n받아치기 (상대가 그 쟁점을 세우면 최소 무엇으로 받는가 -- 요건 id 로)")
    for side, table in adv["받아치기"].items():
        for won, sets in table.items():
            lines.append(f"  {side} <- 상대가 [{won}]: {조합(sets)}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="쟁점 도출 -- 요건과 주장에서 계산한다")
    ap.add_argument("case", help="사건 JSON 경로")
    args = ap.parse_args()
    print(report(load(args.case)))
