"""여성향 청춘 로맨스 세계의 무결성 -- 200화 결말 사슬이 관문을 통과하는가.

세계를 만드는 것은 코드를 쓰는 것과 다르지 않다. 결말 15개를 손으로 배치하면 반드시
어긋나는 곳이 생기고, 그것을 사람이 읽어서 찾으면 놓친다. 이 검사가 실제로 두 개를 잡았다:
expose/reveal 혼동(세계 버그)과 관계 동사가 원장에 안 들어가는 것(시스템 버그).

LLM 없이 돈다. 실행: python3 tests/test_world_romance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel.world_romance import build, OUTCOMES, POV                  # noqa: E402
from novel.state import Scene, Turn                                   # noqa: E402
from novel import gate, arc                                           # noqa: E402
from novel.verbs import validate_op                                   # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# 시퀀스별 감정 궤적. 4·6 은 꺾여야 하는 자리라 실제로 꺾는다.
PULL = {1: (-55, -40), 2: (-45, -20), 3: (-5, 20), 4: (40, -20),
        5: (20, 55), 6: (50, -30), 7: (60, 90), 8: (85, 95)}


def materialize():
    n = build()
    n.scenes = [
        Scene(id=f"ep{o['eps'][0]:03d}", location="연습동", punctum="조율되지 않은 현",
              participants=["설윤", "공명"], mode="dialogue", directives=[o["summary"]],
              episode=o["eps"][1], scale=o["scale"], is_episode_end=True,
              cliffhanger="shock_line", world_ops=list(o.get("world_ops", [])),
              relation_ops=list(o.get("relation_ops", [])),
              requires=list(o["requires"]), establishes=list(o["establishes"]),
              turns=[Turn(who, "", "", "말",
                          {"joy": 45, "melancholy": 40, "isolation": 40,
                           "narrative_pull": PULL[o["seq"]][i % 2]})
                     for who in ("설윤", "공명")])
        for i, o in enumerate(OUTCOMES)]
    return n


print("[규격] 보고서의 수치와 맞는가")
ok(len(OUTCOMES) >= 15, f"사건 {len(OUTCOMES)}개 (보고서 15~20)")
ok(sum(o["eps"][1] - o["eps"][0] + 1 for o in OUTCOMES) == 200, "회차 커버 200/200")
ok(all(arc.sequence_of(o["eps"][0])["n"] == o["seq"] for o in OUTCOMES),
   "각 결말의 회차가 선언한 시퀀스와 일치")

print("[동사] 세계가 카탈로그 밖의 동사를 쓰지 않는가")
bad = [e for o in OUTCOMES for op in o.get("world_ops", []) for e in validate_op(op)]
ok(not bad, f"동사 형식 오류 없음 ({bad[:2]})")

print("[인과] 결말의 requires 가 앞선 establishes 로 갚아지는가")
have, holes = set(), []
for o in OUTCOMES:
    holes += [(o["eps"], r) for r in o["requires"] if r not in have]
    have.update(o["establishes"])
ok(not holes, f"개연성 구멍 없음 ({holes[:2]})")

print("[관문] 결말 사슬 전체가 hard 없이 통과하는가")
n = materialize()
hard = [v for s in n.scenes for v in gate.check(s, n) if v.severity == "hard"]
ok(not hard, f"hard 위반 0 (얻은 값 {len(hard)}: {[str(v)[:60] for v in hard[:2]]})")

print("[원장] 관계가 world_ops 로 선언돼도 원장에 들어가는가")
ok(n.partner("설윤", upto_scene="ep001") is None, "초반엔 연인 없음")
ok(n.partner("설윤", upto_scene="ep186") == "공명",
   "마지막 start_romance 가 원장에 반영된다  ← 시스템 버그였던 자리")

print("[규모] 사건 규모가 시퀀스 하한 아래로 뒷걸음질하지 않는가")
bad_scale = [(o["eps"], o["scale"]) for o in OUTCOMES
             if o["scale"] < arc.sequence_of(o["eps"][0])["scale"][0] - 1]
ok(not bad_scale, f"규모 뒷걸음질 없음 ({bad_scale})")

print("[정보격차] 연독률의 핵심이 중반 내내 살아 있는가")
gone = []
for s in n.scenes:
    i = n.scene_index(s.id)
    gs, _ = n.derive_gates(i)
    live = [g for g in gs if g.kind in ("belief", "public_fiction", "knowledge_deny")
            and n.scene_index(g.from_scene) <= i]
    if not live and s.episode >= 30:
        gone.append(s.episode)
ok(not gone, f"30화 이후 격차가 사라지는 지점 없음 ({gone})")

print("[구원] 쌍방인가 -- 한쪽만이면 이 장르는 실패한다")
txt = " ".join(o["summary"] for o in OUTCOMES)
ok("공명이 재단을 등지고" in txt and "설윤이 돌아와" in txt,
   "남주가 전부를 버리는 장면과 여주가 돌아와 무대에 서는 장면이 둘 다 있다")
ok(build().character("설윤").emotion_envelope.get("joy", 0) >= 30,
   "여주에게 감정 하한이 있다 -- 없으면 몇 씬 만에 무기력해져 '주도적 서사'가 무너진다")

print("[선] 남주가 넘지 말아야 할 선")
ok("무고한 사람을 해치지 않는다" in build().character("공명").persona,
   "페르소나에 명시돼 있다 (보고서: 범죄적 선을 넘으면 독자가 반발한다)")

print("[척추] 모든 블록이 척추를 세울 씨앗을 갖는가")
print("      ← steps 가 없으면 그 블록은 결말 하나 + 곁가지 스물아홉 화가 된다")
thin = [(o["eps"], len(o.get("steps") or [])) for o in OUTCOMES
        if len(o.get("steps") or []) < 2]
ok(not thin,
   f"모든 블록에 steps 가 2개 이상 (모자란 곳: {thin})\n"
   "         실측 2026-09-04: 2블록부터 척추 1 / 서브플롯 29 였다 -- requires 는\n"
   "         앞 블록이 이미 갚아서 열린 조건이 0이 된다")

overlap = [(o["eps"], set(o.get("steps") or []) & set(o["requires"]))
           for o in OUTCOMES if set(o.get("steps") or []) & set(o["requires"])]
ok(not overlap,
   f"steps 와 requires 가 겹치지 않는다 ({overlap})\n"
   "         겹치면 앞 블록이 갚은 것을 또 세우게 된다")

seeds = [c for o in OUTCOMES for c in (o.get("steps") or [])]
ok(len(seeds) == len(set(seeds)),
   f"단계 문구가 블록 간에 중복되지 않는다 ({len(seeds)}개 중 {len(set(seeds))}개 고유)\n"
   "         겹치면 뒤 블록의 씨앗이 앞 블록의 establishes 로 갚아져 사라진다")

print()
if fails:
    print(f"로맨스 세계: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print(f"로맨스 세계: 규격·동사·인과·관문·원장·규모·정보격차·구원 -- 통과 "
      f"({len(OUTCOMES)}개 결말 / 200화)")
