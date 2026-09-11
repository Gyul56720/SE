"""entrypoints(진입점을 **세어서 찾는다**)를 임시 저장소로 붙든다 -- 손으로 적은 목록이 아님을 못박는다.

사용자(2026-09-11): "배선 읽기점검이 하드코딩되면 안 된다고. 어떻게 해결할까 이런 문제를?"
그리고: "가능한 모든 것들(시스템 망가짐을 방지하는 필수 원칙을 빼고) 나머지를 일반해로 바꿔."

붙드는 것: (1) `__main__` 이 있는 파일을 ast 로 찾는다, (2) `add_argument("--…")` 를 읽는다,
(3) **함수 안의** 남의 꾸러미 임포트(늦은 임포트)만 센다 -- 꼭대기 임포트는 어떤 검사에도 걸리므로,
(4) 뿌리에 있는 파일은 본디 안전하다(거짓 경보 금지), (5) 꾸러미 진입점이 늦은 임포트를 쓰면서
뿌리를 안 넣고 스크립트 꼴로 불리면 **위험**, (6) `-m` 으로만 불리면 안전, (7) **진짜 저장소에
위험이 없고, 그 사고를 되살리면 잡는다**, (8) 자가개선이 이것을 틈으로 집는다.

실행: python3 tests/test_entrypoints.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import entrypoints as E  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


d = Path(tempfile.mkdtemp(prefix="test-ep-"))
try:
    (d / "plan").mkdir(); (d / "plan" / "__init__.py").write_text("", encoding="utf-8")
    (d / "plan" / "store.py").write_text("X = 1\n", encoding="utf-8")
    (d / "improve").mkdir(); (d / "improve" / "__init__.py").write_text("", encoding="utf-8")
    # 늦은 임포트(함수 안) + 뿌리 안 넣음 -- 사고의 꼴
    (d / "improve" / "run.py").write_text(
        'import argparse\n\n\ndef 하기():\n    from plan import store\n    return store.X\n\n\n'
        'def main():\n    ap = argparse.ArgumentParser()\n    ap.add_argument("--부탁", default="")\n'
        '    ap.add_argument("--틈만", action="store_true")\n    return 0\n\n\n'
        'if __name__ == "__main__":\n    raise SystemExit(main())\n', encoding="utf-8")
    # 꼭대기 임포트만 -- 늦은 것이 아니다
    (d / "safe").mkdir(); (d / "safe" / "__init__.py").write_text("", encoding="utf-8")
    (d / "safe" / "run.py").write_text(
        'from plan import store\n\n\ndef main():\n    return store.X\n\n\n'
        'if __name__ == "__main__":\n    raise SystemExit(main())\n', encoding="utf-8")
    # 뿌리 파일 -- 늦은 임포트가 있어도 본디 안전
    (d / "root_tool.py").write_text(
        'def go():\n    from plan import store\n    return store.X\n\n\n'
        'if __name__ == "__main__":\n    go()\n', encoding="utf-8")
    (d / "부르는곳.py").write_text(
        'import subprocess\nsubprocess.run(["python3", "improve/run.py", "--부탁", "x"])\n'
        'subprocess.run(["python3", "root_tool.py"])\n'
        'subprocess.run(["python3", "-m", "safe.run"])\n', encoding="utf-8")

    print("== 세어 찾기 ==")
    진 = {e["파일"]: e for e in E.진입점들(d)}
    ok({"improve/run.py", "safe/run.py", "root_tool.py"} <= set(진),
       f"__main__ 이 있는 파일을 ast 로 찾는다 ({sorted(진)})")
    ok(진["improve/run.py"]["깃발"] == ["--부탁", "--틈만"], f"깃발을 ast 로 읽는다 ({진['improve/run.py']['깃발']})")
    ok(진["improve/run.py"]["늦은임포트"] == ["plan"], "함수 안의 남의 꾸러미 = 늦은 임포트")
    ok(진["safe/run.py"]["늦은임포트"] == [], "**꼭대기 임포트는 안 센다** -- 그건 임포트하자마자 터져 어디서든 걸린다")
    ok(진["improve/run.py"]["모듈"] == "improve.run" and 진["improve/run.py"]["꾸러미"] == "improve", "모듈 이름·꾸러미")
    ok(진["root_tool.py"]["꾸러미"] == "", "뿌리 파일은 꾸러미가 없다")

    print("\n== 부르는 자리 ==")
    부 = E.부르는자리(d)
    ok("improve/run.py" in 부["스크립트"] and "safe.run" in 부["모듈"], f"스크립트 꼴·모듈 꼴을 갈라 긁는다")

    print("\n== 위험 판정 ==")
    위 = {x["파일"]: x for x in E.위험들(d)}
    ok(list(위) == ["improve/run.py"], f"**늦은 임포트 + 뿌리 안 넣음 + 스크립트 호출 = 위험** ({sorted(위)})")
    ok("-m improve.run" in 위["improve/run.py"]["왜"], "고칠 길을 말해 준다")
    ok("root_tool.py" not in 위, "**뿌리 파일은 거짓 경보를 안 낸다** -- 스크립트 디렉터리가 곧 뿌리다")
    ok("safe/run.py" not in 위, "-m 으로만 불리는 것은 안전")

    print("\n== 고치면 사라진다 (두 길 다) ==")
    본 = (d / "improve" / "run.py").read_text(encoding="utf-8")
    (d / "improve" / "run.py").write_text(
        "import sys\nfrom pathlib import Path\nREPO = Path(__file__).resolve().parent.parent\n"
        "sys.path.insert(0, str(REPO))\n" + 본, encoding="utf-8")
    ok(not E.위험들(d), "뿌리를 넣으면 위험 없음")
    (d / "improve" / "run.py").write_text(본, encoding="utf-8")
    (d / "부르는곳.py").write_text('import subprocess\nsubprocess.run(["python3", "-m", "improve.run"])\n', encoding="utf-8")
    ok(not E.위험들(d), "-m 으로만 부르면 위험 없음(뿌리를 안 넣어도)")

    print("\n== 안 밟은 깃발 ==")
    (d / "부르는곳.py").write_text('import subprocess\nsubprocess.run(["python3", "improve/run.py", "--부탁", "x"])\n', encoding="utf-8")
    안 = {x["파일"]: x["안밟은"] for x in E.안밟은깃발(d)}
    ok(안.get("improve/run.py") == ["--틈만"], f"아무도 안 부르는 깃발을 짚는다 ({안.get('improve/run.py')})")
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n== 진짜 저장소 ==")
ok(len(E.진입점들(뿌리)) > 50, f"진입점 {len(E.진입점들(뿌리))}개를 세어 찾는다")
ok(not E.위험들(뿌리), f"**지금 위험 없음** -- {[x['파일'] for x in E.위험들(뿌리)]}")

print("\n== 그 사고를 되살리면 잡는가 (검사가 검사 구실을 하는가) ==")
_불 = 뿌리 / "improve" / "run.py"
_원 = _불.read_text(encoding="utf-8")
_뺀 = _원.replace("if str(REPO) not in sys.path:\n    sys.path.insert(0, str(REPO))\n", "")
ok(_뺀 != _원, "improve/run.py 에서 뿌리 넣기를 뺄 수 있다")
try:
    _불.write_text(_뺀, encoding="utf-8")
    ok([x["파일"] for x in E.위험들(뿌리)] == ["improve/run.py"],
       "**빼면 바로 잡는다** -- 목록에 적어서가 아니라 세어서")
    import improve.run as I
    틈 = [g for g in I.틈모으기(뿌리) if g["종류"] == "진입점위험"]
    ok(틈 and 틈[0]["판정명령"] == "python3 entrypoints.py --위험만",
       f"**자가개선이 그것을 틈으로 집는다** -- 다음엔 에이전트가 스스로 고친다 ({[g['무엇'] for g in 틈]})")
finally:
    _불.write_text(_원, encoding="utf-8")
ok(_불.read_text(encoding="utf-8") == _원 and not E.위험들(뿌리), "되돌렸고 다시 위험 없음")

print("\n== 부르는 쪽을 고친다: `python3 pkg/x.py` -> `python3 -m pkg.x` ==")
# **왜 부르는 쪽인가.** 실측 2026-09-11: 파일 안에 뿌리 넣는 줄을 적어 머지·배포했는데도
# VM 이 같은 줄에서 또 죽었다 -- 서버가 든 판이 낡았으면 그 줄이 거기 없다. 고침이 코드
# 안에 있으면 **그 코드가 도착해야만** 듣는다. `-m` 은 불리는 파일이 어떤 판이든 산다.
ok(E.모듈꼴(["python3", "improve/run.py", "--부탁", "x"], 뿌리)
   == (["python3", "-m", "improve.run", "--부탁", "x"], "improve.run"), "꾸러미 진입점을 모듈 꼴로")
ok(E.모듈꼴(["python3", "gatekeeper.py"], 뿌리) == (["python3", "gatekeeper.py"], "gatekeeper.py"),
   "**뿌리 파일은 안 바꾼다** -- 거기선 스크립트 디렉터리가 곧 뿌리다")
ok(E.모듈꼴(["python3", "-m", "improve.run", "--틈만"], 뿌리)
   == (["python3", "-m", "improve.run", "--틈만"], "improve.run"), "이미 모듈 꼴이면 그대로")
ok(E.모듈꼴(["bash", "scripts/precheck.sh"], 뿌리) == (["bash", "scripts/precheck.sh"], "scripts/precheck.sh"),
   "파이썬이 아니면 안 건드린다")
ok(E.모듈꼴(["python3", "없는곳/없다.py"], 뿌리) == (["python3", "없는곳/없다.py"], "없는곳/없다.py"),
   "없는 파일은 안 건드린다")

_ed = (뿌리 / "eval" / "discord_cmd.py").read_text(encoding="utf-8")
ok("entrypoints.모듈꼴" in _ed and "_돌고있나(찾을것)" in _ed,
   "**배경 실행이 한 자리에서 모듈 꼴로 바꾼다** -- 모든 명령이 덮인다")

print("\n  -- 실측: 뿌리 넣는 줄이 없는 낡은 판도 `-m` 이면 산다 --")
_낡 = Path(tempfile.mkdtemp(prefix="test-낡-"))
try:
    (_낡 / "plan").mkdir(); (_낡 / "plan" / "__init__.py").write_text("", encoding="utf-8")
    (_낡 / "plan" / "store.py").write_text("값 = 7\n", encoding="utf-8")
    (_낡 / "improve").mkdir(); (_낡 / "improve" / "__init__.py").write_text("", encoding="utf-8")
    # 고치기 전 판 그대로 -- sys.path 를 건드리는 줄이 **없다**
    (_낡 / "improve" / "run.py").write_text(
        'def 하기():\n    from plan import store\n    return store.값\n\n\n'
        'if __name__ == "__main__":\n    print("값=", 하기())\n', encoding="utf-8")
    밖2 = tempfile.mkdtemp(prefix="test-밖2-")
    스 = subprocess.run([sys.executable, "improve/run.py"], cwd=str(_낡), capture_output=True, text=True, timeout=60)
    ok("No module named 'plan'" in (스.stdout + 스.stderr),
       "스크립트 꼴은 **낡은 판에서 죽는다**(사고의 재현)")
    argv, _ = E.모듈꼴([sys.executable, "improve/run.py"], _낡)
    모 = subprocess.run(argv, cwd=str(_낡), capture_output=True, text=True, timeout=60)
    ok(모.returncode == 0 and "값= 7" in 모.stdout,
       f"**같은 낡은 파일이 `-m` 으로는 산다** ({(모.stdout + 모.stderr).strip()[:60]})")
    shutil.rmtree(밖2, ignore_errors=True)
finally:
    shutil.rmtree(_낡, ignore_errors=True)

print("\n== CLI · 배선 ==")
p = subprocess.run(["python3", "entrypoints.py", "--위험만"], cwd=str(뿌리), capture_output=True, text=True, timeout=180)
ok(p.returncode == 0 and "위험 0개" in p.stdout, f"--위험만 은 위험이 없으면 끝값 0 ({p.stdout.strip()[-30:]})")
_run = (뿌리 / "improve" / "run.py").read_text(encoding="utf-8")
ok("entrypoints" in _run and "진입점위험" in _run, "자가개선이 진입점 위험을 틈 출처로 쓴다")
ok("핵심모듈들" in _run and "임포트그래프" in _run,
   "**핵심 모듈도 손으로 안 적는다** -- 봇의 임포트 그래프에서 센다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("entrypoints: 세어 찾기 · 늦은 임포트 · 거짓 경보 없음 · 위험·고침 · 되살리기 · 자가개선 틈 -- 통과")
