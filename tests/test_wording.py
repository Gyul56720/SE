"""말맛 장부 -- 쓴 것은 세어 두고 안 쓴 쪽으로 민다.

하한을 더 두지 않는다. 하한을 두면 하한을 정확히 맞춘다는 것을 두 번 겪었다
(짧은 '-다' 62%, 긴 대사 여덟 할). 이건 금지가 아니라 **복원력**이다 -- 한쪽으로
기울면 반대쪽으로 미는 힘이고, 기울지 않았으면 아무 일도 하지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow, rhythm, wording as W                          # noqa: E402

_bad = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        _bad.append(label)


print("[말맛] **기울면 되민다** -- 하한을 하나 더 두는 것이 아니다")
ok(W.brief([], "씨", 0).count("말끝") == 0,
   "원고가 없으면 말끝을 안 민다  ← 밀 방향이 없다")

_da = ["배가 들어왔다. " * 40]
ok("-다" in W.hogs(_da), f"'-다' 만 쓰면 그것을 짚는다 ({W.hogs(_da)})")
ok("-다" not in W.thin(_da), "많이 쓴 것을 '써 보라' 고 밀지는 않는다")
ok(len(W.thin(_da)) == W.PUSH_END,
   f"적게 쓴 것 {W.PUSH_END}개를 민다  ← 한꺼번에 다 시키면 안 지켜진다")

_mixed = ["배가 들어왔다. 온다. 오겠다. 올까. 오는군. 올 것이다. 오지. 옴. 와라. " * 3]
ok(not W.hogs(_mixed), f"고르게 썼으면 아무 말도 안 한다 ({W.hogs(_mixed)})")

print()
print("[비유·꼴] **세지 않고 뽑는다** -- 은유를 정규식으로 어떻게 찾겠는가")
_f = [tuple(W.figures("씨", n)) for n in range(20)]
ok(all(len(x) == W.PUSH_FIG for x in _f), "매번 정해진 개수를 뽑는다")
ok(all(len(set(x)) == len(x) for x in _f), "한 덩어리 안에서 겹치지 않는다")
ok(len(set(_f)) > 8, f"덩어리마다 다르다 ({len(set(_f))}가지)")
ok(W.figures("씨", 3) == W.figures("씨", 3), "같은 씨앗·번호면 같다  ← 이어 쓰기에 재현된다")
ok("번역체" in W.FORMS, "영어로 쓴 다음 옮긴 듯한 꼴도 재료다")
ok(len(set(tuple(W.forms("씨", n)) for n in range(20))) > 5, "꼴도 덩어리마다 다르다")

print()
print("[리얼리즘] **자세하되 있을 법하게** -- 다채로움이 허구가 되면 안 된다")
_b = W.brief(["배가 들어왔다. " * 40], "씨", 2)
ok("현실의 테두리 안" in _b, "현실 밖으로 나가지 말라고 한다")
ok("재서 말하면 진짜가 된다" in _b, "자세함이 그럴듯함을 만든다고 말한다")
ok("사람이 저질러서" in _b, "마법으로 풀지 못하게 한다")

print()
print("[문장] **몰리면 되민다** -- 몫이 맞아도 몰려 있으면 읽을 땐 두 덩어리다")
_short = "\n".join(["짧다."] * 9)
_long = "\n".join(["이것은 쉼표로 이어 붙여서 마흔다섯 자를 넘기게 만든 긴 문장인데, 정말로 그렇다."] * 7)
ok([c for c in rhythm.check(_short) if "짧은 문장이 내리" in c],
   "짧은 것이 몰리면 긴 문장으로 끊으라고 한다")
ok([c for c in rhythm.check(_long) if "긴 문장이 내리" in c],
   "긴 것이 몰리면 짧은 문장으로 끊으라고 한다")

print()
print("[흔들기] **목표치는 한 벌을 나눠 쓴다** -- 두 벌로 두면 한쪽만 고치게 된다")
_v = [rhythm.wave("씨", n, 0.1, 0.4) for n in range(80)]
ok(0.1 <= min(_v) and max(_v) <= 0.4, f"구간 안이다 ({min(_v):.2f}~{max(_v):.2f})")
_mid = 0.25
_run = _best = 1
_prev = None
for _x in _v:
    _hi = _x > _mid
    _run = _run + 1 if _hi == _prev else 1
    _prev = _hi
    _best = max(_best, _run)
ok(_best <= 3, f"한쪽으로 안 쏠린다 (최대 {_best}번 연속)")
ok(abs(sum(_v) / len(_v) - _mid) < 0.05, f"평균은 가운데다 ({sum(_v) / len(_v):.2f})")

src = Path(flow.__file__).read_text(encoding="utf-8")
ok("_wording(book)" in src, "프롬프트에 실린다")
ok("리듬은 몫이 아니라 배치다" in src, "몰지 말라고 프롬프트에도 적혀 있다")

print()
print("[군집] **인물이 느는 것이 사건이 느는 것이다**")
from novel import shock as SH                                         # noqa: E402
_sc = SH.brief(SH.draw("씨", 1))
ok("이 일로 사람들이 갈라진다" in _sc, "사건 뒤에 사람들이 갈라진다고 말한다")
ok("새 사람이 하나씩 딸려 온다" in _sc, "갈라진 자리마다 사람이 는다")
ok("군집처럼" in _sc, "붙고 갈라지고 사라지고 죽는다")
ok("죽은 사람은 되살아나지 않는다" in _sc, "죽음만은 되돌릴 수 없다  ← 원장의 무모순성과 같은 말")
ok("한 덩어리에 전부 하지는 마라" in _sc, "한 번에 다 시키지는 않는다")
_ways = {SH.scatter("씨", i) for i in range(12)}
ok(len(_ways) > 6, f"흩어지는 방향이 덩어리마다 다르다 ({len(_ways)}가지)")
ok(all(len(set(w)) == len(w) for w in _ways), "한 사건 안에서 겹치지 않는다")

print()
if _bad:
    print(f"말맛: {len(_bad)}개 실패 -- {_bad}")
    raise SystemExit(1)
print("말맛: 되밀기 · 비유 · 꼴 · 리얼리즘 · 몰림 -- 통과")
