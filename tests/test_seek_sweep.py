r"""**200개를 흔들어 0개인 것과 20만 개를 봐서 0개인 것은 같은 말이 아니다.**

실측 2026-09-09, 원장 100개 감사: 공허 9 · **막힘 52** · 문제 39.

막힘 52개가 제일 큰 덩어리인데 그 안에 두 가지가 섞여 있다 -- 해가 있는데 안
걸리는 것(P1 이 22,991개째다)과, 표본이 판정기에 영영 못 닿는 것. 감사는 그 둘을
못 가른다. 실제로 찾아 봐야 갈린다.

여기서 재는 것은 sweep 이 그 둘을 **갈라서 적는가**, 그리고 **못 찾은 것을 없다고
말하지 않는가** 다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_sweep.py
"""
from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import problem as PR                                # noqa: E402
from seek import spread as SP                                 # noqa: E402
from seek import sweep as SW                                  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


SAMPLE = "def sample(rng):\n    return [rng.randrange(60) for _ in range(2)]\n"
EMBED = "def embed(x):\n    return list(x)\n"

# 200개를 흔들면 거의 안 걸리는데(1/3600) 2만 개를 보면 걸린다 -- 딱 그 자리다
바늘 = "def judge(x):\n    return x[0] == 7 and x[1] == 7\n"
없음 = "def judge(x):\n    return x[0] == 999\n"       # 표본이 못 닿는다. 영영 0개
반반 = "def judge(x):\n    return x[0] < 30\n"
참 = "def judge(x):\n    return True\n"


def 원장(*판정들) -> dict:
    led = PR.blank()
    for i, 판 in enumerate(판정들, 1):
        led["problems"].append({
            "id": f"P{i}", "물음": f"문제{i}", "표본": SAMPLE, "판정": 판,
            "옮김": EMBED,
            "계보": {"부모": "-" if i == 1 else "P1", "연산자": "씨앗" if i == 1 else "이산화"},
            "깊이": 0 if i == 1 else 1})
    led["seq"] = len(판정들)
    return led


TMP = Path(tempfile.mkdtemp()) / "led.json"

print("== 막힘을 갈라 적는다 ==")
_led = 원장(바늘, 없음)
_log = []
_셈 = SW.sweep(_led, TMP, tries=200000, seconds=20.0, log=_log.append)
_t = "\n".join(_log)
ok(_셈["품"] == 1, f"바늘은 찾는다 -- 해가 있다 (품 {_셈['품']}개)")
ok(PR.get(_led, "P1").get("답") == [7, 7], f"답이 원장에 적힌다 ({PR.get(_led, 'P1').get('답')})")
ok(_셈["못품"] == 1, f"못 닿는 것은 못 찾는다 (못품 {_셈['못품']}개)")
ok(PR.get(_led, "P2").get("답") is None, "못 찾은 것에는 답을 안 적는다")
ok("없다는 뜻이 아니다" in _t,
   "**못 찾은 것을 없다고 말하지 않는다** -- 이 찾는 법으로 못 찾은 것이다")
ok("해가 있다" in _t, "찾은 것은 해가 있다고 말한다 -- 찾은 것 자체가 증거다")
ok(PR.get(_led, "P2").get("못푼것", {}).get("본것", 0) > 1000,
   f"몇 개를 봤는지 원장에 남긴다 ({PR.get(_led, 'P2').get('못푼것')})")

print("\n== 등급을 원장에 적는다 ==")
ok(PR.get(_led, "P1").get("등급") == "막힘", "막힘을 적는다")
_led2 = 원장(참, 반반)
with redirect_stdout(io.StringIO()):
    _셈2 = SW.sweep(_led2, TMP, tries=2000, seconds=10.0, log=lambda s: None)
ok(PR.get(_led2, "P1").get("등급") == "공허", "공허를 적는다")

print("\n== 공허는 안 푼다 ==")
ok(PR.get(_led2, "P1").get("답") is None,
   "**공허를 안 푼다** -- 아무것이나 답이면 찾은 것이 아무 말도 안 한다")
ok(PR.get(_led2, "P2").get("답") is not None, "옆의 진짜 문제는 푼다")

print("\n== 이미 푼 것은 건너뛴다 (이어서 돈다) ==")
_was = PR.get(_led, "P1")["답"]
_셈3 = SW.sweep(_led, TMP, tries=10, seconds=5.0, log=lambda s: None)
ok(PR.get(_led, "P1")["답"] == _was, "답이 그대로다 -- 20만 개를 다시 안 본다")
ok(_셈3["품"] == 0, f"푼 것 0개 (얻은 값 {_셈3['품']})")
# **품 0개만 보면 못 잡는다.** 이미 푼 것을 다시 찾아도 10개로는 못 찾으니 품은 그대로
# 0이고 답도 안 덮인다 -- 사보타주를 걸어 보고서야 알았다(실측: 이 줄이 없을 때 exit=0).
# 몇 개를 **뒤졌는지**를 봐야 잡힌다. 안 푼 것 하나(P2)만 뒤져야 한다.
ok(_셈3["못품"] == 1,
   f"**안 푼 것 하나만 뒤진다** (얻은 값 {_셈3['못품']}개)  <- 건너뛰기가 없으면 2개가 된다")

print("\n== 끊겨도 남는다 ==")
_led4 = 원장(바늘, 반반)
SW.sweep(_led4, TMP, tries=200000, seconds=20.0, n=1, log=lambda s: None)
_다시 = PR.load(TMP)
ok(PR.get(_다시, "P1").get("답") is not None,
   "**한 문제를 풀 때마다 저장한다** -- 중간에 끊겨도 앞의 것이 남는다")

print("\n== 공허를 부모로 삼지 않는다 ==")
_led5 = 원장(참, 반반)
_led5["problems"][0]["등급"] = "공허"
_본 = []
SP.step(_led5, lambda p: _본.append(p) or "[]", seed="t", n=0, k=1, log=lambda s: None)
ok(_본 and "문제2" in _본[0] and "문제1" not in _본[0],
   "**공허를 건너뛰고 다음 것을 부모로 잡는다** -- 공허에서 파생하면 공허를 물려받는다")
_led6 = 원장(참)
_led6["problems"][0]["등급"] = "공허"
_본2 = []
SP.step(_led6, lambda p: _본2.append(p) or "[]", seed="t", n=0, k=1, log=lambda s: None)
ok(len(_본2) == 1, "전부 공허면 그래도 돈다 -- 아무것도 못 하는 것보다 낫다")

print("\n== 도약은 답이 양쪽에 다 있어야 잰다 ==")
_led7 = 원장(바늘, 반반)
_j = SW.도약(_led7, log=lambda s: None)
ok(_j.get("모름") == 1, f"답이 없으면 모름이다 (얻은 값 {_j})")
with redirect_stdout(io.StringIO()):
    SW.sweep(_led7, TMP, tries=200000, seconds=20.0, log=lambda s: None)
_j2 = SW.도약(_led7, log=lambda s: None)
ok("모름" not in _j2, f"풀고 나면 판정이 선다 ({_j2})")

print("\n== 호출 0회다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "sweep.py").read_text(encoding="utf-8")
ok("llm_pool" not in _src and "GEMINI" not in _src, "sweep 은 LLM 을 안 부른다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 훑기: 막힘 가르기 · 없다고 안 하기 · 이어 돌기 · 공허 건너뛰기 · 도약 -- 통과")
