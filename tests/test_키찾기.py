"""제미나이 키를 **이름이 아니라 값의 꼴로** 찾는지 붙든다.

실측 2026-09-11(사용자): 키는 `.env` 에 있었는데 `api_keys()` 가 손으로 적어 둔 이름
아홉 개(`GEMINI_API_KEY`, `..._FALLBACK2..8`) 중 하나가 아니어서 풀이 비었다. 그러자
에이전트가 사람에게 이렇게 답했다:

    주어진 정보가 틀렸다(이용자 측) -- GEMINI_API_KEY 가 존재하지 않습니다
    -> !열쇠 GEMINI_API_KEY=<발급받은 키>

**있는 것을 없다고 하고 그 탓을 사람에게 돌렸다.** 사용자의 말: "gemini api key는 .env에
존재한다. 물론 이름이 'gemini api key'는 아니겠지. 이런 문제들은 어떻게 해결하나."

붙드는 것: (1) 아무 이름으로 들어 있어도 값이 `AIza…` 꼴이면 찾는다, (2) 알려진 이름이
먼저고 그 뒤에 꼴로 찾은 것이 붙는다(우선순위가 안 뒤집힌다), (3) 같은 값을 두 번 안 센다,
(4) 키 아닌 값(비밀번호 따위)은 안 집는다, (5) **못 찾았을 때 값을 안 비추고 이름만
적는다** -- 사람이 고칠 수 있게, (6) 오류문이 그것을 쓴다.

실행: python3 tests/test_키찾기.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from orchestrator import llm_pool as L  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


가짜1 = "AIzaSy" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7"
가짜2 = "AIzaSy" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3"
assert L._키꼴.fullmatch(가짜1) and L._키꼴.fullmatch(가짜2)

d = Path(tempfile.mkdtemp(prefix="test-key-"))
_환경 = dict(os.environ)
_경로 = L._dotenv_paths
try:
    (d / ".env").write_text(
        "# 이름이 GEMINI_API_KEY 가 아니다\n"
        f"MY_GOOGLE_THING={가짜1}\n"
        "SMTP_APP_PASSWORD=abcd efgh ijkl mnop\n"
        "DISCORD_TOKEN=not-a-google-key-at-all\n", encoding="utf-8")
    L._dotenv_paths = lambda: (d / ".env",)
    for k in list(os.environ):
        if "GEMINI" in k or "AIza" in (os.environ.get(k) or ""):
            os.environ.pop(k, None)

    print("== 이름이 무엇이든 값의 꼴로 찾는다 ==")
    찾 = L._키꼴로찾기()
    ok([n for n, _ in 찾] == ["MY_GOOGLE_THING"], f"**아무 이름으로 들어 있어도 찾는다** ({[n for n, _ in 찾]})")
    ok(all(v != "abcd efgh ijkl mnop" for _, v in 찾), "키 아닌 값(비밀번호)은 안 집는다")
    ok(all("not-a-google-key" not in v for _, v in 찾), "키처럼 안 생긴 값은 안 집는다")

    print("\n== 알려진 이름이 먼저다 (우선순위가 안 뒤집힌다) ==")
    os.environ["GEMINI_API_KEY"] = 가짜2
    ks = L.api_keys()
    ok([n for n, _ in ks][:1] == ["GEMINI_API_KEY"], f"알려진 이름이 앞 ({[n for n, _ in ks]})")
    ok("MY_GOOGLE_THING" in [n for n, _ in ks], "꼴로 찾은 것도 뒤에 붙는다 -- 한도가 그만큼 는다")

    print("\n== 같은 값을 두 번 안 센다 ==")
    os.environ["GEMINI_API_KEY"] = 가짜1                  # .env 의 것과 같은 값
    ks = L.api_keys()
    ok(len({v for _, v in ks}) == len(ks), f"값이 겹치면 한 번만 ({[n for n, _ in ks]})")

    print("\n== 못 찾았을 때: 값은 안 비추고 이름만 적는다 ==")
    os.environ.pop("GEMINI_API_KEY", None)
    (d / ".env").write_text("SMTP_APP_PASSWORD=abcd\nDISCORD_TOKEN=xyz\n", encoding="utf-8")
    말 = L.키찾은꼴()
    ok("SMTP_APP_PASSWORD" in 말 and "DISCORD_TOKEN" in 말,
       f"**.env 에 어떤 이름들이 있는지 적는다** -- 사람이 고칠 수 있게 ({말[:60]})")
    ok("abcd" not in 말 and "xyz" not in 말, "**값은 한 자도 안 비친다**")
    ok("값" in 말 and "이름이 아니라" in 말, "이름이 아니라 값을 보라고 말한다")

    print("\n== 찾았을 때는 몇 개를 어느 이름으로 찾았는지 말한다 ==")
    (d / ".env").write_text(f"WHATEVER_NAME={가짜1}\n", encoding="utf-8")
    말 = L.키찾은꼴()
    ok("WHATEVER_NAME" in 말 and 가짜1 not in 말, f"이름만 ({말})")
finally:
    L._dotenv_paths = _경로
    os.environ.clear()
    os.environ.update(_환경)
    shutil.rmtree(d, ignore_errors=True)

print("\n== 배선: 오류문이 이것을 쓴다 ==")
_글 = (뿌리 / "orchestrator" / "llm_pool.py").read_text(encoding="utf-8")
# 첫 번째 "빈 후보 풀" 은 설명글이다 -- 진짜 raise 는 마지막 자리다.
ok("키찾은꼴()" in _글.split("빈 후보 풀")[-1][:400],
   "빈 풀 오류문이 **무엇을 봤는지** 적는다(이름 목록까지)")
ok("GEMINI_API_KEY 를 찾지 못했다" not in _글,
   "**'GEMINI_API_KEY 가 없다' 고 단정하지 않는다** -- 이름은 아무것이나 될 수 있다")
ok("이름은 아무것이나 된다" in _글, "이름이 아니라 값의 꼴이라고 말해 준다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("키찾기: 값의 꼴로 찾기 · 우선순위 · 겹침 · 값 안 비침 · 오류문 -- 통과")
