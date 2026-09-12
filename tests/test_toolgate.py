"""toolgate(도구 호출 시점 게이트)와 filetools(정확 편집)를 임시 저장소에서 **실제로
돌려** 붙든다.

붙드는 것: (1) 사고·CLAUDE.md 금지에 묶인 명령은 차단되고 읽기·정상 명령은 통과한다
(거짓 양성이 늘 우는 경보를 만든다), (2) 경로 게이트가 저장소 밖·게이트·원장·.env 를
막는다, (3) 편집은 old 가 정확히 한 번일 때만 바뀌고 0번·2번·빈 old 는 거절된다,
(4) 읽기는 줄 번호를 붙이고 .env 는 못 읽는다, (5) 봇 배선 -- run_shell 이 Popen
**앞에서** toolgate.검사 를 부르고, 두 도구가 ADMIN_TOOLS 에 있고, 프롬프트가 edit_file 을
시킨다(봇은 여기서 임포트 못 하므로 원문을 본다).

LLM·네트워크 없이 돈다. 실행: python3 tests/test_toolgate.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import filetools  # noqa: E402
import toolgate  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== 차단해야 하는 명령 (각각 사고·CLAUDE.md 에 근거) ==")
for 명령, 왜 in [
    ("rm gates/G020_판정_원장과_게이트는_지울_수_없다.py", "게이트 삭제"),
    ("rm -rf gates/", "게이트 통삭제"),
    ("mv gates/G009_verifier_integrity.py /tmp/", "게이트 이동"),
    ("echo 'RULE_ID=1' > gates/G999_x.py", "게이트에 덮어쓰기"),
    ("cp /tmp/x.py gates/G999_x.py", "게이트로 복사"),
    ("sed -i 's/1e-6/1e-2/' gates/G009_verifier_integrity.py", "게이트 sed -i"),
    ("echo '{}' > eval/ledger.jsonl", "판정 원장 덮어쓰기"),
    ("rm router/ledger.jsonl", "판정 원장 삭제"),
    ("truncate -s 0 graph/edges.jsonl", "판정 원장 비우기"),
    ("cat x | sed -i '1d' intent/ledger.jsonl", "판정 원장 sed -i"),
    ("rm -rf /", "루트 통삭제"),
    ("rm -rf .", "저장소 통삭제"),
    ("rm -rf ~", "홈 통삭제"),
    ("cd /home/ubuntu && rm -rf *", "별표 통삭제"),
    ("git push --force origin main", "force push"),
    ("git push -f", "force push 짧은 꼴"),
    ("git push --force-with-lease", "force-with-lease"),
    ("git fetch && git rebase origin/main", "rebase"),
    ("pkill -f python3", "자기 셸 살해"),
    ("pkill -9 -f 'claude -p'", "자기 셸 살해 (시그널 옵션)"),
    ("sudo rm -rf gates/", "sudo 뒤의 삭제"),
    ("ls; rm gates/G001.py", "세미콜론 뒤의 삭제"),
]:
    까닭 = toolgate.검사(명령)
    ok(bool(까닭), f"차단: {왜} ({명령[:40]!r}) -> {까닭[:30]}")

print("\n== 통과해야 하는 명령 (거짓 양성은 늘 우는 경보다) ==")
for 명령, 왜 in [
    ("cat gates/G020_판정_원장과_게이트는_지울_수_없다.py", "게이트 읽기"),
    ("grep -n 'rm -rf' gates/*.py", "게이트 안에서 검색"),
    ("git diff HEAD -- gates/", "게이트 diff"),
    ("ls gates/ && python3 gatekeeper.py", "게이트 목록·실행"),
    ("python3 self_challenge.py prove --candidate /tmp/c.py --broken-tree /tmp/b", "승격 절차"),
    ("echo '{\"x\":1}' >> eval/ledger.jsonl", "판정 원장 덧쓰기(>>)"),
    ("tail -3 router/ledger.jsonl", "판정 원장 읽기"),
    ("python3 eval/run.py", "원장에 적는 모듈"),
    ("rm -rf sandbox/out/20260911-*", "산출물 정리"),
    ("rm -f /tmp/x.txt", "임시 파일 삭제"),
    ("rm -rf node_modules", "상대경로 폴더 삭제"),
    ("git push -u origin claude/x", "정상 push"),
    ("git merge origin/main && git push", "merge 뒤 push"),
    ("git log --oneline -5 | grep rebase", "rebase 라는 말이 든 검색"),
    ("pgrep -af night.sh", "pgrep 확인"),
    ("kill 8311", "PID 로 죽이기"),
    ("echo 'git push --force 는 쓰지 마라' > README.tmp", "경고문을 파일에 쓰기"),
    ("grep -rn 'pkill -f' CLAUDE.md", "CLAUDE.md 에서 검색"),
    ("python3 -c \"print('rm -rf gates/')\"", "문자열 안의 rm"),
    ("git commit -m 'rebase 금지 규칙 추가'", "커밋 메시지 안의 rebase"),
]:
    까닭 = toolgate.검사(명령)
    ok(not 까닭, f"통과: {왜} ({명령[:40]!r}){' <- ' + 까닭 if 까닭 else ''}")

임시 = Path(tempfile.mkdtemp(prefix="test-toolgate-"))
repo = 임시 / "repo"
(repo / "gates").mkdir(parents=True)
(repo / "eval").mkdir()
(repo / "src").mkdir()
(repo / ".git").mkdir()
(repo / "gates" / "G001_x.py").write_text("RULE_ID='G001'\n", encoding="utf-8")
(repo / "eval" / "ledger.jsonl").write_text('{"판정":"초록"}\n', encoding="utf-8")
(repo / ".env").write_text("GEMINI_API_KEY=secret-value-12345\n", encoding="utf-8")
(repo / "src" / "셈.py").write_text(
    "def 더하기(a, b):\n    return a + b\n\n\ndef 빼기(a, b):\n    return a - b\n", encoding="utf-8")

try:
    print("\n== 경로 게이트 ==")
    for path, 쓰기, 왜 in [
        ("../밖.py", True, "저장소 밖"), ("/etc/passwd", True, "절대경로 밖"),
        ("gates/G001_x.py", True, "게이트 편집"), ("eval/ledger.jsonl", True, "판정 원장 편집"),
        (".env", True, ".env 편집"), (".env", False, ".env 읽기"), (".git/config", True, ".git 편집"),
    ]:
        try:
            toolgate.경로풀기(path, 쓰기=쓰기, repo=repo)
            ok(False, f"{왜}({path}) 가 막히지 않았다")
        except ValueError:
            ok(True, f"{왜}({path}) 는 ValueError")
    ok(toolgate.경로풀기("src/셈.py", 쓰기=True, repo=repo).is_file(), "저장소 안 파일은 풀린다")
    ok(toolgate.경로풀기("gates/G001_x.py", 쓰기=False, repo=repo).is_file(),
       "게이트 **읽기**는 된다 -- 막는 것은 쓰기뿐")

    print("\n== 정확 편집 ==")
    말 = filetools.편집("src/셈.py", "    return a + b\n", "    return b + a\n", repo=repo)
    ok("1줄 -> 1줄" in 말 and "return b + a" in (repo / "src" / "셈.py").read_text(encoding="utf-8"),
       f"정확히 한 번이면 바뀐다 ({말})")
    for old, new, 왜 in [
        ("", "x", "빈 old"), ("return a * b", "x", "없는 old"),
        ("a, b", "x", "두 번 나오는 old"), ("return b + a", "return b + a", "old == new"),
    ]:
        try:
            filetools.편집("src/셈.py", old, new, repo=repo)
            ok(False, f"{왜} 가 거절되지 않았다")
        except ValueError as e:
            ok(True, f"{왜} 는 거절 ({str(e)[:40]})")
    # 첫 줄은 맞는데 **뜻이 다른** old(`a * b`)는 여전히 거절 -- 들여쓰기 힌트도 그대로.
    try:
        filetools.편집("src/셈.py", "def 빼기(a, b):\n  return a * b", "x", repo=repo)
        ok(False, "뜻이 다른 old 가 통과했다")
    except ValueError as e:
        ok("들여쓰기" in str(e), f"**첫 줄만 맞으면 들여쓰기 힌트를 준다** ({str(e)[:50]})")
    ok((repo / "src" / "셈.py").read_text(encoding="utf-8").count("def ") == 2,
       "거절된 편집은 파일을 안 건드린다")
    # **공백만 다른 유일한 자리는 맞춘다.** 실측 2026-09-12(VM): `!개선` 의 패치가 들여쓰기 한 칸 차이로
    # `old 가 파일에 없다` 에서 끝났다. 뜻이 아니라 공백이었다. 유일할 때만이고, 그렇다고 말한다.
    _앞 = (repo / "src" / "셈.py").read_text(encoding="utf-8")
    말 = filetools.편집("src/셈.py", "def 빼기(a, b):\n  return a - b", "def 빼기(a, b):\n    return b - a", repo=repo)
    ok("공백만 달라" in 말 and "return b - a" in (repo / "src" / "셈.py").read_text(encoding="utf-8"),
       f"**들여쓰기만 다른 old 는 실제 글에 맞춰 바꾼다 -- 그리고 그렇다고 말한다** ({말})")
    (repo / "src" / "셈.py").write_text(_앞, encoding="utf-8")       # 아래 읽기 검사는 원래 글을 본다

    print("\n== 읽기 ==")
    본 = filetools.읽기("src/셈.py", repo=repo)
    ok("1\tdef 더하기" in 본 and "5\tdef 빼기" in 본, "줄 번호가 붙는다")
    본 = filetools.읽기("src/셈.py", 시작=5, 줄수=1, repo=repo)
    ok("5\tdef 빼기" in 본 and "더 --" in 본, "잘라 읽고 남은 줄 수를 말한다")
    ok("없다" in filetools.읽기("src/없음.py", repo=repo), "없는 파일은 없다고 한다")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 봇 배선 (원문으로 본다) ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
_런셸 = _도구.split("def run_shell", 1)[-1].split("\n@tool", 1)[0]
ok("toolgate.검사(command)" in _런셸, "run_shell 이 toolgate 를 부른다")
ok(_런셸.index("toolgate.검사(command)") < _런셸.index("subprocess.Popen("),
   "**Popen 앞에서** 부른다 -- 돌기 전에 거절해야 게이트다")
ok("def read_file" in _도구 and "def edit_file" in _도구, "두 도구가 정의돼 있다")
ok("read_file, edit_file" in _서버.split("ADMIN_TOOLS = [", 1)[-1].split("]", 1)[0],
   "ADMIN_TOOLS 에 들어 있다")
_프롬프트 = _서버.split("ADMIN_SYSTEM_PROMPT = (", 1)[-1].split("\n)", 1)[0]
ok("edit_file" in _프롬프트 and "read_file" in _프롬프트, "프롬프트가 edit_file 을 시킨다")
ok("toolgate" in _프롬프트, "프롬프트가 도구 게이트를 알린다 -- 우회하지 말라고")
_읽기 = _도구.split("def read_file", 1)[-1].split("\n@tool", 1)[0]
ok("redact_secrets(" in _읽기, "read_file 은 마스킹을 지난다 (G011 의 규율)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("toolgate: 차단/통과 · 경로 게이트 · 정확 편집 · 읽기 · 봇 배선 -- 통과")
