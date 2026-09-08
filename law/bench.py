"""판결문 대조 자 -- **판례 하나가 곧 정답지다.**

판결문에는 세 가지가 다 들어 있다: 사실관계(입력) · 법원이 판단한 쟁점(정답) · 주문(결론).
사실관계만 떼어 `brief.py -> issue.py` 에 넣고, 도출한 쟁점과 결론을 판결문과 견준다.
판례 원장이 차면 정답지가 수만 장 생기는 셈이다. **이것이 밖의 자의 본체다.** 변호사시험은
70문 중 50문이 판례 전용이라 곁가지로 남긴다(ROADMAP 9).

    python3 law/bench.py law/precedents/*.txt --보기        # 부르지 않고 몇 건이 갈리는지만
    python3 law/bench.py law/precedents/*.txt --n 20        # 20건 대조

## 두 수를 낸다 -- 하나는 주된 자고 하나는 참고다

    쟁점 재현율   법원이 판단한 쟁점 중 파이프라인이 도출한 비율      <- 주된 자
    결론 일치율   주문과 파이프라인 결론이 같은 비율                 <- 참고

뒤의 것이 약한 이유: 파이프라인은 증거의 증명력을 안 잰다. 법원이 "증인 진술을 믿을 수
없다" 로 가른 사건은 맞힐 수 없고, 맞힐 수 없는 것을 자로 삼으면 안 된다. 앞의 것은
다르다 -- 어느 요건이 다투어졌는가는 사실관계와 조문에서 계산되는 것이라, 법원과 같은
자리를 짚었는가를 잴 수 있다.

## 갈라야 잰다

판결문을 사실관계와 판단으로 못 가르면 그 건은 **못 가름**으로 세고 점수에서 뺀다.
반쯤 가른 채 재면 그 점수가 거짓이다(`exam.py 읽기점검` 과 같은 이유). `--보기` 가
먼저 그 수를 보여 준다.

## 관문을 모른다

여기서 LLM 을 두 번 부른다 -- 사실관계를 요건표로(brief.py), 판단 절을 쟁점 목록으로.
둘 다 관문 이야기가 없다. 정답을 뽑는 프롬프트에 심판을 실으면 정답이 심판에 맞춰진다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import brief as BR                                           # noqa: E402
from law import corpus as CP                                          # noqa: E402
from law import issue as IS                                           # noqa: E402

# fetch.py 가 저장한 꼴: [판시사항] ... [판결요지] ... [참조조문] ... [판례내용] ...
_OURS = re.compile(r"^\[(판시사항|판결요지|참조조문|참조판례|판례내용)\]\s*$", re.M)
# 판례내용 안의 대법원 서식: 【주 문】 【이 유】 【청구취지】
_THEIRS = re.compile(r"【\s*([가-힣]\s*[가-힣](?:\s*[가-힣]+)?)\s*】")
# 이유 안에서 '판단' 이 시작되는 머리. "3. 판단", "나. 판단", "2. 소멸시효 항변에 관한 판단"
_JUDGE_HEAD = re.compile(r"^\s*(?:\d+|[가-힣])\s*[.)]\s*[^\n]{0,30}판단", re.M)


def split(text: str) -> dict:
    """판례 파일 -> {판시사항, 판결요지, 참조조문, 주문, 이유}. 없는 칸은 빈 문자열."""
    out = {k: "" for k in ("판시사항", "판결요지", "참조조문", "주문", "이유")}
    parts = _OURS.split(text)
    ours = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    for k in ("판시사항", "판결요지", "참조조문"):
        out[k] = ours.get(k, "")
    body = ours.get("판례내용", text)
    ps = _THEIRS.split(body)
    theirs = {re.sub(r"\s+", "", ps[i]): ps[i + 1].strip() for i in range(1, len(ps) - 1, 2)}
    out["주문"] = theirs.get("주문", "")
    out["이유"] = theirs.get("이유", "")
    return out


def facts_of(reason: str) -> tuple:
    """이유에서 **판단 앞부분**(기초사실·당사자 주장)만 뗀다. (사실관계, 판단, 갈렸는가)."""
    m = _JUDGE_HEAD.search(reason)
    if not m:
        return reason.strip(), "", False
    return reason[:m.start()].strip(), reason[m.start():].strip(), True


_GRANT = re.compile(r"지급하라|이행하라|말소하라|인도하라|명도하라|확인한다|취소한다|무효임을")
_DENY = re.compile(r"기각한다")
_DISMISS = re.compile(r"각하한다")


def verdict_of(order: str) -> str:
    """주문 -> 인용 · 일부인용 · 기각 · 각하 · ?. **글자로만 본다.**"""
    o = re.sub(r"\s+", "", order)
    if _DISMISS.search(o) and not _GRANT.search(o):
        return "각하"
    g, d = bool(_GRANT.search(o)), bool(_DENY.search(o))
    if g and d:
        return "일부인용"
    if g:
        return "인용"
    if d:
        return "기각"
    return "?"


def refs_of(refs: str) -> tuple:
    """참조조문 -> (법령명 목록, 조 번호 목록). 판결문이 스스로 어느 조문이 문제인지 말한다."""
    statutes, nums, cur = [], [], ""
    for tok in re.split(r"[,、]", refs):
        st = CP.STATUTE_NAME.search(tok)
        if st and st.group(0) not in CP.NOT_A_STATUTE:
            cur = CP.normalize_statute(st.group(0))
            if cur not in statutes:
                statutes.append(cur)
        for c in CP.find_citations(tok):
            if c.article not in nums:
                nums.append(c.article)
    return statutes, nums


def points_prompt(judgment: str) -> str:
    """**관문 이야기가 한 줄도 없다.** 판단 절에서 법원이 가른 자리를 짧게 적게 한다."""
    return f"""아래는 판결문의 판단 부분입니다. 법원이 **당사자 사이에 다투어져 판단한 자리**를
하나씩 짧은 물음으로 적으십시오. 한 줄에 하나, `…이(가) 인정되는가` 꼴로. 법원이 설명만
하고 넘어간 것은 적지 마십시오. 다른 말은 붙이지 마십시오.

{judgment.strip()}"""


def parse_points(text: str) -> list:
    out = []
    for line in (text or "").splitlines():
        s = re.sub(r"^\s*[-*\d.)]+\s*", "", line).strip()
        if s and "인정되는가" in s:
            out.append(s)
    return out


_TOK = re.compile(r"[가-힣]{2,}")


def _toks(s: str) -> set:
    return set(_TOK.findall(s))


def match(points: list, issues: list, floor: float = 0.5) -> list:
    """법원의 쟁점 하나에 도출 쟁점 하나를 짝짓는다. 낱말 겹침으로 -- LLM 을 안 쓴다.

    법원이 '소멸시효 완성이 인정되는가' 라 했고 파이프라인이 '상사시효 5년이 2024.2.15
    완성이(가) 인정되는가' 를 냈으면 '소멸시효/시효·완성' 이 겹친다. 반이 넘게 겹치면
    같은 자리다. 이 기준은 거칠다 -- 그러나 설명이 되고, LLM 심판이 아니다.
    """
    out = []
    for p in points:
        pt = _toks(p) - {"인정되는가"}
        best, score = None, 0.0
        for i in issues:
            it = _toks(i.question) | _toks(getattr(i, "element", ""))
            if not pt:
                continue
            s = len(pt & it) / len(pt)
            if s > score:
                best, score = i, s
        out.append((p, best if score >= floor else None, round(score, 2)))
    return out


def bench_one(path: Path, ask, corpus, domain: str = "민사") -> dict:
    """판례 하나를 잰다. 못 가르면 그렇다고 적고 점수는 안 낸다."""
    sec = split(path.read_text(encoding="utf-8"))
    facts, judgment, ok_split = facts_of(sec["이유"])
    row = {"판례": path.stem, "주문": verdict_of(sec["주문"]), "갈림": ok_split,
           "재현율": None, "결론일치": None, "쟁점": []}
    if not ok_split or not sec["주문"]:
        row["못가름"] = "이유를 사실관계/판단으로 못 갈랐다" if not ok_split else "주문이 없다"
        return row
    statutes, nums = refs_of(sec["참조조문"])
    if not statutes or not nums:
        row["못가름"] = "참조조문이 없어 어느 조문을 줄지 모른다"
        return row
    try:
        case = BR.brief(facts, domain, statutes, nums, corpus=corpus, ask=ask)
    except (RuntimeError, ValueError) as e:
        row["못가름"] = f"요건표를 못 만들었다: {e}"
        return row
    issues = IS.derive(case)
    points = parse_points(ask(points_prompt(judgment)))
    pairs = match(points, issues)
    hit = sum(1 for _, m, _ in pairs if m is not None)
    row["쟁점"] = [(p, m.element if m else None, s) for p, m, s in pairs]
    row["재현율"] = (hit / len(points)) if points else None
    mine = IS.stations(case)["beklagten"]
    row["결론"] = mine
    row["결론일치"] = (mine == row["주문"]) if row["주문"] in ("인용", "기각") else None
    return row


def report(rows: list) -> str:
    갈린 = [r for r in rows if r.get("재현율") is not None]
    못 = [r for r in rows if r.get("못가름")]
    lines = [f"판례 {len(rows)}건 · 잰 것 {len(갈린)}건 · 못 가른 것 {len(못)}건"]
    if 못:
        lines.append("  못 가른 이유: " + " / ".join(sorted({r['못가름'] for r in 못}))[:200])
    if 갈린:
        재 = sum(r["재현율"] for r in 갈린) / len(갈린)
        결 = [r for r in 갈린 if r.get("결론일치") is not None]
        lines.append(f"  **쟁점 재현율 {재:.0%}**  <- 주된 자 (법원이 가른 자리를 파이프라인도 짚었는가)")
        if 결:
            일 = sum(1 for r in 결 if r["결론일치"]) / len(결)
            lines.append(f"  결론 일치율 {일:.0%} ({len(결)}건)  <- 참고. 증거의 증명력은 안 잰다")
        lines.append("  못 가른 건은 점수에 안 넣었다 -- 반쯤 가른 채 재면 그 점수가 거짓이다.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="판결문으로 잰다 -- 판례 하나가 곧 정답지다")
    ap.add_argument("paths", nargs="+", help="판례 파일들 (law/precedents/*.txt)")
    ap.add_argument("--보기", dest="show", action="store_true",
                    help="부르지 않고 몇 건이 사실관계/판단으로 갈리는지만 본다")
    ap.add_argument("--n", type=int, default=0, help="앞에서부터 이만큼만")
    ap.add_argument("--갈래", dest="domain", default="민사", choices=list(IS.STAGES))
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--장부", dest="ledger", default="law/bench.jsonl")
    a = ap.parse_args(argv)

    paths = [Path(p) for p in a.paths][: a.n or None]
    if a.show:
        갈림 = 못 = 주문없음 = 참조없음 = 0
        for p in paths:
            sec = split(p.read_text(encoding="utf-8"))
            _, _, ok = facts_of(sec["이유"])
            갈림 += ok
            못 += not ok
            주문없음 += not sec["주문"]
            참조없음 += not refs_of(sec["참조조문"])[1]
        print(f"판례 {len(paths)}건: 사실관계/판단으로 갈린 것 {갈림} · 못 가른 것 {못}"
              f" · 주문 없음 {주문없음} · 참조조문 없음 {참조없음}")
        print("못 가른 것이 많으면 자(_JUDGE_HEAD)부터 의심하라 -- 판결문 서식이 다를 수 있다.")
        return 0

    corpus = CP.load(a.corpus)
    rows = []
    with Path(a.ledger).open("w", encoding="utf-8") as f:
        for p in paths:
            row = bench_one(p, BR._pool_ask, corpus, a.domain)
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"  {row['판례']:16} 주문 {row['주문']:6} "
                  + (f"재현율 {row['재현율']:.0%}" if row['재현율'] is not None
                     else f"({row.get('못가름', '')})"))
    print("\n" + report(rows))
    print(f"장부: {a.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
