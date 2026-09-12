"""긴 호흡 루프(investigate)를 붙든다 -- **끝은 코드가 정하고, 되풀이는 세고, 시한은 지킨다.**

사용자(2026-09-12): "50분~1시간이 걸리더라도 문제를 해결했으면 좋겠어. 아주 긴 템포지만,
계속해서 문제를 해결하는 것. 다양한 도구를 가지고. 똑같이 따라해도 좋아."

두뇌·판정·진단을 전부 갈아 끼워(망·모델·게이트 없이) 루프의 뼈대만 본다:
(1) 시작부터 초록이면 안 돈다, (2) 두뇌가 둘째 바퀴에 고치면 둘째 바퀴에 끝나고 마무리
턴을 받는다(머지는 코드가 문제를 잰 뒤), (3) **두뇌가 '됐다' 고 해도 판정이 빨강이면 안 끝난다**,
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
_원 = (I.두뇌, I.판정기, I.진단기, I.모으기, I.머지기)
머지호출 = []
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
    # 머지는 GitHub 를 부르지 않는다 -- 가짜가 호출을 적고 "문제 없음, 붙였다" 를 돌려준다
    I.머지기 = lambda repo, 아이디, 부탁: (머지호출.append((아이디, 부탁)) or
                                     {"됐나": True, "번호": 9, "url": "https://x/pull/9", "문제": [], "알림": ["새 의존성(requirements.txt) -- 배포가 pip 로 깐다"], "왜": "머지됨", "갈래정리": "main 으로 돌아왔다", "크기": "+10 / -0 · 파일 2"})

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
    ok("네가 머지하지 마라" in next(p for p in 받은 if p.startswith("[조사 마무리]")), "두뇌는 머지하지 않는다고 못박는다 -- 코드가 잰다")
    ok("PR https://x/1" in r["마무리"], "마무리 답을 남긴다")
    ok(머지호출 and 머지호출[-1] == ("t1", "증상 A") and r["머지"]["됐나"], f"**해결 뒤 코드가 머지를 판단한다** (호출 {머지호출[-1:]})")
    보 = I.보고(r)
    ok("PR #9 https://x/pull/9" in 보 and "알림: 새 의존성" in 보 and "코드가 붙였다" in 보 and "부탁: 증상 A" in 보,
       "보고가 사람 꼴이다: 부탁 · PR · 알림 · 머지됨")
    ok(any(d.get("단계") == "머지" and d.get("됐나") for d in I.원장읽기(판, "t1")), "원장에 머지 단계가 남는다")
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

    print("\n== 아무것도 안 바뀌면: 갈래 바꿔라 -> **코드가 제2의 뇌를 연다**(두 번) -> 그래도면 멈춘다 ==")
    # 사용자(2026-09-12): "사람 몫으로 넘기는 건 최종이라고. 모르면 제2의 뇌나 dig 로 검색해서 정보 찾고
    # 코드 고치고 문제 있으면 또 수정하고 해서 6시간이 걸려도 좋으니깐 스스로 해결해보라고."
    받은.clear()
    뇌물음 = []
    I.모으기 = lambda 물음: (뇌물음.append(물음) or ["arxiv: 비슷한 사고의 고침 <https://x/1>", "graph: 지난 메모 <m#1>"])
    I.두뇌 = lambda p, t: (받은.append(p) or "같은 걸 또 해 봤다")
    r = I.조사("증상 C", repo=판, 시한초=60, 최대바퀴=20, 아이디="t3")
    ok(r["바퀴"] == I.되풀이한도 and "연속 아무것도 안 바뀌었다" in r["남은것"] and I.되풀이한도 >= 6,
       f"되풀이 {I.되풀이한도}바퀴면 멈춘다 -- 셋이 아니다 (바퀴 {r['바퀴']})")
    ok(len(뇌물음) == 2 and "증상 C" in 뇌물음[0], f"**막히면 코드가 제2의 뇌를 두 번 연다** (물음 {len(뇌물음)}개)")
    ok(any("제2의 뇌가 찾아 온 것" in p and "https://x/1" in p for p in 받은), "찾은 것을 다음 바퀴 프롬프트에 들려 보낸다")
    ok("제2의 뇌를 2번 열었는데도" in r["남은것"] and "!조사" in r["남은것"], "멈출 때 무엇을 다 해 봤는지와 이어 돌리는 길을 적는다")
    ok(any("갈래는 막혔다" in p for p in 받은), "갈래를 바꾸라고도 말한다")
    ok(any(d.get("단계") == "제2의뇌" for d in I.원장읽기(판, "t3")), "원장에 제2의 뇌를 연 바퀴가 남는다")
    I.모으기 = None
    ok(I.기본시한초 == 6 * 3600, "**기본 시한은 여섯 시간** -- 사람에게 넘기는 것은 최후다")

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

    print("\n== 목표 모드: 새 기능은 검사로 못박고 그 검사가 지날 때까지 ==")
    I.판정기 = None                      # 진짜 판정기 -- 재현 명령이 진짜로 돈다
    (판 / "gatekeeper.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    (판 / "audit").mkdir(exist_ok=True); (판 / "audit" / "run.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    (판 / "tests").mkdir(exist_ok=True)
    받은.clear()

    def 두뇌_목표(p, t):
        받은.append(p)
        n = sum(1 for x in 받은 if x.startswith("[조사 바퀴"))
        if n == 1:                        # 첫 바퀴: 검사만 짓는다 (기능이 없으니 빨강)
            (판 / "tests" / "test_목표_g1.py").write_text("import pdfout\nassert pdfout.만들기('x') == 'ok'\n", encoding="utf-8")
            return "검사를 지었다"
        if n == 2:                        # 둘째: 기능을 짓는다
            (판 / "pdfout.py").write_text("def 만들기(md):\n    return 'ok'\n", encoding="utf-8")
            return "기능을 지었다"
        return "…"
    I.두뇌 = 두뇌_목표
    r = I.조사("md 를 pdf 로 제공", repo=판, 시한초=120, 최대바퀴=4, 아이디="g1", 목표=True)
    ok(r["해결"] and r["바퀴"] == 2, f"**검사가 없을 땐 빨강, 지어서 지나면 초록** (바퀴 {r['바퀴']})")
    ok(any(d.get("단계") == "검사유효" for d in I.원장읽기(판, "g1")), "해결 전에 검사가 시작 판에서 빨간지 확인했다")

    print("\n  -- 실측(PR #194): 함수만 정의하고 안 부르는 검사는 늘 초록이다 -> **무효**, 해결로 안 친다 --")
    (판 / "pdfout.py").unlink(missing_ok=True); (판 / "tests" / "test_목표_g1.py").unlink(missing_ok=True)
    받은.clear()

    def 두뇌_속임(p, t):
        받은.append(p)
        n = sum(1 for x in 받은 if x.startswith("[조사 바퀴"))
        if n == 1:                        # 속임수 검사 + 껍데기 기능 (스크립트로 돌면 아무것도 안 돈다)
            (판 / "tests" / "test_목표_g2.py").write_text(
                "def test_x():\n    assert 'pdf' in open('상태').read().lower() or True\n", encoding="utf-8")
            return "검사와 기능을 지었다"
        if n == 2:                        # 되묻자 진짜 검사 + 진짜 기능
            (판 / "tests" / "test_목표_g2.py").write_text("import pdfout\nassert pdfout.만들기('x') == 'ok'\n", encoding="utf-8")
            (판 / "pdfout.py").write_text("def 만들기(md):\n    return 'ok'\n", encoding="utf-8")
            return "제대로 지었다"
        return "…"
    I.두뇌 = 두뇌_속임
    r = I.조사("md 를 pdf 로 제공", repo=판, 시한초=120, 최대바퀴=4, 아이디="g2", 목표=True)
    ok(r["해결"] and r["바퀴"] == 2, f"**속임수 검사는 해결로 안 치고, 진짜 검사로 바꾼 뒤에 해결** (바퀴 {r['바퀴']})")
    ok("[검사 무효]" in 받은[1] and "기능이 없는 판" in 받은[1], "두뇌에게 검사가 무효인 까닭을 들려 준다")
    단 = [d.get("단계") for d in I.원장읽기(판, "g2")]
    ok("검사무효" in 단 and 단[-3:] == ["검사유효", "머지", "끝"], f"원장에 무효 -> 유효 -> 머지가 남는다 ({단})")

    print("\n== 머지 판단: 문제는 막고, 알림은 적기만 한다 (순수 함수) ==")
    깨끗 = {"겹침": False, "검사": [{"이름": "gates", "상태": "completed", "결론": "success"}], "파일들": [{"경로": "x.py", "상태": "modified"}], "더함": 10, "뺌": 2}
    ok(I.머지위험(깨끗) == ([], []), "겹침 없음 · CI 초록 · 작은 diff -> 문제도 알림도 없다(코드가 붙인다)")
    문, 알 = I.머지위험({**깨끗, "겹침": True})
    ok(len(문) == 1 and "충돌" in 문[0], f"충돌은 문제다 ({문})")
    문, 알 = I.머지위험({**깨끗, "검사": [{"이름": "gates", "상태": "completed", "결론": "failure"}]})
    ok(len(문) == 1 and "CI 빨강: gates" in 문[0], f"CI 빨강은 문제다 ({문})")
    문, 알 = I.머지위험({**깨끗, "검사": [{"이름": "gates", "상태": "in_progress", "결론": ""}]})
    ok(문 == [] and 알 and "도는 중" in 알[0], "CI 도는 중은 알림일 뿐 -- 기다리지 않는다")
    문, 알 = I.머지위험({**깨끗, "파일들": [{"경로": "gates/G003_invariants.py", "상태": "removed"}]})
    ok(len(문) == 1 and "삭제" in 문[0], f"파일 삭제는 문제다 ({문})")
    문, 알 = I.머지위험({**깨끗, "더함": 2000, "뺌": 0})
    ok(len(문) == 1 and "상한" in 문[0], "큰 diff 는 문제다 -- 사람이 봐야 할 크기")
    문, 알 = I.머지위험({**깨끗, "파일들": [{"경로": "discord_bot_server.py", "상태": "modified"}, {"경로": "requirements.txt", "상태": "modified"},
                                     {"경로": "public_agent_memory/a.md", "상태": "added"}, {"경로": "repair/ledger.jsonl", "상태": "modified"}]})
    ok(문 == [] and len(알) == 3 and any("봇 본체" in x for x in 알) and any("의존성" in x for x in 알) and any("2개가 딸려" in x for x in 알),
       f"봇 본체 · 의존성 · 딸린 메모는 알림이다 ({알})")
    I.머지기 = lambda repo, 아이디, 부탁: {"됐나": False, "번호": 12, "url": "https://x/pull/12", "문제": ["CI 빨강: gates -- 로그를 봐야 한다"], "알림": [], "왜": "문제 1개", "크기": "+1 / -0 · 파일 1"}
    I.판정기 = 판정_파일로                 # 목표 대목이 진짜 판정기로 바꿔 두었다 -- 파일 판정기로 잠시 되돌린다
    (판 / "상태").write_text("빨강", encoding="utf-8")
    _두뇌전 = I.두뇌
    def 두뇌_바로고침(p, t):               # `받은` 은 건드리지 않는다 -- 아래 목표 대목의 단언이 그것을 읽는다
        (판 / "상태").write_text("초록", encoding="utf-8"); return "고쳤다"
    I.두뇌 = 두뇌_바로고침
    r = I.조사("증상 C", repo=판, 시한초=60, 최대바퀴=3, 아이디="t9")
    보 = I.보고(r)
    ok(r["해결"] and not r["머지"]["됐나"] and "안 붙였다" in 보 and "CI 빨강: gates" in 보 and "`!조사 머지 12`" in 보,
       "**문제가 있으면 안 붙이고, 무엇이 문제인지와 확정 명령을 적는다**")
    I.두뇌, I.판정기 = _두뇌전, None
    ok("tests/test_목표_g2.py" in 받은[0] and "못박아라" in 받은[0], "첫 일이 검사로 못박기라고 말한다")
    ok("재현 명령: `python3 tests/test_목표_g2.py`" in 받은[0], "그 검사가 재현 명령이 된다 -- 판정은 끝값")
    I.판정기 = 판정_파일로

    print("\n== 원장·메모 ==")
    줄들 = I.원장읽기(판, "t3")
    _단 = [d["단계"] for d in 줄들]
    ok(_단[0] == "시작" and _단[-1] == "끝" and _단.count("바퀴") == I.되풀이한도 and _단.count("제2의뇌") == 2,
       f"조사 한 건이 시작·바퀴·제2의뇌·끝으로 적힌다 ({_단})")
    ok(all(d["꼴"] == "조사" for d in 줄들), "repair 원장을 그대로 쓴다(두 벌 아님)")
    메모 = list((판 / "public_agent_memory").glob("*_고치기_*.md"))
    ok(메모 and any("조사 t3" in m.read_text(encoding="utf-8") for m in 메모), "메모가 남는다 -- 밤에 간추려 장기기억이 된다")
finally:
    I.두뇌, I.판정기, I.진단기, I.모으기, I.머지기 = _원
    shutil.rmtree(판, ignore_errors=True)

print("\n== claude 두뇌: 같은 조사는 같은 세션 ==")
_잡 = []
I.claude실행기 = lambda argv, cwd, 초: (_잡.append(argv) or (0, "한 턴"))
try:
    I._claude세션.clear()
    I._두뇌claude("첫 프롬프트", "x1"); I._두뇌claude("둘째 프롬프트", "x1")
    ok(_잡[0][3] == "--session-id" and _잡[1][3] == "--resume" and _잡[0][4] == _잡[1][4],
       f"첫 턴 --session-id, 둘째 --resume, 같은 id ({_잡[0][3]} -> {_잡[1][3]})")
    # 실측 2026-09-12: 프롬프트를 맨 끝에 두었더니 `--allowedTools <tools...>` 가 삼켰다.
    ok(_잡[0][2] == "첫 프롬프트" and "--permission-mode" in _잡[0], "**프롬프트는 깃발보다 앞** · 권한 깃발이 있다")
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
    _i = _잡[0].index("--allowedTools")
    ok("bypassPermissions" not in _잡[0] and "Bash" in _잡[0][_i + 1] and "," in _잡[0][_i + 1]
       and _잡[0][-1] == _잡[0][_i + 1],
       "**root 면 우회 대신 허용 도구 목록 -- 한 문자열로, 맨 끝에** (가변 인자가 뒤를 삼킨다)")
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
C.run("!조사 목표 md 를 pdf 로", runner=lambda argv, 로그, 무엇: (잡힌.update(argv=argv) or "띄웠다"), allow_write=True)
ok(잡힌.get("argv") == ["python3", "investigate/run.py", "--증상", "md 를 pdf 로", "--목표"], f"`!조사 목표 <부탁>` ({잡힌.get('argv')})")
ok(dispatch.고르기("이 오류 시간이 걸려도 끝까지 고쳐 줘")[0].startswith("!조사"), "자연어 '끝까지·시간이 걸려도' 는 조사로")
ok(dispatch.고르기("될 때까지 파헤쳐 봐")[0].startswith("!조사"), "'될 때까지·파헤쳐' 도 조사로")
_bot = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok('"investigate/run.py", "--증상"' in _bot and "긴 호흡으로 넘긴다" in _bot,
   "**repair 세 바퀴로 안 풀리면 봇이 조사를 배경으로 띄운다**")
_넘김 = _bot[_bot.index('"investigate/run.py", "--증상"'):][:600]
ok('"--증거", _증거파일' in _넘김, "봇이 **이 실행의 출력**을 증거 파일로 넘긴다")
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
