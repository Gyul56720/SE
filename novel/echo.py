"""**메아리** -- 앞에 쓴 문장을 그대로 다시 뱉는 것을 잡는다.

실측(2026-09-04, flow3.json): 한 덩어리 2,024자 중 **610자(30%)가 글자 하나 안 틀리고
반복**이었다. 대사 일곱 줄과 서술 일곱 줄이 통째로 두 번 나온다.

    "그 영감탱이가 아직도 숨이 붙어 있단 말이지?"   ← 2회
    "가시죠." / "어디로?" / "올라프손의 병원으로요…"  ← 전부 2회

왜 생기나. 다음 덩어리에게는 꼬리 1,200자가 `[지금까지의 끝부분]` 으로 넘어간다. 모델은
그것을 **참고**가 아니라 **이어 붙일 원고**로 읽고, 받은 것을 먼저 다시 적은 뒤 이어
간다. 덩어리 안에서도 같은 일이 생긴다 -- 길이를 채우려고 앞 문단을 복사한다.

이것은 취향이 아니라 결함이다. 모순과 같은 급으로 다룬다. 다만 순서가 있다:

  1. **잘라낸다.** 꼬리를 그대로 옮겨 적은 앞부분은 호출을 다시 쓰지 않고 도려낸다.
     이건 판정할 것도 없다 -- 이미 원고에 있는 글자다.
  2. 그러고도 남은 반복은 **기각한다.** 잘라내기로 못 고치는 것은 덩어리 안에서 스스로
     복사한 경우인데, 그건 글의 뼈대가 그렇게 짜였다는 뜻이라 다시 받아야 한다.

문장 부호와 공백만 다른 것도 같은 것으로 본다. 사람 눈에 같으면 같은 것이다.
"""
from __future__ import annotations

import re

# 이만큼 이어지는 글자가 똑같으면 우연이 아니다. 한국어 한 문장이 대개 이보다 길다.
SHINGLE = 40
# 덩어리의 이만큼이 반복이면 기각한다. 0 이 아닌 이유는 관용구·인물의 말버릇 때문이다
# ("난 안 가" 를 두 번 말하는 것은 반복이 아니라 성격이다).
TOLERANCE = 0.06

_NORM = re.compile(r"[\s“”\"'‘’.,!?…·\-—~()\[\]]+")


def _norm(s: str) -> str:
    return _NORM.sub("", s)


def _shingles(s: str, n: int = SHINGLE) -> set[str]:
    return {s[i:i + n] for i in range(0, max(0, len(s) - n + 1))}


def trim(text: str, prev: str) -> tuple[str, int]:
    """꼬리를 그대로 옮겨 적은 앞부분을 도려낸다. (남은 글, 잘라낸 글자수)

    줄 단위로 본다. 새 글의 첫 줄들이 앞 글에 그대로 있으면 그만큼 버린다. 중간에 한 줄쯤
    달라도 멈추지 않는다 -- 모델은 옮겨 적으면서 조사 하나를 바꾸기도 한다.
    """
    if not prev:
        return text, 0
    lines = text.splitlines()
    seen = _norm(prev)
    cut = 0
    for i, line in enumerate(lines):
        n = _norm(line)
        if not n:
            cut = i + 1
            continue
        if len(n) >= 8 and n in seen:
            cut = i + 1
        elif i - cut > 2:                 # 새 내용이 세 줄 넘게 이어지면 거기서부터가 본문
            break
    if not cut:
        return text, 0
    kept = "\n".join(lines[cut:]).lstrip()
    dropped = len(text) - len(kept)
    return kept, dropped


def echoed(text: str, prev: str) -> float:
    """앞 글에 이미 있던 글자의 비율."""
    a, b = _norm(text), _norm(prev)
    if len(a) < SHINGLE or not b:
        return 0.0
    hit = sum(1 for sh in _shingles(a) if sh in b)
    return hit / max(1, len(_shingles(a)))


def selfish(text: str) -> tuple[float, list[str]]:
    """덩어리가 **스스로** 복사한 비율과 그 예."""
    lines = [l.strip() for l in text.splitlines() if len(_norm(l)) >= 12]
    seen, dup = {}, []
    for l in lines:
        n = _norm(l)
        if n in seen:
            dup.append(l)
        seen[n] = 1
    if not lines:
        return 0.0, []
    repeated = sum(len(l) for l in dup)
    total = sum(len(l) for l in lines)
    return (repeated / total if total else 0.0), dup


def check(text: str, prev: str) -> list[str]:
    """잘라내기로 못 고치는 반복만 돌려준다."""
    out = []
    rate, dup = selfish(text)
    if rate > TOLERANCE:
        out.append(f"이 덩어리가 자기 문장을 그대로 복사했다 -- 전체의 {rate:.0%}. "
                   f"똑같이 적힌 줄이 {len(dup)}개다. 예: “{dup[0][:40]}…” "
                   f"**앞에 쓴 것을 다시 적지 마라.** 분량이 모자라면 새 일이 일어나게 해라")
    back = echoed(text, prev)
    if back > 0.25:
        out.append(f"앞 글에 이미 있던 문장이 이 덩어리의 {back:.0%}다. "
                   f"[지금까지의 끝부분]은 **읽으라고 준 것이지 옮겨 적으라고 준 것이 아니다.** "
                   f"그 다음 문장부터 시작해라")
    return out
