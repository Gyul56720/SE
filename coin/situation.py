"""**말 한 줄에서 '지금 무엇을 물었나' 를 뽑는다.** 그리고 트리거가 여기 있다.

    python3 coin/situation.py --글 "비트코인 시장 분석해줘"
    python3 coin/situation.py --글 "SOL -12.4% 왜 이래?"
    python3 coin/situation.py --트리거 "오늘 점심 뭐 먹지"        끝값 1 (안 걸림)

## 종목을 표에서 찾지 않는다

박아 둔 표로 종목을 풀면 표에 없는 종목이 오는 날 사용자는 "그런 거 없다" 를 본다.
그래서 세 걸음으로 푼다.

    1. 거래소 심볼 목록  price.심볼목록()  <- 거래소가 주는 것. 코드에 없다
    2. 사람 말 이름      corpus/aliases.json  <- 데이터 파일. 줄만 더하면 는다
    3. 대문자 토막       "SOL" "PEPE" 처럼 글에 그대로 있는 것

1번이 있으면 3번을 거기에 대조해서 **진짜 있는 종목만** 남긴다. 목록이 아직 없으면
대조를 못 하므로 통과시키되 `확인안됨` 으로 표시한다 -- 없는 것을 있다고 하지 않는다.

## 등락률을 같이 받는다

물음이 대개 "BTC -12% 왜 이래" 꼴로 온다. 그 수는 **판정에 안 쓴다** -- 사용자가 준
수를 원장의 수인 척 섞으면 `gate.py` C001 이 잡아야 할 것을 못 잡는다. 쓰는 데는
하나다: **지금이 그 유형의 과거 표본 중 어디쯤인지** 말해 주는 것(`어디쯤()`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import tag as TG                                            # noqa: E402

# 이 말이 있으면 이 파이프라인이 맡는다. **낱말이지 문장 꼴이 아니다** --
# "비트코인 시장 분석해줘" 도 "이더 왜 떨어져" 도 같은 문에 든다.
트리거말 = ("암호화폐", "가상화폐", "가상자산", "코인", "crypto", "cryptocurrency",
            "비트코인", "bitcoin", "btc", "이더리움", "ethereum", "알트코인",
            "김치프리미엄", "디지털자산")
_퍼센트 = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*(?:%|퍼센트|프로)")
_대문자 = re.compile(r"\b([A-Z]{2,10})\b")
_말머리 = {"AI", "API", "ETF", "SEC", "CEO", "FOMC", "CPI", "GDP", "USD", "KRW",
           "US", "EU", "UN", "IT", "PC", "TV", "OK", "URL", "SNS", "FBI", "IMF"}


def 걸리나(글: str) -> tuple:
    """(걸리나, 무엇에). **이 함수 하나가 트리거다** -- 봇도 스킬도 이것을 부른다."""
    낮 = (글 or "").lower()
    걸린 = [w for w in 트리거말 if (w in 낮 if w.isascii() else w in (글 or ""))]
    if 걸린:
        return True, 걸린
    # 종목 이름이 직접 왔을 때도 걸린다 ("SOL 왜 이래")
    자산 = 종목(글, 대조=True)
    return (bool(자산), [f"종목:{a}" for a in 자산]) if 자산 else (False, [])


def 종목(글: str, 대조: bool = True) -> list:
    """글에서 종목을 푼다. 세 걸음 -- 별명 · 거래소 목록 · 대문자 토막."""
    out, 본 = [], set()
    for a in TG.자산재기(글):                       # 사람 말 이름 (데이터 파일)
        if a not in 본:
            out.append(a)
            본.add(a)
    표 = {}
    if 대조:
        try:
            from coin import price as PR
            표 = PR.심볼목록()
        except Exception:                                             # noqa: BLE001
            표 = {}
    for m in _대문자.findall(글 or ""):
        if m in 본 or m in _말머리:
            continue
        if 표 and m not in 표:                      # 목록이 있으면 **진짜 있는 것만**
            continue
        out.append(m)
        본.add(m)
    return out


def 등락률(글: str) -> list:
    return [float(x) for x in _퍼센트.findall(글 or "")]


def 어디쯤(값: float, 수익들: list) -> dict:
    """사용자가 준 등락률이 그 유형 표본 중 어디쯤인가. **판정이 아니라 눈금이다.**"""
    쓸것 = sorted(v for v in (수익들 or []) if v is not None)
    if not 쓸것:
        return {"n": 0, "백분위": float("nan")}
    r = 값 / 100.0
    아래 = sum(1 for v in 쓸것 if v <= r)
    return {"n": len(쓸것), "백분위": 아래 / len(쓸것),
            "더큰것": sum(1 for v in 쓸것 if v > r)}


def 지금유형(사건들: list, 자산들=None, 최근: int = 40) -> list:
    """최근 사건에서 지금 걸려 있는 유형. **뉴스가 정하지 내가 정하지 않는다.**"""
    셈 = {}
    for e in (사건들 or [])[-최근:]:
        if 자산들 and e.get("자산") not in 자산들:
            continue
        셈[e.get("유형")] = 셈.get(e.get("유형"), 0) + e.get("글수", 1)
    return [k for k, _ in sorted(셈.items(), key=lambda kv: -kv[1]) if k]


def 읽기(글: str, 사건들: list = None) -> dict:
    걸림, 무엇 = 걸리나(글)
    자산 = 종목(글) or []
    표 = {}
    try:
        from coin import price as PR
        표 = PR.심볼목록()
    except Exception:                                                 # noqa: BLE001
        표 = {}
    return {
        "걸림": 걸림, "걸린말": 무엇,
        "자산": 자산, "확인안됨": (not 표),
        "등락률": 등락률(글),
        "지금유형": 지금유형(사건들 or [], 자산 or None),
        "물음": (글 or "").strip(),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--글", default="")
    ap.add_argument("--트리거", default="")
    ap.add_argument("--사건", default="")
    a = ap.parse_args(argv)
    if a.트리거:
        걸림, 무엇 = 걸리나(a.트리거)
        print(("걸림: " + ", ".join(무엇)) if 걸림 else "안 걸림")
        return 0 if 걸림 else 1
    if not a.글:
        ap.print_help()
        return 0
    사건p = Path(a.사건) if a.사건 else Path(__file__).resolve().parent / "corpus/events.json"
    사건 = json.loads(사건p.read_text(encoding="utf-8")).get("사건", []) if 사건p.exists() else []
    s = 읽기(a.글, 사건)
    print(f"  걸림      {s['걸림']}  ({', '.join(s['걸린말']) or '-'})")
    print(f"  자산      {', '.join(s['자산']) or '-'}"
          + ("   (거래소 목록이 없어 대조 못 함)" if s["확인안됨"] else ""))
    print(f"  등락률    {s['등락률'] or '-'}")
    print(f"  지금유형  {', '.join(s['지금유형']) or '- (뉴스 원장이 비었다)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
