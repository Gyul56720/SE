"""그림 한 장을 글로 옮긴다. **langchain 을 안 쓴다 -- 그래서 검사가 그냥 부를 수 있다.**

## 왜 있나 (실측 2026-09-15)

사용자가 문제 사진을 올렸는데 봇이 "아직 문제 이미지나 텍스트가 보이지 않습니다" 라고
답했다. 재 보니 그림을 볼 길이 **봇에만** 없었다. 저장소에는 이미 있었다 --
`orchestrator/gemini_http.py::invoke(prompt, images=)` 가 inline_data 로 그림을 싣고,
`llm_pool.call(..., images=)` 이 쿼터·재시도·모델 순위를 그대로 태운다. `law/ocr.py` 가
그 길로 시험지를 읽는다. 봇의 첨부 안내문만 "run_shell로 cat 해 보라" 였고, PNG 를 cat
하면 깨진 바이트다.

## 왜 `bot_tools.py` 안이 아닌가

`bot_tools` 는 맨 위에서 `langchain_core` · `langchain_google_genai` · `langgraph` 를
임포트한다. 그것들이 없는 데서는 **그 파일을 읽어 볼 수조차 없다** -- 검사가 못 돈다.
이 저장소가 셸 스크립트에서 배운 것이 그것이다: 안 돌려 본 검사는 초록불만 낸다.
그래서 속을 여기 두고 `bot_tools.read_image` 는 껍데기만 갖는다
(`filetools` · `channels` · `secret_filter` 와 같은 자리다).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 보낼 수 있는 꼴. 여기 없는 것은 **그림이 아니라고 말한다** -- 아무 바이트나 보내면
# 모델이 "안 보인다" 고 답하고, 그것이 사용자에게는 봇이 못 보는 것으로 보인다.
꼴 = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
     ".webp": "image/webp", ".gif": "image/gif", ".heic": "image/heic",
     ".pdf": "application/pdf"}
상한바이트 = 20 * 1024 * 1024      # inline_data 의 한계. 잘라 보내면 깨진 그림을 읽은 척한다


def 옮겨적기프롬프트(물음: str = "") -> str:
    """무엇을 시키는가. **지어내지 말라고 못박는 것**이 이 프롬프트의 전부다."""
    줄 = ["이 그림에 **적힌 것을 그대로** 글로 옮겨라. 네가 지어내지 마라.",
         "- 수식은 읽은 그대로. 지수·분수·근호가 있으면 그 꼴을 살려라",
         "- 문제 번호·보기(①②③④⑤)·표·그래프의 축과 눈금까지 빠짐없이",
         "- 글씨가 흐려 확실하지 않은 곳은 **[안 보임]** 이라고 적어라. 메우지 마라",
         "- 그림(도형·그래프)은 옮길 수 없으니 무엇이 그려져 있는지 말로 적어라"]
    물음 = (물음 or "").strip()
    if 물음:
        줄 += ["", "옮겨 적은 뒤, 아래 물음에 답하라.", f"물음: {물음}"]
    return "\n".join(줄)


def 읽기(path: str, question: str = "", repo: str = "", 자르개=None) -> str:
    """그림 한 장을 글로. 실패하면 **왜 못 읽었는지**를 돌려준다.

    이 함수는 아무것도 감추지 않는다 -- "보이지 않는다" 로 뭉개면 사용자는 봇이
    사진을 못 보는 줄 알고, 그것이 이 버그가 났을 때 실제로 일어난 일이다.
    """
    뿌리 = repo or os.path.dirname(os.path.abspath(__file__))
    쪽 = Path(path)
    if not 쪽.is_absolute():
        쪽 = Path(뿌리) / path
    if not 쪽.is_file():
        return f"[그림 없음] {쪽} -- 경로가 틀렸거나 첨부가 저장되지 않았다"
    mime = 꼴.get(쪽.suffix.lower())
    if mime is None:
        return (f"[그림 아님] {쪽.name} -- {' · '.join(sorted(꼴))} 만 읽는다. "
                f"글 파일이면 read_file 을 써라")
    바이트 = 쪽.read_bytes()
    if len(바이트) > 상한바이트:
        return (f"[너무 큼] {쪽.name} {len(바이트) // (1024 * 1024)}MB -- "
                f"{상한바이트 // (1024 * 1024)}MB 까지만 보낸다")

    sys.path.insert(0, os.path.join(뿌리, "orchestrator"))
    try:
        import llm_pool
    except Exception as e:                                        # noqa: BLE001
        return f"[그림 못 읽음] llm_pool 을 못 불렀다: {type(e).__name__}: {e}"
    # **gemma 를 뺀다.** 그림을 못 본다 -- 두면 그 후보가 이겨서 "안 보인다" 가 돌아온다
    # (`law/ocr.py` 가 같은 까닭으로 같은 줄을 쓴다).
    풀 = [c for c in llm_pool.build_pool() if "gemma" not in c[0].lower()]
    if not 풀:
        return "[그림 못 읽음] 그림을 볼 수 있는 후보가 없다 -- GEMINI_API_KEY 를 확인하라"
    try:
        글, 라벨 = llm_pool.call(풀, 옮겨적기프롬프트(question),
                               pool_id="read_image", images=[(mime, 바이트)])
    except Exception as e:                                        # noqa: BLE001
        return f"[그림 못 읽음] {type(e).__name__}: {str(e)[:200]}"
    return f"[{쪽.name} · {라벨}]\n" + (자르개(글) if 자르개 else 글)
