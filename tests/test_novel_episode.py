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
            summary="서리가 사람들 앞에서 도경을 감싸고 자기 자리를 잃는다",
            requires=["비밀을 안다", "공개 자리가 있다"],
            establishes=["서리가 자리를 잃었다"], world_ops=[])

# 열린 조건을 하나씩 갚는 척추 비트 + 그 비트가 새로 여는 조건
SPINE = {
    "비밀을 안다": dict(beat="서리가 도경의 통화를 듣는다", participants=["서리"],
                    requires=["같은 공간에 있다"], establishes=["비밀을 안다"], scale=2),
    "공개 자리가 있다": dict(beat="발표회가 공지된다", participants=["서리", "주하"],
                       requires=[], establishes=["공개 자리가 있다"], scale=1),
    "같은 공간에 있다": dict(beat="둘이 같은 조로 묶인다", participants=["서리", "도경"],
                      requires=[], establishes=["같은 공간에 있다"], scale=1),
}


class Fake:
    def __init__(self, wrong_first=False):
        self.prompts, self.wrong_first, self.used_wrong = [], wrong_first, False

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "서브플롯 한 회차" in prompt:
            return json.dumps({"beat": "주하가 오디션에서 떨어진다",
                               "participants": ["서리", "주하"], "scale": 1,
                               "world_ops": []}, ensure_ascii=False)
        if "아직 성립되지 않은 조건" in prompt:
            lo = prompt.index("[아직 성립되지 않은 조건]")
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
n = build()
f = Fake()
scenes = D.build_episode(n, SPEC, llm=f)
ok(len(scenes) == 5, f"5회차로 펴진다 (얻은 값 {len(scenes)})")
ok([s.episode for s in scenes] == [1, 2, 3, 4, 5],
   f"회차 번호가 붙는다 ({[s.episode for s in scenes]})")
ok(scenes[-1].cliffhanger, f"마지막에 클리프행어 ({scenes[-1].cliffhanger!r})")

print("[역방향] 척추가 시간순으로 뒤집혀 서는가")
spine = [s for s in scenes if s.establishes]
order = [s.establishes[0] for s in spine]
ok(order.index("같은 공간에 있다") < order.index("비밀을 안다"),
   f"'같은 공간' 이 '비밀을 안다' 보다 앞에 온다 ({order})")
ok(order[-1] == "서리가 자리를 잃었다", "결말이 마지막")

print("[서브플롯] 남는 칸이 채워지고 인과에 얹히지 않는가")
filler = [s for s in scenes if not s.establishes]
ok(filler, f"서브플롯 {len(filler)}개가 끼어든다")
ok(all(not s.requires for s in filler), "서브플롯은 아무것도 요구하지 않는다")
ok(any("주하" in (s.directives[0] if s.directives else "") for s in filler),
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
ok(len(scenes2) == 5, "되돌려보낸 뒤에도 정상 조립된다")

print("[통합] 조립된 씬이 씬 루프까지 통과하는가")
n3 = build()
n3.scenes = D.build_episode(n3, SPEC, llm=Fake())
r = D.drive(n3, None, llm=Fake(), max_repairs=2, limit=2)
ok(r["verified"] >= 1, f"씬이 실제로 채워진다 ({r})")

print()
if fails:
    print(f"에피소드 조립: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("에피소드 조립: 역방향 척추 · 서브플롯 · 회차 번호 · 클리프행어 · 개연성 · 수리 -- 통과")
