r"""**22개가 어디서 왔나.** 연산자별로 갈라 보는 자를 검사한다.

대조군이 섰다(진짜 22.2% · 무작위 1~2%, 씨 셋). 그러면 다음 물음은 "12개 중 어느
연산자가 냈나" 다. 고르게 나왔으면 연산자 표는 아무 말도 안 하는 것이고, 몇 개에
몰렸으면 그것이 `spread.py` 가 더 자주 걸어야 할 것이다.

**연산자별로도 대조군을 댄다.** "이 연산자가 도약을 많이 낸다" 는 "이 연산자가
후보꼴을 많이 바꾼다" 일 수 있다. 둘이 같이 높으면 연산자의 공이 아니다.

여기서 재는 것은 `tally.py` 가 그 둘을 갈라 적는가, 그리고 **모름을 판정으로 세지
않는가** 다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_tally.py
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import problem as PR                                # noqa: E402
from seek import tally as TA                                  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 판정(k):
    return (f"def judge(x):\n"
            f"    if not isinstance(x, list) or len(x) != {k}:\n"
            f"        raise ValueError('{k}개가 아니다')\n"
            f"    return sum(x) == 1\n")


def 꼴맞춤(k):
    """무엇이 오든 제 꼴로 우겨넣는다 -- 부모가 누구든 보존이 선다."""
    return (f"def embed(x):\n    y = list(x)[:{k}]\n"
            f"    return y + [0] * ({k} - len(y))\n")


def 부모확인(부, k):
    """부모의 꼴을 확인하고 옮긴다 -- 남이 오면 터진다."""
    return (f"def embed(x):\n"
            f"    if len(x) != {부}:\n        raise ValueError('남의 것이다')\n"
            f"    y = list(x)[:{k}]\n    return y + [0] * ({k} - len(y))\n")


def 답(k):
    return [1] + [0] * (k - 1)


# (id, 길이, 부모, 연산자, 옮김, 답있나)
세상 = [
    ("A0", 1, "-", "씨앗", None, True),
    ("A1", 2, "A0", "부모봄", "부모확인", True),
    ("A2", 3, "A1", "꼴만봄", "꼴맞춤", True),
    ("B0", 10, "-", "씨앗", None, True),
    ("B1", 11, "B0", "부모봄", "부모확인", True),
    ("B2", 12, "B1", "꼴만봄", "꼴맞춤", True),
    ("C0", 20, "-", "씨앗", None, False),          # 부모만 없음
    ("C1", 21, "C0", "덜푼것", "꼴맞춤", True),
    ("D0", 30, "-", "씨앗", None, True),           # 자식만 없음
    ("D1", 31, "D0", "덜푼것", "꼴맞춤", False),
    ("E0", 40, "-", "씨앗", None, False),          # 둘 다 없음
    ("E1", 41, "E0", "덜푼것", "꼴맞춤", False),
    # **한 연산자 안에 잰 것과 못 잰 것이 같이 있는 자리.** 이것이 없으면 분모를
    # 걸음 수로 바꿔도 표가 안 변해서, 사보타주가 red 를 못 낸다(실측: exit=0).
    ("F0", 50, "-", "씨앗", None, True),
    ("F1", 51, "F0", "섞임", "꼴맞춤", True),
    ("F2", 52, "F1", "섞임", "꼴맞춤", False),
]
길이 = {i: k for i, k, *_ in 세상}


def 원장() -> dict:
    led = PR.blank()
    for pid, k, par, op, 옮, 있 in 세상:
        rec = {"id": pid, "물음": pid, "표본": "def sample(rng):\n    return []\n",
               "판정": 판정(k),
               "옮김": ("" if 옮 is None else
                        (꼴맞춤(k) if 옮 == "꼴맞춤" else 부모확인(길이[par], k))),
               "계보": {"부모": par, "연산자": op},
               "깊이": 0 if par == "-" else 1}
        if 있:
            rec["답"] = 답(k)
        led["problems"].append(rec)
    led["seq"] = len(세상)
    return led


_led = 원장()
_out = io.StringIO()
with redirect_stdout(_out):
    TA.show(_led, seed=1)
_t = _out.getvalue()

print("== 연산자별로 가른다 ==")
_걸 = TA.걸음들(_led)
_판 = {}
for op, _d, 판, _w in _걸:
    _판.setdefault(op, []).append(판)
ok(set(_판) == {"부모봄", "꼴만봄", "덜푼것", "섞임"},
   f"연산자 넷으로 갈린다 ({sorted(_판)})")
ok(_판.get("부모봄") == ["도약", "도약"], f"부모봄은 둘 다 도약 ({_판.get('부모봄')})")
ok(_판.get("꼴만봄") == ["도약", "도약"], f"꼴만봄도 둘 다 도약 ({_판.get('꼴만봄')})")
ok(_판.get("덜푼것") == ["모름"] * 3, f"덜푼것은 셋 다 모름 ({_판.get('덜푼것')})")
ok(_판.get("섞임") == ["도약", "모름"], f"섞임은 하나가 도약 하나가 모름 ({_판.get('섞임')})")

print("\n== 연산자별 대조군이 그 둘을 가른다 ==")
_무 = TA.무작위_연산자별(_led, seed=1)
ok(_무.get("부모봄", (9, 0))[0] == 0,
   f"**부모봄은 무작위로 하나도 못 낸다** ({_무.get('부모봄')})")
ok(_무.get("꼴만봄", (0, 0))[0] > 0,
   f"**꼴만봄은 무작위로도 낸다** ({_무.get('꼴만봄')})  ← 연산자의 공이 아니다")
ok("꼴만봄" in _t and "무작위 짝도 비슷하게 내는 연산자" in _t,
   "**그 연산자를 이름으로 지목한다** -- 표만 찍고 읽는 것을 사람에게 맡기지 않는다")
ok("부모봄" not in _t.split("무작위 짝도 비슷하게 내는 연산자")[-1].split("\n")[0],
   "부모봄은 지목하지 않는다")

print("\n== 모름을 판정으로 안 센다 ==")
ok("모름 4개" in _t, f"모름을 따로 센다\n{_t}")
ok("부모만 없음 1" in _t and "자식만 없음 2" in _t and "둘 다 없음 1" in _t,
   "**어느 쪽 답이 없어서인지 가른다** -- 할 일이 다르다")
ok("판정이 아니라 아직 못 잰 것" in _t, "모름이 판정이 아니라고 말한다")
ok("모름을 뺀 분모" in _t, "도약률의 분모가 무엇인지 적는다")
# 덜푼것은 3걸음 다 모름이므로 도약률의 분모가 0 -- 100% 로 찍히면 안 된다
_덜 = [ln for ln in _t.split("\n") if ln.startswith("덜푼것")]
ok(_덜 and "0%" in _덜[0], f"**잰 것이 없으면 0% 다** -- 나누기가 안 터진다 ({_덜})")
# 섞임은 2걸음 중 1이 도약이고 1이 모름이다. 모름을 분모에 넣으면 50%로 찍힌다.
_섞 = [ln for ln in _t.split("\n") if ln.startswith("섞임")]
ok(_섞 and "100%" in _섞[0],
   f"**모름을 분모에서 뺀다** -- 넣으면 50%로 찍혀 도약을 절반으로 깎는다 ({_섞})")

print("\n== 깊이별로도 센다 ==")
ok("깊이" in _t and "\n1 " in _t.replace("1  ", "1 "), "깊이 줄이 있다")

print("\n== 호출 0회다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "tally.py").read_text(encoding="utf-8")
ok("llm_pool" not in _src and "GEMINI" not in _src, "tally 는 LLM 을 안 부른다")
ok("raise NotAProblem" not in _src, "**아무것도 기각하지 않는다** -- 숫자를 만들 뿐이다")

print("\n== 씨를 바꿔도 결론이 안 뒤집힌다 ==")
_결 = {TA.무작위_연산자별(_led, s).get("부모봄", (0, 0))[0] for s in (1, 2, 3, 4, 5)}
ok(_결 == {0}, f"부모봄은 어느 씨로도 0이다 ({_결})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 셈: 연산자별 · 연산자별 대조군 · 모름 가르기 · 깊이 -- 통과")
