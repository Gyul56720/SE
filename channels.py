"""**채널 설정을 읽는 한 자리.** 봇과 공개 에이전트가 같은 것을 읽게.

    DISCORD_PUBLIC_CHANNEL_ID=111
    DISCORD_PUBLIC_CHANNEL_ID_2=222
    DISCORD_PUBLIC_CHANNEL_ID_3=333,444      <- 쉼표로 여러 개도 된다

## 왜 모듈로 빼나

`main_public.py` 는 langgraph 를 임포트하므로 그것이 안 깔린 데서는 **읽어 볼 수조차
없다.** 그러면 채널 설정을 잘못 읽는 결손이 검사에 안 걸린다. 여기는 표준 라이브러리
뿐이라 어디서나 임포트되고, 그래서 `tests/test_channels.py` 가 붙들 수 있다.

## 조용히 안 듣는 것이 제일 나쁘다

채널 id 를 잘못 넣으면 봇이 **아무 말도 안 듣는데, 그것이 '봇이 죽었다' 와 화면에서
똑같이 보인다.** 그래서 여기서는 못 읽은 값을 버리지 않고 `이상한것` 으로 돌려주고,
부르는 쪽이 켜질 때 그것을 찍는다. 길드 id 를 채널 자리에 넣는 것이 특히 흔한데
(둘 다 같은 꼴의 수라 눈으로는 안 갈린다), 그것도 `on_ready` 가 잡는다.
"""
from __future__ import annotations

import os

공개채널변수 = "DISCORD_PUBLIC_CHANNEL_ID"
최대 = 9                     # _2 ... _9 까지 본다. 그 이상이 필요하면 쉼표를 쓴다


def 쪼개기(값: str) -> tuple:
    """`"111, 222"` -> `([111, 222], [])`. 수가 아닌 것은 **버리지 않고 돌려준다.**"""
    ids, 이상 = [], []
    for 조각 in str(값 or "").replace(";", ",").split(","):
        조각 = 조각.strip()
        if not 조각:
            continue
        try:
            ids.append(int(조각))
        except ValueError:
            이상.append(조각)
    return ids, 이상


def 모으기(이름들, env=None) -> tuple:
    """환경변수 여럿 -> `(채널 id 목록, 이상한 것)`. **차례를 지키고 겹치면 하나로.**"""
    env = os.environ if env is None else env
    ids, 이상, 본것 = [], [], set()
    for 이름 in 이름들:
        값 = env.get(이름)
        if 값 is None:
            continue
        낸것, 나쁜것 = 쪼개기(값)
        for i in 낸것:
            if i not in 본것:
                본것.add(i)
                ids.append(i)
        이상 += [f"{이름}={x}" for x in 나쁜것]
    return ids, 이상


def 공개채널이름들() -> list:
    """`[DISCORD_PUBLIC_CHANNEL_ID, ..._2, ..._3, ...]`"""
    return [공개채널변수] + [f"{공개채널변수}_{i}" for i in range(2, 최대 + 1)]


def 공개채널(env=None) -> tuple:
    """공개 채널 전부. `(ids, 이상한것)`.

    **첫째 것이 없으면 빈 목록이 아니라 그냥 없는 것**이다 -- 부르는 쪽이 예전처럼
    `KeyError` 를 내야 할지 정한다. 여기서 대신 정하지 않는다.
    """
    return 모으기(공개채널이름들(), env)
