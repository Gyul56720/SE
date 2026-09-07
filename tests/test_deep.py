"""**의미층을 재서 시킨다** -- 인과 · 갈등 · 복선 · 거리 · 속도.

문면만 맞추면 문장은 겹쳐도 이야기는 안 겹친다. 연구용으로 최대한 복제하는 것이
목적이면 의미층도 재야 하고, 재려면 읽는 것을 시켜야 한다. 여기서 고정하는 계약:

  · **한 번에 다 묻는다** -- 칸마다 따로 물으면 스물두 배가 든다. 토막당 한 번,
    spine 이 칸 하나 받던 그 호출로 스물두 칸을 받는다
  · **정해진 낱말이 아니면 버린다** -- 새 낱말이 섞이면 분포가 조용히 망가진다
  · **분포가 아니라 그 대목의 값을 시킨다** -- 복제가 목적이면 "대개 장면이다" 가
    아니라 "이번 대목은 여파다" 라야 한다
  · **같은 자로 우리 원고도 잰다** -- 재지 않는 요구는 지켜졌는지 알 수 없다

실행: python3 tests/test_deep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import deep                                               # noqa: E402

fails = []


def ok(cond, label):
    print(("  OK  " if cond else "  실패 ") + label)
    if not cond:
        fails.append(label)


print("[묻기 -- 한 번에 다]")
q = deep.ask("어떤 대목이다.")
ok(all(k in q for k in deep.PICK), f"고르는 칸 {len(deep.PICK)}개를 다 묻는다")
ok(all(k in q for k in deep.NUM), f"수로 받는 칸 {len(deep.NUM)}개를 다 묻는다")
ok("원문 문장을 옮기지 마라" in q, "원문을 옮기지 말라고 못박는다")
ok(len(q) < 3000, f"물음이 짧다 ({len(q):,}자)")

print("\n[다듬기 -- 정해진 낱말이 아니면 버린다]")
raw = {"장면꼴": "장면", "속도": "빠름", "갈등세기": "3", "인물수": 99,
       "무엇": "문이 잠겼다", "누구": "그", "심은것": "열쇠"}
c = deep.clean(raw)
ok(c["장면꼴"] == "장면", "정해진 낱말은 그대로 둔다")
ok(c["속도"] == "", "없는 낱말('빠름')은 버린다  ← 새 낱말이 분포를 망친다")
ok(c["갈등세기"] == 3, "문자로 온 수도 수로 받는다")
ok(c["인물수"] == 12, "범위를 넘으면 범위 안으로 접는다")
ok(c["심은것"] == "열쇠", "자유 서술 세 칸은 그대로")

print("\n[분포]")
recs = []
for i in range(12):
    r = deep.clean({"장면꼴": "장면" if i % 3 else "여파", "갈등세기": i % 5,
                    "거둔거리": 4 if i == 5 else 0, "심은것": "열쇠" if i == 2 else "",
                    "속도": "장면", "닫는법": "질문"})
    recs.append(r)
d = deep.learn(recs)
ok(abs(d["share"]["장면꼴"]["장면"] - 8 / 12) < 0.01,
   f"고르는 칸은 몫으로 낸다 (장면 {d['share']['장면꼴']['장면']:.0%})")
ok("갈등세기" in d["band"], "수는 폭으로 낸다")
ok(d["복선"]["사거리 가운데"] == 4,
   "복선 사거리는 거둔 것만 모아 본다  ← 0이 섞이면 뭉개진다")
ok(abs(d["심는 몫"] - 1 / 12) < 0.01, "심는 몫을 따로 센다")

print("\n[시키기 -- 분포가 아니라 그 대목의 값]")
one = deep.clean({"장면꼴": "여파", "속도": "늘임", "거리": "생각속",
                  "갈등축": "자신과", "갈등세기": 2, "갈등끝": "유예",
                  "닫는법": "여운", "무엇": "돌아가지 않기로 한다", "누구": "그",
                  "심은것": "편지", "거둔거리": 7, "인물수": 2, "새인물": 0})
b = deep.brief(0, path=None) if False else None
import json, tempfile                                                # noqa: E402
with tempfile.TemporaryDirectory() as t:
    p = Path(t) / "deep.json"
    p.write_text(json.dumps({"recs": [one]}, ensure_ascii=False), encoding="utf-8")
    b = deep.brief(0, path=p)
    b9 = deep.brief(9, path=p)
ok("여파" in b and "늘임" in b and "생각속" in b, "그 대목의 값을 그대로 싣는다")
ok("돌아가지 않기로 한다" in b, "달라지는 것 하나를 싣는다")
ok("놓기만 하고" not in b,
   "그 대목이 심었다고 해서 심으라고 시키지 않는다  ← A 의 94%가 심었다고 나왔다")
ok("편지" not in b, "심은 것의 이름은 안 준다  ← 그건 본보기가 된다")
ok("7대목쯤 전" in b, "거둘 것을 시킨다")
ok("네가 정한다" in b, "무엇으로 그렇게 되는지는 안 시킨다  ← 본보기를 박지 않는다")
ok(b9 == b, "원고가 표본보다 길어지면 마지막 것을 쓴다")
ok(len(b) < 900, f"한 덩이가 짧다 ({len(b)}자)")

print("\n[복선 -- 거둔 자리에서 거꾸로 짚는다]")
# "심은것" 칸은 못 쓴다. A 에서 94%가 무언가를 심었다고 나왔다 -- 열에 아홉이
# 심는다면 작품의 결이 아니라 모델이 그 칸을 늘 채우는 것이다. 쓸 수 있는 것은
# 거둔 쪽(6%)이고, 거기서 사거리만큼 거슬러 올라간 자리에만 놓으라고 시킨다.
_rs = [deep.clean({"장면꼴": "장면", "거둔거리": 0}) for _ in range(20)]
for _i, _r in enumerate(_rs):
    _r["n"] = _i
_rs[12]["거둔거리"] = 10
ok(deep.plants(_rs) == {2}, f"거둔 자리에서 거리만큼 거슬러 올라간다 ({deep.plants(_rs)})")
ok(deep.plants([deep.clean({"거둔거리": 0})]) == set(), "안 거두면 심을 자리도 없다")
ok(deep.plants([dict(deep.clean({"거둔거리": 99}), n=3)]) == set(),
   "글 앞으로 넘어가면 버린다")
with tempfile.TemporaryDirectory() as t:
    _p = Path(t) / "deep.json"
    _p.write_text(json.dumps({"recs": _rs}, ensure_ascii=False), encoding="utf-8")
    ok("놓는다" in deep.brief(2, path=_p), "심을 자리에만 놓으라고 시킨다")
    ok("놓는다" not in deep.brief(3, path=_p), "다른 자리에는 아무 말도 안 한다")
    ok("거둔다" in deep.brief(12, path=_p), "거둘 자리에는 거두라고 시킨다")

print("\n[견주기 -- 같은 자로 우리 원고도 잰다]")
mine = dict(one)
ok(deep.gap(mine, one)["겹친 몫"] == 1.0, "똑같으면 1.0")
mine2 = dict(one, 장면꼴="장면", 갈등세기=4)
g = deep.gap(mine2, one)
ok(g["겹친 몫"] < 1.0 and any("장면꼴" in m for m in g["어긋난 것"]),
   f"어긋나면 무엇이 어긋났는지 댄다 ({g['겹친 몫']})")
ok(deep.gap({}, one)["잰 칸"] == 0, "못 잰 칸은 안 센다  ← 빈 것을 통과로 세지 않는다")

# **부를 수 없는 것을 예순일곱 번 불렀다.** drive._extractor 는 "주입한 것은 주입한
# 대로 쓴다" 는 규칙 때문에 None 을 주면 None 을 돌려준다. 그것을 부르면 TypeError 가
# 나는데, 갈래 이름만 찍고 넘어가는 바람에 같은 잘못이 예순일곱 줄로 흘러갔다.
print("\n[배선 -- 부를 수 있는 것을 준다]")
from novel import drive as D                                         # noqa: E402
ok(D._extractor(None) is None,
   "_extractor(None) 은 None 이다  ← 여기에 기대면 안 된다")
ok(callable(D._extractor(D.default_llm)), "_extractor(default_llm) 은 부를 수 있다")

import importlib.util, json as _json, tempfile as _tf               # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "deep_learn", Path(__file__).resolve().parent.parent / "scripts" / "deep_learn.py")
_dl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dl)

_ANSWER = _json.dumps({"장면꼴": "장면", "속도": "장면", "거리": "어깨너머",
                       "시간": "이어짐", "자리": "실내", "원인": "우연",
                       "갈등축": "자신과", "갈등끝": "유예", "앎격차": "같음",
                       "욕망": "유예", "닫는법": "여운", "원인거리": 0,
                       "사슬깊이": 1, "갈등세기": 1, "거둔거리": 0, "새사실": 1,
                       "인물수": 2, "새인물": 0, "무엇": "문이 잠겼다",
                       "누구": "그", "심은것": ""}, ensure_ascii=False)

with _tf.TemporaryDirectory() as t:
    root = Path(t) / "corpus" / "A"
    root.mkdir(parents=True)
    for i in range(4):
        # PF.MIN_UNIT(1,500자)보다 길어야 잰다. 짧으면 조용히 건너뛴다.
        (root / f"{i:02d}.txt").write_text(
            "그는 걸었다. 문이 닫혔다. 바람이 불었다.\n" * 120, encoding="utf-8")
    out = Path(t) / "deep.json"
    _calls = []

    def _fake(prompt):
        _calls.append(prompt)
        return _ANSWER

    def _dead(prompt):
        _calls.append(prompt)
        raise RuntimeError("키가 없다")

    _was = D.extractor_llm
    try:
        D.extractor_llm = _fake
        rc = _dl.main([str(Path(t) / "corpus"), "--only", "A", "--out", str(out)])
        got = _json.loads(out.read_text(encoding="utf-8"))
        ok(rc == 0 and len(got["recs"]) == 4,
           f"부를 수 있는 것을 주면 다 뽑는다 (기록 {len(got['recs'])}개 · 호출 {len(_calls)}회)")
        ok(len(_calls) == 4, "토막당 한 번만 묻는다  ← 칸이 스물둘이어도 호출은 하나다")

        n0 = len(_calls)
        _dl.main([str(Path(t) / "corpus"), "--only", "A", "--out", str(out)])
        ok(len(_calls) == n0, "이미 뽑은 토막은 다시 안 묻는다  ← 이어 돌기")

        out.unlink()
        _calls.clear()
        D.extractor_llm = _dead
        _dl.main([str(Path(t) / "corpus"), "--only", "A", "--out", str(out)])
        ok(len(_calls) == 3,
           f"내리 세 번 실패하면 멈춘다 ({len(_calls)}회)  ← 예순일곱 번 태우지 않는다")
    finally:
        D.extractor_llm = _was

print()
if fails:
    print(f"의미층: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("의미층: 묻기 · 다듬기 · 분포 · 시키기 · 견주기 -- 통과")
