"""문장 리듬을 **재서** 판정한다 -- 프롬프트로 부탁하지 않고 숫자로 잡는다.

2026-09-04 실측(flow.json, 8,489자)에 대한 사용자 평은 셋이었다:

    "끝이 -다. 이거 너무 단조롭게 재미 없다고.
     문장이 너무 짧고 리듬감이 없다고.
     대사가 너무 작위적이고 딱딱하다고"

프롬프트에는 이미 다 적혀 있었다. `style.narrator()` 의 [리듬] 항목이 "짧은 '-다' 문장이
두 번 이어지면 셋째에서 바꿔라" 라고 말하고, `flow.write_prompt()` 도 "장문과 단문을
섞어라 ... 지금 이 규칙이 가장 자주 깨진다" 라고 말한다. **그런데도 깨졌다.** 부탁으로는
안 된다는 뜻이다.

그래서 여기서는 잰다. 세 가지를 세고, 넘으면 그 숫자를 그대로 모델에게 돌려준다:

  · **'-다' 종결 비율**과 연속 횟수 -- 단조로움의 정체는 대개 이것이다
  · **긴 문장의 몫** -- 단문만 이어지면 리듬이 아니라 목록이 된다
  · **대사의 몫** -- 대사가 없으면 '-다' 를 깰 수단 하나가 통째로 빠진다

판정은 **무르게** 한다. 이건 취향의 영역이고, 자유도가 이 모드의 전부다. 그래서 리듬은
모순과 달리 **원고를 죽이지 않는다** -- 다시 써보라고 하되, 끝내 안 고쳐지면 제일 나은
것을 채택한다(`flow.step`). 기각이 잦으면 그 자유가 먼저 죽는다.
"""
from __future__ import annotations

import re

# 문장 끝 '-다'. 닫는 따옴표나 괄호가 뒤에 붙어도 '-다' 로 센다.
#
# **'-다' 자체는 죄가 없다.** 기준으로 삼은 하루키 예문(style.py 의 [상황]/[점층])을 재보면
# 서술문의 86%가 '-다' 로 끝나고 여섯 문장이 내리 이어진다. 그런데 그건 단조롭지 않다 --
# 그 '-다' 중 71%가 마흔 자를 넘는 긴 문장이기 때문이다.
#
# 단조로움의 정체는 종결어미가 아니라 **길이**다. 짧은 '-다' 가 줄줄이 이어질 때 목록처럼
# 읽힌다. 그래서 여기서 세는 것은 '-다' 가 아니라 **짧은 '-다'** 다.
_DA = re.compile(r"다[.!?…”\"')\]]*$")
_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_QUOTE = re.compile(r"[\"“'']")

# 긴 문장의 기준. 하루키 예문("서른일곱 살이던 그때, 나는 좌석에 앉아 있었다. 그 거대한
# 비행기는 두터운 비구름을 뚫고 내려와, 함부르크 공항에 착륙을 시도하고 있었다.")의
# 둘째 문장이 마흔 몇 자다. 그 정도가 한 번씩 섞여야 리듬이 산다.
LONG = 45

# **점층** -- 앞 문장을 받아 한 단계 올리는 문장. 이것이 이 문체의 뼈다.
#
# 지금까지 프롬프트에만 적혀 있었다(style.py [점층]). 이 세션에서 확인된 것이 하나 있다면
# **재지 않는 것은 안 지켜진다**는 것이다. 그래서 센다.
#
# 요구량은 **분량에 비례한다.** 짧은 글에 세 번을 요구하면 그건 자가 아니라 억지다.
#
# 완벽한 판정은 못 한다. 점층인지 아닌지는 뜻의 문제라 기계가 못 본다. 그러나 한국어에서
# 앞 문장을 받아 올리는 문장은 **첫머리에 자국을 남긴다** -- 고쳐 말하거나("아니,",
# "정확히 말하자면"), 더 얹거나("게다가", "그것도"), 앞 것을 지시어로 받거나("그것은",
# "그 소리는"). 그 자국을 센다. 자국 없이 점층한 문장은 놓치지만, 그건 무른 자의 몫이다.
_CLIMB = (
    "아니", "아니,", "정확히", "그보다", "차라리", "오히려", "실은", "사실",
    "게다가", "더구나", "심지어", "그것도", "그리고 그", "그래서 그", "거기다",
    "그런데 그", "그래도", "다만", "물론", "적어도", "하필", "그중에서도",
    "말하자면", "굳이 말하자면", "요컨대", "결국", "무엇보다",
)
# 앞 문장을 지시어로 받는 첫머리. "그" + 한두 글자 명사 + 조사.
_ANAPHOR = __import__("re").compile(r"^(그것|그건|그게|그 [가-힣]{1,4}[은는이가도을를])")

LIMITS = {
    "da":   0.62,   # **짧은** '-다' 가 이보다 많으면 단조롭다 (하루키 예문은 14%)
    "run":  4,      # 짧은 '-다' 가 이만큼 내리 이어지면 끊어야 한다
    "long": 0.15,   # 긴 문장이 이보다 적으면 목록처럼 읽힌다
    "climb": 5,     # **서술문 이만큼마다 하나**는 앞 문장을 받아 올려야 한다
    "talk": 0.10,   # 대사가 이보다 적으면 '-다' 를 깰 수단이 하나 빠진 것이다
}


def _lines(text: str) -> tuple[list[str], list[str]]:
    """서술문과 대사줄로 가른다."""
    talk, tell = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _QUOTE.match(line):
            talk.append(line)
            continue
        for s in _SPLIT.split(line):
            s = s.strip()
            if s:
                tell.append(s)
    return tell, talk


def climb(text: str) -> int:
    """앞 문장을 받아 한 단계 올린 문장의 수."""
    tell, _ = _lines(text)
    n = 0
    for i, sent in enumerate(tell):
        if i == 0:
            continue
        head = sent.lstrip()
        if _ANAPHOR.match(head) or any(head.startswith(m) for m in _CLIMB):
            n += 1
    return n


def measure(text: str) -> dict:
    tell, talk = _lines(text)
    if not tell:
        return {"da": 0.0, "run": 0, "long": 0.0, "talk": 0.0, "n": 0}

    # 짧으면서 '-다' 로 끝나는 것만 센다. 긴 '-다' 는 리듬을 죽이지 않는다.
    da = [bool(_DA.search(s)) and len(s) < LONG for s in tell]
    run = best = 0
    for hit in da:
        run = run + 1 if hit else 0
        best = max(best, run)

    total = len(tell) + len(talk)
    return {
        "climb": climb(text),
        "da":   sum(da) / len(tell),
        "run":  best,
        "long": sum(len(s) >= LONG for s in tell) / len(tell),
        "talk": len(talk) / total if total else 0.0,
        "n":    len(tell),
    }


def check(text: str) -> list[str]:
    """넘은 것만 사람 말로 돌려준다. 빈 목록이면 리듬은 괜찮다."""
    m = measure(text)
    if m["n"] < 6:                       # 너무 짧으면 통계가 의미 없다
        return []

    out = []
    if m["da"] > LIMITS["da"]:
        out.append(f"서술문 {m['n']}개 중 {m['da']:.0%}가 **짧은 '-다'** 로 끝난다. "
                   f"{LIMITS['da']:.0%} 아래로 내려라 -- 명사로 끝내거나, 말줄임으로 두거나, "
                   f"'-까/-지/-군/-는 것'으로 바꾸거나, 대사로 받아라")
    if m["run"] > LIMITS["run"]:
        out.append(f"짧은 '-다' 문장이 내리 {m['run']}번 이어진 자리가 있다. "
                   f"{LIMITS['run']}번을 넘기지 마라 -- 세 번째나 네 번째에서 생각을 붙이거나, "
                   f"대사를 넣거나, 문장을 끝내지 마라")
    want = max(1, m["n"] // LIMITS["climb"])
    if m["climb"] < want:
        out.append(f"앞 문장을 받아 올리는 문장이 {m['climb']}개다. 서술문 {m['n']}개면 "
                   f"{want}개는 있어야 한다 -- **문장은 낱개로 서 있으면 안 된다.** 한 문장을 놓았으면 다음 "
                   f"문장이 그것을 **더 좁히거나, 더 키우거나, 뒤집어야** 한다. "
                   f"'아니,' '정확히 말하자면,' '그것도' '그 소리는' 으로 앞 문장을 받아라. "
                   f"그러다 끊고 다음으로 넘어가라")

    if m["long"] < LIMITS["long"]:
        out.append(f"{LONG}자 넘는 문장이 {m['long']:.0%}뿐이다. "
                   f"{LIMITS['long']:.0%}는 넘겨라 -- 짧은 문장 서넛에 하나씩은 쉼표로 이어 붙인 "
                   f"긴 문장이 와야 한다. 단문만 이어지면 리듬이 아니라 목록이다")
    if m["talk"] < LIMITS["talk"]:
        out.append(f"대사가 전체 줄의 {m['talk']:.0%}뿐이다. "
                   f"{LIMITS['talk']:.0%}는 넘겨라 -- 사람을 만나게 하고 말을 시켜라")
    return out


def score(text: str) -> float:
    """넘은 정도의 합. 낮을수록 좋다 -- 끝내 못 고쳤을 때 고르는 기준이다."""
    m = measure(text)
    return (max(0, max(1, m["n"] // LIMITS["climb"]) - m["climb"]) * 0.12
            + max(0.0, m["da"] - LIMITS["da"])
            + max(0, m["run"] - LIMITS["run"]) * 0.05
            + max(0.0, LIMITS["long"] - m["long"])
            + max(0.0, LIMITS["talk"] - m["talk"]))
