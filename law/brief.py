"""사안 -> 요건표. **생성자다. 관문을 모른다.**

`law/write.py` 가 법이론서에 대해 하는 일을 요건표에 대해 한다. 사안 글과 조문을 주고
`law/issue.py` 가 읽는 JSON 을 받아 온다. 쟁점을 뽑게 하지 않는다 -- 쟁점은 그 JSON 에서
코드가 계산한다(issue.derive). LLM 이 하는 일은 셋뿐이다:

    조문에서 요건 뽑기 · 사실에서 당사자 주장 뽑기 · **양쪽이 세울 수 있는 것을 전부 세우기**

마지막이 이 파일의 요점이다. 사안 글(소장·답변서)에는 한쪽 주장만 있다. 목표는 양쪽이
**가능한 한 많은** 법적 방어를 내놓는 것이므로, 적혀 있는 주장 외에 그 단계에서 세울 수
있는 항변·재항변을 전부 세우게 한다. 어느 것이 실제로 적혀 있고 어느 것이 세워 본 것인지는
`source` 에 남긴다 -- 사람이 볼 것이다.

## 왜 관문을 모르는가

`novel/gate.py` 와 `law/write.py` 가 배운 것과 같다. 생성자에 심판을 실으면 원고가
사양서가 된다 -- 관문을 통과하는 요건표만 나오고, 진짜 다툴 자리는 빠진다. 그래서 이
프롬프트에는 J001 이 무엇을 보는지, 뒤집기 검사가 무엇인지 한 줄도 없다. 검사는
`python3 law/issuegate.py <json>` 이 따로 한다.

    python3 law/brief.py 사안.txt --법 민법 상법 --조문 105,387,492,162,168,184 \\
        --out law/cases/이름.json
    python3 law/brief.py 사안.txt --법 민법 --조문 492 --프롬프트만    # 부르지 않는다
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import issue as IS                                           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

_POOL = None


def _pool_ask(text: str) -> str:
    """기본 물음이. `write.py` 와 같은 자리 -- 풀은 한 번만 세운다."""
    global _POOL
    if _POOL is None:
        sys.path.insert(0, str(ROOT / "orchestrator"))
        import llm_pool
        pool = llm_pool.build_pool()
        if not pool:
            raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
        _POOL = (llm_pool, pool)
    mod, pool = _POOL
    return mod.call(pool, text, pool_id="law")[0]


def articles(statutes: list, nums: list, corpus) -> list:
    """원장에서 조문 원문을 꺼낸다. **없는 것은 조용히 빼지 않고 말한다.**"""
    out, missing = [], []
    for st in statutes:
        for n in nums:
            body = corpus.text(st, n)
            if body:
                out.append((st, n, body))
    if not out and nums:
        missing = [f"{st} 제{n}조" for st in statutes for n in nums]
        raise RuntimeError(f"원장에 하나도 없다: {', '.join(missing[:6])} "
                           f"-- law/fetch.py 로 먼저 받아라")
    return out


def prompt(facts: str, domain: str, arts: list) -> str:
    """**관문 이야기가 한 줄도 없다.** 사안·조문·무엇을 낼 것인가뿐이다."""
    sides = IS.SIDES.get(domain, ("원고", "피고"))
    stages = IS.STAGES[domain]
    conds = "\n\n".join(f"[{st} 제{n}조]\n{body}" for st, n, body in arts) or "(조문 없음)"
    return f"""다음은 {domain} 사안입니다. 이 사안을 **요건표**로 옮기십시오.

## 사안
{facts.strip()}

## 쓸 수 있는 조문 (이 밖의 조문은 쓰지 마십시오)
{conds}

## 무엇을 낼 것인가

{sides[0]}의 청구가 서려면 어떤 요건이 필요한지, {sides[1]}은 어느 단계에서 무엇을 세울 수
있는지, 그것을 {sides[0]}이 무엇으로 받아칠 수 있는지를 **전부** 적습니다.

  · 단계는 이 넷 중 하나입니다: {' · '.join(stages)}
  · 요건 하나마다 근거 조문(법령명·조 번호)을 붙입니다. 위 조문에 없는 요건은 세우지
    마십시오 -- 대신 "조문 없음" 이라 적고 `statute` 를 비웁니다.
  · **사안에 적힌 주장만 옮기지 마십시오.** 그 단계에서 {sides[1]}이 세울 수 있는
    항변을 법적으로 가능한 것은 전부 세우고, 그 항변마다 {sides[0]}이 세울 수 있는
    재항변을 전부 세우십시오. 약해 보여도 적습니다 -- 강약은 나중에 갈립니다.
  · 재항변은 `defeats` 에 무너뜨리는 요건의 `id` 를 적습니다.
  · `source` 에는 그 요건이 어디서 왔는지 적습니다: 사안에 적혀 있으면 어느 자리인지
    ("소장 2쪽"), 적혀 있지 않은데 세워 본 것이면 "가능한 항변" / "가능한 재항변".
  · `positions` 에는 요건마다 양쪽이 무엇이라 말하는지를 적습니다. 사안에 안 적힌
    요건은 그것을 세우는 쪽을 true, 상대를 false 로 둡니다.
  · 사실 요건(`kind`: "사실")에는 증거방법(`evidence`)을, 법률 요건("법률")에는
    해석기법(`canon`: 문언·체계·역사·목적 중 하나)을 붙입니다.
  · 날짜와 금액은 사안에 적힌 그대로 씁니다. 사람 이름은 쓰지 말고 역할로 부릅니다.

## 출력 (JSON 하나만. 다른 말은 붙이지 마십시오)

{{
 "domain": "{domain}",
 "claim": "누가 무엇을 누구에게 무슨 근거로",
 "elements": [
  {{"id": "짧은id", "text": "요건", "stage": "{stages[0]}", "statute": "법령명",
   "article": "조 번호", "kind": "사실", "evidence": ["갑 제N호증"],
   "invoked": false, "defeats": "", "source": "소장 N쪽"}}
 ],
 "positions": {{"짧은id": {{"{sides[0]}": true, "{sides[1]}": false}}}}
}}"""


_FENCE = re.compile(r"^\s*```(?:json)?\s*\n|\n```\s*$")


def parse(text: str) -> dict:
    """모델이 씌운 울타리를 벗기고 JSON 하나를 꺼낸다. 못 꺼내면 **말한다.**"""
    t = _FENCE.sub("", (text or "").strip())
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"JSON 이 없다: {t[:80]!r}")
    d = json.loads(t[start:end + 1])
    for k in ("domain", "elements", "positions"):
        if k not in d:
            raise ValueError(f"요건표에 {k!r} 가 없다")
    return d


def brief(facts: str, domain: str, statutes: list, nums: list, corpus=None,
          ask=None) -> IS.Case:
    corpus = corpus if corpus is not None else CP.load()
    arts = articles(statutes, nums, corpus)
    d = parse((ask or _pool_ask)(prompt(facts, domain, arts)))
    els = [IS.Element(**{k: v for k, v in e.items()
                         if k in IS.Element.__dataclass_fields__}) for e in d["elements"]]
    return IS.Case(domain=d["domain"], claim=d.get("claim", ""), elements=els,
                   positions=d["positions"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="사안을 요건표로 옮긴다 (관문은 모른다)")
    ap.add_argument("facts", help="사안 글 파일 (소장·답변서 등)")
    ap.add_argument("--갈래", dest="domain", default="민사", choices=list(IS.STAGES))
    ap.add_argument("--법", dest="statutes", nargs="+", required=True)
    ap.add_argument("--조문", dest="nums", default="", help="쉼표로 (예: 105,387,492)")
    ap.add_argument("--out", default="", help="저장할 JSON 경로")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--프롬프트만", dest="dry", action="store_true",
                    help="부르지 않고 프롬프트만 찍는다 -- 무엇을 주는지 눈으로 본다")
    a = ap.parse_args(argv)

    facts = Path(a.facts).read_text(encoding="utf-8")
    nums = [x.strip() for x in a.nums.split(",") if x.strip()]
    corpus = CP.load(a.corpus)
    if a.dry:
        print(prompt(facts, a.domain, articles(a.statutes, nums, corpus)))
        return 0
    case = brief(facts, a.domain, a.statutes, nums, corpus)
    text = IS.dump(case)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"요건표: {a.out}  ({len(case.elements)}개 요건)")
        print(f"다음: python3 law/issue.py {a.out}       # 쟁점·유불리")
        print(f"      python3 law/issuegate.py {a.out}   # 관문")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
