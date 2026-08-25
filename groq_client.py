"""
Groq REST API 얇은 래퍼. gemini_client.py/deepseek_client.py와 같은 generate()/
generate_json() 시그니처를 따른다. OpenAI 호환 엔드포인트, response_format=json_object로
"유효한 JSON 하나"만 보장받고 스키마는 프롬프트 텍스트로 설명해 넣는다. 이미지/PDF 입력은
지원하지 않는다 -- exam_verifier.py에서 이미 텍스트로 뽑아둔 problem_text/choices만
재사용하는 용도로 쓴다.
"""
from __future__ import annotations
import json
import time

import requests

from config import GROQ_API_KEY

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile는 2026-08 시점 Groq 카탈로그에서 빠짐


def _call(model: str, messages: list[dict], json_mode: bool = False, max_retries: int = 3) -> dict:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY가 비어 있다.")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages}
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    last_err = None
    for attempt in range(max_retries):
        resp = requests.post(ENDPOINT, headers=headers, json=body, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            time.sleep(2 ** attempt * 5)
            last_err = f"429 rate limited: {resp.text[:200]}"
            continue
        raise RuntimeError(f"Groq API 오류 {resp.status_code}: {resp.text[:300]}")
    raise RuntimeError(f"Groq API 재시도 초과: {last_err}")


def generate(prompt: str, model: str | None = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    result = _call(model or DEFAULT_MODEL, messages)
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Groq 응답 형식: {json.dumps(result)[:300]}")


def generate_json(prompt: str, schema: dict, model: str | None = None) -> dict:
    schema_instruction = (
        "\n\n반드시 다음 JSON 스키마를 따르는 하나의 JSON 객체로만 답하라 (다른 텍스트 금지):\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
    )
    messages = [{"role": "user", "content": prompt + schema_instruction}]
    result = _call(model or DEFAULT_MODEL, messages, json_mode=True)
    try:
        text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Groq 응답 형식: {json.dumps(result)[:300]}")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


if __name__ == "__main__":
    print(generate("한 문장으로 자기소개해줘"))
