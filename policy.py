#!/usr/bin/env python3
r"""**π -- 개선하는 방법 자신.** 그리고 그것을 바꿀지 **결정하는** tool 하나.

## 경계

    Agent 가 코드를 고치는 것        P  -> P'    (improveloop.py · Phase 2)
    ASTRA 가 제 개선 방법을 고치는 것   π  -> π'    (여기 · Phase 3)

둘은 다르다. 뒤쪽이 자기 발전이다.

## 이 tool 은 코드를 안 고친다 -- **받아들일지 결정한다**

    개선결정()
        지금 상태 D
           ↓
        후보 생성        후보만들기(바탕요약)     -- D 의 연산자표에서 결정적으로 만든다
           ↓
        후보 평가        J정책(후보요약)          -- 정책을 잰다(저장소를 재는 J(P) 가 아니다)
           ↓
        ACCEPT / REJECT  개선결정(바탕, 후보)     -- V 와 ΔJ 둘 다 서야 한다

첫 자기발전 대상은 가장 작은 것 하나다 -- **어떤 변형 연산자를 더 자주 고를 것인가.**

    π = {연산자: 무게}        무게가 크면 시한 안에서 먼저·자주 뽑힌다
    π0 = 무게 전부 1.0        균등. **똑똑한 π 가 아니라 공정한 π** 가 먼저다

## J(π) 는 J(P) 가 아니다

J(P) 는 저장소를 잰다(검사가 의미 변화를 얼마나 잡나). J(π) 는 **정책을 잰다.** 섞으면
*덜 재서 점수를 올리는* π 가 이긴다 -- 그것이 이 저장소가 이미 한 번 본 함정이다.

    J(π) = 시간당 **거짓초록이 있는 칸**을 몇 개 찾았나      (발견칸/시간)

칸 = (파일, 연산자). 칸으로 세면 같은 약점을 거듭 찾는 것이 점수가 되지 않는다(breadth).
그리고 **편향 검사**를 따로 둔다 -- π' 가 공통칸에서 π 와 다른 점수를 내면 그 π' 는 더 빨리
찾은 것이 아니라 **다른 것을 잰 것**이다. 그때는 REJECT 다.

## 기본은 REJECT 다

못 잰 것이 하나라도 있으면 거절한다. 모르는 것은 개선이 아니다.

    python3 policy.py --보고      지금 π 와 결정 이력
    python3 policy.py --후보      마지막 요약에서 π' 후보를 만든다(적지 않는다)
    python3 policy.py --결정      마지막 두 요약으로 ACCEPT/REJECT (적는다)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
정책경로 = "falsegreen/정책.jsonl"
ε = 0.0                  # ΔJ 가 이보다 커야 받아들인다. 같으면 안 바꾼다 -- 흔들지 않는다
무게바닥, 무게천장 = 0.25, 4.0     # π' 가 한 연산자를 아예 버리거나 독차지하지 않게


def 기본정책(연산자들=None) -> dict:
    """π0 -- **공정한 정책.** 무게 전부 1.0. 똑똑한 것이 아니라 공정한 것이 먼저다."""
    if 연산자들 is None:
        import mutate
        연산자들 = mutate.연산자목록()
    return {"이름": "pi0", "무게": {m: 1.0 for m in sorted(연산자들)}, "왜": "균등 -- 첫 π 는 공정해야 한다"}


def 정책들(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 정책경로
    if not p.is_file():
        return []
    out = []
    for 줄 in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if 줄.strip():
            try:
                out.append(json.loads(줄))
            except ValueError:
                continue
    return out


def 지금정책(repo=None) -> dict:
    """**받아들여진 마지막 π.** 없으면 π0. 거절된 후보는 쓰지 않는다."""
    받은 = [x for x in 정책들(repo) if x.get("결정") == "ACCEPT" and x.get("정책")]
    return 받은[-1]["정책"] if 받은 else 기본정책()


def 정책적기(repo=None, 정책: dict = None, 결정: str = "", 까닭=None, 잰것: dict = None) -> dict:
    """결정을 **덧붙인다.** 거절도 적는다 -- 무엇을 해 보고 안 됐는지가 다음 후보의 재료다."""
    repo = Path(repo or REPO)
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "결정": 결정, "정책": 정책, "까닭": list(까닭 or []), "잰것": 잰것 or {}}
    p = repo / 정책경로
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄


# ------------------------------------------------------------------ J(π) -- 정책을 잰다
def J정책(요약줄: dict) -> dict:
    """J(π) = 시간당 **거짓초록이 있는 칸** 수. {발견칸, 시간, Y, 잰칸}.

    칸으로 세는 까닭: 같은 약점에서 변형 백 개를 살려 내는 것은 **하나를 찾은 것**이다.
    그것을 성과로 세면 π 가 한 파일만 파는 쪽으로 흐른다. 시간을 못 알면 Y 는 None 이다
    -- **모르는 것은 0 으로 채우지 않는다.**"""
    칸 = (요약줄 or {}).get("칸") or {}
    import mutate
    발견 = [k for k, v in 칸.items() if (v or {}).get(mutate.살아남음, 0) > 0]
    초 = (요약줄 or {}).get("시한초")
    쓴초 = sum(float((v or {}).get("초") or 0) for v in ((요약줄 or {}).get("연산자") or {}).values())
    기준초 = 쓴초 if 쓴초 > 0 else (float(초) if 초 else 0)
    return {"발견칸": len(발견), "잰칸": len(칸), "시간": round(기준초, 1),
            "Y": (round(len(발견) / 기준초 * 3600, 2) if 기준초 > 0 else None)}


def _번호(이름: str) -> int:
    """`pi3` -> 3. 숫자가 없으면 0. (자릿수를 세면 pi0 -> pi2 가 된다 -- 실측으로 한 번 틀렸다.)"""
    숫 = "".join(c for c in str(이름 or "") if c.isdigit())
    try:
        return int(숫)
    except ValueError:
        return 0


def 후보만들기(바탕요약: dict, 바탕정책: dict = None) -> dict:
    """π' 후보. **결정적이다** -- 같은 D 를 주면 같은 π' 가 나온다(무작위가 아니다).

    무게 ∝ (그 연산자의 FG율) / (변형 하나에 든 초). 찾을 확률이 높고 싸면 더 자주 뽑는다.
    바닥·천장으로 깎는다 -- 한 연산자를 아예 버리면 그것이 재는 의미 변화를 **영영 못 본다**
    (그리고 다음 π 가 그것을 되살릴 근거도 사라진다)."""
    import mutate
    바탕정책 = 바탕정책 or 기본정책()
    연 = (바탕요약 or {}).get("연산자") or {}
    점 = {}
    for m, c in 연.items():
        k, f = c.get(mutate.잡힘, 0), c.get(mutate.살아남음, 0)
        잰것 = c.get("잰것", 0) or 0
        초 = float(c.get("초") or 0)
        if not (k + f) or not 잰것:
            continue
        한개초 = (초 / 잰것) if 초 > 0 else None
        점[m] = (f / (k + f)) / (한개초 if 한개초 else 1.0)
    if not 점:
        return {**바탕정책, "이름": 바탕정책.get("이름", "pi0"),
                "왜": "연산자별 자료가 없다 -- 바꿀 근거가 없어 그대로 둔다"}
    평균 = sum(점.values()) / len(점)
    새무게 = {}
    for m in sorted(set(바탕정책.get("무게") or {}) | set(점)):
        비 = (점.get(m, 평균) / 평균) if 평균 > 0 else 1.0
        새무게[m] = round(min(무게천장, max(무게바닥, 비)), 3)
    앞 = sorted(새무게.items(), key=lambda kv: -kv[1])[:3]
    번 = _번호(바탕정책.get("이름") or (바탕요약.get("정책") or {}).get("이름") or "pi0")
    return {"이름": f"pi{번 + 1}",
            "무게": 새무게,
            "왜": "무게 ∝ FG율 / 변형당 초 -- 자주 찾고 싼 연산자를 더 뽑는다. 위: "
                 + ", ".join(f"{m}×{w}" for m, w in 앞)}


# ------------------------------------------------------------------ 개선결정 -- 이 tool 의 전부
def 개선결정(바탕: dict, 후보: dict, 후보정책: dict = None, 문턱: float = ε) -> dict:
    r"""**(P,π) -> (P',π') -> V,J -> 개선결정.** ACCEPT 는 V 와 ΔJ 가 둘 다 설 때만.

        ACCEPT  ⟺  V(후보) ∧ (J(후보) > J(바탕) + ε)

    V(후보) 는 "후보가 **잴 만한 측정이었나**" 다 -- 코드가 초록인가가 아니다.
      · 사냥을 끝냈나            시한에 잘린 표본은 치우쳐 있다
      · 동등 장치가 살았나        `동등 0` 이 장치가 죽어서 0 이면 판정 전체가 못 믿을 것이다
      · 씨앗이 같나              다른 추출을 견주면 차이가 π 탓인지 씨앗 탓인지 모른다
      · **편향이 없나**          공통칸에서 두 π 의 점수가 어긋나면 π' 는 더 빨리 찾은 것이
                                아니라 **다른 것을 잰 것**이다

    **기본은 REJECT 다.** 못 잰 것이 하나라도 있으면 거절한다 -- 모르는 것은 개선이 아니다."""
    import mutate
    까닭, 막힘 = [], []
    if not (바탕 and 후보):
        return {"결정": "REJECT", "까닭": ["요약이 둘 다 있어야 한다"], "ΔJ": None,
                "V": False, "정책": 후보정책, "잰것": {}}
    if not 후보.get("사냥끝"):
        막힘.append("후보가 사냥을 끝내지 않았다 -- 시한에 잘린 표본은 치우쳐 있다")
    if not 바탕.get("사냥끝"):
        막힘.append("바탕이 사냥을 끝내지 않았다")
    if 후보.get("동등장치") is False:
        막힘.append("동등 장치가 죽었다 -- `동등 0` 이 뜻을 갖지 못한다")
    if (바탕.get("씨앗") is not None and 후보.get("씨앗") is not None
            and 바탕["씨앗"] != 후보["씨앗"]):
        막힘.append(f"씨앗이 다르다 ({바탕['씨앗']} vs {후보['씨앗']}) -- 차이가 π 탓인지 모른다")
    편향 = mutate.점수차(바탕, 후보)
    if not 편향["견줄수있나"]:
        막힘.append("공통칸으로 편향을 못 본다: " + "; ".join(편향["까닭"] or ["모르겠다"]))
    elif 편향["Δ"] is not None and abs(편향["Δ"]) > 0.05:
        막힘.append(f"**편향이 있다** -- 공통칸 점수가 {편향['앞점수']} -> {편향['뒤점수']} "
                   f"({편향['Δ']:+.3f}). 더 빨리 찾은 것이 아니라 다른 것을 쟀다")
    a, b = J정책(바탕), J정책(후보)
    ΔJ = (round(b["Y"] - a["Y"], 2) if (a["Y"] is not None and b["Y"] is not None) else None)
    if ΔJ is None:
        막힘.append("J(π) 를 못 쟀다 -- 쓴 시간을 모른다")
    elif ΔJ <= 문턱:
        막힘.append(f"ΔJ(π) = {ΔJ:+.2f} (시간당 발견칸). 문턱 {문턱} 을 못 넘었다")
    잰것 = {"바탕J": a, "후보J": b, "ΔJ": ΔJ, "편향": 편향}
    if 막힘:
        return {"결정": "REJECT", "까닭": 막힘, "ΔJ": ΔJ, "V": False,
                "정책": 후보정책, "잰것": 잰것}
    까닭.append(f"V 섰다(사냥 끝 · 동등 장치 살음 · 같은 씨앗 · 편향 {편향['Δ']:+.3f})")
    까닭.append(f"ΔJ(π) = {ΔJ:+.2f} 시간당 발견칸 ({a['Y']} -> {b['Y']})")
    return {"결정": "ACCEPT", "까닭": 까닭, "ΔJ": ΔJ, "V": True,
            "정책": 후보정책, "잰것": 잰것}


def 보고(repo=None) -> str:
    것 = 정책들(repo)
    지금 = 지금정책(repo)
    앞 = sorted((지금.get("무게") or {}).items(), key=lambda kv: -kv[1])[:5]
    줄 = [f"**π = {지금.get('이름')}** -- {지금.get('왜', '')}",
         "  무게 위: " + (", ".join(f"{m}×{w}" for m, w in 앞) or "없다")]
    if not 것:
        줄.append(f"\n{정책경로} 가 비어 있다 -- π0(균등)으로 돈다. "
                  "`python3 policy.py --결정` 이 첫 줄을 적는다")
        return "\n".join(줄)
    줄.append(f"\n결정 {len(것)}번:")
    for x in 것[-8:]:
        줄.append(f"  {str(x.get('때'))[:16]} [{x.get('결정')}] "
                  f"{(x.get('정책') or {}).get('이름', '?')} · ΔJ {(x.get('잰것') or {}).get('ΔJ')}")
        for w in (x.get("까닭") or [])[:2]:
            줄.append(f"      {w[:110]}")
    return "\n".join(줄)


def main(argv=None) -> int:
    import mutate
    ap = argparse.ArgumentParser(description="π -- 개선하는 방법 자신. 그리고 그것을 바꿀지 결정한다")
    ap.add_argument("--보고", action="store_true", help="지금 π 와 결정 이력")
    ap.add_argument("--후보", action="store_true", help="마지막 요약에서 π' 후보를 만든다(안 적는다)")
    ap.add_argument("--결정", action="store_true", help="마지막 두 요약으로 ACCEPT/REJECT (적는다)")
    ap.add_argument("--문턱", type=float, default=ε, help=f"ΔJ 문턱 (기본 {ε})")
    a = ap.parse_args(argv)
    요약 = mutate.요약들()
    if a.후보:
        if not 요약:
            print("요약이 없다 -- `python3 mutate.py --요약적기` 를 먼저 돌려라")
            return 2
        후 = 후보만들기(요약[-1], 지금정책())
        print(json.dumps(후, ensure_ascii=False, indent=2))
        return 0
    if a.결정:
        if len(요약) < 2:
            print(f"요약이 {len(요약)}줄이다 -- 바탕과 후보가 둘 다 있어야 한다(사냥 두 번)")
            return 2
        후보정책 = 후보만들기(요약[-2], 지금정책())
        r = 개선결정(요약[-2], 요약[-1], 후보정책, 문턱=a.문턱)
        정책적기(정책=(r["정책"] if r["결정"] == "ACCEPT" else 후보정책),
               결정=r["결정"], 까닭=r["까닭"], 잰것=r["잰것"])
        print(f"**{r['결정']}** · ΔJ(π) {r['ΔJ']}")
        for w in r["까닭"]:
            print(f"  {w}")
        return 0 if r["결정"] == "ACCEPT" else 1
    print(보고())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
