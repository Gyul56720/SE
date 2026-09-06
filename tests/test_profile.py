"""프로필 -- **표본과 원고를 같은 자로 재서 수 한 줄로 만든다.**

지금까지는 프롬프트를 고치고 "나아진 것 같다" 를 눈으로 판단했다. 이 세션에서 되돌린
것들(예문 도배 · 번역투 · 늘어짐)이 전부 그래서 늦게 발견됐다. 여기서 고정하는 계약:

  · **원문은 이 파일에서 끝난다.** 밖으로 나가는 것은 수뿐이다
  · 길이에 안 휘둘린다 -- 비율과 분포만 담는다
  · 꼬리 조각은 안 잰다 -- 통계가 아니라 잡음이다

실행: python3 tests/test_profile.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import profile as P                                        # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


HERE = Path(__file__).resolve().parent
JOB = (HERE / "sample_job.txt").read_text(encoding="utf-8")
OUT = (HERE / "sample_outside.txt").read_text(encoding="utf-8")

print("[측정] **좋은 글 두 편이 서로 다르게 나와야 한다**")
print("      ← 다 같은 수가 나오면 그 자는 아무것도 못 가른다.")
a, b = P.measure(JOB), P.measure(OUT)
ok(a and b, "둘 다 재진다")
diff = [k for k in P.AXES if abs(a[k] - b[k]) > 0.05 * max(1.0, abs(a[k]))]
ok(len(diff) >= 5, f"두 표본이 여러 축에서 갈린다 ({len(diff)}축: {diff[:5]})")
ok(b["dialog"] == 0 and a["dialog"] > 0, "대사 없는 글과 있는 글을 가른다")

print()
print("[길이] **길이에 안 휘둘린다** -- 두 배로 늘려도 비율은 그대로")
twice = P.measure(JOB + "\n" + JOB)
for k in ("da_share", "long", "dialog", "glue"):
    ok(abs(twice[k] - a[k]) < 0.08, f"{k}: {a[k]:.2f} -> {twice[k]:.2f}")
ok(twice["_chars"] > a["_chars"], "글자 수는 따로 들고 있는다")

print()
print("[분포] **가운뎃값을 쓴다** -- 토막 하나가 튀어도 안 흔들린다")
ok(P.summary([1, 1, 1, 1, 100])["mid"] == 1, "튀는 값 하나에 안 끌려간다")
ok(P.summary([])["n"] == 0, "빈 것도 죽지 않는다")
s = P.summary([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
ok(s["lo"] < s["mid"] < s["hi"], f"폭도 같이 낸다 ({s['lo']}~{s['hi']})")

print()
print("[꼬리] **짧은 토막은 안 잰다** -- 잡음이 평균을 흔든다")
d = Path(tempfile.mkdtemp()) / "c"
(d / "S").mkdir(parents=True)
shutil.copy(HERE / "sample_job.txt", d / "S" / "01-01-001.txt")
(d / "S" / "01-01-002.txt").write_text("짧다." * 5, encoding="utf-8")
w = P.profile(d)
ok(len(w["S"]["da_share"]) == 1, f"긴 것 하나만 셌다 ({len(w['S']['da_share'])}개)")
ok(P.MIN_UNIT >= 1000, f"문턱이 있다 ({P.MIN_UNIT}자)")

print()
print("[표] **작품끼리 견줄 수 있어야 한다**")
(d / "T").mkdir()
shutil.copy(HERE / "sample_outside.txt", d / "T" / "01-01-001.txt")
(d / "T" / "01-01-002.txt").write_text(OUT + "\n" + OUT, encoding="utf-8")
dig = P.digest(P.profile(d))
ok(set(dig["works"]) == {"S", "T"}, "작품마다 한 줄")
ok(all(k in dig["all"] for k in P.AXES), "전체 요약도 낸다")
t = P.table(dig)
ok("sent_len" in t and "토막" in t, "표로 찍힌다")
ok(all(len(line) < 120 for line in t.split("\n")), "칸이 안 깨진다  ← 문단 길이만 천 단위다")

print()
print("[원문] **원문은 여기서 끝난다**")
print("      ← 원문 조각이 프롬프트로 새면 원고가 그것으로 도배된다. 다섯 번 겪었다.")
m = P.measure(JOB)
ok(all(isinstance(v, (int, float)) for v in m.values()),
   "프로필에 담기는 것은 수뿐이다  ← 문자열이 하나도 없다")
src = (Path(P.__file__)).read_text(encoding="utf-8")
ok("style" not in src.split("import")[1][:200], "프롬프트 쪽을 건드리지 않는다")

print()
if fails:
    print(f"프로필: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("프로필: 측정 · 길이 무관 · 분포 · 꼬리 · 표 · 원문 격리 -- 통과")
