"""소설 기계 관문의 회귀 검사 -- 위반을 하나씩 심어서 실제로 잡히는지 본다.

막는다고 문서에 적는 것과 실제로 막는 것은 다르다. 직선거리에서 심판과 그 심판의 테스트가
같은 맹점을 공유해 초록불이 떴던 것이 그 증거다.

**과잉 기각도 함께 본다.** 정당한 문장을 기각하는 심판은 맞는 답도 버린다 -- 상대 임계만
쓰다가 진짜 최소가 0 일 때 정답을 기각한 것과 같은 함정이다. LLM·네트워크 없이 돈다.

실행: python3 tests/test_novel_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel.state import Novel, Character, Scene, Turn        # noqa: E402
from novel import gate                                       # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def has(vs, rule, severity=None):
    return any(v.rule == rule and (severity is None or v.severity == severity) for v in vs)


def E(joy=10, mel=50, iso=50, pull=0):
    return {"joy": joy, "melancholy": mel, "isolation": iso, "narrative_pull": pull}


def novel_fixture():
    return Novel(
        title="시험", pov_character="와타나베",
        characters=[
            Character("와타나베", "화자"),
            Character("미도리", "생명력", emotion_envelope={"joy": 40},
                      knows=["아버지의 병"]),
            Character("나오코", "상실", knows=["기즈키의 죽음", "아버지의 병"]),
        ],
        facts={"secrets": {"기즈키의 죽음": ["나오코", "와타나베"]}})


def scene_fixture(**kw):
    base = dict(id="s1", location="재즈 바", punctum="빌 에반스의 피아노",
                participants=["와타나베", "미도리"], mode="dialogue",
                turns=[Turn("미도리", "기대고 싶다", "담배에 불을 붙이며",
                            "나는 사랑에 굶주려 있었어", E(joy=55)),
                       Turn("와타나베", "무슨 말을 해야 할까", "잔을 돌리며",
                            "그렇구나", E(joy=10))],
                prose="빌 에반스의 피아노가 흘렀다. 나는 그녀의 잔을 바라보았다.")
    base.update(kw)
    return Scene(**base)


N = novel_fixture()

print("[정상] 깨끗한 씬은 통과한다 -- 과잉 기각 확인")
vs = gate.check(scene_fixture(), N)
passed, why = gate.verdict(vs)
ok(passed, f"정상 씬이 통과한다 ({why.splitlines()[0]})")

print("[V001] 형식")
bad = scene_fixture(turns=[Turn("유령", "", "", "누구세요", E())])
ok(has(gate.check(bad, N), "V001", "hard"), "등장인물에 없는 화자를 잡는다")
bad = scene_fixture(turns=[Turn("미도리", "", "", "안녕", {"joy": 200, "melancholy": 1,
                                                          "isolation": 1,
                                                          "narrative_pull": 0})])
ok(has(gate.check(bad, N), "V001", "hard"), "감정 범위 밖 값을 잡는다")

print("[V002] 감정 급변")
bad = scene_fixture(turns=[Turn("미도리", "", "", "a", E(joy=90)),
                           Turn("와타나베", "", "", "b", E()),
                           Turn("미도리", "", "", "c", E(joy=5))])
ok(has(gate.check(bad, N), "V002", "hard"), "한 턴에 85 점프하는 것을 잡는다")

print("[V003] 감정 폭 붕괴 -- 미도리를 지키는 관문")
bad = scene_fixture(turns=[Turn("미도리", "", "", "a", E(joy=5)),
                           Turn("미도리", "", "", "b", E(joy=6)),
                           Turn("와타나베", "", "", "c", E())])
vs = gate.check(bad, N)
ok(has(vs, "V003", "hard"), "미도리의 joy 가 봉투 하한(40)에 못 닿으면 기각한다")
ok(has(vs, "V003", "soft"), "감정이 고정된 인물을 soft 로 보고한다")

single = scene_fixture(turns=[Turn("미도리", "", "", "안녕", E(joy=55))])
ok(not has(gate.check(single, N), "V003", "soft"),
   "턴이 하나인 인물은 폭 붕괴로 보고하지 않는다  ← 과잉 기각 방지")

print("[V004] 시점 위반")
bad = scene_fixture(prose="미도리는 아버지를 떠올리며 깊이 후회했다. 비가 내렸다.")
ok(has(gate.check(bad, N), "V004", "hard"), "타인의 내면을 사실로 단정한 것을 잡는다")
good = scene_fixture(prose="나는 미도리가 아버지를 떠올렸다고 생각했다. 비가 내렸다.")
ok(not has(gate.check(good, N), "V004", "hard"),
   "'나는 ~라고 생각했다'(화자의 추측)는 기각하지 않는다  ← 과잉 기각 방지")
q = scene_fixture(prose='"나는 늘 외로웠다고 생각했어." 그녀가 말했다. 비가 내렸다.')
ok(not has(gate.check(q, N), "V004", "hard"), "대사 안의 내면 서술은 검사하지 않는다")

print("[V005] 감정 직접 서술")
bad = scene_fixture(prose="나는 슬펐다. 그리고 외로웠다. 무척 우울했다.")
ok(has(gate.check(bad, N), "V005", "hard"), "직접 감정 서술이 여러 번이면 기각한다")
one = scene_fixture(prose="나는 슬펐다. 빌 에반스의 피아노가 흘렀다.")
ok(has(gate.check(one, N), "V005", "soft"), "한 번은 soft 로 통과시킨다  ← 과잉 기각 방지")
spoken = scene_fixture(prose='"난 외로웠다." 그녀가 말했다. 빌 에반스의 피아노가 흘렀다.')
ok(not has(gate.check(spoken, N), "V005"), "대사 안의 감정어는 허용한다")

print("[V006] 푼크툼 유실")
bad = scene_fixture(prose="나는 잔을 바라보았다. 아무 소리도 나지 않았다.")
ok(has(gate.check(bad, N), "V006", "soft"), "Director 가 심은 푼크툼이 사라진 것을 보고한다")

print("[V007] 화자 없는 씬 -- 원 설계의 구멍")
bad = scene_fixture(participants=["나오코", "레이코"], mode="dialogue")
ok(has(gate.check(bad, N), "V007", "hard"), "화자 부재 씬의 직접 서술을 기각한다")
letter = scene_fixture(participants=["나오코", "레이코"], mode="letter")
ok(not has(gate.check(letter, N), "V007"), "편지 모드로 세탁하면 통과한다")

print("[V008] 지식 누출")
bad = scene_fixture(turns=[Turn("미도리", "", "", "기즈키의 죽음 얘기 들었어", E(joy=55))])
ok(has(gate.check(bad, N), "V008", "hard"), "모르는 비밀을 말하는 인물을 잡는다")
fine = scene_fixture(turns=[Turn("나오코", "", "", "기즈키의 죽음 이후로", E(joy=45))])
ok(not has(gate.check(fine, N), "V008"), "아는 인물이 말하는 것은 통과한다")

print("[판정] hard 가 있으면 기각, soft 만 있으면 통과")
ok(gate.verdict([gate.Violation("X", "soft", "w", "d")])[0], "soft 만이면 통과")
ok(not gate.verdict([gate.Violation("X", "hard", "w", "d")])[0], "hard 가 있으면 기각")

print("[신호] 위반이 수리에 쓸 만한 정보를 담는가")
v = [x for x in gate.check(scene_fixture(prose="미도리는 깊이 후회했다."), N)
     if x.rule == "V004"][0]
ok("미도리" in v.detail and "관찰" in v.detail,
   f"어느 인물의 무엇을 어떻게 고칠지 말해준다: {v.detail[:45]}...")

print()
if fails:
    print(f"소설 기계 관문: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("소설 기계 관문: 형식·급변·폭붕괴·시점·직접감정·푼크툼·화자부재·지식누출을 잡고, "
      "화자의 추측과 대사 속 감정어는 통과시킨다 -- 통과")
