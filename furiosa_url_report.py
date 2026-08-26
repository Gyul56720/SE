"""
FuriosaAI Hugging Face / 공식 문서 / 배포 URL 리서치 리포트 생성기 (company_role_report.py와 같은
grounding 원칙). WebFetch로 실제 확인한 페이지 텍스트만 근거로 주고, Gemini는 정리/구조화만 한다.

  python furiosa_url_report.py
"""

from __future__ import annotations
from pathlib import Path

import gemini_client

PERSONA = """당신은 반도체/AI 가속기 기업을 분석하는 테크 리서처입니다. 아래 "원문 발췌" 밖의
사실을 지어내지 않습니다. 원문에 없는 수치나 이름은 절대 만들지 말고, 불명확하면 "원문에서
확인 안 됨"이라고 명시하십시오."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "org_summary": {"type": "STRING", "description": "Hugging Face 조직 정보 기반 회사/제품 한 줄 요약"},
        "model_lineup": {
            "type": "ARRAY",
            "description": "Hugging Face에 공개된 모델/컬렉션 중 특징적인 것 5-10개",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "category": {"type": "STRING", "description": "예: LLM, VLM, Embedding, Reranker"},
                    "note": {"type": "STRING", "description": "크기/양자화/용도 등 원문 근거"},
                },
                "required": ["name", "category", "note"],
            },
        },
        "sdk_stack": {
            "type": "ARRAY",
            "description": "개발자 문서 기준 하드웨어/SDK/런타임/지원 프레임워크 항목",
            "items": {"type": "STRING"},
        },
        "deployment_channel": {"type": "STRING", "description": "APT 저장소(archive.furiosa.ai) 기준 배포 방식 요약"},
        "spaces_demo": {
            "type": "ARRAY",
            "description": "OCR/MOT Space 각각이 뭘 시연하는지, 원문에서 확인 안 되면 그렇게 명시",
            "items": {"type": "STRING"},
        },
        "github_sdk": {
            "type": "OBJECT",
            "description": "furiosa-sdk 저장소 구조/상태 요약 (죽은 저장소지만 참고용)",
            "properties": {
                "purpose": {"type": "STRING"},
                "structure": {"type": "ARRAY", "items": {"type": "STRING"}},
                "languages": {"type": "STRING"},
                "status": {"type": "STRING", "description": "최신 릴리스/커밋 수/archived 여부"},
            },
            "required": ["purpose", "structure", "languages", "status"],
        },
        "github_models": {
            "type": "OBJECT",
            "description": "furiosa-models 저장소 구조/상태 요약",
            "properties": {
                "purpose": {"type": "STRING"},
                "structure": {"type": "ARRAY", "items": {"type": "STRING"}},
                "included_models": {"type": "ARRAY", "items": {"type": "STRING"}},
                "status": {"type": "STRING"},
            },
            "required": ["purpose", "structure", "included_models", "status"],
        },
        "candidate_insight": {
            "type": "STRING",
            "description": "DV(설계검증)/System SW 지원자 관점에서 이 정보가 시사하는 것 2-4문장. 과장 금지.",
        },
    },
    "required": ["org_summary", "model_lineup", "sdk_stack", "deployment_channel", "spaces_demo",
                 "github_sdk", "github_models", "candidate_insight"],
}

PROMPT_TMPL = PERSONA + """

--- 원문 발췌 (WebFetch로 확인) ---

## Hugging Face 조직 (huggingface.co/furiosa-ai)
{hf_org}

## Hugging Face 모델 목록 (huggingface.co/furiosa-ai/models)
{hf_models}

## Hugging Face 컬렉션 (huggingface.co/furiosa-ai/collections)
{hf_collections}

## Space - OCR (huggingface.co/spaces/furiosa-ai/ocr)
{space_ocr}

## Space - MOT (huggingface.co/spaces/furiosa-ai/mot)
{space_mot}

## 개발자 공식 문서 (developer.furiosa.ai/v2026.3.0/en/)
{dev_docs}

## 배포 저장소 (archive.furiosa.ai)
{archive}

## GitHub - furiosa-sdk (github.com/furiosa-ai/furiosa-sdk, 죽은 저장소지만 참고용)
{github_sdk}

## GitHub - furiosa-models (github.com/furiosa-ai/furiosa-models)
{github_models}

위 원문만 바탕으로 지정된 JSON 스키마로 답하라. 반드시 한국어로.
"""


def run(sources: dict[str, str], out_dir: Path) -> Path:
    print("[Gemini 호출] FuriosaAI URL 리서치 정리 중...")
    prompt = PROMPT_TMPL.format(**sources)
    data = gemini_client.generate_json(prompt, SCHEMA)

    model_block = "\n".join(
        f"- **{m['name']}** ({m['category']}) — {m['note']}" for m in data["model_lineup"]
    )
    sdk_block = "\n".join(f"- {s}" for s in data["sdk_stack"])
    space_block = "\n".join(f"- {s}" for s in data["spaces_demo"])

    gh_sdk = data["github_sdk"]
    gh_sdk_struct = "\n".join(f"  - {s}" for s in gh_sdk["structure"])
    gh_sdk_block = f"""**목적**: {gh_sdk['purpose']}

**구조**:
{gh_sdk_struct}

**언어**: {gh_sdk['languages']}
**상태**: {gh_sdk['status']}"""

    gh_models = data["github_models"]
    gh_models_struct = "\n".join(f"  - {s}" for s in gh_models["structure"])
    gh_models_included = "\n".join(f"  - {s}" for s in gh_models["included_models"])
    gh_models_block = f"""**목적**: {gh_models['purpose']}

**구조**:
{gh_models_struct}

**포함 모델**:
{gh_models_included}

**상태**: {gh_models['status']}"""

    content = f"""---
title: "FuriosaAI - Hugging Face / 공식 문서 리서치"
tags: [career-plan, furiosa, tech-research]
sources:
  - https://huggingface.co/furiosa-ai
  - https://huggingface.co/furiosa-ai/models
  - https://huggingface.co/furiosa-ai/collections
  - https://huggingface.co/spaces/furiosa-ai/ocr
  - https://huggingface.co/spaces/furiosa-ai/mot
  - https://developer.furiosa.ai/v2026.3.0/en/
  - https://archive.furiosa.ai/
  - https://github.com/furiosa-ai/furiosa-sdk
  - https://github.com/furiosa-ai/furiosa-models
---

# FuriosaAI — Hugging Face / 공식 문서 / 배포 리서치

## 요약

{data['org_summary']}

## 모델 라인업 (Hugging Face)

{model_block}

## SDK / 하드웨어 스택 (개발자 공식 문서)

{sdk_block}

## 배포 채널 (archive.furiosa.ai)

{data['deployment_channel']}

## Spaces 데모

{space_block}

## GitHub SDK 코드 구조

### furiosa-sdk

{gh_sdk_block}

### furiosa-models

{gh_models_block}

## 지원자 관점 시사점

{data['candidate_insight']}
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Hugging Face-공식문서 리서치.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  -> {out_path}")
    return out_path


if __name__ == "__main__":
    sources = {
        "hf_org": """등록된 모델 47개. 대표 모델(최근 업데이트): furiosa-ai/Qwen3-Embedding-8B(Sentence Similarity, 8B),
furiosa-ai/Qwen3-Reranker-8B(Text Classification, 8B), furiosa-ai/Qwen3-VL-32B-Thinking(Image-Text-to-Text, 33B),
furiosa-ai/Qwen3-VL-32B-Instruct(Image-Text-to-Text, 33B), furiosa-ai/gpt-oss-120b(Text Generation, 117B),
furiosa-ai/Solar-Open-100B-NVFP4A16(Text Generation, 60B). 공개 데이터셋 없음. Space 3개(MOT, OCR 등).
조직 소개: "FuriosaAI develops data center AI accelerators. Our RNGD accelerator, currently sampling, excels
at high-performance inference for LLMs and agentic AI." 각 모델은 Furiosa Executable Bundle(FXB)을 포함해
RNGD 가속기에서 즉시 실행 가능하도록 구성됨. 팀 규모 51명.""",
        "hf_models": """Qwen3-Embedding-8B(문장 유사도, 1일 전), Qwen3-Reranker-8B(텍스트 분류, 1일 전),
Qwen3-VL-32B-Thinking(이미지-텍스트-텍스트, 7일 전), Qwen3-VL-32B-Instruct(이미지-텍스트-텍스트, 7일 전),
gpt-oss-120b(텍스트 생성, 7일 전), Solar-Open-100B-NVFP4A16(텍스트 생성, 7일 전),
Llama-3.3-70B-Instruct-FP8-dynamic(텍스트 생성, 7일 전), Qwen3-4B-FP8(텍스트 생성, 7일 전).
조직 총 모델 47개, 팀 멤버 51명.""",
        "hf_collections": """K-EXAONE: K-EXAONE-236B-A23B-NVFP4A16(138B). gpt-oss: gpt-oss-120b(117B), gpt-oss-20b(21B).
EXAONE 4: EXAONE-4.0-32B-FP8(32B). Qwen 2.5: 32B/14B/7B/0.5B-Instruct. Llama 3.3: 70B-Instruct-FP8-dynamic(71B),
70B-Instruct, 70B-Instruct-INT8. Solar Open: Solar-Open-100B-NVFP4A16(60B). Qwen3 Generation&Pooling:
32B-FP8(33B), 8B-FP8, 4B-FP8, 30B-A3B-FP8(31B). EXAONE 3.5: 7.8B-Instruct, 32B-Instruct. DeepSeek R1 Distill:
Llama-70B, Llama-8B, Qwen-7B, Qwen-14B. Llama 3.1: Meta-Llama-3.1-8B-Instruct-FP8-dynamic(8B),
Llama-3.1-8B-Instruct-FP8, Llama-3.1-8B-Instruct.""",
        "space_ocr": """OCR(광학 문자 인식) 데모 Space. 페이지 로드 시 "Refreshing" 상태만 확인됨 -- 구체적 모델명/
프레임워크는 원문에서 확인 안 됨(Files/Community 섹션 별도 확인 필요).""",
        "space_mot": """"Mot"라는 이름의 Space, 현재 "Running" 상태. MOT(Multi-Object Tracking) 관련 구체 설명,
사용 모델, 프레임워크는 원문에서 확인 안 됨(App/Files 탭 별도 확인 필요).""",
        "dev_docs": """지원 하드웨어: FuriosaAI RNGD NPU. 최신 SDK 버전 2026.3.0(이전 2026.2/2026.1/2025.X 존재).
주요 런타임: Furiosa-LLM(고성능 LLM 추론 엔진). 지원 프레임워크: PyTorch, ONNX. 문서 구성: Overview
("FuriosaAI offers a streamlined software stack designed for deep learning model inference"), Get Started(설치/
업그레이드/빠른시작), Furiosa-LLM(모델지원/API/예제/프로파일링), Cloud Native(컨테이너/Kubernetes 배포),
Device Management(SMI 시스템관리 인터페이스/튜닝). 지원 모델 예시: Qwen3 계열, Llama 3.1/3.3, GPT-OSS,
EXAONE 등 13개 이상. 저작권 2026 FuriosaAI Inc.""",
        "archive": """APT(Debian/Ubuntu) 패키지 저장소, PyPI 등 다른 배포 채널도 운영 중인 것으로 보임(단정 안 됨).
지원 OS: Ubuntu(명시적 확인). 디렉터리 구조: /ubuntu/(패키지 디렉터리), furiosa-apt-key.gpg(APT 서명용
공개키, 2025-11-20 업데이트).""",
        "github_sdk": """목적: "deep-neural network inference using FuriosaAI NPU chips"용 SDK -- 컴파일러,
프로파일러, 커맨드라인 도구, Python 바인딩 제공. 최상위 구조: .github/, .prow/, jenkins/, kubernetes/,
tekton/(CI/CD), cpp/(C++ 코드), python/(Python 코드), docs/, examples/, tests/, Dockerfile, README.md,
LICENSE.txt, bors.toml, CHANGELOG.md. 언어: Python + C++. 상태: 활성(archived 아님, deprecated 문구 없음),
총 커밋 1,594개, 최신 릴리스 v0.9.0, Apache-2.0 라이선스. 구체적 최근 커밋 날짜는 원문에서 확인 안 됨.""",
        "github_models": """목적: "FuriosaAI NPU를 위한 공개 모델 동물원" -- 학습/데모용 사전학습·양자화 모델
제공, ONNX/tflite 표준이라 CPU/GPU에서도 실행 가능, NPU용 최적화 전후처리 유틸리티와 컴파일러 설정 포함.
최상위 구조: .dvc, .github/workflows, docker/, docs/, licenses/, furiosa/models(핵심 코드), tekton/, tests/,
pyproject.toml, Makefile. 포함 모델: 이미지 분류(ResNet50, EfficientNetB0, EfficientNetV2-S), 물체 감지
(SSDMobileNet, SSDResNet34, YOLOv5M/L), 자세 추정(YOLOv7w6Pose). 상태: 최신 릴리스 v0.10.2(2024-05-29),
총 커밋 357개, archived/deprecated 문구 원문에서 확인 안 됨.""",
    }

    run(sources, Path("result/furiosa"))
