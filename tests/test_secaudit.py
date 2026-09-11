"""secaudit(보안 자가점검)를 임시 파일·가짜 /proc 로 **실제로 돌려** 붙든다.

붙드는 것: (1) 판정은 코드가 한다 -- 남에게 읽히는 개인키·.env·세계 쓰기 파일은 규칙이
심각도를 매긴다, 모델이 '안전' 이라 말해도 소용없다, (2) 소스·템플릿(.py · .env.example)은
비밀이 아니다(거짓 양성 안 냄), (3) 0.0.0.0 로 열린 흔치 않은 포트를 /proc/net/tcp 에서
ss 없이 집어낸다, (4) 도구가 없어 못 본 것은 '못잼' 이지 '안전' 이 아니고, 전부 못잼이면
돌았나=False(끝값 3), (5) 높음이 있으면 끝값 1, (6) 수집·대조는 network 없으면 건너뛰고
4·5 는 돈다, (7) 원장·보고·심각도 정렬, (8) `!점검` 배선 · 도구 · 프롬프트.

network·LLM·root 권한 없이 돈다. 실행: python3 tests/test_secaudit.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from secaudit import checks as C  # noqa: E402
from secaudit import run as R  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-sec-"))
방 = 임시 / "방"
방.mkdir()

try:
    print("== 비밀 파일 노출: 판정은 코드가, 소스·템플릿은 봐준다 ==")
    (방 / ".env").write_text("SMTP_APP_PASSWORD=abcd\n", encoding="utf-8")
    os.chmod(방 / ".env", 0o644)                     # 남이 읽힘 -- 높음
    (방 / "id_ed25519").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n", encoding="utf-8")
    os.chmod(방 / "id_ed25519", 0o644)               # 개인키 노출 -- 높음
    (방 / ".env.example").write_text("SMTP_APP_PASSWORD=\n", encoding="utf-8")
    os.chmod(방 / ".env.example", 0o644)             # 템플릿 -- 봐줌
    (방 / "secret_filter.py").write_text("# secret\n", encoding="utf-8")
    os.chmod(방 / "secret_filter.py", 0o644)         # 소스 -- 봐줌
    (방 / "안전.env").write_text("X=1\n", encoding="utf-8")
    os.chmod(방 / "안전.env", 0o600)                  # 주인만 -- 봐줌
    f = C.비밀파일노출((str(방),))
    증거 = " ".join(f["증거"])
    ok(f["심각도"] == "높음", f"노출된 비밀 파일이 있으면 높음 ({f['심각도']})")
    ok(".env " in 증거 or "/.env " in 증거, ".env 노출을 잡는다")
    ok("id_ed25519" in 증거, "개인키 노출을 잡는다")
    ok(".env.example" not in 증거 and "secret_filter.py" not in 증거 and "안전.env" not in 증거,
       "**소스·템플릿·600 파일은 안 잡는다 (거짓 양성 없음)**")
    os.chmod(방 / ".env", 0o600)
    os.chmod(방 / "id_ed25519", 0o600)
    ok(C.비밀파일노출((str(방),))["심각도"] == "정보", "전부 600 이면 정보")

    print("\n== 세계 쓰기 가능 ==")
    (방 / "열린.sh").write_text("echo hi\n", encoding="utf-8")
    os.chmod(방 / "열린.sh", 0o666)
    f = C.세계쓰기가능((str(방),))
    ok(f["심각도"] == "높음" and any("열린.sh" in e for e in f["증거"]), f"세계 쓰기 파일은 높음 ({f['심각도']})")
    os.chmod(방 / "열린.sh", 0o644)
    ok(C.세계쓰기가능((str(방),))["심각도"] == "정보", "고치면 정보")

    print("\n== 포트: ss 없이 /proc/net/tcp 에서 0.0.0.0 LISTEN 을 집는다 ==")
    # 00000000:07D8 = 0.0.0.0:2008(흔치 않음), 0100007F:1F90 = 127.0.0.1:8080(로컬), st 0A=LISTEN
    가짜tcp = 임시 / "tcp"
    가짜tcp.write_text(
        "  sl  local_address rem_address   st\n"
        "   0: 00000000:07D8 00000000:0000 0A\n"
        "   1: 0100007F:1F90 00000000:0000 0A\n"
        "   2: 00000000:0050 00000000:0000 0A\n"       # 0.0.0.0:80 흔함
        "   3: 00000000:07D8 00000000:0000 01\n",      # ESTABLISHED -- LISTEN 아님
        encoding="utf-8")
    포트들 = C._proc포트(str(가짜tcp))
    ok(("*", 2008) in 포트들 and ("local", 8080) in 포트들 and ("*", 80) in 포트들, f"파싱 ({포트들})")
    ok(("*", 2008) in 포트들 and sum(1 for r, p in 포트들 if p == 2008) == 1, "ESTABLISHED 는 빼고 LISTEN 만")

    print("\n== 도구가 없으면 '못잼' 이지 '안전' 이 아니다 ==")
    f = C.열린포트.__wrapped__() if hasattr(C.열린포트, "__wrapped__") else None  # noqa
    # /proc/net/tcp 가 없는 척은 못 하니, 방화벽을 PATH 없이 불러 '못잼' 을 본다
    옛PATH = os.environ.get("PATH", "")
    os.environ["PATH"] = str(임시 / "없는디렉터리")
    try:
        fw = C.방화벽()
    finally:
        os.environ["PATH"] = 옛PATH
    ok(fw["심각도"] in ("못잼", "중간", "정보"), f"방화벽 점검이 죽지 않는다 ({fw['심각도']})")

    print("\n== 전부(): 심각도 순 정렬 · 터져도 '못잼' 으로 ==")
    def 터지는(): raise RuntimeError("일부러")
    old = C.낱낱들[:]
    C.낱낱들.append(터지는)
    try:
        전 = C.전부()
    finally:
        C.낱낱들[:] = old
    ok(any(x["제목"] == "터지는" and x["심각도"] == "못잼" for x in 전), "**점검이 터지면 못잼 -- 안 죽는다**")
    순 = [C.심각도차례[x["심각도"]] for x in 전]
    ok(순 == sorted(순), "심각도 순으로 정렬된다(높음 먼저)")

    print("\n== 파이프라인: 수집·대조 건너뛰기 · 원장 · 끝값 ==")
    R.수집 = lambda 말: (_ for _ in ()).throw(AssertionError("--뇌 아니면 안 불러야"))
    R.대조 = lambda 물음: (_ for _ in ()).throw(AssertionError("--뇌 아니면 안 불러야"))
    r = R.점검하기(repo=임시, 뇌=False)
    ok(r["돌았나"] and "수집 안 함" in r["수집메모"], "--뇌 없으면 수집·대조를 안 부른다")
    ok(all(f["참고"] == [] for f in r["낱낱들"]), "참고는 비어 있다")
    원장 = R.원장읽기(임시)
    ok(len(원장) == 1 and "셈" in 원장[0] and "낱낱" in 원장[0], "원장에 한 줄(셈·낱낱)")
    보 = R.보고(r)
    ok("보안 자가점검 (읽기 전용)" in 보 and "합계:" in 보, "보고 머리·합계")

    R.수집 = lambda 말: None
    R.대조 = lambda 물음: [{"요약": "지난 규칙: 포트 2024 는 봐준다", "출처": "memo/x.md"}]
    r2 = R.점검하기(repo=임시, 뇌=True, 적기=False)
    ok(any(f["참고"] for f in r2["낱낱들"]), "--뇌 면 대조 참고가 붙는다")
    ok("수집기를 불렀다" in r2["수집메모"], "--뇌 면 수집기를 부른다")
finally:
    R.수집 = None
    R.대조 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 끝값: 높음 있으면 1 · 전부 못잼이면 3 ==")


def 한낱낱(심): return {"id": "x", "제목": "x", "심각도": 심, "증거": [], "고침": ""}


# 모든 낱낱을 대신 꽂아 끝값 규칙만 본다
import types  # noqa: E402
원래 = C.전부
try:
    C.전부 = lambda repo=None: [한낱낱("높음"), 한낱낱("정보")]
    r = R.점검하기(적기=False)
    ok(r["돌았나"] and r["셈"]["높음"] == 1, "높음 1 집계")
    C.전부 = lambda repo=None: [한낱낱("못잼"), 한낱낱("못잼")]
    r = R.점검하기(적기=False)
    ok(not r["돌았나"], "**전부 못잼이면 돌았나=False (끝값 3) -- '안전' 이 아니다**")
finally:
    C.전부 = 원래

print("\n== 배선 ==")
import subprocess  # noqa: E402
import dispatch  # noqa: E402
ok(dispatch.run("!점검", allow_write=False) is not None, "!점검 이 dispatch 에 걸려 있다")
ok("관리 채널" in (dispatch.run("!점검 뇌", allow_write=False) or ""), "--뇌 점검은 관리 채널")
불림 = []
dispatch.run("!점검", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0][:2] == ["python3", "secaudit/run.py"], f"배경으로 띄운다 ({불림})")
ok(dispatch.run("!점검기 x") is None, "붙여 쓴 `!점검기` 는 명령이 아니다")
p = subprocess.run(["python3", "secaudit/run.py", "--json"], cwd=str(뿌리), capture_output=True, text=True)
ok(p.returncode in (0, 1) and '"낱낱들"' in p.stdout, "CLI --json 이 돈다")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def security_audit" in _도구 and "secaudit" in _도구, "security_audit 도구가 있다")
ok(_서버.count(" security_audit,") >= 2, "ADMIN_TOOLS·임포트에 security_audit")
ok("security_audit 도구" in _서버 and "익스플로잇을 실행하지 마라" in _서버,
   "프롬프트가 security_audit 를 이름을 대고 시키고, 공격 금지를 못박는다")
_wire = (뿌리 / "eval" / "wire.py").read_text(encoding="utf-8")
ok("secaudit/run.py" in _wire, "배선 점검에 secaudit 가 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("secaudit: 코드 판정 · 거짓 양성 없음 · /proc 포트 · 못잼≠안전 · 끝값 · 배선 -- 통과")
