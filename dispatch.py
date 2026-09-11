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
from eval import discord_cmd as 평가
from evolve import discord_cmd as 진화
from graph import discord_cmd as 기억
from intent import discord_cmd as 목표
from novel import discord_cmd as 소설
from router import discord_cmd as 경로
from sandbox import discord_cmd as 실험
import relay as 중계

명령들 = (소설, 실험, 감사, 기억, 평가, 경로, 목표, 진화, 중계)


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """첫 번째로 알아듣는 명령 모듈의 답. 아무도 모르면 None(에이전트로)."""
    for 모듈 in 명령들:
        reply = 모듈.run(text, runner, allow_write)
        if reply is not None:
            return reply
    return None
