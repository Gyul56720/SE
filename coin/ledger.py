"""**잰것 원장.** 답이 인용할 수 있는 것은 여기 있는 수뿐이다.

    python3 coin/ledger.py --보기
    python3 coin/ledger.py --찾기 규제금지 --지평 7

`brief/ledger.py` 와 같은 자리다 -- 원장에 없는 수는 보고서에 못 들어간다.
`gate.py` 가 답의 수를 여기에 대조하고(C001), **여기 적힌 날짜로 다시 셈해**
같은 값이 나오는지 본다(C002).

## 이 원장에 뭘 적나 -- 다시 셀 수 있는 것 전부

값만 적으면 못 다시 센다. 그래서 `씨`·`널꼴`·`널판수`·`유예`·`날들` 이 같이 적힌다.
이 다섯이 없으면 C002 는 초록불을 낼 수 없고, **검사 못 하는 초록불은 빨간불보다
나쁘다.**
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CORPUS = Path(__file__).resolve().parent / "corpus"
길 = CORPUS / "measured.json"


def 저장(원장: dict, 경로=None) -> Path:
    p = Path(경로) if 경로 else 길
    p.parent.mkdir(parents=True, exist_ok=True)
    원장 = dict(원장)
    원장["잰때"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p.write_text(json.dumps(원장, ensure_ascii=False), encoding="utf-8")
    return p


def 불러오기(경로=None) -> dict:
    p = Path(경로) if 경로 else 길
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"잰것": []}


def 쓸만한것(원장: dict) -> list:
    """**미검증이 아닌 것만.** 미검증은 통과가 아니라 '아직 아무도 안 봤다' 이다."""
    return [r for r in (원장.get("잰것") or []) if not r.get("미검증")]


def 찾기(원장: dict, 유형: str = "", 자산: str = "", 지평: int = 0,
        살아남은것만: bool = False) -> list:
    out = []
    for r in 쓸만한것(원장):
        if 유형 and r["유형"] != 유형:
            continue
        if 자산 and r["자산"] != 자산:
            continue
        if 지평 and r["지평"] != 지평:
            continue
        if 살아남은것만 and not r.get("살아남음"):
            continue
        out.append(r)
    return out


def 열쇠(r: dict) -> str:
    return f"{r['유형']}|{r['자산']}|D+{r['지평']}"


def 표(원장: dict) -> dict:
    return {열쇠(r): r for r in 쓸만한것(원장)}


def 요약(원장: dict) -> dict:
    잰것 = 원장.get("잰것") or []
    산것 = 쓸만한것(원장)
    return {
        "잰수": len(잰것), "쓸만한것": len(산것),
        "살아남음": sum(1 for r in 산것 if r.get("살아남음")),
        "시험수": (산것[0].get("시험수") if 산것 else 0),
        "미검증": len(잰것) - len(산것),
        "잰때": 원장.get("잰때", ""),
        "사건수": 원장.get("사건수", 0),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--보기", action="store_true")
    ap.add_argument("--찾기", default="")
    ap.add_argument("--자산", default="")
    ap.add_argument("--지평", type=int, default=0)
    ap.add_argument("--살아남은것만", action="store_true")
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)
    원장 = 불러오기(a.원장 or None)
    if not 원장.get("잰것"):
        print("원장이 비었다 -- python3 coin/event.py --재기", file=sys.stderr)
        return 3
    from coin import event as EV
    s = 요약(원장)
    if a.보기 or not a.찾기:
        print(f"잰것 {s['잰수']} · 쓸만한 것 {s['쓸만한것']} · BH 통과 {s['살아남음']} "
              f"· 미검증 {s['미검증']} · 시험수 {s['시험수']} · {s['잰때']}")
    for r in 찾기(원장, a.찾기, a.자산, a.지평, a.살아남은것만):
        print(EV.줄(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
