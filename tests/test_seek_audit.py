r"""**도는 것과 거르는 것은 다른 물음이다.**

실측 2026-09-09: VM 에서 `--n 20` 을 돌려 21개가 낳아지고 **21개가 다 받아들여졌다.**
100% 는 프롬프트가 좋다는 뜻일 수도 있고 거르는 데가 없다는 뜻일 수도 있는데, 그때는
가를 방법이 없었다. 확인해 보니 이랬다.

    def judge(x): return True     -> 원장이 받았다
    def judge(x): return False    -> 원장이 받았다

둘 다 "돈다". 앞의 것은 아무것도 안 거른다 -- 뽑은 것이 다 답이면 찾을 것이 없다.
뒤의 것은 어려운 문제와 구분이 안 된다(P1 이 무작위 200개 중 0개다).

여기서 재는 것은 그 둘을 **갈라서** 다루는가다. 앞은 막고, 뒤는 막지 않는다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_audit.py
"""
from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import audit as AU                                  # noqa: E402
from seek import judge as J                                   # noqa: E402
from seek import problem as PR                                # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


SAMPLE = "def sample(rng):\n    return [rng.randrange(100) for _ in range(3)]\n"
EMBED = "def embed(x):\n    return list(x)\n"


def rec(판정: str, 물음="x") -> dict:
    return {"물음": 물음, "표본": SAMPLE, "판정": 판정, "옮김": EMBED}


def 씨앗원장() -> dict:
    led = PR.blank()
    led["problems"].append({
        "id": "P1", "물음": "씨앗", "표본": SAMPLE,
        "판정": "def judge(x):\n    return sum(x) == 7\n", "옮김": "",
        "계보": {"부모": "-", "연산자": "씨앗"}, "깊이": 0})
    led["seq"] = 1
    return led


참 = "def judge(x):\n    return True\n"
거짓 = "def judge(x):\n    return False\n"
반반 = "def judge(x):\n    return x[0] < 50\n"
바늘 = "def judge(x):\n    return x[0] == 42 and x[1] == 42 and x[2] == 42\n"

print("== 다 받는 판정기는 원장이 안 받는다 ==")
_led = 씨앗원장()
try:
    PR.add(_led, rec(참), parent="P1", op="자원 풀기")
    ok(False, "**`return True` 를 안 받는다** -- 받았다")
except PR.NotAProblem as e:
    ok(True, "**`return True` 를 안 받는다**")
    ok("다 받는다" in str(e), f"왜인지 말한다 -- {str(e)[:60]}")
    ok("32" in str(e), "몇 개를 봤는지 적는다  ← 5개면 우연일 수 있다")

print("\n== 하나도 안 받는 것은 **막지 않는다** ==")
_led2 = 씨앗원장()
_g = PR.add(_led2, rec(거짓), parent="P1", op="제약 더하기")
ok(_g["id"] == "P2", "`return False` 는 받는다  ← P1 이 무작위 200개 중 0개다")
_g2 = PR.add(_led2, rec(바늘), parent="P1", op="차원 올리기")
ok(_g2["id"] == "P3", "바늘 찾기(1/10^6)도 받는다 -- 어려운 것과 틀린 것을 여기서 못 가른다")
ok(PR.add(_led2, rec(반반), parent="P1", op="이산화")["id"] == "P4", "갈리는 것도 받는다")

print("\n== 32개를 본다 ==")
_ok, _why, _잰 = J.runs(rec(반반))
ok(_ok and _잰.get("본것") == 32,
   f"표본 32개를 본다 (얻은 값 {_잰.get('본것')})  ← 5개는 다 통과하는 일이 잦다")
ok(0 < _잰["받음"] < 32, f"갈린 것은 갈린 채로 온다 ({_잰['받음']}/32)")
_ok3, _why3, _잰3 = J.runs(rec("def judge(x):\n    pass\n"))
ok(not _ok3 and _잰3 == {}, "안 도는 것은 잰 것이 비어 있다  ← 셋째 값을 믿고 쓰면 안 된다")

print("\n== 감사가 셋을 가른다 ==")
ok(AU.grade(rec(참), n=60)["등급"] == "공허", "다 받으면 공허")
ok(AU.grade(rec(거짓), n=60)["등급"] == "막힘", "하나도 안 받으면 막힘")
ok(AU.grade(rec(반반), n=60)["등급"] == "문제", "갈리면 문제")
_터 = AU.grade(rec("def judge(x):\n    return 1 / 0\n"), n=60)
ok(_터["등급"] == "터짐" and _터["터짐"] == 60, f"다 터지면 터짐 ({_터['터짐']}개)")
ok(AU.grade({"표본": "없다", "판정": 반반}, n=60)["등급"] == "안돎", "표본이 깨졌으면 안돎")

print("\n== 부모 판정기를 그대로 쓴 것을 잡는다 ==")
_led3 = 씨앗원장()
_같 = dict(rec("def judge(x):\n    return sum(x) == 7\n"), 물음="말만 바꿨다")
_r = PR.add(_led3, _같, parent="P1", op="쌍대")
ok(AU.베낌(_led3, _r), "**판정기가 부모와 글자 그대로 같으면 잡는다** -- 물음만 바꾼 것이다")
ok(not AU.베낌(_led3, PR.add(_led3, rec(반반), parent="P1", op="국소화")),
   "다르면 안 잡는다")
ok(not AU.베낌(_led3, _led3["problems"][0]), "씨앗은 부모가 없다 -- 안 잡는다")

print("\n== 감사가 화면에 그대로 적는다 ==")
_out = io.StringIO()
with redirect_stdout(_out):
    AU.show(_led2, n=60)
_t = _out.getvalue()
ok("막힘 3개" in _t and "문제 1개" in _t, f"등급별로 센다\n{_t[-260:]}")
ok("P4     문제" in _t, "갈리는 것만 문제로 찍는다")
ok("버리지 않는다" in _t, "**막힘을 버리라고 안 한다** -- 과잉 기각은 이 저장소가 싫어하는 쪽이다")

print("\n== 호출 0회다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "audit.py").read_text(encoding="utf-8")
ok("llm_pool" not in _src and "GEMINI" not in _src, "감사는 LLM 을 안 부른다")

print("\n== 이 저장소의 원장에서 ==")
_real = PR.load()
_ids = [p["id"] for p in _real["problems"]]
_공허 = [p["id"] for p in _real["problems"] if AU.grade(p, n=60)["등급"] == "공허"]
ok(not _공허, f"지금 원장에 공허가 없다 (있으면 {_공허})")
ok("P1" in _ids and AU.grade(PR.get(_real, "P1"), n=60)["등급"] == "막힘",
   "**P1 이 막힘이다** -- 막힘을 자동으로 버렸으면 씨앗부터 사라졌다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 감사: 공허 막기 · 막힘 살리기 · 32표본 · 등급 · 베낌 -- 통과")
