"""BaseCallbackHandler -- langchain_core.callbacks 자리.

bot_tools 의 `_간격두기` 가 이것을 상속해 `on_chat_model_start`/`on_llm_start` 로
분당 한도(rpmgate)를 건다. 우리 모델(se_agent.model.ChatModel)은 **HTTP 요청 직전에**
등록된 콜백의 이 메서드를 부른다 -- langchain 이 하던 그대로.
"""
from __future__ import annotations


class BaseCallbackHandler:
    """빈 훅들. 하위 클래스가 필요한 것만 덮어쓴다."""

    def on_chat_model_start(self, *a, **kw):
        pass

    def on_llm_start(self, *a, **kw):
        pass

    def on_llm_end(self, *a, **kw):
        pass

    def on_llm_error(self, *a, **kw):
        pass


def fire_start(callbacks):
    """요청 직전에 부른다. langchain 은 채팅 모델이면 on_chat_model_start 를 부르므로
    그쪽을 우선 부른다(둘 다 있으면 중복 방지)."""
    for cb in callbacks or []:
        fn = getattr(cb, "on_chat_model_start", None)
        if callable(fn):
            try:
                fn({}, [])
                continue
            except Exception:
                pass
        fn = getattr(cb, "on_llm_start", None)
        if callable(fn):
            try:
                fn({}, [])
            except Exception:
                pass
