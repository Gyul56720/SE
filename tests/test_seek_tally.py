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


from tests._seek_고정물 import 원장, 세상        # noqa: E402


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
_행0 = {이름: n for 이름, n, _말 in TA.모름_가르기(
    [w for _op, _d, 판, w in TA.걸음들(_led) if 판 == "모름"])}
ok((_행0.get("부모만 없음"), _행0.get("자식만 없음"), _행0.get("둘 다 없음")) == (1, 2, 1),
   f"**어느 쪽 답이 없어서인지 가른다** -- 할 일이 다르다 ({_행0})")
ok("부모만 없음" in _t and "자식만 없음" in _t and "둘 다 없음" in _t, "화면에도 적는다")
ok("판정이 아니라 아직 못 잰 것" in _t, "모름이 판정이 아니라고 말한다")
ok("모름을 뺀 분모" in _t, "도약률의 분모가 무엇인지 적는다")
# 덜푼것은 3걸음 다 모름이므로 도약률의 분모가 0 -- 100% 로 찍히면 안 된다
_덜 = [ln for ln in _t.split("\n") if ln.startswith("덜푼것")]
ok(_덜 and "0%" in _덜[0], f"**잰 것이 없으면 0% 다** -- 나누기가 안 터진다 ({_덜})")
# 섞임은 2걸음 중 1이 도약이고 1이 모름이다. 모름을 분모에 넣으면 50%로 찍힌다.
_섞 = [ln for ln in _t.split("\n") if ln.startswith("섞임")]
ok(_섞 and "100%" in _섞[0],
   f"**모름을 분모에서 뺀다** -- 넣으면 50%로 찍혀 도약을 절반으로 깎는다 ({_섞})")

print("\n== 모름 가르기가 빠짐없다 ==")
# 실측 2026-09-09: 100개에서 모름 50개인데 부모만 7 · 자식만 27 · 둘 다 8 = **42** 였다.
# 8개가 어느 칸에도 안 들어갔다 -- 세 칸으로는 모자란다.
_모 = [w for _op, _d, 판, w in TA.걸음들(_led) if 판 == "모름"]
_행 = {이름: n for 이름, n, _말 in TA.모름_가르기(_모)}
ok(_행.get("합") == _행.get("머리"),
   f"**합이 총계와 같다** ({_행.get('합')} == {_행.get('머리')})  <- 42 != 50 이 이번의 병이다")
ok("합" in _t and "총계" in _t, "화면에서도 합을 확인해 준다")
ok(_행.get("까닭 모름") == 0, f"까닭 모를 것이 없다 ({_행.get('까닭 모름')})")
ok("이 분류가 모자라다" not in _t, "지금은 모자라다고 안 한다")
# **알림이 살아 있는지 본다.** 모르는 까닭을 하나 먹여 보고 그 칸이 받는지.
_행X = {이름: (n, 말) for 이름, n, 말 in TA.모름_가르기([["처음 보는 까닭"]])}
ok(_행X["까닭 모름"][0] == 1, "모르는 까닭은 '까닭 모름' 으로 떨어진다")
ok("이 분류가 모자라다" in _행X["까닭 모름"][1],
   "**그때 모자라다고 말한다** -- 이 칸이 알림이다")
ok(_행X["합"][0] == 1, "그래도 합은 맞는다 -- 이 칸이 남은 것을 다 받으니까")

# 답이 양쪽에 다 있는데 옮김이 터지는 자리 -- 풀어도 안 줄어드는 모름이다
_고장 = 원장()
# **부모 판정기가 안 서면** cross 가 못 돌아 확장이 None 이 되고, 보존은 서므로
# 도약도 재작성도 딴 문제도 아니다 -- 모름으로 떨어진다. 답은 양쪽에 다 있는데도.
_그 = [p for p in _고장["problems"] if p["id"] == "A1"][0]
_그["판정"] = "def judge(x)\n    이건 파이썬이 아니다\n"
_모2 = [w for _op, _d, 판, w in TA.걸음들(_고장) if 판 == "모름"]
_행2 = {이름: n for 이름, n, _말 in TA.모름_가르기(_모2)}
ok(_행2.get("고장") == 1,
   f"**답은 양쪽에 다 있는데 옮김이 터지는 것을 '고장' 으로 센다** ({_행2.get('고장')})")
ok(_행2.get("합") == _행2.get("머리"), f"그래도 합이 맞는다 ({_행2})")
_o2 = io.StringIO()
with redirect_stdout(_o2):
    TA.show(_고장, seed=1)
ok("풀어도 안 줄어든다" in _o2.getvalue(),
   "**풀어도 안 줄어든다고 말한다** -- 덜 푼 것과 같은 칸에 두면 'sweep 더 돌리면 되겠지' 로 읽힌다")

print("\n== 분모가 얇으면 못 읽는다고 적는다 ==")
ok("잰 것이 적어 못 읽는다" in _t,
   "**1/1 도 100% 다** -- 분모가 얇은 줄에 그렇게 적는다")
_굵 = [ln for ln in _t.split("\n") if ln.startswith("덜푼것")]
ok(_굵 and "못 읽는다" not in _굵[0], "잰 것이 0이면 그 말도 안 붙인다 (0% 로 이미 안 읽힌다)")

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
