"""!자가개선 을 임시 저장소 + 진짜 sandbox·plan 으로 **끝까지 돌려** 붙든다. 모델·망만 가짜.

사용자(2026-09-11): "시스템을 개선할 방법을 스스로 탐색해서 제안한 뒤에 샌드박스에서 시뮬레이션하고
성능 평가가 이루어졌다고 판단되면 사용자의 동의를 구하고 자가 개선한다. 제2의 뇌를 근거로 하고,
탐색 범위가 부족하면 스스로 넓힌다."

붙드는 것: (1) 틈의 판정 명령이 실제 트리에서 빨강일 때만 틈이다(초록이면 '이미초록'),
(2) 제2의 뇌에 근거가 모자라면 스스로 넓혀 모은다(확장바퀴 상한), (3) 제안은 **그림자에만** 닿고
red->green 이 뒤집혀야 하며 리허설이 초록이어야 **동의 대기**가 된다 -- 실제 트리는 그대로,
(4) 사람이 승인해야 붙는다(봇은 dispatch 로 승인 못 침), (5) 안 고쳐지는 제안은 버리고 다음 후보,
(6) 검사를 약화시키는 패치·게이트를 만지는 패치는 거절, (7) 계획판이 켜져 있으면 안 돈다,
(8) 후보 상한 5, (9) 원장·메모, (10) 배선(명령·자연어·6h 루프·배포·union).

실행: python3 tests/test_improve.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from improve import run as I  # noqa: E402
from plan import store as P   # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
d = Path(tempfile.mkdtemp(prefix="test-improve-"))
초록리허설 = lambda repo, 판, 초, 전부=False, 전부초=1800: {  # noqa: E731
    "판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("문법", 0, ""), ("게이트", 0, "")],
    "통과": True, "못잼": [], "걸린초": 0.1}
틈 = {"종류": "CI실패검사", "무엇": "test_mod.py", "판정명령": "python3 tests/test_mod.py", "왜": "main CI 가 빨강이다"}
고치는패치 = json.dumps({"꼴": "패치", "왜": "f 가 2를 돌려 검사가 깨진다 -> 1", "근거": ["dig/corpus/x.md#abc"],
                    "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
try:
    git(d, "init", "-q")
    (d / "gatekeeper.py").write_text("import sys\nprint('[게이트 통과] 흉내')\nsys.exit(0)\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    (d / "tests" / "test_mod.py").write_text('import sys; sys.path.insert(0, ".")\nimport mod\nassert mod.f() == 1, "f 는 1"\nprint("ok")\n', encoding="utf-8")
    git(d, "add", "-A"); git(d, "commit", "-qm", "bug")

    from research import run as Rs
    Rs.분해기 = lambda 목표, 막힌것: "general method one\ngeneral method two"   # 모델 없이 빠르게
    I.틈모으기_ = lambda repo: [틈]
    P.리허설기 = 초록리허설
    넓힌 = []
    I.넓히기_ = lambda 질의들, repo: 넓힌.append(list(질의들))

    print("== 근거: 제2의 뇌가 비면 스스로 넓힌다 (상한까지) ==")
    근 = I.근거모으기(틈, d)
    ok(근["확장"] == I.확장바퀴 and len(넓힌) == I.확장바퀴 and 근["참고"] == [], f"**참고 0 -> {I.확장바퀴}바퀴 넓혀 모았다** (질의 {len(근['질의'])}개)")
    ok(all(q for qs in 넓힌 for q in qs), "넓힐 때 일반 방법론 질의를 준다(기계 일반화라도)")

    print("\n== 탐색 -> 제안 -> 그림자 시뮬 -> 동의 대기 (실제 트리는 그대로) ==")
    I.제안기 = lambda prompt: 고치는패치
    r = I.자가개선(d, 몇=3)
    후 = r["동의대기"]
    ok(r["돌았나"] and 후 is not None and 후["판정"] == "동의대기", f"동의 대기 후보가 생긴다 ({[x['판정'] for x in r['해본']]})")
    ok((d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n", "**실제 트리는 안 바뀌었다**")
    ok(P.현재판(d) is not None and str(P.읽기(d)["요청"]).startswith("자가개선:"), "그림자 계획판이 열려 동의를 기다린다")
    ok(후["댄근거"] == ["dig/corpus/x.md#abc"] and "근거" in I.보고(r), "제안이 댄 근거(출처#해시)가 보고에 남는다")
    ok("+    return 1" in 후["diff"] and "-    return 2" in 후["diff"], "diff 가 사람에게 보인다")
    ok("사람의 동의" in 후["말"] and "red->green" in 후["말"], "red->green · 리허설 초록 뒤 동의를 기다린다고 말한다")
    본 = (d / r["메모"]).read_text(encoding="utf-8")
    ok("자가개선 탐색" in 본 and "동의 대기" in 본, "메모가 남는다(밤에 장기기억으로)")
    꼴들 = [x.get("꼴") for x in I.원장읽기(d)]
    ok(["탐색", "후보", "끝"] == [k for k in 꼴들 if k in ("탐색", "후보", "끝")], f"원장 탐색/후보/끝 ({꼴들})")

    print("\n== 사람이 승인해야 붙는다 ==")
    ok("계획판이 이미 켜져 있다" in I.자가개선(d)["남은것"], "동의 대기 중엔 또 돌지 않는다(한 번에 하나)")
    말 = I.승인(d, 누가="검사")
    ok("적용됨" in 말 and (d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 1\n", f"**승인하면 실제 트리에 붙는다** ({말[:40]})")
    ok(P.현재판(d) is None and any(x.get("꼴") == "승인" for x in I.원장읽기(d)), "계획판이 닫히고 승인이 원장에 남는다")
    git(d, "commit", "-qam", "improved")
    r2 = I.한후보(틈, d)
    ok(r2["판정"] == "이미초록", "고친 뒤엔 같은 틈이 '이미초록' 이다 -- 틈이 아니다")

    print("\n== 안 고쳐지는 제안은 버리고 다음 후보로 ==")
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "bug again")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 3"}]})
    r = I.자가개선(d, 몇=3)
    ok(r["동의대기"] is None and r["해본"][0]["판정"] == "빨강그대로" and P.현재판(d) is None,
       f"**패치를 붙여도 빨강이면 버린다** ({r['해본'][0]['판정']})")
    ok((d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n", "실제 트리는 그대로")

    print("\n== 검사를 약화시키는 패치 · 게이트를 만지는 패치는 거절 ==")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "tests/test_mod.py", "old": 'assert mod.f() == 1, "f 는 1"\n', "new": ""}]})
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "적용실패" and "약화" in r["해본"][0]["말"], "**assert 를 빼는 패치는 거절**")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "새파일": [{"path": "gates/G999_x.py", "내용": "RULE_ID='G999'\n"}]})
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "적용실패", f"**gates/ 를 만드는 패치는 거절**(toolgate) ({r['해본'][0]['말'][:50]})")
    I.제안기 = lambda prompt: "고칠 수 없다"
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "제안없음", "패치 꼴이 아니면 제안없음")

    print("\n== 리허설 빨강이면 붙이지 않는다 ==")
    I.제안기 = lambda prompt: 고치는패치
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {"판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("게이트", 1, "G0 위반")], "통과": False, "못잼": [], "걸린초": 0.1}
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "리허설빨강" and P.현재판(d) is None, "**red->green 이어도 리허설이 빨강이면 버린다**")
    P.리허설기 = 초록리허설

    print("\n== `!개선 <말>`: 사람이 말한 개선 -- red->green 이 아니라 **레포 전체 회귀 없음**이 판정 ==")
    I.틈모으기_ = lambda repo: [틈]
    본판 = {"전부": None}

    def 리허설_회귀없음(repo, 판, 초, 전부=False, 전부초=1800):
        본판["전부"] = 전부
        return {"판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("레포 전체(회귀)", 0, "새로 깨진 것 없음")],
                "통과": True, "못잼": [], "걸린초": 1.0, "회귀": {"새로깨짐": [], "고쳐짐": [], "그대로빨강": []}}
    P.리허설기 = 리허설_회귀없음
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "부탁대로 고침", "근거": ["arxiv#1"],
                                      "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
    r = I.사용자개선("f 가 1을 돌려주게 해줘", d, 초=30)
    ok(r["판정"] == "동의대기" and 본판["전부"] is True,
       f"**부탁은 레포 전체 시뮬을 거쳐 동의 대기** (판정 {r['판정']}, 전부={본판['전부']})")
    ok(r["회귀"] == {"새로깨짐": [], "고쳐짐": [], "그대로빨강": []} and "회귀 없음" in I.부탁보고(r), "회귀 결과가 보고에 남는다")
    ok(r["댄근거"] == ["arxiv#1"] and (d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n",
       "근거를 대고, 실제 트리는 그대로")
    ok("판열림" == I.사용자개선("또", d)["판정"], "동의 대기 중엔 또 안 받는다")
    ok("적용됨" in I.승인(d, 누가="검사"), "`!개선 승인` 으로 붙는다")
    git(d, "commit", "-qam", "부탁 반영")

    print("\n== 멀리서 깨뜨리면 거절한다 ==")
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "again")
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {
        "판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("레포 전체(회귀)", 1, "새로 깨짐 ['test_far.py']")],
        "통과": False, "못잼": [], "걸린초": 1.0, "회귀": {"새로깨짐": ["test_far.py"], "고쳐짐": [], "그대로빨강": []}}
    r = I.사용자개선("뭔가 고쳐줘", d, 초=30)
    ok(r["판정"] == "시뮬빨강" and P.현재판(d) is None,
       f"**레포 전체에서 새로 깨지면 붙이지 않는다** ({r['판정']})")
    ok(r["회귀"]["새로깨짐"] == ["test_far.py"] and "test_far.py" in I.부탁보고(r), "무엇이 깨졌는지 사람에게 말한다")
    ok(I.사용자개선("", d)["판정"] == "빈부탁", "빈 부탁은 안 받는다")
    P.리허설기 = 초록리허설

    print("\n== 틈이 없으면 멈추지 않는다: 제2의 뇌로 성능 개선거리 ==")
    I.틈모으기_ = lambda repo: []                      # 고칠 틈 없음
    P.리허설기 = 리허설_회귀없음
    본참 = {"프롬프트": ""}

    def 고르기_가짜(prompt):
        본참["프롬프트"] = prompt
        return json.dumps({"꼴": "부탁", "부탁": "mod.f 가 1을 돌려주게 하라", "왜": "최신 방법 적용",
                         "근거": ["arxiv:2501.9#aa"]}, ensure_ascii=False)
    I.고르기기 = 고르기_가짜
    I.넓히기_ = lambda 질의들, repo: None
    from graph import ask as _ask
    _원래찾기 = _ask.찾기
    _ask.찾기 = lambda 물음, repo=None, 최대=5: [(9, {"출처": "dig/corpus/x.md", "해시": "aa", "요약": "새 방법 A"})]
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "적용", "근거": ["arxiv:2501.9#aa"],
                                      "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
    try:
        r = I.자가개선(d, 몇=3)
        ok(r["성능"] and r["동의대기"] is not None and r["동의대기"]["판정"] == "동의대기",
           f"**틈 0 -> 성능 개선거리로 넘어가 동의 대기** ({r.get('성능')}, {(r['동의대기'] or {}).get('판정')})")
        ok(r["동의대기"].get("성능거리") and r["동의대기"]["부탁"] == "mod.f 가 1을 돌려주게 하라",
           "제2의 뇌가 고른 것이 부탁이 된다")
        ok("저장소 얼개" in 본참["프롬프트"] and "dig/corpus/x.md #aa" in 본참["프롬프트"],
           "고르기 프롬프트에 저장소 얼개와 모은 참고가 들어간다")
        ok("성능 개선거리" in I.보고(r), "보고가 성능 길로 갔다고 말한다")
        꼴들2 = [x.get("꼴") for x in I.원장읽기(d)]
        ok("성능고르기" in 꼴들2, "원장에 성능고르기가 남는다")
        I.승인(d, 누가="검사"); git(d, "commit", "-qam", "성능 반영")

        print("\n== 근거가 없으면 정직히 멈춘다 ==")
        (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "again")
        _ask.찾기 = lambda 물음, repo=None, 최대=5: []
        r = I.자가개선(d, 몇=1)
        ok(r["동의대기"] is None and "참고가 없다" in r["해본"][0]["말"],
           f"**뇌가 비면 '수집이 먼저다' 라고 말한다** ({r['해본'][0]['판정']})")
        _ask.찾기 = lambda 물음, repo=None, 최대=5: [(9, {"출처": "s", "해시": "b", "요약": "x"})]
        I.고르기기 = lambda prompt: json.dumps({"꼴": "없음", "왜": "적용할 만한 것이 없다"}, ensure_ascii=False)
        r = I.자가개선(d, 몇=1)
        ok(r["해본"][0]["판정"] == "고를것없음", "고를 것이 없으면 그렇다고 한다")
    finally:
        _ask.찾기 = _원래찾기
        I.고르기기 = None

    print("\n== 후보 상한 5 ==")
    I.틈모으기_ = lambda repo: [dict(틈, 무엇=f"t{i}") for i in range(8)]
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 3"}]})
    r = I.자가개선(d, 몇=99)
    ok(len(r["해본"]) == 5 and r["틈수"] == 8, f"**몇=99 줘도 후보 5개까지** ({len(r['해본'])})")
    ok("5개 후보" in r["남은것"], "다 실패하면 그렇다고 말한다")
finally:
    I.제안기 = I.틈모으기_ = I.넓히기_ = I.고르기기 = None
    I.모델막힘 = False
    Rs.분해기 = None
    P.리허설기 = None
    s = P.읽기(d)
    if s:
        P._끄기(d, s)
    shutil.rmtree(d, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("동의" in (dispatch.run("!자가개선", allow_write=True) or "") or "자가개선" in (dispatch.run("!자가개선 도움", allow_write=True) or ""), "!자가개선 도움말")
ok("관리 채널" in (dispatch.run("!자가개선 승인", allow_write=False) or ""), "공개 채널에서 승인 못 한다")
ok(dispatch.run("!개선 상태", allow_write=True) == dispatch.run("!자가개선 상태", allow_write=True) is not None,
   "**`!개선` 도 같은 명령이다**(사용자가 실제로 친 것)")
ok(dispatch.run("!개선기 x") is None and dispatch.run("!자가개선기 x") is None, "붙여 쓴 꼴은 명령이 아니다")
ok(dispatch.고르기("개선해줘")[0] == "!자가개선", "자연어 '개선해줘' 도 간다")
불림2 = []
dispatch.run("!개선 답변을 더 빠르게 해줘", runner=lambda argv, 로그, 무엇: (불림2.append(argv) or "시작"), allow_write=True)
ok(불림2 and 불림2[0][:3] == ["python3", "improve/run.py", "--부탁"] and 불림2[0][3] == "답변을 더 빠르게 해줘",
   f"**`!개선 <말>` 이 그 말을 그대로 부탁으로 넘긴다** ({불림2})")
_run = (뿌리 / "improve" / "run.py").read_text(encoding="utf-8")
ok("def 사용자개선" in _run and "전부: bool = True" in _run, "부탁은 기본이 레포 전체 시뮬이다")
ok("def 성능개선" in _run and "def 부탁고르기" in _run, "틈이 없을 때 가는 길이 있다")
ok('if str(REPO) not in sys.path' in _run, "**스크립트로 돌 때 뿌리를 넣는다**(ModuleNotFoundError 사고)")
ok(not dispatch.도구로쳐도되나("!자가개선 승인")[0], "**봇은 dispatch_command 로 승인을 못 친다**")
ok(dispatch.고르기("스스로 개선할 점 찾아봐")[0] == "!자가개선" and dispatch.고르기("자가개선 점검")[0] == "!자가개선 점검", "자연어 -> !자가개선")
불림 = []
dispatch.run("!자가개선", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0][:2] == ["python3", "improve/run.py"], f"배경으로 돈다 ({불림})")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("async def _자가개선지켜보기" in _서버 and "asyncio.create_task(_자가개선지켜보기())" in _서버 and "IMPROVE_SEC" in _서버,
   "**봇이 6h 마다 스스로 돌아 동의를 구한다**")
ok("!자가개선" in _서버 and "승인` 은 사람만" in _서버, "프롬프트가 !자가개선 을 이름을 대고 '승인은 사람만' 을 적는다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"improve/**.py"' in _wf, "improve 가 배포 경로에")
ok("improve/ledger.jsonl merge=union" in (뿌리 / ".gitattributes").read_text(encoding="utf-8"), "원장은 union")
p = subprocess.run(["python3", "improve/run.py", "--틈만"], cwd=str(뿌리), capture_output=True, text=True, timeout=120)
ok(p.returncode == 0 and "틈" in p.stdout, f"--틈만 CLI 가 돈다 ({p.stdout.strip().splitlines()[-1][:40] if p.stdout.strip() else ''})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("improve: 근거·확장 · 시뮬·동의대기 · 승인 · 버림 · 거절 · 리허설 · 상한 · 배선 -- 통과")
