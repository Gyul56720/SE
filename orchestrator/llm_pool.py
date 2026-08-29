"""
쿼터에 견디는 LLM 호출기 -- orchestration의 모든 LLM 호출(플래너 등)이 공유한다.

문제 (실측, VM 로그): Gemini 무료 티어 쿼터는 (프로젝트, 모델) 단위 일일 한도라, 고정 모델
하나로 호출하면 곧 429 RESOURCE_EXHAUSTED 로 죽는다. 게다가 모델은 단종/개명(404, 400
"only supports Interactions API")되고 과부하(503)도 난다. 단일 ChatGoogleGenerativeAI
호출(improve_agent 초기판이 그랬다)은 이 순간 하나만 막혀도 전체가 멈춘다.

해결: 모든 LLM 호출을 (키 x 모델) 후보 풀로 돌린다. 이 저장소가 Discord 에이전트용으로 이미
쓰는 quota_tracker 를 그대로 재사용한다 --
  - 429(쿼터 소진): record_exhausted 로 오늘자 소진 표시 후 다음 후보.
  - 404/403(단종/유료전용): mark_dead 로 영구 제외(자정에도 안 풀림).
  - 503/500(일시 장애): 다음 후보(영구 제외 안 함).
  - 성공: record_success + 그 후보를 pin -> 다음 호출도 그걸 먼저.
이로써 "Gemini API 자동 변경"이 자동으로, 매 orchestration 호출마다 처리된다.

의존: quota_tracker(경량, 이 저장소) 만 필수. 실제 Gemini 클라이언트/모델 목록 조회는 지연
임포트하고, llm_factory 를 주입할 수 있어(테스트에서 목 주입) 폴백 로직만 따로 검증 가능하다.
에러 분류기는 bot_tools 와 같은 규칙(문자열 매칭)을 여기서도 갖는다 -- orchestrator 가
langchain 없이도 임포트되도록 자체 정의한다(규칙이 바뀌면 bot_tools 와 함께 갱신).
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # quota_tracker 임포트용
import quota_tracker  # noqa: E402

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]


def _is_quota(e) -> bool:
    t = str(e)
    return "RESOURCE_EXHAUSTED" in t or "429" in t


def _is_permanent(e) -> bool:
    t = str(e)
    return any(m in t for m in ("PERMISSION_DENIED", "403", "FAILED_PRECONDITION",
                                "NOT_FOUND", "404", "billing", "not supported", "not found"))


def _model_rank(model: str):
    n = model.lower()
    fam = 3 if "gemma" in n else 2 if "flash-lite" in n else 1 if "flash" in n else 0 if "pro" in n else 4
    return (fam, 1 if "preview" in n else 0)


def _key_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def _default_factory(model: str, key: str):
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=model, google_api_key=key)


def _default_models(key: str):
    try:
        from bot_tools import list_available_models
        return list_available_models(key) or FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def build_pool(keys=None, models=None, llm_factory=_default_factory, model_lister=_default_models):
    """(label, llm) 후보 목록. keys 기본 = 환경변수 두 키. models 기본 = 키별 실사용 모델 조회."""
    if keys is None:
        keys = [k for k in (os.environ.get("GEMINI_API_KEY"),
                            os.environ.get("GEMINI_API_KEY_FALLBACK")) if k]
    pool = []
    for key in keys:
        if not key:
            continue
        kid = _key_id(key)
        kmodels = models or model_lister(key)
        for m in kmodels:
            pool.append((f"key-{kid}:{m}", llm_factory(m, key)))
    return pool


def _extract_text(resp) -> str:
    content = getattr(resp, "content", resp)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)


def call(pool, prompt: str, pool_id: str = "orchestrator") -> tuple[str, str]:
    """후보를 쿼터/장애 견디며 순회. (응답텍스트, 성공한 label) 반환. 전부 실패면 예외."""
    live = [c for c in pool if not quota_tracker.is_dead(c[0])] or pool

    def sort_key(c):
        label = c[0]
        model = label.split(":", 1)[1] if ":" in label else label
        rem = quota_tracker.remaining(label)
        return (rem <= 0, _model_rank(model), -rem)

    ranked = sorted(live, key=sort_key)
    pinned = quota_tracker.get_pinned(pool_id)
    if pinned:
        ranked = [c for c in ranked if c[0] == pinned] + [c for c in ranked if c[0] != pinned]

    last_error = None
    for label, llm in ranked:
        try:
            text = _extract_text(llm.invoke(prompt))
            quota_tracker.record_success(label)
            quota_tracker.set_pinned(pool_id, label)
            return text, label
        except Exception as e:
            if _is_quota(e):
                quota_tracker.record_exhausted(label)
            elif _is_permanent(e):
                quota_tracker.mark_dead(label, str(e)[:200])
            # 일시 장애(503 등)는 기록 없이 다음 후보로.
            last_error = e
    raise last_error if last_error else RuntimeError("빈 후보 풀")
