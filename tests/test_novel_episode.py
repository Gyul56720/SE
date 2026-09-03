"""에피소드 조립의 red-green -- 결말 하나가 회차들로 펴지는가.

검증하는 것은 문장이 아니라 **배선**이다: 척추가 역방향으로 서는가, establishes 가 틀리면
되돌려보내는가, 남는 칸이 서브플롯으로 채워지는가, 회차 번호와 클리프행어가 붙는가,
그리고 나온 씬들이 개연성 관문(V018)을 통과하는가.

LLM 은 가짜다. 실행: python3 tests/test_novel_episode.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel.world_romance import build                                 # noqa: E402
from novel import drive as D, gate                                    # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


SPEC = dict(seq=1, eps=(1, 5), scale=1,
            summary="설윤이 사람들 앞에서 공명을 감싸고 자기 자리를 잃는다",
            requires=["비밀을 안다", "공개 자리가 있다"],
            establishes=["설윤이 자리를 잃었다"], world_ops=[])

# 열린 조건을 하나씩 갚는 척추 비트 + 그 비트가 새로 여는 조건
SPINE = {
    "비밀을 안다": dict(beat="설윤이 공명의 통화를 듣는다", participants=["설윤"],
                    requires=["같은 공간에 있다"], establishes=["비밀을 안다"], scale=2,
                    direction={"staging": "연습동 3번방, 자정",
                               "trigger": "문이 덜 닫혀 있다",
                               "props": "식은 자판기 커피",
                               "camera": "설윤은 손만 본다. 표정은 못 본다",
                               "subtext": "둘 다 왜 여기 있는지 말하지 않는다",
                               "beat_arc": "pull -50 -> -35"}),
    "공개 자리가 있다": dict(beat="발표회가 공지된다", participants=["설윤", "정우"],
                       requires=[], establishes=["공개 자리가 있다"], scale=1),
    "같은 공간에 있다": dict(beat="둘이 같은 조로 묶인다", participants=["설윤", "공명"],
                      requires=[], establishes=["같은 공간에 있다"], scale=1),
}


class Fake:
    def __init__(self, wrong_first=False):
        self.prompts, self.wrong_first, self.used_wrong = [], wrong_first, False

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "서브플롯 한 씬" in prompt:
            return json.dumps({"beat": "정우가 오디션에서 떨어진다",
                               "participants": ["설윤", "정우"], "scale": 1,
                               "direction": {"staging": "복도 끝 게시판 앞",
                                             "props": "떼어낸 압정 자국"},
                               "world_ops": []}, ensure_ascii=False)
        if "갚아야 할 요구" in prompt:
            lo = prompt.index("[이 장면이 갚아야 할 요구]")
            conds = prompt[lo:prompt.index("\n", lo)]
            if self.wrong_first and not self.used_wrong:
                self.used_wrong = True
                return json.dumps({"beat": "엉뚱한 장면", "establishes": ["오타난 조건"],
                                   "requires": []}, ensure_ascii=False)
            for k, v in SPINE.items():
                if k in conds:
                    return json.dumps(v, ensure_ascii=False)
        if "산문만 출력한다" in prompt:
            return "조율되지 않은 현이 울렸다. 나는 창밖을 바라보았다."
        return json.dumps({"inner_thought": "", "action": "", "speech": "그렇구나",
                           "emotions": {"joy": 45, "melancholy": 40,
                                        "isolation": 40, "narrative_pull": -45}},
                          ensure_ascii=False)


print("[조립] 결말 하나가 회차들로 펴지는가")
from novel import arc                                                 # noqa: E402
n = build()
f = Fake()
scenes = D.build_episode(n, SPEC, llm=f)
eps = sorted({s.episode for s in scenes})
ok(eps == [1, 2, 3, 4, 5], f"5회차로 펴진다 ({eps})")
ok(len(scenes) == 5 * arc.SCENES_PER_EPISODE,
   f"회차마다 씬 {arc.SCENES_PER_EPISODE}개 (총 {len(scenes)})")
per_end = {e: sum(1 for s in scenes if s.episode == e and s.is_episode_end) for e in eps}
ok(all(v == 1 for v in per_end.values()),
   f"회차의 끝은 마지막 씬 하나뿐 ({per_end})  ← 전부 end 로 두면 V016/V017/V019 가 오작동")
ok(scenes[-1].cliffhanger, f"마지막에 클리프행어 ({scenes[-1].cliffhanger!r})")

print("[분량] 회차 = 척추 1 + 서브플롯 2 (보고서: 서브플롯이 2/3)")
main = [s for s in scenes if s.id.endswith("m")]
sub = [s for s in scenes if not s.id.endswith("m")]
ok(len(main) == 5 and len(sub) == 10,
   f"척추 {len(main)} / 서브플롯 {len(sub)} -- 서브플롯이 {len(sub)/len(scenes):.0%}")
ok(all(not s.establishes for s in sub), "서브플롯 씬은 인과에 얹히지 않는다")

print("[역방향] 척추가 시간순으로 뒤집혀 서는가")
spine = [s for s in scenes if s.establishes]
order = [s.establishes[0] for s in spine]
ok(order.index("같은 공간에 있다") < order.index("비밀을 안다"),
   f"'같은 공간' 이 '비밀을 안다' 보다 앞에 온다 ({order})")
ok(order[-1] == "설윤이 자리를 잃었다", "결말이 마지막")

print("[서브플롯] 남는 칸이 채워지고 인과에 얹히지 않는가")
filler = [s for s in scenes if not s.establishes]
ok(filler, f"서브플롯 {len(filler)}개가 끼어든다")
ok(all(not s.requires for s in filler), "서브플롯은 아무것도 요구하지 않는다")
ok(any("정우" in (s.directives[0] if s.directives else "") for s in filler),
   "조연의 이야기다")

print("[개연성] 나온 씬들이 V018 을 통과하는가")
n.scenes = scenes
holes = [v for s in scenes for v in gate.check(s, n)
         if v.rule == "V018" and v.severity == "hard"]
ok(not holes, f"개연성 구멍 0 (얻은 값 {[str(v)[:60] for v in holes]})")

print("[수리] establishes 가 조건과 다르면 되돌려보내는가")
n2 = build()
f2 = Fake(wrong_first=True)
scenes2 = D.build_episode(n2, SPEC, llm=f2)
retry = [p for p in f2.prompts if "직전 시도가 기각된 이유" in p]
ok(bool(retry), "틀린 establishes 에 되먹임이 나간다")
ok(any("문자열을 그대로 복사하라" in p for p in retry),
   "무엇을 고칠지 말해준다  ← 한 글자 차이가 개연성 구멍이 되는 자리")
ok(len({s.episode for s in scenes2}) == 5, "되돌려보낸 뒤에도 정상 조립된다")

print("[통합] 조립된 씬이 씬 루프까지 통과하는가")
n3 = build()
n3.scenes = D.build_episode(n3, SPEC, llm=Fake())
r = D.drive(n3, None, llm=Fake(), max_repairs=2, limit=2)
ok(r["verified"] >= 1, f"씬이 실제로 채워진다 ({r})")

print("[V019] 회차 분량이 목표에 못 미치면 잡는가")
n4 = build()
n4.scenes = D.build_episode(n4, SPEC, llm=Fake())
first = [s for s in n4.scenes if s.episode == 1]
for s in first:
    s.prose = "짧다." * 20                                   # 회차 합계 ~1,200자
end = next(s for s in first if s.is_episode_end)
vs = [v for v in gate.check(end, n4) if v.rule == "V019"]
ok(vs and vs[0].severity == "hard", f"목표의 70% 미만이면 hard ({vs[0].detail[:50] if vs else '못잡음'})")
ok(vs and "자 모자란다" in vs[0].detail, "몇 자 모자란지 숫자로 말해준다  ← '더 길게'는 지시가 아니다")
for s in first:
    s.prose = "가" * (arc.CHARS_PER_SCENE + 50)
ok(not [v for v in gate.check(end, n4) if v.rule == "V019"],
   "회차가 5,000자를 채우면 통과")
first[0].prose = ""
ok(not [v for v in gate.check(end, n4) if v.rule == "V019"],
   "아직 안 채워진 회차는 판정하지 않는다  ← 과잉 기각 방지")

print()
if fails:
    print(f"에피소드 조립: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("에피소드 조립: 역방향 척추 · 서브플롯 · 회차 번호 · 클리프행어 · 개연성 · 수리 -- 통과")
