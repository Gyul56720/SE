"""
전역 설정.
다른 모든 모듈은 이 파일에서 설정값을 가져다 쓴다.
실제 값은 .env 파일에 채워넣는다 (.env.example을 복사해서 만들 것).
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- 선택적 백본 ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- 논문 소스 ---
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")
# Unpaywall API 식별용 이메일 (로그인/인증 아님, 무료 API 이용 약관상 요구되는 연락처일 뿐).
# 따로 안 채우면 OPENALEX_MAILTO를 재사용한다.
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "") or OPENALEX_MAILTO

# --- Obsidian ---
OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./vault_output")).expanduser()

# --- 기간 버킷 (자료 수집 Agent가 "기간별로 제시"할 때 쓰는 경계) ---
# 필요하면 여기만 고쳐서 버킷 구간을 조정
PERIOD_BUCKETS = [
    (2005, 2013),
    (2014, 2018),
    (2019, 2022),
    (2023, 2030),
]

if not GEMINI_API_KEY:
    print("[경고] GEMINI_API_KEY가 비어 있다. .env 파일을 확인할 것 (.env.example 참고).")

OBSIDIAN_VAULT_PATH.mkdir(parents=True, exist_ok=True)

# --- 도메인/키워드 폴더 구조 ---
# 예: note_folder("GEMM", "전자전기컴퓨터", "Survey Notes")
#     -> .../Paper Pipeline/전자전기컴퓨터/GEMM/Survey Notes
PAPER_PIPELINE_ROOT = OBSIDIAN_VAULT_PATH.parent
_BAD_PATH_CHARS = re.compile(r'[\\/:*?"<>|]')


def note_folder(keyword: str, domain: str | None, kind: str) -> Path:
    """kind: "Survey Notes" 또는 "Deep Reviews". 도메인이 있으면 <도메인>/<키워드>/<kind>로 중첩,
    없으면 <키워드>/<kind>."""
    keyword_clean = _BAD_PATH_CHARS.sub("_", keyword)
    if domain:
        domain_clean = _BAD_PATH_CHARS.sub("_", domain)
        return PAPER_PIPELINE_ROOT / domain_clean / keyword_clean / kind
    return PAPER_PIPELINE_ROOT / keyword_clean / kind
