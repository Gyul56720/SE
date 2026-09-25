"""MemorySaver -- langgraph.checkpoint.memory.MemorySaver 자리.

thread_id 로 대화 메시지 목록을 들고 있는 사전. 프로세스가 사는 동안만 남는다
(langgraph 의 MemorySaver 와 같은 수명). 여러 후보(agent)가 같은 saver 를 공유해서
후보가 바뀌어도 같은 thread_id 의 맥락이 이어진다 -- bot_tools.build_agent_pool 의 계약.
"""
from __future__ import annotations

import threading


class MemorySaver:
    def __init__(self):
        self._store: dict[str, list] = {}
        self._lock = threading.Lock()

    def get(self, thread_id: str) -> list:
        with self._lock:
            return list(self._store.get(str(thread_id), []))

    def put(self, thread_id: str, messages: list) -> None:
        with self._lock:
            self._store[str(thread_id)] = list(messages)

    def clear(self, thread_id: str) -> None:
        with self._lock:
            self._store.pop(str(thread_id), None)
