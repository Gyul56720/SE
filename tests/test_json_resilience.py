"""추출기가 깨진 JSON 을 내도 밤이 날아가지 않는가.

2026-09-03 밤샘 런은 일곱 시간에 **0자**로 끝났다. 원인은 쿼터도 모델도 아니고 이 자리였다:

    novel/drive.py:588  b = _json(_llm_for(llm, "extractor")(...))
    json.decoder.JSONDecodeError: Expecting ',' delimiter: line 4 column 258

추출기가 값 안의 큰따옴표를 escape 하지 않은 JSON 을 한 번 냈는데, 재시도가 없어서 예외가
build_episode 를 뚫고 올라가 **그 결말 블록 열다섯 화가 통째로 버려졌다.** 같은 일이 블록
마다 반복돼 200화 중 한 화도 산문에 도달하지 못했다.

여기서 고정하는 것:
  1. 깨진 JSON 은 에러 문구를 붙여 다시 묻는다 -- 모델은 대체로 자기 JSON 을 고친다
  2. 끝내 못 받아도 예외가 블록을 죽이지 않는다
  3. dict 가 아닌 JSON(문자열/배열)은 그 자리에서 걸린다 -- 안 걸면 한참 뒤
     'str' object has no attribute 'get' 로 죽어 원인을 못 찾는다

실행: python3 tests/test_json_resilience.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import drive as D                                          # noqa: E402
from novel.state import Scene                                         # noqa: E402
from novel.world_romance import build                                 # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# 실제로 밤을 날린 모양 그대로 -- 값 안의 큰따옴표가 escape 되지 않았다.
BROKEN = '{"beat": "설윤이 "괜찮아"라고 말한다", "establishes": ["비밀을 안다"]}'
GOOD = json.dumps({"beat": "설윤이 통화를 듣는다", "participants": ["설윤"],
                   "requires": [], "establishes": ["비밀을 안다"], "scale": 1},
                  ensure_ascii=False)

print("[재시도] 깨진 JSON 을 내면 에러를 붙여 다시 묻는다")
calls = []


def flaky(prompt):
    calls.append(prompt)
    return BROKEN if len(calls) == 1 else GOOD


got = D.call_json(flaky, "뽑아라", label="시험")
ok(got.get("beat") == "설윤이 통화를 듣는다", f"두 번째에 성공한다 ({got.get('beat')})")
ok(len(calls) == 2, f"두 번 불렀다 ({len(calls)})")
ok("파싱되지 않았다" in calls[1], "재시도 프롬프트에 실패 사실이 실린다")
ok("escape" in calls[1], "무엇을 고칠지 말해준다  ← '다시 해봐'는 지시가 아니다")

print("[한계] 계속 깨지면 조용히 넘어가지 않고 사실대로 실패한다")
try:
    D.call_json(lambda p: BROKEN, "뽑아라", tries=2, label="시험")
    ok(False, "예외가 올라온다")
except ValueError as e:
    ok("2번 시도했지만" in str(e), f"몇 번 시도했는지 말해준다 ({str(e)[:60]})")

print("[형] dict 가 아니면 그 자리에서 걸린다")
for bad, what in ((' "그냥 문자열" ', "문자열"), ("[1, 2, 3]", "배열")):
    try:
        D._json('{"x":1}'.replace('{"x":1}', bad) if "{" not in bad else bad)
        ok(False, f"{what} 을 거른다")
    except ValueError as e:
        ok("객체가 아니라" in str(e) or "찾지 못했다" in str(e),
           f"{what} 을 거른다 ({str(e)[:50]})")

print("[본체] 추출이 끝내 실패해도 **블록이 죽지 않는다**  ← 이 검사가 이 파일의 존재 이유")
SPEC = dict(seq=1, eps=(1, 5), scale=1, summary="설윤이 자리를 잃는다",
            requires=["비밀을 안다"], establishes=["설윤이 자리를 잃었다"], world_ops=[])


def always_broken(prompt):
    if "--- 시나리오 ---" in prompt:
        return BROKEN                                    # 추출은 언제나 깨진다
    return "## 장면\n무언가 일어난다\n\n## 성립시키는 조건\n비밀을 안다"


n = build()
try:
    scenes = D.build_episode(n, SPEC, llm=always_broken, max_repairs=1)
    raised = None
except Exception as e:                                                # noqa: BLE001
    scenes, raised = [], e
ok(raised is None, f"예외가 올라오지 않는다 ({type(raised).__name__ if raised else '없음'})")
ok(scenes, f"결말 씬만이라도 남는다 ({len(scenes)}개)  ← 0개면 블록을 통째로 잃은 것과 같다")

print("[ops] world_ops 가 문자열 목록으로 와도 저장이 죽지 않는다")
print("      ← 밤샘 런의 두 번째 사인: novel.save() 안 derive_gates 에서 터졌다")
from novel import verbs as V                                          # noqa: E402
bad = V.validate_op("설윤이 자리를 잃었다")
ok(bad and "객체가 아니다" in bad[0], f"검증기가 죽지 않고 위반으로 보고한다 ({bad})")
ok(V.validate_op({"event": "meet", "pair": ["설윤", "공명"]}) == [],
   "멀쩡한 op 는 그대로 통과한다")

n2 = build()
sc2 = Scene(id="ops1", episode=1)
sc2.world_ops = ["설윤이 자리를 잃었다"]                    # LLM 이 이렇게 낼 때가 있다
n2.scenes.append(sc2)
try:
    n2.sync_gates(); n2.sync_relations()
    ok(True, "save 경로가 예외 없이 지나간다")
except AttributeError as e:
    ok(False, f"derive_gates 에서 죽었다 ({e})")

kept = D._ops(["문자열", {"event": "meet", "pair": ["설윤", "공명"]}], "시험")
ok(len(kept) == 1 and kept[0]["event"] == "meet",
   f"경계에서 객체만 남긴다 ({kept})  ← 버린 것은 로그에 남는다")

print("[막힘] 막힌 씬 하나가 나머지 전부를 세우지 않는가")
print("      ← 2026-09-04 시험 런: 111초 만에 blocked, verified 0, 뒤 29씬은 손도 못 댔다")
from novel.state import Novel                                         # noqa: E402

BAD_PROSE = "형의 사고 이야기가 거기 있었다. 잔이 식어 있었다."  # 화자가 모르는 비밀
GOOD_PROSE = "그라인더 소리가 멎었다. 나는 잔을 돌리며 창밖을 바라보았다."
TURN = json.dumps({"inner_thought": "", "action": "", "speech": "그렇구나",
                   "emotions": {"joy": 45, "melancholy": 40, "isolation": 40,
                                "narrative_pull": 0}}, ensure_ascii=False)


MARK = "표식복도"      # location 은 화자 프롬프트에 실린다. 씬 id 와 directives 는 아니다.


def make(n_scenes=3):
    nv = build()
    nv.scenes = []
    for i in range(n_scenes):
        sc = Scene(id=f"ep001_{i:03d}m", episode=i + 1,
                   participants=[nv.pov_character], directives=["무언가 일어난다"],
                   location=MARK if i == 0 else "연습동 복도")
        nv.scenes.append(sc)
    return nv


class ProseFake:
    """첫 씬은 언제나 관문에 막히고(V008 지식 누출), 나머지는 깨끗하다."""

    def __call__(self, prompt):
        if "산문만 출력한다" in prompt:
            return BAD_PROSE if MARK in prompt else GOOD_PROSE
        return TURN


nv = make(3)
r = D.drive(nv, None, llm=ProseFake(), max_repairs=1, skip_blocked=0)
ok(r["status"] == "blocked" and r["verified"] == 0,
   f"기본값은 예전 그대로 첫 실패에서 멈춘다 ({r})  ← 대화형에서는 이게 맞다")

nv2 = make(3)
r2 = D.drive(nv2, None, llm=ProseFake(), max_repairs=1, skip_blocked=999)
ok(r2["verified"] >= 1,
   f"넘어가면 뒤 씬들이 채워진다 ({r2})  ← 이게 안 되면 밤이 또 날아간다")
ok(r2["status"] == "partial", f"부분 성공을 'partial' 로 구분한다 ({r2['status']})")
blocked = [s for s in nv2.scenes if s.status == "failed"]
ok(blocked and blocked[0].violations,
   f"막힌 씬은 위반을 그대로 갖고 있다 ({blocked[0].violations[:1] if blocked else '없음'})"
   "  ← 넘어가되 무엇이 막혔는지 잃지 않는다")

print("[한 회차] upto_episode 로 1화만 돌릴 수 있는가")


class CleanFake:
    def __call__(self, prompt):
        return GOOD_PROSE if "산문만 출력한다" in prompt else TURN


nv4 = make(3)                                   # 1화·2화·3화 각 1씬
r4 = D.drive(nv4, None, llm=CleanFake(), max_repairs=1, upto_episode=1)
ok(r4["verified"] == 1, f"1화만 채운다 ({r4})")
ok(r4["remaining"] == 0, f"남은 것 계산도 그 범위 안에서 센다 ({r4['remaining']})")
ok([s.status for s in nv4.scenes] == ["verified", "pending", "pending"],
   f"2·3화는 손대지 않는다 ({[s.status for s in nv4.scenes]})")

print("[인물] 등장인물 아닌 이름이 회차를 죽이지 않는가")
print("      ← 실측: '낯선 남자'·'취객' 이 participants 에 들어가 actor_prompt 의")
print("        novel.character() 가 KeyError 로 터졌고 1~10화가 산문 0자로 끝났다")
nvp = build()
kept = D._people(["설윤", "낯선 남자", "공명", "취객", "설윤"], nvp, "시험")
ok(kept == ["설윤", "공명"], f"등장인물만 남기고 중복도 지운다 ({kept})")
ok(D._people([], nvp, "시험") == [nvp.pov_character],
   "전부 걸러지면 화자를 넣는다  ← 참가자 0명이면 배우 단계가 아무것도 못 한다")
ok(D._people(["취객"], nvp, "시험") == [nvp.pov_character], "낯선 이름만 있어도 마찬가지")

nv5 = build()
sc5 = Scene(id="ghost", episode=1, participants=["취객", "낯선 남자"],
            directives=["취객이 온다"])
nv5.scenes = [sc5]
try:
    r5 = D.run_scene(nv5, sc5, CleanFake(), max_repairs=1)
    ok(r5["status"] in ("verified", "failed"),
       f"이미 저장된 씬에 낯선 이름이 있어도 죽지 않는다 ({r5['status']})")
except KeyError as e:
    ok(False, f"KeyError 로 죽었다 ({e})  ← 회차 전체가 여기서 멈춘다")

print("[V009] 산문 수리로 못 고치는 관계 선언은 경계에서 버린다")
print("      ← 시험 런의 실제 사인: 관계 구성원이 두 사람이 아니다: []  (4시도 111초 실패)")
nv3 = build()
kept, moved = D._rel_ops([{"op": "start", "kind": "연인", "members": []},
                          {"op": "start", "kind": "연인", "members": ["설윤", "설윤"]},
                          {"op": "start", "kind": "연인", "members": ["설윤", "없는사람"]},
                          {"op": "start", "kind": "연인", "members": ["설윤", "공명"]}],
                         nv3, "시험")
ok(len(kept) == 1 and kept[0]["members"] == ["설윤", "공명"],
   f"쓸 수 있는 선언 하나만 남는다 ({kept})")
ok(True, "빈 members · 자기 자신 · 없는 인물 셋 다 걸러진다")

print("[자리] world 동사가 relation_ops 에 오면 **버리지 않고 옮긴다**")
print("      ← 실측: {'op': 'meet', 'pair': [...]} 가 relation_ops 에 들어와 V009 가")
print("        '구성원이 두 사람이 아니다: []' 로 매 시도마다 hard 를 냈다 (16회)")
kept2, moved2 = D._rel_ops([{"op": "meet", "pair": ["설윤", "공명"]},
                            {"op": "start", "kind": "연인", "members": ["설윤", "공명"]}],
                           nv3, "시험")
ok(len(kept2) == 1, f"관계 선언은 남는다 ({kept2})")
ok(len(moved2) == 1 and moved2[0]["event"] == "meet",
   f"world 동사는 world_ops 로 옮겨진다 ({moved2})  ← 버리면 세계 변화가 사라진다")

kept3, moved3 = D._rel_ops(["meet(설윤, 재현)", "misbelieve('공명', 'x', 'y')"],
                           nv3, "시험")
ok(not kept3 and not moved3,
   f"함수 호출처럼 생긴 문자열은 버린다 ({kept3}, {moved3})  ← 파싱하면 더 틀린다")

print("[연출] direction 이 문자열로 와도 서술 단계가 죽지 않는다")
sc = Scene(id="x", direction="복도, 압정 자국")            # LLM 이 이렇게 낼 때가 있다
try:
    out = D._direction(sc)
    ok(out == "", f"빈 연출로 넘어간다 ({out!r})")
except AttributeError as e:
    ok(False, f"'str' object has no attribute 'get' 로 죽었다 ({e})")

print()
if fails:
    print(f"JSON 내구성: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("JSON 내구성: 재시도 · 한계 · 형 검사 · 블록 생존 · 연출 방어 -- 통과")
