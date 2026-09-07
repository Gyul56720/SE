"""①재현 축 -- **LLM 도 네트워크도 안 쓴다.** 해독기를 격리해서 돌리고 Brent 로 검산한다.

이 축이 이 꼴인 이유(실측 2026-09-07, 85개):

  · 이름과 산문으로 공간을 주고받았더니 모델이 부모 이름에 연산자 어휘를 덧붙이는
    데로 수렴했다 -- "멀티리니어 랭크 스펙트럼의 특성류 코호몰로지 공간"
  · 되사상을 산문으로 받으니 "요네다 매몰을 통해 재해석" 이 통과했다. 차 있지만 공허하다.
    space.grade 는 빈 칸만 보므로 이것을 못 거른다

그래서 오가는 것을 식과 수와 코드로 바꿨다. **코드는 돌려 보면 끝난다.**

무엇을 고정하나:
  · 씨앗이 자기 ①재현을 통과하는가 (파이프라인의 출발점이 성한가)
  · 한 칸만 틀려도 떨어지는가 (심판이 살아 있는가)
  · **Strassen 을 하드코딩한 해독기를 잡는가** -- 검산은 통과하지만 점을 안 쓴다
  · 안 도는 코드 · decode 없음 · 빈 칸이 통과로 새지 않는가
  · 해독기가 심판에 손댈 수 없는가 (격리)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import encode as EN
from mathdrift import recall as R
from mathdrift import space as SP

fails = []


def ok(cond, what):
    print(("    OK   " if cond else "    실패 ") + what)
    if not cond:
        fails.append(what)


SEED = SP.load(SP.SEED)["spaces"][0]
PT = SEED["시금석점"]

print("[씨앗] **출발점이 성한가** -- 씨앗이 자기 ①재현을 통과해야 한다")
_s = EN.check(SEED["해독"], PT)
ok(_s["판정"] == "재현", f"씨앗이 Strassen 을 되돌린다 ({_s['판정']})")
ok(not _s["하드코딩"], "씨앗의 해독기는 점을 실제로 쓴다")
ok(_s["치수"] == SEED["치수"], f"적어 둔 치수와 시금석점 길이가 맞는다 ({_s['치수']})")

print()
print("[심판] **판정에 LLM 이 한 방울도 안 들어간다** -- Brent 항등식이 정한다")
_broken = PT[:]
_broken[0] = str(int(_broken[0]) + 1) if not isinstance(_broken[0], str) else _broken[0]
_broken[0] = 5
ok(EN.check(SEED["해독"], _broken)["판정"] == "틀림",
   "한 칸만 틀려도 떨어진다  ← 심판이 살아 있다는 증거다")
ok(EN.check(SEED["해독"], [0] * len(PT))["판정"] == "틀림", "전부 0 인 점은 떨어진다")

print()
print("[하드코딩] **검산은 통과하지만 점을 안 쓰는 해독기를 잡는다**")
_res = EN.run(SEED["해독"], [PT])["results"][0]
_hard = ("def decode(p):\n"
         f"    return {_res['U']!r}, {_res['V']!r}, {_res['W']!r}, {_res['lambda']!r}\n")
_h = EN.check(_hard, PT)
ok(_h["판정"] == "재현", "하드코딩한 것도 검산 자체는 통과한다  ← 그래서 흔들어 본다")
ok(_h["하드코딩"], "**점을 흔들어도 같은 것이 나오면 하드코딩으로 본다**")

print()
print("[못 돎] **산문으로는 못 빠져나간다**")
ok(EN.check("def decode(p):\n    return 1 / 0\n", PT)["판정"] == "못돎", "터지면 못돎")
ok(EN.check("x = 1\n", PT)["판정"] == "못돎", "decode 가 없으면 못돎")
ok(EN.check("def decode(p):\n    return 1, 2\n", PT)["판정"] == "못돎", "꼴이 틀리면 못돎")
ok(EN.check("", PT)["판정"] == "없음", "해독기가 비면 없음")
ok(EN.check(SEED["해독"], [])["판정"] == "없음", "시금석점이 비면 없음")
ok(EN.check("def decode(p):\n    while True:\n        pass\n", PT,
            timeout=3)["판정"] == "못돎", "안 끝나면 시간 초과로 못돎")

print()
print("[격리] **해독기가 심판에 손댈 수 없다** -- mathgen 이 생성기를 임포트 안 하는 것과 같다")
_evil = ("import sys\n"
         "def decode(p):\n"
         "    sys.modules['verifier'] = None\n"
         "    return [[1]*7]*4, [[1]*7]*4, [[1]*7]*4, [1]*7\n")
_e = EN.check(_evil, PT)
ok(_e["판정"] in ("틀림", "못돎"), f"심판을 건드리려 해도 통과 못 한다 ({_e['판정']})")
ok(EN.check(SEED["해독"], PT)["판정"] == "재현", "그 뒤에도 심판이 멀쩡하다")

print()
print("[원장] 판정이 적히는가")
_rec = dict(SEED)
_rec["id"] = "S1"
_out = R.one(_rec, log=lambda *a: None)
ok(_out["판정"] == "재현" and _rec["재현"]["판정"] == "재현", "판정이 원장에 적힌다")
ok(_rec["재현"]["시금석"].startswith("strassen"), "어느 시금석으로 봤는지 남는다")
ok(R.one({"id": "S9"}, log=lambda *a: None)["판정"] == "없음", "칸이 비면 없음으로 적힌다")

print()
if fails:
    print(f"mathdrift 재현: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("mathdrift 재현: 씨앗 · 심판 · 하드코딩 · 못 돎 · 격리 · 원장 -- 통과")
