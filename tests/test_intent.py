"""intent(목표 원장)를 임시 저장소에서 **끝까지 돌려** 붙든다.

붙드는 것: (1) **승인 없는 목표는 집히지 않는다** -- 이 모듈의 존재 이유,
(2) 끝은 말이 아니라 판정명령의 exit 0 이 정한다(실패하면 거절, 근거가 남는다),
(3) 판정명령 없는 목표만 사람 선언으로 끝난다, (4) 사건은 append-only 로 쌓인다,
(5) 공개 채널은 읽기만 된다(!목표 배선), (6) 승인된 목표가 digest(읽힐 텍스트)에
얹히고 승인 없는 제안은 안 올라온다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_intent.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from intent import store as S  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-intent-"))
repo = 임시 / "repo"
repo.mkdir()

try:
    print("== 승인 없는 목표는 집히지 않는다 ==")
    기록id = S.제안("증거 파일을 만든다", 판정명령="test -f 증거.txt", 누가="agent", repo=repo)
    ok(S.상태표(repo)[기록id]["상태"] == "제안됨", "제안이 원장에 남는다")
    ok(S.집기(repo) == [], "**제안만으로는 집기에 안 나온다** -- 이것이 존재 이유다")
    ok("승인" in S.승인(기록id, 누가="사람", repo=repo), "승인이 적힌다")
    골들 = S.집기(repo)
    ok(len(골들) == 1 and 골들[0]["id"] == 기록id, "승인 뒤에야 집힌다")
    ok(골들[0].get("승인한이") == "사람", "누가 승인했는지 남는다")

    print("\n== 끝은 판정명령이 정한다 ==")
    됐다, 말 = S.끝(기록id, repo=repo)
    ok(not 됐다 and "안 끝났다" in 말, f"**증거가 없으면 끝을 거절한다** ({말.splitlines()[0][:50]})")
    ok(S.상태표(repo)[기록id]["상태"] == "승인됨", "거절됐으니 상태가 그대로다")
    (repo / "증거.txt").write_text("됐다\n", encoding="utf-8")
    됐다, 말 = S.끝(기록id, repo=repo)
    ok(됐다 and "exit 0" in 말, f"증거가 생기면 끝난다 ({말[:60]})")
    ok(S.집기(repo) == [], "끝난 목표는 집기에서 빠진다")
    됐다, 말 = S.끝(기록id, repo=repo)
    ok(not 됐다, "끝난 것을 또 끝낼 수 없다")

    print("\n== 판정명령 없는 목표는 사람 선언으로만 ==")
    id2 = S.제안("문체를 더 부드럽게", 누가="agent", repo=repo)   # 코드가 못 재는 목표
    S.승인(id2, repo=repo)
    됐다, 말 = S.끝(id2, 누가="사람", repo=repo)
    ok(됐다 and "선언" in 말, f"판정명령이 없으면 사람 선언으로 끝난다 ({말[:60]})")

    print("\n== 버림과 append-only ==")
    id3 = S.제안("버릴 목표", repo=repo)
    ok("버림" in S.버림(id3, 왜="중복", repo=repo), "제안됨도 버릴 수 있다")
    ok(S.상태표(repo)[id3]["상태"] == "버림", "버림이 접힌다")
    ok(len(S.사건들(repo)) == 8, f"사건 8개가 전부 남아 있다 ({len(S.사건들(repo))}) -- 지운 것이 없다")

    print("\n== 승인된 목표가 읽힐 텍스트(digest)에 얹힌다 ==")
    id4 = S.제안("촉매 원장을 넓힌다", repo=repo)
    S.승인(id4, repo=repo)
    id5 = S.제안("승인 안 된 제안", repo=repo)
    from graph import digest
    글 = digest.짓기(repo=repo)
    ok("승인된 목표" in 글 and "촉매 원장을 넓힌다" in 글, "승인된 목표가 digest 에 올라온다")
    ok("승인 안 된 제안" not in 글, "**승인 없는 제안은 digest 에도 안 올라온다**")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print("\n== !목표 배선 ==")
import dispatch  # noqa: E402
답 = dispatch.run("!목표 제안 아무거나", allow_write=False)
ok(답 is not None and "관리 채널" in 답, "**공개 채널에서는 제안·승인이 안 된다**")
답 = dispatch.run("!목표 승인 x", allow_write=False)
ok(답 is not None and "관리 채널" in 답, "공개 채널 승인도 막힌다")
답 = dispatch.run("!목표 다음", allow_write=False)
ok(답 is not None, "공개 채널도 읽기는 된다")
ok(dispatch.run("!목표수립을 도와줘") is None, "붙여 쓴 `!목표수립` 은 명령이 아니다")
답 = dispatch.run("!진화")
ok(답 is not None and "G020" in 답, "!진화 현황에 상한(G020)이 보인다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("intent: 승인 경계 · 명령 판정 끝 · 사람 선언 · append-only · digest 융합 · 배선 -- 통과")
