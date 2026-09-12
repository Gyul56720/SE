"""J(P) -- **나아졌나를 수로 잰다.** 그리고 argmax 로 고른다. LLM 호출 0회.

사용자(2026-09-12):

    P_{t+1} = argmax_{P' ∈ N(P_t)} J(P')     subject to   V(P') = PASS

지금 파이프라인은 이 식과 세 자리에서 어긋나 있었다.

    N(P_t)   제안을 **하나** 낸다(되물어 다시 청하는 것은 집합이 아니다) -> |N| = 1
    J        없다. "검사를 지났나"(V)만 묻고 "나아졌나"를 안 묻는다
    argmax   없다. **먼저 V 를 지난 것**을 쓴다

V 는 rehearsal·mutate 가 한다(이 파일은 V 를 다시 재지 않는다). 여기서는 J 와 고르기만 한다.

## J 를 무엇으로 재나 -- 모델의 말이 아니라 원장과 코드로

    관찰파일수   변형이 **하나라도 Killed** 된 파일 수            많을수록 좋다
    거짓초록수   Survived(비동등 변형이 살아남음)                 적을수록 좋다
    미정의수     함수 안에서 없는 이름을 부르는 자리              적을수록 좋다
    검사없는파일수  재는 검사를 못 찾은 코드 파일                  적을수록 좋다

## J 도 거짓 초록을 낼 수 있다 -- 그래서 속임 내성을 먼저 박았다

실측 2026-09-12: `ledgerstat` 의 표는 여섯 칸이 늘 0 이었다. 그것이 **아무것도 구별하지 못하는
J** 다. 같은 함정이 여기 있다 -- 예를 들어 `거짓초록수` 만 보면 **검사를 지우는 것이 개선**이 된다
(변형이 살아남을 자리가 없어지므로). 그래서 J 의 칸을 이렇게 골랐다:

  · 검사를 지우면 `관찰파일수` 가 줄고 `검사없는파일수` 가 늘어 **J 가 반드시 떨어진다**
  · 아무것도 단언하지 않는 검사를 더해도 `관찰파일수` 는 **안 오른다**(Killed 가 있어야 센다)
  · 진짜 단언을 더해 변형이 잡히면 `관찰파일수` 가 오르고 `거짓초록수` 가 줄어 **J 가 오른다**

tests/test_judge.py 가 이 셋을 붙든다. J 가 속임에 무너지면 그 위의 argmax 는 **틀린 방향으로**
최적화한다 -- 그것이 J 없는 것보다 나쁘다.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

# ------------------------------------------------------------------ J 의 네 파라미터
# 사용자(2026-09-12): latency/accuracy/memory 같은 특정 잣대에 묶지 말고 일반형으로 둔다.
#
#   J : (P, X, Θ, R) -> Y
#
#     P  평가 대상 프로그램(여기서는 저장소 나무)
#     X  입력·데이터·작업 조건      (어느 파일을 보나, 원장을 어디서 읽나)
#     Θ  평가 기준·목표·가중치      (어느 칸을 보나, 무게, 방향)
#     R  실행·측정 프로토콜          (무엇으로 재나, 시한)
#
# **평가에 영향을 주는 외부 조건을 전부 파라미터로 끌어낸다.** 같은 프로그램이라도 X·Θ·R 이 바뀌면
# Y 가 달라지므로, 코드 안에 박아 두면 같은 수를 다른 뜻으로 읽게 된다(그것이 조용한 거짓 초록이다).
# 그래서 J 는 Y 와 함께 (X, Θ, R) 을 되돌려주고, 원장에 적을 때도 같이 적는다 -- 재현 가능해야 한다.
무게 = {"관찰파일수": 10.0, "거짓초록수": -3.0, "미정의수": -5.0, "검사없는파일수": -1.0}
기본Θ = {"무게": dict(무게), "방향": "최대"}        # 목표: Y 를 크게
기본X = {"파일들": None, "원장저장소": None}        # None = 저장소 전체 · 제 원장
기본R = {"측정자": "잣대", "초": 0}                # 원장과 정적 사실만 읽는다(검사를 돌리지 않는다)


def _코드파일들(repo: Path) -> "list[str]":
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "ls-files", "-z", "*.py"],
                       capture_output=True, text=True)
    return [x for x in r.stdout.split("\0") if x and not x.startswith("tests/")]


def 잣대(repo=None, 원장저장소=None, 파일들: "list[str]" = None) -> dict:
    """J 의 칸들. **여기서 검사를 돌리지 않는다** -- 이미 난 판정(mutate 원장)과 정적 사실만 읽는다.

    `원장저장소` 를 따로 주면 변형 원장은 그쪽에서 읽는다(후보 판을 재면서 원장은 본 저장소의 것을
    쓸 때). 원장이 없으면 관찰파일수·거짓초록수는 0 이다 -- **안 재 본 것을 좋게 세지 않는다.**"""
    repo = Path(repo or REPO)
    칸 = {"관찰파일수": 0, "거짓초록수": 0, "미정의수": 0, "검사없는파일수": 0, "코드파일수": 0, "검사파일수": 0}
    try:
        import mutate
        행들 = mutate.원장읽기(원장저장소 or repo)
        잡은파일 = {str(x.get("target", "")).split(":")[0] for x in 행들 if x.get("outcome") == mutate.잡힘}
        칸["관찰파일수"] = len([f for f in 잡은파일 if f and (repo / f).is_file()])
        칸["거짓초록수"] = len([x for x in 행들 if x.get("outcome") == mutate.살아남음
                           and (repo / str(x.get("target", "")).split(":")[0]).is_file()])
    except Exception:                                  # noqa: BLE001 -- 원장이 없으면 0 이다
        pass
    코드들 = list(파일들) if 파일들 is not None else _코드파일들(repo)
    칸["코드파일수"] = len(코드들)
    칸["검사파일수"] = len(list((repo / "tests").glob("test_*.py"))) if (repo / "tests").is_dir() else 0
    try:
        import rehearsal
        셈 = 0
        for rel in 코드들:
            src = (repo / rel).read_text(encoding="utf-8", errors="replace")
            셈 += len(rehearsal._미정의한파일(src, rel))
        칸["미정의수"] = 셈
    except Exception:                                  # noqa: BLE001
        pass
    try:
        import mutate
        칸["검사없는파일수"] = len([rel for rel in 코드들 if not mutate._검사고르기(repo, rel)])
    except Exception:                                  # noqa: BLE001
        pass
    return 칸


def J(P=None, X: dict = None, Θ: dict = None, R: dict = None) -> dict:
    """J(P; X, Θ, R) -> {Y, 칸, X, Θ, R}. **Y 하나만 주지 않는다** -- 무엇을 어떻게 재서 나온 수인지
    같이 준다. 그래야 다른 때·다른 조건의 Y 와 견줄 수 있는지 판단할 수 있다.

    R["측정자"] 에 함수를 주면 그것으로 칸을 잰다(기본은 이 파일의 `잣대`). 검사에서 가짜 측정자를
    끼워 J 의 논리만 따로 붙들 수 있다."""
    X = {**기본X, **(X or {})}
    Θ = {**기본Θ, **(Θ or {})}
    R = {**기본R, **(R or {})}
    재는자 = R.get("측정자")
    if callable(재는자):
        칸 = 재는자(P, X.get("원장저장소"))            # R -- 측정 프로토콜을 갈아끼운다(검사에서 쓴다)
    else:
        칸 = 잣대(P, X.get("원장저장소"), X.get("파일들"))
    w = Θ.get("무게") or 무게
    Y = sum(w.get(k, 0.0) * 칸.get(k, 0) for k in w)
    if Θ.get("방향") == "최소":
        Y = -Y
    return {"Y": Y, "칸": 칸, "X": X, "Θ": {"무게": dict(w), "방향": Θ.get("방향")}, "R": dict(R)}


def ΔJ(P, P2, X: dict = None, Θ: dict = None, R: dict = None) -> dict:
    """Δ_J(P, P'; X, Θ, R) = J(P') - J(P). **같은 (X, Θ, R) 로 둘을 재야 뜻이 있다.**"""
    a, b = J(P, X, Θ, R), J(P2, X, Θ, R)
    바뀐 = {k: (a["칸"].get(k, 0), b["칸"].get(k, 0)) for k in (Θ or 기본Θ).get("무게", 무게)
          if a["칸"].get(k, 0) != b["칸"].get(k, 0)}
    return {"Δ": b["Y"] - a["Y"], "전": a["Y"], "후": b["Y"], "칸변화": 바뀐,
            "나아졌나": b["Y"] > a["Y"], "X": a["X"], "Θ": a["Θ"], "R": a["R"]}


def 구별하나(Pa, Pb, X: dict = None, Θ: dict = None, R: dict = None) -> "tuple[bool, str]":
    """Obs_J -- **다른 두 프로그램을 J 가 구별하나.**  Pa ≁ Pb  =>  J(Pa) ≠ J(Pb).

    구별하지 못하는 J 는 `ledgerstat` 의 여섯 칸이 늘 0 이던 것과 같다 -- 수는 나오는데 아무것도
    말하지 않는다. 그런 J 위에 세운 argmax 는 **아무 방향으로도** 최적화하지 않는다."""
    a, b = J(Pa, X, Θ, R), J(Pb, X, Θ, R)
    if a["Y"] != b["Y"]:
        return True, f"구별한다 (J {a['Y']:.1f} vs {b['Y']:.1f})"
    return False, f"**구별하지 못한다** (둘 다 J {a['Y']:.1f} · 칸도 {'같다' if a['칸'] == b['칸'] else '다른데 합이 같다'})"


def 타당한가(쌍들: "list[tuple]", X: dict = None, Θ: dict = None, R: dict = None) -> dict:
    """Valid(J) -- **다르다고 알려진 쌍들을 J 가 다 구별하나.** 하나라도 못 구별하면 J 는 타당하지 않다.

    쌍 = (Pa, Pb, 이름). 이 함수가 J 에 대한 red-green 이다: J 를 속이는 쌍을 넣어 깨뜨려 본다."""
    결과 = []
    for 쌍 in 쌍들 or []:
        Pa, Pb = 쌍[0], 쌍[1]
        이름 = 쌍[2] if len(쌍) > 2 else f"{Pa} vs {Pb}"
        됨, 말 = 구별하나(Pa, Pb, X, Θ, R)
        결과.append({"이름": 이름, "구별": 됨, "말": 말})
    못한것 = [x for x in 결과 if not x["구별"]]
    return {"타당한가": (bool(결과) and not 못한것), "못한것": 못한것, "결과": 결과,
            "말": (f"쌍 {len(결과)}개를 다 구별한다" if 결과 and not 못한것
                  else (f"**{len(못한것)}개를 못 구별한다**: " + ", ".join(x["이름"] for x in 못한것[:4])
                        if 못한것 else "견줄 쌍이 없다 -- 타당성을 주장할 수 없다"))}


def 개선인가(P, P2, V=None, 쌍들: "list[tuple]" = None,
          X: dict = None, Θ: dict = None, R: dict = None) -> dict:
    """Improve(P, P') = V(P') ∧ Valid(J) ∧ J(P') ≻ J(P). **세 항이 다 서야 개선이다.**

    V 는 주입받는다(여기서 검증하지 않는다 -- rehearsal·mutate 의 몫이다).
    `쌍들` 을 주면 Valid(J) 를 그 자리에서 확인한다. 안 주면 Valid 는 못잼이고, **개선을 주장하지 않는다.**"""
    V통과, V말 = (V(P2) if callable(V) else (True, "V 를 주지 않았다"))
    타당 = 타당한가(쌍들, X, Θ, R) if 쌍들 else {"타당한가": False, "말": "Valid(J) 를 안 쟀다"}
    델타 = ΔJ(P, P2, X, Θ, R)
    됨 = bool(V통과) and bool(타당["타당한가"]) and bool(델타["나아졌나"])
    막힌 = []
    if not V통과:
        막힌.append(f"V(P')=FAIL: {V말}")
    if not 타당["타당한가"]:
        막힌.append(f"Valid(J) 안 섬: {타당['말']}")
    if not 델타["나아졌나"]:
        막힌.append(f"ΔJ = {델타['Δ']:+.1f} (나아지지 않았다)")
    return {"개선인가": 됨, "V": V통과, "Valid(J)": 타당["타당한가"], "ΔJ": 델타["Δ"],
            "칸변화": 델타["칸변화"], "막힌것": 막힌,
            "말": ("개선이다 -- V 통과 · J 타당 · ΔJ " + f"{델타['Δ']:+.1f}") if 됨
                 else ("개선이 아니다 -- " + " · ".join(막힌))}


def 더나은가(이전칸: dict, 지금칸: dict) -> "tuple[bool, str]":
    """J 로 견준다. 같으면 '아니다' -- 개선을 주장하려면 수가 움직여야 한다."""
    전 = sum(무게[k] * (이전칸 or {}).get(k, 0) for k in 무게)
    후 = sum(무게[k] * (지금칸 or {}).get(k, 0) for k in 무게)
    바뀐 = [f"{k} {(이전칸 or {}).get(k, 0)}->{(지금칸 or {}).get(k, 0)}"
          for k in 무게 if (이전칸 or {}).get(k, 0) != (지금칸 or {}).get(k, 0)]
    말 = f"J {전:.1f} -> {후:.1f}" + (" · " + ", ".join(바뀐) if 바뀐 else " · 칸이 그대로다")
    return (후 > 전), 말


def 고르기(후보들: "list[dict]", V=None, J자=None) -> dict:
    """P_{t+1} = argmax_{P' ∈ N} J(P') s.t. V(P')=PASS. **순수 선택 -- 재지 않는다(주입받는다).**

    후보 = {"이름", "판", ...}. `V(후보) -> (통과, 말)`, `J자(후보) -> (점수, 칸)`.
    V 를 지난 것이 없으면 {"고른것": None, 왜}. 점수가 같으면 **먼저 온 것**을 쓴다(흔들지 않는다)."""
    V = V or (lambda 후보: (True, ""))
    J자 = J자 or (lambda 후보: (0.0, {}))
    본것, 막힌것 = [], []
    for 후 in 후보들 or []:
        통과, 왜 = V(후)
        if not 통과:
            막힌것.append({"이름": 후.get("이름"), "왜": 왜})
            continue
        점수, 칸 = J자(후)
        본것.append({"이름": 후.get("이름"), "후보": 후, "점수": 점수, "칸": 칸})
    if not 본것:
        return {"고른것": None, "본것": [], "막힌것": 막힌것,
                "왜": f"V 를 지난 후보가 없다(후보 {len(후보들 or [])}개 · 막힘 {len(막힌것)}개)"}
    최고 = max(본것, key=lambda x: x["점수"])
    같은것 = [x for x in 본것 if x["점수"] == 최고["점수"]]
    고른 = 같은것[0]
    return {"고른것": 고른, "본것": 본것, "막힌것": 막힌것,
            "왜": (f"후보 {len(후보들)}개 중 V 를 지난 {len(본것)}개에서 J 최고({고른['점수']:.1f})를 골랐다"
                  + (f" · 동점 {len(같은것)}개라 먼저 온 것" if len(같은것) > 1 else ""))}


def 보고(repo=None) -> str:
    _r = J(repo)
    점수, 칸 = _r["Y"], _r["칸"]
    줄 = [f"**J(P) = {점수:.1f}**  (무게: " + ", ".join(f"{k}×{v:+g}" for k, v in 무게.items()) + ")"]
    for k in ("관찰파일수", "거짓초록수", "미정의수", "검사없는파일수"):
        줄.append(f"  {k:12} {칸.get(k, 0):>6}   기여 {무게[k] * 칸.get(k, 0):+.1f}")
    줄.append(f"  (코드 {칸.get('코드파일수', 0)}개 · 검사 {칸.get('검사파일수', 0)}개)")
    if 칸.get("관찰파일수", 0) == 0:
        줄.append("  관찰파일수가 0 이다 -- `!거짓초록` 을 한 번도 안 돌렸다. J 의 절반이 비어 있다")
    return "\n".join(줄)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="J(P) -- 나아졌나를 수로 잰다")
    ap.add_argument("--저장소", default=None)
    a = ap.parse_args(argv)
    print(보고(Path(a.저장소) if a.저장소 else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
