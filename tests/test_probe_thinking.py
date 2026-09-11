"""probe_thinking 의 순수 부분을 붙든다 -- 망·키 없이 도는 것만. 실제 '생각 파트가 오는가' 는 VM 에서 찍는다.

붙드는 것: (1) 파트꼴이 str · dict 파트(extras 표시) · 그 밖을 구분한다, (2) 생각있나는 content ·
additional_kwargs · response_metadata · usage 어디에 thought/thinking 이 있어도 True, 없으면 False,
(3) 키가 없으면 main 이 '못잼' 으로 끝값 3 (모델을 안 부른다).

실행: python3 tests/test_probe_thinking.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace as NS

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
_spec = importlib.util.spec_from_file_location("probe_thinking", 뿌리 / "scripts" / "probe_thinking.py")
PT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PT)

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== 파트꼴 ==")
ok(PT.파트꼴("평문") == ["str"], "평문은 str")
ok(PT.파트꼴([{"type": "text", "text": "a"}, {"type": "text", "text": "b", "extras": {"signature": "x"}}, 3])
   == ["text", "text+extras", "int"], "dict 파트는 type(+extras), 그 밖은 형 이름")

print("\n== 생각있나: 코드 판정 ==")
ok(not PT.생각있나(NS(content="2", additional_kwargs={}, response_metadata={}, usage_metadata={})), "아무 데도 없으면 False")
ok(PT.생각있나(NS(content=[{"type": "thinking", "thinking": "..."}], additional_kwargs={}, response_metadata={}, usage_metadata={})),
   "content 파트에 thinking 이면 True")
ok(PT.생각있나(NS(content="2", additional_kwargs={}, response_metadata={}, usage_metadata={"output_token_details": {"reasoning": 12}})),
   "usage 에 reasoning 토큰이면 True")
ok(PT.생각있나("thought: 문자열 응답") and not PT.생각있나("문자열 응답"), "문자열 응답도 그대로 본다")

print("\n== 키 없으면 못잼(끝값 3), 모델을 안 부른다 ==")
from orchestrator import llm_pool  # noqa: E402
_원래 = llm_pool.api_keys
불림 = []
llm_pool.api_keys = lambda: []
llm_pool._default_factory = lambda m, k: (불림.append(m) or NS(invoke=lambda p: "x"))
try:
    ok(PT.main() == 3 and not 불림, "키 없음 -> 3, 호출 0회")
finally:
    llm_pool.api_keys = _원래

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("probe_thinking: 파트꼴 · 생각 판정 · 키 없음 -- 통과")
