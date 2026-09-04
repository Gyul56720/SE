"""씬 루프의 red-green -- **관문 위반이 실제로 수리로 이어지는가.**

LLM 은 가짜다. 네트워크·쿼터 없이 매번 같은 결과가 나오고, 검증하는 것은 문장의 품질이
아니라 **루프의 배선**이다: 위반이 프롬프트에 실리는가, 고친 뒤 통과하는가, 한도를 넘으면
사실대로 실패하는가, 죽었다 다시 시작하면 verified 씬을 건너뛰는가.

실행: python3 tests/test_novel_drive.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel.state import Novel, Character, Scene            # noqa: E402
from novel import drive as D                               # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def world():
    return Novel(title="시험", pov_character="A",
                 characters=[Character("A", "화자"),
                             Character("B", "동기", emotion_envelope={"joy": 40})],
                 # 화자가 모르는 비밀 하나. 산문이 이것을 언급하면 V008 이 hard 로 잡는다.
                 facts={"secrets": {"B의 비밀번호": {"knows": ["B"], "aliases": []}}},
                 scenes=[Scene(id="s01", location="카페", punctum="그라인더 소리",
                               participants=["A", "B"], directives=["둘이 말하지 않는다"])])


GOOD_TURN = {"inner_thought": "무슨 말을 해야 할까", "action": "잔을 돌리며",
             "speech": "그렇구나", "emotions": {"joy": 45, "melancholy": 40,
                                              "isolation": 40, "narrative_pull": 0}}
GOOD_PROSE = "그라인더 소리가 멎었다. 나는 잔을 돌리며 창밖을 바라보았다."
# 분량 보충(fill_prose)이 이어쓰기로 받는 것. 한 번에 목표를 넘겨 루프가 한 번에 끝난다.
FILLER = "물을 올렸다. 레코드를 골랐다. 창밖은 아직 밝았다. " * 60
BAD_PROSE = "B의 비밀번호가 적혀 있었다. 잔이 식어 있었다."   # V008 지식 누출


class Fake:
    """단계를 알아보고 정해진 응답을 낸다. prose_seq 로 산문을 순서대로 바꿔 끼운다."""

    def __init__(self, prose_seq, joy=45):
        self.prose_seq, self.joy = list(prose_seq), joy
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "이어서 계속 써라" in prompt:          # 분량 보충 단계
            return FILLER
        if "산문만 출력한다" in prompt:
            return self.prose_seq.pop(0) if self.prose_seq else GOOD_PROSE
        t = dict(GOOD_TURN)
        t["emotions"] = dict(GOOD_TURN["emotions"], joy=self.joy)
        return json.dumps(t, ensure_ascii=False)


print("[GREEN] 깨끗한 씬은 한 번에 통과한다")
n = world(); f = Fake([GOOD_PROSE])
r = D.run_scene(n, n.scenes[0], f)
ok(r["status"] == "verified", f"verified ({r})")
ok(r["attempts"] == 1, "시도 1회")
ok(bool(n.scenes[0].prose), "산문이 채워진다")

print("[RED->GREEN] 산문이 관문에 걸리면 다시 쓰고, 위반이 프롬프트에 실린다")
n = world(); f = Fake([BAD_PROSE, GOOD_PROSE])
r = D.run_scene(n, n.scenes[0], f)
ok(r["status"] == "verified", f"두 번째 시도에서 통과 ({r['status']})")
ok(r["attempts"] == 2, f"시도 2회 (얻은 값 {r['attempts']})")
retry = [p for p in f.prompts if "직전 시도가 기각된 이유" in p]
ok(bool(retry), "재시도 프롬프트에 되먹임 문단이 들어간다")
ok(any("V008" in p for p in retry),
   "어느 규칙이 깨졌는지가 프롬프트에 실린다")
ok(any("reveal" in p or "모른다" in p for p in retry),
   "어떻게 고칠지도 실린다  ← (bool,str) 로는 못 하는 일")

print("[한도] 계속 실패하면 사실대로 failed 를 낸다")
n = world(); f = Fake([BAD_PROSE] * 10)
r = D.run_scene(n, n.scenes[0], f, max_repairs=2)
ok(r["status"] == "failed", "failed 로 끝난다")
ok(n.scenes[0].status == "failed", "씬 상태가 failed")
ok(len(n.scenes[0].attempts) >= 2, f"시도 이력이 남는다 ({len(n.scenes[0].attempts)}건)")
ok("violations" in r and r["violations"], "무엇이 막았는지 반환에 남는다")

print("[봉투] 어두운 씬 **하나**는 통과한다 -- 봉투는 회차 단위로 본다")
print("      ← 씬마다 물었더니 V003 이 25회로 되돌려보내기 1위였고 집필 시간의 100%가")
print("        수리에 버려졌다(2026-09-04 탐침). 새벽 편의점 장면에 joy 40 을 요구하면")
print("        인물이 이상해진다 -- 봉투의 의도는 아크의 성질이지 씬의 성질이 아니었다.")
n = world(); f = Fake([GOOD_PROSE] * 10, joy=5)
r = D.run_scene(n, n.scenes[0], f, max_repairs=1)
ok(r["status"] == "verified",
   f"가라앉은 씬 하나로는 기각하지 않는다 ({r['status']})")
ok(not any("V003" in v for v in (r.get("violations") or [])),
   "V003 hard 가 나오지 않는다")
print("      (연속 회차로 가라앉는 것은 여전히 잡는다 -- test_novel_gate 의 [V003 봉투])")

print("[단계 수리] 산문만 틀리면 배우 턴을 다시 만들지 않는가")
print("      ← 실측 2026-09-04: 씬 하나가 24호출(6 x 4시도) · 2.3분. 호출은 5.8초로")
print("        빠른데 횟수가 문제였다. 산문 규칙 하나 때문에 배우 턴 넷을 새로 받았다.")


class Counting:
    """단계별 호출 수를 센다. 산문은 처음 두 번 관문에 걸리게 만든다."""

    def __init__(self):
        self.n = {"director": 0, "actor": 0, "narrator": 0, "filler": 0}
        self.prose_calls = 0

    def __call__(self, prompt):
        if "이어서 계속 써라" in prompt:
            self.n["filler"] += 1                 # 분량 보충은 수리와 다른 단계다
            return FILLER
        if "산문만 출력한다" in prompt:
            self.n["narrator"] += 1
            self.prose_calls += 1
            return BAD_PROSE if self.prose_calls <= 2 else GOOD_PROSE
        if "location" in prompt and "punctum" in prompt:
            self.n["director"] += 1
            return json.dumps({"location": "복도", "punctum": "빗소리",
                               "directives": ["x"], "scale": 1}, ensure_ascii=False)
        self.n["actor"] += 1
        return json.dumps(GOOD_TURN, ensure_ascii=False)


n = world(); c = Counting()
r = D.run_scene(n, n.scenes[0], c, max_repairs=3)
ok(r["status"] == "verified", f"결국 통과한다 ({r['status']})")
ok(c.n["narrator"] == 3, f"화자는 세 번 불린다 ({c.n['narrator']})  ← 두 번 걸리고 세 번째 통과")
# 시도 1: 턴 4 + 산문 1 (산문 걸림)
# 시도 2: **턴 재사용** + 산문 1 (또 걸림 -- 두 번 연속이므로 다음엔 턴도 다시)
# 시도 3: 턴 4 + 산문 1 (통과)
ok(c.n["actor"] == 8,
   f"배우 8회 ({c.n['actor']})  ← 시도 2에서 턴을 재사용했다. 예전 구조는 12회다")
ok(c.n["director"] == 0,
   f"디렉터는 안 불린다 ({c.n['director']})  ← 이 씬은 location 이 이미 차 있다")
prose_only = [a for a in n.scenes[0].attempts if a.get("stage") == "prose"]
ok(len(prose_only) == 2, f"산문 단계에서 두 번 막혔다 ({len(prose_only)})")
ok(c.n["filler"] == 1,
   f"분량 보충은 한 번 ({c.n['filler']})  ← **관문을 통과한 뒤에만** 채운다. "
   f"기각될 산문에 이어쓰기를 붙이면 그 호출이 통째로 버려진다")
ok(sum(c.n.values()) - c.n["filler"] == 11,
   f"수리 루프는 총 11회 ({sum(c.n.values()) - c.n['filler']})  ← 예전 구조는 15회(5x3)였다.\n"
   "         실패가 산문에만 몰릴수록 절약이 커진다: 4시도면 24 -> 9회")

print("[영속] 씬마다 저장하고, 재개하면 verified 를 건너뛴다")
d = Path(tempfile.mkdtemp()); path = d / "novel.json"
n = world()
n.scenes.append(Scene(id="s02", location="계단", punctum="빗소리",
                      participants=["A", "B"], directives=["두 번째"]))
res = D.drive(n, str(path), llm=Fake([GOOD_PROSE] * 10), log=d / "log.jsonl")
ok(res["verified"] == 2 and res["remaining"] == 0, f"두 씬 모두 통과 ({res})")
ok(path.exists(), "파일로 저장된다")

reloaded = Novel.load(path)
ok(all(s.status == "verified" for s in reloaded.scenes), "상태가 살아남는다")
ok(reloaded.next_pending() is None, "재개 시 남은 씬이 없다")

n2 = Novel.load(path)
n2.scenes.append(Scene(id="s03", location="빈 사무실", punctum="사각형 자국",
                       participants=["A", "B"], directives=["세 번째"]))
counter = Fake([GOOD_PROSE] * 10)
res2 = D.drive(n2, str(path), llm=counter, log=d / "log.jsonl")
ok(res2["verified"] == 1, f"새 씬 하나만 돈다 -- verified 는 건너뛴다 ({res2})")

print("[기록] scenes.jsonl 에 씬마다 한 줄")
lines = [json.loads(x) for x in (d / "log.jsonl").read_text(encoding="utf-8").splitlines()]
ok(lines[0]["event"] == "start" and lines[-1]["event"] == "end", "start/end 로 감싼다")
ok(sum(1 for r in lines if r["event"] == "scene") == 3, "씬 3개가 기록된다")

print()
if fails:
    print(f"씬 루프: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("씬 루프: 통과·수리·한도·봉투·영속·재개·기록 -- 통과")
