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

from novel import dyn, profile as PF, targets as TG

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
}
# 몇 개를 목표로 보여 줄까. 다 보여 주면 그것도 열넷짜리 목록이다.
SHOW = int(os.environ.get("DRIFT_SHOW_AXES", "5"))


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
    if k in ("glue", "climb"):
        return f"{v:.2f}"
    return f"{v:.0%}"


def target_block(seed: str, n: int) -> str:
    """이번 덩어리가 맞출 수 -- 다섯 개만. 나머지는 자가 뒤에서 본다."""
    keys = [k for k in PF.AXES if k in SAY]
    # 덩어리마다 다른 다섯 개를 고른다. 늘 같은 것만 보여 주면 나머지는 잊힌다.
    import hashlib
    order = sorted(keys, key=lambda k: hashlib.sha1(
        f"{seed}|pick|{n}|{k}".encode("utf-8")).hexdigest())
    rows = [f"  · {SAY[k]}: **{_fmt(k, v)}**" for k, v in aims(seed, n, order[:SHOW])]
    if not rows:
        return ""
    return ("[이번 대목의 수] 이 수에 맞춰 쓴다. **덩어리마다 다르다** -- 매번 같은\n"
            "몫으로 쓰면 그것이 곧 단조로움이다.\n" + "\n".join(rows))


def build(book: dict, ledger: str = "", asks: str = "", opening_head: str = "",
          head: str = "") -> str:
    """프롬프트 한 벌. 조각은 부르는 쪽이 준다 -- 여기서 만드는 것은 **뼈대**다."""
    chunks = book.get("chunks") or []
    opening = not chunks
    tail = "".join(chunks)[-TAIL:]
    seed = book.get("seed_id") or book.get("first", "")
    parts = [
        head or "한국어 소설을 쓴다. 산문만 출력한다 -- 제목도 머리말도 표식도 쓰지 마라.",
        f"[분량] 약 {CHARS}자. 끊지 말고 이어라. 회차도 씬도 없다.",
        target_block(seed, len(chunks)),
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
