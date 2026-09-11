"""delegate(위임·병렬)를 임시 저장소에서 가짜 탐색기로 **끝까지 돌려** 붙든다.

붙드는 것: (1) 쪼개기가 비밀·이진·산출물을 안 읽고 묶음글자 안에서 채운다, (2) 묶음이
**동시에** 던져진다(스레드가 겹친다), (3) 대조가 실재하는 인용만 채택하고 지어낸 인용·
남의 파일·빈 인용은 퇴짜로 센다 -- 공백만 다른 것은 봐준다, (4) 깨진 JSON·호출 실패에도
죽지 않는다, (5) 채택/불채택이 router 원장에 채택표시로 남는다, (6) !위임 배선(공개 채널
거절 · `::` 꼴 · 글롭 검사).

LLM·네트워크 없이 돈다. 실행: python3 tests/test_delegate.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from delegate import run as D  # noqa: E402
from router import call as R  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-delegate-"))
repo = 임시 / "repo"
(repo / "src").mkdir(parents=True)
(repo / "sandbox" / "out").mkdir(parents=True)
(repo / ".env").write_text("GEMINI_API_KEY=secret\n", encoding="utf-8")
(repo / "src" / "a.py").write_text("def 해시(path):\n    return sha256(path)[:12]\n", encoding="utf-8")
(repo / "src" / "b.py").write_text("x = 1\n" * 3000, encoding="utf-8")          # 큰 파일 -> 잘림
(repo / "src" / "c.py").write_text("def 대조(요약, 원문):\n    return 요약 in 원문\n", encoding="utf-8")
(repo / "src" / "d.png").write_bytes(b"\x89PNG")
(repo / "sandbox" / "out" / "x.txt").write_text("산출물\n", encoding="utf-8")
(repo / "src" / "비밀.env").write_text("TOKEN=1\n", encoding="utf-8")

try:
    print("== 쪼개기 ==")
    묶음들 = D.쪼개기(["src/*", "sandbox/out/*", ".env"], repo=repo, 상한=100)
    파일들 = [str(p.relative_to(repo)) for b in 묶음들 for p in b]
    ok("src/a.py" in 파일들 and "src/c.py" in 파일들, f"읽을 파일이 들어온다 ({파일들})")
    ok(".env" not in 파일들 and "sandbox/out/x.txt" not in 파일들 and "src/d.png" not in 파일들,
       "**비밀·산출물·이진은 안 읽는다**")
    ok("src/비밀.env" not in 파일들, "**`무엇.env` 꼴도 안 읽는다** (첫 판이 읽었다)")
    ok(len(묶음들) >= 3, f"상한이 작으면 묶음이 갈린다 ({len(묶음들)}묶음)")
    ok(len(D.쪼개기(["src/*"], repo=repo)) == 1, "기본 상한(24000자)이면 이 정도는 한 묶음이다")

    print("\n== 동시에 던진다 ==")
    동시 = {"지금": 0, "최대": 0}
    lock = threading.Lock()

    def 느린탐색기(역할, prompt):
        with lock:
            동시["지금"] += 1
            동시["최대"] = max(동시["최대"], 동시["지금"])
        time.sleep(0.15)
        with lock:
            동시["지금"] -= 1
        return {"답": "[]", "id": None}

    D.부르기 = 느린탐색기
    r = D.위임("아무거나", ["src/*"], repo=repo, 묶음상한=100)
    ok(동시["최대"] >= 2, f"**묶음이 겹쳐 돈다** (동시 최대 {동시['최대']})")
    ok(r["호출"] == r["묶음"] and r["호출"] >= 2, f"묶음마다 한 호출 ({r['호출']})")

    print("\n== 대조: 실재하는 인용만 채택 ==")
    답들 = [
        {"파일": "src/a.py", "인용": "return sha256(path)[:12]", "왜": "여기서 해시"},
        {"파일": "src/a.py", "인용": "return sha256(path)[:32]", "왜": "지어냄"},
        {"파일": "src/c.py", "인용": "def 대조(요약,   원문):", "왜": "공백만 다름"},
        {"파일": "src/없는.py", "인용": "x", "왜": "남의 파일"},
        {"파일": "src/a.py", "인용": "", "왜": "빈 인용"},
    ]

    def 지어내는탐색기(역할, prompt):
        return {"답": "여기 결과입니다:\n" + json.dumps(답들, ensure_ascii=False), "id": "호출1"}

    D.부르기 = 지어내는탐색기
    r = D.위임("해시는 어디서", ["src/a.py", "src/c.py"], 병렬=1, repo=repo)
    채택파일 = {(g["파일"], g["줄"]) for g in r["채택"]}
    ok(("src/a.py", 2) in 채택파일, f"실재하는 인용은 줄 번호 붙여 채택 ({채택파일})")
    ok(("src/c.py", 1) in 채택파일, "공백만 다른 인용은 봐준다")
    ok(len(r["채택"]) == 2 and len(r["퇴짜"]) == 3,
       f"**지어낸 것·남의 파일·빈 인용은 퇴짜** (채택 {len(r['채택'])} · 퇴짜 {len(r['퇴짜'])})")
    ok(all(len(g["해시"]) == 12 for g in r["채택"]), "채택에 해시가 붙는다")
    ok(any("원문에 없다" in x for x in r["퇴짜"]), "퇴짜 사유가 적힌다")
    보 = D.보고(r, "해시는 어디서")
    ok("src/a.py:2" in 보 and "지어낸" in 보, "보고에 파일:줄과 퇴짜 설명이 있다")

    print("\n== 깨진 답·죽는 호출에도 안 죽는다 ==")
    D.부르기 = lambda 역할, p: {"답": "JSON 아님 {{{", "id": None}
    r = D.위임("x", ["src/a.py"], repo=repo)
    ok(r["돌았나"] and not r["채택"], "깨진 JSON 은 빈 채택")

    def 죽는탐색기(역할, p):
        raise RuntimeError("쿼터 소진")

    D.부르기 = 죽는탐색기
    r = D.위임("x", ["src/a.py"], repo=repo)
    ok(r["돌았나"] and any("호출 실패" in x for x in r["퇴짜"]), f"호출 실패는 퇴짜로 남는다 ({r['퇴짜']})")
    r = D.위임("x", ["없는/*"], repo=repo)
    ok(not r["돌았나"], "읽을 파일이 없으면 돌았나=False")

    print("\n== 채택 여부가 router 원장에 남는다 ==")
    D.부르기 = None                                   # 진짜 경로: router.부르기 -> 가짜 지미니
    R.지미니호출 = lambda p, prefer, pool_id: (json.dumps(답들[:1], ensure_ascii=False), "key-x:gemini-fake")
    r = D.위임("해시는 어디서", ["src/a.py"], repo=repo)
    s = R.요약(repo=repo)
    ok(s.get("탐색기", {}).get("호출") == 1 and s["탐색기"]["채택분자"] == 1,
       f"탐색기 호출 1 · 채택 1 이 원장에 있다 ({s.get('탐색기')})")
    R.지미니호출 = lambda p, prefer, pool_id: ("[]", "key-x:gemini-fake")
    D.위임("x", ["src/a.py"], repo=repo)
    s = R.요약(repo=repo)
    ok(s["탐색기"]["채택분모"] == 2 and s["탐색기"]["채택분자"] == 1, "빈손은 불채택으로 남는다")
finally:
    D.부르기 = None
    R.지미니호출 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== !위임 배선 ==")
import dispatch  # noqa: E402
ok(dispatch.run("!위임 graph/*.py :: 해시", allow_write=False) is not None
   and "관리 채널" in dispatch.run("!위임 graph/*.py :: 해시", allow_write=False), "공개 채널은 거절")
불림 = []
답 = dispatch.run("!위임 graph/*.py router/*.py :: 해시를 어디서",
                 runner=lambda 물음, 범위들: (불림.append((물음, 범위들)) or
                                          {"채택": [], "퇴짜": [], "묶음": 0, "파일": 0, "호출": 0, "걸린초": 0.0, "돌았나": True}),
                 allow_write=True)
ok(불림 and 불림[0] == ("해시를 어디서", ["graph/*.py", "router/*.py"]), f"글롭과 물음이 갈라져 넘어간다 ({불림})")
ok("::" in (dispatch.run("!위임 graph/*.py 해시", allow_write=True) or ""), ":: 없으면 꼴을 알려준다")
ok("거절" in (dispatch.run("!위임 ../x :: 해시", allow_write=True) or ""), "저장소 밖 글롭은 거절")
ok(dispatch.run("!위임장 써줘") is None, "붙여 쓴 `!위임장` 은 명령이 아니다")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def delegate" in _도구 and "delegate, search_memory" in _서버, "delegate 도구가 정의되고 ADMIN_TOOLS 에 있다")
ok("탐색기" in R.역할들 and R.역할들["탐색기"]["바탕"] == "gemini", "router 역할표에 탐색기가 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("delegate: 쪼개기 · 동시 · 대조 채택/퇴짜 · 안 죽음 · 원장 채택표시 · 배선 -- 통과")
