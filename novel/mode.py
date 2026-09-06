"""**프롬프트를 말하기의 갈래로 나눈다** -- 덩어리가 아니라 지금 무엇을 쓰는 중이냐로.

(이름이 mode 인 것은 state.py 가 이미 오케스트레이션의 세계 상태이기 때문이다.
여기서 말하는 "상태" 는 줄 하나가 지금 어떤 말하기냐다.)

문제. 프롬프트가 하나면 한 덩어리 안에서 묘사도 대사도 전환도 같은 요구를 받는다.
그런데 작품마다 다른 것은 "묘사를 몇 줄 하다가 대사로 넘어가고 몇 턴 주고받다가 다시
묘사로 돌아오는가" 이고, 그것은 덩어리 단위로는 안 잡힌다.

그래서 줄을 다섯 상태로 보고, **표본에서 그 상태들이 어떻게 이어지는지**를 배운다.

    묘사  밖과 사람을 그린다
    대사  따옴표 안
    전환  자리나 때가 옮겨 간다
    내면  속으로 생각한다
    맺음  대목을 닫는다

배우는 것은 둘이다. **전이**(묘사 다음에 무엇이 오는가)와 **머무름**(한 상태에 몇 줄
있는가). 이 둘이면 그 작품의 호흡을 그릴 수 있다. LLM 호출은 0회다 -- 전부 정규식이다.

쓸 때는 다음 덩어리가 밟을 상태 열을 뽑아 프롬프트에 준다. 상태마다 볼 축이 다르므로
**상태가 바뀌면 프롬프트도 바뀐다.**
"""
from __future__ import annotations

import hashlib
import os
import re
from collections import Counter

STATES = ("묘사", "대사", "전환", "내면", "맺음")

# 배운 것을 두는 자리. targets.json 이 "얼마나" 라면 이쪽은 "무엇 다음에 무엇" 이다.
PATH = os.environ.get("DRIFT_MODES", str(
    __import__("pathlib").Path(__file__).resolve().parent / "modes.json"))

_QUOTE = re.compile(r'^\s*[\"“‘\'(\[]')
# 자리·때가 옮겨 가는 자국. profile._SCENE 과 같은 결이되 줄 첫머리를 본다.
_MOVE = re.compile(
    r"(다음 ?날|이튿날|그날|아침|저녁|밤|새벽|한참|얼마 뒤|잠시 뒤|이윽고|그리고 나서|"
    r"도착|들어서|나와서|나서자|돌아와|올라가|내려가|건너|향해|떠나|출발|들어갔|나갔)")
# 속으로 생각하는 자국. 따옴표 없이 의문·추측·회상으로 도는 문장.
_INNER = re.compile(
    r"(생각했|떠올렸|싶었|것 같았|모르겠|기억|왜 그런|어쩌면|아마도|하고 싶|두려웠|"
    r"라고 여겼|자문|되뇌)")

# 상태마다 프롬프트에서 볼 축. **여기 없는 축은 그 상태에서 안 싣는다** -- 대사를
# 쓰는 중에 문단 길이를 말해 봐야 지켜지지 않는다.
WATCH = {
    "묘사": ("sent_len", "sent_var", "long", "short", "outside", "scene",
             "para_len", "glue", "climb",
             "simile", "sense_eye", "sense_ear", "sense_skin", "nosubj"),
    # 이음 축(dialog · t2t · n2t · tag_rate · talk_run · rally)은 글 전체에서 재고,
    # 줄의 성질(길이 · 물음 · 말끝 · 낱말)은 대사 줄만 모아서 잰다.
    "대사": ("dialog", "t2t", "n2t", "tag_rate", "talk_len2", "talk_run",
             "rally", "q_rate", "ell_rate", "talk_len",
             "sent_len", "short", "end_var", "ttr", "comma", "josa_rate",
             "polite", "neg"),
    "전환": ("scene", "para_len", "short", "clock", "sent_len",
             "timeword", "conj_head"),
    "내면": ("da_share", "end_var", "end_var2", "sent_len", "glue", "ttr",
             "tense_now", "person_1", "neg", "nosubj"),
    "맺음": ("close_t", "short", "sent_len", "askrate"),
}
# 상태마다 무엇을 하라는 한 줄. **데이터로 빼지 않은 유일한 문장** -- 이건 축의 설명이
# 아니라 상태의 정의라서 directives 와 결이 다르다.
SAY = {
    "묘사": "지금은 **보이는 것**을 쓴다. 이름과 수를 대고, 눈이 옮겨 가는 순서대로.",
    "대사": "지금은 **말**이다. 주고받게 하고, 지문은 표본이 붙이는 만큼만 붙인다.",
    "전환": "지금은 **옮겨 가는 자리**다. 짧게 끊고, 언제 어디로 갔는지 대라.",
    "내면": "지금은 **속말**이다. 감정에 이름을 붙이지 말고 무엇을 떠올렸는지 써라.",
    "맺음": "지금은 **닫는 자리**다. 다 보여주고 닫지 마라 -- 한 박 먼저 멈춘다.",
}


# 갈래별로 따로 재면 안 되는 축. **이음은 갈래를 섞어야 나오는 수다** -- 대사 줄만
# 모아 놓고 "지문 다음이 대사일 확률" 을 재면 언제나 0 이다. 이름·장면도 글 전체를
# 봐야 하므로 여기 둔다.
# **이음만 뺀다.** 줄 하나하나의 성질(대사 한 줄의 길이 · 묻는 대사의 몫)은 대사
# 줄만 모아 놓고도 그대로 잴 수 있다. 처음에 그것까지 빼 놓았더니 대사 갈래가 보는
# 축이 0개가 되어, 제일 특이한 갈래에 수가 하나도 안 붙었다.
BLIND = ("dialog", "t2t", "n2t", "t2n", "tag_rate", "talk_run", "talk_max",
         "rally", "open_t", "close_t", "names", "newname", "scene", "repeat")

# 갈래별 수를 두는 자리. 없으면 안 쓴다.
NUMS = os.environ.get("DRIFT_MODE_TARGETS", str(
    __import__("pathlib").Path(__file__).resolve().parent / "targets.modes.json"))


def split(text: str) -> dict:
    """글을 갈래별 글로 가른다. **한 자로 다 재니 폭이 벌어졌다** -- 대사 줄은 짧고
    묘사 줄은 길어서, 섞어 재면 문장 길이가 21~55자가 된다. 그 폭은 어느 갈래의
    것도 아니다."""
    lines = [l for l in text.splitlines() if l.strip()]
    out = {a: [] for a in STATES}
    for l, a in zip(lines, seq(text)):
        out[a].append(l)
    return {a: "\n".join(v) for a, v in out.items() if v}


# 대사 줄만 모아 놓으면 **문장 자가 헛돈다.** rhythm 은 따옴표로 시작하는 줄을
# 대사로 보고 문장에서 빼기 때문에, 대사 갈래에서는 잴 문장이 거의 안 남는다
# (실측: A 의 대사 갈래 sent_len 이 4~21자, 짧은 문장 몫이 1.00 이었다 -- 그건 대사
# 길이가 아니라 대사 사이에 낀 몇 줄의 길이였다). 그래서 따옴표를 벗겨 다시 잰다.
_MARKS = re.compile(r'^\s*[\"“‘\'(\[]|[\"”’)\]]\s*$', re.M)


def unquote(text: str) -> str:
    """따옴표만 벗긴다. 안의 글자는 안 건드린다."""
    return _MARKS.sub("", text)


# 따옴표가 있어야 나오는 축. 벗긴 글로 재면 안 되는 것들이다.
QUOTED = ("talk_len2", "talk_len", "q_rate", "ex_rate", "ell_rate", "quote")


def nums(path: str = "") -> dict:
    """갈래별 폭. {갈래: {축: {lo, mid, hi}}}. 없으면 빈 것 -- 그러면 갈래 줄에
    수가 안 붙고 예전과 같아진다."""
    import json
    try:
        with open(path or NUMS, encoding="utf-8") as f:
            return json.load(f).get("modes", {})
    except (OSError, ValueError):
        return {}


def of(line: str, prev: str = "묘사") -> str:
    """줄 하나의 상태. **순서가 곧 우선순위다** -- 대사가 제일 세다."""
    s = line.strip()
    if not s:
        return prev
    if _QUOTE.match(s):
        return "대사"
    if _MOVE.search(s[:20]):
        return "전환"
    if _INNER.search(s):
        return "내면"
    return "묘사"


def seq(text: str) -> list:
    """글 전체의 상태 열. 마지막 줄은 맺음으로 본다."""
    lines = [l for l in text.splitlines() if l.strip()]
    out, prev = [], "묘사"
    for l in lines:
        prev = of(l, prev)
        out.append(prev)
    if out:
        out[-1] = "맺음"
    return out


def learn(texts) -> dict:
    """표본에서 전이와 머무름을 배운다. **호출 0회.**"""
    trans = {a: Counter() for a in STATES}
    runs = {a: [] for a in STATES}
    first = Counter()
    for t in texts:
        ks = seq(t)
        if not ks:
            continue
        first[ks[0]] += 1
        cur, n = ks[0], 1
        for a, b in zip(ks, ks[1:]):
            trans[a][b] += 1
            if b == cur:
                n += 1
            else:
                runs[cur].append(n)
                cur, n = b, 1
        runs[cur].append(n)
    out = {"trans": {}, "run": {}, "first": {}}
    for a in STATES:
        tot = sum(trans[a].values()) or 1
        out["trans"][a] = {b: trans[a].get(b, 0) / tot for b in STATES}
        out["run"][a] = (sum(runs[a]) / len(runs[a])) if runs[a] else 1.0
    ft = sum(first.values()) or 1
    out["first"] = {a: first.get(a, 0) / ft for a in STATES}
    return out


def plan(model: dict, seed: str, n: int, lines: int = 24) -> list:
    """다음 덩어리가 밟을 상태 열. 배운 전이를 **해시로** 굴린다 -- 이어 써도 재현된다."""
    if not model or not model.get("trans"):
        return []
    # **맺음은 중간에 안 나온다.** 표본에서 맺음은 늘 마지막 줄이라 나가는 전이가
    # 없다. 중간에 뽑히면 그 다음이 빈 분포가 되어 묘사로 떨어지고, 대목 한가운데에
    # "닫아라" 가 실린다. 그래서 뽑을 때 빼고 마지막에만 세운다.
    live = tuple(k for k in STATES if k != "맺음")

    def roll(probs, salt):
        h = int(hashlib.sha1(f"{seed}|{salt}|{n}".encode("utf-8")).hexdigest()[:8], 16)
        x = (h % 10000) / 10000.0
        tot = sum(probs.get(k, 0.0) for k in live) or 1.0
        acc = 0.0
        for k in live:
            acc += probs.get(k, 0.0) / tot
            if x < acc:
                return k
        return live[0]
    cur = roll(model["first"], "s0")
    out = [cur]
    while len(out) < lines:
        stay = max(1, round(model["run"].get(cur, 1.0)))
        for _ in range(stay - 1):
            if len(out) >= lines:
                break
            out.append(cur)
        cur = roll(model["trans"].get(cur, {}), f"s{len(out)}")
        if len(out) < lines:
            out.append(cur)
    out[-1] = "맺음"
    return out[:lines]


def shape(states: list) -> list:
    """상태 열을 (상태, 줄 수) 로 접는다. 프롬프트에 스물네 줄을 늘어놓지 않으려고."""
    out = []
    for s in states:
        if out and out[-1][0] == s:
            out[-1][1] += 1
        else:
            out.append([s, 1])
    return [(a, b) for a, b in out]


def brief(model: dict, seed: str, n: int, lines: int = 24) -> str:
    """프롬프트에 붙일 한 덩이. **상태마다 볼 것이 다르다.**"""
    return render(plan(model, seed, n, lines))


def render(st: list, extra: dict | None = None) -> str:
    """상태 열 하나를 프롬프트 한 덩이로. 열을 따로 받는 것은 부르는 쪽이 같은 열로
    **축까지 골라야** 하기 때문이다(state.watched)."""
    if not st:
        return ""
    folded = shape(st)
    road = " → ".join(f"{a}{b}줄" for a, b in folded)
    seen = []
    for a, _b in folded:
        if a not in seen:
            seen.append(a)
    tips = []
    for a in seen:
        n = (extra or {}).get(a, "")
        tips.append(f"  · **{a}** -- {SAY[a]}" + (f"\n      {n}" if n else ""))
    return ("[이 대목의 흐름] 표본이 밟는 순서다. 그대로 밟되 줄 수는 언저리면 된다.\n"
            f"  {road}\n" + "\n".join(tips))


def load(path: str = "") -> dict:
    """배워 둔 모델. **없으면 빈 것을 돌려준다** -- 그러면 brief 가 빈 줄이 되고
    프롬프트는 예전과 똑같아진다. 배운 적 없는 흐름을 지어내서 시키지 않는다."""
    import json
    try:
        with open(path or PATH, encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return {}
    return m if m.get("trans") else {}


def save(model: dict, path: str = "") -> str:
    import json
    p = path or PATH
    with open(p, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2, sort_keys=True)
    return p


def watched(states) -> tuple:
    """이 대목에 나오는 상태들이 보는 축. 차례는 상태가 나온 차례다."""
    out = []
    for a in states:
        for k in WATCH.get(a, ()):
            if k not in out:
                out.append(k)
    return tuple(out)
