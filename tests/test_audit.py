"""**점검하는 자를 점검한다.**

사용자(2026-09-09): "모든 파이프라인 전부 다 점검해."

이 저장소가 같은 병을 네 번 앓았다 -- 적어 두고 안 부친 규칙(`--persona` · 첫회차
규율 · `echo.check` · `GENRE` 빈 값). 넷 다 **원고는 멀쩡히 나온다.** 그래서
`novel/audit.py` 가 배선을 찍는데, 그 자가 틀리면 이 저장소가 가장 싫어하는 것이 된다:
**검사하지 않은 초록불.** 그래서 여기서 자 자체에 이빨이 있는지 본다.

실행: python3 tests/test_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import audit                                              # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def states(book):
    return {n: st for n, st, _ in audit.wiring(book)}


print("[이빨] **꺼진 것을 꺼졌다고 하는가**")
_off = states(audit.sample(genre="", heat=0.0))
_dead = [n for n, st in _off.items() if st == "꺼짐"]
ok(len(_dead) >= 4, f"갈래 없는 원고에서 꺼진 것을 잡는다 ({len(_dead)}개: {', '.join(_dead[:4])})")
for _n in ("회차 각본", "당김", "갈래 꾸러미"):
    ok(_off.get(_n) == "꺼짐", f"  {_n} 이 꺼졌다고 말한다")

print("\n[초록] **켜진 것을 켜졌다고 하는가**")
_on = states(audit.sample(genre="lanobe", heat=0.6))
ok(not [n for n, st in _on.items() if st == "꺼짐"],
   f"제대로 켠 원고에는 꺼짐이 없다 ({[n for n, st in _on.items() if st == '꺼짐']})")
for _n in ("회차 각본", "당김", "갈래 꾸러미", "쾌감", "부상(영구)", "수위 본보기"):
    ok(_on.get(_n) == "켜짐", f"  {_n} 이 실린다")

print("\n[늑대소년] **차례가 아닌 것을 꺼졌다고 하지 않는가**")
# 개그는 한 덩어리 걸러, 첫 쪽 규율은 첫 덩어리에만. 그것을 다 '꺼짐' 이라고 하면
# 이 자가 늑대소년이 되고, 진짜 꺼진 것이 그 속에 묻힌다.
ok(_on.get("개그") == "차례아님", f"짝수 덩어리의 개그 ({_on.get('개그')})")
ok(_on.get("첫 쪽 규율") == "차례아님", f"둘째 덩어리의 첫 쪽 규율 ({_on.get('첫 쪽 규율')})")
_first = states(audit.sample(genre="lanobe", heat=0.6, chunks=0))
ok(_first.get("첫 쪽 규율") == "켜짐", "첫 덩어리에서는 켜진다  ← 차례가 오면 실린다")
_odd = states(audit.sample(genre="lanobe", heat=0.6, chunks=1))
ok(_odd.get("개그") == "켜짐", "홀수 덩어리에서는 개그가 실린다")

print("\n[인자] **drift.sh 가 넘기는 것을 flow 가 받는가**")
# 실측 2026-09-09: drift.sh 가 없는 인자 `--body` 를 넘기고 있었다. 그 손잡이를 쓰면
# 런이 아예 안 뜬다 -- `unrecognized arguments: --body`.
_f = audit.flags()
ok(not _f.get("_없다"), "drift.sh 를 찾는다")
ok(_f["안 받는다"] == [], f"지금은 전부 받는다 ({_f['안 받는다']})")
ok(len(_f["넘긴다"]) >= 8, f"넘기는 인자를 센다 ({len(_f['넘긴다'])}개)")

# **줄 이음을 안 펴면 이 버그를 놓친다.** `--body` 가 `set --` 의 둘째 줄에 있었다.
_tmp = Path(REPO / "tests" / "_audit_sh_tmp.sh")
_tmp.write_text('set -- --out "$BOOK" --chars 1 \\\n       --없는인자 9 --genre x\n', encoding="utf-8")
try:
    _bad = audit.flags(_tmp)
    ok("없는인자" not in "".join(_bad["넘긴다"]), "한글 인자는 안 센다(꼴이 다르다)")
    _tmp.write_text('set -- --out "$BOOK" --chars 1 \\\n       --nosuchflag 9\n', encoding="utf-8")
    _bad = audit.flags(_tmp)
    ok("nosuchflag" in _bad["안 받는다"],
       f"이어진 줄의 인자도 잡는다 ({_bad['안 받는다']})  ← 안 펴면 놓친다")
finally:
    _tmp.unlink(missing_ok=True)

print("\n[축 · 손 · 모듈]")
_a = audit.axes()
ok(len(_a["live"]) >= 10, f"프롬프트를 움직이는 축을 센다 ({len(_a['live'])}개)")
ok(_a["mute"] == [], f"폭만 있고 말이 없는 축은 없다 ({_a['mute']})")
_h = audit.hands()
ok("echo.dedup" in _h["고침"], f"원고를 고치는 손을 센다 ({_h['고침']})")
ok("echo" in _h["장부에만"], "장부에만 남는 것도 센다")
_orp = [m for m in audit.orphans() if m not in audit.TOOLS]
ok(_orp == [], f"연장이 아닌 고아 모듈이 없다 ({_orp})")
ok("heat" in [k for k, _ in audit.switches()],
   "값이 뜻 없는 손잡이를 짚는다  ← HEAT=0.6 도 1.0 도 같다")

print("\n[보고]")
_r = audit.report(audit.sample())
for _sec in ("[배선]", "[축]", "[손]", "[손잡이]", "[인자]", "[모듈]"):
    ok(_sec in _r, f"  {_sec}")
ok(audit.main(["--genre", "lanobe"]) == 0, "명령줄이 돈다")

print()
if fails:
    print(f"점검: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("점검: 이빨 · 초록 · 늑대소년 · 인자 · 축 · 손 · 모듈 · 보고 -- 통과")
