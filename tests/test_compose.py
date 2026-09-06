"""**프롬프트를 축에서 짓는다** -- 손으로 쓴 문장론은 한 줄도 안 들어간다.

지금까지의 프롬프트는 사람이 쓴 작법서였다(7,000자 페르소나 + 규칙 블록). 표본을 재
보니 그 요구가 표본과 어긋나 있었고, 어긋난 요구가 원고를 망기고 있었다 -- 늘어짐의
뿌리가 우리 지시였다. 그래서 규칙 하나로 다시 짓는다:

    **프롬프트에 들어가는 모든 줄은 재는 축에 매여 있어야 한다. 못 재는 것은 안 쓴다.**

여기서 고정하는 것은 그 규칙이다.

실행: python3 tests/test_compose.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import compose, flow, profile as PF, targets as TG         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


BK = flow.blank()
BK["chunks"] = ["그는 갔다.\n" * 300]

print("[규칙] **모든 줄이 재는 축에 매여 있다**")
ok(set(compose.SAY) <= set(PF.AXES), "이름을 붙인 축은 전부 재는 축이다")
# 폭이 아직 없는 축(표본을 다시 재야 나오는 것)은 **조용히 빠진다** -- 목표를
# 지어내지 않는다. 이름만 있고 폭이 없으면 프롬프트에 안 실린다.
_named = [k for k in compose.SAY if TG.band(k)]
ok(len(_named) >= 12, f"폭이 있는 축이 프롬프트에 실린다 ({len(_named)}개)")
ok(all(f"{compose.SAY[k]} =" in flow.write_prompt(flow.blank()) for k in _named),
   "폭이 있는 축은 하나도 안 빠진다")
ok(not any(f"{compose.SAY[k]} =" in flow.write_prompt(flow.blank())
           for k in compose.SAY if not TG.band(k)),
   "폭이 없는 축은 안 실린다  ← 목표를 지어내지 않는다")
_p = flow.write_prompt(BK)
for _gone in ("[문장]", "[상황]", "[점층]", "[리듬]", "[낱말]", "[정밀]", "[심층]",
              "[아이러니]", "[스윙]", "[여백]", "[농담]", "[결]"):
    ok(_gone not in _p, f"손으로 쓴 작법서 항목이 없다: {_gone}")
ok("건조" not in _p and "하루키" not in _p, "문체를 말로 규정하지 않는다")

print()
print("[수] **목표는 표본에서 오고 덩어리마다 흔들린다**")
_a1 = dict(compose.aims("씨", 1, list(compose.SAY)))
_a2 = dict(compose.aims("씨", 2, list(compose.SAY)))
ok(_a1 != _a2, "덩어리마다 다르다  ← 매번 같은 몫이면 그것이 단조로움이다")
for _k, _v in _a1.items():
    _lo, _hi = TG.band(_k)
    ok(_lo <= _v <= _hi, f"{_k}: 표본 폭 안이다 ({_v:.2f} ∈ {_lo:.2f}~{_hi:.2f})")
ok(compose.aims("씨", 3, list(compose.SAY)) == compose.aims("씨", 3, list(compose.SAY)),
   "같은 씨앗·번호면 같다  ← 이어 써도 재현된다")

print()
print("[고르기] **전부 보여 준다** -- 수정이 한 번뿐이니 처음이 자세해야 한다")
_blk = compose.target_block("씨", 4)
ok(compose.SHOW == 0, "기본은 **전부** 보여 준다  ← 수정이 한 번뿐이라 처음이 자세해야 한다")
ok(_blk.count("  · ") == len(_named), f"폭이 있는 축을 다 준다 ({_blk.count('  · ')}개)")
_vals = {tuple(re.findall(r"= \*\*([^*]+)\*\*", compose.target_block("씨", n)))
         for n in range(10)}
ok(len(_vals) > 5, f"값은 덩어리마다 다르다 ({len(_vals)}가지)")

print()
print("[짜임] **뼈대만 있다**")
ok("[분량]" in _p and "[세계" in _p and "끝부분" in _p, "분량 · 원장 · 꼬리")
ok(len(_p) < 5000, f"그래도 짧다 ({len(_p):,}자)  ← 예전은 13,417자였다")
_first = flow.write_prompt(flow.blank())
ok("첫 문장" in _first or "여는 좌표" in _first, "첫 덩어리에는 여는 자리를 준다")
ok(800 < len(_first) < 3000,
   f"첫 덩어리는 수와 설명으로 채운다 ({len(_first):,}자)  ← 꼬리가 없는 대신 자세히")

print()
print("[예문] **하나도 없다**")
# **프롬프트에 예문이 있는지를 본다.** 코드의 축 이름이나 주석이 아니라, 실제로
# 모델에게 나가는 글에 따옴표로 묶인 본보기 문장이 있는지다 -- 그것이 도배를 부른다.
_body = _p.split("[지금까지의 끝부분", 1)[0]      # 꼬리는 원고지 예문이 아니다
_quoted = re.findall(r'["“‘][가-힣][^"”’]{10,}["”’]', _body)
ok(not _quoted, f"프롬프트에 본보기 문장이 없다 ({_quoted[:1]})")
ok("처럼)" not in _body and "같이)" not in _body, "'~처럼' 으로 예를 달지 않는다")
ok(not re.search(r"\d{4}년", _body), "프롬프트에 연도가 없다")
ok(not re.search(r"[A-Za-z]{4,}", _body.replace("DRIFT", "")),
   "영어 낱말이 안 섞인다  ← 축 이름은 사람 말로 옮겨서 준다")


print()
print("[초고] **처음이 자세해야 한다** -- 수정은 일괄 한 번뿐이다")
print("      ← 걸린 문장들을 한 장에 담아 한 번에 고치고 끝낸다. 통째로 다시 쓰지")
print("        않는다. 그러니 초고 프롬프트가 다 말해 줘야 한다.")
_dr = flow.write_prompt(flow.blank())
ok(_dr.count("  · ") >= 12, f"축을 다 준다 ({_dr.count('  · ')}개)")
ok(_dr.count("\n      ") >= 12, "축마다 어떻게 맞추는지도 준다")
from novel import dyn as _dyn                                         # noqa: E402
ok(all("aim" in v for k, v in _dyn.load().items() if k in compose.SAY),
   "그 설명은 코드가 아니라 데이터다(directives.json 의 aim)")
ok("[이 대목에서 일어날 일]" in _dr, "무엇이 달라질지도 한 걸음 준다")
_src = Path(flow.__file__).read_text(encoding="utf-8")
ok("고칠 것을 **전부** 모은다" in _src, "수정은 걸린 것을 다 모아 한 번에 한다")
ok("한꺼번에** 풀어" in _src or "한꺼번에" in _src, "한 문장에 겹친 딱지도 한 번에 푼다")

print()
if fails:
    print(f"짓기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("짓기: 규칙 · 수 · 고르기 · 짜임 · 예문 없음 · 초고 -- 통과")
