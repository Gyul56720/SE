"""분량 -- 회차가 5,000자로 나오는가. **지시가 아니라 코드가 센다.**

사용자 실측: "5000자 내외 <- 이거 근데 글자 수가 실제 측정보다 많이 작게 나와.
3000자 내외로 나오더라." 원인은 지시의 형태다. 화자 프롬프트는 계속 "공백 포함 1,667자
안팎" 이라고 말하고 있었지만 그건 모델이 지킬 수 있는 형태가 아니다. 관문 V019 는 회차가
다 찬 뒤에야 hard 를 냈는데, 그때는 수리 루프가 이미 지나간 씬을 다시 쓰지 못한다.

그래서 씬을 쓰는 자리로 옮겼다: 코드가 길이를 재고, 모자란 만큼을 **숫자로** 돌려주고,
다시 쓰는 것이 아니라 **이어서** 쓰게 한다.

실행: python3 tests/test_length.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D, arc                                     # noqa: E402
from novel.state import Scene                                         # noqa: E402
from novel.world_romance import build                                 # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


N = build()
TARGET = arc.CHARS_PER_SCENE


def scene(text=""):
    s = Scene(id="s1", episode=1, kind="routine", location="주방", punctum="식은 커피")
    s.prose = text
    return s


class Adder:
    """부르는 만큼 이어서 주는 가짜 화자. 한 번에 목표를 다 채우지 않는다 --
    실제 모델이 그렇다."""

    def __init__(self, chunk=400):
        self.chunk, self.calls = chunk, 0

    def __call__(self, prompt):
        self.calls += 1
        return "가" * self.chunk


print("[분량] 모자라면 이어 쓴다")
s = scene("나" * 500)
a = Adder(700)
got = D.fill_prose(N, s, a, TARGET)
ok(got >= TARGET * D.PROSE_MIN_RATIO,
   f"목표의 95% 이상까지 채운다 ({got} / 목표 {TARGET})")
ok(a.calls >= 2, f"한 번으로 안 되면 여러 번 부른다 ({a.calls}회)")
ok(s.prose.startswith("나"), "앞부분을 지우지 않는다  ← 다시 쓰기가 아니라 이어쓰기다")

print("[분량] 이미 찼으면 부르지 않는다  ← 과잉 호출 방지")
s2 = scene("다" * TARGET)
a2 = Adder()
D.fill_prose(N, s2, a2, TARGET)
ok(a2.calls == 0, f"호출 0회 ({a2.calls})")

print("[분량] 상한이 있다  ← 빈 응답에 영원히 매달리지 않는다")
s3 = scene("라" * 100)
a3 = Adder(10)                                   # 매번 10자만 준다 = 사실상 빈 응답
D.fill_prose(N, s3, a3, TARGET)
ok(a3.calls == 1, f"빈 응답이 오면 한 번에 멈춘다 ({a3.calls}회)")

s4 = scene("마" * 100)
a4 = Adder(60)                                   # 조금씩 주지만 목표엔 못 미친다
D.fill_prose(N, s4, a4, TARGET)
ok(a4.calls == D.PROSE_EXTEND_TRIES,
   f"시도 상한 {D.PROSE_EXTEND_TRIES}회에서 멈춘다 ({a4.calls}회)  ← 밤을 여기 태우지 않는다")

print("[프롬프트] 모자란 자수를 숫자로 준다  ← '더 길게' 는 지시가 아니다")
p = D.extend_prompt(N, scene("바" * 600), 1067)
ok("1067자 이상 더 써라" in p, "몇 자 모자란지 말해준다")
ok("새 사건을 만들지 마라" in p,
   "사건이 아니라 루틴·독백·딴 이야기로 채우게 한다  ← 늘리라고 하면 플롯이 부푼다")
ok("이어서 계속 써라" in p, "다시 쓰기가 아니라 이어쓰기")
ok("건조한" in p and "느낌표" in p, "문체 규율이 이어쓰기에도 실린다")

print("[회차] 씬 셋이 5,000자를 만드는가")
ok(arc.CHARS_PER_SCENE * arc.SCENES_PER_EPISODE >= arc.CHARS_PER_EPISODE - 3,
   f"{arc.CHARS_PER_SCENE}자 x {arc.SCENES_PER_EPISODE}씬 = "
   f"{arc.CHARS_PER_SCENE * arc.SCENES_PER_EPISODE}자 (목표 {arc.CHARS_PER_EPISODE})")

print()
if fails:
    print(f"분량: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("분량: 이어쓰기 · 과잉 호출 방지 · 시도 상한 · 숫자 되먹임 -- 통과")
