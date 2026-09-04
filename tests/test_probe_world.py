"""탐침 세계 -- 파이프라인 한 바퀴를 싸게 도는 최소 단위가 실제로 최소인가.

1~10화 블록은 디렉터 호출이 30회다. 배선 하나를 확인하려고 30회를 쓰고 40분을 기다리면,
기다리다 지쳐 확인 없이 밤을 걸게 된다(2026-09-04에 두 번 그랬고 두 번 다 0자였다).

여기서 고정하는 것은 **탐침이 싸고, 그러면서도 진짜를 잡는다**는 두 가지다. 실제로 이
탐침을 만들자마자 네 개를 잡았다:

  1. steps 를 시간순으로 썼는데 역방향 조립이 또 뒤집어 인과가 거꾸로 섰다
  2. 시계가 [12.0, 12.5, 0.0] 로 늘었다 줄었다 했다
  3. 결말 비트의 driver 가 비어 V022 가 결말 회차를 수동으로 읽었다
  4. 1~20화에 정보 격차가 없어 V016 이 3화부터 hard 를 냈다
     -- **1화만 돌려서는 절대 못 봤을 것이다.** 3회차가 쌓여야 발동한다

실행: python3 tests/test_probe_world.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import drive as D, gate                                    # noqa: E402
from novel import world_probe as W                                    # noqa: E402
from novel.world_romance import OUTCOMES as REAL                      # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


MD = ("## 장면\nb\n\n## 성립시키는 조건\n{cond}\n\n## 선행 조건\n없음\n\n"
      "## 등장인물\n설윤, 공명\n\n## 공간\nx\n\n## 여는 사건\nx\n\n## 장치\nx\n\n"
      "## 화자의 시야\nx\n\n## 말하지 않는 것\nx\n\n## 감정 이동\n0\n\n"
      "## 움직이는 사람\n설윤\n\n## 치른 대가\n무언가\n\n## 남은 시간\n{h}")


class Fake:
    def __init__(self):
        self.h, self.calls = 13.0, {"director": 0, "extractor": 0}

    def __call__(self, p):
        if "--- 시나리오 ---" in p:
            self.calls["extractor"] += 1
            sc = p.split("--- 시나리오 ---")[1]
            ls, cond = sc.splitlines(), ""
            for i, l in enumerate(ls):
                if l.startswith("## 성립시키는 조건"):
                    cond = next((x.strip() for x in ls[i + 1:] if x.strip()), "")
            return json.dumps({"beat": "b", "participants": ["설윤", "공명"],
                               "requires": [], "establishes": [cond] if cond else [],
                               "scale": 1, "driver": "설윤", "cost": "c",
                               "deadline_hours": self.h}, ensure_ascii=False)
        self.calls["director"] += 1
        if "<Task_Objective>" in p:
            self.h = max(0.5, self.h - 0.5)
            lo = p.index("<Task_Objective>")
            m = re.findall(r"'([^']+)'", p[lo:p.index("</Task_Objective>")])
            return MD.format(cond=m[0] if m else "", h=self.h)
        return MD.format(cond="", h=self.h)


n, f = W.build(), Fake()
scenes = D.build_episode(n, W.OUTCOMES[0], llm=f, max_repairs=0)
n.scenes.extend(scenes)
spine = [s for s in scenes if s.establishes]

print("[비용] 탐침이 실제로 싼가")
ok(f.calls["director"] <= 12,
   f"디렉터 호출 {f.calls['director']}회 (1~10화 블록은 30회였다)")
ok(len(scenes) <= 12, f"씬 {len(scenes)}개 -- 한 번 돌려보기에 충분히 작다")

print("[순서] 척추가 시간순으로 서는가  ← steps 는 사람이 시간순으로 쓴다")
order = [s.establishes[0] for s in spine]
ok(order.index("설윤이 배정 이의서를 쓰기로 한다")
   < order.index("공명이 그 이의를 정면으로 거절한다"),
   f"쓰기로 한 다음에 거절당한다 ({order[:2]})\n"
   "         실측: 역방향 조립이 시간순 steps 를 또 뒤집어 거꾸로 세웠다")
ok(order[-1] in W.OUTCOMES[0]["establishes"], "결말이 마지막")

print("[시계] 단조 감소하는가  ← 조립이 끝난 뒤 산수로 정한다")
hours = [s.deadline_hours for s in spine]
ok(all(a > b for a, b in zip(hours, hours[1:])), f"줄어들기만 한다 ({hours})")
ok(hours[0] == W.OUTCOMES[0]["deadline_hours"], f"결말이 준 시계에서 시작한다 ({hours[0]})")

print("[능동] 결말까지 움직이는 사람이 있는가")
ok(all(s.driver for s in spine),
   f"척추 전부 driver 가 채워진다 ({[s.driver for s in spine]})\n"
   "         결말이 비면 V022 가 그 회차를 '화자가 구경만 했다' 로 읽는다")

print("[관문] 조립 직후 hard 위반이 없는가")
hard = [str(v)[:70] for s in scenes for v in gate.check(s, n) if v.severity == "hard"]
ok(not hard, f"hard 0건 ({hard[:2]})")

print("[정보격차] 본편도 첫 블록부터 격차를 여는가")
kinds = {op.get("event") for o in REAL[:1] for op in (o.get("world_ops") or [])}
ok("conceal" in kinds or "misbelieve" in kinds or "fabricate" in kinds,
   f"1블록 world_ops 에 격차를 여는 동사가 있다 ({sorted(kinds)})\n"
   "         없으면 V016 이 3화부터 hard 를 낸다 -- 1화만 돌려서는 못 본다")

print()
if fails:
    print(f"탐침 세계: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("탐침 세계: 비용 · 순서 · 시계 · 능동 · 관문 · 정보격차 -- 통과")
