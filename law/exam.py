"""**밖의 자.** 변호사시험을 풀리고, 그 답안을 우리 심판이 검사한다.

    python3 law/exam.py full_ocr_result.txt --보기        # 몇 문항을 읽었는지 눈으로 본다
    python3 law/exam.py full_ocr_result.txt --n 5         # 다섯 문항만 풀어 본다
    python3 law/exam.py full_ocr_result.txt --답 answers.txt
    python3 law/exam.py --장부 law/exam.jsonl             # 적어 둔 것을 다시 읽는다

## 왜 밖의 자가 필요한가

지금 우리 점수는 **우리가 만든 관문의 위반 수**뿐이다. 자기가 만든 자로 자기를 재는
것이라, 관문이 놓친 것은 영원히 안 보인다(law/ROADMAP.md 5번). 변호사시험은 우리가
안 만든 자다 -- 정답이 밖에서 정해져 있다.

**두 수를 같은 장부에 나란히 적는다.**

    정답률      밖의 자 -- 이 답이 맞는가
    위반 수     안의 자 -- 그 근거가 조문과 어긋나지 않는가

둘이 같이 움직이는지가 핵심이다. 관문 위반은 내려가는데 정답률도 같이 내려가면,
그 지시문은 관문만 통과시키는 쪽으로 답안을 균질화한 것이다(novel/gate.py 가
"관문이 작가가 되면 원고가 균질해진다" 로 겪은 그 사고의 법 버전).

## 이 시험이 우리 자의 한계도 같이 보여 준다

선택형 지문은 **조문 번호를 거의 안 쓴다.** 전부 "다툼이 있는 경우 판례에 의함" 이다.
그래서 시험지 자체에는 우리 관문이 댈 것이 거의 없다. 그러나 **답안**은 다르다 --
근거를 조문으로 쓰라고 시키면, 그 근거가 우리 원장과 대조된다. 재는 자리를 시험지에서
답안으로 옮기는 것이 이 파일이 하는 일이다.

## 생성자는 관문을 모른다

`law/write.py` 와 같은 규율이다. 푸는 쪽 프롬프트에 L001 도 W004 도 없다 --
알려 주면 답안이 관문을 통과하는 쪽으로 균질해지고, 그러면 두 수를 견주는 일 자체가
뜻을 잃는다. `tests/test_law_exam.py` 가 닫힌 목록으로 그것을 고정한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import wording as WD                                         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "law" / "exam.jsonl"

# 휴대폰으로 찍은 화면이라 문제와 상관없는 줄이 섞인다.
# **닫힌 목록으로 지운다** -- 뜻으로 지우면 문제 본문을 지운다.
_CHROME = re.compile(
    r"^\s*(?:\d{1,2}:\d{2}|LTE|5G|viewer\.moj\.go\.kr|\d+\s*쪽|[◀▶←→]+|\d+\s*/\s*\d+)\s*$")
_PAGE = re.compile(r"^\s*\d{1,3}\s*쪽\s*$")

_ASK = re.compile(r"^\s*문\s*(\d{1,3})\s*[.．]\s*(.*)$")
_ITEM = re.compile(r"^\s*([ㄱ-ㅎ])\s*[.．]\s*(.+)$")
_PICK = re.compile(r"[①②③④⑤]")
_PICK_NO = {c: i + 1 for i, c in enumerate("①②③④⑤")}


@dataclass
class Question:
    번호: int
    물음: str = ""
    보기: list = field(default_factory=list)
    선택지: list = field(default_factory=list)

    def 글(self) -> str:
        """모델에게 보여 줄 문제 전문."""
        out = [f"문 {self.번호}. {self.물음}"]
        out += [f"  {ㄱ}. {t}" for ㄱ, t in self.보기]
        out += [f"  {'①②③④⑤'[i]} {t}" for i, t in enumerate(self.선택지)]
        return "\n".join(out)


def clean(text: str) -> list:
    """화면 껍데기를 걷어낸 줄 목록."""
    return [l.rstrip() for l in text.splitlines()
            if l.strip() and not _CHROME.match(l) and not _PAGE.match(l)]


def parse(text: str) -> list:
    """`문 N.` 으로 자르고, 그 안에서 보기(ㄱ~)와 선택지(①~)를 가른다.

    **읽은 것을 세어 보여 줘야 한다**(`--보기`). OCR 은 깨지고, 깨진 채로 조용히
    반쯤 읽으면 그 뒤의 점수가 전부 거짓이 된다.
    """
    qs, cur = [], None
    for line in clean(text):
        m = _ASK.match(line)
        if m:
            cur = Question(int(m.group(1)), m.group(2).strip())
            qs.append(cur)
            continue
        if cur is None:
            continue
        if _PICK.search(line):
            for part in re.split(r"(?=[①②③④⑤])", line):
                part = part.strip()
                if part and _PICK.match(part):
                    cur.선택지.append(part[1:].strip())
            continue
        m = _ITEM.match(line)
        if m:
            cur.보기.append((m.group(1), m.group(2).strip()))
        elif cur.보기:
            cur.보기[-1] = (cur.보기[-1][0], cur.보기[-1][1] + " " + line.strip())
        else:
            cur.물음 = (cur.물음 + " " + line.strip()).strip()
    return [q for q in qs if q.물음]


def prompt(q: Question) -> str:
    """**관문 이야기가 한 줄도 없다.** 문제와, 근거를 어떻게 적을지뿐이다."""
    return f"""다음은 대한민국 변호사시험 선택형 문제입니다. 답을 고르고 그 근거를 씁니다.

{q.글()}

다음 두 줄로만 답하십시오.

답: <번호 하나>
근거: <왜 그 번호인가. 조문에 근거가 있으면 `민법 제109조` 처럼 법령명과 번호로
      부르고, 조문의 말을 옮길 때는 그 낱말을 그대로 씁니다. 조문이 아니라 판례
      법리에 따른 것이면 그렇다고 적습니다.>"""


_ANS = re.compile(r"답\s*[:：]?\s*([①②③④⑤]|[1-5])")
_WHY = re.compile(r"근거\s*[:：]?\s*(.+)", re.S)


def read_reply(text: str) -> tuple:
    """(고른 번호, 근거). 못 읽으면 (0, 원문) -- **조용히 0점 처리하지 않는다.**"""
    m = _ANS.search(text or "")
    pick = _PICK_NO.get(m.group(1), 0) if m and m.group(1) in _PICK_NO else (
        int(m.group(1)) if m else 0)
    w = _WHY.search(text or "")
    return pick, (w.group(1).strip() if w else (text or "").strip())


class _Doc:
    """관문이 기대하는 최소한의 문서 꼴. 답안은 8절 문서가 아니다."""

    def __init__(self, text: str):
        self.sections = {"2. 조문과 이론": text}
        self.statute = None
        self.path = Path("답안.md")


def judge(why: str, corpus) -> dict:
    """답안의 근거를 원장과 대조한다. **심판은 LLM 이 아니다.**"""
    doc = _Doc(why)
    cits = CP.find_citations(why)
    미검증 = [c.raw for c in cits if not corpus.has(c.statute, c.article)]
    rows = [r for r in WD.trace(doc, corpus) if r["인용"]]
    어긋남 = [k for r in rows for k in r["어긋남"]]
    return {"인용": len(cits), "미검증": len(미검증),
            "어긋남": 어긋남, "맞음": sum(len(r["맞음"]) for r in rows)}


def _pool_ask(text: str) -> str:
    sys.path.insert(0, str(ROOT / "orchestrator"))
    import llm_pool
    global _POOL
    try:
        pool = _POOL
    except NameError:
        pool = None
    if not pool:
        pool = llm_pool.build_pool()
        if not pool:
            raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
        globals()["_POOL"] = pool
    return llm_pool.call(pool, text, pool_id="exam")[0]


def load_key(path) -> dict:
    """정답표. `12: 3` · `12 3` · `12,3` 아무 꼴이나 받는다."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d{1,3})\s*[:：,\t ]\s*([①②③④⑤]|[1-5])\s*$", line)
        if m:
            v = m.group(2)
            out[int(m.group(1))] = _PICK_NO.get(v, 0) or int(v)
    return out


def report(rows: list, key: dict) -> None:
    """**두 수를 나란히 적는다.** 하나만 보면 다른 하나가 어디로 가는지 모른다."""
    n = len(rows)
    if not n:
        print("푼 것이 없다.")
        return
    맞힘 = [r for r in rows if key and r["고름"] == key.get(r["번호"])]
    어긋 = sum(len(r["어긋남"]) for r in rows)
    무근거 = sum(1 for r in rows if not r["인용"])
    print(f"\n문항 {n}개")
    if key:
        본 = [r for r in rows if r["번호"] in key]
        print(f"  정답률   {len(맞힘)}/{len(본)}  <- **밖의 자**")
    else:
        print("  정답률   정답표가 없어 못 적는다 (--답 으로 준다)")
    print(f"  어긋남   {어긋}건        <- **안의 자** (근거가 조문과 어긋난 자리)")
    print(f"  미검증   {sum(r['미검증'] for r in rows)}건  (원장에 없는 법령)")
    print(f"  조문을 아예 안 부른 답안 {무근거}개"
          f"  <- 이건 관문이 볼 것이 없는 자리다")
    if key:
        print("\n**두 수가 같이 움직이는지 본다.** 어긋남이 내려가는데 정답률도 같이"
              "\n내려가면, 그 지시문은 관문만 통과시키는 쪽으로 답안을 균질화한 것이다.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="변호사시험으로 잰다 (밖의 자)")
    ap.add_argument("target", nargs="?", default="", help="OCR 한 시험지 txt")
    ap.add_argument("--보기", dest="show", action="store_true",
                    help="풀지 않고 몇 문항을 어떻게 읽었는지만 보여준다")
    ap.add_argument("--n", type=int, default=0, help="앞에서부터 이만큼만")
    ap.add_argument("--답", dest="key", default="", help="정답표 파일")
    ap.add_argument("--장부", dest="ledger", default="", help="적어 둔 것을 다시 읽는다")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    a = ap.parse_args(argv)

    key = load_key(a.key) if a.key else {}
    if a.ledger:
        rows = [json.loads(l) for l in Path(a.ledger).read_text(encoding="utf-8").splitlines() if l.strip()]
        report(rows, key)
        return 0
    if not a.target:
        ap.error("시험지 txt 를 주거나 --장부 를 주십시오")

    qs = parse(Path(a.target).read_text(encoding="utf-8"))
    print(f"문항 {len(qs)}개를 읽었다"
          + (f" (번호 {qs[0].번호}~{qs[-1].번호})" if qs else ""))
    빈 = [q.번호 for q in qs if not q.선택지]
    if 빈:
        print(f"  **선택지를 못 읽은 문항 {len(빈)}개**: {빈[:12]}"
              f"\n  OCR 이 깨진 자리다. 이대로 풀면 그 점수는 거짓이다.")
    if a.show:
        for q in qs[:2]:
            print("\n" + "-" * 60 + "\n" + q.글())
        return 0
    if not qs:
        print("읽은 문항이 없다. --보기 로 원문 꼴을 먼저 확인하라.", file=sys.stderr)
        return 2

    corpus = CP.load(a.corpus)
    rows = []
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", encoding="utf-8") as f:
        for q in (qs[:a.n] if a.n else qs):
            pick, why = read_reply(_pool_ask(prompt(q)))
            row = {"번호": q.번호, "고름": pick, "근거": why, **judge(why, corpus)}
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            mark = ("O" if key.get(q.번호) == pick else "X") if q.번호 in key else "?"
            print(f"[{mark}] 문 {q.번호:<3} 고름 {pick}  인용 {row['인용']}"
                  f"  어긋남 {len(row['어긋남'])}")
    report(rows, key)
    print(f"\n장부: {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
