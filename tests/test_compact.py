"""compact(대화 간추리기)를 가짜 메시지로 붙든다 -- 격차표 '맥락 관리'.

붙드는 것: (1) 상한 미만이면 안 간추리고 이상이면 간추린다(코드 판정), (2) 요지는 코드가 만든다 --
사람 말·부른 도구·실패 줄·마지막 답 머리, 모델 호출 0회, (3) 메모가 public_agent_memory 에
front-matter 와 함께 쓰인다(graph/night 가 밤에 색인), (4) 씨앗은 한 번만 꺼내진다,
(5) 배선 -- invoke_with_recovery 가 씨앗을 앞에 붙이고 두 invoke 자리에서 간추린다.

LLM 없이 돈다. 실행: python3 tests/test_compact.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import compact  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 사람(t):
    return NS(type="human", content=t, tool_calls=[])


def 모델(t="", *calls):
    return NS(type="ai", content=t, tool_calls=[{"name": c, "args": {}, "id": c} for c in calls])


def 도구(name, t="..."):
    return NS(type="tool", content=t, name=name, tool_calls=None)


print("== 상한: 코드 판정 ==")
짧은 = [사람("안녕"), 모델("네")]
ok(not compact.간추릴때(짧은, 40), "상한 미만은 안 간추린다")
긴 = []
for i in range(14):
    긴 += [사람(f"부탁 {i}: 시세 봐 줘"), 모델("", "run_shell"), 도구("run_shell", "ok" if i % 5 else "실패: 403 막힘"), 모델(f"답 {i}")]
ok(len(긴) == 56 and compact.간추릴때(긴, 40), f"상한 이상이면 간추린다 ({len(긴)}줄)")

print("\n== 요지는 코드가 만든다 ==")
r = compact.요지(긴 + [사람("[이어짐] 지난 대화 ..."), 모델("", "search_memory", "run_shell"), 모델("마지막 답 여기")])
ok(r["깃발"] == ["run_shell", "search_memory"], f"부른 도구를 중복 없이 순서대로 ({r['깃발']})")
ok(len(r["사람말"]) == 14 and r["사람말"][0].startswith("부탁 0"), "사람 말만 모으고 [이어짐] 머리는 뺀다")
ok(r["실패"] and all("403" in s for s in r["실패"]) and len(r["실패"]) <= 5, f"실패 줄은 마지막 5개까지 ({len(r['실패'])})")
ok(r["마지막답"] == "마지막 답 여기", "마지막 답 머리")

임시 = Path(tempfile.mkdtemp(prefix="test-compact-"))
try:
    print("\n== 메모 + 씨앗 ==")
    상대, 씨 = compact.간추리기("thread-1", 긴, repo=임시)
    p = 임시 / 상대
    ok(p.is_file() and 상대.startswith("public_agent_memory/") and "_대화_thread-1" in 상대, f"메모가 쓰인다 ({상대})")
    본 = p.read_text(encoding="utf-8")
    ok(본.startswith("---\ntopic: '대화 간추림: thread-1'") and "## 부른 도구(깃발)" in 본 and "run_shell" in 본, "front-matter · 깃발")
    ok("## 실패·거절 줄" in 본 and "403" in 본, "실패 줄이 메모에 남는다(밤에 장기기억으로)")
    ok(씨.startswith("[이어짐]") and 상대 in 씨 and "search_memory 로 읽어라" in 씨, "씨앗 한 줄")
    ok(compact.씨앗꺼내기("thread-1") == 씨 and compact.씨앗꺼내기("thread-1") == "", "**씨앗은 한 번만 꺼내진다**")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 (bot_tools 원문) ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
ok("prompt = compact.씨앗꺼내기(base_thread_id) + prompt" in _도구, "invoke 앞에 씨앗을 붙인다")
ok(_도구.count('_간추림(base_thread_id, thread_map, result["messages"])') == 2, "두 invoke 자리 모두에서 간추린다")
ok("thread_map[base_thread_id] = f\"{base_thread_id}-{uuid.uuid4().hex[:8]}\"" in _도구, "간추린 뒤 실을 새로 잇는다(thread_map 회전)")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"compact.py"' in _wf, "compact 가 배포 경로에")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("compact: 상한 판정 · 코드 요지 · 메모 · 씨앗 · 배선 -- 통과")
