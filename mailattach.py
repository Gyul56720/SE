# -*- coding: utf-8 -*-
"""메일 첨부 경로를 푼다 -- **`bot_tools` 밖에 둔 이유가 있다.**

`bot_tools` 는 langchain 을 들이므로, 그것이 없는 환경(이 에이전트 컨테이너가 그렇다)
에서는 **통째로 임포트가 안 된다.** 그러면 첨부 경로 가드처럼 순수한 로직까지 검사를
못 받는다 -- 과제 #9 가 적어 둔 그 병(`G012 사고증명이 환경 의존이다`)과 같은 자리다.

그래서 망·모형·프레임워크가 필요 없는 부분만 여기 둔다. `tests/test_mailattach.py`
가 이것을 **langchain 없이** 끝까지 돌린다.
"""
import glob as _glob
import re
from pathlib import Path

import toolgate

# Gmail 의 실질 상한은 25 MB 인데, base64 로 부풀면 실제 바이트가 더 든다(약 4/3).
# 그래서 원본 기준 20 MB 에서 끊는다 -- 상한에 걸려 되돌아오는 것보다 먼저 막는 게 낫다.
첨부최대 = 20 * 1024 * 1024
첨부개수 = 12

# A subject-line **tag** is not an unfilled placeholder. Measured 2026-09-21:
# Priya's report was fully generated but not a single mail went out, because
# `[보고]` in the subject was read as "a slot you forgot to fill".
#
# This list is the *only* thing the placeholder gate waives, and it is waived
# only when a caller names it explicitly. Both the English tags (the company
# writes in English now) and the Korean ones (older subjects, and what the user
# still types) are here. `tests/test_mailattach.py` asserts that whatever
# `house/report.SUBJECT_TAG` currently is appears in this list -- the two must
# not drift, and they did drift once already, within an hour of each other.
SUBJECT_TAGS = ["[REPORT]", "[FYI]", "[NOTICE]", "[URGENT]", "[RE]",
                "[보고]", "[공유]", "[안내]", "[긴급]", "[회신]"]
말머리 = SUBJECT_TAGS        # kept: existing call sites use this name


def 풀기(attach: str, repo=None) -> tuple:
    """쉼표/띄어쓰기로 나눈 **저장소 안 상대경로**들을 실제 파일로 푼다.

    글롭을 받는다(`house/signoff/*.sv`) -- 사인오프 꾸러미를 통째로 붙일 때 한 줄이면
    되게. 저장소 밖 · 비밀값 자리는 `toolgate.경로풀기` 가 막는다.

    돌려주는 것: (경로들, 거절사유들). **둘 다 돌려준다** -- 몇 개만 막혔을 때
    나머지를 보내고 막힌 것을 말해 줄 수 있어야 하기 때문이다.
    """
    쪽들 = [x for x in re.split(r"[,\s]+", (attach or "").strip()) if x]
    낸것, 거절 = [], []
    뿌리 = Path(repo or toolgate.REPO).resolve()
    for 쪽 in 쪽들:
        if any(ch in 쪽 for ch in "*?["):
            # 글롭은 **저장소 안에서만** 편다. 절대경로 글롭은 안 받는다.
            if 쪽.startswith("/") or ".." in 쪽:
                거절.append(f"{쪽}: 저장소 밖을 가리키는 글롭")
                continue
            후보 = sorted(_glob.glob(str(뿌리 / 쪽)))
            if not 후보:
                거절.append(f"{쪽}: 맞는 파일이 없다")
                continue
        else:
            후보 = [쪽]
        for c in 후보:
            try:
                p = toolgate.경로풀기(str(c), 쓰기=False, repo=repo)
            except ValueError as e:
                거절.append(f"{Path(str(c)).name}: {e}")
                continue
            if not p.is_file():
                거절.append(f"{c}: 파일이 아니다")
                continue
            낸것.append(p)
    본것, 추린것 = set(), []
    for p in 낸것:                       # 글롭이 겹치면 같은 파일이 두 번 온다
        if p not in 본것:
            본것.add(p)
            추린것.append(p)
    return 추린것, 거절


def 재기(경로들) -> int:
    return sum(p.stat().st_size for p in 경로들)


def 막히나(경로들) -> str:
    """보내기 전에 한도를 본다. 막을 까닭이 없으면 빈 문자열."""
    if len(경로들) > 첨부개수:
        return (f"{len(경로들)}개는 너무 많다(최대 {첨부개수}) -- "
                "tar 로 묶고 그것을 붙여라")
    총 = 재기(경로들)
    if 총 > 첨부최대:
        return (f"합 {총/1e6:.1f} MB 는 메일로 못 보낸다(상한 "
                f"{첨부최대/1e6:.0f} MB) -- 큰 것을 빼거나 tar.gz 로 묶어라")
    return ""
