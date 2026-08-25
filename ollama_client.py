"""
로컬 Ollama 서버 얇은 래퍼. gemini_client.py/groq_client.py/deepseek_client.py와 같은
generate()/generate_json() 시그니처를 따른다.

Groq의 allam-2-7b 테스트에서 저사양 모델이 "스키마를 텍스트로 설명 + 프롬프트로 지시"
방식으로는 JSON 자체를 못 지키고 붕괴하는 걸 실측했다 (실측: "몇느 별" 같은 무의미 텍스트).
Ollama는 format 파라미터에 JSON Schema를 넘기면 grammar-constrained decoding으로
토큰 샘플링 자체를 스키마에 맞는 것만 나오게 강제한다 -- 모델이 "알아서 잘 따르길"
기대하는 게 아니라 디코딩 레벨에서 강제하는 것이라, 모델이 약해도 최소한 "유효한 JSON"은
보장된다(내용 품질은 별개).

이 프로젝트의 스키마(SOLVE_SCHEMA 등)는 Gemini responseSchema 방언이라 타입이
"OBJECT"/"STRING"/"ARRAY"/"BOOLEAN"(대문자)이다. 표준 JSON Schema는 소문자
("object"/"string"/...)를 쓰므로 _to_json_schema()가 재귀적으로 변환해서, 기존
스키마를 그대로 재사용할 수 있게 한다.
"""
from __future__ import annotations
import json

import requests

from config import OLLAMA_HOST, OLLAMA_MODEL

ENDPOINT = f"{OLLAMA_HOST}/api/chat"

_GEMINI_TO_JSONSCHEMA_TYPE = {
    "OBJECT": "object", "STRING": "string", "ARRAY": "array",
    "BOOLEAN": "boolean", "NUMBER": "number", "INTEGER": "integer",
}


def _to_json_schema(schema):
    """Gemini responseSchema 방언(대문자 타입, camelCase 없음)을 표준 JSON Schema로
    재귀 변환한다. 이미 표준(소문자) 스키마면 그대로 통과시킨다."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k == "type" and isinstance(v, str):
                out[k] = _GEMINI_TO_JSONSCHEMA_TYPE.get(v, v.lower())
            else:
                out[k] = _to_json_schema(v)
        return out
    if isinstance(schema, list):
        return [_to_json_schema(v) for v in schema]
    return schema


def _call(model: str, messages: list[dict], format_: dict | str | None = None) -> dict:
    body = {"model": model, "messages": messages, "stream": False}
    if format_ is not None:
        body["format"] = format_
    try:
        resp = requests.post(ENDPOINT, json=body, timeout=300)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Ollama 서버({OLLAMA_HOST})에 연결 못 함 -- 'ollama serve' 돌고 있는지, "
            f"모델이 pull 돼 있는지(`ollama pull {model}`) 확인할 것: {e}"
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama API 오류 {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def generate(prompt: str, model: str | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    result = _call(model or OLLAMA_MODEL, messages)
    try:
        return result["message"]["content"]
    except KeyError:
        raise RuntimeError(f"예상치 못한 Ollama 응답 형식: {json.dumps(result)[:300]}")


def generate_json(prompt: str, schema: dict, model: str | None = None) -> dict:
    """format에 JSON Schema를 넘겨서 grammar-constrained 디코딩으로 강제한다 --
    프롬프트 텍스트로 스키마를 설명하기만 하는 deepseek_client.py/groq_client.py
    방식보다 저사양 모델에서 훨씬 안전하다."""
    messages = [{"role": "user", "content": prompt}]
    json_schema = _to_json_schema(schema)
    result = _call(model or OLLAMA_MODEL, messages, format_=json_schema)
    try:
        text = result["message"]["content"]
    except KeyError:
        raise RuntimeError(f"예상치 못한 Ollama 응답 형식: {json.dumps(result)[:300]}")
    return json.loads(text)


if __name__ == "__main__":
    print(generate("한 문장으로 자기소개해줘"))
