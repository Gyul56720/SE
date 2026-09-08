"""**Gemini 를 직접 부른다.** langchain_google_genai 를 걷어낸 자리다.

왜 걷어냈나. `llm_pool.py` 는 613줄인데 langchain 을 실제로 부르는 것은 세 줄이었다 --
객체를 만들고, `.invoke(prompt)` 하고, 응답 껍질을 벗기는 것. 나머지 610줄(키 회전 ·
쿼터 추적 · 모델 순위 · 동시 발사 폭 · 429 복구 · 명부)은 전부 이 저장소가 직접 짠
것이다. 그리고 langchain 이 주는 것 하나는 **꺼야 했다**:

    "langchain 기본값(max_retries=6, timeout 없음)을 그대로 쓰면 실패하는 후보 하나가
     지수 backoff 로 30~50초를 먹고, timeout 이 없어 응답이 안 오는 요청은 영원히
     매달린다. **후보 풀 자체가 재시도 전략이므로** 한 후보 안에서 오래 버틸 이유가 없다."

추상화 비용은 내고 이득은 안 받는 모양이었다. 그리고 모델 목록 조회(`bot_tools.
list_available_models`)는 이미 `requests` 로 직접 부르고 있었다 -- 같은 API 를 한쪽은
직접, 한쪽은 langchain 을 거쳐 부르던 셈이다.

## 에러 문자열이 계약이다

풀의 분류(`_is_quota` · `_is_rpm` · `_is_permanent` · `_retry_delay`)는 **예외의
`str()` 을 읽는다.** 그래서 여기서 던지는 예외는 그 형태를 지켜야 한다:

    "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, ..., 'retryDelay': '27s'}}"

상태 코드 · 상태 이름 · 응답 본문을 그대로 담는다. 직접 짜면 이 문자열을 **우리가
통제하므로** 남의 래퍼가 무엇을 감싸 줄지 짐작할 필요가 없다.

## 한 후보 안에서 안 버틴다

HTTP 응답이 왔으면(429든 503이든) 그것은 **풀이 판단할 일**이다 -- 여기서 다시
던지지 않는다. 연결 자체가 안 된 경우(끊김 · 시간 초과)만 MAX_RETRIES 만큼 다시
해 본다. 그것도 풀의 다음 후보로 넘어가는 것보다 싸기 때문이다.

되돌리는 법: `GEMINI_CLIENT=langchain` 이면 예전 경로를 쓴다.
"""
from __future__ import annotations

import json
import os

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(RuntimeError):
    """**str() 이 곧 계약이다.** 풀의 분류가 이 문자열을 읽는다."""

    def __init__(self, status: int, name: str, body: str):
        self.status, self.name, self.body = status, name, body
        super().__init__(f"{status} {name}. {body}")


class Reply:
    """`.content` 로 읽는다 -- `llm_pool._extract_text` 가 그렇게 본다."""
    __slots__ = ("content",)

    def __init__(self, content: str):
        self.content = content


def _name_of(payload: dict, status: int) -> str:
    err = payload.get("error") or {}
    return str(err.get("status") or err.get("message") or status)


class Client:
    """한 (모델, 키) 조합. `invoke(prompt) -> Reply`.

    langchain 의 `ChatGoogleGenerativeAI` 가 있던 자리이고, 풀이 쓰는 것은 `.invoke`
    하나뿐이라 그것만 갖춘다."""

    def __init__(self, model: str, key: str, timeout: float = 60.0,
                 max_output_tokens: int = 8192, attempts: int = 2):
        self.model, self.key = model, key
        self.timeout, self.max_output_tokens = timeout, max_output_tokens
        self.attempts = max(1, attempts)

    def __repr__(self) -> str:              # 로그에 키가 안 새게
        return f"<Gemini {self.model}>"

    def invoke(self, prompt) -> Reply:
        import requests
        body = {"contents": [{"parts": [{"text": _text_of(prompt)}]}],
                "generationConfig": {"maxOutputTokens": self.max_output_tokens}}
        if SAFETY:
            body["safetySettings"] = SAFETY
        url = API.format(model=self.model)
        last = None
        for _ in range(self.attempts):
            try:
                # **키는 헤더로 보낸다. 절대 URL 에 싣지 않는다.**
                # `?key=...` 로 보내면 그 키가 **URL 의 일부**가 되고, URL 은 예외
                # 메시지에 그대로 실려 나온다 -- requests 의 연결 오류·시간 초과는
                # 요청 URL 을 문자열에 담는다. 아래 except 가 그 문자열을
                # GeminiError 본문으로 옮기고, 풀이 그것을 stderr 에 찍는다.
                # 그러면 **키가 로그에 남는다**(실측 2026-09-07: 사용자가 붙여넣은
                # 도구 출력에 키가 통째로 들어 있었다 -- 그 키는 폐기했다).
                # 헤더로 보내면 어떤 예외 문자열에도 키가 들어갈 자리가 없다.
                r = requests.post(url, headers={"x-goog-api-key": self.key},
                                  json=body, timeout=self.timeout)
            except Exception as e:
                # **연결이 안 된 것만 다시 해 본다.** 응답이 왔으면 그것은 풀이 판단한다.
                #
                # 그리고 **그 예외 문자열을 그대로 옮기지 않는다.** 남의 예외가 무엇을
                # 담고 있을지 우리가 정하지 못한다 -- requests 는 요청 URL 을 담고,
                # 프록시나 재지정이 끼면 우리가 안 만든 URL 도 담긴다. 위에서 키를
                # URL 에서 뺀 것이 첫 번째 벽이고, 이것이 두 번째 벽이다. 벽 하나는
                # 언젠가 뚫린다.
                last = GeminiError(504, "DEADLINE_EXCEEDED",
                                   _hide(f"{type(e).__name__}: {e}", self.key))
                continue
            if r.status_code >= 400:
                try:
                    payload = r.json()
                except Exception:
                    payload = {}
                # 본문을 **그대로** 실어야 retryDelay 같은 것이 분류에 닿는다.
                raise GeminiError(r.status_code, _name_of(payload, r.status_code),
                                  json.dumps(payload, ensure_ascii=False) or r.text)
            return Reply(_answer_of(r.json()))
        raise last


# **안전 필터.** 기본값은 전부 푼다 -- 이 저장소의 소설 파이프라인은 성인 연재물을
# 쓰고(사용자 요구 2026-09-08: "지금은 12세, 나는 19세 연재물"), Gemini 의 기본 문턱은
# 침소 장면과 폭력 장면에서 candidates 를 비운 채 200 을 준다. 그러면 _answer_of 가
# EMPTY/SAFETY 로 던지고, 풀은 그것을 일시장애로 세어 같은 프롬프트를 다른 키로 다시
# 두드린다 -- 호출만 태우고 원고는 안 온다.
#
# `GEMINI_SAFETY=default` 로 두면 Google 기본값으로 돌아간다. 법학 등 다른 파이프라인은
# 이 필터에 걸릴 글을 안 만드니 어느 쪽이든 같다. 계정 정책으로 막히는 범주는 이 설정과
# 무관하게 막힌다.
_SAFETY_OFF = [{"category": c, "threshold": "BLOCK_NONE"} for c in (
    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT")]
SAFETY = [] if os.environ.get("GEMINI_SAFETY", "off") == "default" else _SAFETY_OFF


def _hide(text: str, key: str) -> str:
    """글에서 키를 지운다. **아는 것만 지운다** -- 키처럼 생긴 것을 짐작으로 지우면
    진짜 오류 내용까지 지워 버린다."""
    return text.replace(key, "<키 가림>") if key else text


def _text_of(prompt) -> str:
    """풀은 문자열을 준다. 혹시 langchain 메시지 꼴이 와도 글자만 뽑는다."""
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, (list, tuple)):
        return "\n".join(_text_of(p) for p in prompt)
    return str(getattr(prompt, "content", prompt))


def _answer_of(data: dict) -> str:
    """**막힌 응답은 빈 글이 아니라 사실대로 던진다.** 안전 필터에 걸리거나 토큰을
    다 쓰면 candidates 가 비거나 parts 가 없는 채로 200 이 온다 -- 빈 글을 돌려주면
    풀은 성공으로 세고 원고에 빈 덩어리가 들어간다."""
    cands = data.get("candidates") or []
    if not cands:
        fb = (data.get("promptFeedback") or {}).get("blockReason", "")
        raise GeminiError(200, f"EMPTY{'/' + fb if fb else ''}",
                          json.dumps(data, ensure_ascii=False))
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    out = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not out.strip():
        reason = cands[0].get("finishReason", "")
        raise GeminiError(200, f"EMPTY{'/' + reason if reason else ''}",
                          json.dumps(data, ensure_ascii=False))
    return out
