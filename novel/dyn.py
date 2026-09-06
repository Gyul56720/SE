"""**어긋난 축만 싣는다.**

지금까지 프롬프트는 상수였다 -- 12,433자 중 9,000자쯤이 매 호출 똑같이 실렸다.
그래서 두 가지가 동시에 나빴다: 토큰을 매번 다 태우고, **묻혀서 안 지켜졌다.**
스무 항목을 늘 다 시키면 어느 것도 강조가 아니다.

여기서는 반대로 한다. 직전 덩어리를 재서 **표본 폭을 벗어난 축만** 문장으로 만든다.
맞고 있는 축은 한 글자도 안 싣는다. 프롬프트가 짧아지면서 동시에 세진다.

  · 지시문은 코드가 아니라 **데이터**다(directives.json) -- 나중에 tuner 가 여기를 고친다
  · 수는 targets.json 에서 온다 -- 지시문에 수를 박지 않는다
  · 첫 덩어리에는 잴 것이 없다. 그때는 아무 축도 안 싣는다

**한 번에 몇 개까지만.** 어긋난 축이 열이라도 다 싣지 않는다 -- 한꺼번에 시키면
안 지켜진다는 것을 이 저장소에서 반복해서 겪었다. 먼 것부터 몇 개만.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from novel import profile as PF, score as SC, targets as TG

HERE = Path(__file__).resolve().parent
PATH = Path(os.environ.get("DRIFT_DIRECTIVES", HERE / "directives.json"))

# 한 덩어리에 실을 지시 수. 늘리면 도로 묻힌다.
MAX_ASKS = int(os.environ.get("DRIFT_MAX_ASKS", "4"))
# 이만큼 벗어나야 말한다. 폭 안이면 아무 말도 안 한다.
SLACK = float(os.environ.get("DRIFT_ASK_SLACK", "0.25"))

_CACHE: dict | None = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(PATH.read_text(encoding="utf-8")).get("axes", {})
        except Exception:
            _CACHE = {}
    return _CACHE


def off(text: str) -> list:
    """(축, 어느 쪽으로, 거리, 우리 값). 먼 것부터."""
    m = PF.measure(text)
    if not m:
        return []
    out = []
    for k in PF.AXES:
        band = TG.band(k)
        if not band or k not in m:
            continue
        lo, hi = band
        d = SC._gap(m[k], lo, hi)
        if d > SLACK:
            out.append((k, "low" if m[k] < lo else "high", d, m[k]))
    return sorted(out, key=lambda x: -x[2])


def asks(text: str, limit: int = MAX_ASKS, climb_words: str = "") -> list:
    """이번 덩어리에 실을 지시문들. 어긋난 축이 없으면 빈 목록이다."""
    from novel import rhythm
    out = []
    for kind, side, gap, got in off(text):
        say = (load().get(kind) or {}).get(side, "")
        if not say:
            continue
        band = TG.band(kind) or (0.0, 0.0)
        out.append(say.format(got=got, lo=band[0], hi=band[1],
                              mid=TG.mid(kind, 0.0),
                              n_climb=rhythm.LIMITS["climb"],
                              climb_words=climb_words))
        if len(out) >= limit:
            break
    return out


def brief(text: str, limit: int = MAX_ASKS, climb_words: str = "") -> str:
    """프롬프트에 붙일 한 덩이. 다 맞고 있으면 **빈 줄**이다."""
    items = asks(text, limit, climb_words)
    if not items:
        return ""
    body = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(items))
    return ("[직전 덩어리에서 어긋난 것] **여기만 고쳐라.** 나머지는 지금대로 좋다.\n"
            + body)
