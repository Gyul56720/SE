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
                 scenes=[Scene(id="s01", location="카페", punctum="그라인더 소리",
                               participants=["A", "B"], directives=["둘이 말하지 않는다"])])


GOOD_TURN = {"inner_thought": "무슨 말을 해야 할까", "action": "잔을 돌리며",
             "speech": "그렇구나", "emotions": {"joy": 45, "melancholy": 40,
                                              "isolation": 40, "narrative_pull": 0}}
GOOD_PROSE = "그라인더 소리가 멎었다. 나는 잔을 돌리며 창밖을 바라보았다."
BAD_PROSE = "B는 깊이 후회했다. 나는 슬펐다. 그리고 외로웠다. 무척 우울했다."


class Fake:
    """단계를 알아보고 정해진 응답을 낸다. prose_seq 로 산문을 순서대로 바꿔 끼운다."""

    def __init__(self, prose_seq, joy=45):
        self.prose_seq, self.joy = list(prose_seq), joy
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
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
ok(any("V004" in p or "V005" in p for p in retry),
   "어느 규칙이 깨졌는지가 프롬프트에 실린다")
ok(any("화자의 관찰" in p or "푼크툼" in p for p in retry),
   "어떻게 고칠지도 실린다  ← (bool,str) 로는 못 하는 일")

print("[한도] 계속 실패하면 사실대로 failed 를 낸다")
n = world(); f = Fake([BAD_PROSE] * 10)
r = D.run_scene(n, n.scenes[0], f, max_repairs=2)
ok(r["status"] == "failed", "failed 로 끝난다")
ok(n.scenes[0].status == "failed", "씬 상태가 failed")
ok(len(n.scenes[0].attempts) >= 2, f"시도 이력이 남는다 ({len(n.scenes[0].attempts)}건)")
ok("violations" in r and r["violations"], "무엇이 막았는지 반환에 남는다")

print("[봉투] 인물이 균일한 우울로 수렴하면 잡힌다 -- 미도리 관문")
n = world(); f = Fake([GOOD_PROSE] * 10, joy=5)
r = D.run_scene(n, n.scenes[0], f, max_repairs=1)
ok(r["status"] == "failed", "B 의 joy 가 봉투(40)에 못 닿아 기각된다")
ok(any("V003" in v for v in r["violations"]), f"V003 으로 기각 ({r['violations'][:1]})")

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
