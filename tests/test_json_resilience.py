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
