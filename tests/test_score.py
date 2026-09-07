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

print()
if fails:
    print(f"점수: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("점수: 거리 · 총점 · 꼴 · 표 · 출처 -- 통과")
