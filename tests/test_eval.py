"""eval(통합 러너 · 답 회귀)을 **실제로 돌려** 붙든다.

붙드는 것: (1) 끝값 0/3/그외가 초록/못돌림/빨강으로 갈리고 못돌림은 초록 행세를
못 한다, (2) 원장에 쌓이고 직전과 견줘 **후퇴**(초록→빨강)와 회복이 갈린다,
(3) 답 회귀가 성한 표면은 통과시키고 깨진 기대는 어긋남으로 잡으며 모르는 꼴은
fail-closed 다, (4) 실제 questions.jsonl 이 지금 저장소에서 전부 통과한다,
(5) !평가 배선(공개 채널 거절 · runner 주입).

LLM·네트워크 없이 돈다(러너 갈래는 가짜 스크립트). 실행: python3 tests/test_eval.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from eval import answers, run as 러너  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-eval-"))
repo = 임시 / "repo"
repo.mkdir()
import subprocess
subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
(repo / "초록.py").write_text("print('다 좋다')\n", encoding="utf-8")
(repo / "빨강.py").write_text("print('무언가 틀렸다')\nraise SystemExit(1)\n", encoding="utf-8")
(repo / "재료없음.py").write_text("print('원장이 비어 있다: 어쩌고')\nraise SystemExit(3)\n",
                               encoding="utf-8")

가짜갈래 = [
    {"이름": "ㄱ", "명령": ["python3", "초록.py"], "초": 30, "무게": "빠름"},
    {"이름": "ㄴ", "명령": ["python3", "빨강.py"], "초": 30, "무게": "빠름"},
    {"이름": "ㄷ", "명령": ["python3", "재료없음.py"], "초": 30, "무게": "빠름"},
]

원래갈래 = 러너.갈래들
러너.갈래들 = 가짜갈래
try:
    print("== 끝값이 판정으로 갈린다 ==")
    결과 = 러너.돌리기(["ㄱ", "ㄴ", "ㄷ"], repo=repo)
    판 = {r["갈래"]: r for r in 결과}
    ok(판["ㄱ"]["판정"] == "초록", f"0 -> 초록 ({판['ㄱ']['판정']})")
    ok(판["ㄴ"]["판정"] == "빨강" and "틀렸다" in 판["ㄴ"]["꼬리"],
       "**그외 -> 빨강, 꼬리는 로그에서 적는다** (기억이 아니라)")
    ok(판["ㄷ"]["판정"] == "못돌림", f"3 -> 못돌림 ({판['ㄷ']['판정']}) -- 초록 행세 금지")
    ok((repo / "eval" / "ledger.jsonl").is_file(), "원장에 쌓인다")

    print("\n== 직전과 견줘 후퇴/회복을 말한다 ==")
    (repo / "초록.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    (repo / "빨강.py").write_text("print('고쳤다')\n", encoding="utf-8")
    결과 = 러너.돌리기(["ㄱ", "ㄴ", "ㄷ"], repo=repo)
    판 = {r["갈래"]: r for r in 결과}
    ok(판["ㄱ"].get("흐름") == "후퇴", f"**초록→빨강 = 후퇴** ({판['ㄱ'].get('흐름')})")
    ok(판["ㄴ"].get("흐름") == "회복", f"빨강→초록 = 회복 ({판['ㄴ'].get('흐름')})")
    ok(판["ㄷ"].get("흐름") == "여전", f"못돌림→못돌림 = 여전 ({판['ㄷ'].get('흐름')})")
    보 = 러너.보고(결과)
    ok("후퇴" in 보, "보고문이 후퇴를 크게 적는다")
finally:
    러너.갈래들 = 원래갈래
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 답 회귀: 깨진 기대를 잡고, 모르는 꼴은 fail-closed ==")
어긋 = answers.행검사({"물음": "!소설", "꼴": "고정명령", "담겨야": ["소설"]})
ok(not 어긋, f"성한 행은 통과 ({어긋})")
어긋 = answers.행검사({"물음": "!소설", "꼴": "고정명령", "담겨야": ["양자컴퓨터"]})
ok(어긋 and "담겨야" in 어긋[0], f"없는 말 기대는 어긋남 ({어긋})")
어긋 = answers.행검사({"물음": "오늘 뭐 먹지", "꼴": "고정명령"})
ok(어긋 and "배선" in 어긋[0], "고정 명령이 아닌 것을 고정명령이라 기대하면 어긋남")
어긋 = answers.행검사({"물음": "!소설", "꼴": "에이전트로"})
ok(어긋 and "삼켰다" in 어긋[0], "고정 명령이 받는 것을 에이전트로 기대하면 어긋남")
어긋 = answers.행검사({"물음": "x", "꼴": "이상한꼴"})
ok(어긋 and "성하지 않은" in 어긋[0], "**모르는 꼴은 통과가 아니라 어긋남이다** (fail-closed)")
어긋 = answers.행검사({"물음": "없는깃발없는말999", "꼴": "색인"})
ok(어긋 and "못 찾는다" in 어긋[0], "색인에 없는 것은 못 찾는다고 말한다")

print("\n== 실제 물음 원장이 지금 저장소에서 통과한다 ==")
행들 = [json.loads(x) for x in (뿌리 / "eval" / "questions.jsonl")
       .read_text(encoding="utf-8").splitlines() if x.strip()]
어긋수, lines = answers.전부검사(행들)
ok(어긋수 == 0, f"questions.jsonl {len(행들)}행 전부 통과 (어긋남 {어긋수})")
if 어긋수:
    print("\n".join(lines))

print("\n== !평가 배선 ==")
import dispatch  # noqa: E402
답 = dispatch.run("!평가", allow_write=False)
ok(답 is not None and "관리 채널" in 답, "공개 채널에서는 안 돌린다")
불림 = []


def 가짜러너(이름들):
    불림.append(이름들)
    return [{"갈래": x, "판정": "초록", "끝값": 0, "걸린초": 0.0, "꼬리": ""} for x in 이름들]


답 = dispatch.run("!평가", runner=가짜러너, allow_write=True)
ok(불림 and all(x in 불림[0] for x in ("게이트", "답")),
   f"빠른 갈래가 러너로 넘어간다 ({불림})")
ok(답 is not None and "OK" in 답, "보고가 답이 된다")
ok(dispatch.run("!평가서 좀 써줘") is None, "붙여 쓴 `!평가서` 는 명령이 아니다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("eval: 판정 가름 · 후퇴/회복 · 답 회귀 fail-closed · 실원장 통과 · 배선 -- 통과")
