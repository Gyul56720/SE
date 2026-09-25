"""메시지 객체 -- langchain 의 HumanMessage/AIMessage/ToolMessage 자리.

**왜 자체로 짓나.** 부르는 쪽(relay.도구호출들 · compact._꼴/_글/_도구이름들 ·
bot_tools.extract_text)이 메시지를 **오리 타이핑**으로 읽는다. 그 계약만 지키면 된다:

    .type      : "human" | "ai" | "tool"
    .content   : str  또는  [{"type":"text","text":...}, ...]  (파트 리스트)
    AIMessage  : .tool_calls = [{"name":.., "args":{..}, "id":..}, ...]
                 .additional_kwargs = {}  (제공자별 tool_calls 자리, 우리는 위에 담으니 빈 dict)
    ToolMessage: .name = 도구이름, .content = 결과 글

langchain 을 걷어낸 자리다. 계약은 tests/test_se_agent.py 가 붙든다.
"""
from __future__ import annotations


class BaseMessage:
    type = ""

    def __init__(self, content="", **kw):
        self.content = content
        self.additional_kwargs = kw.pop("additional_kwargs", {})

    def __repr__(self):
        g = self.content if isinstance(self.content, str) else str(self.content)
        return f"<{type(self).__name__} {g[:40]!r}>"


class HumanMessage(BaseMessage):
    type = "human"


class AIMessage(BaseMessage):
    type = "ai"

    def __init__(self, content="", tool_calls=None, **kw):
        super().__init__(content, **kw)
        # 각 원소: {"name": str, "args": dict, "id": str}
        self.tool_calls = list(tool_calls or [])


class ToolMessage(BaseMessage):
    type = "tool"

    def __init__(self, content="", name="", tool_call_id="", **kw):
        super().__init__(content, **kw)
        self.name = name
        self.tool_call_id = tool_call_id


def to_message(m):
    """('user', '글') 튜플이나 이미 메시지인 것을 메시지로. bot_tools 는
    {"messages": [("user", prompt)]} 로 넘긴다."""
    if isinstance(m, BaseMessage):
        return m
    if isinstance(m, (list, tuple)) and len(m) == 2:
        role, content = m
        role = str(role).lower()
        if role in ("user", "human"):
            return HumanMessage(content)
        if role in ("ai", "assistant", "model"):
            return AIMessage(content)
        if role in ("tool", "function"):
            return ToolMessage(content)
        return HumanMessage(content)
    if isinstance(m, dict) and "role" in m:
        return to_message((m["role"], m.get("content", "")))
    return HumanMessage(str(m))


def text_of(content) -> str:
    """content(str 또는 파트 리스트)에서 글자만. bot_tools.extract_text 와 같은 규칙."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return str(content)
