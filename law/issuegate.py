"""쟁점의 기계 관문 J001~J010 -- LLM 을 쓰지 않는다.

`law/gate.py` 가 완성된 문서를 보는 심판이라면, 이 파일은 **쟁점표**를 보는 심판이다.
판정 기준은 전부 `law/METHOD.md` 에 출처가 달려 있다. 여기서 새로 지어낸 규칙은 없다.

    J001  요건이 조문에 걸려 있는가            원장 필요   hard
    J002  단계가 그 갈래의 단계표에 있는가                 hard
    J003  증명책임이 단계에서 따라 나오는 것과 같은가       hard
    J004  양측 주장이 있고 서로 반대인가                   hard
    J005  답이 갈릴 때 결론이 갈리는가 (뒤집기 검사)        hard
    J006  원용해야 하는 항변을 원용 없이 세웠는가           hard
    J007  청구원인이 애초에 충분한가 (Klägerstation)        hard
    J008  법률쟁점의 해석기법이 닫힌 목록에 있는가          hard / 증거방법 없음 soft
    J009  같은 요건에 쟁점을 두 번 세웠는가                 hard
    J010  사람/LLM 이 낸 쟁점표가 도출 결과와 같은가        hard
    J011  재항변의 과녁이 실재하고 사슬이 돌지 않는가       hard

J005 가 이 파일의 심장이다. "중요해 보이는가" 는 취향이지만 "답이 갈릴 때 결론이 갈리는가"
는 계산이다. 미국 판례론의 holding 정의와 한국 민사소송법 제216조가 같은 자리를 짚는다
(METHOD 2-3, 3-3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import issue as IS                                           # noqa: E402
from law.gate import Violation, verdict                               # noqa: E402


def check_anchor(case, corpus) -> tuple:
    """J001 -- 요건이 실재하는 조문에 걸려 있는가.

    조문 없는 요건은 요건이 아니다. Gutachtenstil 의 Obersatz 가 근거 조문을 요구하는 것과
    같다(METHOD 1-1). 원장이 그 법령을 안 담고 있으면 기각이 아니라 미검증이다.
    """
    out, checked, unverified = [], 0, 0
    for e in case.elements:
        if not e.statute or not e.article:
            out.append(Violation("J001", "hard", f"요건 {e.id}",
                                 f"근거 조문이 없다 ({e.text!r})"))
            continue
        if not corpus.covers(e.statute):
            unverified += 1
            continue
        checked += 1
        if not corpus.has(e.statute, e.article):
            out.append(Violation("J001", "hard", f"요건 {e.id}",
                                 f"{e.statute} 에 제{e.article}조가 없다 (원장 대조)"))
    return out, checked, unverified


def check_stage(case, issues) -> list:
    """J002 -- 단계가 그 갈래의 단계표에 있는가 (METHOD 3-6)."""
    allowed = IS.STAGES.get(case.domain, ())
    out = []
    for e in case.elements:
        if e.stage not in allowed:
            out.append(Violation("J002", "hard", f"요건 {e.id}",
                                 f"{case.domain} 에 없는 단계 {e.stage!r} "
                                 f"(가능: {'/'.join(allowed)})"))
    return out


def check_burden(case, issues) -> list:
    """J003 -- 증명책임은 단계에서 따라 나온다. 어긋나면 배분을 틀린 것이다.

    법률요건분류설(METHOD 3-2): 각 당사자는 자기에게 유리한 법규의 요건사실을 증명한다.
    그래서 증명책임은 쟁점마다 사람이 정하는 것이 아니라 단계가 정한다.
    """
    out = []
    for iss in issues:
        e = next((x for x in case.elements if x.id == iss.element), None)
        # 재항변은 그 상대의 반대편이 증명한다 -- 단계표가 아니라 사슬이 정한다.
        want = IS.burden_of(case, e) if e is not None else \
            IS.BURDEN.get((case.domain, iss.stage))
        if want and iss.burden != want:
            out.append(Violation("J003", "hard", f"쟁점 {iss.element}",
                                 f"{iss.stage} 단계의 증명책임은 {want} 인데 "
                                 f"{iss.burden} 로 적었다"))
    return out


def check_opposition(case, issues) -> list:
    """J004 -- 한쪽 주장만 있는 것은 쟁점이 아니라 설명이다 (METHOD 2-4)."""
    out = []
    for iss in issues:
        vals = set(bool(v) for v in iss.positions.values())
        if len(iss.positions) < 2:
            out.append(Violation("J004", "hard", f"쟁점 {iss.element}",
                                 f"주장이 한쪽뿐이다 ({iss.positions})"))
        elif len(vals) < 2:
            out.append(Violation("J004", "hard", f"쟁점 {iss.element}",
                                 "양측이 같은 값을 말한다 -- 다툼이 없다"))
    return out


def check_outcome_relevance(case, issues) -> list:
    """J005 -- 답이 갈려도 결론이 같으면 쟁점이 아니다. 뒤집기 검사.

    Abramowicz & Stearns 의 holding("lead to the judgment", METHOD 2-3)과 민사소송법
    제216조(기판력은 주문에 한하고 상계 항변만 대항액 한도 예외, METHOD 3-3)가 같은 자리를
    짚는다. 앞 단계가 이미 무너져 뒤 단계가 무의미해진 경우도 여기서 같이 걸린다.
    """
    cs = IS.contested(case)
    out = []
    for iss in issues:
        e = next((x for x in case.elements if x.id == iss.element), None)
        if e is None:
            out.append(Violation("J005", "hard", f"쟁점 {iss.element}",
                                 "요건 목록에 없는 요건을 쟁점으로 세웠다"))
            continue
        if not IS.flips_outcome(case, e, cs or [e]):
            out.append(Violation("J005", "hard", f"쟁점 {iss.element}",
                                 f"답이 갈려도 결론이 안 바뀐다 ({e.stage}) -- 방론이다"))
    return out


def check_invocation(case, issues) -> list:
    """J006 -- 원용해야만 판단하는 항변(Einrede/권리저지)을 원용 없이 세웠는가.

    METHOD 1-2·3-2: 권리저지 사유는 직권으로 고려되지 않고 의무자가 원용해야 한다.
    소멸시효 항변을 아무도 안 걸었는데 쟁점으로 세우면 그건 절차적으로 틀린 쟁점이다.
    """
    out = []
    for iss in issues:
        if (case.domain, iss.stage) not in IS.INVOKED_ONLY:
            continue
        e = next((x for x in case.elements if x.id == iss.element), None)
        if e is not None and e.defeats:
            continue                     # 재항변은 항변이 아니다 -- 원용 표시는 항변에 붙는다
        if e is not None and not e.invoked:
            out.append(Violation("J006", "hard", f"쟁점 {iss.element}",
                                 f"{iss.stage} 는 원용해야 판단하는데 원용 표시가 없다"))
    return out


def check_schluessig(case, issues=None) -> list:
    """J007 -- 청구원인이 애초에 충분한가 (Klägerstation, METHOD 1-4).

    청구하는 쪽 진술만으로도 이미 지는 사건이면, 쟁점을 논하기 전에 **주장 자체가
    불충분**하다. 이때 쟁점표를 아무리 잘 만들어도 소용이 없다.
    """
    st = IS.stations(case)
    losing = {"민사": "기각", "형사": "무죄", "헌법": ("각하", "합헌")}[case.domain]
    lost = st["klaeger"] in (losing if isinstance(losing, tuple) else (losing,))
    if not lost:
        return []
    missing = [e.text for e in case.elements
               if IS.BURDEN.get((case.domain, e.stage)) == st["claimant"]
               and not case.positions.get(e.id, {}).get(st["claimant"], False)]
    return [Violation("J007", "hard", "사건",
                      f"{st['claimant']} 진술만으로 이미 '{st['klaeger']}' 다 "
                      f"(주장 없는 요건: {', '.join(missing) or '없음'})")]


def check_method(case, issues) -> list:
    """J008 -- 법률쟁점은 해석기법이, 사실쟁점은 증거방법이 있어야 한다.

    해석기법은 Savigny 의 네 canones + 후대 목적론으로 **닫아 둔다**(METHOD 1-6). 닫힌
    목록이라야 기계가 볼 수 있고, 임의로 이름 붙인 기법이 늘어나는 것을 막는다.
    증거방법 쪽은 soft 다 -- 증거는 뒤에 붙는 일이 흔해서 기각할 일이 아니다.
    """
    out = []
    for iss in issues:
        e = next((x for x in case.elements if x.id == iss.element), None)
        if e is None:
            continue
        if e.kind == "법률":
            if e.canon not in IS.CANONS:
                out.append(Violation("J008", "hard", f"쟁점 {iss.element}",
                                     f"해석기법 {e.canon!r} 가 목록에 없다 "
                                     f"({'/'.join(IS.CANONS)})"))
        elif e.kind == "사실":
            if not e.evidence:
                out.append(Violation("J008", "soft", f"쟁점 {iss.element}",
                                     "사실쟁점인데 증거방법이 비어 있다"))
        else:
            out.append(Violation("J008", "hard", f"쟁점 {iss.element}",
                                 f"쟁점 종류가 '사실'/'법률' 이 아니다: {e.kind!r}"))
    return out


def check_duplicate(case, issues) -> list:
    """J009 -- 같은 요건에 쟁점을 두 번 세웠는가."""
    seen, out = set(), []
    for iss in issues:
        if iss.element in seen:
            out.append(Violation("J009", "hard", f"쟁점 {iss.element}",
                                 "같은 요건에 쟁점이 두 번 있다"))
        seen.add(iss.element)
    return out


def check_derivation(case, issues) -> list:
    """J010 -- 사람이나 LLM 이 낸 쟁점표가 **도출 결과와 같은가.**

    이 파이프라인에서 쟁점은 생성물이 아니라 도출물이다(law/issue.py). 그러므로 누가
    쟁점표를 내밀든, 요건과 주장에서 계산한 것과 달라지면 그 차이가 곧 오류다.
    빠뜨린 쟁점과 없는 쟁점을 둘 다 짚는다.
    """
    derived = {i.element for i in IS.derive(case)}
    given = {i.element for i in issues}
    out = []
    for eid in sorted(derived - given):
        out.append(Violation("J010", "hard", f"요건 {eid}",
                             "도출되는 쟁점인데 쟁점표에 없다"))
    for eid in sorted(given - derived):
        out.append(Violation("J010", "hard", f"쟁점 {eid}",
                             "도출되지 않는 것을 쟁점으로 세웠다"))
    return out


def check_chain(case, issues=None) -> list:
    """J011 -- 재항변의 과녁이 실재하고, 사슬이 돌지 않는가.

    `defeats` 가 없는 id 를 가리키면 그 재항변은 허공을 치는 것이고, A 가 B 를, B 가 A 를
    무너뜨리면 결론이 정해지지 않는다. 둘 다 요건표가 틀린 것이다.
    """
    out = []
    ids = {e.id for e in case.elements}
    for e in case.elements:
        if not e.defeats:
            continue
        if e.defeats not in ids:
            out.append(Violation("J011", "hard", f"요건 {e.id}",
                                 f"무너뜨린다는 요건 {e.defeats!r} 이 요건표에 없다"))
            continue
        seen, cur = {e.id}, e.defeats
        while cur:
            if cur in seen:
                out.append(Violation("J011", "hard", f"요건 {e.id}",
                                     "재항변 사슬이 돈다 -- 결론이 정해지지 않는다"))
                break
            seen.add(cur)
            nxt = case.element(cur)
            cur = nxt.defeats if nxt else ""
    return out


def check(case, issues=None, corpus=None) -> tuple:
    """(위반 목록, 검증된 요건 수, 미검증 요건 수).

    issues 를 주지 않으면 도출 결과를 검사한다 -- 그때 J010 은 자기 자신과 비교하게 되므로
    건너뛴다.
    """
    corpus = corpus if corpus is not None else CP.load()
    given = issues is not None
    issues = issues if given else IS.derive(case)
    out, checked, unverified = check_anchor(case, corpus)
    for fn in (check_stage, check_burden, check_opposition, check_outcome_relevance,
               check_invocation, check_schluessig, check_method, check_duplicate,
               check_chain):
        out.extend(fn(case, issues))
    if given:
        out.extend(check_derivation(case, issues))
    return out, checked, unverified


def main(argv=None):
    ap = argparse.ArgumentParser(description="쟁점 기계 관문 J001~J010")
    ap.add_argument("case", help="사건 JSON")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    case = IS.load(args.case)
    corpus = CP.load(args.corpus)
    print(IS.report(case))
    vs, checked, unverified = check(case, corpus=corpus)
    ok, summary = verdict(vs)
    print(f"\n관문: {summary}")
    for v in vs:
        if v.severity == "hard" or args.verbose:
            print(f"  {v}")
    print(f"요건 조문 대조: 검증 {checked}건 · 미검증 {unverified}건")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
