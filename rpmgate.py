# -*- coding: utf-8 -*-
"""rpmgate -- **분당 한도에 걸리기 전에 간격을 둔다.**

## 고치려는 것

ReAct 루프는 사용자 메시지 **하나**에 LLM 을 여러 번 부른다. 도구를 부를 때마다 한 번씩
더 부르니, 파일 몇 개 읽고 셸 두어 번 돌리는 평범한 부탁도 열 번을 넘는다. 그것이 몇 초
안에 연달아 나간다.

무료 티어의 분당 한도(RPM)는 (프로젝트, 모델) 당 몇 회다. 그래서 **한 메시지가 자기
한도를 혼자 다 쓴다.** 그 다음에 일어나는 일이 사용자가 본 것이다:

    429 RPM -> 60초 쿨다운 -> 다음 후보로 전환 -> 그 후보도 곧 같은 꼴 -> ...

게다가 후보를 갈아타면 **그 대화를 새 모델이 이어받아** 다시 한 바퀴 돈다. 즉 한도에
걸릴수록 호출이 더 늘어난다. 되먹임이다.

지금까지의 대응은 전부 **맞고 난 뒤**였다 -- 쿨다운에 올리고, 뒤로 밀고, 건너뛰고
(quota_tracker · poolpick). 그건 피해를 줄일 뿐 **안 맞게 하지는 못한다.**
여기는 맞기 전에 간격을 둔다.

## 왜 '한 번 쉬기' 가 아니라 창(window)인가

고정 간격(예: 매 호출 6초)은 두 가지로 틀린다. 놀 때도 기다리고(첫 호출부터 6초),
몰아칠 때는 여전히 넘는다(한도가 10인데 60초에 10번을 앞쪽에 몰면 다음 분 초입에서
터진다). 그래서 **최근 60초에 몇 번 썼는지**를 세고, 한도에 닿았을 때만 *가장 오래된
호출이 창 밖으로 나갈 때까지* 기다린다. 한가하면 한 번도 안 쉰다.

## 한도는 모델마다 다르다

구글 무료 티어 기준으로 flash-lite > flash > pro 순으로 넉넉하다. 이름으로 고른다 --
정확한 수를 API 가 주지 않으므로 **보수적으로** 잡는다. `GEMINI_RPM` 을 주면 전부
그 값으로 덮는다(계정 등급이 다르면 그쪽이 맞다).

시계와 잠을 인자로 받는다 -- 검사에서 진짜로 60초를 기다리지 않기 위해서다.
"""
from __future__ import annotations

import collections
import os
import re
import threading
import time

창 = 60.0                       # 한도가 걸리는 시간 창 (초)
기본RPM = int(os.environ.get("GEMINI_RPM_DEFAULT", "10"))
덮어쓰기 = os.environ.get("GEMINI_RPM", "")      # 있으면 모델을 안 보고 이 값

# 이름 -> 분당 한도. 위에서부터 먼저 맞는 것을 쓴다(flash-lite 가 flash 보다 앞이어야 한다).
한도표 = (
    (re.compile(r"flash-?lite", re.I), 15),
    (re.compile(r"flash", re.I), 10),
    (re.compile(r"\bpro\b|-pro", re.I), 5),
    (re.compile(r"gemma", re.I), 10),
)


# ---------------------------------------------------------------- 부를 값이 있는가
# **pro 계열은 후보에서 뺀다.** 무료 티어에서 pro 의 분당 한도는 flash 계열의 몇 분의
# 일이라, 후보에 끼워 두면 거의 매번 429 만 받아 오면서 그 키의 벌점만 올린다 -- 답을
# 주지도 않고 다음 시도를 늦추기만 하는 후보다.
#
# 이 저장소는 이 교훈을 **이미 배웠다.** `orchestrator/llm_pool.py` 가 같은 문장을 적어
# 두고 같은 모델들을 거른다. 그런데 디스코드 에이전트 경로(bot_tools.build_agent_pool)는
# 그 거름망을 안 거쳤고, 게다가 `_model_quality_rank` 가 pro 를 **1순위**로 친다 --
# 그래서 매 메시지가 pro 부터 두드리고 429 를 먹었다. 사용자가 보낸 로그 그대로다:
#
#     candidate=key-…:gemini-3.1-pro-preview-customtools 분당 한도(RPM) 초과
#     candidate=key-…:gemini-pro-latest 분당 한도(RPM) 초과
#     candidate=key-…:gemini-pro-latest 분당 한도(RPM) 초과
#
# llm_pool 이 실측으로 적어 둔 것과 **같은 두 이름**이다. 한 저장소에서 같은 교훈을 두
# 번 배우지 않으려면 거름망이 두 경로에 다 있어야 한다.
#
# 답의 품질은 프롬프트와 도구가 정하지 모델 등급이 정하지 않는다. 되살리려면
# `GEMINI_ALLOW_PRO=1`.
SKIP_MODEL = re.compile(os.environ.get("GEMINI_SKIP_MODEL", r"pro"), re.I)
ALLOW_PRO = os.environ.get("GEMINI_ALLOW_PRO", "") not in ("", "0", "false")


def worth_calling(model: str) -> bool:
    """Is this model worth having in the pool at all?

    A candidate that answers 429 every time is worse than no candidate: it costs a
    round trip, raises that key's penalty, and delays the one that would have
    answered."""
    if ALLOW_PRO:
        return True
    return not SKIP_MODEL.search((model or "").split(":", 1)[-1])


def usable_models(names) -> list:
    """Filter a model list, **but never hand back an empty pool.**

    If the filter would remove everything, the filter is wrong about this account,
    not the account about the filter -- an empty pool means the bot cannot answer at
    all, which is strictly worse than a slow answer."""
    names = [n for n in (names or []) if n]
    kept = [n for n in names if worth_calling(n)]
    return kept or names


def 모델한도(model: str) -> int:
    """이 모델을 분당 몇 번까지 부를 것인가."""
    if 덮어쓰기:
        try:
            return max(1, int(덮어쓰기))
        except ValueError:
            pass
    이름 = (model or "").split(":", 1)[-1]
    for 패, 값 in 한도표:
        if 패.search(이름):
            return 값
    return 기본RPM


class 문:
    """(키, 모델) 마다 최근 창 안의 호출을 세고, 한도에 닿으면 잠깐 재운다.

    **한 프로세스 안의 호출만 센다.** 다른 프로세스(야간 런 등)가 같은 키를 쓰면 그쪽은
    안 보인다 -- 그건 여기서 풀 문제가 아니라 quota_tracker 가 429 를 맞고 나서 푸는
    문제다. 여기가 막는 것은 *한 대화가 혼자 자기 한도를 다 쓰는* 꼴이다.
    """

    def __init__(self, 지금=None, 쉬기=None, 창길이: float = 창):
        self._지금 = 지금 or time.monotonic
        self._쉬기 = 쉬기 or time.sleep
        self._창 = float(창길이)
        self._자국: dict = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()

    def 센것(self, label: str) -> int:
        """지금 창 안에 남아 있는 호출 수."""
        with self._lock:
            return len(self._치우기(label, self._지금()))

    def _치우기(self, label: str, 이제: float):
        q = self._자국[label]
        while q and 이제 - q[0] >= self._창:
            q.popleft()
        return q

    def 지나가기(self, label: str, 한도: "int | None" = None) -> float:
        """한 번 부를 자리를 얻는다. 기다린 초를 돌려준다(안 기다렸으면 0.0).

        **잠은 락 밖에서 잔다.** 락을 쥔 채 자면 다른 모델을 부르는 스레드까지 같이
        멈춘다 -- 서로 다른 모델은 각자의 통을 쓰므로 함께 멈출 이유가 없다.
        """
        cap = 한도 if 한도 is not None else 모델한도(label)
        cap = max(1, int(cap))
        잔 = 0.0
        while True:
            with self._lock:
                이제 = self._지금()
                q = self._치우기(label, 이제)
                if len(q) < cap:
                    q.append(이제)
                    return 잔
                기다릴 = self._창 - (이제 - q[0])
            기다릴 = max(0.01, 기다릴)
            self._쉬기(기다릴)
            잔 += 기다릴

    def 비우기(self, label: "str | None" = None) -> None:
        with self._lock:
            if label is None:
                self._자국.clear()
            else:
                self._자국.pop(label, None)


문지기 = 문()


def 지나가기(label: str, 한도: "int | None" = None) -> float:
    return 문지기.지나가기(label, 한도)


def 센것(label: str) -> int:
    return 문지기.센것(label)


# ---------------------------------------------------------------- 바퀴에도 끝이 있다
# **한 메시지가 돌 수 있는 바퀴 수.** LangGraph 의 recursion_limit 은 '노드를 몇 번
# 밟는가' 라서 도구 한 번마다 2 씩(모델 -> 도구) 는다 -- 60 이면 도구 서른 번쯤이다.
#
# **처음에 25 로 뒀는데 그것이 틀렸다(실측 2026-09-21).** langgraph 기본값을 그대로
# 가져왔을 뿐인데, 이 봇의 평범한 한 턴이 그것을 넘는다 -- 저장소를 고치고 검사를
# 돌리고 커밋하는 일은 도구 열두 번으로 안 끝난다. 사용자가 받은 것은 "25 바퀴 상한에
# 닿아 멈췄습니다" 였고, **일이 끝난 게 아니라 잘린 것**이었다.
#
# 이 값을 무엇으로 정할 것인가. 처음에는 분당 한도를 막으려고 짧게 잡았는데, 그 일은
# 위의 간격(지나가기)이 한다 -- 한도에 닿으면 재우지, 자르지 않는다. **그러니 이
# 상한은 한도 조절 장치가 아니라 폭주 방지 장치다.** 같은 도구를 끝없이 부르며 도는
# 것만 끊으면 된다. 그래서 넉넉하게 잡는다.
바퀴상한 = int(os.environ.get("REACT_RECURSION_LIMIT", "60"))


def 설정(thread_id: str, 상한: "int | None" = None) -> dict:
    """LangGraph 에 넘길 config. thread_id 와 바퀴 상한을 함께 싣는다."""
    return {"configurable": {"thread_id": thread_id},
            "recursion_limit": int(상한 or 바퀴상한)}


def 바퀴넘침(e: Exception) -> bool:
    """바퀴 상한에 닿아 끝난 것인가. 이것은 **고장이 아니라 끊은 것**이다 --
    새 thread 로 재시도하면 같은 일을 처음부터 또 돌면서 한도만 두 배로 쓴다."""
    if type(e).__name__ == "GraphRecursionError":
        return True
    글 = str(e)
    return "recursion_limit" in 글 or "Recursion limit" in 글


def 끊긴말(상한: "int | None" = None, 한일=()) -> str:
    """상한에 닿았을 때 사람에게 하는 말.

    두 가지를 반드시 말한다. **대화가 남아 있다는 것**(안 그러면 처음부터 다시
    시킨다), 그리고 **여기까지 무엇을 했는지**. 실측 2026-09-21: 첫 판은 "멈췄습니다"
    만 말하고 한 일을 안 적었다 -- 사용자는 셸이 돌았는지 파일이 바뀌었는지 알 길이
    없었다. 잘린 답에서 제일 급한 정보가 그것이다.
    """
    n = int(상한 or 바퀴상한)
    줄 = [f"(여기서 끊었습니다) 한 메시지 안에서 도구를 {n} 바퀴 넘게 돌아 멈췄습니다."]
    한일 = [str(x) for x in (한일 or []) if x]
    if 한일:
        줄.append("\n**여기까지 실제로 돌린 것:**")
        줄 += [f"  · `{x[:120]}`" for x in 한일[-12:]]
    줄.append("\n여기까지 한 일은 대화에 남아 있습니다. '이어서 해줘' 라고 하시면 "
             "이어서 합니다. 한 번에 여러 가지를 부탁하신 것이면 나눠 주시면 더 "
             "빠릅니다(분당 한도를 덜 씁니다).")
    return "\n".join(줄)
