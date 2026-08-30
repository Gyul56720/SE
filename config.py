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
# 기본 키가 429(쿼터 초과)에 걸렸을 때 자동 전환할 보조 키. 없으면 기존처럼 그냥 실패한다.
GEMINI_API_KEY_FALLBACK = os.getenv("GEMINI_API_KEY_FALLBACK", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# --- 선택적 백본 ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# --- 논문 소스 ---
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")
# Unpaywall API 식별용 이메일 (로그인/인증 아님, 무료 API 이용 약관상 요구되는 연락처일 뿐).
# 따로 안 채우면 OPENALEX_MAILTO를 재사용한다.
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "") or OPENALEX_MAILTO

# --- Obsidian ---
OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./vault_output")).expanduser()

# --- Discord 봇 ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
# 화이트리스트에 없는 유저는 무시한다 (봇이 있는 채널/서버 아무나가 아니라 지정한 유저만 사용 가능).
DISCORD_ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}

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
# Paper Pipeline 폴더보다 한 단계 위 (vault 루트). math_extractor.py의 "mathmetics" 폴더처럼
# 개별 논문 파이프라인 결과와 분리해서 vault 최상위에 둘 것들이 여기 기준으로 위치를 잡는다.
VAULT_ROOT = PAPER_PIPELINE_ROOT.parent
# math_extractor.py가 쓰는 것과 동일한 mathmetics 폴더 경로. main.py가 검색 결과(Survey Notes)를
# mathmetics 하위 서브폴더에 쓸 때도 이 상수를 그대로 재사용한다 -- math_extractor.py 자체의
# 동작(수학/구조 노트를 이 폴더 바로 밑에 평평하게 쓰는 것)은 절대 건드리지 않는다.
MATHMETICS_ROOT = VAULT_ROOT / "mathmetics"
_BAD_PATH_CHARS = re.compile(r'[\\/:*?"<>|]')


def note_folder(keyword: str, domain: str | None, kind: str, root: Path | None = None) -> Path:
    """kind: "Survey Notes" 또는 "Deep Reviews". 도메인이 있으면 <도메인>/<키워드>/<kind>로 중첩,
    없으면 <키워드>/<kind>. root를 안 주면 Paper Pipeline 밑, MATHMETICS_ROOT를 주면 mathmetics
    폴더 하위에 같은 규칙으로 중첩된다."""
    root = root or PAPER_PIPELINE_ROOT
    keyword_clean = _BAD_PATH_CHARS.sub("_", keyword)
    if domain:
        domain_clean = _BAD_PATH_CHARS.sub("_", domain)
        return root / domain_clean / keyword_clean / kind
    return root / keyword_clean / kind
