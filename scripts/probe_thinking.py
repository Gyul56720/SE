"""probe_thinking -- 응답 파트에 '생각(thinking)' 이 실제로 오는지 **한 번 찍어 본다.**

격차표(SE vs Claude Code) '생각 노출': "(나) 미확인 -- VM 에서 응답 파트 한 번 찍어 실제로 오는지
본 뒤 결정". 기억으로 결정하지 않는다. 이 스크립트가 관리 모델을 한 번 부르고 파트 꼴을
그대로 찍는다. 판정은 코드가: 생각 파트/생각 토큰 수가 보이면 True, 아니면 False, 키 없으면 못잼.

    python3 scripts/probe_thinking.py            # 끝값 0 찍었다 · 3 키 없음(못잼)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))


def 파트꼴(content) -> "list[str]":
    if isinstance(content, str):
        return ["str"]
    if isinstance(content, list):
        out = []
        for p in content:
            if isinstance(p, dict):
                out.append(str(p.get("type") or "dict") + ("+extras" if p.get("extras") else ""))
            else:
                out.append(type(p).__name__)
        return out
    return [type(content).__name__]


def 생각있나(resp) -> bool:
    덩어리 = json.dumps({"content": getattr(resp, "content", resp),
                      "kw": getattr(resp, "additional_kwargs", {}),
                      "meta": getattr(resp, "response_metadata", {}),
                      "usage": getattr(resp, "usage_metadata", {})}, default=str, ensure_ascii=False).lower()
    return any(k in 덩어리 for k in ("thought", "thinking", "reasoning"))


def main() -> int:
    from orchestrator import llm_pool
    keys = llm_pool.api_keys()
    if not keys:
        print("못잼 -- GEMINI_API_KEY 가 없다. VM(.env) 에서 돌려라")
        return 3
    model = os.environ.get("DISCORD_ADMIN_MODEL", "gemini-3.5-flash-lite")
    m = llm_pool._default_factory(model, keys[0][1])
    resp = m.invoke("1+1 은? 한 줄로 답하라.")
    content = getattr(resp, "content", resp)
    보 = {"모델": model, "클라이언트": llm_pool.CLIENT, "파트꼴": 파트꼴(content),
         "생각파트": 생각있나(resp),
         "메타키": sorted((getattr(resp, "response_metadata", {}) or {}).keys())[:12],
         "usage": getattr(resp, "usage_metadata", None)}
    print(json.dumps(보, ensure_ascii=False, default=str))
    print("판정: " + ("생각 파트/토큰이 **온다** -- 노출 여부를 설계할 수 있다" if 보["생각파트"]
                    else "생각 파트가 **안 온다** -- 노출할 것이 없다(이 모델·클라이언트에선)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
