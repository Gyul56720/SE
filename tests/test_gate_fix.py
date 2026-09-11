r"""게이트 자동 고치기 -- 위반을 띄우기만 하지 않고 **코드가 먼저 고치고 다시 검사한다.**

실측 2026-09-11: 봇이 codify 로 만든 파일의 `\int` 에 G017 이 걸려 커밋이 막혔다(그 파일은
gitignore 인데도). 사용자: "게이트 위반은 띄우는 게 아니라 자동으로 고쳐줘야지".

붙드는 것: (1) escapes.고치기 -- r 접두 / 백슬래시 겹치기 / raw·f-string 은 손 안 댐 / 문법
깨지면 안 고침, (2) 게이트는 gitignore 파일을 안 본다, (3) G017.fix 가 파일을 고쳐 check 가
비게 된다, (4) G013.fix 가 빠진 경로를 paths 에 붙여 check 가 비게 된다, (5) run_gates(고치기=True)
가 fix 있는 게이트는 고치고 재검사, fix 없는 게이트는 그대로 막는다 + 보고에 '고침' 줄,
(6) codify 가 저장 전에 고친다, (7) 배선 -- 봇의 git_sync 가 고치기=True 로 부른다.

실행: python3 tests/test_gate_fix.py
"""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import escapes      # noqa: E402
import gatekeeper   # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== escapes.고치기 ==")
새, n = escapes.고치기('x = "\\int_0^1 f"\n')
ok(n == 1 and 새 == 'x = r"\\int_0^1 f"\n', f"r 접두를 붙인다 ({새.strip()!r})")
새, n = escapes.고치기('"""\\lambda x\n두 줄"""\ny = 1\n')
ok(n == 1 and 새.startswith('r"""\\lambda'), "독스트링(여러 줄)도 r 로")
새, n = escapes.고치기('s = "\\d\\""\n')
ok(n == 1 and 새 == 's = "\\\\d\\""\n', f"따옴표 이스케이프가 있어 raw 가 안 되면 백슬래시를 겹친다 ({새.strip()!r})")
ok(escapes.고치기('s = r"\\int"\n')[1] == 0 and escapes.고치기('s = f"\\int{1}"\n')[1] == 0, "raw · f-string 은 손대지 않는다")
ok(escapes.고치기('s = "\\n\\t ok"\n')[1] == 0, "멀쩡한 이스케이프는 그대로")
새, n = escapes.고치기('s = "\\int f\\n"\n')
ok(n == 1 and 새 == 's = "\\\\int f\\n"\n', f"**유효한 \\n 이 섞여 있으면 r 대신 잘못된 것만 겹친다(뜻 보존)** ({새.strip()!r})")
src, n = escapes.고치기('def f(:\n  "\\int"\n')
ok(n == 0, "문법이 깨진 원문은 안 고친다(0)")

os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
임시 = Path(tempfile.mkdtemp(prefix="test-gatefix-"))
try:
    subprocess.run(["git", "-C", str(임시), "init", "-q"], check=True)
    (임시 / ".gitignore").write_text("out/\n", encoding="utf-8")
    (임시 / "out").mkdir()
    (임시 / "out" / "gen.py").write_text('"""\\int"""\n', encoding="utf-8")
    (임시 / "bad.py").write_text('"""\\lambda"""\nX = "\\sum"\n', encoding="utf-8")
    ctx = gatekeeper.GateContext(임시)
    파일들 = [ctx.rel(f) for f in ctx.python_files()]

    print("\n== gitignore 파일은 게이트가 안 본다 ==")
    ok("bad.py" in 파일들 and "out/gen.py" not in 파일들, f"**gitignore(out/) 는 제외** ({파일들})")

    print("\n== G017: check -> fix -> check ==")
    G017 = importlib.import_module([m for m in os.listdir(뿌리 / "gates") if m.startswith("G017")][0][:-3].join(["gates.", ""]))
    ok(len(G017.check(ctx)) == 2, "bad.py 의 두 리터럴이 걸린다")
    고침 = G017.fix(ctx)
    ok(고침 == ["bad.py (2개 리터럴)"] and G017.check(gatekeeper.GateContext(임시)) == [],
       f"**fix 가 고치고 check 가 빈다** ({고침})")
    ok((임시 / "bad.py").read_text(encoding="utf-8") == 'r"""\\lambda"""\nX = r"\\sum"\n', "파일이 r 접두로 바뀌었다")

    print("\n== G013: 빠진 배포 경로를 fix 가 붙인다 ==")
    G013 = importlib.import_module([m for m in os.listdir(뿌리 / "gates") if m.startswith("G013")][0][:-3].join(["gates.", ""]))
    (임시 / ".github" / "workflows").mkdir(parents=True)
    wf = 임시 / ".github" / "workflows" / "deploy-oracle.yml"
    wf.write_text('on:\n  push:\n    paths:\n      - ".github/workflows/deploy-oracle.yml"\n      - "server.py"\n      - "deploy/x.service"\n      - "gatekeeper.py"\n      - "self_challenge.py"\n      - "gates/**"\njobs: {}\n', encoding="utf-8")
    (임시 / "deploy").mkdir()
    (임시 / "deploy" / "x.service").write_text("[Service]\nExecStart=/usr/bin/python3 /home/ubuntu/SE/server.py\n", encoding="utf-8")
    (임시 / "server.py").write_text("import helper\n", encoding="utf-8")
    (임시 / "helper.py").write_text("X = 1\n", encoding="utf-8")
    ctx = gatekeeper.GateContext(임시)
    전 = G013.check(ctx)
    ok(any("helper.py" in v for v in 전), f"helper.py 가 paths 에 없다고 걸린다 ({len(전)})")
    고침 = G013.fix(ctx)
    ok("helper.py" in 고침 and '- "helper.py"' in wf.read_text(encoding="utf-8"), f"**fix 가 paths 에 붙인다** ({고침})")
    ok(G013.check(gatekeeper.GateContext(임시)) == [], "붙인 뒤 check 가 빈다")

    print("\n== run_gates(고치기=True): fix 있는 건 고치고 재검사, 없는 건 막는다 ==")
    상태 = {"n": 0}
    고칠수있는 = types.SimpleNamespace(__name__="GX1", RULE_ID="GX1", TITLE="고칠 수 있는", ORIGIN="", EVIDENCE="",
                                   check=lambda c: ["위반"] if 상태["n"] == 0 else [],
                                   fix=lambda c: (상태.__setitem__("n", 1) or ["x.py"]))
    못고치는 = types.SimpleNamespace(__name__="GX2", RULE_ID="GX2", TITLE="못 고치는", ORIGIN="", EVIDENCE="", check=lambda c: ["남는 위반"])
    _원래 = gatekeeper.load_gates
    gatekeeper.load_gates = lambda: [고칠수있는, 못고치는]
    try:
        r = gatekeeper.run_gates(임시, 고치기=True)
        ok(not r.passed and r.고친것 == ["GX1 고침: x.py"], f"GX1 은 고쳐 통과, GX2 는 그대로 막힘 ({r.고친것})")
        ok([x.rule_id for x in r.results if x.violations] == ["GX2"], "남는 위반은 fix 없는 게이트뿐")
        상태["n"] = 0
        r2 = gatekeeper.run_gates(임시, 고치기=False)
        ok(r2.고친것 == [] and [x.rule_id for x in r2.results if x.violations] == ["GX1", "GX2"], "고치기=False 면 예전처럼 띄우기만")
    finally:
        gatekeeper.load_gates = _원래

    print("\n== codify 는 저장 전에 고친다 ==")
    from codify import run as C
    C.코드공 = lambda p: '```python\n"""\\int f"""\ndef f(*a, **k):\n    return 0\n```'
    try:
        r = C.코드화({"종류": "수식", "이름": "esc", "원문": "x", "예시": []}, repo=임시)
        본 = (임시 / r["파일"]).read_text(encoding="utf-8")
        ok(r["성공"] and r.get("이스케이프고침") == 1 and 'r"""\\int f"""' in 본, "**저장된 코드가 이미 r 로 고쳐져 있다**")
    finally:
        C.코드공 = None
finally:
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
_guard = (뿌리 / "commit_guard.py").read_text(encoding="utf-8")
ok("commit_guard.검사(Path(REPO_DIR), 빠름=True)" in _서버 and "run_gates(repo, 고치기=True)" in _guard,
   "**봇의 git_sync 가 문지기(commit_guard)를 지나고, 문지기가 먼저 고치고 재검사한다**")
_gk = (뿌리 / "gatekeeper.py").read_text(encoding="utf-8")
ok('"--고치기" in sys.argv' in _gk, "CLI `python3 gatekeeper.py --고치기`")
p = subprocess.run(["python3", "escapes.py", "tests/test_gate_fix.py"], cwd=str(뿌리), capture_output=True, text=True, timeout=30)
ok(p.returncode == 0 and "그대로" in p.stdout, "escapes CLI 가 돈다(이 파일은 raw 독스트링이라 그대로)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("gate fix: escapes · gitignore 제외 · G017/G013 fix · run_gates 고치기 · codify · 배선 -- 통과")
