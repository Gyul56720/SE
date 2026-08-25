"""
Gemini REST API 얇은 래퍼. SDK 버전 이슈를 피하려고 requests로 직접 호출한다.
(이미 연동된 Gemini가 SDK 기반이라면 이 파일만 그 SDK 호출로 바꿔치기하면 됨 -
 analyzer.py/research_graph.py는 generate()/generate_json() 시그니처만 보고 쓴다.)

이미지(수식 사진) 인식은 transfer_math_chatbot과 같은 Gemini 멀티모달 경로를 REST로
재구현한 것 -- generate()/generate_json()에 images 인자를 추가로 받는다.
"""

from __future__ import annotations
import base64
import json
import mimetypes
import re
import time
from pathlib import Path

import requests

from config import GEMINI_API_KEY, GEMINI_API_KEY_FALLBACK, GEMINI_MODEL

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# 기본 키가 429(쿼터 초과)로 완전히 막히면 이 순서대로 다음 키로 넘어가서 다시 시도한다.
_API_KEYS = [k for k in (GEMINI_API_KEY, GEMINI_API_KEY_FALLBACK) if k]


def _image_part(image_path: Path) -> dict:
    """이미지 파일을 REST inlineData 파트로 인코딩 (수식 사진 인식용)."""
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime_type, "data": data}}


def _build_parts(prompt: str, images: list[Path] | None) -> list[dict]:
    parts: list[dict] = [{"text": prompt}]
    for img in images or []:
        parts.append(_image_part(img))
    return parts


def _call(model: str, contents: list[dict], generation_config: dict | None = None,
          max_retries: int = 3) -> dict:
    url = ENDPOINT.format(model=model)
    body = {"contents": contents}
    if generation_config:
        body["generationConfig"] = generation_config

    if not _API_KEYS:
        raise RuntimeError("GEMINI_API_KEY가 비어 있다.")

    last_err = None
    for key_index, api_key in enumerate(_API_KEYS):
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        for attempt in range(max_retries):
            resp = requests.post(url, headers=headers, json=body, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:  # 무료 한도(RPM/일일 쿼터) 초과 - 잠깐 쉬고 재시도
                time.sleep(2 ** attempt * 5)
                last_err = f"429 rate limited (key {key_index+1}/{len(_API_KEYS)}): {resp.text[:200]}"
                continue
            raise RuntimeError(f"Gemini API 오류 {resp.status_code}: {resp.text[:300]}")
        # 이 키로는 max_retries를 다 써도 429 -- 다음 키(있으면)로 완전히 전환해서 다시 시도
        if key_index + 1 < len(_API_KEYS):
            print(f"[gemini_client] 키 {key_index+1}가 쿼터 초과로 보임 -- 보조 키로 전환.")
    raise RuntimeError(f"Gemini API 재시도 초과 (키 {len(_API_KEYS)}개 다 소진): {last_err}")


def generate(prompt: str, model: str | None = None, images: list[Path] | None = None) -> str:
    """자유 텍스트 응답이 필요할 때. images를 주면 멀티모달 요청(수식 사진 인식 등)."""
    contents = [{"role": "user", "parts": _build_parts(prompt, images)}]
    result = _call(model or GEMINI_MODEL, contents)
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Gemini 응답 형식: {json.dumps(result)[:300]}")


def _fix_stray_backslashes(text: str) -> str:
    """math_extractor.py처럼 LaTeX(\\frac, \\theta, \\underline 등)를 JSON 문자열 안에 담아달라고
    하면, Gemini가 이중이스케이프를 안 해서 \\f/\\t/\\b/\\r/\\u 같은 조합이 진짜 JSON 이스케이프
    (form feed/tab/backspace/...)로 오인된다. 의도된 이스케이프로 볼 만한 \\", \\\\, \\n만 남기고
    나머지 백슬래시는 전부 이중이스케이프해서 리터럴로 되살린다."""
    return re.sub(r'\\(?!["\\n])', r"\\\\", text)


def _has_corruption_markers(obj) -> bool:
    """_fix_stray_backslashes가 필요했는지 판단하는 신호. json.loads는 \\f/\\t/\\b/\\r를
    유효한 이스케이프로 보고 에러 없이 조용히 통과시키므로(실측: "\\frac{a}{b}" ->
    "\x0crac{a}{b}"), 파싱 자체는 성공해도 결과 문자열에 이 제어문자가 남아있으면 원문이
    LaTeX 백슬래시였는데 잘못 먹힌 것으로 본다 (이 앱의 텍스트 필드에 이 제어문자가 실제로
    의도적으로 들어갈 일은 사실상 없음)."""
    if isinstance(obj, str):
        return any(ch in obj for ch in "\x08\x09\x0c\x0d")
    if isinstance(obj, dict):
        return any(_has_corruption_markers(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_corruption_markers(v) for v in obj)
    return False


def _robust_json_loads(text: str) -> dict:
    """3단계 방어: (1) 있는 그대로 파싱 (2) 실패하면 보수적 sanitize 후 재시도
    (3) 그래도 실패하면(LaTeX가 한 응답 안에 여러 번, 겹쳐서, 혹은 예상 못 한 조합으로 깨진
    경우) 모든 백슬래시를 예외 없이 이중이스케이프하는 최종 폴백 -- 이러면 JSON 파싱은
    100% 성공한다(백슬래시 나열은 항상 유효한 JSON이므로). 대가로 이미 올바르게
    이중이스케이프된 아주 드문 케이스가 과도하게 이스케이프될 수 있지만, 실측상 Gemini가
    이 스키마들에서 스스로 올바르게 이중이스케이프하는 경우는 관측된 적이 없어 이 쪽이
    항상 더 안전하다."""
    try:
        data = json.loads(text)
        if not _has_corruption_markers(data):
            return data
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_fix_stray_backslashes(text))
    except json.JSONDecodeError:
        return json.loads(text.replace("\\", "\\\\"))


def generate_json(prompt: str, schema: dict, model: str | None = None,
                   images: list[Path] | None = None) -> dict:
    """구조화 추출용. responseSchema로 강제해서 파싱 실패 확률을 크게 낮춘다."""
    contents = [{"role": "user", "parts": _build_parts(prompt, images)}]
    gen_config = {"responseMimeType": "application/json", "responseSchema": schema}
    result = _call(model or GEMINI_MODEL, contents, gen_config)
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"예상치 못한 Gemini 응답 형식: {json.dumps(result)[:300]}")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return _robust_json_loads(text)


if __name__ == "__main__":
    print(generate("한 문장으로 자기소개해줘"))
