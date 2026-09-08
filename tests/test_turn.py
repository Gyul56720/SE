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
ok(T.MIN_CHARS == 50000, f"원고 바닥은 5만 자다 ({T.MIN_CHARS:,})  ← 사람이 정한 운영점")
ok(_m["need"] >= T.MIN_CHARS, "창 계산보다 5만 자 바닥이 세면 그쪽이 이긴다")
ok(T.measure("가" * 49000, win=2000, stride=500)["ok"] is False,
   "창이 충분해도 5만 자 아래면 안 잰다  ← 바닥이 따로 있다")

print()
print("[밀도] **반전 수는 창 수에 휘둘린다 -- 만 자당으로 본다**")
print("      ← 논문의 9.92 와 우리 21 을 나란히 두면 안 된다. 창·보폭이 다르면")
print("        점의 개수가 달라지고 반전 수도 따라 달라진다. 보폭은 못 찾았다.")
# **5만 자를 넘겨야 잰다** -- 바로 위에서 그 바닥을 검사했다.
_long = ("좋다 기쁘다 웃었다 따뜻한 " * 40 + "싫다 슬프다 울었다 차가운 " * 40) * 50
assert len(_long) > T.MIN_CHARS, f"시험 글이 바닥보다 짧다 ({len(_long):,})"
_m2 = T.measure(_long, win=T.WIN, stride=T.STRIDE)
ok(_m2["ok"] and "density" in _m2, "밀도를 같이 낸다")
ok(abs(_m2["density"] - _m2["turns"] / (_m2["chars"] / 10000)) < 0.02,
   f"밀도 = 반전 / (글자수/만) ({_m2['density']})")
_tb2 = T.table(_m2)
ok("만 자당" in _tb2 and "목표" in _tb2, "목표와 나란히 찍는다")
ok("나란히 두지 마라" in _tb2, "논문 수와 직접 비교하지 말라고 못박는다")
ok("엎은 원고" in _tb2, "바닥이 어디서 왔는지 밝힌다")
ok(T.WIN == 10000 and T.STRIDE == 2500,
   f"창 기본값은 실측으로 골랐다 ({T.WIN:,}/{T.STRIDE:,})  ← 두 원고에서 흔들림이 제일 고른 자리")
ok(T.AIM > max(T.DROPPED),
   f"목표({T.AIM})가 엎은 원고의 최대({max(T.DROPPED)})보다 높다"
   "  ← 엎은 것에서 목표가 아니라 바닥을 뽑았다")

print()
print("[신뢰도] **자가 제 흔들림을 같이 낸다**")
print("      ← 같은 글이면 어디서부터 자르든 같은 수가 나와야 한다. 안 그러면")
print("        그 수를 믿을 이유가 없고, 숨기는 것보다 같이 내놓는 편이 정직하다.")
_up = ("좋다 기쁘다 웃었다 따뜻한 " * 40 + "싫다 슬프다 울었다 차가운 " * 40) * 50
_m = T.measure(_up, win=2000, stride=500)
ok(_m["ok"], "충분히 길면 잰다")
ok("spread" in _m and "counts" in _m, "흔들림과 시작점별 값을 같이 낸다")
ok(len(_m["counts"]) == T.ORIGINS, f"시작점 {T.ORIGINS}군데에서 잰다")
_tb = T.table(_m)
ok("흔들림" in _tb, "표에 흔들림이 나온다")
ok(("믿을 만하다" in _tb) or ("믿지 마라" in _tb) or ("반쯤만" in _tb),
   "믿어도 되는지 말로 적어 준다")
ok("나란히 두지 마라" in _tb,
   "논문 수와 직접 견주지 말라고 못박는다  ← 창·보폭이 다르면 반전 수는 비교가 안 된다")

print()
print("[되먹임] **자를 시키지 않고 일을 시킨다**")
print("      ← '감성어를 더 넣어라' 라고 하면 모델은 사전을 맞추러 간다. 밝은 낱말과")
print("        어두운 낱말을 번갈아 뿌리면 이 자는 속는다. 그건 이야기가 뒤집힌 것이")
print("        아니라 낱말이 뒤집힌 것이다.")
# **5만 자를 넘겨야 한다** -- 그 아래에서는 되먹임이 아예 안 나온다(바로 아래에서 검사).
_flat = {"chunks": ["좋다 기쁘다 웃었다 따뜻한 " * 250] * 16, "ledger": {}}
assert sum(len(c) for c in _flat["chunks"]) > T.MIN_CHARS
_b = T.brief(_flat)
ok("[국면]" in _b, "뒤집힘이 모자라면 되먹인다")
for _w in ("정서가", "감성어", "반전", "극성", "사전"):
    ok(_w not in _b, f"되먹임에 '{_w}' 가 안 나온다  ← 자를 시키면 자를 속인다")
ok("사건이지 기분이 아니다" in _b, "기분 말고 사건으로 뒤집으라고 한다")
ok("뒤집고 원래대로 돌아오면" in _b, "되돌아오면 안 뒤집힌 것이라고 못박는다")
ok(T.brief({"chunks": [], "ledger": {}}) == "", "첫 덩어리에는 안 나온다")
ok(T.brief({"chunks": ["x" * 3000], "ledger": {}}) == "",
   "5만 자 아래면 안 나온다  ← 잴 수가 없다")

print()
print("[배선] **프롬프트에 실린다. 다만 짧으면 안 실린다**")
from novel import flow                                                # noqa: E402
_p = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=_flat["chunks"]))
ok("[국면]" in _p, "뒤집힘이 모자라면 프롬프트에 실린다")
ok(not any(w in _p for w in ("정서가", "감성어", "극성")),
   "프롬프트 어디에도 자의 낱말이 안 샌다")
_p2 = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=["x" * 300]))
ok("[국면]" not in _p2, "짧으면 안 실린다  ← 지금까지의 프롬프트 그대로다")

print()
print("[사전] **저장소에 안 들어간다. 대신 받아 온다** -- 라이선스 표기가 없다")
_src = (Path(__file__).resolve().parent.parent / "novel" / "turn.py").read_text(encoding="utf-8")
# G016: 문서 계약 -- 여기서 재는 것은 **동작이 아니라 문서**다. 사전을 왜 저장소에
# 안 담는지는 코드로 드러나지 않고(안 담는 것이니 코드가 없다) 적어 둔 것이 전부다.
# 진짜 동작(무시 규칙 · 못 받았을 때의 실패)은 바로 아래 줄들이 잰다.
ok("KnuSentiLex" in _src and "라이선스" in _src,
   "어디서 받는지와 왜 안 담는지 **적혀 있다**  ← 문서 계약이다, 동작이 아니다")
_ig = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
ok("novel/knu/" in _ig, "무시 규칙에 있다")
# **auto=False 로 물어야 한다.** auto 로 두면 실제로 받아 오려 들고, 여기는 망이
# 되는 기계라 엉뚱한 경로에 클론이 성공한다(실측: 시험이 /없는 디렉토리를 만들었다).
# 받아 오는 길과 못 받았을 때의 길은 따로 검사해야 한다.
_saved, T._CACHE = T._CACHE, None
_saved_path, T.LEX_PATH = T.LEX_PATH, Path("/없는/경로/SentiWord_Dict.txt")
_died = ""
try:
    T.lexicon(auto=False)
except T.MissingLexicon as e:
    _died = str(e)
T._CACHE, T.LEX_PATH = _saved, _saved_path
ok("git clone" in _died and "DRIFT_SENTI_LEX" in _died,
   "받아 오지 못하면 사실대로 실패하고 받는 법을 알려 준다  ← 조용히 0 을 내면 안 된다")
ok(hasattr(T, "fetch") and callable(T.fetch),
   "없으면 받아 오는 길이 있다  ← 손으로 한 줄 치게 하면 VM 에서 그 줄을 빼먹는다")
# G016: 문서 계약 -- 받아 오는 **동작**은 바로 위 두 줄이 쟀다(못 받으면 사실대로
# 실패하는가 · fetch 가 있는가). 여기서 재는 것은 그 까닭을 적어 뒀는가뿐이다.
ok("코드가 서버에 도달하지 못하는" in _src,
   "왜 자동으로 받는지 **적어 뒀다**  ← 이 저장소가 네 번 데인 그 자리다")

print()
if fails:
    print(f"반전: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("반전: 읽기 · 반전 · 짧으면 거절 · 신뢰도 · 진단만 · 사전 격리 -- 통과")
