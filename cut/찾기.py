"""후보 찾기 -- **모델 없이, 선언된 유한 족을 훑는다.**

여기 있는 것은 symbolic regression 이 아니다. 미리 적어 둔 부등식 **족(family)** 을
열거하고 각각을 `채택판정` 에 넣는다. 까닭 셋:

  1. 족을 손으로 적으면 **그 족에 대한 유효성 증명을 사람이 쓸 수 있다.** 회귀가 뱉은
     식은 그 인스턴스에서만 성립할 수 있고, family 로 올리려면 어차피 증명이 필요하다.
  2. 모델이 없어도 돈다. 모델이 약하면 탐색도 약해지는 구조를 피한다.
  3. 아무것도 못 찾으면 그것도 **결과다** -- "이 족에서는 반례가 없다"(포화). 못 찾은
     것을 "없다" 로 읽지 않게, 훑은 수를 같이 남긴다.

## 지금 있는 족: 노드 덮개 (node cover)

바탕 노드 묶음 `S` 와 가상 노드 묶음 `T` 에 대해

    sum_{v in T} cpu(v)  >  sum_{u in S} cap(u)     (덮개 조건)
    ==>  sum_{v in T} sum_{u in S} x[v,u]  <=  |T| - 1

**증명(모든 인스턴스).** T 를 전부 S 안에 놓으면 S 가 쓰는 CPU 가 sum_{v in T} cpu(v) 이고
이것이 S 의 용량 합을 넘는다. CPU 제약에 어긋나므로 가능해가 아니다. 따라서 T 가운데
S 에 놓이는 것은 많아야 |T|-1 개다. 인스턴스 크기·구조와 무관하다. ∎

**|S| >= |T| 일 때만 뜻이 있다.** |S| < |T| 면 일대일 제약이 이미 <= |S| <= |T|-1 을 준다.
그래서 열거에서 그 경우를 뺀다 -- 안 빼면 전부 `안자름` 이 나와 훑은 수만 늘어난다.
"""

from __future__ import annotations

import itertools
import json
import time
from pathlib import Path

from . import ff as FF
from . import 판정 as J

원장경로 = "cut/판정.jsonl"
기본상한 = 200                 # 훑을 후보 수 상한. 조합은 금방 터진다


def 노드덮개족(바탕, 요청, T크기=(2, 3), S크기=(2, 4), 상한: int = 기본상한):
    """(이름, a, b) 를 차례로 낸다. **결정적이다** -- 같은 인스턴스면 같은 순서."""
    VR, VS = sorted(요청.노드), sorted(바탕.노드)
    난것 = 0
    for t in range(T크기[0], min(T크기[1], len(VR)) + 1):
        for T in itertools.combinations(VR, t):
            need = sum(요청.노드[v]["cpu"] for v in T)
            for s in range(max(S크기[0], t), min(S크기[1], len(VS)) + 1):
                # |S| >= |T| 인 것만. 아니면 일대일 제약이 이미 더 세게 막는다
                for S in itertools.combinations(VS, s):
                    if sum(바탕.노드[u]["cpu"] for u in S) >= need:
                        continue                      # 덮개 조건 불성립 -- 유효하지 않다
                    a = {("x", v, u): 1.0 for v in T for u in S}
                    yield (f"덮개 T{list(T)} S{list(S)}", a, float(t - 1))
                    난것 += 1
                    if 난것 >= 상한:
                        return


족들 = {"노드덮개": 노드덮개족}


def 훑기(바탕, 요청, 족: str = "노드덮개", 상한: int = 기본상한, 시한초: float = 30.0,
       말하기=None, **족인자) -> dict:
    """족을 훑고 **표본 벡터**를 낸다. 찾은 것만 세지 않는다.

        훑은 = ACCEPT + 무효 + 안자름 + 안조임 + 못잼

    이 항등식이 서야 "못 찾았다" 와 "안 훑었다" 가 안 섞인다."""
    말 = 말하기 or (lambda s: None)
    만들기 = 족들.get(족)
    if 만들기 is None:
        return {"됐나": False, "말": f"모르는 족 '{족}' ({', '.join(족들)})"}
    p = FF.짓기(바탕, 요청)
    셈 = {"ACCEPT": 0, "무효": 0, "안자름": 0, "안조임": 0, "못잼": 0}
    받은것, 시작 = [], time.monotonic()
    훑은 = 0
    for 이름, a, b in 만들기(바탕, 요청, 상한=상한, **족인자):
        훑은 += 1
        r = J.채택판정(p, a, b, 시한초=시한초)
        if r["결정"] == "ACCEPT":
            셈["ACCEPT"] += 1
            받은것.append({"이름": 이름, "b": b, "까닭": r["까닭"]})
            말(f"[찾기] **ACCEPT** {이름} <= {b}")
        else:
            칸 = {"유효": "무효", "자름": "안자름", "조임": "안조임"}.get(r["막힌곳"], "못잼")
            # 유효 단계에서 막혔어도 '못잼' 일 수 있다 -- 무효와 가른다
            if r["막힌곳"] == "유효" and r.get("유효", {}).get("판정") == J.못잼:
                칸 = "못잼"
            셈[칸] += 1
        if 훑은 % 25 == 0:
            말(f"[찾기] {훑은}개 훑음 · ACCEPT {셈['ACCEPT']}")
    return {
        "됐나": True, "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "족": 족, "훑은": 훑은, **셈,
        "맞나": 훑은 == sum(셈.values()),
        "받은것": 받은것, "초": round(time.monotonic() - 시작, 2),
        "상한닿음": 훑은 >= 상한,
        "크기": p.크기(),
    }


def 보고(r: dict) -> str:
    if not r.get("됐나"):
        return "**못 훑었다**: " + str(r.get("말"))
    줄 = [f"족 `{r['족']}` · 훑은 후보 {r['훑은']}개 · {r['초']}초",
         f"  ACCEPT {r['ACCEPT']} · 무효 {r['무효']} · 안자름 {r['안자름']} · "
         f"안조임 {r['안조임']} · 못잼 {r['못잼']}"
         + ("  (맞다)" if r["맞나"] else "  **(항등식이 안 맞는다)**")]
    for x in r["받은것"][:5]:
        줄.append(f"    받음  {x['이름']} <= {x['b']}")
    if r["상한닿음"]:
        줄.append("  **상한에 닿았다** -- 다 훑은 것이 아니다. 포화라고 말하지 마라")
    elif r["ACCEPT"] == 0:
        줄.append("  **이 족을 다 훑었고 받은 것이 없다** -- 포화다. "
                  "다음은 족을 넓히는 것이지 문턱을 낮추는 것이 아니다")
    return "\n".join(줄)


def 적기(r: dict, repo=None) -> dict:
    p = Path(repo or Path(__file__).resolve().parent.parent) / 원장경로
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = {k: v for k, v in r.items() if k != "받은것"}
    줄["받은것"] = [x["이름"] for x in r.get("받은것", [])]
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄
