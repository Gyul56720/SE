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
ok(has(vs, "V003", "soft"), "씬 안에서 감정이 고정이면 보고한다 (폭 붕괴)")

print("[V003 봉투] 하한은 **씬이 아니라 회차** 단위로 본다")
print("      ← 씬마다 물으면 새벽 편의점 장면에 joy 40 을 요구하게 된다.")
print("        실측 2026-09-04: V003 이 25회로 되돌려보내기 1위, 집필 시간 100%가 수리에")
n3 = novel_fixture()
n3.scenes = []
for ep in (1, 2):
    for k in range(2):
        sc = scene_fixture(turns=[Turn("미도리", "", "", "a", E(joy=5)),
                                  Turn("미도리", "", "", "b", E(joy=6))])
        sc.id, sc.episode, sc.is_episode_end = f"e{ep}s{k}", ep, (k == 1)
        n3.scenes.append(sc)

end1 = n3.scenes[1]
v1 = [v for v in gate.check(end1, n3) if v.rule == "V003" and "닿지 않았다" in v.detail]
ok(v1 and v1[0].severity == "soft",
   f"한 회차 가라앉는 것은 soft ({v1[0].severity if v1 else '못잡음'})  ← 서사다")

end2 = n3.scenes[3]
v2 = [v for v in gate.check(end2, n3) if v.rule == "V003" and "닿지 않았다" in v.detail]
ok(v2 and v2[0].severity == "hard",
   f"두 회차 연속이면 hard ({v2[0].severity if v2 else '못잡음'})  ← 이게 병이다")
ok(v2 and "1화도 그랬다" in v2[0].detail, "직전 회차를 짚어준다")

n4 = novel_fixture()
n4.scenes = []
for k in range(2):
    sc = scene_fixture(turns=[Turn("미도리", "", "", "a", E(joy=5)),
                              Turn("미도리", "", "", "b", E(joy=55))])
    sc.id, sc.episode, sc.is_episode_end = f"g{k}", 1, (k == 1)
    n4.scenes.append(sc)
ok(not [v for v in gate.check(n4.scenes[1], n4)
        if v.rule == "V003" and "닿지 않았다" in v.detail],
   "회차 안에 한 번이라도 하한을 넘으면 통과  ← 씬마다 밝을 필요는 없다")
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


# ===================================================================== 거시 서사
print()
print("[V013] 감정선이 시퀀스 궤도 위에 있는가 -- 200화에서 무너지는 것은 진도다")
from novel import arc                                                # noqa: E402

def arc_scene(ep, pull, scale=0, end=False, cliff="", sid=None):
    s = scene_fixture(id=sid or f"e{ep}")
    s.episode, s.scale, s.is_episode_end, s.cliffhanger = ep, scale, end, cliff
    s.turns = [Turn("A", "", "", "말", E(joy=45, pull=pull)),
               Turn("B", "", "", "말", E(joy=45, pull=pull))]
    return s

N2 = novel_fixture()
N2.pov_character = "A"

s = arc_scene(15, pull=70)                     # 시퀀스 1(-60~-10)인데 이미 끌림
N2.scenes = [s]
ok(has(gate.check(s, N2), "V013", "hard"),
   "15화에 pull 70 -> 너무 빨리 가까워졌다고 기각")

s = arc_scene(170, pull=-80)                   # 시퀀스 7(40~100)인데 아직 밀어냄
N2.scenes = [s]
ok(has(gate.check(s, N2), "V013", "hard"),
   "170화에 pull -80 -> 진도가 멈췄다고 기각")

s = arc_scene(15, pull=-30)                    # 정상
N2.scenes = [s]
ok(not has(gate.check(s, N2), "V013"), "궤도 위의 씬은 통과  ← 과잉 기각 방지")

print("[V014] 꺾여야 하는 시퀀스에 꺾임이 있는가 -- 너무 순탄한 것이 이 장르의 실패")
flat = [arc_scene(ep, pull=40, sid=f"f{ep}") for ep in (75, 90, 100)]
N2.scenes = flat
ok(has(gate.check(flat[-1], N2), "V014", "hard"),
   "시퀀스 4(입덕 부정)가 pull 변동 0 이면 기각")
dipped = [arc_scene(75, pull=50, sid="d1"), arc_scene(90, pull=-10, sid="d2"),
          arc_scene(100, pull=45, sid="d3")]
N2.scenes = dipped
ok(not has(gate.check(dipped[-1], N2), "V014"), "실제로 꺾이면 통과")

print("[V015] 사건 규모가 뒷걸음질하지 않는가")
s = arc_scene(150, pull=20, scale=1)            # 시퀀스 6 은 규모 4~5
N2.scenes = [s]
ok(has(gate.check(s, N2), "V015", "hard"), "150화에 일상 규모 -> 기각")
s = arc_scene(150, pull=20, scale=4)
N2.scenes = [s]
ok(not has(gate.check(s, N2), "V015"), "규모가 맞으면 통과")

print("[V016] 독자-인물 정보 격차가 살아 있는가 -- 연독률의 핵심")
eps = [arc_scene(ep, pull=-20, end=True, cliff="caught", sid=f"g{ep}")
       for ep in (10, 15, 20)]
N2.scenes = eps
ok(has(gate.check(eps[-1], N2), "V016", "hard"),
   "3회차 연속 아무도 아무것도 모르지 않으면 기각")
eps[0].world_ops = [{"event": "misbelieve", "who": "B", "term": "그 밤",
                     "believes": "다른 사람"}]
N2.scenes = eps
ok(not has(gate.check(eps[-1], N2), "V016", "hard"), "오해가 하나라도 살아 있으면 통과")

print("[V017] 클리프행어는 선언으로 -- 텍스트에서 추론하지 않는다")
s = arc_scene(20, pull=-20, end=True, cliff="눈이 마주쳤다")
N2.scenes = [s]
ok(has(gate.check(s, N2), "V017", "hard"), "5대 공식 밖의 값은 기각")
s = arc_scene(20, pull=-20, end=True, cliff="")
N2.scenes = [s]
ok(has(gate.check(s, N2), "V017", "soft"),
   "회차 끝에 없으면 soft  ← 매회 남발하면 양치기 소년이라 hard 로 막지 않는다")
s = arc_scene(20, pull=-20, end=True, cliff="before_crisis")
N2.scenes = [s]
ok(not has(gate.check(s, N2), "V017"), "유효한 공식이면 통과")

print("[거시] 회차 배분이 보고서와 맞는가")
ok(sum(arc.episodes_in(x["n"]) for x in arc.SEQUENCES) == 200, "8시퀀스 합계 200화")
ev = sum(x["events"][1] for x in arc.SEQUENCES)
ok(15 <= ev <= 21, f"사건 상한 합계 {ev}개 (보고서 15~20)")

print()
if fails:
    print(f"거시 관문: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("거시 관문: 진도·꺾임·규모·정보격차·클리프행어 -- 통과")


# ============================================================ 개연성 사슬 (V018)
print()
print("[V018] 플롯 구멍을 그래프 도달 가능성으로 잡는가")
from novel.episode import Beat, Outcome, Episode, assemble_backward   # noqa: E402
from novel import episode as EP                                       # noqa: E402

def chain_scenes(specs):
    out = []
    for i, (req, est) in enumerate(specs, 1):
        s = scene_fixture(id=f"c{i:02d}")
        s.requires, s.establishes = list(req), list(est)
        out.append(s)
    return out

N3 = novel_fixture(); N3.pov_character = "A"
N3.scenes = chain_scenes([([], ["열쇠를 얻는다"]),
                          (["열쇠를 얻는다"], ["문을 연다"]),
                          (["문을 연다"], [])])
ok(not any(v.rule == "V018" for s in N3.scenes for v in gate.check(s, N3)),
   "요구가 앞에서 전부 성립되면 통과")

N3.scenes = chain_scenes([([], ["문을 연다"]),
                          (["열쇠를 얻는다"], [])])
vs = [v for v in gate.check(N3.scenes[1], N3) if v.rule == "V018"]
ok(vs and vs[0].severity == "hard", "성립시키는 씬이 없으면 hard 로 구멍을 짚는다")
ok("개연성 구멍" in vs[0].detail, f"구멍이라고 말해준다: {vs[0].detail[:40]}...")

N3.scenes = chain_scenes([([], ["열쇠를 얻는다"]),
                          (["열쇠를  얻는다"], [])])          # 오타(공백 하나)
vs = [v for v in gate.check(N3.scenes[1], N3) if v.rule == "V018"]
ok(vs and vs[0].severity == "soft", "비슷한 것이 있으면 soft 로 낮추고 오타라고 짚는다")

print("[V018] state: 조건은 원장에 대고 판정한다")
N4 = novel_fixture(); N4.pov_character = "A"
N4.scenes = chain_scenes([([], []), (["state:rel:연인:와타나베,미도리"], [])])
N4.scenes[0].relation_ops = [{"op": "start", "kind": "연인",
                              "members": ["와타나베", "미도리"]}]
ok(not any(v.rule == "V018" for v in gate.check(N4.scenes[1], N4)),
   "원장에 관계가 살아 있으면 통과")
N4.scenes[0].relation_ops = []
ok(any(v.rule == "V018" for v in gate.check(N4.scenes[1], N4)),
   "원장이 만족하지 않으면 기각")

print("[역방향] 결말에서 거꾸로 쌓으면 쓰이지 않는 비트는 안 들어온다")
oc = Outcome("A 가 자리를 잃는다", requires=["비밀을 안다", "공개 자리가 있다"])
lib = [Beat("통화를 듣는다", requires=["같은 공간"], establishes=["비밀을 안다"]),
       Beat("같은 조가 된다", establishes=["같은 공간"]),
       Beat("발표회 공지", establishes=["공개 자리가 있다"]),
       Beat("아무도 안 쓰는 비트", establishes=["쓸모없음"])]
chain, left = assemble_backward(oc, entry=set(), library=lib)
ok(len(chain) == 3 and not left, f"4개 중 3개만 채택, 미충족 0 (얻은 값 {len(chain)}, {left})")
ok(all("아무도" not in b.beat for b in chain), "존재 이유 없는 비트는 배제된다")
ok(chain[0].beat == "같은 조가 된다", f"시간순으로 뒤집힌다 (첫 비트 {chain[0].beat!r})")
ok(not EP.check_causality(Episode(n=1, outcome=oc, beats=chain)),
   "조립된 사슬은 개연성 검사를 통과한다")

print()
if fails:
    print(f"개연성: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("개연성 사슬: 구멍 검출·오타 구분·원장 판정·역방향 조립 -- 통과")


# ============================================================ 문장 리듬 (V020)
print()
print("[V020] 문장 리듬 -- 셀 수 있는 것만 잡는다")

def prose_scene(text, sid="r1"):
    s = scene_fixture(id=sid)
    s.prose = text
    return s

MONO = ("나는 생각했다. 그는 말했다. 비가 시작했다. 나는 후회했다. "
        "그가 대답했다. 나는 침묵했다.")
N5 = novel_fixture(); N5.pov_character = "와타나베"
s = prose_scene(MONO); N5.scenes = [s]
vs = [v for v in gate.check(s, N5) if v.rule == "V020"]
ok(any(v.severity == "hard" and "연속" in v.detail for v in vs),
   "같은 종결('…했다')이 네 번 연속이면 hard")
DA = ("나는 창밖을 보았다. 비가 내렸다. 그는 말이 없었다. 잔이 비었다. "
      "나는 일어났다. 문이 닫혔다. 골목이 젖어 있었다.")
sd = prose_scene(DA, "r5"); N5.scenes = [sd]
vd = [v for v in gate.check(sd, N5) if v.rule == "V020"]
ok(any(v.severity == "soft" and "다' 로 끝나는" in v.detail for v in vd),
   "'-다' 일색은 soft -- 한국어 과거 서술은 원래 다로 끝난다")
ok(any(v.severity == "hard" and "비슷하다" in v.detail for v in vs),
   "문장 길이가 전부 비슷하면 hard")

VARIED = ("빗소리. 나는 창밖을 오래 바라보다가, 잔에 남은 얼음이 저 혼자 무너지는 소리를 "
          "듣고서야 고개를 돌렸다 — 그가 이미 자리를 뜬 뒤였다. "
          "테이블에는 물 자국만 링처럼 남아 있었다. 나는 그것을 손끝으로 문질렀다. "
          "지워지지 않았다. 지워질 리가 없었고, 나는 그 사실을 알면서도 한참을 문질렀는데, "
          "그러는 동안 카페의 음악이 두 번 바뀌었고 바깥은 조금 더 어두워졌다.")
s2 = prose_scene(VARIED, "r2"); N5.scenes = [s2]
vs2 = [v for v in gate.check(s2, N5) if v.rule == "V020"]
ok(not any(v.severity == "hard" for v in vs2),
   f"짧은·긴 문장과 대시·비유가 섞이면 통과 ({[v.detail[:28] for v in vs2]})")

print("[V020] 과잉 기각 방지")
s3 = prose_scene("짧다. 하나. 둘.", "r3"); N5.scenes = [s3]
ok(not [v for v in gate.check(s3, N5) if v.rule == "V020"],
   "문장이 5개 미만이면 판정하지 않는다 -- 표본이 없다")
DIALOG = ('"나는 늘 그랬어. 그랬다. 그랬다니까. 정말 그랬다." 그가 말했다. '
          + VARIED)
s4 = prose_scene(DIALOG, "r4"); N5.scenes = [s4]
ok(not any(v.severity == "hard" for v in gate.check(s4, N5) if v.rule == "V020"),
   "대사 안의 반복은 세지 않는다 -- 규칙은 서술에 거는 것이다")

print()
if fails:
    print(f"문장 리듬: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("문장 리듬: 종결 반복·길이 분산·만연체·대시·비유, 그리고 과잉 기각 방지 -- 통과")
