"""**목소리를 재는 자** -- 문장도 사건도 아닌 것들.

문장(문면)과 사건(서사)을 다 맞춰도 다른 글이 되는 자리가 있다. 누가 말하고 있는가,
어느 시제로 보는가, 무엇에 빗대는가, 어느 감각으로 쓰는가, 사람을 무엇이라 부르는가.
읽는 사람이 "문체" 라고 부르는 것의 절반이 여기다.

**전부 정규식이다. LLM 호출 0회.** 의미를 안 읽고 표지만 센다 -- 거칠지만 셀 수 있고,
셀 수 있으면 자가 되고, 자가 되면 시킬 수 있다.

거친 것은 거칠다고 적어 둔다. `주어없음` 은 주격 표지가 안 보이는 문장을 셀 뿐
진짜 주어 생략과 다르고, `감각` 은 낱말 사전이 작아서 몫이 아니라 **비**로만 뜻이 있다.
"""
from __future__ import annotations

import re
from collections import Counter

# 시제. 한국어 서사에서 과거형과 현재형은 서술의 거리를 통째로 바꾼다.
_PAST = re.compile(r"(았|었|였)(다|고|지만|는데|으며|다가)[.\s\"”']")
_PRES = re.compile(r"[가-힣](ㄴ다|는다)[.\s\"”']")
# 인칭. 서술자가 판 안에 있는가 밖에 있는가.
_FIRST = re.compile(r"\b(나는|내가|나를|나의|내|우리는|우리가)\b")
_THIRD = re.compile(r"\b(그는|그가|그를|그의|그녀는|그녀가|그녀를|그녀의)\b")
# 존대 서술. 서술문 자체가 높임인가.
_POLITE = re.compile(r"(습니다|ㅂ니다|입니다|였습니다|해요|이에요|예요)[.!?\s]")
# 비유. **직유는 셀 수 있다** -- 문체의 지문 가운데 제일 싸게 잡히는 것.
_SIMILE = re.compile(r"(같이|같은|같았|처럼|듯이|듯한|듯했|마냥|인 양)")
# 부정.
_NEG = re.compile(r"(안 |못 |지 않|지 못|없|아니)")
# 피동·사동. 번역투와 토박이 문장을 가르는 자리.
# **거친 근사다.** '-되다 · -어지다' 는 확실하고, '-히/리/기' 는 종결꼴만 본다
# (닫혔다 · 열렸다 · 안겼다). 자동사가 몇 개 섞이지만 같은 자로 표본과 원고를 함께
# 재므로 견주는 데는 쓸 수 있다.
_PASSIVE = re.compile(r"[가-힣](되었|되는|된다|된 |어졌|아졌|해졌|워졌|혔다|렸다|겼다)")
# 문두 접속부사. 문장을 무엇으로 잇는가 -- 절로 잇는 것(glue)과 다른 자리다.
_CONJ = re.compile(r"^(그러나|그리고|하지만|그런데|그래서|그러자|그러면|그런|또|또한|"
                   r"게다가|다만|물론|어쨌든|결국)\b")
# 때를 가리키는 표지.
_TIME = re.compile(r"(그날|이튿날|다음 ?날|어제|오늘|내일|아침|낮|저녁|밤|새벽|"
                   r"한참|이윽고|잠시|얼마 뒤|그때|그동안|요즘|언젠가)")
# 주격 표지가 안 보이는 문장. **진짜 주어 생략과 다르다** -- 거친 근사다.
_SUBJ = re.compile(r"[가-힣]+(은|는|이|가)\s")
# 첩어(의성·의태의 큰 몫). 두 글자가 되풀이되는 꼴.
_MIMIC = re.compile(r"([가-힣]{2})\1")

# 감각. **사전이 작다** -- 몫의 절대값이 아니라 감각끼리의 비로만 본다.
SENSE = {
    "eye":  ("보|바라보|눈|빛|어둠|그림자|색|하얀|검은|붉은|푸른|비치|번쩍|반짝"),
    "ear":  ("듣|들리|소리|목소리|울리|조용|시끄|고요|웅성|삐걱|쿵|딸깍"),
    "nose": ("냄새|향|비린|퀴퀴|매캐|향기|악취"),
    "skin": ("차갑|뜨겁|따뜻|서늘|축축|메마|아프|저리|간지|무겁|딱딱|부드럽"),
    "tongue": ("맛|달|쓰|짜|시큼|삼키|씹|목이 마|허기"),
}
_SENSE = {k: re.compile(v) for k, v in SENSE.items()}


def _sent(text: str) -> list:
    from novel import rhythm
    tell, _talk = rhythm._lines(text)
    return [s for s in tell if s.strip()]


def measure(text: str) -> dict:
    """목소리 축. 문장이 없으면 빈 것을 돌려준다 -- 0 으로 채우면 거짓이 된다."""
    sents = _sent(text)
    if not sents:
        return {}
    n = len(sents)
    chars = max(1, len(text))
    past = len(_PAST.findall(text))
    pres = len(_PRES.findall(text))
    first = len(_FIRST.findall(text))
    third = len(_THIRD.findall(text))
    out = {
        "polite": len(_POLITE.findall(text)) / n,
        # **직유의 밀도.** 문장 백 개당 몇 번 빗대는가.
        "simile": len(_SIMILE.findall(text)) / n,
        "neg": len(_NEG.findall(text)) / n,
        "passive": len(_PASSIVE.findall(text)) / n,
        "conj_head": sum(1 for s in sents if _CONJ.match(s)) / n,
        "timeword": len(_TIME.findall(text)) / (chars / 1000),
        # 주격 표지가 안 보이는 문장의 몫. 거친 근사.
        "nosubj": sum(1 for s in sents if not _SUBJ.search(s)) / n,
        "mimic": len(_MIMIC.findall(text)) / (chars / 1000),
    }
    # **자국이 하나도 없으면 그 축은 안 낸다.** 0 으로 채우면 "현재형을 안 쓴다" 와
    # "시제를 알 수 없다" 가 같은 값이 되고, 그 0 들이 폭을 아래로 끌어내린다.
    if past + pres:
        out["tense_now"] = pres / (past + pres)
    if first + third:
        out["person_1"] = first / (first + third)

    # 감각의 비. 다섯을 합해 1이 되게 나눈다 -- 사전 크기에 안 흔들리게.
    c = {k: len(rx.findall(text)) for k, rx in _SENSE.items()}
    tot = sum(c.values())
    if tot:
        for k, v in c.items():
            out["sense_" + k] = v / tot
    return out


def axes() -> list:
    """이 자가 내는 축 이름."""
    return sorted(measure("그는 걸었다. 나는 보았다. 그리고 그날 하얀 빛이 "
                          "눈처럼 쏟아졌다. 춥지 않았다.").keys())


SAY = {
    "tense_now": "현재형으로 쓴 서술의 몫",
    "person_1": "'나' 로 쓴 대목의 몫",
    "polite": "높임으로 끝나는 서술문의 몫",
    "simile": "문장 하나당 빗대는 횟수",
    "neg": "'안 · 못 · 없다' 가 든 문장의 몫",
    "passive": "피동으로 쓴 문장의 몫",
    "conj_head": "'그러나 · 그래서' 로 문장을 여는 몫",
    "timeword": "천 자당 때를 가리키는 말의 수",
    "nosubj": "주어를 안 세운 문장의 몫",
    "mimic": "천 자당 첩어의 수",
    "sense_eye": "감각 가운데 눈의 몫",
    "sense_ear": "감각 가운데 귀의 몫",
    "sense_nose": "감각 가운데 코의 몫",
    "sense_skin": "감각 가운데 살갗의 몫",
    "sense_tongue": "감각 가운데 입의 몫",
}
