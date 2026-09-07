"""반전 -- **문헌에서 수가 붙은 유일한 성공 공식.** 그리고 아직 못 믿는 자.

Knight, Rocklage & Bart (2024) 가 약 3만 편에서 반전의 수와 크기를 재고 성공과
대조했다. 소설은 다운로드 +110%. 그래서 제일 먼저 집었는데 **자가 흔들려서 진단
도구로만 두었다**(EVIDENCE.md 22절).

여기서 고정하는 계약:

  · **프롬프트에 안 실린다** -- 흔들리는 자로 되먹임을 걸면 그 흔들림이 원고로 간다
  · **제 신뢰도를 같이 낸다** -- 시작점을 옮겨 재서 폭을 찍는다. 폭이 크면 믿지 마라
  · **짧으면 사실대로 거절한다** -- 창 넷에서 "반전이 많다" 는 말은 성립하지 않는다
  · **낱말 안쪽을 안 잡는다** -- 제일 긴 것부터 맞춘다
  · **사전 없이도 검사는 돈다** -- 사전은 저장소에 없다(라이선스 표기 없음)

실행: python3 tests/test_turn.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import turn as T                                           # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# **가짜 사전을 끼운다.** 진짜 사전은 저장소에 없다(라이선스 표기가 없어 안 담는다).
# 검사가 그것을 요구하면 CI 에서 조용히 건너뛰게 되고, 건너뛴 초록불은 검사한
# 빨간불보다 나쁘다 -- 이 저장소가 이미 배운 것이다.
T._CACHE = {"좋다": 2, "기쁘다": 2, "웃었다": 1, "따뜻한": 1,
            "싫다": -2, "슬프다": -2, "울었다": -1, "차가운": -1,
            "좋다가": 9}          # 낱말 안쪽 검사용 -- 더 긴 것이 이겨야 한다

print("[읽기] **제일 긴 것부터 맞춘다** -- 짧은 것을 먼저 잡으면 낱말 안쪽이 걸린다")
ok(T.valence("좋다")[0] == 2, "짧은 낱말을 잡는다")
ok(T.valence("좋다가")[0] == 9, "더 긴 것이 있으면 그쪽이 이긴다  ← 안 그러면 '좋다'가 걸린다")
ok(T.valence("아무것도 없는 문장")[1] == 0, "안 걸리면 0개다")
ok(T.valence("")[0] == 0.0, "빈 글은 0이다")
_v, _n = T.valence("좋다 싫다")
ok(_n == 2 and _v == 0.0, f"평균을 낸다 (+2, -2 → {_v})")

print()
print("[반전] **부호가 바뀌는 자리를 센다**")
ok(T.reversals([1, 2, 3, 4, 5])[0] == 0, "쭉 오르면 반전이 없다")
ok(T.reversals([1, 1, 1, 1, 1])[0] == 0, "평평하면 반전이 없다")
_t, _a = T.reversals([0, 5, 0, 5, 0, 5, 0])
ok(_t >= 2, f"오르내리면 반전이 잡힌다 ({_t}회)")
ok(_a > 0, f"크기도 낸다 ({_a:.3f})")
ok(T.reversals([1])[0] == 0 and T.reversals([])[0] == 0, "점이 없으면 0이다  ← 안 터진다")

print()
print("[짧으면 거절] **창 넷에서 '많다' 는 말은 성립하지 않는다**")
_m = T.measure("짧은 글", win=5000, stride=1250)
ok(_m["ok"] is False and _m["why"] == "짧다", "짧으면 사실대로 거절한다")
ok(_m["need"] > _m["chars"], f"얼마나 필요한지 말한다 ({_m['need']:,}자)")
ok("짧다" in T.table(_m) and "필요하다" in T.table(_m), "표에도 이유가 나온다")
ok(T.MIN_WINDOWS >= 8, f"창 최소 개수를 둔다 ({T.MIN_WINDOWS}개)")

print()
print("[신뢰도] **자가 제 흔들림을 같이 낸다**")
print("      ← 같은 글이면 어디서부터 자르든 같은 수가 나와야 한다. 안 그러면")
print("        그 수를 믿을 이유가 없고, 숨기는 것보다 같이 내놓는 편이 정직하다.")
_up = ("좋다 기쁘다 웃었다 따뜻한 " * 40 + "싫다 슬프다 울었다 차가운 " * 40) * 6
_m = T.measure(_up, win=2000, stride=500)
ok(_m["ok"], "충분히 길면 잰다")
ok("spread" in _m and "counts" in _m, "흔들림과 시작점별 값을 같이 낸다")
ok(len(_m["counts"]) == T.ORIGINS, f"시작점 {T.ORIGINS}군데에서 잰다")
_tb = T.table(_m)
ok("흔들림" in _tb, "표에 흔들림이 나온다")
ok(("믿을 만하다" in _tb) or ("믿지 마라" in _tb) or ("반쯤만" in _tb),
   "믿어도 되는지 말로 적어 준다")
ok("우리 목표가 아니다" in _tb,
   "논문 수를 목표로 오해하지 않게 못박는다  ← 영어 소설 5만 낱말에서 나온 수다")

print()
print("[진단만] **프롬프트에 안 실린다**")
_flow = (Path(__file__).resolve().parent.parent / "novel" / "flow.py").read_text(encoding="utf-8")
ok("turn" not in _flow.replace("turned", "").replace("return", ""),
   "flow 가 turn 을 안 부른다  ← 흔들리는 자로 되먹임을 걸면 그것이 원고로 간다")
ok(not hasattr(T, "brief"), "brief() 가 없다  ← 되먹임을 낼 자리 자체를 안 만들었다")

print()
print("[사전] **저장소에 안 들어간다** -- 라이선스 표기가 없다")
_src = (Path(__file__).resolve().parent.parent / "novel" / "turn.py").read_text(encoding="utf-8")
ok("KnuSentiLex" in _src and "라이선스" in _src, "어디서 받는지와 왜 안 담는지 적혀 있다")
_ig = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
ok("novel/knu/" in _ig, "무시 규칙에 있다")
_saved, T._CACHE = T._CACHE, None
_saved_path, T.LEX_PATH = T.LEX_PATH, Path("/없는/경로/SentiWord_Dict.txt")
_died = ""
try:
    T.lexicon()
except T.MissingLexicon as e:
    _died = str(e)
T._CACHE, T.LEX_PATH = _saved, _saved_path
ok("git clone" in _died and "DRIFT_SENTI_LEX" in _died,
   "사전이 없으면 사실대로 실패하고 받는 법을 알려 준다  ← 조용히 0 을 내면 안 된다")

print()
if fails:
    print(f"반전: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("반전: 읽기 · 반전 · 짧으면 거절 · 신뢰도 · 진단만 · 사전 격리 -- 통과")
