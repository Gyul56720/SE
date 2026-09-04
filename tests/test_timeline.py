"""시간 되감기 -- **모순을 없애는 방법은 좌표를 하나 더 주는 것이다.**

씨앗에 "스무 살 생일에 하루를 되돌려 받는 나라" 가 나왔다. 그러면 우리가 만든 관계·지식
원장이 통째로 무너진다: "둘이 사귀기 시작했다" 와 "그런 적 없다" 가 같이 참이 되고,
"설윤이 안다" 와 "설윤이 모른다" 가 같이 참이 된다. 관문은 그것을 모순으로 잡는다.

이 저장소는 이미 같은 문제를 한 번 풀었다. misbelieve 가 그것이다 -- "설윤은 X 를 믿는데
사실은 Y" 는 진실과 믿음을 **가르기 전에는** 모순이었다. 축을 하나 더 주니 둘 다 참이 됐다.

시간도 같다. 씬에 branch 를 주고, 원장이 **지금 시간선에 남아 있는 씬만** 보게 하면
모순이 사라진다. 되감은 사람만 기억을 갖고 넘어오고(carry), 그 비대칭이 정보 격차를
통째로 만든다.

실행: python3 tests/test_timeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import gate                                                # noqa: E402
from novel.state import Scene                                         # noqa: E402
from novel.world_romance import build                                 # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def sc(sid, **kw):
    s = Scene(id=sid, participants=["설윤", "공명"])
    for k, v in kw.items():
        setattr(s, k, v)
    return s


print("[동사] rewind 가 표에 있고 규율이 붙어 있는가")
from novel.verbs import VERBS, BUDGETED                               # noqa: E402
ok("rewind" in VERBS, "닫힌 집합에 등록돼 있다")
ok(set(VERBS["rewind"]["params"]) == {"who", "carry", "cost", "back_to"},
   f"who/carry/cost/back_to 를 요구한다 ({VERBS['rewind']['params']})")
ok("rewind" in BUDGETED,
   "예산 동사다  ← 횟수가 무한하면 긴장이 죽는다 (씨앗이 요구하는 규율)")

print("[좌표] 지워진 구간의 관계 변화가 이 시간선에 남지 않는가")
n = build()
n.scenes = [
    sc("s0"),
    sc("s1", relation_ops=[{"op": "start", "kind": "연인",
                            "members": ["설윤", "공명"]}]),
    sc("s2", world_ops=[{"event": "rewind", "who": "설윤", "carry": ["설윤"],
                         "cost": "그날의 목소리를 잃는다", "back_to": "s1"}]),
    sc("s3"),
]
live, carried = n.timeline(3)
ok(live == {0, 3}, f"s1·s2 가 지워진다 ({sorted(live)})")
ok(carried.get("설윤") == {1, 2}, f"설윤만 그 구간을 기억한다 ({carried})")

rels, problems = n.derive_relations(3)
ok(not rels, f"지워진 연애는 원장에 없다 ({[(r.kind, r.members) for r in rels]})")
ok(not [p for p in problems if p[0] == "hard"],
   f"모순으로 잡히지 않는다 ({problems})")

print("[비대칭] 되감은 사람만 기억을 갖고 넘어오는가  ← 이것이 정보 격차의 엔진이다")
n2 = build()
n2.scenes = [
    sc("t0", world_ops=[{"event": "reveal", "term": "공명의 무대 공포",
                         "to": ["설윤", "도영"]}]),
    sc("t1", world_ops=[{"event": "rewind", "who": "설윤", "carry": ["설윤"],
                         "cost": "손끝의 감각 하나", "back_to": "t0"}]),
    sc("t2"),
]
knowers = gate._knowers(n2, "공명의 무대 공포", "t2")
ok("설윤" in knowers, f"되감은 설윤은 여전히 안다 ({sorted(knowers)})")
ok("도영" not in knowers,
   f"같이 들었던 도영은 모른다 ({sorted(knowers)})\n"
   "         ← 이 비대칭이 없으면 되감기가 서사 장치가 아니라 그냥 취소다")

print("[모순 없음] 같은 사실이 시간선마다 다를 수 있는가")
print("      ← misbelieve 가 진실과 믿음을 갈랐듯, branch 가 시간을 가른다")
before = gate._knowers(n2, "공명의 무대 공포", "t0")
ok("도영" in before, f"되감기 전에는 도영도 알았다 ({sorted(before)})")
ok("도영" not in gate._knowers(n2, "공명의 무대 공포", "t2"),
   "되감기 후에는 모른다 -- 둘 다 참이고 모순이 아니다")

print("[안전] 되감기가 없으면 아무것도 바뀌지 않는가")
n3 = build()
n3.scenes = [sc("u0"), sc("u1", relation_ops=[{"op": "start", "kind": "연인",
                                               "members": ["설윤", "공명"]}])]
live3, carried3 = n3.timeline(1)
ok(live3 == {0, 1} and not carried3, f"전부 살아 있다 ({sorted(live3)})")
ok(len(n3.derive_relations(1)[0]) == 1, "관계가 정상적으로 선다")

print("[방어] back_to 가 없는 씬을 가리켜도 죽지 않는가")
n4 = build()
n4.scenes = [sc("v0"), sc("v1", world_ops=[{"event": "rewind", "who": "설윤",
                                            "carry": ["설윤"], "cost": "x",
                                            "back_to": "없는씬"}])]
try:
    live4, _ = n4.timeline(1)
    ok(live4 == {0}, f"그 씬만 지우고 넘어간다 ({sorted(live4)})")
except Exception as e:                                                # noqa: BLE001
    ok(False, f"죽었다 ({type(e).__name__})")

print()
if fails:
    print(f"시간선: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("시간선: 동사 · 좌표 · 비대칭 · 모순 없음 · 안전 -- 통과")
