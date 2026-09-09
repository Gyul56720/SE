r"""문제를 낳는 쪽 배선 검사. **가짜 모델로 돈다 -- LLM 도 네트워크도 안 쓴다.**

무엇을 재는가:
  · 프롬프트가 **판정기**를 달라고 하는가 (식이 아니라)
  · 모델이 안 도는 판정기를 내면 **원장이 안 받는가** -- 이 파이프라인의 요점이다
  · 그런데 그것이 **기각이 아닌가** (나머지는 받는다)
  · 낳은 것이 계보를 갖는가
  · 낳자마자 풀고 도약을 잴 수 있는가
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import ops as OPS
from seek import problem as PR
from seek import reach as RE
from seek import solve as SO
from seek import spread as SP

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def seed_led():
    """씨앗: 세 수의 합이 12인가. **판정기가 후보꼴을 먼저 본다** -- 안 그러면
    나중에 확장을 못 잰다(seek/reach.py 의 한계)."""
    led = PR.blank()
    PR.add(led, {
        "물음": "세 수의 합이 12인가",
        "표본": "def sample(rng):\n    return [rng.randrange(10) for _ in range(3)]\n",
        "판정": ("def judge(x):\n"
                 "    if len(x) != 3:\n        raise ValueError('세 수가 아니다')\n"
                 "    return sum(x) == 12\n"),
    }, parent="-", op="씨앗")
    return led


GOOD = {
    "표본": "def sample(rng):\n    return [rng.randrange(10) for _ in range(4)]\n",
    "판정": ("def judge(x):\n"
             "    if len(x) != 4:\n        raise ValueError('네 수가 아니다')\n"
             "    return sum(x) == 12\n"),
    "옮김": "def embed(x):\n    return list(x) + [0]\n",
}


class Fake:
    """**셋을 낸다: 멀쩡한 것 · pass 판정기 · 터지는 판정기.**"""

    def __init__(self):
        self.prompts = []

    def __call__(self, p):
        self.prompts.append(p)
        ops = [l.split(" : ")[0].strip(" ·") for l in p.split("\n")
               if l.startswith("  · ")]
        out = []
        for i, op in enumerate(ops):
            if i == 0:
                out.append({"연산자": op, "물음": f"{op} 로 넓힌 것", **GOOD})
            elif i == 1:
                out.append({"연산자": op, "물음": "게으른 것",
                            "표본": GOOD["표본"],
                            "판정": "def judge(x):\n    pass\n",
                            "옮김": GOOD["옮김"]})
            else:
                out.append({"연산자": op, "물음": "터지는 것",
                            "표본": GOOD["표본"],
                            "판정": "def judge(x):\n    return 1 / 0\n",
                            "옮김": GOOD["옮김"]})
        return "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"


print("== 프롬프트가 판정기를 달라고 한다 ==")
_led = seed_led()
_picks = SP._pick(_led, "t", 0, 3)
_p = SP.prompt(PR.get(_led, "P1"), _picks)
ok("def judge(x):" in _p, "`def judge(x):` 를 달라고 한다")
ok("def sample(rng):" in _p and "def embed(x):" in _p, "표본과 옮김도 달라고 한다")
ok("돌거나 안 돌거나" in _p, "**그럴듯한 것이 없다고 못 박는다**")
ok("원장이 안 받는다" in _p, "안 도는 것은 원장이 안 받는다고 미리 말해 준다")
ok("그럴듯한 식이면 된다" not in _p and "엄밀할 필요 없다" not in _p,
   "**mathdrift 를 41/51 로 만든 그 문장이 없다**")
ok("부탁이 아니라 문법이다" in _p, "부탁이 아니라 문법이라고 적혀 있다")
ok(len(_picks) == 3 and len({o for o, _, _ in _picks}) == 3, "연산자가 셋 다 다르다")

print("\n== 안 도는 판정기는 원장이 안 받는다 (그런데 기각은 아니다) ==")
_f = Fake()
_log = []
_got = SP.step(_led, _f, seed="t", n=0, k=3, log=_log.append)
ok(len(_f.prompts) == 1, "호출은 한 번")
ok(len(_got) == 1, f"셋 중 **하나만** 올랐다 ({len(_got)}개)")
ok(sum(1 for l in _log if "안 받았다" in l) == 2, "안 받은 둘을 로그에 적는다")
ok(any("pass" in l or "참/거짓" in l for l in _log),
   f"`pass` 판정기가 왜 안 받아졌는지 적는다")
ok(any("ZeroDivision" in l or "터" in l or "안 돈다" in l for l in _log),
   "터지는 판정기도 왜인지 적는다")
ok(len(_led["problems"]) == 2, "**나머지 하나는 그대로 받았다** -- 묶음을 통째로 안 버린다")

print("\n== 낳은 것이 계보를 갖는다 ==")
_kid = _got[0]
ok((_kid.get("계보") or {}).get("부모") == "P1", "부모가 원장의 것이다")
ok((_kid.get("계보") or {}).get("연산자") in OPS.BY_NAME, "연산자가 목록에서 나왔다")
ok(_kid.get("깊이") == 1, "깊이가 붙는다")
ok(PR.lineage(_led, _kid["id"]) == ["P1", _kid["id"]], "씨앗까지 사슬이 된다")

print("\n== 낳자마자 풀고 도약을 잰다 ==")
_seedp = PR.get(_led, "P1")
_r0 = SO.search(_seedp, tries=20000, seed=1)
ok(_r0.get("답") is not None, f"씨앗을 푼다 ({_r0.get('본것', 0)}개 봤다)")
_seedp["답"] = _r0["답"]
_r1 = SO.search(_kid, tries=20000, seed=1)
ok(_r1.get("답") is not None, f"낳은 문제도 푼다 ({_r1.get('본것', 0)}개 봤다)")
_kid["답"] = _r1["답"]
_rr = RE.step(_led, _kid["id"])
ok(_rr["보존"] is True, "부모의 답이 자식에서도 답이다 (옮김이 돈다)")
ok(_rr["확장"] is True, "자식의 답을 부모가 **못 읽는다**")
ok(_rr["판정"] == "도약", f"**도약이라고 한다** ({_rr['판정']})")

print("\n== 깨진 응답 ==")
ok(SP.step(_led, lambda p: "JSON 아님", "t", 1, 3, log=lambda s: None) == [],
   "JSON 이 아니면 건너뛴다")


def _boom(p):
    raise RuntimeError("망 끊김")


ok(SP.step(_led, _boom, "t", 1, 3, log=lambda s: None) == [], "호출이 터지면 건너뛴다")
ok(len(SP.objects('[{"a":1},{"b":2}]')) == 2, "배열을 읽는다")
ok(len(SP.objects('앞말 {"a":1} 사이 {"b":2} 뒷말')) == 2,
   "배열이 깨져도 중괄호 덩어리를 건진다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("seek 낳기: 프롬프트 · 안 받기 · 계보 · 풀고 재기 · 깨진 응답 -- 통과")
