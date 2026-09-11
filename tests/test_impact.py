"""impact(이 코드를 고치면 무엇이 딸려 움직이는가)를 임시 저장소로 붙든다.

사용자(2026-09-11): "봇이 '만약에 코드를 이렇게 고치면 발생하는 모든 경우의 수' 를 파악해야 한다."
실측: git_sync 가 부르는 것을 바꾸면서 **그것이 관리 채널 답변 경로 안에서 돈다**는 것을 안 짚었다.

붙드는 것: (1) 임포트 그래프가 앞·뒤 두 방향으로 선다, (2) 역의존이 전이적이다(A<-B<-C),
(3) 진입점 표가 '어느 입구에 닿는가' 와 '왜 위험한가' 를 준다, (4) 표지가 새로 들어온 망 호출·
무한 되풀이를 짚는다, (5) 덮는 검사는 audit.검사찾기 를 그대로 쓴다(두 벌 금지), (6) 진짜
저장소에서 commit_guard 를 짚으면 **답변 경로·커밋 경로**가 나온다(내가 놓쳤던 그 둘), (7) 배선.

LLM·망 없이 돈다. 실행: python3 tests/test_impact.py
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

import impact as I  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
d = Path(tempfile.mkdtemp(prefix="test-impact-"))
try:
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    (d / "low.py").write_text("X = 1\n", encoding="utf-8")
    (d / "mid.py").write_text("import low\n", encoding="utf-8")
    (d / "top.py").write_text("from mid import *\n", encoding="utf-8")
    (d / "홀로.py").write_text("Y = 2\n", encoding="utf-8")
    (d / "pkg").mkdir()
    (d / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (d / "pkg" / "leaf.py").write_text("import top\n", encoding="utf-8")

    print("== 임포트 그래프 · 역의존(전이) ==")
    앞, 뒤 = I.임포트그래프(d)
    ok("low" in 앞["mid"] and "mid" in 뒤["low"], "앞·뒤 두 방향")
    역 = I.역의존("low", 뒤)
    ok(set(역) == {"mid", "top", "pkg.leaf"} and 역[0] == "mid",
       f"**A<-B<-C 전이적으로, 가까운 것부터** ({역})")
    ok(I.역의존("홀로", 뒤) == [], "홀로 선 모듈은 부르는 이가 없다")

    print("\n== 표지: 더한 글에서 위험을 짚는다 ==")
    표 = dict(I.표지들("+ import urllib.request\n+ while True:\n+     time.sleep(30)\n"))
    ok("망 호출" in 표 and "무한 되풀이" in 표 and "긴 잠" in 표, f"망·무한·잠 ({sorted(표)})")
    ok(not I.표지들("+ X = 1\n"), "멀쩡한 글엔 표지 없음")
    ok("답변 경로" in dict(I.표지들("+ urlopen(x)\n"))["망 호출"], "망 호출의 까닭이 답변 경로를 말한다")
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n== 진짜 저장소: 내가 놓쳤던 그 둘을 짚는가 ==")
r = I.영향(뿌리, 파일들=["commit_guard.py"])
입구 = dict(r["진입점"])
ok("discord_bot_server._git_sync_locked" in 입구, "**커밋 경로에 닿는다고 말한다**")
ok("discord_bot_server._handle_admin_message" in 입구, "**관리 채널 답변 경로에 닿는다고 말한다**")
ok("사람이 답을 그만큼 기다린다" in 입구["discord_bot_server._handle_admin_message"], "왜 위험한지까지 준다")
ok("아무것도 저장하지 못한다" in 입구["discord_bot_server._git_sync_locked"], "커밋 경로가 막히면 무엇이 죽는지")
ok("discord_bot_server" in r["역의존"]["commit_guard.py"], "봇이 이것을 부른다")
덮는 = sorted({t for ts in r["검사"].values() for t in ts})
ok(any("test_commit_guard" in t for t in 덮는), f"덮는 검사를 audit 과 같은 눈으로 찾는다 ({len(덮는)}개)")
보 = I.보고(r)
ok("닿는 입구" in 보 and "덮는 검사" in 보, "보고에 입구·검사")

r2 = I.영향(뿌리, 파일들=[])
ok(r2["파일"] == [] and "바뀐 .py 가 없다" in I.보고(r2), "바뀐 코드가 없으면 그렇다고 말한다")

print("\n== 배선 ==")
_guard = (뿌리 / "commit_guard.py").read_text(encoding="utf-8")
ok("import impact" in _guard and "impact.보고(r영)" in _guard, "**문지기가 커밋 전에 영향을 보인다**")
_plan = (뿌리 / "plan" / "store.py").read_text(encoding="utf-8")
ok("import impact" in _plan and "impact.보고(r)" in _plan, "**계획(diff)에 영향이 붙는다** -- 승인 전에 사람이 본다")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("impact.py --파일" in _서버 and "모든 경우의 수" in _서버, "프롬프트: 고치기 전에 impact 를 돌려라")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"impact.py"' in _wf, "impact 가 배포 경로에")
p = subprocess.run(["python3", "impact.py", "--파일", "relay.py"], cwd=str(뿌리), capture_output=True, text=True, timeout=120)
ok(p.returncode == 0 and "영향 분석" in p.stdout, "CLI 가 돈다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("impact: 그래프 · 전이 역의존 · 입구 · 표지 · 검사 · 배선 -- 통과")
