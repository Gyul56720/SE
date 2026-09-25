"""@tool -- langchain_core.tools.tool 자리.

함수를 감싸 (이름 · 설명 · 인자 스키마)를 뽑고, **그대로 호출 가능**하게 둔다.
ReAct 고리(se_agent.react)는 `t.name` / `t.description` / `t.args_schema` 로 Gemini
functionDeclaration 을 짓고, `t(**args)` 로 실행한다.

langchain 처럼 **설명(독스트링)이 없으면 ValueError** 로 거부한다 -- bot_tools.py 가
그 동작에 기댄다(설명 없는 함수는 임포트 자체가 실패해야 한다, 실측 주석 2026).
"""
from __future__ import annotations

import functools
import inspect
import typing

_PYT = {
    int: "integer", float: "number", str: "string", bool: "boolean",
    list: "array", dict: "object",
}


def _json_type(ann):
    if ann is inspect.Parameter.empty:
        return "string"
    origin = typing.get_origin(ann)
    if origin in (list, tuple):
        return "array"
    if origin is dict:
        return "object"
    return _PYT.get(ann, "string")


def _schema_from_sig(fn):
    """함수 시그니처 -> JSON schema {type:object, properties, required}. Gemini
    functionDeclaration.parameters 에 그대로 쓴다."""
    sig = inspect.signature(fn)
    props, required = {}, []
    for name, p in sig.parameters.items():
        if name in ("self", "cls") or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        props[name] = {"type": _json_type(p.annotation)}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


class Tool:
    """호출 가능한 도구. langchain StructuredTool 의 우리가 쓰는 겉모습만."""

    def __init__(self, fn, name=None, description=None):
        self.fn = fn
        self.name = name or fn.__name__
        self.description = (description or inspect.getdoc(fn) or "").strip()
        if not self.description:
            raise ValueError(
                f"도구 '{self.name}' 에 설명(독스트링)이 없다 -- langchain 처럼 거부한다")
        self.args_schema = _schema_from_sig(fn)
        functools.update_wrapper(self, fn)

    def __call__(self, *a, **kw):
        return self.fn(*a, **kw)

    def declaration(self) -> dict:
        """Gemini functionDeclarations 원소."""
        return {"name": self.name, "description": self.description,
                "parameters": self.args_schema}

    def __repr__(self):
        return f"<Tool {self.name}>"


def tool(fn=None, *, name=None, description=None):
    """@tool 또는 @tool(name=..). langchain 과 같은 두 쓰임."""
    if fn is None:
        return lambda f: Tool(f, name=name, description=description)
    return Tool(fn, name=name, description=description)
