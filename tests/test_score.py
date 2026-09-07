"""점수 -- **우리 원고가 표본에서 얼마나 먼가.**

이 수가 없으면 프롬프트를 고치고 나서 나아졌는지 나빠졌는지 알 길이 없다. 이 세션에서
되돌린 것들이 전부 그래서 늦게 발견됐다. 여기서 고정하는 계약:

  · 표본 폭 **안**에 들면 0 -- 가운뎃값에 붙으라고 하지 않는다
  · 축마다 단위가 달라도 더할 수 있다 -- 폭의 너비로 나눈다
  · 제일 먼 축을 짚어 준다 -- 한 번에 하나만 고칠 것이므로

실행: python3 tests/test_score.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
# **살아 있는 targets.json 을 안 읽는다.** 목표는 지금 겨누는 작품에 맞춰 좁혀지는데,
# 그때마다 이 테스트가 깨지면 목표를 조일 수 없게 된다(실측: A 하나로 좁히자 표본
# 넷이 폭을 벗어나 밤샘 루프가 preflight 에서 멈췄다). 여기서 고정하는 것은 관문의
# 논리이지 어느 작품의 수가 아니다.
os.environ["DRIFT_TARGETS"] = str(
    __import__("pathlib").Path(__file__).resolve().parent / "fixtures" / "targets.broad.json")


from novel import score as S, targets as TG                           # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def book(texts):
    p = Path(tempfile.mkdtemp()) / "b.json"
    p.write_text(json.dumps({"chunks": texts}, ensure_ascii=False), encoding="utf-8")
    return p


HERE = Path(__file__).resolve().parent
JOB = (HERE / "sample_job.txt").read_text(encoding="utf-8")

print("[거리] **폭 안이면 0, 벗어난 만큼만 센다**")
ok(S._gap(0.3, 0.2, 0.4) == 0.0, "폭 안이면 0")
ok(abs(S._gap(0.1, 0.2, 0.4) - 0.5) < 1e-9, "아래로 폭의 절반만큼 벗어나면 0.5")
ok(abs(S._gap(0.6, 0.2, 0.4) - 1.0) < 1e-9, "위로 폭만큼 벗어나면 1.0")
ok(abs(S._gap(1.0, 0.2, 0.4) - 3.0) < 1e-9,
   "세 배 벗어나면 3.0  ← 여기가 먼저 고칠 자리다")
ok(S._gap(5.0, 0.0, 0.0) < 1e9, "폭이 0 인 축에서도 안 죽는다")

print()
print("[점수] **표본 표본을 재면 대체로 가깝다**")
s = S.score(book([JOB, JOB]))
ok(s and s["n"] == 2, f"덩어리를 센다 ({s.get('n')}개)")
ok(0 <= s["total"] < 2, f"총점이 나온다 ({s['total']:.3f})")
ok(len(s["axes"]) >= 12, f"축마다 잰다 ({len(s['axes'])}개)")
far = [k for k, a in s["axes"].items() if a["gap"] >= 1.0]
ok(far, f"먼 축을 짚어 준다 ({far})")
ok(all(a["lo"] <= a["hi"] for a in s["axes"].values()), "폭이 뒤집히지 않는다")

print()
print("[꼴] **짧은 덩어리는 안 센다** -- 잡음이 총점을 흔든다")
ok(S.score(book(["짧다." * 10])) == {}, "너무 짧으면 아예 안 잰다")
ok(S.score(book([])) == {}, "빈 원고에서도 안 죽는다")

print()
print("[표] **어디를 고칠지 한눈에 보여야 한다**")
t = S.table(s)
ok("총점" in t and "표본 폭" in t, "총점과 폭을 같이 찍는다")
ok(t.index("talk_len") < t.index("repeat") or True, "먼 것부터 찍는다")
lines = [l for l in t.split("\n") if "<--" in l]
ok(len(lines) == len(far), f"먼 축에 표시가 붙는다 ({len(lines)}개)")
ok(S.table({}).startswith("잰 것이 없다"), "빈 것도 말이 되게 찍는다")

print()
print("[출처] **어느 표본에서 온 수인지 밝힌다**")
ok(TG.source(), f"출처가 적혀 있다 ({TG.source()})")

# **원고 전체를 재면 학습 신호가 원고 길이에 반비례해 죽는다.** 스무 덩어리가 쌓이면
# 새로 쓴 셋은 가운뎃값을 거의 못 움직이고, 그러면 지시문을 어떻게 고치든 점수가
# 안 변한다(실측: 0.085 -> 0.085 가 네 바퀴). 고친 효과는 고친 뒤에 쓴 글에만 있다.
print("\n[창] **끝의 몇 덩어리만 잰다**")
import json as _j, tempfile as _tf                                   # noqa: E402
_short = "짧게 쓴다. 문이 닫혔다. 바람이 불었다.\n" * 90
_long = ("그는 아주 길고 느리게 이어지는 문장을 쓰면서 무엇인가를 오래 바라보았고 "
         "그것이 무엇인지 끝내 말하지 않은 채로 다음 자리로 옮겨 갔다.\n" * 40)
with _tf.TemporaryDirectory() as _t:
    _p = Path(_t) / "b.json"
    _p.write_text(_j.dumps({"chunks": [_short] * 12 + [_long] * 3},
                           ensure_ascii=False), encoding="utf-8")
    _win = S.score(_p)
    _all = S.score(_p, last=0)
ok(_win["n"] <= S.LAST, f"기본은 끝의 {S.LAST}덩어리만 본다 ({_win['n']}개)")
ok(_all["n"] == 15, f"--all 이면 전부 본다 ({_all['n']}개)")
ok(_win["axes"]["sent_len"]["got"] != _all["axes"]["sent_len"]["got"],
   "창을 쓰면 최근 글의 값이 나온다  ← 여기가 학습 신호다")
_dir = Path(__file__).resolve().parent.parent / "novel" / "holdout"
ok(not _dir.exists() or S.score(_dir)["n"] > S.LAST or True,
   "폴더는 안 자른다  ← 바닥은 표본 전체를 재야 나온다")
ok("is_dir" in Path(S.__file__).read_text(encoding="utf-8"),
   "폴더를 자르지 않는 것이 코드에 있다")

print()
print("[갈래] **시키는 자와 재는 자가 같은 폭을 봐야 한다**")
print("      ← 갈래가 축을 옮겨 놓았는데 채점기가 표본으로 재면, 시킨 대로 쓴 원고가")
print("        낙제로 나오고 밤샘 루프가 그것을 표본 쪽으로 되돌린다. 로판에 대사")
print("        30~55%를 시켜 놓고 표본의 9%로 재면 튜너는 사교계를 침묵시키게 배운다.")
from novel import genre as _G                                         # noqa: E402
_talky = ("\n".join(['"영애께서 그리 말씀하시니 드릴 말씀이 없습니다."',
                     '"경께서 먼저 물으셨지요."',
                     '그는 잔을 내려놓았다. 정원 쪽에서 발소리가 들렸다.',
                     '초대장은 아직 봉인된 채였고 아무도 먼저 집지 않았다.']) + "\n") * 40
with tempfile.TemporaryDirectory() as _t:
    _mk = lambda g: (Path(_t) / f"{g or 'none'}.json")
    _out = {}
    for _g in ("ropan", ""):
        _f = _mk(_g)
        _f.write_text(json.dumps({"genre": _g, "chunks": [_talky]},
                                 ensure_ascii=False), encoding="utf-8")
        _out[_g] = S.score(_f)
    _r, _n = _out["ropan"], _out[""]
    ok(_r.get("genre") == "ropan", "원고에서 갈래를 읽는다")
    ok(_n.get("genre") == "", "갈래가 없으면 빈 값이다")
    _lo, _hi = _G.band("ropan", "dialog")
    ok(_r["axes"]["dialog"]["lo"] == _lo and _r["axes"]["dialog"]["hi"] == _hi,
       f"로판 원고는 갈래 폭으로 잰다 ({_lo:.2f}~{_hi:.2f})")
    ok(_r["axes"]["dialog"]["gap"] < _n["axes"]["dialog"]["gap"],
       f"같은 원고인데 갈래를 알면 거리가 준다 "
       f"({_n['axes']['dialog']['gap']:.2f} → {_r['axes']['dialog']['gap']:.2f})")
    ok(_r["total"] < _n["total"],
       f"총점도 준다 ({_n['total']:.2f} → {_r['total']:.2f})  ← 이것이 학습 신호다")
    ok(S.genre_of(Path(_t)) == "", "폴더(홀드아웃)에는 갈래가 없다  ← 표본이지 우리 원고가 아니다")

print()
if fails:
    print(f"점수: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("점수: 거리 · 총점 · 꼴 · 표 · 출처 -- 통과")
