"""`scripts/novel_purge.sh` -- **가짜 나무를 지어 실제로 돌린다.**

이것은 **되돌릴 수 없는 것을 지우는 스크립트**다. 원고는 전부 .gitignore 라 깃 어디에도
사본이 없다. 그러니 "지켜야 할 것을 지키나" 를 글로 확인하는 것으로는 모자란다 --
`bash -n` 과 grep 은 파일이 한 줄도 안 도는 동안 전부 통과한다(실측 2026-09-09 seek.sh).

여기서 붙드는 것:
  1. list 가 **아무것도 안 지운다**
  2. delete 가 원고를 지운다
  3. **지켜야 할 것을 안 지운다** -- knu/ · targets.json · directives.json · plan.json · *.py · *.md
  4. scope=output 이 corpus/holdout 을 안 건드린다 (표본은 따로 골라야 지운다)
  5. 없는 디렉터리·틀린 인자는 2 로 막는다
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
스크립트 = 뿌리 / "scripts" / "novel_purge.sh"
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


원고들 = ["romance.json", "seeded.json", "seeds_used.json", "final.json", "final.txt",
        "tune.jsonl", "tune.best.json", "arm.json", "spine.json",
        "seeded.scenes.jsonl", "romance.debt.jsonl", "romance.json.bak",
        "full_drift.txt", "drift.json.20260901", "baseline_A.txt", "corpus_report.txt"]
지킬것 = ["targets.json", "directives.json", "plan.json",
        "turn.py", "style.py", "README.md", "DATA.md"]


def 나무(뿌리경로: Path):
    d = 뿌리경로 / "novel"
    d.mkdir(parents=True)
    for f in 원고들 + 지킬것:
        (d / f).write_text("원고든 코드든 한 줄\n", encoding="utf-8")
    (d / "knu").mkdir()
    (d / "knu" / "SentiWord_Dict.txt").write_text("사전\n", encoding="utf-8")
    for c in ("corpus", "holdout"):
        (d / c).mkdir()
        (d / c / "A.txt").write_text("표본 소설\n", encoding="utf-8")
    return d


def 돌리기(d: Path, 모드: str, 범위: str = "output"):
    r = subprocess.run(["bash", str(스크립트), 모드, 범위, str(d)],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


바깥 = Path(tempfile.mkdtemp(prefix="purge-"))
try:
    print("== list 는 아무것도 안 지운다 ==")
    d = 나무(바깥 / "a")
    코드, 글 = 돌리기(d, "list")
    ok(코드 == 0, f"list 가 0 으로 끝난다 ({코드})")
    ok(all((d / f).exists() for f in 원고들), "**원고가 그대로 있다**")
    ok("아무것도 안 지웠다" in 글, "안 지웠다고 말한다")
    ok(f"걸린 것 {len(원고들)}개" in 글, f"걸린 수를 먼저 보인다 ({len(원고들)}개여야 한다)")

    print("\n== delete 가 원고를 지운다 ==")
    d = 나무(바깥 / "b")
    코드, 글 = 돌리기(d, "delete")
    ok(코드 == 0, f"delete 가 0 으로 끝난다 ({코드})")
    남은원고 = [f for f in 원고들 if (d / f).exists()]
    ok(not 남은원고, f"원고가 다 지워졌다 (남은 것 {남은원고})")

    print("\n== 지켜야 할 것을 안 지운다 ==")
    for f in 지킬것:
        ok((d / f).exists(), f"`{f}` 가 남았다")
    ok((d / "knu" / "SentiWord_Dict.txt").exists(),
       "**knu/ 감성사전이 남았다** -- 남의 자료이고 turn.py 가 읽는다")

    print("\n== scope=output 은 표본 말뭉치를 안 건드린다 ==")
    ok((d / "corpus" / "A.txt").exists() and (d / "holdout" / "A.txt").exists(),
       "corpus·holdout 이 남았다 -- 표본은 `all` 로 명시해야 지운다")

    print("\n== scope=all 은 표본까지 지운다 ==")
    d = 나무(바깥 / "c")
    코드, 글 = 돌리기(d, "delete", "all")
    ok(코드 == 0 and not (d / "corpus").exists() and not (d / "holdout").exists(),
       f"corpus·holdout 이 지워졌다 ({코드})")
    ok((d / "knu" / "SentiWord_Dict.txt").exists() and (d / "turn.py").exists(),
       "**all 에서도 knu/ 와 코드는 지키다** -- 범위가 넓어져도 지킬 것은 같다")

    print("\n== 틀린 인자는 막는다 ==")
    코드, _ = 돌리기(바깥 / "없는데", "list")
    ok(코드 == 2, f"없는 디렉터리는 2 ({코드})")
    d = 나무(바깥 / "d")
    코드, _ = 돌리기(d, "지워")
    ok(코드 == 2, f"모르는 모드는 2 ({코드})")
    ok(all((d / f).exists() for f in 원고들), "모드가 틀렸을 때 **아무것도 안 지운다**")
    코드, _ = 돌리기(d, "delete", "전부")
    ok(코드 == 2, f"모르는 범위는 2 ({코드})")
    ok(all((d / f).exists() for f in 원고들), "범위가 틀렸을 때도 안 지운다")
finally:
    shutil.rmtree(바깥, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("novel_purge: list 는 안 지운다 · delete 는 지운다 · 지킬 것은 지킨다 · 틀린 인자는 막는다 -- 통과")
