"""막힌 씬을 다시 도는가 -- **blocked 로 런이 끝나면 안 된다.**

실측 2026-09-04 (VM, Gemini): 12씬 중 9씬이 통과하고 3씬이 막힌 채 220초 만에
"1~3화 blocked" 로 런이 끝났다. 예산은 여섯 시간이었다.

원인은 `attempted` 다. 한 호출 안에서 같은 씬을 다시 잡지 않게 막는데(그게 없으면 같은
씬을 999번 "넘어간다" 고 찍는 무한 루프가 된다 -- 회귀 검사가 실측으로 잡았다), 그러면
막힌 씬은 **그 런 안에서 두 번 다시 기회를 얻지 못한다.** 남은 다섯 시간이 통째로 낭비된다.

그런데 여기서 실패는 결정론적이지 않다. 디렉터·배우·화자를 새로 뽑고 실패 사유를 되먹이면
다음 바퀴에 통과하는 일이 흔하다. 그래서 바퀴를 돈다.

실행: python3 tests/test_rounds.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel.state import Novel, Character, Scene                       # noqa: E402
from novel import drive as D                                          # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


TURN = json.dumps({"inner_thought": "", "action": "", "speech": "그렇구나",
                   "emotions": {"joy": 45, "melancholy": 40, "isolation": 40,
                                "narrative_pull": 0}}, ensure_ascii=False)
GOOD = "그라인더 소리가 멎었다. 나는 잔을 돌리며 창밖을 바라보았다."
BAD = "공명의 비밀번호가 적혀 있었다. 잔이 식어 있었다."   # V008 지식 누출
FILLER = "물을 올렸다. 레코드를 골랐다. 창밖은 아직 밝았다. " * 60
MARK = "식은 자판기 커피"          # 이 씬을 프롬프트에서 알아보는 표식


def world(n=3):
    nv = Novel(title="시험", pov_character="A",
               characters=[Character("A", "화자"), Character("공명", "동기")],
               # 화자가 모르는 비밀 하나. 산문이 이것을 언급하면 V008 이 hard 로 잡는다.
               facts={"secrets": {"공명의 비밀번호": {"knows": ["공명"], "aliases": []}}})
    nv.scenes = [Scene(id=f"s{i}", episode=1, location="카페", punctum="소리",
                       participants=["A", "공명"], directives=["둘이 말하지 않는다"])
                 for i in range(n)]
    return nv


print("[바퀴] 막힌 씬을 다음 바퀴에 다시 잡는가")


class Stubborn:
    """s2 는 첫 바퀴에 계속 막힌다. **punctum 으로 식별한다** -- 화자 프롬프트에
    실리는 것은 location/punctum 이지 directives 가 아니다."""

    def __init__(self):
        self.round2 = False
        self.prose_for_s2 = 0

    def __call__(self, prompt):
        if "이어서 계속 써라" in prompt:
            return FILLER
        if "산문만 출력한다" in prompt:
            if MARK in prompt:                   # s2 의 punctum 으로 식별한다
                self.prose_for_s2 += 1
                return GOOD if self.round2 else BAD
            return GOOD
        return TURN


n = world(3)
n.scenes[2].punctum = MARK
r = D.drive(n, None, llm=Stubborn(), max_repairs=1, skip_blocked=9, rounds=1)
ok(r["status"] == "partial" and r["failed"] == 1,
   f"한 바퀴로는 막힌 채 끝난다 ({r['status']}, failed {r['failed']})  ← 이것이 그 실측이다")
ok(r["blocked"] and r["blocked"][0]["id"] == "s2",
   f"무엇이 막았는지 함께 돌려준다 ({r.get('blocked')})  ← 'blocked' 세 글자로는 아침에 알 수 없다")
ok("V008" in r["blocked"][0]["why"], f"어느 관문인지까지 ({r['blocked'][0]['why'][:40]})")

n2 = world(3)
n2.scenes[2].punctum = MARK


class Flip(Stubborn):
    """두 번째 바퀴부터 통과한다 -- 실패가 결정론적이지 않다는 것의 최소 모형."""

    def __call__(self, prompt):
        if MARK in prompt and "산문만 출력한다" in prompt:
            self.prose_for_s2 += 1
            if self.prose_for_s2 > 2:        # 첫 바퀴(시도 2회)를 넘기면 통과
                return GOOD
            return BAD
        return Stubborn.__call__(self, prompt)


r2 = D.drive(n2, None, llm=Flip(), max_repairs=1, skip_blocked=9, rounds=3)
ok(r2["status"] == "done", f"두 번째 바퀴에서 통과한다 ({r2['status']})")
ok(r2["failed"] == 0 and not r2["blocked"], f"막힌 씬이 남지 않는다 ({r2})")
ok(all(s.status == "verified" for s in n2.scenes), "세 씬 모두 verified")

print("[바퀴] 통과한 씬은 다시 쓰지 않는다  ← 다시 쓰면 그만큼이 통째로 버려진다")
n3 = world(2)
n3.scenes[0].status = "verified"
n3.scenes[0].prose = "이미 쓴 산문"
D.drive(n3, None, llm=Stubborn(), max_repairs=1, skip_blocked=9, rounds=3)
ok(n3.scenes[0].prose == "이미 쓴 산문", "verified 산문이 그대로다")

print("[바퀴] 이력은 지우지 않는다  ← 아침에 읽을 유일한 단서다")
stuck = [s for s in n.scenes if s.status == "failed"]
ok(stuck and stuck[0].attempts, f"attempts 가 남아 있다 ({len(stuck[0].attempts)}건)")

print("[영속] 바퀴를 돌아도 씬마다 저장한다")
d = Path(tempfile.mkdtemp()); path = d / "n.json"
n4 = world(2)
n4.scenes[1].punctum = MARK
D.drive(n4, str(path), llm=Flip(), max_repairs=1, skip_blocked=9, rounds=3)
ok(path.exists() and all(s.status == "verified" for s in Novel.load(path).scenes),
   "저장된 원고도 전부 verified")

print()
if fails:
    print(f"바퀴: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("바퀴: 재시도 · 막힘 보고 · verified 보존 · 이력 보존 · 영속 -- 통과")
