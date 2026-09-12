"""증상에서 **증거를 캐고 가설을 판정하는지** 붙든다 -- 모델 없이.

사용자(2026-09-11): "왜 나의 에이전트는 이런 식의 사고과정을 거치면서 스스로 해결하지
못하는거야? 너의 사고 과정처럼 나의 에이전트로 사고하면서 스스로 문제를 찾고 코드를
수정하게 만들어줘."

가장 중요한 단언은 **그 사고를 재현하는 것**이다. 사람이 한 일은 이랬다:

    트레이스백의 줄번호를 읽었다 -> 지금 HEAD 의 그 함수는 거기가 아니다
    -> 옛 커밋을 짚으니 맞는 판이 있다 -> **도는 코드가 낡았다**
    -> 고침이 틀린 게 아니라 도착하지 않은 것이다

이 중 어디에도 모델이 없다. 전부 저장소에 적힌 사실이다.

붙드는 것(임시 git 저장소에서): (1) 트레이스백을 읽는다, (2) **낡은 판을 짚는다**,
(3) 최신 판이면 그렇다고 한다(거짓 경보 금지), (4) 저장소 안 모듈은 '없는' 것이 아니라
sys.path 라고 가른다, (5) 머지 안 한 커밋을 짚는다, (6) 가설 차례가 옳다,
(7) 증상 글이 아니면 못 읽었다고 한다, (8) repair 가 모델 앞에 이것을 거치고,
**모델이 없어도 · 모델이 사람 탓을 해도** 저장소의 답이 이긴다.

실행: python3 tests/test_diagnose.py   (망·모델 없이 돈다)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import diagnose as D  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


print("== 트레이스백을 읽는다 ==")
# 아래 `/home/ubuntu/SE/...` 는 **사용자가 실제로 보낸 트레이스백 글자 그대로**다. 파일을
# 여는 자리가 아니라 파싱할 입력이다 -- 진단이 남의 기계 경로를 저장소 상대 경로로
# 옮길 줄 아는지가 바로 여기서 보는 것이다.  # G019: 기계 경로
_VM = "/home/ubuntu/SE"        # G019: 기계 경로
글 = ('Traceback (most recent call last):\n'
      f'  File "{_VM}/discord_bot_server.py", line 12, in 시키기\n'
      '    나가기()\n'
      f'  File "{_VM}/improve/run.py", line 410, in 사용자개선\n'
      '    from plan import store as P\n'
      "ModuleNotFoundError: No module named 'plan'\n")
증 = D.증상파싱(글, 뿌리)
ok(증["예외"] == "ModuleNotFoundError" and 증["없는모듈"] == "plan", f"예외·없는 모듈 ({증['예외']}, {증['없는모듈']})")
ok(len(증["자리"]) == 2 and 증["자리"][-1] == {"파일": "improve/run.py",
   "원래경로": f"{_VM}/improve/run.py", "줄": 410, "함수": "사용자개선"},
   f"**가장 깊은 자리**를 쓴다 ({증['자리'][-1]})")
ok(D.증상파싱("그냥 잘 돌았습니다", 뿌리)["자리"] == [], "증상 글이 아니면 자리가 없다")

os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
판 = Path(tempfile.mkdtemp(prefix="test-dg-"))
원격 = Path(tempfile.mkdtemp(prefix="test-dg-원격-"))
try:
    subprocess.run(["git", "init", "--bare", "-q", str(원격)], check=False)
    git(판, "init", "-q"); git(판, "checkout", "-qb", "main")
    (판 / "plan").mkdir(); (판 / "plan" / "__init__.py").write_text("", encoding="utf-8")
    (판 / "plan" / "store.py").write_text("값 = 1\n", encoding="utf-8")
    (판 / "improve").mkdir(); (판 / "improve" / "__init__.py").write_text("", encoding="utf-8")
    # 옛 판: 사용자개선 이 3~6줄
    (판 / "improve" / "run.py").write_text(
        "import sys\n\n\ndef 사용자개선():\n    from plan import store\n    return store.값\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "옛 판")
    git(판, "remote", "add", "origin", str(원격)); git(판, "push", "-q", "-u", "origin", "main")
    옛 = git(판, "rev-parse", "--short", "HEAD").stdout.strip()

    print("\n== 최신 판이면 낡았다고 하지 않는다 (거짓 경보 금지) ==")
    자리옛 = {"파일": "improve/run.py", "줄": 5, "함수": "사용자개선"}
    r = D.판이낡았나(자리옛, 판)
    ok(r["판정"] == "아니다", f"지금 HEAD 와 맞으면 '아니다' ({r['말'][:60]})")

    print("\n== 판을 고쳐 줄이 밀리면 **낡았다고 짚는다** ==")
    (판 / "improve" / "run.py").write_text(
        "import sys\nfrom pathlib import Path\nREPO = Path(__file__).resolve().parent.parent\n"
        "sys.path.insert(0, str(REPO))\n\n\ndef 사용자개선():\n    from plan import store\n"
        "    return store.값\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "뿌리를 넣는다")
    r = D.판이낡았나(자리옛, 판)
    ok(r["판정"] == "그렇다" and r.get("커밋") == 옛,
       f"**도는 코드가 낡았다고 짚고 어느 판인지 댄다** ({r.get('커밋')} vs 옛 {옛})")
    ok("또 고치지 마라" in r["고칠거리"] and "안 닿았거나" in r["고칠거리"] and "옛 실행의 것" in r["고칠거리"],
       "**코드를 또 고치라고 하지 않는다** -- 도달 문제거나 옛 실행의 글이라고 말한다")
    ok(r["판정명령"], "다시 확인할 명령을 들려 준다")

    print("\n== 저장소 안 모듈은 '없는' 것이 아니다 ==")
    r = D.모듈이어디에("plan", 판)
    ok(r["판정"] == "그렇다" and "설치할 것이 아니다" in r["말"],
       "**sys.path 문제라고 가른다** -- 설치하라고 하지 않는다")
    ok(D.모듈이어디에("numpy", 판)["판정"] == "아니다", "진짜 바깥 꾸러미는 바깥이라고 한다")

    print("\n== 머지 안 한 커밋을 짚는다 (이 저장소가 여섯 번 앓은 병) ==")
    r = D.머지했나("improve/run.py", 판)
    ok(r["판정"] == "그렇다" and "origin/main 밖에" in r["말"], f"안 민 커밋을 짚는다 ({r['말'][:60]})")
    git(판, "push", "-q", "origin", "main")
    ok(D.머지했나("improve/run.py", 판)["판정"] == "아니다", "밀고 나면 '아니다'")

    print("\n== 도달 확인: 지금 판이 그 판의 후손이고 origin/main 과 같으면 **옛 실행의 글**이다 ==")
    r = D.도달확인(옛, 판)
    ok(r["판정"] == "그렇다" and "옛 실행의 글" in r["말"] and "고칠 코드가 없다" in r["고칠거리"],
       f"**고칠 코드가 없다고 끝맺는다** ({r['말'][:60]})")
    (판 / "plan" / "store.py").write_text("값 = 2\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "로컬만")
    git(판, "push", "-q", "origin", "main")
    git(판, "reset", "-q", "--hard", "HEAD~1")
    r = D.도달확인(옛, 판)
    ok(r["판정"] == "그렇다" and "배포가 안 닿았다" in r["말"], f"origin/main 보다 뒤면 **배포가 안 닿았다** ({r['말'][:60]})")
    git(판, "reset", "-q", "--hard", "origin/main")

    print("\n== 진단 한 바퀴: 차례가 옳은가 ==")
    글판 = ('  File "improve/run.py", line 5, in 사용자개선\n'
            '    from plan import store\n'
            "ModuleNotFoundError: No module named 'plan'\n")
    d = D.진단(글판, 판)
    ok(d["가설"], "가설을 낸다")
    ok(d["가설"][0]["탐침"] == "판이낡았나",
       f"**낡은 판이 맨 앞이다** -- 그것이면 다른 이야기는 헛것이다 ({[h['탐침'] for h in d['가설']]})")
    ok(any(h["탐침"] == "모듈이어디에" for h in d["가설"]), "sys.path 가설도 함께 든다")
    ok("도는 코드가 낡았다" in D.보고(d), "보고가 그것을 말로 적는다")

    print("\n== 증상 글이 아니면 못 읽었다고 한다 ==")
    d2 = D.진단("오늘 날씨가 좋습니다", 판)
    ok(not d2["가설"] and "못 읽었다" in d2.get("말", ""), "지어내지 않는다")
finally:
    shutil.rmtree(판, ignore_errors=True)
    shutil.rmtree(원격, ignore_errors=True)

print("\n== 진짜 저장소: 그 사고를 그대로 재현하는가 ==")
d = D.진단(글, 뿌리)
ok(d["가설"] and d["가설"][0]["탐침"] == "판이낡았나",
   f"**사용자가 보낸 그 트레이스백에서 '도는 코드가 낡았다' 를 스스로 짚는다** ({[h['탐침'] for h in d['가설']]})")
ok(any("m improve.run" in h["고칠거리"] for h in d["가설"]),
   "`-m` 으로 부르라는 구조적 고침까지 낸다")
p = subprocess.run(["python3", "-m", "diagnose", "--글", 글], cwd=str(뿌리),
                   capture_output=True, text=True, timeout=300)
ok(p.returncode == 0 and "도는 코드가 낡았다" in p.stdout, f"CLI 가 돈다 (끝값 {p.returncode})")
ok(subprocess.run(["python3", "-m", "diagnose", "--글", "그냥 말"], cwd=str(뿌리),
                  capture_output=True, text=True, timeout=120).returncode == 3,
   "증상이 아니면 끝값 3 (못돌림) -- 초록이 아니다")

print("\n== repair 가 모델 **앞에** 이것을 거친다 ==")
import repair.run as R  # noqa: E402
_원진단, _원제안, _원모으기, _원실측 = R.진단기, R.제안기, R.모으기, R.실측
판2 = Path(tempfile.mkdtemp(prefix="test-dg-rp-"))
try:
    (판2 / "scripts").mkdir(parents=True, exist_ok=True)
    R.모으기 = lambda 증상: []
    # 임시 판에서는 sandbox 를 못 깐다 -- 여기서 보려는 것은 **모델이 없을 때의 갈래**이지
    # 격리 판이 깔리는지가 아니다(그건 tests/test_repair.py 가 본다). 실측만 갈아 끼운다.
    R.실측 = lambda 명령, repo=None, 초=120: {"돌았나": True, "끝값": 1, "꼬리": "ModuleNotFoundError: No module named 'plan'", "메모": ""}
    R.진단기 = lambda 글, repo=None: {"증상": {}, "증거": [], "가설": [
        {"무엇": "도는 코드가 낡았다 -- abc1234 의 줄번호와 맞는다", "탐침": "판이낡았나",
         "고칠거리": "코드를 또 고치지 마라. 머지·배포를 보라", "판정명령": "git log -1"}]}

    def _모델없음(prompt):
        raise RuntimeError("빈 후보 풀 -- 쓸 수 있는 제미나이 키를 못 찾았다")
    R.제안기 = _모델없음
    r = R.고치기("bash -lc 'exit 1'", "ModuleNotFoundError", repo=판2, 바퀴=1, 초=30)
    ok(r["돌았나"] and r.get("진단만") and "저장소가 답했다" in r["남은것"],
       f"**모델을 못 불러도 저장소의 답을 낸다** ({r['남은것'][:70]})")
    ok("또 고치지 마라" in r["남은것"], "그 답이 진단의 고칠거리다")

    R.제안기 = lambda prompt: '{"꼴": "사람", "왜": "키가 없다", "사람이_할_것": "GEMINI_API_KEY 를 발급받아 넣어라"}'
    _원시도 = R.시도
    R.시도 = lambda 제안, 명령, repo=None, 초=120: {"판정": "입력오류", "요약": "GEMINI_API_KEY 가 없다", "꼬리": ""}
    try:
        r2 = R.고치기("bash -lc 'exit 1'", "빈 후보 풀", repo=판2, 바퀴=1, 초=30)
    finally:
        R.시도 = _원시도
    ok(r2.get("진단이_뒤집음") and not r2.get("입력오류"),
       "**모델이 '이용자 측' 이라 해도 진단이 설명하면 사람 탓을 안 한다**")
    ok("저장소가 다르게 말한다" in r2["남은것"], f"무엇이 뒤집혔는지 말한다 ({r2['남은것'][:60]})")
finally:
    R.진단기, R.제안기, R.모으기, R.실측 = _원진단, _원제안, _원모으기, _원실측
    shutil.rmtree(판2, ignore_errors=True)

print("\n== 재현이 안 되는 사고도 잡는다 (로그 꼬리로) ==")
# 낡은 판이 배포돼 터지면 **여기 트리에서는 재현이 안 된다** -- 여기는 최신이니까.
# 그때도 로그의 줄번호는 진실을 말한다. 그래서 repair 가 증거글을 따로 받는다.
_원진단2, _원제안2, _원모으기2, _원실측2 = R.진단기, R.제안기, R.모으기, R.실측
판3 = Path(tempfile.mkdtemp(prefix="test-dg-증거-"))
받은 = {}
try:
    R.모으기 = lambda 증상: []
    R.실측 = lambda 명령, repo=None, 초=120: {"돌았나": True, "끝값": 1, "꼬리": "(재현 안 됨)", "메모": ""}
    def _엿보기(글, repo=None):
        받은["글"] = 글
        return {"증상": {}, "증거": [], "가설": []}
    R.진단기 = _엿보기
    R.제안기 = lambda prompt: '{"꼴": "사람", "사람이_할_것": "x"}'
    _원시도2 = R.시도
    R.시도 = lambda 제안, 명령, repo=None, 초=120: {"판정": "사람", "요약": "x", "꼬리": ""}
    try:
        R.고치기("bash -lc 'exit 1'", "증상", repo=판3, 바퀴=1, 초=30,
               증거글='  File "improve/run.py", line 410, in 사용자개선')
    finally:
        R.시도 = _원시도2
    ok("line 410" in 받은.get("글", ""),
       "**재현 꼬리가 아니라 로그의 트레이스백이 진단에 닿는다**")
finally:
    R.진단기, R.제안기, R.모으기, R.실측 = _원진단2, _원제안2, _원모으기2, _원실측2
    shutil.rmtree(판3, ignore_errors=True)

_bot = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("증거글=증거글" in _bot and "로그파일" in _bot,
   "**봇이 배경 로그 꼬리를 들려 보낸다** -- 재현 안 되는 사고도 진단이 본다")
ok("증거부터 캤다" in _bot, "사람에게 증거를 먼저 보여 준다")
# 사용자(2026-09-12): "여기서 끝나네 끝까지 못 고쳐주고?" -- 진단이 '도달' 이라 했으면 그 확인을 실제로 한다.
ok("_dg.도달확인" in _bot and "도달 확인" in _bot, "**봇이 '판이낡았나' 가설의 확인을 실제로 돌려 끝맺는다**")
ok('"--증거", _증거파일' in _bot, "조사로 넘길 때도 이 실행의 출력만 증거로 준다")
ok("--도달" in (뿌리 / "diagnose.py").read_text(encoding="utf-8"), "`python3 -m diagnose --도달 <커밋>` 이 있다")

_rp = (뿌리 / "repair" / "run.py").read_text(encoding="utf-8")
ok(_rp.index("진단기 or _진단기본") < _rp.index("제안기 or _제안기본"),
   "**증거 캐기가 모델 부르기보다 앞에 있다**")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("diagnose: 트레이스백 읽기 · 낡은 판 짚기 · sys.path 가르기 · 머지 · 차례 · repair 배선 -- 통과")
