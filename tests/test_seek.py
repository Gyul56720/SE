r"""seek 배선 검사. **LLM 도 네트워크도 안 쓴다.**

무엇을 재는가:
  · 판정기 없는 것을 원장이 **못 받는가** (비었는지가 아니라 **도는지**로)
  · 도약 판정이 아무 데나 초록불을 켜지 않는가 (쌍대는 재작성이어야 한다)
  · 판정기가 부모 프로세스에서 안 도는가 (격리)
  · 망가진 문제(전부 받음 · 아무것도 안 받음)를 흔들어서 잡는가
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import judge as J
from seek import problem as PR
from seek import reach as RE

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


GOOD_SAMPLE = "def sample(rng):\n    return [rng.randrange(10) for _ in range(3)]\n"
GOOD_JUDGE = ("def judge(x):\n"
              "    if len(x) != 3:\n"
              "        raise ValueError('세 수가 아니다')\n"
              "    return sum(x) == 12\n")
EMBED = "def embed(x):\n    return list(x)\n"


print("== 판정기 없는 것은 문제가 아니다 ==")
led = PR.blank()
for bad, why in (
    ({"물음": "뭔가", "표본": "", "판정": GOOD_JUDGE}, "표본이 비었다"),
    ({"물음": "뭔가", "표본": GOOD_SAMPLE, "판정": ""}, "판정이 비었다"),
    ({"물음": "뭔가", "표본": GOOD_SAMPLE, "판정": "def judge(x):\n    pass\n"},
     "판정이 **이름만** 있다 (pass 는 판정이 아니다)"),
    ({"물음": "뭔가", "표본": GOOD_SAMPLE, "판정": "def nope(x):\n    return True\n"},
     "판정 이름이 틀렸다"),
    ({"물음": "뭔가", "표본": GOOD_SAMPLE, "판정": "def judge(x):\n    1/0\n"},
     "판정이 터진다"),
):
    try:
        PR.add(led, bad, parent="-", op="씨앗")
        ok(False, f"거절한다: {why}")
    except PR.NotAProblem:
        ok(True, f"거절한다: {why}")

_seed = PR.add(led, {"물음": "세 수의 합이 12인가", "표본": GOOD_SAMPLE,
                     "판정": GOOD_JUDGE}, parent="-", op="씨앗")
ok(_seed["id"] == "P1", "제대로 된 것은 받는다")
ok(_seed.get("깊이") == 0, "씨앗의 깊이는 0")

print("\n== `pass` 를 비었는지로만 보면 통과한다 -- 그래서 돌려 본다 ==")
_lazy = {"물음": "x", "표본": GOOD_SAMPLE, "판정": "def judge(x):\n    pass\n"}
ok(all(str(_lazy.get(f) or "").strip() for f in PR.CODE),
   "`pass` 판정기는 **비어 있지 않다**  ← 비었는지만 보면 통과한다")
ok(not J.runs(_lazy)[0], "그런데 돌려 보면 안 된다  ← 이 차이가 어제 41개를 만든 자리다")

print("\n== 자식은 부모 없이 못 온다 ==")
try:
    PR.add(led, {"물음": "x", "표본": GOOD_SAMPLE, "판정": GOOD_JUDGE, "옮김": EMBED},
           parent="P99", op="경계화")
    ok(False, "원장에 없는 부모를 거절한다")
except ValueError:
    ok(True, "원장에 없는 부모를 거절한다")
try:
    PR.add(led, {"물음": "x", "표본": GOOD_SAMPLE, "판정": GOOD_JUDGE},
           parent="P1", op="경계화")
    ok(False, "**옮김 없는 자식을 거절한다** -- 부모의 답이 여기서도 답인지 볼 수가 없다")
except PR.NotAProblem:
    ok(True, "**옮김 없는 자식을 거절한다** -- 부모의 답이 여기서도 답인지 볼 수가 없다")

print("\n== 판정기는 부모 프로세스에서 안 돈다 ==")
import os as _os
_mark = Path(__file__).resolve().parent.parent / "seek" / ".격리검사"
if _mark.exists():
    _mark.unlink()
_evil = {"물음": "x", "표본": GOOD_SAMPLE,
         "판정": (f"def judge(x):\n"
                  f"    import pathlib\n"
                  f"    pathlib.Path({str(_mark)!r}).write_text('돌았다')\n"
                  f"    return True\n")}
_ran, _, _ = J.runs(_evil)
ok(_ran, "판정기가 돌기는 한다")
ok(_mark.exists(), "**코드는 실제로 돈다** -- 샌드박스가 아니라 프로세스 분리다")
ok("pathlib" not in dir(), "부모의 이름 공간은 안 더럽혀졌다")
if _mark.exists():
    _mark.unlink()

print("\n== 망가진 문제를 흔들어서 잡는다 ==")
_all = {"표본": GOOD_SAMPLE, "판정": "def judge(x):\n    return True\n"}
_none = {"표본": GOOD_SAMPLE, "판정": "def judge(x):\n    return False\n"}
_s1, _s2 = J.shake(_all, n=60), J.shake(_none, n=60)
ok(_s1.get("받음") == _s1.get("본것") == 60, f"전부 받는 판정기가 드러난다 ({_s1.get('받음')}/60)")
ok(_s2.get("받음") == 0, f"아무것도 안 받는 판정기가 드러난다 ({_s2.get('받음')}/60)")
_mid = J.shake({"표본": GOOD_SAMPLE, "판정": GOOD_JUDGE}, n=200)
ok(0 < _mid.get("받음", 0) < 200, f"멀쩡한 것은 그 사이다 ({_mid.get('받음')}/200)")

print("\n== 도약 판정이 아무 데나 안 켜진다 ==")
_l = PR.blank()
_p = PR.add(_l, {"물음": "합 12", "표본": GOOD_SAMPLE, "판정": GOOD_JUDGE},
            parent="-", op="씨앗")
_p["답"] = [3, 4, 5]
# 재작성: 후보꼴이 같다. 부모가 자식의 답을 읽는다.
_re = PR.add(_l, {"물음": "합 12 (같은 것)", "표본": GOOD_SAMPLE,
                  "판정": GOOD_JUDGE, "옮김": EMBED},
             parent="P1", op="쌍대")
_re["답"] = [6, 5, 1]
_r = RE.step(_l, _re["id"])
ok(_r["보존"] is True, "재작성도 보존은 한다")
ok(_r["확장"] is False, "그런데 확장은 아니다  ← 부모가 자식의 답을 읽는다")
ok(_r["판정"] == "재작성", f"**재작성이라고 한다** (얻은 값 {_r['판정']})")

# 도약: 후보꼴이 커진다. 부모가 자식의 답을 못 읽는다.
_up = PR.add(_l, {"물음": "**네 수**의 합이 12",
                  "표본": "def sample(rng):\n    return [rng.randrange(10) for _ in range(4)]\n",
                  "판정": ("def judge(x):\n"
                           "    if len(x) not in (3, 4):\n        raise ValueError('길이')\n"
                           "    return sum(x) == 12\n"),
                  "옮김": EMBED}, parent="P1", op="경계화")
_up["답"] = [3, 3, 3, 3]
_r2 = RE.step(_l, _up["id"])
ok(_r2["보존"] is True, "부모의 답 [3,4,5] 가 자식에서도 답이다")
ok(_r2["확장"] is True, "자식의 답 [3,3,3,3] 을 부모가 **읽지도 못한다**")
ok(_r2["판정"] == "도약", f"**도약이라고 한다** (얻은 값 {_r2['판정']})")

# 딴 문제: 보존이 깨진다
_off = PR.add(_l, {"물음": "합이 100", "표본": GOOD_SAMPLE,
                   "판정": ("def judge(x):\n"
                            "    if len(x) != 3:\n        raise ValueError('세 수가 아니다')\n"
                            "    return sum(x) == 100\n"), "옮김": EMBED},
              parent="P1", op="망각")
_off["답"] = [50, 30, 20]
_r3 = RE.step(_l, _off["id"])
ok(_r3["보존"] is False, "부모의 답이 여기서는 답이 아니다")
ok(_r3["판정"] != "도약", f"**도약이라고 안 한다** (얻은 값 {_r3['판정']})")

print("\n== 씨앗은 견줄 부모가 없다 ==")
ok(RE.step(_l, "P1").get("ok") is False, "씨앗에는 도약을 못 묻는다")

print("\n== 퇴화 -- 넷째 칸 ==")
# 실측 2026-09-09, 100개: 모름 50개 중 8개가 이것이었다. 답이 양쪽에 다 있고 두
# 검사가 다 돌았는데 둘 다 아니라고 답한 것 -- 못 잰 것이 아니라 **다 잰 것**이다.
# `모름` 과 한 칸에 섞여 있어서 "더 풀면 판정이 서겠지" 로 읽혔는데 풀 것이 없다.
_부 = {"id": "A", "판정": "def judge(x):\n    return len(x) == 2 and sum(x) == 1\n",
       "답": [1, 0]}
_자 = {"id": "B", "판정": "def judge(x):\n    return len(x) == 2 and sum(x) == 9\n",
       "옮김": "def embed(x):\n    return list(x)\n", "답": [1, 0],
       "계보": {"부모": "A"}}
_퇴 = RE.pair(_부, _자)
ok(_퇴["보존"] is False and _퇴["확장"] is False, f"보존도 확장도 아니오 ({_퇴['보존']}·{_퇴['확장']})")
ok(_퇴["판정"] == "퇴화",
   f"**퇴화라고 부른다** (얻은 값 {_퇴['판정']})  <- 이것이 모름에 섞여 있던 8개다")

_out = io.StringIO()
_led퇴 = PR.blank()
_led퇴["problems"] = [dict(_부, 물음="부모", 계보={"부모": "-", "연산자": "씨앗"}, 깊이=0),
                     dict(_자, 물음="자식", 계보={"부모": "A", "연산자": "제약 더하기"}, 깊이=1)]
with redirect_stdout(_out):
    RE.show(_led퇴, "B")
ok("좁아졌다" in _out.getvalue(),
   "**좁아졌다고 말한다** -- 목표가 '퇴화가 아니라 도약' 이므로 이 칸을 안 세면 반쪽만 본다")
ok("다 잰 것이지" in _out.getvalue(), "못 잰 것이 아니라고 못박는다")

# 넷이 서로 안 겹친다
_넷 = {}
for 보, 확 in ((True, True), (True, False), (False, True), (False, False)):
    _r = dict(보존=보, 확장=확)
    _판 = ("도약" if (보 and 확) else "재작성" if 보 and 확 is False else
           "딴 문제" if 확 and 보 is False else "퇴화" if 보 is False and 확 is False else "모름")
    _넷[(보, 확)] = _판
ok(len(set(_넷.values())) == 4, f"보존·확장 네 조합이 네 이름으로 갈린다 ({_넷})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("seek: 문법 · 격리 · 흔들기 · 도약/재작성/딴문제 -- 통과")
