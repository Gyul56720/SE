"""쟁점이 **도출되는가**, 그리고 관문 J001~J010 이 실제로 걸리는가.

핵심 주장 하나를 검사로 고정한다: **쟁점은 판단이 아니라 계산이다.** 요건표와 양측 주장만
주면 어느 것이 쟁점이고 어느 것이 방론인지가 정해진다(law/METHOD.md 1-4, 2-3, 3-3).

    python3 tests/test_law_issue.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import issue as IS                                           # noqa: E402
from law import issuegate as JG                                       # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)
EMPTY = CP.Corpus()

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def E(eid, text, stage, **kw):
    kw.setdefault("statute", "가상시험법")
    kw.setdefault("article", "7")
    kw.setdefault("evidence", ["서증"])
    return IS.Element(id=eid, text=text, stage=stage, **kw)


def 대여금(시효원용=True, 교부주장=True):
    """대여금 청구 -- 요건 넷에 다툼 셋. 실제 요건사실 배치를 본뜬 모양."""
    els = [
        E("합의", "소비대차 합의", "권리근거"),
        E("교부", "금전의 교부", "권리근거"),
        E("변제", "변제", "권리소멸", article="7의2"),
        E("시효", "소멸시효 완성", "권리저지", article="12", invoked=시효원용),
    ]
    pos = {
        "합의": {"원고": True, "피고": False},
        "교부": {"원고": 교부주장, "피고": True} if 교부주장 else {"피고": True},
        "변제": {"원고": False, "피고": True},
        "시효": {"원고": False, "피고": True},
    }
    return IS.Case(domain="민사", claim="원고가 피고에게 대여금 반환을 구한다",
                   elements=els, positions=pos)


print("[정거장] Relationstechnik -- 원고 쪽 한 번, 피고 쪽 한 번")
c = 대여금()
st = IS.stations(c)
ok(st["klaeger"] == "인용", f"원고 진술만으로는 인용 (얻은 값 {st['klaeger']})")
ok(st["beklagten"] == "기각", f"피고 진술을 넣으면 기각 (얻은 값 {st['beklagten']})")
ok(st["split"], "두 정거장이 갈린다 -- 그 사이에 쟁점이 있다")

print()
print("[도출] 쟁점은 고르는 것이 아니라 계산된다")
issues = IS.derive(c)
ok({i.element for i in issues} == {"합의", "변제", "시효"},
   f"다투고 결론을 바꾸는 셋이 쟁점 (얻은 값 {sorted(i.element for i in issues)})")
ok(all(i.element != "교부" for i in issues),
   "양측이 같은 값을 말한 '교부' 는 쟁점이 아니다 -- 다툼이 없다")
ok([i.burden for i in issues if i.element == "합의"] == ["원고"],
   "권리근거의 증명책임은 원고 (단계에서 따라 나온다)")
ok([i.burden for i in issues if i.element == "변제"] == ["피고"],
   "권리소멸의 증명책임은 피고")

print()
print("[원용] 원용하지 않은 항변은 쟁점이 되지 못한다 (Einrede / 권리저지)")
c2 = 대여금(시효원용=False)
ids = {i.element for i in IS.derive(c2)}
ok("시효" not in ids, f"원용 없는 소멸시효는 도출되지 않는다 (얻은 값 {sorted(ids)})")
ok(any(e.id == "시효" for e in IS.moot(c2)),
   "다투고는 있으나 결론을 못 바꾼다 -- 방론으로 보고된다")
bad = [IS.Issue(element="시효", question="시효?", stage="권리저지", burden="피고",
                positions={"원고": False, "피고": True}, kind="사실")]
vs = JG.check_invocation(c2, bad)
ok(any(v.rule == "J006" for v in vs), "그래도 쟁점표에 넣으면 J006 이 잡는다")

print()
print("[J007] 청구원인이 애초에 불충분하면 쟁점 이전 문제다 (Klägerstation)")
c3 = 대여금(교부주장=False)
vs = JG.check_schluessig(c3)
ok(any(v.rule == "J007" and "교부" in v.detail for v in vs),
   f"원고가 '금전의 교부' 를 주장하지 않았다 -> hard (얻은 값 {[v.detail for v in vs]})")
ok(not JG.check_schluessig(c), "주장이 갖춰진 사건은 J007 이 걸리지 않는다")

print()
print("[J005] 답이 갈려도 결론이 안 바뀌면 쟁점이 아니다 -- 순서 의존성이 여기서 나온다")
헌법 = IS.Case(
    domain="헌법", claim="청구인이 법률조항의 위헌확인을 구한다",
    elements=[E("직접성", "기본권 침해의 직접성", "적법요건", article="3"),
              E("최소성", "침해의 최소성", "정당화", article="12")],
    positions={"직접성": {"청구인": True, "국가": False},
               "최소성": {"청구인": False, "국가": True}})
ids = {i.element for i in IS.derive(헌법)}
ok(ids == {"직접성", "최소성"}, f"적법요건과 본안이 둘 다 쟁점 (얻은 값 {sorted(ids)})")

각하 = IS.Case(
    domain="헌법", claim="같은 사건, 다만 직접성에 다툼이 없다",
    elements=헌법.elements,
    positions={"직접성": {"청구인": False, "국가": False},
               "최소성": {"청구인": False, "국가": True}})
ids = {i.element for i in IS.derive(각하)}
ok(ids == set(),
   f"적법요건이 확정적으로 깨지면 본안 쟁점은 논할 자리가 없다 (얻은 값 {sorted(ids)})")
vs = JG.check_outcome_relevance(각하, [IS.Issue(
    element="최소성", question="최소성?", stage="정당화", burden="국가",
    positions={"청구인": False, "국가": True}, kind="법률")])
ok(any(v.rule == "J005" for v in vs), "그래도 세우면 J005 가 '방론이다' 로 잡는다")

print()
print("[J001~J003] 조문 · 단계 · 증명책임")
vs, checked, unver = JG.check_anchor(c, CORPUS)
ok(not vs and checked == 4, f"원장에 있는 조문 넷 -> 통과 (검증 {checked}건)")
vs, checked, unver = JG.check_anchor(c, EMPTY)
ok(not vs and unver == 4 and checked == 0,
   "원장이 비면 기각이 아니라 미검증 4건")
없는조문 = IS.Case(domain="민사", claim="x",
                elements=[E("합의", "합의", "권리근거", article="99")], positions={})
vs, _, _ = JG.check_anchor(없는조문, CORPUS)
ok(any(v.rule == "J001" for v in vs), "원장에 없는 제99조 -> hard")
조문없음 = IS.Case(domain="민사", claim="x",
                elements=[IS.Element("합의", "합의", "권리근거")], positions={})
vs, _, _ = JG.check_anchor(조문없음, CORPUS)
ok(any("근거 조문이 없다" in v.detail for v in vs), "조문 없는 요건 -> hard")

틀린단계 = IS.Case(domain="민사", claim="x",
                elements=[E("x", "x", "위법성")], positions={})
ok(any(v.rule == "J002" for v in JG.check_stage(틀린단계, [])),
   "민사에 '위법성' 단계는 없다 -> hard")

틀린책임 = [IS.Issue(element="합의", question="q", stage="권리근거", burden="피고",
                  positions={"원고": True, "피고": False}, kind="사실")]
ok(any(v.rule == "J003" for v in JG.check_burden(c, 틀린책임)),
   "권리근거인데 증명책임을 피고로 적었다 -> hard")

print()
print("[J004 · J008 · J009] 대립 · 해석기법 · 중복")
한쪽만 = [IS.Issue(element="합의", question="q", stage="권리근거", burden="원고",
                positions={"원고": True}, kind="사실")]
ok(any(v.rule == "J004" for v in JG.check_opposition(c, 한쪽만)),
   "주장이 한쪽뿐이면 쟁점이 아니라 설명이다 -> hard")

법률쟁점 = IS.Case(domain="민사", claim="x",
                elements=[E("해석", "조항의 의미", "권리근거", kind="법률",
                            canon="목적론적확장")], positions={})
iss = [IS.Issue(element="해석", question="q", stage="권리근거", burden="원고",
                positions={"원고": True, "피고": False}, kind="법률")]
ok(any(v.rule == "J008" and v.severity == "hard"
       for v in JG.check_method(법률쟁점, iss)),
   "Savigny 의 닫힌 목록에 없는 해석기법 -> hard")
법률쟁점.elements[0].canon = "문언"
ok(not JG.check_method(법률쟁점, iss), "'문언' 은 목록에 있다 -> 통과")

증거없음 = IS.Case(domain="민사", claim="x",
                elements=[E("합의", "합의", "권리근거", evidence=[])], positions={})
iss = [IS.Issue(element="합의", question="q", stage="권리근거", burden="원고",
                positions={"원고": True, "피고": False}, kind="사실")]
ok([v.severity for v in JG.check_method(증거없음, iss)] == ["soft"],
   "사실쟁점에 증거방법이 없으면 soft -- 증거는 뒤에 붙는다")

중복 = 틀린책임 * 2
ok(any(v.rule == "J009" for v in JG.check_duplicate(c, 중복)), "같은 요건 두 번 -> hard")

print()
print("[J010] 쟁점표가 도출 결과와 다르면 그 차이가 오류다")
빠뜨림 = [i for i in IS.derive(c) if i.element != "변제"]
vs = JG.check_derivation(c, 빠뜨림)
ok(any(v.rule == "J010" and "없다" in v.detail for v in vs),
   "도출되는데 빠뜨린 쟁점 -> hard")
군더더기 = IS.derive(c) + [IS.Issue(element="교부", question="q", stage="권리근거",
                                 burden="원고", positions={"원고": True, "피고": True},
                                 kind="사실")]
vs = JG.check_derivation(c, 군더더기)
ok(any(v.rule == "J010" and "도출되지 않는" in v.detail for v in vs),
   "도출 안 되는데 세운 쟁점 -> hard")
ok(not JG.check_derivation(c, IS.derive(c)), "도출 결과 그대로면 통과")

print()
print("[통합] 멀쩡한 사건은 관문 전체를 통과한다")
vs, checked, unver = JG.check(c, corpus=CORPUS)
hard = [v for v in vs if v.severity == "hard"]
ok(not hard, f"hard 0건 (얻은 값 {[str(v) for v in hard]})")
ok("쟁점 3개" in IS.report(c), "보고서가 쟁점 수를 적는다")

print()
print("[재항변] **받아치기는 한 번으로 끝나지 않는다** -- Einrede <- Replik <- Duplik")
_사슬 = IS.Case(domain="민사", claim="원고가 피고에게 대금을 구한다", elements=[
    IS.Element("합의", "합의", "권리근거", "가상시험법", "7"),
    IS.Element("시효", "소멸시효 완성", "권리저지", "가상시험법", "12", invoked=True),
    IS.Element("승인", "채무 승인으로 중단", "권리저지", "가상시험법", "12", defeats="시효"),
    IS.Element("승인아님", "그 말은 승인이 아니다", "권리저지", "가상시험법", "12", defeats="승인"),
], positions={"합의": {"원고": True, "피고": True}, "시효": {"원고": False, "피고": True},
              "승인": {"원고": True, "피고": False}, "승인아님": {"원고": False, "피고": True}})
_a = {"합의": True, "시효": True, "승인": False, "승인아님": False}
ok(IS.outcome(_사슬, _a) == "기각", "항변만 서면 기각")
_a["승인"] = True
ok(IS.outcome(_사슬, _a) == "인용", "재항변이 서면 항변이 무너져 인용")
_a["승인아님"] = True
ok(IS.outcome(_사슬, _a) == "기각", "재재항변이 서면 재항변이 무너져 다시 기각")
ok(IS.burden_of(_사슬, _사슬.element("승인")) == "원고"
   and IS.burden_of(_사슬, _사슬.element("승인아님")) == "피고",
   "증명책임이 사슬을 따라 뒤집힌다 -- 항변은 피고, 재항변은 원고, 재재항변은 피고")
_vs, _, _ = JG.check(_사슬, corpus=CORPUS)
ok(not [v for v in _vs if v.rule in ("J003", "J006")],
   f"J003·J006 이 재항변을 잘못 잡지 않는다 (얻은 값 {[str(v) for v in _vs if v.rule in ('J003', 'J006')]})")

# J011: 허공을 치는 재항변과 도는 사슬은 요건표가 틀린 것이다.
_허공 = IS.Case(domain="민사", claim="x", elements=[
    IS.Element("합의", "합의", "권리근거", "가상시험법", "7"),
    IS.Element("재", "재항변", "권리저지", "가상시험법", "12", defeats="없는요건")],
    positions={"합의": {"원고": True, "피고": True}})
ok(any(v.rule == "J011" for v in JG.check_chain(_허공)), "과녁이 없는 재항변을 잡는다 (J011)")
_순환 = IS.Case(domain="민사", claim="x", elements=[
    IS.Element("A", "A", "권리저지", "가상시험법", "12", defeats="B"),
    IS.Element("B", "B", "권리저지", "가상시험법", "12", defeats="A")], positions={})
ok(any("돈다" in v.detail for v in JG.check_chain(_순환)), "서로를 무너뜨리는 사슬을 잡는다 (J011)")
ok(IS.outcome(_순환, {"A": True, "B": True}) in ("인용", "기각"),
   "도는 사슬이어도 끝없이 돌지 않는다")

print()
print("[유·불리] **취향이 아니라 증명책임에서 계산한다**")
_adv = IS.advantage(_사슬)
ok(_adv["출발선"] == "인용" and _adv["출발선에서 이기는 쪽"] == "원고",
   f"아무것도 증명 안 되면 항변의 증명책임자(피고)가 진다 (얻은 값 {_adv['출발선']})")
ok(_adv["최소승리"]["피고"] == [["시효"]],
   f"피고가 이기려면 최소 시효 하나 (얻은 값 {_adv['최소승리']['피고']})")
ok(_adv["받아치기"]["원고"]["시효"] == [["승인"]],
   f"피고가 시효를 세우면 원고는 승인으로 받는다 (얻은 값 {_adv['받아치기']['원고']['시효']})")
ok(_adv["받아치기"]["피고"]["승인"] == [["시효", "승인아님"]],
   f"원고가 승인을 세우면 피고는 시효+승인아님으로 받는다 (얻은 값 {_adv['받아치기']['피고']['승인']})")
_막힘 = IS.Case(domain="민사", claim="x", elements=[
    IS.Element("합의", "합의", "권리근거", "가상시험법", "7"),
    IS.Element("무효", "무효", "권리장애", "가상시험법", "7")],
    positions={"합의": {"원고": True, "피고": True}, "무효": {"원고": False, "피고": True}})
ok(IS.advantage(_막힘)["받아치기"]["원고"]["무효"] == [],
   "재항변이 없는 항변은 '받아칠 것이 없다' 로 나온다 -- 요건표를 더 세우라는 신호다")

print()
if fails:
    print(f"쟁점: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("쟁점 도출과 관문 J001~J011: 정거장 · 뒤집기 · 원용 · 순서 의존 · 재항변 · 유불리 -- RED/GREEN 통과")
