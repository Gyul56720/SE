"""**프롬프트를 축에서 짓는다.** 손으로 쓴 문장론은 한 줄도 안 들어간다.

왜 다시 짓는가. 지금까지의 프롬프트는 사람이 쓴 작법서였다 -- [문장] [상황] [점층]
[리듬] [낱말] [정밀] … 7,000자가 넘는 페르소나. 그것이 틀렸다는 것이 표본을 재면서
드러났다: 긴 문장 몫도, 점층 간격도, 대사 몫도, 긴 대사도 전부 표본과 어긋나 있었고,
그 어긋난 요구가 원고를 망치고 있었다(늘어짐의 뿌리가 우리 지시였다).

그래서 규칙 하나로 다시 짓는다.

    **프롬프트에 들어가는 모든 줄은 재는 축에 매여 있어야 한다.**
    못 재는 것은 안 쓴다.

그러면 자연히 이렇게 된다.

  · 목표는 표본에서 온다(targets.json) -- 우리가 지어내지 않는다
  · 지시문은 축마다 하나씩 데이터로 있다(directives.json) -- 코드에 안 박는다
  · 이번 덩어리에 실리는 것은 **어긋난 축뿐**이다 -- 맞고 있으면 아무 말도 안 한다
  · 예문은 없다 -- 예를 박으면 원고가 그것으로 도배된다(다섯 번 겪었다)
  · 층은 문면부터다(TAXONOMY.md) -- 서사·세계는 재는 자가 생긴 뒤에 올린다

빠진 것은 **일부러** 빠진 것이다. 재는 자가 없는 요구를 프롬프트에 넣으면 지켜졌는지
알 수 없고, 알 수 없는 것은 고칠 수도 없다.
"""
from __future__ import annotations

import os

from novel import deep, dyn, mode as MD, plot, profile as PF, spine, targets as TG, voice

# 한 덩어리에 쓸 분량.
CHARS = int(os.environ.get("DRIFT_CHUNK", "3200"))
# 꼬리를 얼마나 보여 줄까.
TAIL = int(os.environ.get("DRIFT_TAIL", "1200"))

# 축 이름을 사람 말로. **여기 있는 것만 프롬프트에 나간다** -- 이름이 없는 축은
# 재기만 하고 시키지는 않는다는 뜻이다.
SAY = {
    "sent_len":  "문장 평균 길이(자)",
    "sent_var":  "문장 길이의 들쭉날쭉함(0~1)",
    "long":      "마흔다섯 자 넘는 문장의 몫",
    "short":     "스무 자 안쪽 문장의 몫",
    "da_share":  "짧은 '-다' 로 끝나는 서술문의 몫",
    "end_var":   "말끝이 고르게 흩어진 정도(0~1)",
    "glue":      "한 문장에 이어 붙인 절의 수",
    "climb":     "서술문 하나당 앞 문장을 받아 올린 횟수",
    "dialog":    "대사 줄의 몫",
    "talk_len":  "긴 대사의 몫",
    "rally":     "가장 길게 주고받은 턴 수",
    "para_len":  "문단 하나의 길이(자)",
    "outside":   "밖(이름·수·표기)이 적힌 문장의 몫",
    # 서사층 대용. 의미를 안 읽고 이야기의 결을 재는 다섯.
    "names":     "천 자당 여러 번 도는 이름의 수",
    "newname":   "한 번 나오고 마는 이름의 몫",
    "scene":     "천 자당 자리·때가 옮겨 가는 자국의 수",
    "clock":     "시한·약속이 걸린 문장의 몫",
    "askrate":   "묻는 줄의 몫",
    # 낱낱(grain). 한 작품을 흉내 낼 때만 폭이 생기고, 폭이 없으면 안 실린다.
    "ttr":       "쓴 낱말 가운데 서로 다른 것의 몫",
    "hapax":     "딱 한 번만 쓴 낱말의 몫",
    "wordlen":   "낱말 평균 글자 수",
    "josa_rate": "조사가 붙은 어절의 몫",
    "conn_rate": "연결어미가 붙은 어절의 몫",
    "josa_var":  "조사가 고르게 흩어진 정도",
    "conn_var":  "연결어미가 고르게 흩어진 정도",
    "end_var2":  "종결어미가 고르게 흩어진 정도",
    "comma":     "백 자당 쉼표 수",
    "quote":     "백 자당 따옴표 수",
    "dash":      "백 자당 줄표 수",
    "hanja":     "한자의 몫",
    "latin":     "로마자의 몫",
    "digit":     "숫자의 몫",
    # 줄과 줄 사이 -- 이 작품의 목소리는 여기서 갈린다.
    "n2t":       "지문 다음 줄이 대사일 확률",
    "t2t":       "대사 다음 줄이 또 대사일 확률",
    "t2n":       "대사 다음 줄이 지문일 확률",
    "talk_run":  "대사가 몇 줄씩 이어지나",
    "talk_max":  "가장 길게 이어진 대사 줄 수",
    "tag_rate":  "대사에 지문이 붙은 몫",
    "q_rate":    "묻는 대사의 몫",
    "ex_rate":   "느낌표가 붙은 대사의 몫",
    "ell_rate":  "말줄임이 든 대사의 몫",
    "talk_len2": "대사 한 줄의 길이(자)",
    "open_t":    "대사로 여는가",
    "close_t":   "대사로 닫는가",
}
# 목소리 축(voice). 문장도 사건도 아닌 것들 -- 시제 · 인칭 · 비유 · 감각 · 호칭.
# **이름은 그 자가 들고 있다** -- 여기 옮겨 적으면 축을 더할 때마다 두 곳을 고쳐야 한다.
SAY.update(voice.SAY)
# **초고 프롬프트는 자세할수록 좋다.** 수정은 덩어리마다 한 번뿐이고 그것도 일괄
# 수정이다 -- 걸린 문장들을 한 장에 담아 한 번에 고치고 끝낸다. 통째로 다시 쓰지
# 않는다. 그러니 처음에 다 말해 줘야 한다. 0 이면 재는 축을 전부 싣는다.
SHOW = int(os.environ.get("DRIFT_SHOW_AXES", "0"))


def aims(seed: str, n: int, keys: list) -> list:
    """이번 덩어리의 목표값. **폭 안에서 덩어리마다 흔든다** -- 가운뎃값을 목표로
    삼으면 모든 덩어리가 가운뎃값이 되고, 표본 자체가 그렇지 않다."""
    from novel import rhythm
    out = []
    for k in keys:
        band = TG.band(k)
        if not band or k not in SAY:
            continue
        lo, hi = band
        out.append((k, rhythm.wave(f"{seed}|aim|{k}", n, lo, hi)))
    return out


def _fmt(k: str, v: float) -> str:
    if k in ("sent_len", "para_len", "rally"):
        return f"{v:.0f}"
    if k in ("wordlen", "comma", "quote", "dash", "talk_run"):
        return f"{v:.2f}"
    if k in ("talk_max", "talk_len2"):
        return f"{v:.0f}"
    if k in ("glue", "climb"):
        return f"{v:.2f}"
    return f"{v:.0%}"


# 설명(aim)을 몇 줄까지 붙일까. 값은 전부 주되 설명까지 마흔 줄이면 프롬프트가 터진다.
AIMS = int(os.environ.get("DRIFT_SHOW_AIMS", "8"))


# 상태 열을 몇 줄로 그릴까. 한 덩어리가 대략 이만큼의 줄이 된다.
LINES = int(os.environ.get("DRIFT_STATE_LINES", "24"))


# 갈래 하나에 수를 몇 개까지 붙일까. 갈래마다 여섯이면 다섯 갈래에 서른이다.
MODE_NUMS = int(os.environ.get("DRIFT_MODE_NUMS", "6"))


def mode_nums(seed: str, n: int, st: list) -> dict:
    """갈래마다 **그 갈래에서 잰** 수. 섞어 잰 수 하나로는 대사 줄과 묘사 줄에 같은
    문장 길이를 시키게 된다 -- A 에서 그 폭이 21.6~55.3자였다.

    targets.modes.json 이 없으면 빈 것을 돌려주고, 그러면 갈래 줄에 수가 안 붙는다."""
    from novel import rhythm
    table = MD.nums()
    out = {}
    for m in set(st):
        band = table.get(m) or {}
        keys = [k for k in MD.WATCH.get(m, ()) if k in band and k in SAY]
        if not keys:
            continue
        vs = []
        for k in keys[:MODE_NUMS]:
            v = rhythm.wave(f"{seed}|aim|{m}|{k}", n, band[k]["lo"], band[k]["hi"])
            vs.append(f"{SAY[k]} {_fmt(k, v).strip()}")
        out[m] = "(이 갈래에서: " + " · ".join(vs) + ")"
    return out


def target_block(seed: str, n: int, last: str = "", watch=()) -> str:
    """이번 덩어리가 맞출 수. **값은 전부, 설명은 몇 개만.**

    수정이 덩어리마다 한 번뿐이라 초고가 자세해야 한다. 그렇다고 축 마흔 개에
    설명을 다 붙이면 프롬프트가 터지고, 무엇보다 **다 강조하면 강조가 아니다.**
    그래서 값은 빽빽하게 전부 주고, 어떻게 맞추는지는 **지금 어긋난 축부터** 몇 개만
    붙인다. 직전 덩어리가 없으면(첫 덩어리) 굵은 축부터 붙인다."""
    keys = [k for k in PF.AXES if k in SAY and TG.band(k)]
    if SHOW:
        import hashlib
        keys = sorted(keys, key=lambda k: hashlib.sha1(
            f"{seed}|pick|{n}|{k}".encode("utf-8")).hexdigest())[:SHOW]
    if not keys:
        return ""
    vals = dict(aims(seed, n, keys))

    # 어느 축에 설명을 붙일까. **이번 대목이 보는 축부터**(watch), 그 안에서도
    # 직전 덩어리가 어긋난 것부터. 대사를 쓰는 대목에 문단 길이를 설명해 봐야
    # 지켜지지 않는다 -- 여덟 줄뿐인 자리를 지금 쓰는 것에 준다.
    far = []
    if last:
        far = [k for k, _side, _d, _v in dyn.off(last, slack=0.0) if k in vals]
    w = [k for k in watch if k in vals]
    order = ([k for k in w if k in far] + [k for k in far if k not in w]
             + [k for k in w if k not in far] + keys) if (far or w) else keys
    seen, uniq = set(), []
    for k in order:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    order = uniq

    dense = " · ".join(f"{SAY[k]} {_fmt(k, vals[k]).strip()}" for k in keys)
    how = dyn.load()
    tips = []
    for k in order[:AIMS]:
        t = (how.get(k) or {}).get("aim", "")
        if t:
            tips.append(f"  · **{SAY[k]} {_fmt(k, vals[k]).strip()}** -- {t}")
    out = ["[이번 대목의 수] **이 수에 맞춰 쓴다.** 덩어리마다 다르다 -- 매번 같은",
           "몫으로 쓰면 그것이 곧 단조로움이다. 아래는 다 재서 판정한다.",
           "  " + dense]
    if tips:
        out.append("")
        out.append("  이번에 특히 볼 것:")
        out += tips
    return "\n".join(out)


def build(book: dict, ledger: str = "", asks: str = "", opening_head: str = "",
          head: str = "") -> str:
    """프롬프트 한 벌. 조각은 부르는 쪽이 준다 -- 여기서 만드는 것은 **뼈대**다."""
    chunks = book.get("chunks") or []
    opening = not chunks
    tail = "".join(chunks)[-TAIL:]
    seed = book.get("seed_id") or book.get("first", "")
    # **이번 대목이 밟을 상태 열.** 배운 적 없으면 빈 열이고, 그러면 흐름 줄도
    # 축 고르기도 예전 그대로다 -- 없는 것을 지어내서 시키지는 않는다.
    st = MD.plan(MD.load(), seed, len(chunks), LINES)
    parts = [
        head or "한국어 소설을 쓴다. 산문만 출력한다 -- 제목도 머리말도 표식도 쓰지 마라.",
        f"[분량] 약 {CHARS}자. 끊지 말고 이어라. 회차도 씬도 없다.",
        MD.render(st, mode_nums(seed, len(chunks), st)),
        target_block(seed, len(chunks), tail if not opening else "", MD.watched(st)),
    ]
    if ledger:
        parts.append("[세계 — 지금까지 확정된 것]\n" + ledger
                     + "\n  * 여기 적힌 것과 어긋나게 쓰지 마라. 나머지는 전부 자유다."
                     + "\n  * 없는 것은 새로 지어내도 된다. 지어냈으면 이름과 수를 대라.")
    if opening:
        parts.append((opening_head or "[첫 문장 — 이것으로 시작하라]")
                     + "\n" + book.get("first", ""))
    else:
        parts.append("[지금까지의 끝부분 — 여기서 이어 쓴다]\n..." + tail
                     + "\n  * **이 마지막 문장 다음 순간부터 써라.** 여기가 지금이다."
                       "\n  * 위 글을 옮겨 적지 마라. 읽으라고 준 것이다."
                       "\n  * 시간은 앞으로만 간다.")
    # **다음 한 걸음.** 개요는 없다 -- 무엇이 달라지는지 갈래만 정하고 내용은 원고가
    # 정한다. 걸음도 재는 축에 매여 있다(names · scene · clock · askrate).
    # **셋 중 있는 것을 쓴다.** 의미층 기록(deep.json)이 있으면 그것이 제일 자세하다
    # -- 스물두 칸을 그 대목의 값 그대로 시킨다. 없으면 뼈대(spine.json)의 한 줄,
    # 그것도 없으면 갈래만 뽑아 준다. 지어내서 시키지는 않는다.
    parts.append(deep.brief(len(chunks)) or spine.brief(len(chunks)) or
                 plot.brief(seed, len(chunks), book.get("ledger")))
    if asks:
        parts.append(asks)
    return "\n\n".join(p for p in parts if p)


def offbrief(book: dict) -> str:
    """직전 덩어리에서 어긋난 축만. 맞고 있으면 빈 줄이다."""
    chunks = book.get("chunks") or []
    if not chunks:
        return ""
    a = dyn.arm(book.get("seed_id") or book.get("first", ""), len(chunks))
    book["_arm"] = a
    return dyn.brief(chunks[-1], limit=a["asks"], slack=a["slack"])
