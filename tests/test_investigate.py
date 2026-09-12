"""긴 호흡 루프(investigate)를 붙든다 -- **끝은 코드가 정하고, 되풀이는 세고, 시한은 지킨다.**

사용자(2026-09-12): "50분~1시간이 걸리더라도 문제를 해결했으면 좋겠어. 아주 긴 템포지만,
계속해서 문제를 해결하는 것. 다양한 도구를 가지고. 똑같이 따라해도 좋아."

두뇌·판정·진단을 전부 갈아 끼워(망·모델·게이트 없이) 루프의 뼈대만 본다:
(1) 시작부터 초록이면 안 돈다, (2) 두뇌가 둘째 바퀴에 고치면 둘째 바퀴에 끝나고 마무리
턴을 받는다(머지는 사람), (3) **두뇌가 '됐다' 고 해도 판정이 빨강이면 안 끝난다**,
(4) 아무것도 안 바뀌면 둘째 바퀴에 '갈래 바꿔라' 를 넣고 셋째에 멈춘다, (5) 시한을
지킨다, (6) 두뇌를 못 부르면 못돌림이다, (7) 진단의 가설이 프롬프트에 든다, (8) 원장·메모,
(9) 배선 -- dispatch · 자연어 · 봇의 넘기기 · 배포 · 읽기점검.

실행: python3 tests/test_investigate.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from investigate import run as I  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
판 = Path(tempfile.mkdtemp(prefix="test-iv-"))
_원 = (I.두뇌, I.판정기, I.진단기)
try:
    subprocess.run(["git", "-C", str(판), "init", "-q"], check=False)
    (판 / "repair").mkdir(); (판 / "public_agent_memory").mkdir()
    (판 / "상태").write_text("빨강", encoding="utf-8")
    subprocess.run(["git", "-C", str(판), "add", "-A"], check=False)
    subprocess.run(["git", "-C", str(판), "commit", "-qm", "init"], check=False)

    def 판정_파일로(repo, 재현명령=""):
        빨 = (Path(repo) / "상태").read_text(encoding="utf-8").strip() != "초록"
        return [{"이름": "재현", "끝값": 1 if 빨 else 0, "꼬리": "AssertionError: 아직 빨강" if 빨 else "ok"},
                {"이름": "게이트", "끝값": 0, "꼬리": "[게이트 통과]"}]

    I.판정기 = 판정_파일로
    I.진단기 = lambda 글, repo=None: {"증상": {}, "증거": [], "가설": []}

    print("== 시작부터 초록이면 안 돈다 ==")
    (판 / "상태").write_text("초록", encoding="utf-8")
    I.두뇌 = lambda p, t: (_ for _ in ()).throw(AssertionError("두뇌를 부르면 안 된다"))
    r = I.조사("증상", repo=판, 시한초=60, 최대바퀴=3)
    ok(r["해결"] and r["바퀴"] == 0, f"판정이 다 0 이면 두뇌를 안 부른다 ({r['메모']})")

    print("\n== 두뇌가 둘째 바퀴에 고치면 둘째 바퀴에 끝난다 · 마무리 턴 ==")
    (판 / "상태").write_text("빨강", encoding="utf-8")
    받은 = []

    def 두뇌_둘째에고침(p, t):
        받은.append(p)
        if p.startswith("[조사 마무리]"):
            return "커밋 abc123 · PR https://x/1 · 남은 것 없음"
        n = sum(1 for x in 받은 if x.startswith("[조사 바퀴"))
        if n == 2:
            (판 / "상태").write_text("초록", encoding="utf-8")
            return "고쳤다. 다음엔 게이트를 본다."
        return "가설 하나 확인 중"
    I.두뇌 = 두뇌_둘째에고침
    r = I.조사("증상 A", repo=판, 시한초=60, 최대바퀴=5, 아이디="t1")
    ok(r["해결"] and r["바퀴"] == 2, f"둘째 바퀴에 해결 (바퀴 {r['바퀴']})")
    ok(any(p.startswith("[조사 마무리]") for p in 받은), "해결되면 마무리 턴을 한 번 준다")
    ok("머지는 사람" in next(p for p in 받은 if p.startswith("[조사 마무리]")), "**머지는 사람이 누른다**고 못박는다")
    ok("PR https://x/1" in r["마무리"], "마무리 답을 남긴다")
    ok(all(t == "investigate-t1" for t in [I and "investigate-t1"]), "한 조사는 한 thread 로 기억이 이어진다")
    첫 = 받은[0]
    ok("지금 빨강인 판정" in 첫 and "AssertionError: 아직 빨강" in 첫, "프롬프트에 빨강 판정과 그 꼬리가 든다")
    ok("'됐다' 고 말하지 마라" in 첫 and "끝값" in 첫, "판정은 끝값이 한다고 두뇌에게 못박는다")
    둘째 = [p for p in 받은 if p.startswith("[조사 바퀴 2")][0]
    ok("지난 바퀴에 해 본 것" in 둘째 and "가설 하나 확인 중" in 둘째, "지난 바퀴 요약을 들려 보낸다")

    print("\n== 두뇌가 '됐다' 고 해도 판정이 빨강이면 안 끝난다 ==")
    (판 / "상태").write_text("빨강", encoding="utf-8")
    I.두뇌 = lambda p, t: "됐다! 완전히 해결했다. 문제 없음."
    r = I.조사("증상 B", repo=판, 시한초=60, 최대바퀴=5, 아이디="t2")
    ok(not r["해결"], "**두뇌의 말은 판정이 아니다**")

    print("\n== 아무것도 안 바뀌면: 둘째에 '갈래 바꿔라', 셋째에 멈춘다 ==")
    받은.clear()
    I.두뇌 = lambda p, t: (받은.append(p) or "같은 걸 또 해 봤다")
    r = I.조사("증상 C", repo=판, 시한초=60, 최대바퀴=10, 아이디="t3")
    ok(r["바퀴"] == I.되풀이한도 and "연속 아무것도 안 바뀌었다" in r["남은것"],
       f"되풀이 {I.되풀이한도}바퀴면 멈춘다 (바퀴 {r['바퀴']})")
    ok(any("갈래는 막혔다" in p for p in 받은), "**멈추기 전에 갈래를 바꾸라고 한 번 말한다**")
    ok("다른 가설로 가라" in [p for p in 받은 if "갈래는 막혔다" in p][0]
       and "diagnose" in [p for p in 받은 if "갈래는 막혔다" in p][0], "무엇으로 바꿀지 도구 이름을 댄다")

    print("\n== 시한을 지킨다 ==")
    호출 = []
    I.두뇌 = lambda p, t: (호출.append(1) or "…")
    r = I.조사("증상 D", repo=판, 시한초=0, 최대바퀴=10, 아이디="t4")
    ok(not r["해결"] and "시한" in r["남은것"] and not 호출, f"시한이 0 이면 한 바퀴도 안 돈다 ({r['남은것'][:40]})")

    print("\n== 두뇌를 못 부르면 못돌림 ==")
    def _못부름(p, t):
        raise RuntimeError("빈 후보 풀")
    I.두뇌 = _못부름
    r = I.조사("증상 E", repo=판, 시한초=60, 최대바퀴=3, 아이디="t5")
    ok(not r["돌았나"] and "두뇌를 못 불렀다" in r["남은것"], "초록이라고 하지 않는다")

    print("\n== 진단의 가설이 프롬프트 맨 앞에 든다 ==")
    받은.clear()
    I.진단기 = lambda 글, repo=None: {"증상": {}, "증거": [], "가설": [
        {"무엇": "도는 코드가 낡았다 -- 09ee299 의 줄번호와 맞는다", "탐침": "판이낡았나",
         "고칠거리": "코드를 또 고치지 마라. 머지·배포를 보라", "판정명령": "git log -1"}]}
    I.두뇌 = lambda p, t: (받은.append(p) or "…")
    I.조사("증상 F", repo=판, 시한초=60, 최대바퀴=1, 아이디="t6")
    ok("저장소가 캔 증거" in 받은[0] and "도는 코드가 낡았다" in 받은[0] and "확인: git log -1" in 받은[0],
       "**바퀴마다 diagnose 가 앞에 선다** -- 가설·고칠거리·확인 명령")

    print("\n== 원장·메모 ==")
    줄들 = I.원장읽기(판, "t3")
    ok([d["단계"] for d in 줄들] == ["시작", "바퀴", "바퀴", "바퀴", "끝"], f"조사 한 건이 시작·바퀴·끝으로 적힌다 ({[d['단계'] for d in 줄들]})")
    ok(all(d["꼴"] == "조사" for d in 줄들), "repair 원장을 그대로 쓴다(두 벌 아님)")
    메모 = list((판 / "public_agent_memory").glob("*_고치기_*.md"))
    ok(메모 and any("조사 t3" in m.read_text(encoding="utf-8") for m in 메모), "메모가 남는다 -- 밤에 간추려 장기기억이 된다")
finally:
    I.두뇌, I.판정기, I.진단기 = _원
    shutil.rmtree(판, ignore_errors=True)

print("\n== claude 두뇌: 같은 조사는 같은 세션 ==")
_잡 = []
I.claude실행기 = lambda argv, cwd, 초: (_잡.append(argv) or (0, "한 턴"))
try:
    I._claude세션.clear()
    I._두뇌claude("첫 프롬프트", "x1"); I._두뇌claude("둘째 프롬프트", "x1")
    ok(_잡[0][2] == "--session-id" and _잡[1][2] == "--resume" and _잡[0][3] == _잡[1][3],
       f"첫 턴 --session-id, 둘째 --resume, 같은 id ({_잡[0][2]} -> {_잡[1][2]})")
    ok("--permission-mode" in _잡[0] and _잡[0][-1] == "첫 프롬프트", "권한 bypass · 프롬프트는 맨 끝")
    # 실측 2026-09-12: 첫 실제 조사에서 claude -p 가 끝값 1 과 함께 오류 문구를 냈는데,
    # 출력이 있다는 이유로 그것을 '두뇌의 답' 으로 넘겨 세 바퀴를 태웠다.
    I.claude실행기 = lambda argv, cwd, 초: (1, "--dangerously-skip-permissions cannot be used with root")
    try:
        I._두뇌claude("p", "x2"); ok(False, "끝값 1 이면 출력이 있어도 올려야 한다")
    except RuntimeError as e:
        ok("cannot be used with root" in str(e), "**끝값 1 이면 출력이 있어도 RuntimeError** -- 오류 문구를 답으로 넘기지 않는다")
    _원루트 = I._루트인가
    I.claude실행기 = lambda argv, cwd, 초: (_잡.append(argv) or (0, "ok"))
    _잡.clear()
    I._루트인가 = lambda: True
    I._두뇌claude("p", "x3")
    ok("bypassPermissions" not in _잡[0] and "--allowedTools" in _잡[0] and "Bash" in _잡[0],
       "**root 면 우회 대신 허용 도구 목록** (root 에선 우회가 거절된다)")
    I._루트인가 = lambda: False
    I._두뇌claude("p", "x4")
    ok("bypassPermissions" in _잡[1] and "--allowedTools" not in _잡[1], "root 가 아니면 우회")
    I._루트인가 = _원루트
finally:
    I.claude실행기 = None; I._claude세션.clear()
ok('"--두뇌", choices=["봇", "claude"]' in (뿌리 / "investigate" / "run.py").read_text(encoding="utf-8"), "`--두뇌 claude` 깃발")

print("\n== 배선 ==")
import dispatch  # noqa: E402
from investigate import discord_cmd as C  # noqa: E402
ok(C in dispatch.명령들, "dispatch 에 걸려 있다")
ok(dispatch.run("!조사 도움", None, True) and "한 시간" in dispatch.run("!조사 도움", None, True), "`!조사 도움`")
ok(dispatch.run("!조사 x", None, False) and "관리 채널" in dispatch.run("!조사 x", None, False), "공개 채널은 못 띄운다")
ok(dispatch.run("!조사기 x", None, True) is None, "붙여 쓴 것은 명령이 아니다")
잡힌 = {}
C.run("!조사 증상 하나 :: python3 tests/test_x.py", runner=lambda argv, 로그, 무엇: (잡힌.update(argv=argv, 무엇=무엇) or "띄웠다"), allow_write=True)
ok(잡힌.get("argv") == ["python3", "investigate/run.py", "--증상", "증상 하나", "--명령", "python3 tests/test_x.py"],
   f"`::` 로 재현 명령을 가른다 ({잡힌.get('argv')})")
ok(dispatch.고르기("이 오류 시간이 걸려도 끝까지 고쳐 줘")[0].startswith("!조사"), "자연어 '끝까지·시간이 걸려도' 는 조사로")
ok(dispatch.고르기("될 때까지 파헤쳐 봐")[0].startswith("!조사"), "'될 때까지·파헤쳐' 도 조사로")
_bot = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok('"investigate/run.py", "--증상"' in _bot and "긴 호흡으로 넘긴다" in _bot,
   "**repair 세 바퀴로 안 풀리면 봇이 조사를 배경으로 띄운다**")
_넘김 = _bot[_bot.index('"investigate/run.py", "--증상"'):][:600]
ok('"--증거", 로그파일' in _넘김, "봇이 로그 꼬리를 증거로 넘긴다")
ok("!조사 <증상> :: <재현 명령>" in _bot, "프롬프트가 이름을 대고 시킨다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"investigate/**.py"' in _wf, "배포 경로에")
_wire = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok('"investigate.run", "--배선"' in _wire, "읽기점검이 배선을 본다(두뇌 안 부름)")
p = subprocess.run([sys.executable, "-m", "investigate.run", "--배선"], cwd=str(뿌리), capture_output=True, text=True, timeout=120)
ok(p.returncode == 0 and "배선됨" in p.stdout, f"--배선 CLI 끝값 0 ({p.stdout.strip()[:50]})")
p = subprocess.run([sys.executable, "-m", "investigate.run"], cwd=str(뿌리), capture_output=True, text=True, timeout=120)
ok(p.returncode == 3, "증상 없이 부르면 끝값 3 -- 초록이 아니다")
_run = (뿌리 / "investigate" / "run.py").read_text(encoding="utf-8")
ok(re.search(r"^if str\(REPO\) not in sys\.path:\n\s+sys\.path\.insert\(0, str\(REPO\)\)", _run, re.M) is not None,
   "스크립트로 돌 때 뿌리를 넣는다(improve/run.py 의 사고)")
ok("run_admin_agent" in _run and "import discord_bot_server" in _run, "두뇌는 봇의 관리 에이전트 그대로 -- 갈아 끼우지 않는다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("investigate: 끝은 코드가 · 두뇌 말은 판정 아님 · 되풀이 · 시한 · 못돌림 · 진단 앞세움 · 원장 · 배선 -- 통과")
