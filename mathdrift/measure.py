"""**확산을 잰다** -- 새것과 물려받은 것. `novel/diffusion.py` 의 두 계수를 공간 층으로.

원문의 규율 그대로다:

> 확산은 이 둘이 **함께** 있을 때만 일어난다. 새것만 있으면 산만해지고(연결 없는 나열),
> 되돌아온 것만 있으면 제자리를 돈다.

공간 층에서 그 둘은 이렇게 된다:

  · **새것**     부모에 없던 구조. 0 이면 이름만 바꾼 것이다
  · **물려받음**  부모에서 그대로 온 것. 0 이면 인과성이 없다 -- 남의 공간이다

"완전히 다르면 안 된다" 가 재는 것이 정확히 뒤엣것이다.

## 재는 방식과 그 한계를 먼저 적는다

칸에 적힌 낱말을 토큰으로 갈라 집합으로 견준다. **이것은 대리값이다.** 같은 구조를 다른
낱말로 쓰면 물려받은 것을 못 보고, 다른 구조를 같은 낱말로 쓰면 물려받았다고 잘못 센다.
`mathgen/README.md` 가 압축비에 대해 적어 둔 것과 같은 종류의 정직한 한계다.

제대로 재려면 두 공간 사이의 사상을 실제로 만들어 봐야 하는데, 그건 검증 단계의 일이고
비싸다. 여기서는 **싸게 재서 숫자를 돌려주되 아무것도 죽이지 않는다** -- 그것이
`diffusion.py` 의 첫 번째 제약이었다.
"""
from __future__ import annotations

import re

from mathdrift import space as SP

_TOK = re.compile(r"[0-9A-Za-z가-힣]+")

# 어느 공간에나 나오는 말. 세면 전부 "물려받았다" 로 보여서 계수가 죽는다.
STOP = {"이", "그", "것", "수", "의", "를", "은", "는", "에", "로", "와", "과", "한",
        "하는", "있는", "되는", "공간", "점", "문제", "구조", "하나", "모든", "위", "안"}


def _toks(rec: dict) -> set[str]:
    """내용 칸만 본다. **`왜` 칸은 빼고 센다** -- 거기는 사람에게 하는 설명이라
    부모 얘기를 그대로 옮겨 적기 마련이고, 그러면 물려받음이 부풀려진다."""
    buf = []
    for f in SP.FIELDS:
        if f == "왜":
            continue
        v = rec.get(f)
        buf.append(v if isinstance(v, str) else str(v or ""))
    return {t for t in _TOK.findall(" ".join(buf)) if len(t) > 1 and t not in STOP}


# **한 낱말이 겹친 것은 물려받은 것이 아니다.** 실측: 아무 상관 없는 공간("날씨/기압")도
# "연속" 하나가 겹쳐서 확산으로 셌다. 그래서 바닥을 둘 둔다 -- 겹친 낱말의 절대 수와,
# 자식 어휘 중에서 그것이 차지하는 몫. 둘 다 넘어야 물려받았다고 본다.
KEEP_MIN = 2
KEEP_SHARE = 0.15


def measure(child: dict, parent: dict | None) -> dict:
    """두 계수와, 둘이 함께 있는지."""
    c = _toks(child)
    if parent is None:                      # 씨앗은 부모가 없다 -- 잴 것이 없다
        return {"새것": len(c), "물려받음": 0, "몫": 0.0, "확산": False, "씨앗": True}
    p = _toks(parent)
    new, kept = len(c - p), len(c & p)
    share = kept / len(c) if c else 0.0
    real = kept >= KEEP_MIN and share >= KEEP_SHARE
    return {"새것": new, "물려받음": kept, "몫": round(share, 3),
            "확산": bool(new and real), "씨앗": False}


def note(m: dict) -> str:
    """숫자를 사람 말로. **판정이 아니라 관찰이다** -- 어느 쪽도 기각 사유가 아니다."""
    if m.get("씨앗"):
        return "씨앗"
    if not m["확산"] and not m["새것"]:
        return "제자리 -- 이름만 바뀐 것일 수 있다"
    if not m["확산"]:
        return (f"인과 약함 -- 부모와 겹치는 것이 {m['물려받음']}개"
                f" (몫 {m['몫']}). 남의 공간일 수 있다")
    return f"확산 (새것 {m['새것']} / 물려받음 {m['물려받음']}, 몫 {m['몫']})"


def spread(led: dict) -> dict:
    """원장 전체에서 확산이 얼마나 일어났나. 이어 돌릴 때 얕아지는지를 본다."""
    n = ok = 0
    for s in led["spaces"]:
        m = s.get("잰것") or {}
        if m.get("씨앗"):
            continue
        n += 1
        ok += 1 if m.get("확산") else 0
    return {"잰공간": n, "확산": ok, "몫": (ok / n) if n else 0.0}
