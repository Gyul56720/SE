"""ChatModel -- langchain_google_genai.ChatGoogleGenerativeAI 자리.

**두 쓰임을 다 갖춘다.**
  1) `.invoke(prompt) -> Reply(.content)`  : 글만 넣고 글만 받는다(bot_tools 의 번역 등).
  2) `.call(contents, tools) -> dict`      : ReAct 고리가 도구를 붙여 부른다(functionCall).

에러 문자열 계약과 안전필터는 orchestrator.gemini_http 를 그대로 쓴다 -- 풀의 분류
(is_quota_error 등)가 그 문자열을 읽으므로 **한 출처**로 둔다. 키는 헤더로만 보낸다.

callbacks: HTTP 요청 **직전에** on_chat_model_start 를 부른다(rpmgate 분당 간격).
max_retries/timeout 를 인자로 받는다 -- bot_tools 가 그렇게 넘긴다(옛 ChatGoogleGenerativeAI
겉모습). 연결 자체가 안 될 때만 재시도하고, HTTP 응답(4xx/5xx)은 풀이 판단하게 올린다.
"""
from __future__ import annotations

import json

from orchestrator.gemini_http import API, SAFETY, GeminiError, Reply, _hide, _name_of
from se_agent import callbacks as _cb


class ChatModel:
    def __init__(self, model: str, google_api_key: str, max_retries: int = 2,
                 timeout: float = 60.0, callbacks=None, max_output_tokens: int = 8192):
        self.model = model
        self.key = google_api_key
        self.max_retries = max(1, int(max_retries))
        self.timeout = float(timeout)
        self.callbacks = list(callbacks or [])
        self.max_output_tokens = max_output_tokens

    def __repr__(self):
        return f"<Gemini {self.model}>"           # 키가 로그에 안 새게

    # --- 저수준 HTTP (연결 오류만 재시도, HTTP 오류는 올린다) ---
    def _post(self, body: dict) -> dict:
        import requests
        _cb.fire_start(self.callbacks)            # 요청 직전 분당 간격
        if SAFETY:
            body = {**body, "safetySettings": SAFETY}
        body.setdefault("generationConfig", {})["maxOutputTokens"] = self.max_output_tokens
        url = API.format(model=self.model)
        last = None
        for _ in range(self.max_retries):
            try:
                r = requests.post(url, headers={"x-goog-api-key": self.key},
                                  json=body, timeout=self.timeout)
            except Exception as e:                # 연결 실패만 재시도
                last = GeminiError(504, "DEADLINE_EXCEEDED",
                                   _hide(f"{type(e).__name__}: {e}", self.key))
                continue
            if r.status_code >= 400:
                try:
                    payload = r.json()
                except Exception:
                    payload = {}
                raise GeminiError(r.status_code, _name_of(payload, r.status_code),
                                  json.dumps(payload, ensure_ascii=False) or r.text)
            return r.json()
        raise last

    # --- 1) 글만 (도구 없음) ---
    def invoke(self, prompt, images=None) -> Reply:
        import base64
        parts = [{"inline_data": {"mime_type": m, "data": base64.b64encode(b).decode()}}
                 for m, b in (images or [])]
        parts.append({"text": _text_of(prompt)})
        data = self._post({"contents": [{"parts": parts}]})
        return Reply(_answer_text(data, allow_empty=False))

    # --- 2) 도구 붙여 (ReAct 고리용) ---
    def call(self, contents: list, tools: "list | None" = None) -> dict:
        """돌려주는 것: {"text": str, "tool_calls": [{"name","args","id"}, ...]}."""
        body = {"contents": contents}
        if tools:
            body["tools"] = [{"functionDeclarations": [t.declaration() for t in tools]}]
        data = self._post(body)
        return _parse_candidate(data)


def _text_of(prompt) -> str:
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, (list, tuple)):
        return "\n".join(_text_of(p) for p in prompt)
    return str(getattr(prompt, "content", prompt))


def _answer_text(data: dict, allow_empty: bool) -> str:
    cands = data.get("candidates") or []
    if not cands:
        fb = (data.get("promptFeedback") or {}).get("blockReason", "")
        raise GeminiError(200, f"EMPTY{'/' + fb if fb else ''}",
                          json.dumps(data, ensure_ascii=False))
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    out = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not out.strip() and not allow_empty:
        reason = cands[0].get("finishReason", "")
        raise GeminiError(200, f"EMPTY{'/' + reason if reason else ''}",
                          json.dumps(data, ensure_ascii=False))
    return out


def _parse_candidate(data: dict) -> dict:
    """functionCall 파트와 text 파트를 함께 뽑는다. 도구 호출 응답은 text 가 비어도
    정상이므로 EMPTY 로 던지지 않는다 -- 단, 파트가 아예 없으면(안전 차단 등) 던진다."""
    cands = data.get("candidates") or []
    if not cands:
        fb = (data.get("promptFeedback") or {}).get("blockReason", "")
        raise GeminiError(200, f"EMPTY{'/' + fb if fb else ''}",
                          json.dumps(data, ensure_ascii=False))
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    text, calls = "", []
    for i, p in enumerate(parts):
        if not isinstance(p, dict):
            continue
        if "text" in p:
            text += p.get("text", "")
        fc = p.get("functionCall")
        if isinstance(fc, dict) and fc.get("name"):
            calls.append({"name": fc["name"], "args": dict(fc.get("args") or {}),
                          "id": f"call_{i}"})
    if not text.strip() and not calls:
        reason = cands[0].get("finishReason", "")
        raise GeminiError(200, f"EMPTY{'/' + reason if reason else ''}",
                          json.dumps(data, ensure_ascii=False))
    return {"text": text, "tool_calls": calls}
