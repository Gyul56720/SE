"""**생성자.** 조문 원문을 주고 법이론서 한 편을 받는다. 심판은 여기 없다.

    python3 law/write.py 민사소송법 "기판력의 객관적 범위" 216,218
    python3 law/write.py --계획 law/plan.json          # 계획에 적힌 것 전부
    python3 law/write.py --계획 law/plan.json --법 헌법 # 그중 한 법만

## 왜 생성자가 관문을 몰라야 하는가

이 저장소가 두 번 데었다.

  · `novel/gate.py` -- 관문을 나중에 붙였더니 원고가 관문을 통과하려고 균질해졌다
  · `mathdrift/spread.py` -- 발산 프롬프트에 심판을 실었더니 20개 중 20개가
    "없음" 이 됐고, 더 나쁘게는 발산이 사양서가 됐다

그래서 **이 파일의 프롬프트에는 관문 이야기가 한 줄도 없다.** L001 이 무엇을 보는지,
W004 가 준용과 적용을 가르는지, 판례 인용이 금지인지 -- 생성자는 모른다. 아는 것은
조문 원문과 무엇을 쓸 것인가뿐이다. 검사는 `law/gate.py` 가 나중에 따로 한다.

`tests/test_law_write.py` 가 프롬프트에 그런 낱말이 안 실리는 것을 검사로 고정한다.
다시 새어 들어가면 그 자리에서 걸린다.

## 닫힌책

주는 것은 **원장에서 꺼낸 조문 원문**뿐이다. 모르는 것은 지어내지 말고 모른다고
적으라고 시킨다 -- 기존 17개 문서가 이미 그렇게 쓰여 있다("조문 원문에 명시되지 않음,
학설/판례 확인 필요"). 이것은 관문 이야기가 아니라 **무엇을 재료로 쓰라는 지시**다.
재료를 안 주면 모델이 기억에서 꺼내 오고, 그것이 법률 LLM 의 1위 실패 모드다
(Dahl 외 2024: 무작위 연방 판례 질문에 환각 58~88%).

## 모델

**Gemini 를 쓴다.** 산문이 토큰의 대부분이라 구독으로 청구할 자리가 아니다 --
`novel/` 이 디렉터만 Claude 로 두고 산문을 Gemini 로 돌리는 것과 같은 배치다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "법이론서"

SECTIONS = (
    "1. 왜 알아야 하는가",
    "2. 조문과 이론",
    "3. 핵심 법리",
    "4. 해석기법",
    "5. 실무상 흔한 오해",
    "6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)",
    "7. 연습 사실관계",
    "8. 다음 주제와의 연결",
)

_POOL = None


def _pool_ask(text: str) -> str:
    """기본 물음이. 후보 풀은 한 번만 세운다 -- build_pool 이 키마다 모델을 조회한다."""
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


def articles(statute: str, nums: list, corpus) -> list:
    """원장에서 조문 원문을 꺼낸다. **없는 것은 조용히 빼지 않고 말한다.**

    빼고 쓰면 모델은 그 조문을 기억에서 꺼내 오고, 그 문서는 원장에 없는 것을 근거로
    삼은 채 관문을 통과해 버린다 -- 대조할 수 없는 것이 대조된 척하는 자리다.
    """
    out, missing = [], []
    for n in nums:
        body = corpus.text(statute, str(n))
        (out.append((str(n), body)) if body else missing.append(str(n)))
    if missing:
        raise SystemExit(
            f"원장에 {statute} 제{'조, 제'.join(missing)}조 가 없다.\n"
            f"  python3 law/fetch.py {statute!r} 로 먼저 받아라.")
    return out


def prompt(statute: str, topic: str, arts: list, corpus=None) -> str:
    """**관문 이야기가 한 줄도 없다.** 조문과 무엇을 쓸 것인가뿐이다."""
    body = "\n\n".join(b for _, b in arts)
    via = []
    for n, _ in arts:
        for name, borrowed in (corpus.via(statute, n) if corpus else []):
            via.append(f"[{n}조가 끌어다 쓰는 {name}]\n{borrowed}")
    extra = ("\n\n## 위 조문이 끌어다 쓰는 조문\n\n" + "\n\n".join(via)) if via else ""
    names = "\n".join(f"## {s}" for s in SECTIONS)
    return f"""당신은 한국 법학 교재를 쓰는 저자입니다. 아래 조문 원문만을 재료로
'{topic}' 한 편을 씁니다.

## 재료 -- {statute}

{body}{extra}

## 재료를 벗어나지 않는 법

위 원문에 없는 것은 **지어내지 말고 모른다고 적으십시오.** 그 자리에는
"조문 원문에 명시되지 않음, 학설/판례 확인 필요" 라고 씁니다. 기억나는 판례나
학설이 있어도 적지 마십시오 -- 이 글의 근거는 위 원문뿐입니다.

조문을 부를 때는 `제216조` 처럼 번호로 부릅니다. 조문의 말을 옮길 때는 원문의
낱말을 그대로 씁니다.

## 형식

맨 위에 front-matter 를 둡니다.

---
title: "{topic}"
domain: {_domain(statute)}
tags: [법이론서, {_domain(statute)}]
key_principle: "이 주제의 핵심을 한 문장으로"
source_statute: "{statute}"
---

그 아래 `# {topic}` 제목을 두고, 다음 여덟 절을 이 이름 그대로 순서대로 씁니다.

{names}

'6. 사례 적용' 과 '7. 연습 사실관계' 의 사실관계는 새로 지어낸 것이므로,
**각 사례 블록 안에** "(본 사례는 학습용으로 새로 창작한 가상의 사실관계이며
실제 판례가 아님)" 이라고 적습니다. 절 제목에만 적지 말고 블록마다 적으십시오.

마크다운 본문만 출력하십시오. 다른 말은 붙이지 마십시오."""


def _domain(statute: str) -> str:
    return {"민법": "01_민법총칙", "형법": "04_형법각론",
            "민사소송법": "05_민사소송법", "형사소송법": "06_형사소송법",
            "대한민국헌법": "07_헌법", "헌법": "07_헌법",
            "도시 및 주거환경정비법": "03_도시정비법"}.get(statute, "00_기타")


_FENCE = re.compile(r"^\s*```(?:markdown|md)?\s*\n|\n```\s*$")


def clean(text: str) -> str:
    """모델이 씌운 코드 울타리를 벗긴다. front-matter 가 `---` 라 울타리와 헷갈린다."""
    t = _FENCE.sub("", (text or "").strip())
    return t.strip() + "\n"


def write(statute: str, topic: str, nums: list, corpus=None,
          ask=None, out: Path | None = None) -> Path:
    corpus = corpus if corpus is not None else CP.load()
    arts = articles(statute, nums, corpus)
    text = clean((ask or _pool_ask)(prompt(statute, topic, arts, corpus)))
    d = (out or (OUT / _domain(statute) / "이론"))
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[\\/:*?\"<>|]", "", topic)
    n = len(list(d.glob("*.md"))) + 1
    path = d / f"{n:02d}_{safe}.md"
    path.write_text(text, encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="법이론서 한 편을 쓴다 (관문은 모른다)")
    ap.add_argument("statute", nargs="?", default="")
    ap.add_argument("topic", nargs="?", default="")
    ap.add_argument("articles", nargs="?", default="", help="쉼표로 (예: 216,218)")
    ap.add_argument("--계획", dest="plan", default="")
    ap.add_argument("--법", dest="only", default="", help="계획 중 이 법만")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--프롬프트만", dest="dry", action="store_true",
                    help="부르지 않고 프롬프트만 찍는다 -- 무엇을 주는지 눈으로 본다")
    a = ap.parse_args(argv)

    corpus = CP.load(a.corpus)
    jobs = []
    if a.plan:
        for row in json.loads(Path(a.plan).read_text(encoding="utf-8")):
            if a.only and row["법"] != a.only:
                continue
            jobs.append((row["법"], row["주제"], row["조문"]))
    elif a.statute and a.topic:
        jobs.append((a.statute, a.topic,
                     [x.strip() for x in a.articles.split(",") if x.strip()]))
    else:
        ap.error("법·주제·조문 을 주거나 --계획 을 주십시오")

    for statute, topic, nums in jobs:
        if a.dry:
            print(prompt(statute, topic, articles(statute, nums, corpus), corpus))
            print("=" * 70)
            continue
        p = write(statute, topic, nums, corpus)
        print(f"[씀] {p}  ({len(p.read_text(encoding='utf-8'))}자)")
    if not a.dry:
        print("\n이제 심판을 돌린다:  python3 law/gate.py 법이론서")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
