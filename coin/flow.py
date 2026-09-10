"""**돈이 어디로 움직이나 -- 포지션 · 온체인 · 심리.** 그리고 뉴스와 **같은 기계**에 태운다.

    python3 coin/flow.py --탐침                 어느 자료가 실제로 답하나
    python3 coin/flow.py --받기                 원장을 채운다
    python3 coin/flow.py --상태                 지금 각 계열이 자기 역사의 몇 % 자리인가
    python3 coin/flow.py --사건화               극단만 골라 **사건으로** 만든다

## 왜 따로 판정하지 않나

여기서 오는 것(자금조달률 · 미결제약정 · 대형 이체 · 공포탐욕)은 뉴스가 아니지만
**성질이 같다** -- 어떤 날 어떤 일이 있었다는 것. 그래서 새 논리를 안 만들고
`event.py` 에 그대로 태운다. 널도 · 겹침도 · 다중비교 보정도 · 관문도 뉴스와 똑같이
걸린다. **판정 논리를 하나만 두는 것**이 이 저장소가 `law` -> `brief` -> `jaso` 로
오면서 지킨 것이다.

극단을 고르는 자도 박지 않는다 -- `자기 역사의 상위/하위 몇 %` 이고, 그 몇 % 는
`scenario.py`·`regime.py` 와 같은 오분위다.

## 무엇을 '고래' 라고 부를 수 있나

    자금조달률       선물에서 롱이 숏에게 무는 값. **쏠림이 값으로 보이는 자리**
    미결제약정       열려 있는 계약 규모. 늘면 새 돈이 들어온 것
    대형 이체        임계 이상 온체인 이체 건수. **지갑을 실제로 본다**
    공포탐욕         심리 지수

앞의 둘은 '세력' 이라기보다 **레버리지 포지션**이고, 셋째만 지갑이다. 그래서 이름을
그렇게 붙였다. `regime.py` 의 거래량은 이것들이 없을 때의 **대용**이고, 이것들이
있으면 대용이 아니라 이쪽을 쓴다.

## 열쇠가 필요한 것은 열쇠를 요구한다

없으면 **그 계열이 없는 채로 돈다.** 다른 계열 값으로 메우지 않는다
(`brief/source.py` 와 같은 규약).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CORPUS = Path(__file__).resolve().parent / "corpus"
길 = CORPUS / "flow.json"


@dataclass
class 재료:
    이름: str
    url: str
    무엇: str
    열쇠: str = ""
    확인: str = ""          # 언제 실제로 도는 것을 봤나. 비면 **본 적 없다**
    쪽: str = ""            # 어느 자산에 붙나. 비면 시장 전체

    def 쓸수있나(self) -> tuple:
        if self.열쇠 and not os.environ.get(self.열쇠):
            return False, f"{self.열쇠} 가 없다"
        return True, ""


# **무료 · 열쇠 없는 것을 앞에 둔다.** 열쇠가 있어야 하는 것은 없으면 그냥 빠진다.
재료들 = [
    재료("자금조달률", "https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=1000",
         "선물에서 롱이 숏에게 무는 값 -- 쏠림이 값으로 보인다", 쪽="자산"),
    재료("미결제약정", "https://fapi.binance.com/futures/data/openInterestHist"
                       "?symbol={sym}&period=1d&limit=500",
         "열려 있는 계약 규모 -- 늘면 새 돈이 들어온 것", 쪽="자산"),
    재료("공포탐욕", "https://api.alternative.me/fng/?limit=0&format=json",
         "심리 지수 0~100"),
    재료("대형이체", "https://api.blockchair.com/bitcoin/transactions"
                     "?q=value(10000000000..)&s=time(desc)&limit=100",
         "**지갑을 실제로 본다** -- 100 BTC 이상 이체 건수"),
    재료("체인활동", "https://api.blockchain.info/charts/n-transactions"
                     "?timespan=5years&format=json",
         "온체인 거래 건수"),
    재료("이더대형", "https://api.etherscan.io/api?module=stats&action=ethsupply"
                     "&apikey={key}", "이더 쪽 -- 열쇠가 있어야 한다",
         열쇠="ETHERSCAN_API_KEY"),
]
표 = {r.이름: r for r in 재료들}

# 극단이 사건이 될 때의 이름. `tag.py` 의 유형과 같은 자리에 선다.
흐름유형 = ("자금조달과열", "자금조달냉각", "미결제급증", "미결제급감",
            "대형이체급증", "공포극단", "탐욕극단")


try:
    from dig import fetch as DIG
except Exception:                                                     # noqa: BLE001
    DIG = None


def _http(url: str, timeout: float = 20.0):
    """`dig` 가 있으면 그것으로 -- 헤더벌 돌려쓰기가 여기서도 필요하다
    (거래소·온체인 API 가 기본 User-Agent 를 막는 일이 있다)."""
    if DIG is not None:
        r = DIG.받기(url)
        if not r.됐나:
            raise RuntimeError(r.왜 or f"HTTP {r.코드}")
        return json.loads(r.몸통)
    req = urllib.request.Request(url, headers={"User-Agent": "SE-coin/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _날(ms) -> str:
    return datetime.fromtimestamp(float(ms) / 1000, timezone.utc).strftime("%Y-%m-%d")


def 받기(자산: str = "BTC", 부르기=_http) -> dict:
    """계열 이름 -> {날: 값}. 못 받은 것은 **빈 채로 둔다.**"""
    from coin import price as PR
    sym = PR.심볼찾기(자산)
    out, 왜 = {}, {}
    for r in 재료들:
        ok, 까닭 = r.쓸수있나()
        if not ok:
            왜[r.이름] = 까닭
            continue
        url = r.url.replace("{sym}", sym).replace(
            "{key}", os.environ.get(r.열쇠, "") if r.열쇠 else "")
        try:
            got = 부르기(url)
        except Exception as e:                                        # noqa: BLE001
            왜[r.이름] = f"{type(e).__name__}: {str(e)[:60]}"
            continue
        계 = {}
        try:
            if r.이름 == "자금조달률":
                for x in got:
                    계[_날(x["fundingTime"])] = float(x["fundingRate"])
            elif r.이름 == "미결제약정":
                for x in got:
                    계[_날(x["timestamp"])] = float(x["sumOpenInterest"])
            elif r.이름 == "공포탐욕":
                for x in got.get("data", []):
                    계[datetime.fromtimestamp(int(x["timestamp"]), timezone.utc)
                       .strftime("%Y-%m-%d")] = float(x["value"])
            elif r.이름 == "대형이체":
                for x in (got.get("data") or []):
                    d = str(x.get("time", ""))[:10]
                    계[d] = 계.get(d, 0) + 1
            elif r.이름 == "체인활동":
                for x in (got.get("values") or []):
                    계[datetime.fromtimestamp(int(x["x"]), timezone.utc)
                       .strftime("%Y-%m-%d")] = float(x["y"])
        except Exception as e:                                        # noqa: BLE001
            왜[r.이름] = f"꼴이 다르다: {type(e).__name__}: {str(e)[:50]}"
            continue
        if 계:
            out[r.이름] = 계
        else:
            왜[r.이름] = "답은 왔는데 줄이 0개"
    return {"자산": 자산, "계열": out, "못받음": 왜,
            "받은때": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def 저장(원장: dict, 경로=None) -> Path:
    p = Path(경로) if 경로 else 길
    p.parent.mkdir(parents=True, exist_ok=True)
    옛 = 불러오기(p)
    계 = 옛.get("계열") or {}
    for k, v in (원장.get("계열") or {}).items():
        계.setdefault(k, {}).update(v)              # **쌓는다.** 덮어쓰지 않는다
    원장 = dict(원장)
    원장["계열"] = 계
    p.write_text(json.dumps(원장, ensure_ascii=False), encoding="utf-8")
    return p


def 불러오기(경로=None) -> dict:
    p = Path(경로) if 경로 else 길
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"계열": {}}


def 상태(원장: dict = None) -> dict:
    """지금 각 계열이 **자기 역사의 몇 % 자리**인가. 문턱이 없다."""
    from coin.regime import _백분위
    계 = (원장 or 불러오기()).get("계열") or {}
    out = {}
    for 이름, 값들 in 계.items():
        날 = sorted(값들)
        if len(날) < 20:
            out[이름] = {"n": len(날), "백분위": float("nan"), "왜": "줄이 모자란다"}
            continue
        모음 = [값들[d] for d in 날]
        out[이름] = {"n": len(날), "날": 날[-1], "값": 값들[날[-1]],
                     "백분위": _백분위(값들[날[-1]], 모음)}
    return out


def 사건화(원장: dict = None, 자산: str = "BTC", 칸수: int = 5) -> list:
    """**극단인 날만 사건으로 만든다.** 이것이 `event.py` 로 그대로 들어간다.

    극단의 자는 오분위 -- 위 칸이면 '과열/급증', 아래 칸이면 '냉각/급감'.
    """
    from coin.regime import _백분위
    계 = (원장 or 불러오기()).get("계열") or {}
    위, 아래 = 1 - 1.0 / 칸수, 1.0 / 칸수
    이름표 = {"자금조달률": ("자금조달과열", "자금조달냉각"),
              "미결제약정": ("미결제급증", "미결제급감"),
              "대형이체": ("대형이체급증", ""),
              "공포탐욕": ("탐욕극단", "공포극단")}
    사건 = []
    for 이름, 값들 in 계.items():
        쌍 = 이름표.get(이름)
        if not 쌍:
            continue
        날 = sorted(값들)
        모음 = [값들[d] for d in 날]
        for d in 날:
            p = _백분위(값들[d], 모음)
            유형 = 쌍[0] if p >= 위 else (쌍[1] if p <= 아래 else "")
            if not 유형:
                continue
            사건.append({"유형": 유형, "자산": 자산,
                         "최초": f"{d}T00:00:00+00:00", "주류": f"{d}T00:00:00+00:00",
                         "주국": "XX", "나라들": ["XX"], "나라수": 1, "글수": 1,
                         "출처들": [이름], "지연": 0.0,
                         "본보기": f"{이름} {값들[d]:.6g} (자기 역사의 {p*100:.0f}% 자리)"})
    사건.sort(key=lambda e: e["최초"])
    return 사건


def 탐침() -> list:
    out = []
    for r in 재료들:
        ok, 왜 = r.쓸수있나()
        if not ok:
            out.append({"이름": r.이름, "산것": 0, "왜": 왜})
            continue
        from coin import price as PR
        url = r.url.replace("{sym}", PR.심볼찾기("BTC")).replace(
            "{key}", os.environ.get(r.열쇠, "") if r.열쇠 else "")
        try:
            got = _http(url, timeout=15.0)
            n = len(got) if isinstance(got, list) else len(
                got.get("data") or got.get("values") or [])
            out.append({"이름": r.이름, "산것": n, "왜": "" if n else "답은 왔는데 줄이 0개"})
        except Exception as e:                                        # noqa: BLE001
            out.append({"이름": r.이름, "산것": 0, "왜": f"{type(e).__name__}: {str(e)[:60]}"})
        time.sleep(0.2)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--탐침", action="store_true")
    ap.add_argument("--받기", action="store_true")
    ap.add_argument("--상태", action="store_true")
    ap.add_argument("--사건화", action="store_true")
    ap.add_argument("--자산", default="BTC")
    a = ap.parse_args(argv)
    if a.탐침:
        r = 탐침()
        for x in r:
            print(f"  {'OK  ' if x['산것'] else '못함'} {x['이름']:<12} {x['산것']:>5}줄  {x['왜']}")
        산것 = [x for x in r if x["산것"]]
        print(f"\n{len(산것)}/{len(r)} 이 답했다. "
              "**여기(에이전트 컨테이너)에서는 프록시가 다 막는다 -- VM 에서 돌려라**")
        return 0 if 산것 else 3
    if a.받기:
        원 = 받기(a.자산)
        p = 저장(원)
        for k, v in (원.get("계열") or {}).items():
            print(f"  OK   {k:<12} {len(v)}줄")
        for k, v in (원.get("못받음") or {}).items():
            print(f"  못함 {k:<12} {v}")
        print(f"  -> {p}")
        return 0 if 원.get("계열") else 3
    if a.상태:
        s = 상태()
        if not s:
            print("원장이 비었다 -- python3 coin/flow.py --받기", file=sys.stderr)
            return 3
        for k, v in s.items():
            if v["백분위"] == v["백분위"]:
                print(f"  {k:<12} {v['날']} {v['값']:>14.6g}  자기 역사의 "
                      f"{v['백분위']*100:5.1f}% 자리  (n={v['n']})")
            else:
                print(f"  {k:<12} 못 잼 -- {v.get('왜','')}")
        return 0
    if a.사건화:
        사건 = 사건화(자산=a.자산)
        셈 = {}
        for e in 사건:
            셈[e["유형"]] = 셈.get(e["유형"], 0) + 1
        for k, v in sorted(셈.items()):
            print(f"  {k:<14} {v}건")
        print(f"\n사건 {len(사건)}개 -- 이것이 뉴스 사건과 **같은 원장으로** 들어간다")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
