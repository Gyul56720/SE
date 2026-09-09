r"""**22개가 무언가를 뜻하려면, 그 자가 계보를 봐야 한다.**

실측 2026-09-09: 100개를 훑고 도약 22 · 재작성 16 · 딴 문제 11 · 모름 50 이 나왔다.
99걸음 중 22%다. 반가운 수인데 **21/21 과 같은 모양**이라, 그때처럼 자부터 검사한다.

`reach` 의 확장 판정은 "부모 판정기가 자식의 답을 **읽지도 못한다**" 이다. 그런데
그것은 두 문제의 **후보꼴이 다르다**는 말이기도 하다. 꼴은 아무 두 문제나 다르다.
그러면 계보와 상관없는 남을 부모로 대도 도약이 나온다 -- 그 수는 연산자의 공이
아니라 꼴 차이의 그림자다.

여기서 재는 것은 `control.py` 가 **그 두 세상을 가르는가** 다.

    세상 A  옮김이 제 부모의 꼴에만 맞는다  -> 무작위 짝은 보존이 깨진다. 자가 계보를 본다
    세상 B  옮김이 아무것에나 맞는다        -> 무작위 짝도 도약을 낸다. 자가 꼴만 본다

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_control.py
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import control as CT                                # noqa: E402
from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 판정(k: int) -> str:
    """후보꼴을 **먼저 본다** -- 안 그러면 확장이 영영 안 잡힌다(reach 독스트링)."""
    return (f"def judge(x):\n"
            f"    if not isinstance(x, list) or len(x) != {k}:\n"
            f"        raise ValueError('{k}개가 아니다')\n"
            f"    return sum(x) == 1\n")


def 아무거나옮김(k: int) -> str:
    """**제 꼴로 맞춰 준다.** 무엇이 오든 k개로 자르거나 채운다.

    LLM 이 실제로 쓸 법한 옮김이 이 꼴이다 -- 제 문제의 후보꼴은 아는데 부모가
    누구인지는 프롬프트에 없으니, 받은 것을 제 꼴로 우겨넣는다.
    """
    return (f"def embed(x):\n"
            f"    y = list(x)[:{k}]\n"
            f"    return y + [0] * ({k} - len(y))\n")


def 제부모만옮김(부모길이: int, k: int) -> str:
    """부모의 꼴을 **확인하고** 옮긴다. 남이 오면 터진다."""
    return (f"def embed(x):\n"
            f"    if len(x) != {부모길이}:\n"
            f"        raise ValueError('이 옮김은 {부모길이}개짜리 부모의 것이다')\n"
            f"    y = list(x)[:{k}]\n"
            f"    return y + [0] * ({k} - len(y))\n")


# **두 사슬**이다. 한 사슬이면 모두가 서로의 조상이나 후손이라 무작위로 고를 남이
# 없다. 길이대를 갈라 둔 것은(1~3 · 10~12) 남의 옮김이 우연히 맞는 일을 막으려는 것이다.
사슬 = [("P1", 1, "-"), ("P2", 2, "P1"), ("P3", 3, "P2"),
        ("P4", 10, "-"), ("P5", 11, "P4"), ("P6", 12, "P5")]
길이 = {pid: k for pid, k, _ in 사슬}


def 세상(옮김) -> dict:
    """`옮김(부모길이, 내길이)` 을 받아 원장을 짓는다. 답은 다 [1,0,0,...]."""
    led = PR.blank()
    for pid, k, par in 사슬:
        led["problems"].append({
            "id": pid, "물음": f"{k}개짜리", "표본": "def sample(rng):\n    return []\n",
            "판정": 판정(k),
            "옮김": "" if par == "-" else 옮김(길이[par], k),
            "답": [1] + [0] * (k - 1),
            "계보": {"부모": par, "연산자": "씨앗" if par == "-" else "차원 올리기"},
            "깊이": 0 if par == "-" else 1})
    led["seq"] = len(사슬)
    return led


print("== 자가 무엇을 재는지부터 ==")
_B = 세상(lambda 부, 내: 아무거나옮김(내))
_r = RE.pair(PR.get(_B, "P5"), PR.get(_B, "P3"))
ok(_r["판정"] == "도약",
   f"P5 -> P3 은 **아무 사이도 아닌데** 도약이 나온다 ({_r['판정']})"
   "  ← 꼴만 다르면 서는 판정이다")

print("\n== 세상 B: 옮김이 아무것에나 맞으면 무작위도 도약을 낸다 ==")
_진 = CT.셈(_B, "진짜", seed=1)
_무 = CT.셈(_B, "무작위", seed=1)
ok(_진.get("도약", 0) > 0, f"진짜 짝이 도약을 낸다 ({_진})")
ok(_무.get("도약", 0) > 0, f"**무작위 짝도 낸다** ({_무})  ← 그러면 진짜 쪽 수는 공이 아니다")
ok(CT.비율(_무, "도약") >= CT.비율(_진, "도약") * 0.5,
   f"비율이 비슷하다 -- 진짜 {CT.비율(_진, '도약'):.0%} · 무작위 {CT.비율(_무, '도약'):.0%}")
_out = io.StringIO()
with redirect_stdout(_out):
    CT.show(_B, seed=1)
_t = _out.getvalue()
ok("연산자가 무엇을" in _t and "꼴이 다른지만" in _t,
   "**그렇다고 말한다** -- 숫자만 찍고 읽는 것을 사람에게 맡기지 않는다")

print("\n== 세상 A: 옮김이 제 부모의 꼴에만 맞으면 무작위는 깨진다 ==")
# P2..P5 의 부모는 P1(1개짜리)이므로 옮김도 1개짜리만 받는다
_A = 세상(제부모만옮김)
_진A = CT.셈(_A, "진짜", seed=1)
_무A = CT.셈(_A, "무작위", seed=1)
ok(_진A.get("도약", 0) > 0, f"진짜 짝은 도약을 낸다 ({_진A})")
ok(_무A.get("도약", 0) == 0, f"**무작위 짝은 하나도 못 낸다** ({_무A})")
_out = io.StringIO()
with redirect_stdout(_out):
    CT.show(_A, seed=1)
ok("계보를 본다" in _out.getvalue(), "이쪽은 자가 계보를 본다고 말한다")

print("\n== 무작위 짝이 계보를 다시 밟지 않는다 ==")
_기 = 세상(lambda 부, 내: 아무거나옮김(내))
ok(CT.자손(_기, "P1") == {"P1", "P2", "P3"}, "후손을 다 찾는다 -- 제 사슬만")
ok(CT.조상(_기, "P3") == {"P3", "P2", "P1"}, "조상을 다 찾는다")
ok(CT.자손(_기, "P3") == {"P3"}, "잎은 후손이 저뿐이다")
ok(CT.조상(_기, "P6") == {"P6", "P5", "P4"}, "다른 사슬의 조상도 제대로 찾는다")
_걸린것 = []
_orig = RE.pair


def _엿(par, kid):
    _걸린것.append((par["id"], kid["id"]))
    return _orig(par, kid)


RE.pair = _엿
try:
    CT.셈(_기, "무작위", seed=7)
finally:
    RE.pair = _orig
_진짜부모 = {pid: par for pid, _, par in 사슬}
ok(_걸린것 and all(p != _진짜부모[k] for p, k in _걸린것),
   f"**진짜 부모를 무작위로 다시 뽑지 않는다** ({_걸린것})")
ok(all(p != k for p, k in _걸린것), "저 자신을 부모로 삼지 않는다")

print("\n== 흔들기를 바꿔도 결론이 안 뒤집힌다 ==")
_결 = {CT.비율(CT.셈(_A, "무작위", seed=s), "도약") for s in (1, 2, 3, 4, 5)}
ok(_결 == {0.0}, f"세상 A 는 어느 씨로도 무작위 도약이 0이다 ({_결})")
_결B = [CT.비율(CT.셈(_B, "무작위", seed=s), "도약") for s in (1, 2, 3, 4, 5)]
ok(all(v > 0 for v in _결B), f"세상 B 는 어느 씨로도 0이 아니다 ({_결B})")

print("\n== 호출 0회다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "control.py").read_text(encoding="utf-8")
ok("llm_pool" not in _src and "GEMINI" not in _src, "대조군은 LLM 을 안 부른다")
ok("raise NotAProblem" not in _src and "del " not in _src,
   "**아무것도 기각하지 않는다** -- 숫자를 만들 뿐이다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 대조군: 두 세상 가르기 · 계보 피하기 · 씨 흔들기 -- 통과")
