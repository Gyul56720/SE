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

import os
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


# **되풀이는 글자가 아니라 상황에서도 난다.** 낱말을 바꿔 쓰면 위의 자들은 다 통과하는데
# 읽는 사람에게는 아까 그 장면이다. 짧은 조각으로 견주면 그것이 잡힌다 -- 40자는 통째로
# 베낀 것을 잡는 자이고, 이쪽은 **바꿔 쓴 것**을 잡는 자다.
SAMEY = int(os.environ.get("DRIFT_SAMEY", "12"))
SAMEY_MAX = float(os.environ.get("DRIFT_SAMEY_MAX", "0.45"))


def _bag(s: str) -> set:
    """낱말 뭉치. 조사와 어미가 붙는 말이라 **앞 두세 글자**로 자른다 -- '공장에서' 와
    '공장은' 을 같은 것으로 보려는 것이다."""
    out = set()
    for w in re.findall(r"[가-힣A-Za-z0-9]+", s):
        if len(w) >= 2:
            out.add(w[:3] if len(w) >= 4 else w)
    return out


def samey(text: str, prev: str) -> float:
    """앞 글과 **얼마나 비슷한가.** 글자를 이어 붙여 견주지 않고 **낱말 뭉치**로 견준다 --
    되풀이는 대개 순서를 바꿔 오기 때문이다. 이어 붙인 조각으로 보면 '항구에서 도영을
    만나' 와 '도영을 항구에서 만나' 가 남남으로 나온다."""
    a, b = _bag(text), _bag(prev)
    if len(a) < 8 or not b:
        return 0.0
    return len(a & b) / len(a)


def check(text: str, prev: str) -> list[str]:
    """잘라내기로 못 고치는 반복만 돌려준다."""
    out = []
    rate, dup = selfish(text)
    if rate > TOLERANCE:
        out.append(f"이 덩어리가 자기 문장을 그대로 복사했다 -- 전체의 {rate:.0%}. "
                   f"똑같이 적힌 줄이 {len(dup)}개다. 예: “{dup[0][:40]}…” "
                   f"**앞에 쓴 것을 다시 적지 마라.** 분량이 모자라면 새 일이 일어나게 해라")
    # **선 채로 서 있는 지시 대신 재서 말한다.** "같은 장면을 또 쓰지 마라" 를 프롬프트에
    # 박아 두면 매 덩어리가 그 말을 듣는다 -- 겹치지 않은 덩어리까지 그 말을 듣는다.
    # 겹쳤을 때만, 얼마나 겹쳤는지와 함께 말한다.
    same = samey(text, prev)
    if same > SAMEY_MAX:
        out.append(f"이 대목이 앞과 {same:.0%} 겹친다 -- 자리도 사람도 얘기도 아까 그것이다. "
                   f"한 걸음 나가거나, 다른 데로 새거나, 조건 하나를 바꿔라")
    back = echoed(text, prev)
    if back > 0.25:
        out.append(f"앞 글에 이미 있던 문장이 이 덩어리의 {back:.0%}다. "
                   f"[지금까지의 끝부분]은 **읽으라고 준 것이지 옮겨 적으라고 준 것이 아니다.** "
                   f"그 다음 문장부터 시작해라")
    return out
