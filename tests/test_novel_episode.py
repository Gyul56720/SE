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


def _md(b: dict, cond: str, clock: float = 9) -> str:
    """SPINE 항목을 **디렉터가 낼 법한 Markdown 시나리오**로 만든다.

    디렉터는 이제 JSON 이 아니라 Markdown 을 낸다(형식 세금 면제). 가짜 LLM 도 같은
    계약을 지켜야 한다 -- JSON 을 돌려주면 추출 단계를 건너뛴 채 통과해서, 실제로는
    깨진 배선이 초록으로 보인다."""
    d = b.get("direction") or {}
    return (f"## 장면\n{b['beat']}\n\n"
            f"## 성립시키는 조건\n{cond}\n\n"
            f"## 선행 조건\n{', '.join(b.get('requires') or []) or '없음'}\n\n"
            f"## 등장인물\n{', '.join(b.get('participants') or ['설윤'])}\n\n"
            f"## 공간\n{d.get('staging', '연습동 3번방, 자정')}\n\n"
            f"## 여는 사건\n{d.get('trigger', '문이 덜 닫혀 있다')}\n\n"
            f"## 장치\n{d.get('props', '식은 자판기 커피')}\n\n"
            f"## 화자의 시야\n{d.get('camera', '설윤은 손만 본다')}\n\n"
            f"## 말하지 않는 것\n{d.get('subtext', '둘 다 삼킨다')}\n\n"
            f"## 감정 이동\n{d.get('beat_arc', 'pull -50 -> -35')}\n\n"
            # 새 계약(2026-09-04): 누가 움직였고 무엇을 잃었고 시계가 얼마나 남았는가.
            # 조립 단계가 이 셋을 강제하므로 가짜도 지켜야 한다 -- 안 지키면 비트가
            # 되돌려보내져 척추가 서지 않는다(실측으로 그렇게 깨졌다).
            f"## 움직이는 사람\n{b.get('driver', '설윤')}\n\n"
            f"## 치른 대가\n{b.get('cost', '정우에게 빚을 졌다')}\n\n"
            f"## 남은 시간\n{clock}")


def _section(md: str, head: str) -> str:
    """Markdown 에서 '## head' 아래 첫 줄. 추출기가 하는 일의 최소판이다."""
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and head in ln:
            for nxt in lines[i + 1:]:
                if nxt.strip():
                    return nxt.strip()
    return ""


class Fake:
    """두 단계 계약을 흉내낸다: 디렉터는 Markdown, 추출기는 JSON.

    프롬프트를 표식으로 갈라 어느 단계인지 알아본다. 표식이 실제 프롬프트와 어긋나면
    이 가짜가 조용히 엉뚱한 분기로 빠지므로, 아래 stages 로 각 단계가 실제로 불렸는지
    센다 -- 안 세면 '한 단계도 안 탔는데 통과'가 가능하다."""

    def __init__(self, wrong_first=False):
        self.prompts, self.wrong_first, self.used_wrong = [], wrong_first, False
        self.stages = {"director": 0, "extractor": 0, "subplot": 0}
        self.clock = 13.0          # 결말이 준 14 보다 작게 시작해서 계속 줄인다

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "서브플롯 한 씬" in prompt:               # 서브플롯도 창작이다 -> Markdown
            self.stages["subplot"] += 1
            return ("## 장면\n정우가 오디션에서 떨어진다\n\n"
                    "## 등장인물\n설윤, 정우\n\n"
                    "## 공간\n복도 끝 게시판 앞\n\n"
                    "## 여는 사건\n정우가 명단에서 눈을 뗀다\n\n"
                    "## 장치\n떼어낸 압정 자국\n\n"
                    "## 화자의 시야\n설윤은 정우의 등만 본다\n\n"
                    "## 말하지 않는 것\n정우는 축하한다는 말을 삼킨다\n\n"
                    "## 움직이는 사람\n정우\n\n"
                    "## 치른 대가\n없음\n\n"
                    "## 남은 시간\n8")

        if "<Task_Objective>" in prompt:                    # 1단계: 창작 -> Markdown
            self.stages["director"] += 1
            conds = prompt.split("<Task_Objective>")[1].split("</Task_Objective>")[0]
            self.clock = max(0.5, self.clock - 1)
            if self.wrong_first and not self.used_wrong:
                self.used_wrong = True
                return _md({"beat": "엉뚱한 장면", "participants": ["설윤"]},
                           "오타난 조건", self.clock)
            for k, v in SPINE.items():
                if k in conds:
                    return _md(v, k, self.clock)
            return _md({"beat": "빈 장면", "participants": ["설윤"]}, "", self.clock)

        if "--- 시나리오 ---" in prompt:                     # 2단계: 추출 -> JSON
            self.stages["extractor"] += 1
            sc = prompt.split("--- 시나리오 ---")[1].split("--- 끝 ---")[0]
            cond = _section(sc, "성립시키는 조건")
            v = SPINE.get(cond)
            extra = {"driver": _section(sc, "움직이는 사람"),
                     "cost": _section(sc, "치른 대가"),
                     "deadline_hours": float(_section(sc, "남은 시간") or 0)}
            if v:
                return json.dumps(dict(v, establishes=[cond], **extra),
                                  ensure_ascii=False)
            return json.dumps({"beat": _section(sc, "장면"),
                               "participants": [x.strip() for x in
                                                _section(sc, "등장인물").split(",") if x.strip()],
                               "requires": [], **extra,
                               "establishes": [cond] if cond else [],
                               "direction": {"staging": _section(sc, "공간"),
                                             "trigger": _section(sc, "여는 사건"),
                                             "props": _section(sc, "장치"),
                                             "camera": _section(sc, "화자의 시야"),
                                             "subtext": _section(sc, "말하지 않는 것")}},
                              ensure_ascii=False)

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

print("[2단계] 창작(Markdown)과 추출(JSON)이 실제로 갈려 있는가")
ok(f.stages["director"] and f.stages["extractor"],
   f"두 단계가 모두 불린다 ({f.stages})")
ok(f.stages["director"] + f.stages["subplot"] == f.stages["extractor"],
   f"창작 한 번에 추출 한 번 ({f.stages})  ← 어긋나면 한쪽이 JSON 을 직접 받고 있다는 뜻이고,\n"
   "         그 프롬프트는 형식 세금을 그대로 문다")
dp = next(p for p in f.prompts if "<Task_Objective>" in p)
ok("JSON 도 XML 도 쓰지 마라" in dp, "디렉터에게는 JSON 을 금지한다  ← 형식 세금 면제")
ok("<System_Persona>" in dp and "<World>" in dp, "입력은 XML 로 구역이 갈려 있다")
with_sc = [s for s in scenes if s.direction.get("scenario", "").startswith("## 장면")]
ok(len(with_sc) == len(scenes) - 1,
   f"결말을 뺀 모든 씬이 시나리오 원문을 싣는다 ({len(with_sc)}/{len(scenes) - 1})\n"
   "         ← 아래층(배우/화자)이 실제로 받는 것이 이것이다. 서브플롯이 빠지면 2/3가 맨몸이다")

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
