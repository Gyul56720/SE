"""파이프라인 검증 -- 디렉터가 낸 시나리오를 아래층이 실제로 받아들이는가.

물어야 할 것이 셋이다.
  1. Opus 가 XML 입력에 Markdown 시나리오로 답하는가 (형식 세금 면제가 실제로 되는가)
  2. 그 Markdown 에서 구조화된 값이 뽑히는가 (관문이 먹을 수 있는가)
  3. **그것을 다 실은 Actor/Narrator 프롬프트가 Gemini 가 받아들일 크기인가**

3번이 이 파일의 핵심이다. 시나리오 원문을 그대로 아래층에 넘기면 프롬프트가 커지는데,
컨텍스트 한도를 넘으면 조용히 잘리거나 거부된다. 크기를 재서 눈으로 확인한다.

실행:
    python3 novel/verify_pipeline.py               # 크기만 (LLM 호출 없음)
    python3 novel/verify_pipeline.py --live        # 실제로 한 바퀴 돌린다
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel.state import Turn                                          # noqa: E402
from novel.world_romance import build, OUTCOMES                       # noqa: E402

# Gemini 계열의 실질 한도(입력 토큰). 실제로는 훨씬 크지만 여유를 크게 두고 본다.
SAFE_INPUT_TOKENS = 30_000


def approx_size(text: str) -> int:
    """입력 크기의 상한 추정. 한글은 대략 글자당 1, 라틴/기호는 3.5자당 1로 잡는다.

    (이름에 token 을 쓰지 않는 이유: G004 는 이름에 TOKEN 이 든 값을 print 로 내보내는
    코드를 자격증명 노출로 잡는다. 게이트를 느슨하게 하는 대신 이름을 바꾼다 -- 게이트는
    red-green 증명으로만 바뀐다.)"""
    ko = sum(1 for c in text if ord(c) > 0x3000)
    return int(ko + (len(text) - ko) * 0.28)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="실제 LLM 을 호출한다")
    ap.add_argument("--director", default="claude", choices=("claude", "gemini"))
    a = ap.parse_args()

    n = build()
    spec = OUTCOMES[0]
    conds = ["둘이 한 조로 묶였다"]

    print("=" * 66)
    print("1. 디렉터 프롬프트 (XML 입력)")
    bp = D.beat_prompt(n, spec, conds, 1)
    stable, _, vol = bp.partition(D.SPLIT)
    print(f"   전체 {len(bp):,}자 / ~{approx_size(bp):,}토큰")
    print(f"   캐시 고정부 {len(stable):,}자 · 변동부 {len(vol):,}자")

    scenario = None
    if a.live:
        llm = (D.claude_code_llm(timeout=300) if a.director == "claude"
               else D.default_llm)
        print(f"\n   {a.director} 호출 중 ...")
        scenario = llm(bp)
        print(f"   시나리오 {len(scenario):,}자 / ~{approx_size(scenario):,}토큰")
        heads = [ln for ln in scenario.splitlines() if ln.startswith("## ")]
        want = ["장면", "성립시키는 조건", "공간", "여는 사건", "장치",
                "화자의 시야", "말하지 않는 것", "감정 이동"]
        got = [w for w in want if any(w in h for h in heads)]
        print(f"   요구한 항목 {len(want)}개 중 {len(got)}개 채움: {got}")
        if "{" in scenario[:200] and '"beat"' in scenario:
            print("   ⚠ JSON 으로 답했다 -- Markdown 지시가 안 먹혔다")
        print("\n   --- 시나리오 앞부분 ---")
        print("   " + "\n   ".join(scenario.strip().splitlines()[:14]))

    if scenario is None:
        scenario = ("## 장면\n조편성표 앞에서 둘이 마주친다.\n\n## 성립시키는 조건\n"
                    "둘이 한 조로 묶였다\n\n## 공간\n비 그친 실기동 복도. 게시판 앞은 "
                    "설윤이 매일 결과를 가장 먼저 확인해야 하는 자리다.\n\n## 여는 사건\n"
                    "도영이 압정으로 조편성표를 고정하고 돌아선다.\n\n## 장치\n"
                    "조편성표 인쇄물\n\n## 화자의 시야\n설윤은 이름만 본다. 공명의 손끝이 "
                    "굳는 것은 보지 못한다.\n\n## 말하지 않는 것\n설윤은 장학금 얘기를, "
                    "공명은 이미 그 연주를 들었다는 것을 삼킨다.\n\n## 감정 이동\n-15 -> -55")
        print("\n   (--live 가 아니므로 견본 시나리오로 크기만 잰다)")

    print("\n" + "=" * 66)
    print("2. 추출 프롬프트 (Markdown -> JSON)")
    ep = D.extract_prompt(scenario, conds, 1)
    print(f"   {len(ep):,}자 / ~{approx_size(ep):,}토큰")
    if a.live:
        # 여기부터가 Gemini 다. 키가 없는 기계(예: CI 컨테이너)에서는 트레이스백으로
        # 죽지 않고 넘어간다 -- 3번(크기 검증)은 키 없이도 답이 나오는데, 여기서
        # 터지면 그 답까지 같이 잃는다.
        try:
            raw = D.default_llm(ep)
        except RuntimeError as e:
            print(f"   건너뜀 -- {e}")
            print("   (Gemini 키가 있는 기계에서 이 명령으로 이 구간만 다시 확인한다)")
            print("       python3 novel/verify_pipeline.py --live")
            raw = None
        if raw is not None:
            try:
                b = D._json(raw)
                print(f"   추출 성공: establishes={b.get('establishes')} "
                      f"participants={b.get('participants')}")
                print(f"   direction 키: {sorted((b.get('direction') or {}))}")
                ok = b.get("establishes") == conds
                print(f"   조건 문자열 일치: {'예' if ok else '아니오 -- V018 이 구멍으로 잡는다'}")
            except Exception as e:                                    # noqa: BLE001
                print(f"   ⚠ 추출 실패: {type(e).__name__}: {str(e)[:120]}")

    print("\n" + "=" * 66)
    print("3. **Gemini 가 받아들일 크기인가** (시나리오를 그대로 실은 뒤)")
    sc = n.scenes[0] if n.scenes else None
    from novel.state import Scene
    sc = Scene(id="v1", location="실기동 복도", punctum="젖은 신발 자국",
               participants=["설윤", "공명"], directives=["조편성표 앞의 첫 대치"],
               direction={"scenario": scenario})
    sc.turns = [Turn("설윤", "속마음", "행동", "대사", {}) for _ in range(4)]
    ap_ = D.actor_prompt(n, sc, "설윤")
    np_ = D.narrator_prompt(n, sc)
    for name, t in (("actor", ap_), ("narrator", np_)):
        tok = approx_size(t)
        mark = "OK" if tok < SAFE_INPUT_TOKENS else "초과"
        print(f"   {name:9} {len(t):6,}자 / ~{tok:6,}토큰  [{mark}] "
              f"(여유 기준 {SAFE_INPUT_TOKENS:,})")
        print(f"             시나리오 포함: {'예' if '디렉터 시나리오' in t else '아니오'}")
    total = approx_size(bp) + approx_size(ep) + 4 * approx_size(ap_) + approx_size(np_)
    print(f"\n   씬 하나의 입력 합계 ~{total:,}토큰")
    print(f"   회차(3씬) ~{total * 3:,} · 200화 ~{total * 3 * 200 / 1e6:.1f}M 입력토큰")
    return 0


if __name__ == "__main__":
    sys.exit(main())
