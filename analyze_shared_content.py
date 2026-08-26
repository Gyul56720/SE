"""
공유 콘텐츠(예: Gemini 공유 링크 전문, 긴 대화록 등) 분석기.

기존 math_extractor.py/book_generator.py는 "논문"이나 "개념" 전용 스키마였는데, 이건 내용
종류를 모르는 임의의 긴 텍스트를 받아서 구조/핵심주장/수치/실행가능항목을 뽑는 범용 버전이다.
큰 원문은 이 스크립트가 통째로 읽어서 Gemini에 넘기고, Claude(대화)에는 구조화된 요약만
돌아가게 하는 것이 목적 -- 원문을 채팅에 붙여넣지 않기 위함.

사용법:
  1. inbox/gemini_share_content.txt 에 원문 전체를 붙여넣어 저장한다.
  2. python analyze_shared_content.py 실행.
  3. result/shared-analysis/ 에 구조화 리포트가 저장된다.
"""

from __future__ import annotations
from pathlib import Path

import gemini_client

INBOX = Path("inbox/gemini_share_content.txt")

PERSONA = """당신은 긴 문서/대화록을 분석해서 핵심을 구조화하는 애널리스트입니다.
원문에 없는 내용을 지어내지 않습니다. 원문이 불완전하거나 잘려 보이면 그렇다고 명시하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "content_type": {"type": "STRING", "description": "원문이 무엇인지(대화록/보고서/코드/기타)"},
        "core_summary": {"type": "STRING", "description": "핵심 내용 요약 (5-10문장)"},
        "key_points": {
            "type": "ARRAY", "description": "핵심 주장/사실/수치 5-10개",
            "items": {"type": "STRING"},
        },
        "actionable_items": {
            "type": "ARRAY", "description": "이 내용에서 실행/후속조치로 이어질 수 있는 항목",
            "items": {"type": "STRING"},
        },
        "caveats": {"type": "STRING", "description": "원문의 한계, 불확실한 부분, 잘린 것으로 보이는 부분"},
    },
    "required": ["content_type", "core_summary", "key_points", "actionable_items", "caveats"],
}

PROMPT_TMPL = PERSONA + """

아래는 사용자가 공유한 원문 전체다. 지정된 JSON 스키마로 분석하라. 반드시 한국어로.

--- 원문 시작 ---
{text}
--- 원문 끝 ---
"""


def run() -> Path:
    if not INBOX.exists() or not INBOX.read_text(encoding="utf-8").strip():
        raise RuntimeError(f"{INBOX}가 비어있다. 원문을 먼저 붙여넣어라.")
    text = INBOX.read_text(encoding="utf-8")
    print(f"[읽음] {INBOX} -- {len(text)}자")

    print("[Gemini 호출] 구조화 분석 중...")
    data = gemini_client.generate_json(PROMPT_TMPL.format(text=text[:400_000]), SCHEMA)

    key_points = "\n".join(f"- {k}" for k in data["key_points"])
    actions = "\n".join(f"- {a}" for a in data["actionable_items"]) or "- (없음)"

    content = f"""---
title: "공유 콘텐츠 분석 -- {data['content_type']}"
tags: [shared-content-analysis]
---

# 공유 콘텐츠 분석 ({data['content_type']})

## 핵심 요약

{data['core_summary']}

## 핵심 포인트

{key_points}

## 실행 가능 항목

{actions}

## 한계/주의사항

{data['caveats']}
"""
    out_dir = Path("result/shared-analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "분석결과.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}")
    return out_path


if __name__ == "__main__":
    run()
