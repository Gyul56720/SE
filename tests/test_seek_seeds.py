r"""**씨앗을 여럿 둔다 -- 대상이 갈려야 계보가 갈린다.**

실측 2026-09-09, 원장 100개를 읽고: 도약 22개가 대조군을 통과했는데 **100개가 전부
5선 정렬망이었다.** 깊이 3까지 내려가도 물음이 "5선 정렬망이 ... 하는가" 다. 연산자
12개가 바꾸는 것은 술어뿐이고 대상은 한 번도 안 바뀐다.

씨앗이 하나뿐인 것이 그 원인이다. 모든 부모가 P1 의 후손이고, 프롬프트는 부모의
판정기를 보고 쓴다.

여기서 재는 것은 씨앗 다섯이 **정말 다른 대상인가** 다. 물음 문장이 다른 것으로는
모자란다 -- 후보꼴이 달라야 계보가 섞이지 않는다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_seeds.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from seek import audit as AU                                  # noqa: E402
from seek import judge as J                                   # noqa: E402
from seek import solve as SO                                  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


씨앗 = json.loads((뿌리 / "seek" / "seed.json").read_text(encoding="utf-8"))["problems"]

print("== 씨앗이 여럿이다 ==")
ok(len(씨앗) >= 5, f"다섯 이상 ({len(씨앗)}개)")
ok(len({p["물음"] for p in 씨앗}) == len(씨앗), "물음이 다 다르다")
ok(all(p["계보"]["부모"] == "-" for p in 씨앗), "다 씨앗이다 -- 부모가 없다")
ok(all(p["옮김"] == "" for p in 씨앗), "씨앗에는 옮김이 없다 -- 옮겨 올 부모가 없으니까")

print("\n== JSON 이 파이썬 소스와 안 어긋난다 ==")
_r = subprocess.run([sys.executable, str(뿌리 / "seek" / "seeds" / "build.py"), "--확인"],
                    capture_output=True, text=True, cwd=str(뿌리))
ok(_r.returncode == 0,
   f"**seed.json 이 seek/seeds/*.py 와 같다** -- 손으로 고치면 여기서 걸린다\n"
   f"        {_r.stdout.strip()}{_r.stderr.strip()}")

print("\n== 판정기가 후보꼴을 먼저 본다 ==")
# 안 보면 확장이 영영 안 잡힌다(reach 독스트링). 도약을 재려면 이게 있어야 한다
for p in 씨앗:
    got = J.judge(p, "이건 후보가 아니다")
    ok(not got.get("ok"),
       f"{p['id']} 는 엉뚱한 것을 받으면 터진다 -- {str(got.get('왜'))[:46]}")

print("\n== 공허한 씨앗이 없다 ==")
for p in 씨앗:
    g = AU.grade(p, n=300)
    ok(g["등급"] != "공허", f"{p['id']} 등급 {g['등급']} ({g['받음']}/{g['본것']})")
    ok(g["터짐"] == 0, f"{p['id']} 는 제 표본에 안 터진다 (터짐 {g['터짐']})")

print("\n== 다섯 다 실제로 풀린다 ==")
# **해가 있다는 것을 찾아서 보인다.** 못 푸는 씨앗을 심으면 그 가지는 영영 모름이다
답 = {}
for p in 씨앗:
    got = SO.search(p, tries=400000, seed=0, seconds=60.0)
    답[p["id"]] = got.get("답")
    ok(got.get("ok") and got.get("답") is not None,
       f"{p['id']} 를 찾았다 ({got.get('본것', 0):,}개 봤다)")

print("\n== 대상이 정말 갈렸다 ==")
# **물음 문장이 다른 것으로는 모자란다.** 후보꼴이 달라야 계보가 안 섞인다.
# 남의 답을 먹이면 못 읽어야 한다 -- 읽고 받으면 같은 대상을 다른 말로 적은 것이다.
겹침 = []
for a in 씨앗:
    for b in 씨앗:
        if a["id"] == b["id"] or 답[b["id"]] is None:
            continue
        got = J.judge(a, 답[b["id"]])
        if got.get("ok") and got.get("받음"):
            겹침.append(f"{a['id']} 가 {b['id']} 의 답을 받는다")
ok(not 겹침, f"**어느 씨앗도 남의 답을 안 받는다** ({겹침})")

읽힘 = sum(1 for a in 씨앗 for b in 씨앗
           if a["id"] != b["id"] and 답[b["id"]] is not None
           and J.judge(a, 답[b["id"]]).get("ok"))
ok(읽힘 <= len(씨앗),
   f"대부분은 **읽지도 못한다** (20쌍 중 읽히는 것 {읽힘}쌍)"
   "  <- 이것이 확장 판정이 서는 조건이다")

print("\n== 여러 갈래로 낳는다 ==")
# spread 는 부모를 ps[n % len(ps)] 로 고른다. 씨앗이 다섯이면 첫 다섯 바퀴가
# 다섯 갈래로 나간다 -- 하나면 첫 바퀴부터 한 갈래다.
from seek import spread as SP                                 # noqa: E402
led = {"seq": len(씨앗), "problems": [dict(p) for p in 씨앗]}
부모들 = []
for i in range(5):
    SP.step(led, lambda q: 부모들.append(q) or "[]", seed="t", n=i, k=1,
            log=lambda s: None)
탄것 = [p["물음"] for p in 씨앗
        if any(p["물음"][:20] in q for q in 부모들)]
ok(len(탄것) == len(씨앗),
   f"**첫 다섯 바퀴가 다섯 갈래로 나간다** ({len(탄것)}/{len(씨앗)})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 씨앗: 여럿 · 소스와 일치 · 꼴 검사 · 안 공허 · 풀림 · 대상 갈림 -- 통과")
