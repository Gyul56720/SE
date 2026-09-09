"""**만화 식 소설 -- 문체가 실제로 그렇게 나왔는지 잰다.**

사용자(2026-09-09): "실제 만화를 쓸건 아니야. **만화 식 소설**을 쓸거야."

## 왜 있나

`style.MANGA` 가 만화 식 문체를 **시킨다**. 그런데 시키는 것과 나오는 것은 다르다.
이 저장소가 실측으로 배운 것이 그것이다 -- 서브플롯 프롬프트에 "겹치지 마라" 를 넣어도
절반쯤만 지켜졌고, 그래서 분량 배분은 지시가 아니라 **코드가** 맡게 됐다(`style.py` 머리).

만화 식 문체에는 **셀 수 있는 것이 셋** 있다. 로판과 만화 식이 갈리는 자리가 정확히 여기다.

    대사 비율     만화는 대사가 민다. 로판은 지문이 밀고 대사가 얹힌다
    지문 길이     만화의 지문은 그림이 하던 일이라 짧다. 길어지는 순간 만화가 아니다
    짧은 문단     여백과 의성어. 채우지 않는 자리가 있어야 컷이 된다

셋 다 취향이 아니라 수다. 그래서 여기서 잰다.

## 재기만 한다 -- 기각하지 않는다

**`gate.py` 가 문장 리듬 검사(V020)를 뺀 이유를 되풀이하지 않는다.** 거기 적혀 있다:
관문이 작가가 되면 그 자리를 통과하려고 원고가 균질해진다. 대사 비율을 하드로 걸면
모델이 비율을 맞추려고 의미 없는 대사를 끼워 넣는다 -- 재려던 것이 목표가 되는 순간
그 수는 죽는다.

그래서 `fit()` 은 **soft 만** 낸다. 쓰는 것을 막지 않고, 튜닝할 때 보는 눈금이 된다.
이것이 SUCCESS.md 가 말하는 목적함수 쪽이지 관문 쪽이 아니다.

## 만화를 그리는 것이 아니다

쪽 · 넘김의 홀짝 · 노드 같은 **인쇄의 규율은 여기 없다.** 산문에는 쪽이 없다. 만화가
장을 넘겨서 하던 일(반전을 넘김 뒤에 두기)은 산문에서 **대목의 사이**가 하고, 그것은
`style.MANGA` 의 [끊기] 가 시킨다. 그리는 쪽의 규율은 `MANGA.md` 에 문서로만 있다.

실행:

    python3 -m novel.manga --book novel/drift.json          # 마지막 덩어리 셋을 잰다
    python3 -m novel.manga --book novel/drift.json --전부
"""
from __future__ import annotations

import json
import re

from novel.gate import Violation

# 대사가 분량에서 차지하는 몫. 만화는 대사가 민다.
TALK_MIN = 0.35
# 지문 한 문단의 길이. 넘으면 그림이 하던 일을 글이 설명하고 있는 것이다.
NARR_MAX = 200
# 짧은 문단(여백 · 의성어 · 한 줄 반응)이 차지하는 몫.
SOLO_MAX_LEN = 30
SOLO_MIN = 0.08

# 대사. 큰따옴표 · 겹낫표 · 홑낫표를 다 본다.
_TALK = re.compile(r'"[^"\n]*"|“[^”\n]*”|「[^」\n]*」|『[^』\n]*』')


def paragraphs(text: str) -> list:
    """문단. 웹소설 꼴이라 **줄 하나가 문단 하나**다 -- 빈 줄로도, 한 줄로도 나뉜다."""
    return [ln.strip() for ln in re.split(r"\n+", text or "") if ln.strip()]


def is_talk(p: str) -> bool:
    """대사 문단인가. 따옴표 안이 문단의 절반을 넘으면 대사로 친다."""
    inside = sum(len(m.group()) for m in _TALK.finditer(p))
    return bool(p) and inside * 2 > len(p)


def measure(text: str) -> dict:
    """센다. **판정하지 않는다.**"""
    ps = paragraphs(text)
    n = len("".join(ps))
    talk_chars = sum(len(m.group()) for m in _TALK.finditer("\n".join(ps)))
    narr = [p for p in ps if not is_talk(p)]
    solo = [p for p in ps if len(p) <= SOLO_MAX_LEN]
    return {
        "문단": len(ps),
        "글자": n,
        "대사비율": (talk_chars / n) if n else 0.0,
        "대사문단": sum(1 for p in ps if is_talk(p)),
        "지문평균": (sum(len(p) for p in narr) / len(narr)) if narr else 0.0,
        "지문최장": max((len(p) for p in narr), default=0),
        "긴지문": sum(1 for p in narr if len(p) > NARR_MAX),
        "짧은문단": (len(solo) / len(ps)) if ps else 0.0,
    }


def fit(text: str) -> list:
    """만화 식에서 얼마나 벗어났나. **전부 soft 다 -- 기각 권한이 없다.**

    하드를 만들지 않는 이유는 위 문서에 있다(gate.py 의 V020 이 겪은 것)."""
    m, vs = measure(text), []
    if m["글자"] < 200:
        return vs                       # 너무 짧으면 비율이 뜻을 잃는다
    if m["대사비율"] < TALK_MIN:
        vs.append(Violation("M201", "soft", "대사",
                            f"대사가 {m['대사비율']:.1%}다 (만화 식은 {TALK_MIN:.0%} 이상)"
                            " -- 지문이 밀고 있다. 사건을 말과 동작으로 굴려라"))
    if m["긴지문"]:
        vs.append(Violation("M202", "soft", "지문",
                            f"{NARR_MAX}자 넘는 지문 문단이 {m['긴지문']}개 (최장 {m['지문최장']}자)"
                            " -- 그림이 하던 일을 글이 설명하고 있다"))
    if m["짧은문단"] < SOLO_MIN:
        vs.append(Violation("M203", "soft", "여백",
                            f"짧은 문단이 {m['짧은문단']:.1%}다 ({SOLO_MIN:.0%} 이상)"
                            " -- 여백과 의성어가 없다. 다 채우면 컷이 안 생긴다"))
    return vs


def report(text: str) -> str:
    m = measure(text)
    vs = fit(text)
    rows = [f"만화 식 -- {m['글자']:,}자 · 문단 {m['문단']}개",
            f"  대사 비율   {m['대사비율']:>6.1%}  (목표 {TALK_MIN:.0%} 이상)"
            f"   · 대사 문단 {m['대사문단']}/{m['문단']}",
            f"  지문 평균   {m['지문평균']:>6.0f}자  (최장 {m['지문최장']}자 · {NARR_MAX}자 초과 {m['긴지문']}개)",
            f"  짧은 문단   {m['짧은문단']:>6.1%}  (목표 {SOLO_MIN:.0%} 이상 · {SOLO_MAX_LEN}자 이하)"]
    rows.append("")
    rows += [f"  {v}" for v in vs] or ["  만화 식으로 나왔다."]
    return "\n".join(rows)


# ---------------------------------------------------------------- CLI

def main() -> int:
    import argparse
    import sys
    from pathlib import Path

    ap = argparse.ArgumentParser(description="원고가 만화 식으로 나왔는지 잰다")
    ap.add_argument("--book", default="novel/drift.json")
    ap.add_argument("--덩어리", dest="k", type=int, default=3, help="마지막 몇 덩어리")
    ap.add_argument("--전부", dest="all", action="store_true")
    a = ap.parse_args()

    p = Path(a.book)
    if not p.exists():
        print(f"원고가 없다: {p}", file=sys.stderr)
        return 1
    chunks = (json.loads(p.read_text(encoding="utf-8")).get("chunks") or [])
    if not chunks:
        print("원고에 덩어리가 없다", file=sys.stderr)
        return 1
    use = chunks if a.all else chunks[-max(1, a.k):]
    print(f"[{p}] 덩어리 {len(use)}/{len(chunks)}개")
    print()
    print(report("\n".join(use)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
