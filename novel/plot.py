"""**줄거리를 미리 쓰지 않는다. 다음 한 걸음만 정한다.**

문제. 문면만 맞추면 문장은 좋아져도 이야기가 안 걸린다. 그렇다고 개요를 세우면
그 순간 표류가 아니게 되고, 한 번 정한 개요가 틀렸을 때 되돌릴 길이 없다.

가운데를 간다. **개요는 없고, 다음 한 걸음의 꼴만 정한다.**

  · 무엇을 쓸지(내용)는 안 정한다 -- 원고의 원장에서 나온다
  · 언제 무엇을 할지(리듬)만 표본에서 배운다 -- 이름을 몇 개나 굴릴지, 언제 자리를
    옮길지, 시한을 걸지, 물을지. 전부 재는 축이다(names · scene · clock · askrate)
  · **한 걸음은 상태 변화 하나다**(TAXONOMY 의 서사층 최소 단위). 열 가지를 시키지
    않는다 -- 하나만 시키고, 그것이 이번 덩어리에서 실제로 일어났는지 다음에 잰다

**수정은 한 번뿐이다.** 걸음을 뽑고, 원장과 어긋나는지 한 번 보고(호출 없이 -- 이미
확정된 사실과 부딪히는지만), 어긋나면 다른 걸음으로 바꾼다. 두 번은 안 본다.
"""
from __future__ import annotations

import hashlib
import os

from novel import targets as TG

# 상태 변화의 갈래. TAXONOMY 서사층에서 그대로 가져왔다. **내용이 아니라 갈래다** --
# 무엇이 달라지는지만 정하고, 무엇으로 그렇게 되는지는 원고가 정한다.
CHANGE = {
    "위치": "누가 어디에서 어디로 옮겨 간다",
    "소유": "무엇이 손을 옮긴다 -- 주거나, 뺏기거나, 잃거나",
    "앎":   "누가 몰랐던 것을 알게 된다. 아는 사람과 모르는 사람이 갈린다",
    "관계": "둘 사이가 달라진다. 가까워지거나 틀어지거나 이름이 바뀐다",
    "능력": "할 수 있던 것을 못 하게 되거나, 못 하던 것을 하게 된다",
    "지위": "부르는 이름이나 자리가 달라진다",
    "몸":   "다치거나 아프거나 못 자거나 배가 고프다",
    "마음": "마음먹은 것이 바뀐다. 그 변화는 겪은 일 때문이어야 한다",
    "약속": "약속이 생기거나 깨진다",
    "여유": "시간이나 돈이 줄어든다. 얼마나 남았는지 알게 된다",
}
# 걸음이 어디서 오는가. 이것도 갈래일 뿐 내용이 아니다.
FROM = {
    "앞엣것에서": "앞에서 놓인 것 하나가 원인이 되어",
    "밖에서":     "상관없던 데서 들이닥쳐",
    "사람이":     "누가 마음먹고 해서",
    "절차가":     "규정이나 순서가 그렇게 되어 있어서",
    "몰라서":     "누가 잘못 알고 있어서",
    "미뤄서":     "미뤄 둔 것이 이제 와서",
}
PATH = os.environ.get("DRIFT_PLOT", "1") not in ("0", "false", "")


def _pick(pool, seed: str, n: int, salt: str):
    keys = list(pool)
    h = hashlib.sha1(f"{seed}|{salt}|{n}".encode("utf-8")).hexdigest()
    return keys[int(h[:8], 16) % len(keys)]


def step(seed: str, n: int, ledger: dict | None = None) -> dict:
    """다음 한 걸음. **수정은 한 번뿐이다** -- 원장과 부딪히면 한 번만 바꾼다."""
    kind = _pick(CHANGE, seed, n, "change")
    how = _pick(FROM, seed, n, "from")
    # 한 번의 검토: 원장이 비어 있는데 "앞엣것에서" 를 시키면 시킬 앞엣것이 없다.
    if how == "앞엣것에서" and not _has(ledger):
        how = _pick(FROM, seed, n, "from2")
    return {"kind": kind, "how": how}


def _has(ledger: dict | None) -> bool:
    if not ledger:
        return False
    return any(ledger.get(k) for k in ("people", "places", "objects", "open"))


def brief(seed: str, n: int, ledger: dict | None = None) -> str:
    """프롬프트에 붙일 한 덩이. 걸음 하나와, 표본에서 온 이야기의 결."""
    if not PATH:
        return ""
    s = step(seed, n, ledger)
    lines = [f"[이 대목에서 일어날 일] **하나만.** 다 벌이지 마라.",
             f"  · 무엇이 달라지나: **{s['kind']}** -- {CHANGE[s['kind']]}",
             f"  · 어디서 오나: **{s['how']}** -- {FROM[s['how']]}",
             "  · 무엇으로 그렇게 되는지는 **네가 정한다.** 앞에 놓인 것을 쓰든 새로"
             " 지어내든 좋다. 다만 이 대목이 끝났을 때 **위 하나는 실제로 달라져 있어야**"
             " 한다. 말로 정리하지 말고 겪게 해라."]
    tips = _rhythm_tips(seed, n)
    if tips:
        lines.append("  · " + " · ".join(tips))
    return "\n".join(lines)


def _rhythm_tips(seed: str, n: int) -> list:
    """표본에서 배운 **이야기의 결.** 내용이 아니라 잦기다."""
    out = []
    for axis, say in (("scene", "자리나 때를 한 번 옮겨라"),
                      ("clock", "시한이 걸린 것을 하나 두어라"),
                      ("askrate", "누가 소리 내어 물어라")):
        band = TG.band(axis)
        if not band:
            continue
        lo, hi = band
        h = int(hashlib.sha1(f"{seed}|tip|{axis}|{n}".encode()).hexdigest()[:8], 16)
        # 표본에서 그 결이 나타나는 만큼만 시킨다 -- 늘 시키면 그것도 버릇이다.
        if hi > 0 and (h % 100) / 100.0 < min(0.9, (lo + hi) / 2 * 3):
            out.append(say)
    return out
