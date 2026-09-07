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

from novel import genre as GENRE, profile as PF, score as SC, targets as TG

HERE = Path(__file__).resolve().parent
PATH = Path(os.environ.get("DRIFT_DIRECTIVES", HERE / "directives.json"))

# 한 덩어리에 실을 지시 수. 늘리면 도로 묻힌다.
MAX_ASKS = int(os.environ.get("DRIFT_MAX_ASKS", "4"))
# 이만큼 벗어나야 말한다. 폭 안이면 아무 말도 안 한다.
SLACK = float(os.environ.get("DRIFT_ASK_SLACK", "0.25"))

# **설정 자체를 덩어리마다 흔든다.** 지시문을 한 번 고치고 런을 통째로 다시 돌리면
# 한 사이클에 관측이 하나뿐이다 -- 그건 최적화가 아니라 생성이다. 대신 덩어리마다 다른
# 설정(팔)을 배정하고, 그 덩어리가 어떻게 나왔는지를 팔과 함께 적는다. 서른 덩어리를
# 쓰면 서른 개의 관측이 공짜로 생긴다. 호출은 하나도 안 는다.
#
# 흔드는 것: 몇 개나 싣는가 · 얼마나 벗어나야 말하는가 · 폭의 어디를 겨누는가.
ARMS = [
    {"asks": 2, "slack": 0.25, "aim": "mid"},
    {"asks": 4, "slack": 0.25, "aim": "mid"},
    {"asks": 6, "slack": 0.15, "aim": "mid"},
    {"asks": 4, "slack": 0.50, "aim": "near"},
    {"asks": 1, "slack": 0.25, "aim": "mid"},
    {"asks": 4, "slack": 0.10, "aim": "near"},
]


def arm(seed: str, n: int) -> dict:
    """이번 덩어리에 배정된 설정. 원고와 번호로 정해지니 이어 써도 재현된다.

    **돌아가며 뽑는다. 해시로 뽑으면 몰린다** -- 여덟 덩어리에서 팔 둘은 한 번도
    안 나오고 다른 팔이 두 번씩 나왔다(실측). 그것만으로도 나쁘지만 더 나쁜 것이
    있다: 튜너가 지시문을 고쳐 가므로 **나중에 뽑힌 팔은 더 나은 지시문 덕을 본다.**
    그 이득이 팔에 고르게 퍼지지 않으면 팔의 성적이 아니라 순서를 재게 된다.

    시작 자리는 원고마다 다르게 둔다(해시) -- 늘 0번부터 시작하면 그것도 결이 된다."""
    import hashlib
    off = int(hashlib.sha1(f"{seed}|arm0".encode("utf-8")).hexdigest()[:8], 16)
    a = dict(ARMS[(off + n) % len(ARMS)])
    a["id"] = ARMS.index(next(x for x in ARMS if x["asks"] == a["asks"]
                              and x["slack"] == a["slack"] and x["aim"] == a["aim"]))
    return a


_CACHE: dict | None = None


def load() -> dict:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(PATH.read_text(encoding="utf-8")).get("axes", {})
        except Exception:
            _CACHE = {}
    return _CACHE


def off(text: str, slack: float | None = None, gname: str = "") -> list:
    """(축, 어느 쪽으로, 거리, 우리 값). 먼 것부터.

    **갈래가 옮긴 축은 갈래로 잰다.** 이것을 안 하면 손질 루프가 표본 폭으로 재고,
    갈래가 옮겨 놓은 자리는 영영 안 고쳐진다 -- 실측 2026-09-07: 로판 대사 몫을
    30~55%로 시켜 놓고 여기서는 표본 폭 1~29%로 쟀다. 나온 원고가 10%였는데 그 폭
    안이라 **아무도 대사를 늘리라고 하지 않았다.** 시키는 자와 재는 자가 다른 폭을
    보면 그 차이만큼이 통째로 사각이 된다(compose.aims · score.py 와 같은 이유)."""
    m = PF.measure(text)
    if not m:
        return []
    out = []
    for k in PF.AXES:
        band = GENRE.band(gname, k) or TG.band(k)
        if not band or k not in m:
            continue
        lo, hi = band
        d = SC._gap(m[k], lo, hi)
        if d > (SLACK if slack is None else slack):
            out.append((k, "low" if m[k] < lo else "high", d, m[k]))
    return sorted(out, key=lambda x: -x[2])


def asks(text: str, limit: int = MAX_ASKS, climb_words: str = "",
         slack: float | None = None, gname: str = "") -> list:
    """이번 덩어리에 실을 지시문들. 어긋난 축이 없으면 빈 목록이다."""
    from novel import rhythm
    rows = off(text, slack, gname)
    # **갈래가 옮긴 축은 한 자리를 보장한다.** 어긋난 축은 거리 순으로 실리는데 한도가
    # 넷이라, 갈래 축이 다섯 번째면 영영 안 실린다 -- 실측 2026-09-07: 로판 대사가
    # 10%인데 sent_var·end_var·short·da_share 넷에 밀려 잘렸고, 팔이 {2,4,6,4,1,4}로
    # 돌아가니 여섯 덩어리에 한 번만 실렸다.
    #
    # 갈래를 준다는 것은 사람이 **이 갈래로 써라**고 명시한 것이다. 그 요구가 표본과의
    # 일반적인 거리에 밀려서는 안 된다. 다만 다 앞세우지도 않는다 -- 제일 먼 갈래 축
    # 하나만 앞으로 당긴다.
    if gname and limit:
        gx = [i for i, r in enumerate(rows) if GENRE.band(gname, r[0])]
        if gx and gx[0] >= limit:
            rows = [rows[gx[0]]] + [r for i, r in enumerate(rows) if i != gx[0]]
    out = []
    for kind, side, gap, got in rows:
        say = (load().get(kind) or {}).get(side, "")
        if not say:
            continue
        # **갈래가 옮긴 축은 가운뎃값도 갈래에서 온다.** 표본에 없는 축(로판의 높임
        # 대사 몫)을 TG.mid 로 물으면 0 이 돌아오고, 지시문이 "표본은 0%가 높임으로
        # 간다" 가 된다 -- 로판에 정반대를 시키는 말이다(실측 2026-09-07).
        band = GENRE.band(gname, kind) or TG.band(kind) or (0.0, 0.0)
        mid = ((band[0] + band[1]) / 2 if GENRE.band(gname, kind)
               else TG.mid(kind, 0.0))
        out.append(say.format(got=got, lo=band[0], hi=band[1], mid=mid,
                              n_climb=rhythm.LIMITS["climb"],
                              climb_words=climb_words))
        if len(out) >= limit:
            break
    return out


def brief(text: str, limit: int = MAX_ASKS, climb_words: str = "",
          slack: float | None = None, gname: str = "") -> str:
    """프롬프트에 붙일 한 덩이. 다 맞고 있으면 **빈 줄**이다."""
    items = asks(text, limit, climb_words, slack, gname)
    if not items:
        return ""
    body = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(items))
    return ("[직전 덩어리에서 어긋난 것] **여기만 고쳐라.** 나머지는 지금대로 좋다.\n"
            + body)
