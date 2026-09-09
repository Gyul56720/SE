"""**가격 원장.** 일봉만 받는다. 여기서 나가는 것은 되짚을 수 있는 수뿐이다.

    python3 coin/price.py --받기 BTC --부터 2017-08-17     # 원장을 채운다 (망 필요)
    python3 coin/price.py --보기 BTC                       # 무엇이 들었나
    python3 coin/price.py --수익 BTC --날 2021-05-19 --지평 7

## 진입일 규칙 -- 이 파일에서 제일 중요한 열다섯 줄

사건 연구가 조용히 틀리는 첫째 길이 **미리보기**다. 뉴스가 21일 08:00 UTC 에 났는데
21일 **시가**나 21일 **종가**를 아무 생각 없이 진입가로 쓰면, 그 값에는 이미 그
뉴스에 대한 반응이 들어 있다. 그러면 "뉴스 뒤 수익률" 이 아니라 "이미 오른 뒤의
되돌림" 을 재게 되고, **부호가 뒤집힌다.**

    바이낸스 일봉 `2021-05-21` = [05-21 00:00, 05-22 00:00) 이고 **종가는 05-22 00:00 에
    확정된다.** 그래서 05-21 08:00 뉴스의 첫 '살 수 있는 종가' 는 그 봉의 종가다.

여기에 하나를 더 건다. 마감 직전(`유예` 시간 안)에 온 뉴스는 **다음 날 종가**로 민다.
23:59 뉴스를 1분 뒤 종가로 잡는 것은 종이 위에서만 되는 일이다. 기본 2시간.

`유예` 는 잰 값과 함께 원장에 적힌다 -- 바꿔 재면 다른 수가 나오는 손잡이이므로,
어느 값으로 쟀는지가 안 남으면 그 수는 재현이 안 된다.

## 못 세면 안 센다

D0+h 봉이 없으면(원장 끝) 그 사건은 **버린다.** 마지막 값으로 메우면 최근 사건이
전부 수익률 0 으로 들어가 널 쪽으로 끌어내린다 -- 조용히 틀리는 둘째 길이다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# **`python3 coin/price.py` 로 직접 부를 때를 위한 것.** 파이썬은 sys.path[0] 에
# 스크립트가 든 폴더(coin/)를 넣지 현재 폴더를 안 넣는다. 그래서 `from coin import ...`
# 이 ModuleNotFoundError 로 죽는다 -- 실측 2026-09-09, VM 에서 가격 받기가 여기서 멈췄다.
sys.path.insert(0, str(ROOT))
CORPUS = Path(__file__).resolve().parent / "corpus"
BINANCE = "https://api.binance.com/api/v3/klines"
안내 = "https://api.binance.com/api/v3/exchangeInfo"
심볼길 = CORPUS / "symbols.json"
유예기본 = float(2.0)


def 심볼목록(다시: bool = False, 부르기=None) -> dict:
    """**종목표를 코드에 안 박는다.** 거래소가 주는 목록을 받아 두고 그것으로 푼다.

    박아 두면 새 종목이 나올 때마다 코드를 고쳐야 하고, 고치기 전에는 사용자가
    "그런 거 없다" 를 본다. 목록은 `corpus/symbols.json` 에 그대로 담긴다.
    """
    if 심볼길.exists() and not 다시:
        return json.loads(심볼길.read_text(encoding="utf-8"))
    got = (부르기 or _http)(안내)
    표 = {}
    for s in got.get("symbols", []):
        if s.get("status") != "TRADING":
            continue
        표.setdefault(s.get("baseAsset", ""), []).append(s.get("symbol", ""))
    심볼길.parent.mkdir(parents=True, exist_ok=True)
    심볼길.write_text(json.dumps(표, ensure_ascii=False), encoding="utf-8")
    return 표


def 심볼찾기(자산: str, 짝=("USDT", "USD", "BUSD", "USDC")) -> str:
    """자산 이름 -> 거래 심볼. 목록이 없으면 관례(<자산>USDT)로 되돌린다."""
    a = (자산 or "").upper()
    try:
        표 = 심볼목록()
    except Exception:                                                 # noqa: BLE001
        표 = {}
    후보 = 표.get(a) or []
    for q in 짝:
        if a + q in 후보:
            return a + q
    return 후보[0] if 후보 else a + 짝[0]


def 길(자산: str, 간격: str = "") -> Path:
    """눈금마다 따로 담는다 -- 분봉과 일봉을 한 파일에 섞으면 둘 다 못 쓴다."""
    꼬리 = f"_{간격}" if 간격 and 간격 != "1d" else ""
    return CORPUS / f"price_{자산}{꼬리}.json"


# ------------------------------------------------------------------ 받기
def _http(url: str, timeout: float = 20.0):
    """`dig` 가 있으면 그것으로 (헤더벌 · 곁문 · 오류에도 몸통 읽기)."""
    try:
        from dig import fetch as DIG
    except Exception:                                                 # noqa: BLE001
        DIG = None
    if DIG is not None:
        r = DIG.받기(url)
        if not r.됐나:
            raise RuntimeError(r.왜 or f"HTTP {r.코드}")
        return json.loads(r.몸통)
    req = urllib.request.Request(url, headers={"User-Agent": "SE-coin/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


COINBASE = "https://api.exchange.coinbase.com/products/{p}/candles"


def _코인베이스(자산: str, 부터: str, 까지: str, 부르기=_http) -> list:
    """**곁길.** 바이낸스가 막히는 데가 많다(클라우드 IP 를 나라 단위로 막는다).

    코인베이스는 한 번에 300봉까지라 잘라 가며 받는다. 꼴이 다르다:
    [[초, 저, 고, 시, 종, 양], ...] 이고 **최신이 먼저** 온다.
    """
    t0 = datetime.strptime(부터, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    t1 = (datetime.strptime(까지, "%Y-%m-%d").replace(tzinfo=timezone.utc)
          if 까지 else datetime.now(timezone.utc))
    본, a = {}, t0
    while a < t1:
        b = min(a + timedelta(days=290), t1)
        url = (COINBASE.format(p=f"{자산.upper()}-USD")
               + f"?granularity=86400&start={a.strftime('%Y-%m-%d')}"
               f"&end={b.strftime('%Y-%m-%d')}")
        try:
            묶음 = 부르기(url)
        except Exception:                                             # noqa: BLE001
            묶음 = []
        for k in (묶음 or []):
            if not isinstance(k, list) or len(k) < 6:
                continue
            날 = datetime.fromtimestamp(k[0], timezone.utc).strftime("%Y-%m-%d")
            본[날] = [날, float(k[3]), float(k[2]), float(k[1]), float(k[4]), float(k[5])]
        a = b
    return [본[d] for d in sorted(본)]


def 받기(자산: str, 부터: str = "2017-08-17", 까지: str = "", 부르기=_http,
        시간대=None, 간격: str = "") -> dict:
    """바이낸스 일봉. 막히면 **코인베이스로 되돌린다** -- 한 곳이 막혔다고 안 끝낸다.

    실측 2026-09-09 (VM): `--채우기` 가 "가격 원장이 없다: BTC" 로 끝났다. 바이낸스가
    그 기계에서 안 열린 것인데, 곁길이 없어서 **파이프라인 전체가 죽었다.**
    """
    from coin import clock as CK
    tz = CK.시간대(시간대)
    # **시간대가 걸리면 시간봉이다.** 거래소 일봉은 UTC 자정으로 잘려 있어서
    # 아무리 만져도 한국(또는 뉴욕) 하루가 안 나온다 -- 다시 묶어야 한다.
    # 받는 양이 24배라 기본은 UTC(0)다.
    # 눈금을 밖에서 줄 수 있다 -- 1m(실시간) · 1h(지금 자리) · 1d(추세).
    # 안 주면 시간대가 정한다: 시간대가 걸리면 시간봉으로 받아 다시 묶어야 하므로.
    간격 = 간격 or ("1h" if abs(tz) > 1e-9 else "1d")
    잘게 = 간격 != "1d"
    한번 = 1000
    sym = 심볼찾기(자산)
    t0 = int(datetime.strptime(부터, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    끝 = int((datetime.strptime(까지, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
             if 까지 else time.time() * 1000)
    봉, 시간봉 = [], []
    while t0 < 끝:
        try:
            묶음 = 부르기(f"{BINANCE}?symbol={sym}&interval={간격}"
                        f"&startTime={t0}&limit={한번}")
        except Exception as e:                                        # noqa: BLE001
            print(f"  바이낸스가 안 열린다({type(e).__name__}) -- 코인베이스로 간다",
                  file=sys.stderr)
            묶음 = []
        if not 묶음:
            break
        if 잘게:
            시간봉 += 묶음
        else:
            for k in 묶음:
                날 = datetime.fromtimestamp(k[0] / 1000, timezone.utc).strftime("%Y-%m-%d")
                봉.append([날, float(k[1]), float(k[2]), float(k[3]),
                          float(k[4]), float(k[5])])
        t0 = int(묶음[-1][0]) + (3_600_000 if 잘게 else 86_400_000)
        if len(묶음) < 한번:
            break
    if 시간봉:
        # **여기가 시세 시간보정이다.** 1d 로 다시 묶을 때만. 분·시간봉을 그대로
        # 쓰려는 것이면(눈금을 밖에서 준 것이면) 안 묶는다 -- 그 눈금이 목적이므로.
        if 간격 in ("1h", "1m", "5m", "15m") and 시간대 is not None and 간격 != "1d":
            봉 = [[datetime.fromtimestamp(k[0] / 1000, timezone.utc).isoformat(
                timespec="seconds"), float(k[1]), float(k[2]), float(k[3]),
                float(k[4]), float(k[5])] for k in 시간봉]
        else:
            봉 = CK.묶기(시간봉, tz)
        출처 = "binance"
    elif 봉:
        출처 = "binance"
    else:
        봉 = _코인베이스(자산, 부터, 까지, 부르기)
        출처 = "coinbase"
        if 잘게 and 봉:
            print("  코인베이스로 되돌렸다 -- 그쪽은 일봉이라 **시간보정이 안 걸렸다**",
                  file=sys.stderr)
    봉.sort(key=lambda r: r[0])
    본 = {}
    for r in 봉:                       # 같은 날이 두 번 오면 뒤엣것
        본[r[0]] = r
    봉 = [본[k] for k in sorted(본)]
    return {"자산": 자산.upper(), "출처": 출처, "심볼": sym, "시간대": tz,
            "간격": 간격,
            "받은때": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "봉": 봉}


def 저장(원장: dict, 경로: Path = None) -> Path:
    p = Path(경로) if 경로 else 길(원장["자산"], 원장.get("간격", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(원장, ensure_ascii=False), encoding="utf-8")
    return p


def 불러오기(자산: str = "BTC", 경로=None, 간격: str = "") -> dict:
    p = Path(경로) if 경로 else 길(자산, 간격)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 재기
class 계열:
    """종가 계열 하나. 날짜 문자열(YYYY-MM-DD)로만 말한다."""

    __slots__ = ("자산", "종가", "날들", "차례")

    def __init__(self, 원장: dict):
        self.자산 = 원장.get("자산", "?")
        self.종가 = {r[0]: r[4] for r in 원장.get("봉", [])}
        self.날들 = sorted(self.종가)
        self.차례 = {d: i for i, d in enumerate(self.날들)}

    def __len__(self):
        return len(self.날들)

    def 구간(self) -> tuple:
        return (self.날들[0], self.날들[-1]) if self.날들 else ("", "")

    def 진입일(self, 시각: str, 유예: float = 유예기본) -> str:
        """뉴스 시각(ISO, UTC) -> 첫 '살 수 있는 종가' 의 날.

        그날 봉의 종가는 **다음 날 00:00 UTC** 에 확정된다. 그때까지 `유예` 시간이
        안 남았으면 다음 날로 민다.
        """
        t = _때(시각)
        if t is None:
            return ""
        마감 = (t.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        남은 = (마감 - t).total_seconds() / 3600.0
        날 = t.strftime("%Y-%m-%d") if 남은 >= 유예 else (t + timedelta(days=1)).strftime("%Y-%m-%d")
        return self.있는날(날)

    def 있는날(self, 날: str) -> str:
        """그 날이 원장에 없으면(공백일) **다음으로 있는 날.** 없으면 빈 문자열."""
        if 날 in self.차례:
            return 날
        for d in self.날들:                       # 날들은 정렬돼 있다
            if d >= 날:
                return d
        return ""

    def 수익(self, D0: str, 지평: int):
        """close(D0+지평) / close(D0) - 1. 못 세면 None -- **메우지 않는다**."""
        i = self.차례.get(D0)
        if i is None or i + 지평 >= len(self.날들):
            return None
        a, b = self.종가[self.날들[i]], self.종가[self.날들[i + 지평]]
        if not a:
            return None
        return b / a - 1.0

    def 살수있는날들(self, 지평: int) -> list:
        """D0 로 쓸 수 있는 모든 날 -- **널 모형이 뽑는 자리**다."""
        return self.날들[: max(0, len(self.날들) - 지평)]


def _때(s: str):
    """**RSS 날짜는 `%z` 로 안 읽힌다.**

    실측 2026-09-09 (VM 탐침): 피드 스무 곳 남짓이 "답은 왔는데 글이 0개" 로 찍혔다.
    막힌 것도 빈 것도 아니었다 -- 날짜를 못 읽어서 **줄마다 조용히 버리고 있었다.**

        "Tue, 09 Sep 2026 12:00:00 GMT"   -> None    <- 버려졌다
        "Tue, 09 Sep 2026 12:00:00 +0000" -> 됐다

    `%z` 는 `+0000` 같은 숫자 오프셋만 받고 `GMT` · `EST` 같은 **이름**은 안 받는다.
    그런데 RFC-822 를 쓰는 피드의 상당수가 이름을 쓴다. 그래서 통과한 곳(coindesk ·
    theblock)과 0건인 곳(연준 · SEC 소송)이 갈렸던 것이고, **갈린 까닭이 내용이 아니라
    날짜 표기였다.**

    `email.utils.parsedate_to_datetime` 이 RFC-822 를 제대로 읽는다 -- 이름 시간대까지.
    """
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    t = None
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z",
                  "%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
            try:
                t = datetime.strptime(s, f)
                break
            except ValueError:
                continue
        else:
            try:
                t = parsedate_to_datetime(s.replace("+00:00", "GMT"))
            except (TypeError, ValueError):
                return None
    if t is None:
        return None
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--받기", default="")
    ap.add_argument("--부터", default="2017-08-17")
    ap.add_argument("--까지", default="")
    ap.add_argument("--시간대", default=None,
                    help="하루를 어디서 자르나. 9=한국 · -5=뉴욕. 걸면 시간봉으로 받는다")
    ap.add_argument("--간격", default="", help="1m · 1h · 1d. 안 주면 시간대가 정한다")
    ap.add_argument("--보기", default="")
    ap.add_argument("--수익", default="")
    ap.add_argument("--날", default="")
    ap.add_argument("--지평", type=int, default=7)
    a = ap.parse_args(argv)

    if a.받기:
        try:
            원장 = 받기(a.받기, a.부터, a.까지, 시간대=a.시간대, 간격=a.간격)
        except Exception as e:                                        # noqa: BLE001
            print(f"못 받았다: {type(e).__name__}: {e}", file=sys.stderr)
            return 3
        p = 저장(원장)
        c = 계열(원장)
        if not len(c):
            print(f"{a.받기}: **한 봉도 못 받았다** -- 바이낸스도 코인베이스도 "
                  "안 열린다. 망을 보라", file=sys.stderr)
            return 3
        print(f"{a.받기}: 봉 {len(c)}개 · {c.구간()[0]} ~ {c.구간()[1]} "
              f"· 출처 {원장['출처']} · 시간대 UTC{원장.get('시간대', 0):+g} -> {p}")
        return 0

    if a.보기:
        c = 계열(불러오기(a.보기))
        if not len(c):
            print(f"원장이 비었다 -- python3 coin/price.py --받기 {a.보기}", file=sys.stderr)
            return 3
        print(f"{a.보기}: 봉 {len(c)}개 · {c.구간()[0]} ~ {c.구간()[1]}")
        return 0

    if a.수익:
        c = 계열(불러오기(a.수익))
        D0 = c.있는날(a.날) if a.날 else ""
        r = c.수익(D0, a.지평) if D0 else None
        print(f"{a.수익} {D0} D+{a.지평}: " + ("못 셌다" if r is None else f"{r*100:+.2f}%"))
        return 0 if r is not None else 3

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
