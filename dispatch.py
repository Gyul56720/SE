"""고정 명령의 배선 -- 한 곳에서 잇는다.

배포판이란 남이 같은 말을 쳤을 때 같은 일이 나는 것이고, 그것을 보장하는 것은
에이전트가 아니라 고정 명령이다(`novel/discord_cmd.py` 의 사고 기록). 명령 모듈이
둘이 되면서(!소설 · !실험) 봇이 모듈마다 한 줄씩 부르는 대신 여기 한 줄만 부른다 --
새 기관의 명령은 이 목록에 한 줄 넣으면 배선이 끝난다.

규약: 각 모듈은 PREFIX 와 run(text, runner=None, allow_write=True) 를 가지고,
**모르는 말에는 None 을 돌려준다.** 그러면 다음 모듈로, 다 모르면 에이전트로 간다 --
이 파일이 기존 동작을 뺏지 않는다.
"""
from __future__ import annotations

from audit import discord_cmd as 감사
from codify import discord_cmd as 코드화
from delegate import discord_cmd as 위임
from dig import discord_cmd as 수집
from eval import discord_cmd as 평가
from evolve import discord_cmd as 진화
from graph import discord_cmd as 기억
from intent import discord_cmd as 목표
from novel import discord_cmd as 소설
from repair import discord_cmd as 고치기
from research import discord_cmd as 연구
from plan import discord_cmd as 계획
from secaudit import discord_cmd as 점검
from router import discord_cmd as 경로
from sandbox import discord_cmd as 실험
import keys as 열쇠
import relay as 중계

명령들 = (소설, 실험, 감사, 기억, 평가, 경로, 목표, 진화, 중계, 위임, 수집, 열쇠, 고치기, 점검, 코드화, 연구, 계획)


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """첫 번째로 알아듣는 명령 모듈의 답. 아무도 모르면 None(에이전트로)."""
    for 모듈 in 명령들:
        reply = 모듈.run(text, runner, allow_write)
        if reply is not None:
            return reply
    return None


# 사람이 치는 것과 봇이 치는 것의 경계. 실측 2026-09-11: 봇이 자연어 부탁에 고정 명령 **목록을
# 보여 주고** 끝냈다 -- 목록이 아니라 알맞은 명령을 제가 쳐야 한다. 단 승인 주체는 사람이다:
# `!목표 승인` `!계획 승인` 과 비밀값을 받는 `!열쇠` 는 봇이 대신 치지 못한다.
사람만 = ("승인",)


def 도구로쳐도되나(text: str) -> "tuple[bool, str]":
    t = (text or "").strip()
    if not t.startswith("!"):
        return False, "고정 명령은 `!` 로 시작한다"
    머리 = t.split(maxsplit=2)
    if 머리[0] == "!열쇠":
        return False, "!열쇠 는 사람이 친다 -- 비밀값을 봇이 대신 넣지 않는다"
    if len(머리) > 1 and 머리[1] in 사람만:
        return False, f"`{머리[0]} {머리[1]}` 은 사람만 친다 -- 승인 주체는 사람이다(관리 채널 화이트리스트)"
    return True, ""
