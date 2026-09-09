"""**스키마에서 결론을 끌어낸다.** 데이터도 LLM 도 안 쓴다.

`law/issue.py` 를 도메인 밖으로 뺀 것이다. 거기서 법에 묶여 있던 것은 **단계 이름**
하나뿐이었고, 나머지(무너뜨림 사슬 · 두 정거장 · 뒤집기 검사)는 이미 도메인을 몰랐다.

## 두 정거장 -- 이것이 추론의 심장이다

    세우는 쪽 진술만으로     결론이 무엇인가
    다투는 쪽 진술까지 넣으면 결론이 무엇인가

둘이 **갈리면 그 사이에 다툴 거리가 있다.** 안 갈리면 둘 중 하나다 -- 세우는 쪽이
애초에 못 세웠거나, 상대 주장이 결론을 못 바꾸거나. 어느 쪽이든 말해 줄 것이 있다.

독일 Relationstechnik 의 Klägerstation/Beklagtenstation 이 원형이다(law/METHOD.md 1-4).
법에서 온 것이지만 **법에만 쓰이는 모양이 아니다** -- 주장하는 쪽과 다투는 쪽이 있고
요건이 걸려 있으면 어디서든 같다.

## 뒤집기 -- 무엇이 결론을 지고 있나

다투어진다고 다 중요한 것이 아니다. **그 요건의 답이 갈릴 때 결론이 갈리는 경우가
하나라도 있어야** 결론에 닿아 있는 것이다. 없으면 곁가지다.

다른 다툼들의 결말은 아직 모르므로 전부 훑는다. 조합이 너무 많으면 자르되, 자른 경우
**남기는 쪽으로** 답한다 -- 못 찾은 것이지 없는 것이 아니고, **과잉 기각하는 심판은
맞는 답도 버린다**(`novel/gate.py` 가 배운 것).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from reason import schema as SC

CAP = 14          # 이보다 많은 다툼은 조합을 다 못 훑는다


@dataclass
class 쟁점:
    요건: str
    물음: str
    입장: dict
    출처: str = ""
    역할: str = ""

    def __str__(self) -> str:
        # **요건 id 를 앞에 단다.** 없으면 스키마의 어느 줄에서 온 쟁점인지 되짚을 수가
        # 없다 -- 수에 근거를 달아 두는 것(B002)과 같은 자리다. 말만 있으면 비슷한
        # 문장 둘을 사람이 못 가른다(검사가 이 자리를 잡았다).
        p = " vs ".join(f"{k}:{'O' if v else 'X'}" for k, v in self.입장.items())
        꼬리 = f" · 출처 {self.출처}" if self.출처 else " · **출처 없음**"
        return f"[{self.요건}] {self.물음} ({p}{꼬리})"


def 살아있나(s: SC.스키마, 배정: dict) -> dict:
    """요건이 **서 있는가.** 인정되어도 그것을 무너뜨리는 것이 서 있으면 없다.

    받아치기가 한 번으로 끝나지 않는다: 주장 <- 반박 <- 재반박 <- 재재반박.
    이 함수가 그 사슬을 따라간다. 되돌이는 스키마가 틀린 것이고(S003 이 막는다)
    여기서는 끝없이 돌지 않게 본 것을 기억한다.
    """
    대상: dict = {}
    for e in s.요건:
        if e.무너뜨림:
            대상.setdefault(e.무너뜨림, []).append(e)
    memo: dict = {}

    def alive(eid, seen=()):
        if eid in memo:
            return memo[eid]
        if eid in seen:
            return False
        if not 배정.get(eid, False):
            memo[eid] = False
            return False
        for d in 대상.get(eid, []):
            if alive(d.id, seen + (eid,)):
                memo[eid] = False
                return False
        memo[eid] = True
        return True

    return {e.id: alive(e.id) for e in s.요건}


def 결론(s: SC.스키마, 배정: dict) -> str:
    """배정 하나에서 결론. `섬` 또는 `안섬`.

    **둘뿐이다.** '못 세워서 안 섬' 과 '무너져서 안 섬' 을 갈라 두면 뒤집기 검사가
    그 갈림까지 '결론이 바뀌었다' 로 세어, 어느 쪽이든 주장이 지는 자리를 쟁점으로
    올린다. 왜 안 섰는지는 `왜()` 가 따로 말한다.
    """
    산것 = 살아있나(s, 배정)
    세울것 = [e for e in s.요건 if e.역할 == SC.세움 and not e.무너뜨림]
    깨는것 = [e for e in s.요건 if e.역할 == SC.무너뜨림 and not e.무너뜨림]
    if not all(산것[e.id] for e in 세울것):
        return "안섬"
    for e in 깨는것:
        if 산것[e.id] and (not e.원용필요 or e.원용됨):
            return "안섬"
    return "섬"


def 왜(s: SC.스키마, 배정: dict) -> str:
    """결론이 그렇게 난 까닭을 한 줄로. **판정이 아니라 설명이다.**"""
    산것 = 살아있나(s, 배정)
    못선것 = [e for e in s.요건
              if e.역할 == SC.세움 and not e.무너뜨림 and not 산것[e.id]]
    if 못선것:
        return f"세울 것이 안 섰다: {', '.join(e.id for e in 못선것)}"
    깬것 = [e for e in s.요건
            if e.역할 == SC.무너뜨림 and not e.무너뜨림 and 산것[e.id]
            and (not e.원용필요 or e.원용됨)]
    if 깬것:
        return f"무너뜨리는 것이 섰다: {', '.join(e.id for e in 깬것)}"
    return "세울 것이 다 서고 무너뜨리는 것이 없다"


def _배정(s: SC.스키마, 우선: list) -> dict:
    """이 쪽들의 말대로 배정한다. 앞쪽이 이긴다 -- 안 적힌 것은 False."""
    out = {}
    for e in s.요건:
        pos = s.입장.get(e.id, {})
        v = False
        for 쪽 in 우선:
            if 쪽 in pos:
                v = bool(pos[쪽])
                break
        out[e.id] = v
    return out


def 정거장(s: SC.스키마) -> dict:
    """두 정거장을 돌린다. **갈리면 그 사이에 다툴 거리가 있다.**"""
    세, 다 = s.쪽들()
    a = _배정(s, [세])
    b = _배정(s, [다, 세])
    return {"세우는쪽": 세, "다투는쪽": 다,
            "세운쪽결론": 결론(s, a), "세운쪽왜": 왜(s, a),
            "다툰뒤결론": 결론(s, b), "다툰뒤왜": 왜(s, b),
            "갈림": 결론(s, a) != 결론(s, b)}


def 다툼(s: SC.스키마) -> list:
    """양측이 **반대로** 말한 요건. 한쪽만 말한 것은 다툼이 아니다."""
    out = []
    for e in s.요건:
        pos = s.입장.get(e.id, {})
        if len(pos) >= 2 and len({bool(v) for v in pos.values()}) > 1:
            out.append(e)
    return out


def 뒤집는가(s: SC.스키마, 대상, 다른것: list, cap: int = CAP) -> bool:
    """이 요건의 답이 갈릴 때 결론이 갈리는 경우가 **하나라도** 있는가.

    조합이 cap 을 넘으면 True 로 답한다 -- 못 찾은 것이지 없는 것이 아니다.
    """
    바탕 = _배정(s, list(s.쪽들()))
    다른것 = [e for e in 다른것 if e.id != 대상.id]
    if len(다른것) > cap:
        return True
    for combo in itertools.product([False, True], repeat=len(다른것)):
        a = dict(바탕)
        for e, v in zip(다른것, combo):
            a[e.id] = v
        a[대상.id] = False
        아니 = 결론(s, a)
        a[대상.id] = True
        예 = 결론(s, a)
        if 아니 != 예:
            return True
    return False


def 도출(s: SC.스키마) -> list:
    """쟁점. **뽑는 것이 아니라 계산하는 것이다.**

    둘을 다 넘겨야 쟁점이다: (1) 다투어진다 (2) 결론에 닿아 있다.
    """
    cs = 다툼(s)
    out = []
    for e in cs:
        if not 뒤집는가(s, e, cs):
            continue
        out.append(쟁점(요건=e.id, 물음=f"{e.말 or e.id}이(가) 인정되는가",
                       입장={k: bool(v) for k, v in s.입장.get(e.id, {}).items()},
                       출처=e.출처, 역할=e.역할))
    return out


def 곁가지(s: SC.스키마) -> list:
    """다투어지고는 있으나 결론을 못 바꾸는 요건. **보고는 한다.**"""
    cs = 다툼(s)
    return [e for e in cs if not 뒤집는가(s, e, cs)]
