---
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

FuriosaAI develops data center AI accelerators, and their RNGD accelerator excels at high-performance inference for LLMs and agentic AI.

## 모델 라인업 (Hugging Face)

- **furiosa-ai/Qwen3-Embedding-8B** (Embedding) — Sentence Similarity, 8B
- **furiosa-ai/Qwen3-Reranker-8B** (Reranker) — Text Classification, 8B
- **furiosa-ai/Qwen3-VL-32B-Thinking** (VLM) — Image-Text-to-Text, 33B
- **furiosa-ai/Qwen3-VL-32B-Instruct** (VLM) — Image-Text-to-Text, 33B
- **furiosa-ai/gpt-oss-120b** (LLM) — Text Generation, 117B
- **furiosa-ai/Solar-Open-100B-NVFP4A16** (LLM) — Text Generation, 60B

## SDK / 하드웨어 스택 (개발자 공식 문서)

- FuriosaAI RNGD NPU
- Furiosa-LLM
- PyTorch
- ONNX
- Cloud Native (Container/Kubernetes)
- Device Management (SMI)

## 배포 채널 (archive.furiosa.ai)

APT(Debian/Ubuntu) 패키지 저장소(archive.furiosa.ai) 및 furiosa-apt-key.gpg 공개키 제공, PyPI 등 다른 배포 채널도 운영 중인 것으로 보임

## Spaces 데모

- OCR: OCR(광학 문자 인식) 데모 Space, 구체적 모델명/프레임워크는 원문에서 확인 안 됨
- MOT: MOT(Multi-Object Tracking) 관련 Space, 사용 모델 및 프레임워크는 원문에서 확인 안 됨

## GitHub SDK 코드 구조

### furiosa-sdk

**목적**: deep-neural network inference using FuriosaAI NPU chips

**구조**:
  - .github/
  - .prow/
  - jenkins/
  - kubernetes/
  - tekton/
  - cpp/
  - python/
  - docs/
  - examples/
  - tests/
  - Dockerfile
  - README.md
  - LICENSE.txt
  - bors.toml
  - CHANGELOG.md

**언어**: Python + C++
**상태**: 활성(archived 아님, deprecated 문구 없음), 총 커밋 1,594개, 최신 릴리스 v0.9.0

### furiosa-models

**목적**: FuriosaAI NPU를 위한 공개 모델 동물원

**구조**:
  - .dvc
  - .github/workflows
  - docker/
  - docs/
  - licenses/
  - furiosa/models
  - tekton/
  - tests/
  - pyproject.toml
  - Makefile

**포함 모델**:
  - ResNet50
  - EfficientNetB0
  - EfficientNetV2-S
  - SSDMobileNet
  - SSDResNet34
  - YOLOv5M/L
  - YOLOv7w6Pose

**상태**: 최신 릴리스 v0.10.2(2024-05-29), 총 커밋 357개, archived/deprecated 문구 원문에서 확인 안 됨

## 지원자 관점 시사점

퓨리오사아이의 SDK 및 모델 스택은 RNGD NPU를 중심으로 고성능 LLM 및 멀티모달 모델 추론에 최적화되어 있습니다. 설계검증 및 시스템 SW 지원자는 PyTorch와 ONNX 같은 주요 프레임워크 연동, Furiosa-LLM 런타임, 그리고 쿠버네티스 기반의 클라우드 네이티브 배포 환경을 이해해야 합니다. 또한 컴파일러, 프로파일러, 그리고 FXB(Furiosa Executable Bundle) 구조를 통해 NPU 하드웨어와 소프트웨어가 어떻게 유기적으로 결합되는지 파악하는 것이 중요합니다.
