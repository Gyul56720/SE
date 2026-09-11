"""router(역할표 · 강등 · 비용 원장 · 심판)를 가짜 호출기로 **끝까지 돌려** 붙든다.

붙드는 것: (1) 역할표는 닫혀 있고 판정기는 모델을 거절한다, (2) 디렉터가 3연속
실패하면 gemini 로 내려가고 원장에 '물러섬' 이 남는다, (3) 탐침이 성공하면 복귀한다,
(4) 호출·채택이 원장에 쌓여 요약이 맞는 수를 낸다, (5) 심판이 재료 부족(3)과
물러섬 태반(1)과 성함(0)을 가른다, (6) !경로 배선.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_router.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from router import call as R  # noqa: E402
from router import check as C  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-router-"))

print("== 역할표는 닫혀 있다 ==")
try:
    R.부르기("시인", "x", repo=임시)
    ok(False, "모르는 역할이 안 막혔다")
except ValueError as e:
    ok("모르는 역할" in str(e), f"모르는 역할은 거절 ({str(e)[:40]})")
try:
    R.부르기("판정기", "이 답이 맞나?", repo=임시)
    ok(False, "판정기가 모델을 불렀다")
except ValueError as e:
    ok("코드가 한다" in str(e), "**판정기는 모델을 거절하고 코드 심판을 가리킨다**")

print("\n== 디렉터: 3연속 실패면 물러서고, 원장에 남는다 ==")
클로드상태 = {"모드": "죽음"}


def 가짜클로드(prompt):
    if 클로드상태["모드"] == "죽음":
        raise RuntimeError("구독 한도")
    return "클로드의 답"


def 가짜지미니(prompt, prefer, pool_id):
    return f"지미니의 답(prefer={prefer})", "key-x:gemini-fake"


R.클로드호출 = 가짜클로드
R.지미니호출 = 가짜지미니
try:
    for i in range(2):
        try:
            R.부르기("디렉터", "주제", repo=임시)
            ok(False, f"{i + 1}번째 실패가 예외로 안 올라왔다")
        except RuntimeError:
            pass
    ok(True, "강등 전 실패는 그대로 올라온다 (조용히 안 삼킨다)")
    r = R.부르기("디렉터", "주제", repo=임시)   # 3번째 -- 강등되고 gemini 로
    ok(r["바탕"] == "gemini(물러섬)" and "지미니" in r["답"],
       f"**3연속 실패에 gemini 로 물러선다** ({r['바탕']})")
    r = R.부르기("디렉터", "주제", repo=임시)
    ok(r["바탕"] == "gemini(물러섬)", "강등 중에는 계속 물러선 길로 간다")

    print("\n== 탐침이 성공하면 복귀한다 ==")
    클로드상태["모드"] = "살아남"
    R._강등기.재시도초 = 0.0                      # 검사에서는 기다리지 않는다
    r = R.부르기("디렉터", "주제", repo=임시)
    ok(r["바탕"] == "claude" and r["답"] == "클로드의 답",
       f"**탐침 성공 -- claude 로 복귀** ({r['바탕']})")

    print("\n== 다른 역할들 ==")
    r = R.부르기("추출기", "쪽", repo=임시)
    ok("prefer=gemma" in r["답"], f"추출기는 gemma 를 먼저 찾는다 ({r['답']})")
    r배우 = R.부르기("배우", "장면", repo=임시)
    ok(r배우["바탕"] == "gemini", "배우는 gemini 풀로")

    print("\n== 비용 원장과 요약 ==")
    R.채택표시(r배우["id"], True, repo=임시)
    R.채택표시(r["id"], False, repo=임시)
    s = R.요약(repo=임시)
    ok(s["디렉터"]["호출"] == 5 and s["디렉터"]["성공"] == 3,
       f"디렉터: 호출 5(실패 2 포함) · 성공 3 ({s['디렉터']})")
    ok("gemini(물러섬)" in s["디렉터"]["바탕"] and "claude" in s["디렉터"]["바탕"],
       "바탕 분포에 물러섬과 claude 가 갈라져 남는다")
    ok(s["배우"]["채택분자"] == 1 and s["추출기"]["채택분자"] == 0,
       "채택표시가 역할별로 이어진다")

    print("\n== 심판: 재료 부족 / 물러섬 태반 / 성함 ==")
    빈곳 = 임시 / "빈저장소"
    끝값, lines = C.심판(repo=빈곳)
    ok(끝값 == 3, f"원장이 없으면 재료 부족(3) -- 초록 행세 금지 ({lines})")
    많이 = 임시 / "많이"
    for i in range(20):
        R._적기(많이, {"때": "t", "id": f"i{i}", "역할": "디렉터",
                     "바탕": "gemini(물러섬)", "라벨": "x", "걸린초": 1,
                     "성공": True, "프롬프트글자": 1, "답글자": 1})
    끝값, lines = C.심판(repo=많이)
    ok(끝값 == 1 and any("죽어 있다" in x for x in lines),
       f"**물러섬 태반이면 빨강** ({끝값})")
    성한 = 임시 / "성한"
    for i in range(20):
        R._적기(성한, {"때": "t", "id": f"i{i}", "역할": "디렉터", "바탕": "claude",
                     "라벨": "claude-cli", "걸린초": 1, "성공": True,
                     "프롬프트글자": 1, "답글자": 1})
    끝값, lines = C.심판(repo=성한)
    ok(끝값 == 0, f"claude 로 잘 가고 있으면 성함(0) ({끝값})")

    print("\n== !경로 배선 ==")
    import dispatch
    답 = dispatch.run("!경로")
    ok(답 is not None and "판정기" in 답 and "코드" in 답,
       "역할표가 나온다 -- 판정기=코드까지")
    ok(dispatch.run("!경로당 어디야") is None, "붙여 쓴 `!경로당` 은 명령이 아니다")
    답 = dispatch.run("!경로 심판")
    ok(답 is not None and ("재료 부족" in 답 or "성하다" in 답 or "빨강" in 답),
       f"심판이 나온다 ({(답 or '')[:30]!r})")
finally:
    R.클로드호출 = None
    R.지미니호출 = None
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("router: 닫힌 표 · 판정기 거절 · 강등/복귀 · 비용 원장 · 심판 · 배선 -- 통과")
