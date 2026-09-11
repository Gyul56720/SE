"""repair(고치기 루프)를 임시 git 저장소에서 가짜 수리기·가짜 제2의 뇌로 **끝까지 돌려** 붙든다.

붙드는 것: (1) 재현 명령이 끝값 0 이면 바로 끝(모델 0회), (2) 틀린 패치는 sandbox 재현이
실패해 **되돌려지고**, 다음 바퀴의 프롬프트에 '해 본 것' 으로 올라가며, 맞는 패치가 오면
해결 -- 판정은 끝값이 한다, (3) 명령 꼴 제안은 sandbox 에서 `명령 && 재현` 이 통과해야
진짜로 돈다, 게이트가 막는 명령은 거절, (4) '사람' 꼴이면 멈추고 남은 한 가지를 적는다,
(5) 깨진 JSON 은 거절 바퀴로 세고 죽지 않는다, (6) 바퀴 상한, (7) 실패 이유가
public_agent_memory 메모(topic 머리말)로 남아 graph/night 가 간추릴 수 있다, (8) 원장의
못 푼 증상이 dig/harvest 의 틈이 된다, (9) `!고치기` 배선 · 도구 · 프롬프트.

LLM·망 없이 돈다. 실행: python3 tests/test_repair.py
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

from repair import run as RP  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-repair-"))
repo = 임시 / "repo"
repo.mkdir()
subprocess.run(["git", "init", "-q", str(repo)], check=True)
(repo / "app.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
(repo / "check.py").write_text("import app\nassert app.add(2, 3) == 5, 'add 가 틀렸다'\nprint('ok')\n", encoding="utf-8")
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "첫"],
               env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}, check=True)

프롬프트들 = []
RP.모으기 = lambda 증상: [f"참고: 뺄셈이 아니라 덧셈 <dig/corpus/x.md> ({증상[:20]})"]

try:
    print("== 이미 끝값 0 이면 모델 0회 ==")
    RP.제안기 = lambda p: (_ for _ in ()).throw(AssertionError("부르면 안 된다"))
    r = RP.고치기("true", "없음", repo=repo)
    ok(r["해결"] and r["바퀴"] == 0 and "고칠 것이 없다" in r["메모"], "끝값 0 -> 바로 해결, 제안기 안 부름")

    print("\n== 틀린 패치는 되돌리고, 맞는 패치가 오면 해결 ==")
    제안열 = [
        json.dumps({"꼴": "패치", "패치": [{"파일": "app.py", "old": "return a - b", "new": "return a * b"}], "왜": "곱셈?"}, ensure_ascii=False),
        "생각해보니...\n" + json.dumps({"꼴": "패치", "패치": [{"파일": "app.py", "old": "return a - b", "new": "return a + b"}], "왜": "덧셈"}, ensure_ascii=False),
    ]

    def 수리기(p):
        프롬프트들.append(p)
        return 제안열.pop(0)
    RP.제안기 = 수리기
    r = RP.고치기("python3 check.py", "AssertionError: add 가 틀렸다", repo=repo, 바퀴=3)
    ok(r["해결"] and r["바퀴"] == 2, f"**두 바퀴 만에 해결** (바퀴 {r['바퀴']})")
    ok([h["판정"] for h in r["해본것"]] == ["실패", "해결"], f"첫 패치 실패 · 둘째 해결 ({[h['판정'] for h in r['해본것']]})")
    ok("return a + b" in (repo / "app.py").read_text(encoding="utf-8"), "맞는 패치가 작업 트리에 남았다")
    ok("참고: 뺄셈이 아니라" in 프롬프트들[0] and "이미 해 본 것" in 프롬프트들[1] and "곱셈?" not in 프롬프트들[0],
       "**제2의 뇌 참고가 프롬프트에, 실패한 바퀴가 다음 프롬프트에 '해 본 것' 으로**")
    ok("add 가 틀렸다" in 프롬프트들[0], "실측한 꼬리가 프롬프트에 있다")
    메모 = (repo / r["메모"]).read_text(encoding="utf-8")
    ok(메모.startswith("---\ntopic: '고치기: AssertionError") and "해결됐다" in 메모 and "곱셈?" in 메모 and "-> **실패**" in 메모,
       "**메모에 topic 머리말 · 해 본 것(실패 포함) · 판정** -- night 가 간추릴 꼴")
    원장 = RP.원장읽기(repo)
    ok([x["꼴"] for x in 원장] == ["시작", "바퀴", "바퀴", "끝"] and 원장[-1]["해결"], "원장: 시작 · 바퀴 2 · 끝(해결)")

    print("\n== 명령 꼴: 판에서 통과해야 진짜로, 게이트가 막는 것은 거절 ==")
    (repo / "check2.py").write_text("import os, sys\nsys.exit(0 if os.path.exists('설정.txt') else 1)\n", encoding="utf-8")
    제안열[:] = [json.dumps({"꼴": "명령", "명령": "rm -rf gates/", "왜": "나쁨"}),
              json.dumps({"꼴": "명령", "명령": "echo 있다 > 설정.txt", "왜": "설정 파일"})]
    r = RP.고치기("python3 check2.py", "설정 없음", repo=repo, 바퀴=3)
    ok(r["해결"] and [h["판정"] for h in r["해본것"]] == ["거절", "해결"],
       f"**게이트가 막는 명령은 거절, 되는 명령은 판에서 통과 뒤 진짜로** ({[h['판정'] for h in r['해본것']]})")
    ok((repo / "설정.txt").is_file(), "진짜 트리에 설정 파일이 생겼다")

    print("\n== 사람 꼴이면 멈추고 남은 한 가지 ==")
    (repo / "check3.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    제안열[:] = [json.dumps({"꼴": "사람", "사람이_할_것": "구글 계정에서 앱 비밀번호를 새로 만들어 !열쇠 로 달라", "왜": "코드 밖"}, ensure_ascii=False)]
    r = RP.고치기("python3 check3.py", "5.7.8 Username and Password not accepted", repo=repo, 바퀴=3)
    ok(not r["해결"] and r["바퀴"] == 1 and "앱 비밀번호" in r["남은것"], f"사람 꼴 -> 바퀴 1 에서 멈추고 남은 것 ({r['남은것'][:40]})")
    메모 = (repo / r["메모"]).read_text(encoding="utf-8")
    ok("못 풀었다" in 메모 and "## 남은 것" in 메모 and "앱 비밀번호" in 메모, "메모에 못 풀었다 + 남은 것")
    ok("5.7.8 Username and Password not accepted" in RP.미해결증상들(repo), "**못 푼 증상이 원장에 남는다** (수집기의 틈)")

    print("\n== 이용자 측 과실: 주어진 정보가 틀렸다고 고지하고 멈춘다 ==")
    제안열[:] = [json.dumps({"꼴": "입력", "틀린것": "SMTP_APP_PASSWORD", "왜": "16자 영문이 아니다 -- 계정 비밀번호를 준 듯",
                            "다시_달라": "!열쇠 SMTP_APP_PASSWORD=<앱 비밀번호 16자>"}, ensure_ascii=False)]
    RP.제안기 = 수리기
    r = RP.고치기("python3 check3.py", "5.7.8 BadCredentials", repo=repo, 바퀴=5)
    ok(not r["해결"] and r.get("입력오류") and r["바퀴"] == 1 and r["남은것"].startswith("주어진 정보가 틀렸다 (이용자 측)"),
       f"**입력 꼴 -> 바퀴 1 에서 멈추고 이용자 측 과실을 고지** ({r['남은것'][:60]})")
    보 = RP.보고(r)
    ok("주어진 정보가 틀렸다" in 보 and "고쳐 달라: !열쇠 SMTP_APP_PASSWORD" in 보, "보고가 고지와 수정 요청을 한 줄로")

    print("\n== 같은 제안 되풀이면 멈춘다 · 바퀴는 최대 5 ==")
    같은 = json.dumps({"꼴": "패치", "패치": [{"파일": "check3.py", "old": "exit(1)", "new": "exit(2)"}], "왜": "또"})
    RP.제안기 = lambda p: 같은
    r = RP.고치기("python3 check3.py", "늘 실패", repo=repo, 바퀴=5)
    ok(r["바퀴"] == 2 and r["해본것"][-1]["판정"] == "반복" and "되풀이" in r["남은것"],
       f"**같은 패치를 두 번 내면 2바퀴에서 멈춘다** ({[h['판정'] for h in r['해본것']]})")
    ok("exit(1)" in (repo / "check3.py").read_text(encoding="utf-8"), "실패한 패치는 되돌아가 있다")
    n = {"수": 0}

    def 매번다른(p):
        n["수"] += 1
        return json.dumps({"꼴": "명령", "명령": f"echo {n['수']}", "왜": "x"})
    RP.제안기 = 매번다른
    r = RP.고치기("python3 check3.py", "늘 실패", repo=repo, 바퀴=99)
    ok(r["바퀴"] == 5 and n["수"] == 5, f"**바퀴 99 를 줘도 최대 5** ({r['바퀴']}, 호출 {n['수']})")

    print("\n== 깨진 제안 · 바퀴 상한 ==")
    RP.제안기 = lambda p: "JSON 아님 {{{"
    r = RP.고치기("python3 check3.py", "늘 실패", repo=repo, 바퀴=2)
    ok(not r["해결"] and [h["판정"] for h in r["해본것"]] == ["거절", "반복"] and "되풀이" in r["남은것"],
       f"깨진 JSON 은 거절 바퀴 -- 같은 것이 또 오면 반복으로 멈춘다 ({[h['판정'] for h in r['해본것']]})")

    def 죽는수리기(p):
        raise RuntimeError("쿼터 소진")
    RP.제안기 = 죽는수리기
    r = RP.고치기("python3 check3.py", "x", repo=repo)
    ok(not r["돌았나"] and "수리기를 못 불렀다" in r["남은것"], "모델을 못 부르면 못돌림")

    print("\n== CLI (임시 git 저장소에서 -- 감사는 git 아닌 사본 안에서 이 검사를 돌린다) ==")
    p = subprocess.run(["python3", "repair/run.py", "--명령", "true", "--증상", "배선", "--저장소", str(repo)],
                       cwd=str(뿌리), capture_output=True, text=True)
    ok(p.returncode == 0 and "해결" in p.stdout, f"CLI: 끝값 0 재현은 바로 해결 (끝값 {p.returncode}: {(p.stdout + p.stderr)[-200:]!r})")

    print("\n== 틈: harvest 가 못 푼 증상을 검색어로 ==")
    from dig import harvest as H
    (repo / "eval" / "tasks").mkdir(parents=True)
    틈 = H.틈찾기(repo)
    ok(any(g["갈래"] == "수리" and "Username" in g["말"] for g in 틈), f"수집기의 틈에 못 푼 증상이 들어온다 ({[g['말'][:30] for g in 틈]})")
finally:
    RP.제안기 = None
    RP.모으기 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("::" in (dispatch.run("!고치기 python3 x.py", allow_write=True) or ""), ":: 없으면 꼴을 알려준다")
ok("관리 채널" in (dispatch.run("!고치기 python3 x.py :: 증상", allow_write=False) or ""), "공개 채널 거절")
불림 = []
dispatch.run("!고치기 python3 mailer.py --진단 :: 5.7.8 not accepted",
             runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0] == ["python3", "repair/run.py", "--명령", "python3 mailer.py --진단", "--증상", "5.7.8 not accepted"],
   f"명령과 증상이 argv 로 갈라진다 ({불림})")
ok("차단" in (dispatch.run("!고치기 rm -rf gates/ :: x", allow_write=True) or ""), "게이트가 막는 재현 명령은 거절")
ok(dispatch.run("!고치기장 x") is None, "붙여 쓴 `!고치기장` 은 명령이 아니다")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def repair(command: str, symptom: str)" in _도구 and "repair_run.고치기" in _도구, "repair 도구가 루프를 부른다")
ok(_서버.count(" repair,") >= 2 and "repair 도구" in _서버, "ADMIN_TOOLS·임포트·프롬프트에 repair")
ok("[사람에게 묻기 전에" in _서버 and "(1) 없이 (2) 로 가지 마라" in _서버,
   "**프롬프트: 사람에게 묻기 전에 자가 해결 단계가 먼저** (사용자 규정)")
from router import call as R  # noqa: E402
ok("수리기" in R.역할들, "router 역할표에 수리기")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("repair: 실측·되돌림·해결 · 명령/게이트 · 사람 · 깨진 제안 · 기억 메모 · 틈 · 배선 -- 통과")
