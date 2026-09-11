"""eval/answers -- 답 회귀. 같은 물음에 어제와 같은 일이 나는가.

에이전트의 답 중 **약속된 부분**은 결정적이다: 고정 명령은 같은 말에 같은 일이 나야
하고(배포판의 정의), 모르는 말은 에이전트로 떨어져야 하고, 주입은 거절돼야 하고,
간추린 기억은 계속 찾혀야 한다. 이 표면은 dispatch/graph 를 고치다 소리 없이 깨진다
-- 화면에서는 '봇이 멍청해졌다' 로만 보인다. 그래서 (물음, 기대) 쌍을 원장
(eval/questions.jsonl)에 두고 매번 다시 묻는다.

모델이 짓는 부분(산문·추론)은 여기서 안 잰다 -- 그 판정은 도메인 심판(lol/score ·
law/bench · verify.대조)의 일이고, 여기서 흉내 내면 두 벌이 생긴다.

기대의 꼴은 닫혀 있다(brain 규율 -- 검사 꼴이 열리면 검사를 검사할 것이 없다):

    고정명령   dispatch 가 받아서 답한다. 담겨야/안담겨야 로 내용을 붙든다
    에이전트로 dispatch 가 None -- 고정 명령이 남의 말을 삼키지 않는다
    색인       graph 색인에서 찾힌다. 출처접두 로 어느 원장인지 붙든다

행 하나: {"물음": "...", "꼴": "고정명령", "채널": "관리|공개",
          "담겨야": [...], "안담겨야": [...], "출처접두": "..."}

쓰기:
    python3 eval/answers.py             # questions.jsonl 전부
    python3 eval/answers.py --줄 '<json 한 줄>'   # 행 하나만 (원장에 넣기 전에 볼 때)
끝값: 0 다 통과 · 1 어긋난 행 있음 · 3 원장을 못 읽었다
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

물음원장 = Path(__file__).resolve().parent / "questions.jsonl"
꼴들 = ("고정명령", "에이전트로", "색인")


def 행검사(행: dict) -> "list[str]":
    """행 하나를 실제로 물어보고 어긋난 것을 돌려준다. 빈 목록이면 통과."""
    import dispatch
    from graph import ask as graph_ask

    꼴 = 행.get("꼴", "")
    물음 = 행.get("물음", "")
    if 꼴 not in 꼴들 or not 물음:
        return [f"성하지 않은 행이다(꼴={꼴!r}) -- 아는 꼴: {꼴들}"]

    if 꼴 == "색인":
        hits = graph_ask.찾기(물음)
        접두 = 행.get("출처접두", "")
        if not hits:
            return [f"색인에서 못 찾는다: {물음!r}"]
        if 접두 and not any(n["출처"].startswith(접두) for _, n in hits):
            return [f"찾긴 했는데 출처가 다르다: {[n['출처'] for _, n in hits[:3]]}"]
        return []

    답 = dispatch.run(물음, None, 행.get("채널", "관리") != "공개")
    if 꼴 == "에이전트로":
        return [] if 답 is None else [f"고정 명령이 남의 말을 삼켰다: {답[:80]!r}"]
    if 답 is None:
        return ["고정 명령이 못 알아듣는다 (None) -- 배선이 끊겼다"]
    어긋 = [f"담겨야 할 말이 없다: {말!r}" for 말 in 행.get("담겨야", []) if 말 not in 답]
    어긋 += [f"담기면 안 되는 말이 있다: {말!r}" for 말 in 행.get("안담겨야", []) if 말 in 답]
    return 어긋


def 전부검사(행들: "list[dict]") -> "tuple[int, list[str]]":
    """(어긋난 행 수, 보고 줄들)."""
    lines, 어긋수 = [], 0
    for i, 행 in enumerate(행들, 1):
        어긋 = 행검사(행)
        표 = "OK  " if not 어긋 else "어긋"
        lines.append(f"  {표} [{행.get('꼴', '?')}] {행.get('물음', '')[:50]!r}")
        if 어긋:
            어긋수 += 1
            lines += [f"        {x}" for x in 어긋]
    return 어긋수, lines


def main() -> int:
    ap = argparse.ArgumentParser(description="같은 물음에 어제와 같은 일이 나는가")
    ap.add_argument("--줄", default="", help="원장 대신 이 JSON 행 하나만")
    args = ap.parse_args()
    if args.줄:
        행들 = [json.loads(args.줄)]
    else:
        if not 물음원장.is_file():
            print(f"물음 원장이 없다: {물음원장}")
            return 3
        행들 = []
        for line in 물음원장.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                행들.append(json.loads(line))
            except ValueError:
                print(f"깨진 줄(그대로 세고 빨간불): {line[:60]!r}")
                행들.append({})
    어긋수, lines = 전부검사(행들)
    print("\n".join(lines))
    print(f"\n{len(행들)}행 중 어긋남 {어긋수}행")
    return 1 if 어긋수 else 0


if __name__ == "__main__":
    raise SystemExit(main())
