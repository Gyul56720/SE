"""
Gemini REST API 얇은 래퍼. SDK 버전 이슈를 피하려고 requests로 직접 호출한다.
(이미 연동된 Gemini가 SDK 기반이라면 이 파일만 그 SDK 호출로 바꿔치기하면 됨 -
 analyzer.py/research_graph.py는 generate()/generate_json() 시그니처만 보고 쓴다.)
"""

from __future__ import annotations
import json
import time
import requests

from config import GEMINI_API_KEY, GEMINI_MODEL

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _call(model: str, contents: list[dict], generation_config: dict | None = None,
          max_retries: int = 3) -> dict:
    url = ENDPOINT.format(model=model)
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    body = {"contents": contents}
    if generation_config:
        body["generationConfig"] = generation_config

    last_err = None
    for attempt in range(max_retries):
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:  # 무료 한도(RPM) 초과 - 잠깐 쉬고 재시도
            time.sleep(2 ** attempt * 5)
            last_err = f"429 rate limited: {resp.text[:200]}"
            continue
        raise RuntimeError(f"Gemini API 오류 {resp.status_code}: {resp.text[:300]}")
    raise RuntimeError(f"Gemini API 재시도 초과: {last_err}")


def generate(prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    """자유 텍스트 응답이 필요할 때."""
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    gen_config = {}
    result = _call(model or GEMINI_MODEL, contents, gen_config or None)
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Gemini 응답 형식: {json.dumps(result)[:300]}")


def generate_json(prompt: str, schema: dict, model: str | None = None) -> dict:
    """구조화 추출용. responseSchema로 강제해서 파싱 실패 확률을 크게 낮춘다."""
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    gen_config = {"responseMimeType": "application/json", "responseSchema": schema}
    result = _call(model or GEMINI_MODEL, contents, gen_config)
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Gemini 응답 형식: {json.dumps(result)[:300]}")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


if __name__ == "__main__":
    print(generate("한 문장으로 자기소개해줘"))
