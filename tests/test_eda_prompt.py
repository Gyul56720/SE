"""회로 설계 물음이 **숙제 틀로 답해지지 않게** 하는 규칙이 두 채널에 다 들어갔나.

사용자(2026-09-15): "admin agent 에서 회로 설계 질문, '문제'로 파악하고 수학 문제
풀듯이 나온다. 디지털·아날로그 회로설계 부분은 따로 답하는 원칙에 어긋난다."

## 왜 갈렸나 -- 도구는 둘 다, 규칙은 한쪽만

`draw_circuit` · `run_spice` · `run_rtl` · `concept` 은 두 채널에 다 물려 있었다.
그런데 **갈래 규칙은 공개 프롬프트에만** 적혀 있었고, 관리 프롬프트에는

    문제가 오면 **풀이 · 약한 개념 · 오답노트 · 예상 질문과 답변** 넷을 다 내라.

가 예외 없이 적혀 있었다. 회로 물음이 그대로 그 숙제 틀로 들어갔다.

**도구를 물리는 것과 그것을 쓰라고 말하는 것은 다른 일이다.** 도구 배선만 검사하고
있었으므로(`test_spice` · `test_concepts` 의 [배선] 대목) 이 구멍은 안 보였다.

## 이 검사가 붙드는 것

1. 규칙이 **두 프롬프트에 다 있다** -- 한쪽만 고치면 빨개진다.
2. 규칙이 **숙제 틀보다 앞에 온다** -- 뒤에 있으면 이미 그 틀로 읽은 뒤다.
3. 규칙이 **한 자리에서 온다**(`eda_prompt.갈래규칙`) -- 베껴 적으면 또 갈린다.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import eda_prompt as e                                            # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


def 풀기(x):
    """리터럴 이어 붙이기와 `+ _eda.갈래규칙` 을 합성해 **런타임 글**을 만든다."""
    if isinstance(x, ast.Constant):
        return x.value
    if isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add):
        return 풀기(x.left) + 풀기(x.right)
    if isinstance(x, ast.Attribute):
        return e.갈래규칙
    raise TypeError(type(x).__name__)


def 프롬프트(파일: str, 이름: str) -> str:
    나무 = ast.parse((뿌리 / 파일).read_text(encoding="utf-8"))
    for n in ast.walk(나무):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == 이름
                                             for t in n.targets):
            return 풀기(n.value)
    raise AssertionError(f"{파일} 에 {이름} 이 없다")


채널 = (("discord_bot_server.py", "ADMIN_SYSTEM_PROMPT", "관리", "문제가 오면"),
       ("main_public.py", "PUBLIC_SYSTEM_PROMPT", "공개", "## 문제가 오면"))

print("\n[규칙] 두 채널에 다 있나")
글들 = {}
for 파일, 이름, 말, 틀 in 채널:
    글 = 프롬프트(파일, 이름)
    글들[말] = (글, 틀)
    ok(e.표 in 글, f"**{말} 채널에 갈래 규칙이 있다** (없으면 회로 물음이 숙제가 된다)")
    ok("숙제 틀로 답하지 마라" in 글, f"{말}: 그 말이 실제로 들어 있다")

print("\n[순서] 숙제 틀보다 **앞**에 오나")
for 말, (글, 틀) in 글들.items():
    i, j = 글.find(e.표), 글.find(틀)
    ok(j >= 0, f"{말}: 숙제 틀({틀!r})을 찾았다")
    ok(0 <= i < j,
       f"**{말}: 갈래 규칙({i})이 숙제 틀({j})보다 먼저** -- 뒤면 이미 그 틀로 읽은 뒤다")

print("\n[한 자리] 베껴 적지 않았나")
for 파일, 이름, 말, _ in 채널:
    src = (뿌리 / 파일).read_text(encoding="utf-8")
    ok("import eda_prompt" in src, f"{말}: `eda_prompt` 를 임포트한다")
    ok("_eda.갈래규칙" in src,
       f"**{말}: 글을 베끼지 않고 한 자리에서 가져온다** -- 베끼면 한쪽만 고쳐진다")
    ok("숙제 틀로 답하지 마라" not in src,
       f"{말}: 규칙 본문이 이 파일에 **직접 적혀 있지 않다**")

print("\n[알맹이] 규칙이 실제로 갈래를 가르나")
규 = e.갈래규칙
for 낱말, 까닭 in (("concept(", "개념부터 못 박으라고 한다"),
                ("draw_circuit", "그리라고 한다"),
                ("run_spice", "아날로그를 돌리라고 한다"),
                ("monte_carlo", "공정 산포를 보라고 한다"),
                ("run_rtl", "디지털을 돌리라고 한다"),
                ("prove_rtl", "형식 증명을 시킨다"),
                ("place_rtl", "실제 Fmax 를 재라고 한다"),
                ("손계산", "잰 것을 손계산과 나란히 놓으라고 한다"),
                ("못잼", "**못잼을 통과로 읽지 말라고 한다**"),
                ("한국어", "문제 풀이는 한국어라고 못 박는다"),
                ("영어", "설계는 영어라고 못 박는다")):
    ok(낱말 in 규, f"규칙이 `{낱말}` 을 말한다 -- {까닭}")

print("\n[끼우기] 두 번 끼우지 않는다")
한번 = e.끼우기("앞\n앵커\n뒤", "앵커")
ok(한번.count(e.표) == 1, "한 번 끼운다")
ok(e.끼우기(한번, "앵커").count(e.표) == 1,
   "**이미 있으면 안 끼운다** -- 두 벌이면 프롬프트가 늘어지기만 한다")
try:
    e.끼우기("앵커가 없는 글", "없는앵커")
    ok(False, "없는 앵커면 터진다")
except ValueError:
    ok(True, "**없는 앵커면 터진다** -- 조용히 안 끼우고 넘어가지 않는다")

for 말, (글, _) in 글들.items():
    ok(글.count(e.표) == 1, f"{말}: 규칙이 한 벌만 들어 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL[:5]}")
    sys.exit(1)
print("eda_prompt: 두 채널에 다 있고 · 숙제 틀보다 먼저 오고 · 한 자리에서 온다 -- 통과")
