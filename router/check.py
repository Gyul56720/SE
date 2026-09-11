"""router/check -- 비용 원장을 심판한다. eval 의 '경로' 갈래.

무엇을 재나: **비싼 길이 죽은 채 아무도 모르는 상태**. 디렉터는 claude 로 가야 하는데
강등이 이어지면 전부 gemini(물러섬)로 나간다 -- 답은 계속 나오므로 화면에서는 아무
일도 없어 보인다. 그것이 CLAUDE.md 의 분업이 소리 없이 무너지는 꼴이다.

판정 (끝값 관례 그대로):
    끝값 3  재료 부족 -- 원장이 없거나 디렉터 호출이 아직 적다(못돌림, 초록 아님)
    끝값 1  최근 디렉터 호출의 태반이 물러섬이다 -- claude 경로가 사실상 죽어 있다.
            또는 채택 기록이 충분한데 비싼 길의 채택률이 싼 길보다 **낮다** --
            비싼 모델이 값을 못 하고 있다(역할표를 내릴 신호).
    끝값 0  성하다

쓰기: python3 router/check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from router import call as R  # noqa: E402

최근몇 = 50
물러섬_문턱 = 0.8
채택_최소표본 = 20


def 심판(repo=None) -> "tuple[int, list[str]]":
    기록들 = [r for r in R.원장읽기(repo) if r.get("역할")]
    lines: list = []
    디렉터 = [r for r in 기록들 if r["역할"] == "디렉터"][-최근몇:]
    if len(디렉터) < 5:
        return 3, [f"재료 부족 -- 디렉터 호출이 {len(디렉터)}건뿐이다 (5건은 있어야 잰다)"]

    물러섬 = sum(1 for r in 디렉터 if "물러섬" in r.get("바탕", ""))
    비율 = 물러섬 / len(디렉터)
    lines.append(f"디렉터 최근 {len(디렉터)}건 중 물러섬 {물러섬}건 ({비율:.0%})")
    빨강 = False
    if 비율 > 물러섬_문턱:
        빨강 = True
        lines.append(f"**빨강: claude 경로가 사실상 죽어 있다** (문턱 {물러섬_문턱:.0%}) -- "
                     "구독 한도·로그인·탐침 간격을 보라. 답은 나오고 있어서 화면에는 안 보인다")

    s = R.요약(repo)
    비싼 = s.get("디렉터", {})
    싼들 = [v for k, v in s.items() if k in ("배우", "화자", "추출기")]
    if 비싼.get("채택분모", 0) >= 채택_최소표본 and any(
            v.get("채택분모", 0) >= 채택_최소표본 for v in 싼들):
        비싼율 = 비싼["채택분자"] / 비싼["채택분모"]
        싼율 = max(v["채택분자"] / v["채택분모"] for v in 싼들 if v["채택분모"])
        lines.append(f"채택률 -- 디렉터 {비싼율:.0%} vs 싼 역할 최고 {싼율:.0%}")
        if 비싼율 < 싼율:
            빨강 = True
            lines.append("**빨강: 비싼 모델이 값을 못 한다** -- 역할표에서 디렉터를 "
                         "내리는 것을 검토하라 (CLAUDE.md 분업의 근거가 뒤집혔다)")
    else:
        lines.append("(채택 기록이 아직 적어 채택률 비교는 못 잰다 -- 채택표시() 를 이어 적어라)")
    return (1 if 빨강 else 0), lines


def main() -> int:
    끝값, lines = 심판()
    print("\n".join(f"  {x}" for x in lines))
    return 끝값


if __name__ == "__main__":
    raise SystemExit(main())
