"""eval/tasks(절대 기준 과제 원장)를 임시 저장소에서 가짜 풀이기로 **끝까지 돌려** 붙든다.

붙드는 것: (1) 판정은 코드가 한다 -- 실행 과제는 답 코드를 실제로 돌려 검사 끝값으로,
정답은 정규화 대조로, 담겨야는 낱말 포함으로. 모델이 "맞았다" 고 써도 소용없다,
(2) 참고 있음/없음을 같은 과제로 풀어 **이득**을 갈래별로 낸다 -- 참고를 봐야만 아는
풀이기로 지식 갈래 이득이 +로 잡힌다, (3) 준 참고(출처·해시)가 원장 줄에 남는다,
(4) 무한 루프·블록 없음·깨진 과제·죽는 호출에 죽지 않는다, (5) 같은 조건의 직전 바퀴보다
맞힘이 줄면 후퇴, (6) 진짜 과제 12개가 성하고 러너·배선·프롬프트에 걸려 있다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_eval_tasks.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from eval import tasks as T  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-tasks-"))
repo = 임시 / "repo"
(repo / "eval" / "tasks").mkdir(parents=True)
subprocess.run(["git", "init", "-q", str(repo)], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "첫"],
               env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}, check=True)


def 과제쓰기(t: dict):
    (repo / "eval" / "tasks" / f"{t['id']}.json").write_text(
        json.dumps(t, ensure_ascii=False), encoding="utf-8")


과제쓰기({"id": "코드-더하기", "과제갈래": "코드", "물음": "add(a,b) 를 써라",
        "판정": {"꼴": "실행", "검사": "import 답\nassert 답.add(2, 3) == 5\nprint('ok')\n"}})
과제쓰기({"id": "추론-둘", "과제갈래": "추론", "물음": "1+1 은?",
        "판정": {"꼴": "정답", "정답들": ["2", "둘"]}})
과제쓰기({"id": "지식-게이트", "과제갈래": "지식", "물음": "재작성을 막는 게이트는?",
        "깃발": ["게이트"], "판정": {"꼴": "정답", "정답들": ["G005"]}})
과제쓰기({"id": "지식-말", "과제갈래": "지식", "물음": "오답노트가 하지 말라는 것은?",
        "판정": {"꼴": "담겨야", "담겨야": ["상수", "붙여넣"]}})
(repo / "eval" / "tasks" / "깨진.json").write_text("{", encoding="utf-8")
과제쓰기({"id": "꼴없음", "과제갈래": "추론", "물음": "x", "판정": {"꼴": "점수"}})

가짜참고 = [{"출처": "memo/g005.md", "해시": "abc123", "깃발": ["게이트", "재작성"],
          "요약": "재작성 규범은 G005 게이트로 코드화되었다"}]


def 아는풀이기(prompt: str) -> dict:
    """참고를 봐야만 지식을 안다. 코드·추론은 참고와 무관하게 푼다."""
    참고봄 = "[참고" in prompt
    if "add(a,b)" in prompt:
        return {"답": "이렇게:\n```python\ndef add(a, b):\n    return a + b\n```\n", "id": None, "라벨": "가짜"}
    if "1+1" in prompt:
        return {"답": "하나 더 하나.\n답: 2", "id": None, "라벨": "가짜"}
    if "게이트는" in prompt:
        return {"답": ("답: G005" if 참고봄 else "답: 모르겠다"), "id": None, "라벨": "가짜"}
    if "오답노트" in prompt:
        return {"답": ("탐색 결과를 상수로 붙여넣지 마라" if 참고봄 else "모른다"), "id": None, "라벨": "가짜"}
    return {"답": "", "id": None, "라벨": "가짜"}


try:
    print("== 과제 읽기: 깨진 것은 거르고 성한 것만 ==")
    과제들, 거른 = T.과제읽기(repo)
    ok([t["id"] for t in 과제들] == ["지식-게이트", "지식-말", "추론-둘", "코드-더하기"],
       f"성한 과제 4개가 id 순으로 온다 ({[t['id'] for t in 과제들]})")
    ok(len(거른) == 2 and any("JSON" in x for x in 거른) and any("꼴" in x for x in 거른),
       f"깨진 JSON 과 모르는 꼴은 까닭과 함께 거른다 ({거른})")

    print("\n== 판정은 코드가 한다 ==")
    실행과제 = 과제들[3]
    ok(T.판정하기(실행과제, "```python\ndef add(a,b): return a+b\n```")[0] == "맞음", "맞는 코드는 맞음")
    판, 꼬리 = T.판정하기(실행과제, "정답입니다! 검사 통과했습니다.\n```python\ndef add(a,b): return a-b\n```")
    ok(판 == "틀림" and "AssertionError" in 꼬리, f"**틀린 코드는 '통과했다' 고 써도 틀림** ({꼬리[-60:]!r})")
    ok(T.판정하기(실행과제, "def add(a,b): return a+b")[0] == "틀림", "코드 블록이 없으면 틀림")
    ok(T.판정하기(실행과제, "```python\nimport 답\n```\n```python\ndef add(a,b):\n    return a+b\n```")[0] == "맞음",
       "블록이 여럿이면 마지막 것을 답으로 본다")
    판, 꼬리 = T.판정하기({"판정": {"꼴": "실행", "검사": "import 답\n", "초": 2}},
                    "```python\nwhile True: pass\n```")
    ok(판 == "틀림" and ("안 끝났다" in 꼬리 or "끊겼다" in 꼬리), f"**무한 루프는 시간 고삐로 끊긴다** ({꼬리})")
    ok(T.판정하기(과제들[2], "풀이...\n답: **2**")[0] == "맞음", "정답: 꾸밈 글자를 벗기고 견준다")
    ok(T.판정하기(과제들[2], "답: 3\n답: 둘")[0] == "맞음", "정답: 마지막 `답:` 줄을 본다")
    ok(T.판정하기(과제들[2], "풀이\n2")[0] == "맞음" and T.판정하기(과제들[2], "그냥 2")[0] == "틀림",
       "정답: `답:` 이 없으면 마지막 줄 통째로 -- 부분 일치는 없다")
    ok(T.판정하기(과제들[1], "상수로 붙여넣지 마라")[0] == "맞음"
       and T.판정하기(과제들[1], "상수를 쓰지 마라")[1].startswith("빠진 말"), "담겨야: 전부 있어야 맞음")

    print("\n== 참고 있음/없음 한 바퀴 -> 이득 ==")
    T.풀이 = 아는풀이기
    T.참고찾기 = lambda 물음, repo: (가짜참고 if "게이트" in 물음 or "오답노트" in 물음 else [])
    r = T.돌리기(["없음", "있음"], repo=repo)
    ok(r["돌았나"] and len(r["줄들"]) == 8, f"과제 4 x 조건 2 = 8줄 ({len(r['줄들'])})")
    없 = r["묶음들"]["없음"]
    있 = r["묶음들"]["있음"]
    ok(없["맞음"] == 2 and 있["맞음"] == 4, f"참고 없음 2/4 · 있음 4/4 ({없['맞음']}, {있['맞음']})")
    ok(r["이득"] == {"전체": 2, "코드": 0, "추론": 0, "지식": 2},
       f"**이득이 갈래별로 난다 -- 지식 +2, 나머지 0** ({r['이득']})")
    ok(없["틀린과제"] == ["지식-게이트", "지식-말"], f"틀린 과제 id 가 남는다 ({없['틀린과제']})")
    보 = T.보고(r)
    ok("지식 +2" in 보 and "참고의 이득: 전체 +2" in 보, "보고에 갈래별 이득이 찍힌다")
    ok(sorted(없["천장"]) == ["추론", "코드"] and 있["천장"] == [],
       f"**천장: 참고 없이 만점인 갈래를 코드가 표시한다** ({없['천장']})")
    ok("천장(눈금 없음): " in 보 and "더 어려운 과제" in 보, "보고가 천장을 말한다")

    print("\n== 원장: 준 참고가 줄에 남는다 ==")
    원장 = T.원장읽기(repo)
    과제줄 = [x for x in 원장 if x.get("꼴") == "과제"]
    묶음줄 = [x for x in 원장 if x.get("꼴") == "과제묶음"]
    ok(len(과제줄) == 8 and len(묶음줄) == 2, f"과제 8줄 + 묶음 2줄 ({len(과제줄)}, {len(묶음줄)})")
    지식있음 = [x for x in 과제줄 if x["과제"] == "지식-게이트" and x["참고"] == "있음"][0]
    ok(지식있음["참고들"] == [{"출처": "memo/g005.md", "해시": "abc123"}] and 지식있음["판정"] == "맞음",
       "**어떤 참고(출처·해시)를 줬는지 남는다** -- 가지치기의 재료")
    ok(all(x["참고들"] == [] for x in 과제줄 if x["참고"] == "없음"), "없음 조건은 참고들이 빈다")
    ok(all("갈래" not in x for x in 과제줄), "eval/run 의 갈래 키와 안 겹친다(과제갈래)")

    print("\n== 후퇴: 같은 조건의 직전보다 줄면 ==")
    def 잊은풀이기(prompt):
        return {"답": "답: 모르겠다", "id": None, "라벨": "가짜"}
    T.풀이 = 잊은풀이기
    r2 = T.돌리기(["없음"], repo=repo)
    ok(r2["묶음들"]["없음"]["흐름"] == "후퇴", f"2 -> 0 은 후퇴 ({r2['묶음들']['없음']['흐름']})")
    T.풀이 = 아는풀이기
    r3 = T.돌리기(["없음"], repo=repo)
    ok(r3["묶음들"]["없음"]["흐름"] == "향상", "0 -> 2 는 향상")

    print("\n== 죽는 호출·빈 과제 ==")
    def 죽는풀이기(prompt):
        raise RuntimeError("쿼터 소진")
    T.풀이 = 죽는풀이기
    r4 = T.돌리기(["없음"], repo=repo, 적기=False)
    ok(not r4["돌았나"] and all(x["판정"] == "못돌림" for x in r4["줄들"]), "전부 못 부르면 돌았나=False (끝값 3 감)")
    ok(not T.돌리기(["없음"], repo=repo, 갈래="지식", 과제id="없는", 적기=False)["돌았나"], "고른 과제가 없으면 안 돈다")
    T.풀이 = 아는풀이기
    r5 = T.돌리기(["없음"], repo=repo, 갈래="코드", 적기=False)
    ok(len(r5["줄들"]) == 1 and r5["줄들"][0]["과제"] == "코드-더하기", "--갈래 로 고른다")
finally:
    T.풀이 = None
    T.참고찾기 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 진짜 과제 12개와 배선 ==")
진짜, 거른 = T.과제읽기()
ok(len(진짜) >= 20 and not 거른, f"eval/tasks/ 과제 {len(진짜)}개 · 거름 {거른}")
ok({t["과제갈래"] for t in 진짜} == set(T.갈래이름들), "세 갈래가 다 있다")
for t in 진짜:
    if t["판정"]["꼴"] == "실행":
        판, 꼬리 = T.판정하기(t, "```python\n```")
        ok(판 == "틀림" and "ok" not in 꼬리, f"{t['id']}: 빈 답은 틀림 (검사가 헐겁지 않다)")
        if "본보기" in t:
            판, 꼬리 = T.판정하기(t, "```python\n" + t["본보기"] + "\n```")
            ok(판 == "맞음", f"{t['id']}: **본보기가 통과한다** (자가 넘을 수 있는 눈금이다) {꼬리[-80:]!r}")
ok(sum(1 for t in 진짜 if t["과제갈래"] == "추론") >= 8 and sum(1 for t in 진짜 if t["과제갈래"] == "코드") >= 8,
   "추론·코드에 눈금 과제가 더해졌다 (각 8개 이상)")
p = subprocess.run(["python3", "eval/tasks.py", "--목록"], cwd=str(뿌리), capture_output=True, text=True)
ok(p.returncode == 0 and "과제 20개" in p.stdout, "--목록 은 호출 없이 0")
from eval import run as 러너  # noqa: E402
ok(any(g["이름"] == "과제" and g["무게"] == "느림" for g in 러너.갈래들), "eval/run 갈래에 '과제'(느림)가 있다")
from router import call as R  # noqa: E402
ok("풀이기" in R.역할들, "router 역할표에 풀이기가 있다")
import dispatch  # noqa: E402
ok("과제" in (dispatch.run("!평가 과제", allow_write=False) or ""), "!평가 과제 가 배선되어 있다")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("eval/tasks.py" in _서버, "프롬프트가 eval/tasks.py 를 이름을 대고 시킨다")
_wire = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok("eval/tasks.py" in _wire, "배선 점검에 과제 목록이 들어 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("eval/tasks: 코드 판정 · 참고 이득 · 원장 참고들 · 후퇴 · 안 죽음 · 진짜 12개 -- 통과")
