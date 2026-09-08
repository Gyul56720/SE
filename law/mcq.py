"""선택형 -- **관문을 거꾸로 쓴다.** 답을 맞히는 데 쓰는 자리.

출제자는 옳은 지문에서 낱말 하나를 바꿔 오답을 만든다: 서법(`하여야`->`할 수 있다`) ·
접속(`및`->`또는`) · 경계(`이내`->`초과`) · 법효과어(`준용`->`적용`) · 용어(`재물`->
`재산상 이익`). **그게 정확히 W001~W005 다.** `law/mutate.py` 가 관문을 시험하려고 그
다섯 축으로 오답을 심는데, 실제 출제도 같은 축을 쓴다.

그래서 관문을 뒤집을 수 있다:

    선택지 다섯 -> 각각을 조문과 대조 -> 조문과 어긋나는 것을 짚는다
    "옳지 않은 것은?"  -> 어긋난 그것이 답
    "옳은 것은?"       -> 어긋난 것을 소거

    python3 law/mcq.py law/exam/2026_민사법_선택형_손옮김.txt          # 풀 수 있는 것만
    python3 law/mcq.py 시험지.txt --답 정답표.txt                     # 맞았는지까지

## 이것은 시험을 푸는 도구가 아니다

**조문으로 판정되는 지문에만 답한다.** 실측(2026 민사법 70문): 지문 515개 중 조문
실마리가 있는 것은 30개(6%)뿐이고, 나머지는 판례 법리만으로 서 있다. 그러니 이 파일이
푸는 문항은 처음부터 적다. **적은 채로 정확한 것**이 목표다 -- 조문이 말해 주지 않는
자리에서 답을 지어내면 그건 이 저장소가 막으려는 바로 그것이다.

그래서 `--보기` 가 먼저 몇 문항이나 손댈 수 있는지 보여 준다. 손댈 수 있는 수가
적으면 원장을 더 채우라는 뜻이지, 답을 넓게 찍으라는 뜻이 아니다.

## 왜 '소거' 이고 '선택' 이 아닌가

어긋남을 못 찾았다는 것은 **그 지문이 옳다는 뜻이 아니라 조문으로는 볼 것이 없다는
뜻**이다(미검증 ≠ 통과). 그래서 어긋난 지문이 정확히 하나일 때만 "옳지 않은 것" 문제에
답하고, 둘 이상이면 답하지 않는다 -- 둘 중 하나는 자가 헛짚은 것이기 때문이다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import exam as EX                                            # noqa: E402
from law import wording as WD                                         # noqa: E402

# 물음이 옳은 것을 고르라는지 옳지 않은 것을 고르라는지. 이걸 뒤집으면 답이 뒤집힌다.
_NEG = re.compile(r"옳지\s*않은|틀린|적절하지\s*않은|해당하지\s*않는")
_POS = re.compile(r"옳은\s*것|적절한\s*것|해당하는\s*것")
# 보기(ㄱㄴㄷ)를 조합해 고르는 꼴. 선택지가 지문이 아니라 조합이라 소거 방식이 다르다.
_COMBO = re.compile(r"^\s*[ㄱ-ㅎ](\s*[,·]\s*[ㄱ-ㅎ])*\s*$")
_OX = re.compile(r"[ㄱ-ㅎ]\s*\(\s*[○×OXｘ]\s*\)")


class _Doc:
    """관문이 기대하는 최소한의 문서 꼴. 지문 하나가 곧 한 절이다."""

    def __init__(self, text: str, statute=None):
        self.sections = {"2. 조문과 이론": text}
        self.statute = statute
        self.path = Path("지문.md")


def statute_of(text: str, corpus) -> str | None:
    """이 지문이 어느 법령을 말하는가. **못 정하면 None -- 짐작하지 않는다.**

    법이론서는 front-matter 에 법령을 선언하지만 시험지에는 그런 것이 없다. 그래서
    지문 안에서 찾는다: 「민법」처럼 이름이 적혀 있으면 그것이고, `제126조` 처럼
    번호만 있으면 **원장에서 그 조를 가진 법령이 하나일 때만** 그것으로 본다.

    둘 이상이면 None 이다. 민법 제12조와 형법 제12조는 다른 조문이고, 어느 쪽인지
    모르는 채 하나를 골라 대조하면 **틀린 조문으로 멀쩡한 지문을 기각**한다.
    """
    for m in CP.STATUTE_NAME.finditer(text):
        name = m.group(0)
        if name not in CP.NOT_A_STATUTE and corpus.covers(name):
            return CP.normalize_statute(name)
    cands = None
    for c in CP.find_citations(text):
        if c.statute:
            continue
        has = set(corpus.statutes_with(c.article))
        cands = has if cands is None else (cands & has)
    if cands and len(cands) == 1:
        return next(iter(cands))
    return None


# 지문 하나를 조문과 대 보는 관문만 고른다. 문서 단위 관문(L005 단정 · L007 구조 ·
# L008 창작 라벨)은 여기서 부르지 않는다 -- 시험지는 법이론서가 아니라서 그 셋은
# 언제나 걸리고, 그 걸림은 정답과 아무 상관이 없다.
#
# 실측: 시험지에 gate.py 를 통째로 겨눴더니 hard 13건이 났는데 **전부 L007 하나**였고
# 실질 위반은 0건이었다. 그것을 보고 "정답을 확신할 수 없다" 고 읽으면 안 된다.
_지문관문 = ("L001 인용실재", "L003 수량", "W001~W005 문언")


def judge_one(text: str, corpus) -> dict:
    """지문 하나를 조문과 대조. 어느 법령인지 못 정하면 대조 0 이다."""
    from law import gate as GT

    doc = _Doc(text, statute_of(text, corpus))
    tg = WD._targets(text, doc, corpus)
    if not tg:
        return {"대조": 0, "어긋남": []}
    vs = [v for v in WD.check(doc, corpus) if v.severity == "hard"]
    cite, _, _ = GT.check_citations(doc, corpus)
    vs += [v for v in cite if v.severity == "hard"]
    vs += [v for v in GT.check_quantities(doc, corpus) if v.severity == "hard"]
    return {"대조": len(tg), "어긋남": [v.detail for v in vs],
            "조문": [r for r, _ in tg], "법령": doc.statute}


def polarity(question: str) -> str:
    """물음이 무엇을 고르라는가. `옳지않은` · `옳은` · `?`(모름)."""
    if _NEG.search(question):
        return "옳지않은"
    if _POS.search(question):
        return "옳은"
    return "?"


def shape(q) -> str:
    """선택지가 지문인가(`지문`), 보기 조합인가(`조합`), OX 조합인가(`OX`)."""
    picks = list(q.선택지)
    if not picks:
        return "?"
    if all(_OX.search(p) for p in picks):
        return "OX"
    if all(_COMBO.match(p) for p in picks):
        return "조합"
    return "지문"


def solve(q, corpus) -> dict:
    """한 문항. **답할 수 있을 때만 답한다.** 못 하면 왜 못 하는지 적는다."""
    pol, sh = polarity(q.물음), shape(q)
    row = {"번호": q.번호, "물음꼴": pol, "선택지꼴": sh,
           "고름": 0, "근거": [], "왜못품": ""}
    if pol == "?":
        row["왜못품"] = "옳은/옳지 않은 어느 쪽을 고르라는지 물음에서 못 읽었다"
        return row

    if sh == "지문":
        판 = [judge_one(t, corpus) for t in q.선택지]
        row["대조된지문"] = sum(1 for j in 판 if j["대조"])
        어긋난 = [i + 1 for i, j in enumerate(판) if j["어긋남"]]
        if not row["대조된지문"]:
            row["왜못품"] = "선택지 어디에도 원장에 있는 조문이 안 걸렸다"
            return row
        if pol == "옳지않은":
            if len(어긋난) == 1:
                row["고름"] = 어긋난[0]
                row["근거"] = 판[어긋난[0] - 1]["어긋남"]
            elif len(어긋난) > 1:
                row["왜못품"] = (f"어긋난 지문이 {len(어긋난)}개다 {어긋난} -- "
                                f"하나는 자가 헛짚은 것이라 답하지 않는다")
            else:
                row["왜못품"] = (f"조문과 어긋나는 지문을 못 찾았다 "
                                f"(대조한 지문 {row['대조된지문']}/{len(q.선택지)})")
        else:                                    # 옳은 것을 고르라
            남은 = [i + 1 for i, j in enumerate(판) if not j["어긋남"]]
            if len(남은) == 1:
                row["고름"] = 남은[0]
                row["근거"] = [f"나머지 넷이 조문과 어긋났다 (소거)"]
            else:
                row["왜못품"] = (f"소거하고 {len(남은)}개가 남았다 -- "
                                f"어긋남을 못 찾은 것은 옳다는 뜻이 아니다")
        return row

    # 보기 조합 · OX: 보기마다 판정한 뒤 그 조합과 맞는 선택지를 찾는다.
    if not q.보기:
        row["왜못품"] = f"선택지가 {sh} 꼴인데 보기(ㄱㄴㄷ)가 없다"
        return row
    판 = {k: judge_one(t, corpus) for k, t in q.보기}
    대조 = [k for k, j in 판.items() if j["대조"]]
    row["대조된보기"] = len(대조)
    if len(대조) < len(q.보기):
        row["왜못품"] = (f"보기 {len(q.보기)}개 중 {len(대조)}개만 조문이 걸렸다 -- "
                        f"나머지를 모르면 조합을 못 고른다")
        return row
    어긋난 = {k for k, j in 판.items() if j["어긋남"]}
    row["보기판정"] = {k: ("어긋남" if k in 어긋난 else "안어긋남") for k in 판}
    row["왜못품"] = ("보기는 다 대조했으나 조합을 고르는 자리는 아직 안 만들었다 "
                    "-- '안 어긋남'은 '옳다'가 아니라서 조합을 확정할 수 없다")
    return row


def report(rows: list, key: dict) -> str:
    푼 = [r for r in rows if r["고름"]]
    lines = [f"\n문항 {len(rows)}개 중 **답한 것 {len(푼)}개**"]
    if key:
        본 = [r for r in 푼 if r["번호"] in key]
        맞 = [r for r in 본 if key[r["번호"]] == r["고름"]]
        if 본:
            lines.append(f"  답한 것 중 정답 {len(맞)}/{len(본)}"
                         f"  <- **답한 것만 센다. 안 답한 것은 틀린 게 아니라 안 푼 것이다**")
        미 = [r["번호"] for r in rows if not r["고름"] and r["번호"] in key]
        if 미:
            lines.append(f"  안 푼 것 {len(미)}개 -- 이만큼이 조문으로 안 보이는 자리다")
    else:
        lines.append("  정답률은 정답표가 없어 못 적는다 (--답 으로 준다)")
    까닭 = {}
    for r in rows:
        if r["왜못품"]:
            k = r["왜못품"].split("--")[0].split("(")[0].strip()
            까닭[k] = 까닭.get(k, 0) + 1
    if 까닭:
        lines.append("  못 푼 까닭:")
        for k, n in sorted(까닭.items(), key=lambda x: -x[1]):
            lines.append(f"    {n:3}개  {k}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="선택형 -- 조문으로 판정되는 것만 푼다 (관문을 거꾸로)")
    ap.add_argument("target", help="시험지 txt")
    ap.add_argument("--답", dest="key", default="", help="정답표")
    ap.add_argument("--보기", dest="show", action="store_true",
                    help="풀지 않고 몇 문항이나 손댈 수 있는지만 본다")
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    a = ap.parse_args(argv)

    qs = EX.parse(Path(a.target).read_text(encoding="utf-8"))
    qs = qs[: a.n or None]
    corpus = CP.load(a.corpus)
    if not corpus:
        print("원장이 비어 있다. law/fetch.py 로 조문을 먼저 받아라.", file=sys.stderr)
        return 2
    print(f"문항 {len(qs)}개 · 원장 {len(corpus.articles)}개 법령")

    if a.show:
        꼴 = {}
        for q in qs:
            꼴[(polarity(q.물음), shape(q))] = 꼴.get((polarity(q.물음), shape(q)), 0) + 1
        for (p, s), n in sorted(꼴.items(), key=lambda x: -x[1]):
            print(f"  {n:3}개  물음 '{p}' · 선택지 '{s}'")
        print("  '지문' 꼴만 지금 풀 수 있다 -- 조합·OX 는 보기 판정이 다 서야 한다.")
        return 0

    key = EX.load_key(Path(a.key)) if a.key else {}
    rows = []
    for q in qs:
        r = solve(q, corpus)
        rows.append(r)
        if r["고름"]:
            mark = ("O" if key.get(q.번호) == r["고름"] else "X") if q.번호 in key else "?"
            print(f"[{mark}] 문 {q.번호:<3} -> {r['고름']}  {r['근거'][0][:70] if r['근거'] else ''}")
    print(report(rows, key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
