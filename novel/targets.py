"""**목표값은 표본에서 온다.** 우리가 지어낸 수가 아니라.

실측 2026-09-06. 표본 소설 154토막을 재고 우리가 요구하던 값과 나란히 놓아 보니
거의 다 틀렸다.

    긴 문장 몫   표본 0.03  <->  우리 요구 0.15 이상   (5배)
    점층         표본 0.09  <->  우리 요구 0.20        (2배)
    절 잇기      표본 0.36  <->  우리 상한 1.10        (3배 헐렁)
    대사 몫      표본 0.09  <->  우리 하한 0.10 + 갈래 0.12~0.50
    긴 대사      표본 0.00  <->  "120자 넘는 대사 하나 필수"

그리고 "45자 넘는 문장이 15%는 돼야 한다" 는 요구가 바로 -고 · -면서 늘어짐의
뿌리였다 -- 표본에 없는 목표를 맞추려니 절을 이어 붙인 것이다. **자가 원인을 지목한
것이 아니라 자 자체가 원인이었다.**

여기서는 표본의 10~90% 폭을 그대로 쓴다. 하한은 "표본 하위 10%보다 못하면 짚는다",
상한은 "상위 10%보다 심하면 짚는다" 는 뜻이다. 가운뎃값을 목표로 삼지 않는다 --
그러면 모든 덩어리가 가운뎃값이 되고, 표본 자체가 그렇지 않다.

targets.json 은 **수만** 담는다. 원문은 profile.py 에서 끝난다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATH = Path(os.environ.get("DRIFT_TARGETS", HERE / "targets.json"))

_CACHE: dict | None = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(PATH.read_text(encoding="utf-8")).get("axes", {})
        except Exception:
            _CACHE = {}                # 없으면 부르는 쪽의 기본값이 산다
    return _CACHE


def band(axis: str, default=None):
    """(하한, 상한). 표본의 10~90%다."""
    a = load().get(axis)
    return (a["lo"], a["hi"]) if a else default


def mid(axis: str, default=None):
    a = load().get(axis)
    return a["mid"] if a else default


def source() -> str:
    try:
        return json.loads(PATH.read_text(encoding="utf-8")).get("_source", "")
    except Exception:
        return ""
