"""**되돌이(무한 재귀)와 원장 더럽히기를 붙든다.** 실측 2026-09-15.

## 무슨 일이 났나

`eval/acceptance.py` 를 고친 판에서 인수 검사를 돌렸더니 프로세스가 끝없이 불어났다.

    eval/acceptance.py --(기관:audit 점검)--> audit/run.py
      --(바뀐 파일에 걸린 검사)--> tests/test_acceptance.py --> eval/acceptance.py --> ...

고아 프로세스가 열 벌 넘게 살아 있었고, **대마다** `기관:codify` 점검이
`codify/ledger.jsonl` 에 줄을 하나씩 더했다. 추적되는 원장이라 그것이 `git add -A` 로
커밋에 쓸려 들어갔고, 다른 갈래와 충돌했다.

**고리가 잠기는 것은 acceptance 를 고쳤을 때뿐인데, 그때가 바로 이 점검을 돌릴 때다.**
평소에는 안 보이다가 손대는 순간 터지는 꼴이라, 규칙으로는 안 막힌다 -- 검사가 막는다.

## 무엇을 붙드나

  1. 감사 안에서 불리면 `기관:audit` 을 건너뛴다 -- **그리고 통과로 세지 않는다**
  2. 감사가 그 표를 실제로 세운다(안 세우면 손자에게 안 내려간다)
  3. codify 점검이 **추적되는 원장에 안 쓴다**
  4. `scripts/tests.sh` 가 나무를 더럽힌 판을 실패로 낸다
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
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


import eval.wire as W                                             # noqa: E402

print("== 1. 감사 안에서는 기관:audit 을 건너뛴다 ==")
ok(W.안에서돈다 == "SE_IN_AUDIT", f"표 이름이 한 자리에 있다 ({W.안에서돈다})")
_옛 = os.environ.get(W.안에서돈다)
os.environ[W.안에서돈다] = "1"
try:
    줄들 = W.읽기()
finally:
    os.environ.pop(W.안에서돈다, None)
    if _옛 is not None:
        os.environ[W.안에서돈다] = _옛
감사줄 = next((x for x in 줄들 if x["이름"] == "기관:audit"), None)
ok(감사줄 is not None, "기관:audit 점검이 목록에 있다")
ok(감사줄 and 감사줄["판정"] == "못돌림",
   f"**통과가 아니라 못돌림이다** -- 안 돌린 것을 초록으로 세지 않는다 ({감사줄 and 감사줄['판정']})")
ok(감사줄 and "되돌이" in (감사줄["꼬리"] or ""), f"까닭을 적는다 -- {감사줄 and 감사줄['꼬리'][:40]!r}")
ok(any(x["이름"] != "기관:audit" and x["판정"] != "못돌림" for x in 줄들),
   "**나머지 점검은 그대로 돈다** -- 한 점만 끊는다")

print("\n== 2. 감사가 그 표를 실제로 세운다 ==")
_감사 = (뿌리 / "audit" / "run.py").read_text(encoding="utf-8")
_돌리는곳 = _감사.split("돌릴 = sorted(", 1)[-1].split("for t in 돌릴", 1)[0]
ok('os.environ["SE_IN_AUDIT"]' in _돌리는곳,
   "**검사를 돌리기 전에** 세운다 -- 뒤에 세우면 첫 검사가 그대로 되돌이를 판다")

print("\n== 3. codify 점검이 추적되는 원장에 안 쓴다 ==")
_점검 = next(x for x in W.읽기점검 if x[0] == "기관:codify")
ok("--저장소" in _점검[1], f"점검이 --저장소 를 준다 ({_점검[1]})")
ok("{임시}" in _점검[1], "임시 자리를 쓴다")
_원장 = 뿌리 / "codify" / "ledger.jsonl"
_라우터 = 뿌리 / "router" / "ledger.jsonl"
_앞 = _원장.read_text(encoding="utf-8") if _원장.is_file() else ""
_라앞 = _라우터.read_text(encoding="utf-8") if _라우터.is_file() else ""
# **깃발만으로는 모자란다.** 실측 2026-09-15: `--저장소` 만 주고 돌렸더니 codify 의
# 원장은 옮겨졌는데 **`router/ledger.jsonl` 에 두 줄이 늘었다** -- codify 가 속에서
# `router.call` 을 부르고, 그 쪽은 깃발을 못 받아 제 원장을 진짜 자리에 쓴다.
# 깃발은 그 파일 하나에만 닿고, **환경 변수는 손자까지 내려간다.** 둘 다 준다.
임시 = tempfile.mkdtemp(prefix="codify-점검-")
r = subprocess.run(["python3", "codify/run.py", "--원문", "x", "--저장소", 임시],
                   cwd=str(뿌리), capture_output=True, text=True, timeout=120,
                   env=dict(os.environ, SE_LEDGER_ROOT=임시, PYTHONPATH=str(뿌리)))
_뒤 = _원장.read_text(encoding="utf-8") if _원장.is_file() else ""
_라뒤 = _라우터.read_text(encoding="utf-8") if _라우터.is_file() else ""
ok(_앞 == _뒤, f"**진짜로 돌려도 추적되는 원장이 안 늘었다** (끝값 {r.returncode})")
ok(_라앞 == _라뒤,
   "**속에서 부르는 router 의 원장도 안 늘었다** -- 깃발은 한 파일에만 닿고 "
   "환경 변수가 손자까지 내려간다")
ok((Path(임시) / "codify" / "ledger.jsonl").is_file(),
   "**임시 자리에는 적혔다** -- 안 적혔으면 `--저장소` 가 그냥 무시된 것이다")
shutil.rmtree(임시, ignore_errors=True)

print("\n== 3-b. 다섯 원장이 다 옮겨진다 (codify 만이 아니었다) ==")
# 실측 2026-09-15: 배선 점검 한 바퀴에 **다섯 원장에 스물두 줄**이 쌓였다 --
# codify 1 · eval답 4 · improve 4 · router 10 · secaudit 4. codify 만 고치고
# "고쳤다" 고 하면 나머지 넷이 그대로 남는다. 그래서 자리를 한 군데로 모았다.
import ledgerroot as LR                                           # noqa: E402
ok(LR.뿌리(None, "/기본") == Path("/기본"), "환경 변수가 없으면 기본 그대로")
os.environ[LR.환경이름] = "/옮긴데"
try:
    ok(LR.뿌리(None, "/기본") == Path("/옮긴데"), "환경 변수가 서면 거기로")
    ok(LR.뿌리("/준것", "/기본") == Path("/준것"),
       "**부르는 쪽이 준 repo 가 늘 이긴다** -- 검사들이 임시 저장소를 주고 돈다")
finally:
    os.environ.pop(LR.환경이름, None)

# **글자가 아니라 원장을 잰다.** 처음에는 `"Path(repo or REPO) /"` 가 남았나만 봤는데
# 그 검사는 **초록이었고 secaudit 은 여전히 진짜 원장에 쓰고 있었다** -- 그 함수가 맨
# 앞에서 `repo = Path(repo or REPO)` 로 인자를 덮어쓰기 때문이다. 글자를 보는 검사는
# 그 자리를 못 본다. 그래서 실제로 돌리고 줄 수를 센다.
_원장들 = ("codify/ledger.jsonl", "eval/ledger.jsonl", "improve/ledger.jsonl",
        "router/ledger.jsonl", "secaudit/ledger.jsonl")


def _줄수():
    return {f: len((뿌리 / f).read_text(encoding="utf-8").splitlines())
            for f in _원장들 if (뿌리 / f).is_file()}


_앞줄 = _줄수()
_옮긴데 = tempfile.mkdtemp(prefix="원장-")
_환 = dict(os.environ, SE_LEDGER_ROOT=_옮긴데, PYTHONPATH=str(뿌리))
for _명 in (["python3", "codify/run.py", "--원문", "x"],
          ["python3", "secaudit/run.py", "--json"]):
    subprocess.run(_명, cwd=str(뿌리), env=_환, capture_output=True, text=True, timeout=200)
_뒤줄 = _줄수()
_늘어난것 = {f: (_뒤줄[f] - _앞줄[f]) for f in _앞줄 if _뒤줄.get(f, 0) != _앞줄[f]}
ok(not _늘어난것,
   f"**진짜로 돌려도 추적되는 원장이 한 줄도 안 는다** (늘어난 것 {_늘어난것})")
ok(any((Path(_옮긴데) / f).is_file() for f in _원장들),
   f"**옮긴 자리에는 적혔다** -- 안 적혔으면 표가 그냥 무시된 것이다 "
   f"({[f for f in _원장들 if (Path(_옮긴데) / f).is_file()]})")
shutil.rmtree(_옮긴데, ignore_errors=True)

_와이어 = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok("ledgerroot.환경이름" in _와이어,
   "배선 점검이 그 표를 세운다 -- 안 세우면 자식이 여전히 진짜 원장에 쓴다")

print("\n== 4. tests.sh 가 나무를 더럽힌 판을 실패로 낸다 ==")
_셸 = (뿌리 / "scripts" / "tests.sh").read_text(encoding="utf-8")
ok("before_tree=" in _셸 and "after_tree=" in _셸, "앞뒤로 나무를 잰다")
ok('git status --porcelain -uno' in _셸,
   "**추적되는 것만 본다**(-uno) -- 새 임시 파일까지 실패로 세면 늘 우는 경보가 된다")
_끝 = _셸.split("after_tree=", 1)[-1]
ok('fail=$((fail + 1))' in _끝, "다르면 실패 수를 올린다 -- 말만 하고 지나가지 않는다")

# **글자만 보면 안 된다.** 바로 위 세 줄은 `tests.sh` 의 원문을 본 것이고, 원문이
# 맞아도 안 도는 수가 있다(이 저장소가 seek.sh 에서 치른 값이다). 그래서 **더럽히는
# 검사를 하나 지어 실제로 돌려** 빨개지는지 본다. 더럽히는 자리는 `.gitignore` 가
# 아닌 추적되는 파일이어야 한다.
_찌꺼기 = 뿌리 / "tests" / "test_zz일부러더럽힌다.py"
_더럽힐것 = 뿌리 / "codify" / "ledger.jsonl"
_원본 = _더럽힐것.read_text(encoding="utf-8")
_찌꺼기.write_text("\n".join([
    "from pathlib import Path",
    "p = Path(__file__).resolve().parent.parent / 'codify' / 'ledger.jsonl'",
    "with open(p, 'a', encoding='utf-8') as f:",
    "    f.write('일부러 더럽힌 줄\\n')",
    "print('일부러 더럽혔다 -- tests.sh 가 이것을 잡아야 한다')",
    "",
]), encoding="utf-8")
try:
    _r = subprocess.run(["bash", "scripts/tests.sh", "-k", "zz일부러더럽힌다"],
                        cwd=str(뿌리), capture_output=True, text=True, timeout=300)
    _글 = _r.stdout + _r.stderr
    ok(_r.returncode != 0,
       f"**더럽힌 판이 빨강으로 끝난다** (끝값 {_r.returncode}) -- 초록이면 아무도 못 본다")
    ok("추적되는 파일을 건드렸다" in _글, f"무엇이 잘못인지 말한다 -- {_글.strip()[-120:]!r}")
    ok("codify/ledger.jsonl" in _글, "**어느 파일인지 짚는다** -- 안 짚으면 찾느라 또 헤맨다")
finally:
    _찌꺼기.unlink(missing_ok=True)
    _더럽힐것.write_text(_원본, encoding="utf-8")
ok(_더럽힐것.read_text(encoding="utf-8") == _원본, "검사가 제 뒤를 치운다")
ok("한글" in _셸 or all(ord(c) < 128 for c in
                      "".join(l.split("=")[0] for l in _셸.splitlines()
                              if "=" in l and not l.strip().startswith("#"))),
   "셸 변수 이름에 한글이 없다 (CLAUDE.md -- bash 는 그것을 대입으로 안 읽는다)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("되돌이 끊기: 한 점만 끊는다 · 통과로 안 센다 · 원장을 안 더럽힌다 · 나무를 붙든다 -- 통과")
