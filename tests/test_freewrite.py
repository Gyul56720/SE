"""자유 집필 -- 화자가 **회차를 통째로** 쓴다.

씬 단위 집필은 화자에게 "이 씬을 1,666자로 쓰라" 고 시킨다. 그건 분량 할당량이고, 할당량은
곧 희석 지시다 -- 채우라고 하면 채운다(README 5번). 회차를 통째로 주면 화자가 어디를
늘리고 어디를 자를지 스스로 정하고, 점층과 전환(문장론 3·4번)도 씬 경계에 잘리지 않는다.

호출도 회차당 18(씬 3 x (배우 4 + 화자 1 + 보충))에서 2~3으로 준다.

여기서 고정하는 것: 표식으로 갈리는가 · 표식이 없어도 원고를 잃지 않는가 · 회차 분량을
코드가 채우는가 · 관문이 여전히 도는가 · 씬 단위 모드가 그대로인가.

실행: python3 tests/test_freewrite.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D, arc                                     # noqa: E402
from novel.state import Novel, Character, Scene                       # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def world(n_scenes=3, ep=1):
    nv = Novel(title="시험", pov_character="A",
               characters=[Character("A", "화자"), Character("공명", "동기")],
               facts={"secrets": {"공명의 비밀번호": {"knows": ["공명"], "aliases": []}}})
    nv.scenes = [Scene(id=f"ep{ep:03d}_{i}", episode=ep, location=f"장소{i}",
                       punctum=f"감각{i}", participants=["A", "공명"],
                       kind="cider", directives=["무언가 일어난다"])
                 for i in range(n_scenes)]
    nv.scenes[-1].is_episode_end = True
    return nv


BODY = "나는 문을 열었다. 비가 오고 있었다. 아, 또 여긴가 하고 생각했다. " * 40


def marked(n=3, body=BODY):
    return "\n\n".join(f"{D.FREE_MARK}{i}\n{body}" for i in range(1, n + 1))


print("[표식] 회차 산문을 씬별로 가르는가")
parts = D.split_episode(marked(3), 3)
ok(len(parts) == 3, f"셋으로 갈린다 ({len(parts)})")
ok(all(p.strip() for p in parts), "빈 조각이 없다")
ok(D.FREE_MARK not in parts[0], "표식은 본문에 안 남는다")

print("[표식] 표식이 없거나 모자라도 원고를 잃지 않는가")
print("      ← 모델이 표식을 빠뜨리는 일은 반드시 생긴다. 통째로 버리면 회차가 날아간다")
parts2 = D.split_episode("표식 없는 긴 산문. " * 100, 3)
ok(len(parts2) == 3, f"길이로라도 셋으로 나눈다 ({len(parts2)})")
ok(all(p.strip() for p in parts2), "조각이 다 차 있다")
parts3 = D.split_episode(marked(2), 3)
ok(len(parts3) == 3, f"표식이 모자라도 셋을 채운다 ({len(parts3)})")

print()
print("[집필] 회차를 한 번에 쓰고 씬에 나눠 담는가")


class Once:
    """회차 프롬프트에 한 번 답하고, 모자라면 이어쓰기에 답한다."""

    def __init__(self, body=BODY):
        self.body, self.calls, self.kinds = body, 0, []

    def __call__(self, prompt):
        self.calls += 1
        if "이어서 계속 써라" in prompt:
            self.kinds.append("fill")
            return "이어지는 산문. " * 200
        self.kinds.append("episode")
        return marked(3, self.body)


nv = world()
llm = Once()
r = D.write_episode(nv, nv.scenes, llm)
ok(r["status"] == "verified", f"통과한다 ({r['status']} {r.get('violations')})")
ok(all(sc.prose for sc in nv.scenes), "세 씬에 산문이 담긴다")
ok(llm.kinds[0] == "episode", "회차 프롬프트로 한 번에 받는다")
ok(llm.calls <= 3, f"호출이 적다 ({llm.calls}회)  ← 씬 단위는 회차당 18회다")

print("[분량] 회차 분량을 코드가 채우는가  ← 지시로는 안 지켜진다")
ok(r["chars"] >= arc.CHARS_PER_EPISODE * D.PROSE_MIN_RATIO,
   f"{r['chars']:,}자 (목표 {arc.CHARS_PER_EPISODE:,})")
short = world()
s_llm = Once(body="짧다. " * 10)
r2 = D.write_episode(short, short.scenes, s_llm)
ok("fill" in s_llm.kinds, "모자라면 이어쓰기를 부른다")
ok(len(short.scenes[-1].prose) > len(short.scenes[0].prose),
   "**마지막 씬에** 이어 쓴다  ← 중간을 부풀리면 이어놓은 흐름이 끊긴다")

print("[관문] 산문 관문은 그대로 도는가")
bad = world()
b_llm = Once(body="공명의 비밀번호가 적혀 있었다. " * 30)      # V008 지식 누출
rb = D.write_episode(bad, bad.scenes, b_llm)
ok(rb["status"] == "failed", f"기각한다 ({rb['status']})")
ok(any("V008" in v for v in rb["violations"]), f"어느 관문인지 남는다 ({rb['violations'][:1]})")
ok(all(sc.status == "failed" for sc in bad.scenes), "회차 전체가 failed 로 표시된다")

print()
print("[루프] drive(freewrite=True) 가 회차 단위로 도는가")
d = Path(tempfile.mkdtemp())
nv3 = world()
nv3.scenes += [Scene(id="ep002_0", episode=2, location="x", punctum="y",
                     participants=["A"], kind="cider", is_episode_end=True)]
res = D.drive(nv3, str(d / "n.json"), llm=Once(), freewrite=True)
ok(res["status"] == "done", f"두 회차 모두 통과 ({res})")
ok(res["verified"] == 2, f"회차 수로 센다 ({res['verified']})  ← 씬 수가 아니다")
ok((d / "n.json").exists(), "회차마다 저장한다")

print("[루프] upto_episode 로 자르는가")
nv4 = world()
nv4.scenes += [Scene(id="ep002_0", episode=2, location="x", punctum="y",
                     participants=["A"], kind="cider", is_episode_end=True)]
res2 = D.drive(nv4, None, llm=Once(), freewrite=True, upto_episode=1)
ok(res2["verified"] == 1, f"1화만 쓴다 ({res2['verified']})")
ok(not nv4.scenes[-1].prose, "2화는 손대지 않는다")

print("[기본] 씬 단위 모드는 그대로인가  ← 자유 집필은 기본값이 아니다")
nv5 = world(2)
turn_llm_calls = []


class SceneFake:
    def __call__(self, prompt):
        turn_llm_calls.append("prose" if "산문만 출력한다" in prompt else "other")
        if "이어서 계속 써라" in prompt:
            return "이어지는 산문. " * 200
        if "산문만 출력한다" in prompt:
            return "나는 문을 열었다. 비가 왔다."
        return '{"inner_thought": "", "action": "", "speech": "응", "emotions": {}}'


D.drive(nv5, None, llm=SceneFake(), limit=1)
ok(any(k == "other" for k in turn_llm_calls),
   "씬 모드에서는 배우 턴을 받는다  ← 두 모드가 섞이지 않는다")

print("[절단] 회차 끝을 끊으라고 지시하는가  ← 지정 안 하면 모델은 해소로 닫는다")
nvz = world()
nvz.scenes[-1].cliffhanger = "caught"
pz = D.episode_prompt(nvz, nvz.scenes, arc.CHARS_PER_EPISODE)
ok("절단면" in pz and "해소하지 마라" in pz, "마지막 씬이 절단면이라고 못박는다")
ok("목격당하는" in pz, "디렉터가 고른 공식을 그대로 준다")
nvw = world()
pw = D.episode_prompt(nvw, nvw.scenes, arc.CHARS_PER_EPISODE)
ok("절단 공식 다섯 중 하나" in pw and pw.count("·") >= 5,
   "공식이 없으면 다섯을 다 보여주고 고르게 한다")
# [엔딩] 을 [끊기] 로 줄였다 -- 회차가 없는 모드에 "다음 화에서 답할 질문" 을
# 시키고 있었다. 끊는 자리와 마지막 문장 규율만 남긴다.
ok("[끊기]" in pz, "끊는 자리 규율이 함께 실린다")
ok("마지막 문장은 짧게" in pz, "마지막 문장을 짧게 끊으라고 한다")
ok("읽는 사람이 대신 느낀다" in pz, "화자의 감정을 쓰지 말라고 한다")

print("[분량] 회차 목표가 6,000자인가")
ok(arc.CHARS_PER_EPISODE == 6000, f"{arc.CHARS_PER_EPISODE:,}자")
ok(f"{arc.CHARS_PER_EPISODE}자 안팎" in pz, "프롬프트에 그 숫자가 실린다")

print()
if fails:
    print(f"자유 집필: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("자유 집필: 표식 분할 · 안전망 · 분량 · 관문 · 회차 루프 · 기본 모드 보존 -- 통과")
