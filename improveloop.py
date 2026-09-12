"""Verified Improvement Loop (Phase 2) -- **채택 루프**. LLM 호출 0회(생성자를 주입받는다).

사용자(2026-09-12):

    P_t -> Generate(P'_1..P'_n) -> V(P'_i) -> J(P_t, P'_i) -> Select -> P_{t+1}

    채택:  P' = argmax J(P_t, P'_i)     단,  V(P') = PASS  ∧  ΔJ(P_t, P') > ε

"검증 가능한 J 다음의 첫 구현 목표는 자기학습이 아니라 Verified Improvement Loop 이고,
그것이 안정화된 뒤 원장을 이용해 π 를 갱신하는 것이 진짜 Phase 3 이다."

## 이 파일이 하는 것과 안 하는 것

하는 것: 후보를 받아 V 로 걸러, 같은 (X, Θ, R) 로 J 를 재고, **ΔJ > ε 인 최고**를 고르고, 한 줄도
빠짐없이 원장에 적는다. 그리고 채택된 것을 새 P_t 로 삼아 다시 돈다.

안 하는 것: **아무것도 재지 않는다.** 생성(improve·investigate) · 검증(rehearsal·mutate) ·
평가(judge) 를 전부 주입받는다. 그래서 가짜를 끼워 루프의 논리만 따로 붙들 수 있고, 실제로는
같은 함수가 그 자리에 들어간다.

## 왜 ε 가 필요한가

ΔJ = 0 인 후보를 채택하면 루프가 **영원히 돈다** -- 아무것도 나아지지 않는 채 커밋이 쌓인다
(오늘 실측한 병: 관문을 지났지만 나아진 것이 없는 머지). 그래서 기본 ε = 0 이고, 같으면 안 받는다.

## 원장 (사용자가 지정한 칸)

    {P_t, P', V, J, ΔJ, hypothesis, cost, result}

`logs/개선루프.jsonl` 에 덧붙이기만 한다. 버린 후보도 적는다 -- **왜 안 받았는지**가 π 의 재료다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
원장상대 = "logs/개선루프.jsonl"
기본ε = 0.0                     # ΔJ 가 이보다 커야 채택한다. 같으면 안 받는다


def _원장(repo: Path) -> Path:
    p = repo / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def 적기(repo, 줄: dict) -> None:
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **줄}
    with _원장(Path(repo or REPO)).open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False, default=str) + "\n")


def 원장읽기(repo=None) -> "list[dict]":
    p = _원장(Path(repo or REPO))
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


def 한바퀴(P, 생성자, V자=None, J자=None, X: dict = None, Θ: dict = None, R: dict = None,
        ε: float = 기본ε, 원장저장소=None, 말하기=None) -> dict:
    """한 바퀴: 후보를 받아 V 로 걸러 J 로 견주고 **ΔJ > ε 인 최고**를 고른다.

    생성자(P) -> [{"이름", "판", "가설"?, ...}]     N(P_t)
    V자(후보)  -> (통과: bool, 말: str)             rehearsal·mutate
    J자(P, X, Θ, R) -> {"Y", "칸", ...}            judge.J
    돌려주는 것: {고른것, 후보들, 본것, 막힌것, ΔJ, 왜}"""
    말 = 말하기 or (lambda s: None)
    if J자 is None:
        import judge
        J자 = judge.J
    바탕 = J자(P, X, Θ, R)
    시작 = time.monotonic()
    후보들 = list(생성자(P) or [])
    # **평가 조건을 원장에 같이 적는다** -- 다른 Θ·X·R 로 잰 J 와 섞이면 ΔJ 가 거짓말이 된다.
    # J 가 되돌려주면 그것을, 안 주면 루프가 받은 파라미터를 적는다(둘 다 없으면 기본값이라고 적는다).
    적기(원장저장소 or P, {"꼴": "바퀴시작", "P_t": str(P), "후보수": len(후보들),
                      "J": 바탕["Y"], "칸": 바탕.get("칸"),
                      "Θ": 바탕.get("Θ") if 바탕.get("Θ") is not None else (Θ if Θ is not None else "기본"),
                      "X": 바탕.get("X") if 바탕.get("X") is not None else (X if X is not None else "기본"),
                      "R": 바탕.get("R") if 바탕.get("R") is not None else (R if R is not None else "기본")})
    말(f"[루프] 후보 {len(후보들)}개 · 바탕 J = {바탕['Y']:.1f}")
    본것, 막힌것 = [], []
    for 후 in 후보들:
        이름 = 후.get("이름") or str(후.get("판"))
        비용 = {"초": round(time.monotonic() - 시작, 1)}
        통과, V말 = (V자(후) if callable(V자) else (True, "V 를 주지 않았다"))
        if not 통과:
            막힌것.append({"이름": 이름, "왜": V말})
            적기(원장저장소 or P, {"꼴": "후보", "P_t": str(P), "P'": 이름, "V": False, "V말": V말[:200],
                              "J": None, "ΔJ": None, "hypothesis": 후.get("가설", ""),
                              "cost": 비용, "result": "버림(V)"})
            말(f"[루프] {이름}: V 빨강 -- {V말[:60]}")
            continue
        그것 = J자(후.get("판") or P, X, Θ, R)
        델타 = 그것["Y"] - 바탕["Y"]
        본것.append({"이름": 이름, "후보": 후, "J": 그것["Y"], "ΔJ": 델타, "칸": 그것.get("칸")})
        적기(원장저장소 or P, {"꼴": "후보", "P_t": str(P), "P'": 이름, "V": True, "V말": V말[:200],
                          "J": 그것["Y"], "ΔJ": 델타, "hypothesis": 후.get("가설", ""),
                          "cost": 비용, "result": "견줌"})
        말(f"[루프] {이름}: V 초록 · J {그것['Y']:.1f} · ΔJ {델타:+.1f}")
    받을것 = [x for x in 본것 if x["ΔJ"] > ε]
    if not 받을것:
        왜 = (f"ΔJ > ε({ε}) 인 후보가 없다 (V 지남 {len(본것)}개 · 막힘 {len(막힌것)}개)"
             if 본것 else f"V 를 지난 후보가 없다 (후보 {len(후보들)}개)")
        적기(원장저장소 or P, {"꼴": "바퀴끝", "P_t": str(P), "result": "채택없음", "왜": 왜,
                          "ΔJ최고": (max(x["ΔJ"] for x in 본것) if 본것 else None)})
        말(f"[루프] 채택 없음 -- {왜}")
        return {"고른것": None, "후보들": 후보들, "본것": 본것, "막힌것": 막힌것, "ΔJ": None, "왜": 왜}
    최고 = max(받을것, key=lambda x: x["ΔJ"])
    같은것 = [x for x in 받을것 if x["ΔJ"] == 최고["ΔJ"]]
    고른 = 같은것[0]                                    # 동점이면 먼저 온 것 -- 흔들지 않는다
    적기(원장저장소 or P, {"꼴": "바퀴끝", "P_t": str(P), "P'": 고른["이름"], "V": True,
                      "J": 고른["J"], "ΔJ": 고른["ΔJ"], "hypothesis": 고른["후보"].get("가설", ""),
                      "cost": {"초": round(time.monotonic() - 시작, 1)}, "result": "채택",
                      "칸변화": {k: (바탕["칸"].get(k), 고른["칸"].get(k)) for k in (고른["칸"] or {})
                              if 바탕["칸"].get(k) != 고른["칸"].get(k)}})
    말(f"[루프] **채택** {고른['이름']} · ΔJ {고른['ΔJ']:+.1f}")
    return {"고른것": 고른, "후보들": 후보들, "본것": 본것, "막힌것": 막힌것, "ΔJ": 고른["ΔJ"],
            "왜": (f"V 를 지난 {len(본것)}개 중 ΔJ 최고({고른['ΔJ']:+.1f})를 채택"
                  + (f" · 동점 {len(같은것)}개라 먼저 온 것" if len(같은것) > 1 else ""))}


def 여러바퀴(P, 생성자, 적용자, V자=None, J자=None, 바퀴수: int = 5, ε: float = 기본ε,
         X: dict = None, Θ: dict = None, R: dict = None, 원장저장소=None, 말하기=None) -> dict:
    """P_t -> P_{t+1} -> … 채택이 없으면 멈춘다. 적용자(고른것, P) -> 새 P_t.

    **멈춤이 실패가 아니다** -- "더 나아질 후보를 못 만들었다" 는 측정 결과다(원장에 남는다)."""
    말 = 말하기 or (lambda s: None)
    지금 = P
    바퀴들 = []
    for n in range(1, max(1, 바퀴수) + 1):
        말(f"[루프] 바퀴 {n}/{바퀴수} · P_t = {지금}")
        r = 한바퀴(지금, 생성자, V자, J자, X, Θ, R, ε, 원장저장소 or P, 말하기)
        바퀴들.append({"바퀴": n, "ΔJ": r["ΔJ"], "고른것": (r["고른것"] or {}).get("이름"),
                     "본것": len(r["본것"]), "막힌것": len(r["막힌것"])})
        if r["고른것"] is None:
            적기(원장저장소 or P, {"꼴": "루프끝", "바퀴": n, "result": "멈춤", "왜": r["왜"]})
            return {"P": 지금, "바퀴들": 바퀴들, "멈춘까닭": r["왜"], "나아간바퀴": len([x for x in 바퀴들 if x["ΔJ"]])}
        지금 = 적용자(r["고른것"], 지금) or 지금
    적기(원장저장소 or P, {"꼴": "루프끝", "바퀴": len(바퀴들), "result": "바퀴수 다 씀"})
    return {"P": 지금, "바퀴들": 바퀴들, "멈춘까닭": "바퀴수를 다 썼다",
            "나아간바퀴": len([x for x in 바퀴들 if x["ΔJ"]])}


def 보고(repo=None) -> str:
    행들 = 원장읽기(repo)
    채택 = [x for x in 행들 if x.get("result") == "채택"]
    버림 = [x for x in 행들 if str(x.get("result", "")).startswith("버림")]
    견줌 = [x for x in 행들 if x.get("result") == "견줌"]
    줄 = [f"**개선 루프** -- 원장 {len(행들)}줄 · 채택 {len(채택)} · 견줌 {len(견줌)} · 버림 {len(버림)}"]
    if 채택:
        총 = sum(float(x.get("ΔJ") or 0) for x in 채택)
        줄.append(f"쌓인 ΔJ = {총:+.1f}")
        for x in 채택[-5:]:
            이름 = x.get("P'") or "?"
            가설 = str(x.get("hypothesis") or "")[:40]
            때 = str(x.get("때", ""))[:16]
            줄.append(f"  {때} {이름} · ΔJ {float(x.get('ΔJ') or 0):+.1f}"
                      + (f" · 가설: {가설}" if 가설 else ""))
    없음 = [x for x in 행들 if x.get("result") == "채택없음"]
    if 없음:
        줄.append(f"채택 없이 끝난 바퀴 {len(없음)}개 -- 마지막 까닭: {str(없음[-1].get('왜'))[:90]}")
    return "\n".join(줄)
