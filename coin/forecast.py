"""**예보 원장과 채점.** 이 파이프라인이 쓸모 있는지 아는 유일한 길.

    python3 coin/forecast.py --걸어보기 --자산 BTC --유형 규제금지 --지평 7
    python3 coin/forecast.py --채우기        지평이 지난 예보의 실현 칸을 채운다
    python3 coin/forecast.py --채점          Brier · 기저율 대비 skill
    python3 coin/forecast.py --보고          칸별 신뢰도까지

## 무엇을 채점하는가 -- 산문이 아니라 **확률 벡터**다

LLM 이 쓴 글은 채점할 수 없다. 그래서 채점하는 것은 `scenario.py` 가 낸
**칸별 확률 벡터**다. 그것은 원장이 정한 것이지 모델이 정한 것이 아니므로,
채점하는 것은 곧 **사건 연구에 예측력이 있는가**를 재는 것이다.

    나가는 것   (칸1..칸5 의 확률, 지평, 기준일, 어느 잰것에서 왔나)
    지평이 지나면  실제로 어느 칸에 떨어졌나
    채점        Brier · log-loss · **기저율 예보자 대비 skill**

## skill 이 요점이다 -- Brier 혼자로는 아무 뜻이 없다

칸이 다섯이면 아무 것도 모르는 예보자(칸마다 20%)의 Brier 는 0.8 이다. 우리 것이
0.78 이라고 좋은 것이 아니다. 그래서 늘 같이 낸다:

    skill = 1 - BS(우리) / BS(기저율 예보자)

`skill <= 0` 이면 **예측력이 없다.** 그것이 이 파이프라인의 정직한 답일 가능성이
높고, 그렇게 말할 수 있어야 이것이 측정 도구다. 못 말하면 광고다.

## 진짜 어려운 것 -- 표본을 어떻게 모으나

D+7 예보는 이레 뒤에야 채점된다. 한 주에 하나씩 쌓으면 skill 이 뜻을 가지려면
몇 년이 걸린다. 그동안은 **아무것도 모르는 채로 쓰게 된다.**

그래서 `걸어보기()`(walk-forward)를 둔다 -- 과거의 각 날 T 로 돌아가,
**그날까지의 자료만으로** 사건 연구를 다시 하고, 그때 냈을 예보를 T+h 로 채점한다.
그러면 수백 개의 채점된 예보가 지금 바로 생긴다.

**이것이 이 파일에서 제일 조심할 자리다.** 미리보기가 한 칸이라도 새면 skill 이
거짓으로 올라간다. 그래서 T 시점에서:

    가격    T 까지의 봉만                (계열을 자른다)
    사건    최초 보도가 T 이전인 것만
    칸 경계 T 까지의 널 분포가 정한다     (`scenario.칸경계` 를 자른 계열로)
    널      T 까지의 날들에서만 뽑는다

넷 중 하나라도 T 뒤를 보면 그 skill 은 거짓이다. `tests/test_coin_forecast.py` 가
**일부러 미래를 흘려 넣고** skill 이 뛰는지 본다 -- 안 뛰면 자르기가 안 듣는 것이다.

## 무엇을 채점하지 않는가

**맞았는지 틀렸는지로 답을 기각하지 않는다.** 확률 예보는 한 번으로 못 재고,
한 번으로 재려 들면 20% 를 준 칸이 나왔다고 "틀렸다" 고 말하게 된다. 채점은
**모아서** 뜻이 생기고, 그래서 `gate.py` 는 이 파일을 안 읽는다.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import scenario as SC                                       # noqa: E402

길 = Path(__file__).resolve().parent / "corpus/forecast.json"


def 불러오기(경로=None) -> dict:
    p = Path(경로) if 경로 else 길
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"예보": []}


def 저장(원장: dict, 경로=None) -> Path:
    p = Path(경로) if 경로 else 길
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(원장, ensure_ascii=False), encoding="utf-8")
    return p


def 적기(뭉치: dict, 기준일: str, 경로=None, 꼬리: str = "") -> dict:
    """예보 하나를 원장에. **확률 벡터와 칸 경계를 그대로 남긴다** -- 나중에 채점하려면
    그때의 칸이 무엇이었는지가 있어야 한다."""
    칸별 = sorted(뭉치["시나리오"], key=lambda s: s["칸"])
    예 = {"자산": 뭉치["자산"], "유형": 뭉치["유형"], "지평": 뭉치["지평"],
          "기준일": 기준일, "경계": list(뭉치["경계"]),
          "확률": [s["확률"] for s in 칸별], "표본n": 뭉치["n"],
          "널확률": 칸별[0]["널확률"] if 칸별 else 0.0,
          "실현칸": None, "실현수익": None, "꼬리": 꼬리,
          "적은때": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    원장 = 불러오기(경로)
    원장.setdefault("예보", []).append(예)
    저장(원장, 경로)
    return 예


def 채우기(계열들: dict, 경로=None) -> int:
    """지평이 지난 예보의 **실현 칸**을 채운다. 못 세면 그냥 둔다."""
    원장 = 불러오기(경로)
    센것 = 0
    for 예 in 원장.get("예보", []):
        if 예.get("실현칸") is not None:
            continue
        c = 계열들.get(예["자산"])
        if c is None:
            continue
        D0 = c.있는날(예["기준일"])
        r = c.수익(D0, 예["지평"]) if D0 else None
        if r is None:
            continue
        예["실현수익"] = r
        예["실현칸"] = SC._칸번호(r, 예["경계"])
        센것 += 1
    if 센것:
        저장(원장, 경로)
    return 센것


def _brier(p: list, 참칸: int) -> float:
    return sum((pi - (1.0 if i == 참칸 else 0.0)) ** 2 for i, pi in enumerate(p))


def _logloss(p: list, 참칸: int, 바닥: float = 1e-6) -> float:
    return -math.log(max(바닥, p[참칸] if 0 <= 참칸 < len(p) else 바닥))


def 채점(원장: dict = None, 최소: int = 20) -> dict:
    """**기저율 예보자와 견준다.** 그것 없이는 Brier 혼자 아무 뜻이 없다."""
    원장 = 원장 if 원장 is not None else 불러오기()
    잰것 = [e for e in (원장.get("예보") or []) if e.get("실현칸") is not None]
    if not 잰것:
        return {"n": 0, "왜": "채점할 것이 없다 -- 지평이 지난 예보가 없다"}
    우리 = sum(_brier(e["확률"], e["실현칸"]) for e in 잰것) / len(잰것)
    기저 = sum(_brier([e["널확률"]] * len(e["확률"]), e["실현칸"]) for e in 잰것) / len(잰것)
    로그 = sum(_logloss(e["확률"], e["실현칸"]) for e in 잰것) / len(잰것)
    skill = (1 - 우리 / 기저) if 기저 else float("nan")
    맞춤 = sum(1 for e in 잰것
               if e["확률"] and e["실현칸"] == max(range(len(e["확률"])),
                                                key=lambda i: e["확률"][i])) / len(잰것)
    return {"n": len(잰것), "Brier": 우리, "기저Brier": 기저, "skill": skill,
            "logloss": 로그, "머리맞춤": 맞춤,
            "모자람": len(잰것) < 최소, "최소": 최소,
            "왜": (f"표본이 {len(잰것)}개다 (최소 {최소}) -- skill 을 믿지 마라"
                  if len(잰것) < 최소 else "")}


def 신뢰도(원장: dict = None, 칸수: int = 10) -> list:
    """**준 확률과 실제로 난 비율이 맞나.** 0.8 을 준 것들이 여덟 번에 한 번 나면 거짓말이다."""
    원장 = 원장 if 원장 is not None else 불러오기()
    통 = [[0, 0.0] for _ in range(칸수)]
    for e in (원장.get("예보") or []):
        if e.get("실현칸") is None:
            continue
        for i, p in enumerate(e["확률"]):
            b = min(칸수 - 1, int(p * 칸수))
            통[b][0] += 1
            통[b][1] += 1.0 if i == e["실현칸"] else 0.0
    return [{"준확률": (i + 0.5) / 칸수, "센것": n, "실제": (s / n if n else float("nan"))}
            for i, (n, s) in enumerate(통) if n]


# ------------------------------------------------------------------ 걸어보기
def _자른계열(계열, 까지: str):
    """**T 까지의 봉만.** 미리보기가 한 칸이라도 새면 skill 이 거짓으로 오른다."""
    from coin import price as PR
    봉 = [[d, 0, 0, 0, 계열.종가[d], 0] for d in 계열.날들 if d <= 까지]
    return PR.계열({"자산": 계열.자산, "봉": 봉})


def 걸어보기(계열, 사건들: list, 유형: str, 자산: str, 지평: int,
           걸음: int = 1, 최소표본: int = 8, 판수: int = 400,
           경로=None, 적기까지: bool = True, 유예: float = None) -> dict:
    """과거의 **사건 날마다** T 로 돌아가, 그날까지의 자료만으로 재고 T+h 로 채점한다.

    ## 달력 날이 아니라 사건 날이다 -- 처음에 이것을 틀렸다

    첫 판은 서른 날마다 예보를 냈다. 그런데 이 파이프라인의 예보는 조건부다 --
    "**그 뉴스가 뜨면** 며칠 뒤에 얼마" 다. 아무 날에나 그 조건부 분포를 갖다 대면
    조건이 없는 날에 조건부 답을 하는 것이고, 그러면 **기저율 예보자보다 나쁠 수밖에
    없다.** 실측이 그랬다: 신호를 -10% 로 심어 놓고도 skill 이 -0.372 였다.

    맞게 고치면 예보는 **사건이 실제로 난 날에만** 나간다. 그 대신 표본이 사건 수만큼
    으로 줄고, 그것이 이 채점이 오래 걸리는 진짜 까닭이다.

    ## 미리보기를 막는 네 자리

        가격    T 까지의 봉만              (`_자른계열`)
        사건    최초 보도가 **T 이전**인 것만 -- 지금 재는 그 사건도 뺀다
        칸 경계 T 까지의 널 분포가 정한다
        널      T 까지의 날들에서만

    둘째가 특히 그렇다. 지금 예보하려는 사건까지 표본에 넣으면 **자기 답을 보고
    예보하는 것**이다.
    """
    from coin import event as EV
    from coin import price as PR
    유예 = PR.유예기본 if 유예 is None else 유예
    # 이 유형·자산의 사건 날(D0)만. 여기서만 예보가 나간다
    D0들 = EV.사건날들(계열, 사건들, 유형, 자산, "최초", 유예)
    낸것, 건너뜀 = [], 0
    for k, T in enumerate(D0들):
        if k % max(1, 걸음):
            continue
        if 계열.수익(T, 지평) is None:          # 채점할 미래가 없다
            건너뜀 += 1
            continue
        잘린 = _자른계열(계열, T)
        # **T 이전 사건만.** 지금 재는 이 사건도 뺀다 -- 자기 답을 보면 안 된다
        옛사건 = [e for e in 사건들 if (e.get("최초") or "")[:10] < T]
        if len(옛사건) < 최소표본:
            건너뜀 += 1
            continue
        r = EV.재기(잘린, 옛사건, 유형, 자산, 지평, 판수=판수, 최소표본=최소표본)
        if r["미검증"]:
            건너뜀 += 1
            continue
        뭉 = SC.뽑기(잘린, r)                 # 칸 경계도 T 까지의 널이 정한다
        if not 뭉.get("시나리오"):
            건너뜀 += 1
            continue
        낸것.append(적기(뭉, T, 경로, 꼬리="걸어보기") if 적기까지 else 뭉)
    return {"낸것": len(낸것), "건너뜀": 건너뜀, "사건날": len(D0들),
            "지평": 지평, "유형": 유형, "자산": 자산}


def 적기줄(s: dict) -> str:
    if not s.get("n"):
        return f"  채점: {s.get('왜','')}"
    별 = "**예측력 없음**" if s["skill"] <= 0 else f"skill {s['skill']:+.3f}"
    꼬 = f"  ({s['왜']})" if s.get("왜") else ""
    return (f"  채점 n={s['n']} · Brier {s['Brier']:.4f} vs 기저 {s['기저Brier']:.4f} "
            f"-> {별} · logloss {s['logloss']:.3f} · 머리맞춤 {s['머리맞춤']*100:.0f}%{꼬}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--걸어보기", action="store_true")
    ap.add_argument("--채우기", action="store_true")
    ap.add_argument("--채점", action="store_true")
    ap.add_argument("--보고", action="store_true")
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--유형", default="")
    ap.add_argument("--지평", type=int, default=7)
    ap.add_argument("--걸음", type=int, default=30)
    a = ap.parse_args(argv)

    from coin import price as PR
    if a.걸어보기:
        원 = PR.불러오기(a.자산)
        if not 원:
            print(f"가격 원장이 없다: {a.자산}", file=sys.stderr)
            return 3
        c = PR.계열(원)
        사건p = Path(__file__).resolve().parent / "corpus/events.json"
        사건 = json.loads(사건p.read_text(encoding="utf-8")).get("사건", []) if 사건p.exists() else []
        if not a.유형:
            print("--유형 을 줘라", file=sys.stderr)
            return 3
        r = 걸어보기(c, 사건, a.유형, a.자산, a.지평, a.걸음)
        print(f"  걸어보기: 낸 예보 {r['낸것']}개 · 건너뜀 {r['건너뜀']}")
        계 = {a.자산: c}
        print(f"  실현 칸 채움: {채우기(계)}개")
        print(적기줄(채점()))
        return 0

    if a.채우기:
        계 = {}
        for x in {e["자산"] for e in 불러오기().get("예보", [])}:
            원 = PR.불러오기(x)
            if 원:
                계[x] = PR.계열(원)
        print(f"  채움 {채우기(계)}개")
        return 0

    s = 채점()
    print(적기줄(s))
    if a.보고 or a.채점:
        for r in 신뢰도():
            print(f"    준확률 {r['준확률']*100:4.0f}% -> 실제 {r['실제']*100:5.1f}% "
                  f"({r['센것']}번)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
