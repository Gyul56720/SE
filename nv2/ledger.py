"""**원장 -- 사실은 여기 남는다. 프롬프트 줄은 잊힌다.**

앞 판에서 확인한 것: 프롬프트에 적은 규칙은 다음 호출에서 사라지지만, 원장에 적힌
사실은 남아 계속 실린다. 그래서 **지켜져야 하는 사실**은 전부 여기로 온다 --
이름 · 설정 · 낫지 않는 상처 · 심어 둔 것.
"""
from __future__ import annotations

BUCKETS = ("사람", "자리", "물건", "사실", "상처", "설정집", "심음")


def blank() -> dict:
    return {k: [] for k in BUCKETS}


def add(led: dict, bucket: str, item: dict) -> None:
    """같은 이름은 다시 안 세운다 -- 다시 세우면 값이 둘이고 그것이 모순이다."""
    if bucket not in led:
        led[bucket] = []
    name = str(item.get("이름") or "").strip()
    if name and any(str(x.get("이름")) == name for x in led[bucket]):
        return
    led[bucket].append(item)


def hero(led: dict) -> str:
    """주인공의 이름. 없으면 빈 것 -- 수리가 이것을 알아야 '화자' 를 바꿀 수 있다."""
    for p in led.get("사람") or []:
        if p.get("주인공"):
            return str(p.get("이름") or "")
    ps = led.get("사람") or []
    return str(ps[0].get("이름") or "") if ps else ""


def brief(led: dict, limit: int = 8) -> str:
    """[세계] 블록. **어긋나면 안 되는 것만** 적는다 -- 자랑하려고 적는 게 아니다."""
    out = []
    for p in (led.get("사람") or [])[:limit]:
        bits = " · ".join(f"{k} {v}" for k, v in p.items()
                          if k not in ("이름", "주인공") and v)
        out.append(f"  · {p.get('이름')}{' (주인공)' if p.get('주인공') else ''}"
                   + (f" -- {bits}" if bits else ""))
    for c in (led.get("설정집") or [])[:limit]:
        out.append(f"  · [설정] {c.get('이름')} -- {c.get('규칙', '')}"
                   " (이 이름 그대로 쓴다 · 다시 설명하지 마라)")
    for w in (led.get("상처") or [])[:limit]:
        out.append(f"  · [상처] {w.get('누구')}: {w.get('무엇')}"
                   " -- **낫지 않는다.** 이 회차에도 그대로다")
    for s in (led.get("심음") or [])[:limit]:
        if not s.get("거둠"):
            out.append(f"  · [심어 둠] {s.get('무엇')} -- 아직 안 거뒀다")
    for b in ("자리", "물건", "사실"):
        for x in (led.get(b) or [])[:4]:
            out.append(f"  · [{b}] {x.get('이름')}"
                       + (f" -- {x.get('무엇') or x.get('규칙') or ''}"
                          if (x.get("무엇") or x.get("규칙")) else ""))
    return "\n".join(out)


def wound(led: dict, who: str, what: str) -> None:
    add(led, "상처", {"이름": f"{who}:{what}", "누구": who, "무엇": what})


def size(led: dict) -> int:
    return sum(len(v) for v in led.values() if isinstance(v, list))
