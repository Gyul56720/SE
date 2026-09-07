"""**조판을 재는 자** -- 지면이 어떻게 생겼는가.

문장(문면) · 사건(서사) · 목소리 · 의미까지 재 놓고도 빠진 층이 있었다. **글이
지면에 놓인 꼴**이다. 편지 한 장이 통째로 들어가는가, 장면을 빈 줄로 가르는가,
가르는 자리에 별표를 찍는가, 문단 첫머리를 들여쓰는가, 회차에 제목이 붙는가.

읽는 사람은 이것을 제일 먼저 본다 -- 문장을 읽기 전에 **눈에 들어오는 꼴**이다.
그런데 한 축도 없었다. 편지를 물어보셔서 그제야 붙였고, 그건 "말한 것만 재고 말
안 한 것은 영영 안 잰다" 는 그 잘못이다. 그래서 여기서는 끝까지 적는다.

전부 정규식이다. **LLM 호출 0회.**
"""
from __future__ import annotations

import re

# 장면을 가르는 표. 빈 줄만 쓰는 작품, 별표를 찍는 작품, 아무것도 안 쓰는 작품이 있다.
_DIVIDER = re.compile(r"^\s*([*＊·•◇◆□■※\-—=~＿_]{2,}|\*\s*\*\s*\*)\s*$", re.M)
# 회차·장의 제목 줄. 짧고, 끝에 온점이 없고, 앞뒤가 빈 줄인 줄.
_HEAD = re.compile(r"^\s*(제?\s*\d+\s*[화장부권편]|[0-9]+\.|[「『\[][^」』\]]{1,30}[」』\]])\s*$", re.M)
# 날짜·시각 머리. "2월 3일" 처럼 대목 앞에 붙는 것.
_STAMP = re.compile(r"^\s*(\d{1,4}[년.\-/]\s*\d{1,2}[월.\-/]\s*\d{0,2}일?|"
                    r"[월화수목금토일]요일|오전 \d|오후 \d)\s*$", re.M)
# 편지·쪽지의 자국. 부르는 말로 열고 서명으로 닫는다.
_LETTER_OPEN = re.compile(r"^\s*\S{1,12}\s*(에게|께|귀하)\s*[,.]?\s*$", re.M)
_LETTER_CLOSE = re.compile(r"^\s*\S{1,12}\s*(올림|드림|배상|씀)\s*\.?\s*$", re.M)
# 들여쓴 줄. 문단 첫머리를 들여쓰는 작품과 안 쓰는 작품이 갈린다.
_INDENT = re.compile(r"^[ 　\t]+\S", re.M)
# 줄표로 여는 대사(희곡·번역 문학의 꼴).
_DASH_TALK = re.compile(r"^\s*[—–-]\s*\S", re.M)
# 가운데 끼는 강조·인용 표시.
_EMPH = re.compile(r"[‘’'][^’']{1,20}[’']|[《〈][^》〉]{1,30}[》〉]")


def measure(text: str) -> dict:
    """조판 축. 줄이 없으면 빈 것을 돌려준다."""
    lines = text.splitlines()
    live = [l for l in lines if l.strip()]
    if not live:
        return {}
    n = len(live)
    per_k = max(1.0, len(text) / 1000)
    # 빈 줄이 하나 이상 이어지는 자리. 문단 사이인지 장면 사이인지는 개수로 가른다.
    blanks, run, runs = 0, 0, []
    for l in lines:
        if l.strip():
            if run:
                runs.append(run)
                run = 0
        else:
            run += 1
            blanks += 1
    if run:
        runs.append(run)
    big = sum(1 for r in runs if r >= 2)      # 두 줄 이상 비면 장면 가르기로 본다
    return {
        "lay_blank": len(runs) / per_k,        # 천 자당 빈 줄 자리
        "lay_break": big / per_k,              # 천 자당 장면 가르기(두 줄 이상)
        "lay_div": len(_DIVIDER.findall(text)) / per_k,
        "lay_head": len(_HEAD.findall(text)) / per_k,
        "lay_stamp": len(_STAMP.findall(text)) / per_k,
        "lay_letter": (len(_LETTER_OPEN.findall(text))
                       + len(_LETTER_CLOSE.findall(text))) / per_k,
        "lay_indent": len(_INDENT.findall(text)) / n,
        "lay_dashtalk": len(_DASH_TALK.findall(text)) / n,
        "lay_emph": len(_EMPH.findall(text)) / per_k,
        "lay_linelen": sum(len(l) for l in live) / n,
    }


def axes() -> list:
    return sorted(measure("가나다 라마바.\n\n  들여쓴 줄이다.\n\n\n* * *\n"
                          "영이에게\n잘 지내니.\n철수 올림\n").keys())


SAY = {
    "lay_blank":    "천 자당 빈 줄로 끊는 자리",
    "lay_break":    "천 자당 장면을 크게 가르는 자리",
    "lay_div":      "천 자당 가르는 표(별표·줄표)의 수",
    "lay_head":     "천 자당 제목 줄의 수",
    "lay_stamp":    "천 자당 날짜·시각 머리의 수",
    "lay_letter":   "천 자당 편지의 부름말·서명 줄",
    "lay_indent":   "첫머리를 들여쓴 줄의 몫",
    "lay_dashtalk": "줄표로 여는 대사 줄의 몫",
    "lay_emph":     "천 자당 홑따옴표·꺾쇠 강조의 수",
    "lay_linelen":  "줄 하나의 평균 길이(자)",
}
