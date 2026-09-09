"""**계속 돌면서 모은다.** 하루에 한 번 받으면 그 사이 것이 통째로 빠진다.

    python3 coin/watch.py --시간 24                24시간 돌고 멈춘다
    python3 coin/watch.py --시간 24 --틈 300       5분마다 (기본)
    python3 coin/watch.py --한바퀴                 한 바퀴만 (검사용)

## 왜 한 번 받는 것으로는 안 되나

RSS 는 **지금 걸려 있는 것**만 준다. 대개 최근 20~50건이고, 바쁜 매체는 그것이 두세
시간치다. 하루에 한 번 받으면 나머지 스물한 시간이 통째로 없는 것이 되고, **없는지
아무도 모른다** -- 원장은 그냥 좀 작을 뿐이니까.

그리고 이 파이프라인은 **최초 보도 시각**으로 D0 를 잡는다. 자주 볼수록 그 시각이
정확해진다.

## 본때 -- 이 파일이 원장에 더하는 칸

매체가 적은 시각과 **우리가 본 시각**은 다른 물음이다. 자주 돌면 본 시각이 참
발행 시각에 가까워지고, 그러면 `시각 > 본때` 인 줄(시간대 버그 · 소급 수정)이
드러난다. 그런 줄은 `news.뭉치기` 가 D0 후보에서 뺀다.

## 두 가지 틈

    얕은  RSS 스물몇 곳. 기본 5분. 가볍다
    깊은  GDELT(여러 나라 말) · 돈 흐름 · 가격. 기본 1시간. 무겁다

## 죽지 않는다

한 출처가 터져도 다음 바퀴로 간다. 바퀴마다 로그에 한 줄을 남기므로 **로그가 안
늘면 죽은 것**이다 -- `CLAUDE.md` 가 프로세스가 살아 있는지만 보지 말라고 한 그 자리다.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import news as NW                                           # noqa: E402
from coin import source as SRC                                        # noqa: E402

try:
    from dig import search as DIGS                                    # noqa: E402
except Exception:                                                     # noqa: BLE001
    DIGS = None

# 나라마다 무엇으로 찾을 것인가. **말이 나라를 정한다** -- 중국어로 물으면 중국 쪽
# 문에서 중국 쪽 주소가 나온다.
#
# ## `dig/search._집` 을 빌려 쓴다 -- 밑줄인데 왜
#
# 도메인을 견주려면 `html.duckduckgo.com` 과 `duckduckgo.com` 을 한집으로 봐야 하고,
# 그것을 제대로 하려면 `naver.co.kr` 이 `co.kr` 로 뭉개지지 않게 꼬리를 알아야 한다
# (`co` · `ne` · `or` · `go` · `ac`). `search.py` 가 그 표를 이미 갖고 있다.
#
# 여기에 다시 쓰면 두 벌이 되고, 두 벌은 **갈라진다** -- 그쪽이 꼬리를 하나 더 알게
# 되어도 이쪽은 모른 채로 남는다. 그래서 빌려 쓴다.
#
# 다만 밑줄 이름은 **말없이 사라질 수 있다.** 그러면 이 걸음이 런타임에 죽는데, 그것을
# 검사가 아니라 사용자가 보게 된다. 그래서 두 가지를 건다:
#   1. 없으면 `_집벌충` 으로 물러선다 (꼬리표 없이 뒤 두 마디만 -- 거칠지만 안 죽는다)
#   2. `tests/test_coin_loop.py` 가 `search._집` 이 있는지 붙든다.
#      이름이 바뀌면 **검사가 빨개진다** -- 사용자가 아니라.
찾을말 = {
    "US": "cryptocurrency regulation announcement",
    "EU": "MiCA crypto regulation announcement",
    "KR": "가상자산 규제 공지 거래소",
    "CN": "加密货币 监管 公告",
    "JP": "暗号資産 規制 発表",
}

CORPUS = Path(__file__).resolve().parent / "corpus"
멈춤 = {"이제": False}


def _멈춰(*_):
    멈춤["이제"] = True
    print("[멈춤 신호] 이 바퀴만 끝내고 멈춘다", flush=True)


def 한바퀴(깊게: bool = False, 원장길=None, 출처=None, 나라=None) -> dict:
    """한 바퀴. `깊게` 면 GDELT · 흐름까지.

    `출처` 를 주면 그것만 본다 -- **검사가 망을 안 타게 하는 자리다.** 곁문이 붙은
    뒤로 한 바퀴가 아흔네 곳 x (헤더벌 + 곁문 여섯) 이 되어서, 망이 막힌 데서
    검사를 돌리면 그 시간을 전부 기다린다. 검사는 망을 타면 안 된다.
    """
    잰때 = datetime.now(timezone.utc)
    출처 = 출처 if 출처 is not None else [s for s in SRC.쓸수있는것(나라=나라)
                                        if s.꼴 in ("rss", "html")]
    새 = NW.받기(출처)
    if 깊게:
        어제 = (잰때 - timedelta(days=1)).strftime("%Y-%m-%d")
        무거운 = [s for s in SRC.쓸수있는것(나라=나라) if s.꼴 in ("gdelt", "json")]
        새 += NW.받기(무거운, 부터=어제, 까지=잰때.strftime("%Y-%m-%d"))
    원장 = NW.합치기(NW.불러오기(원장길), 새)
    NW.저장(원장, 원장길)
    사건 = NW.뭉치기(원장["글"])
    NW.저장({"만든때": 잰때.isoformat(timespec="seconds"), "창시간": 12.0,
             "사건": 사건}, NW.사건길)
    나라 = {}
    for g in 새:
        나라[g["나라"]] = 나라.get(g["나라"], 0) + 1
    앞선 = sum(1 for g in 원장["글"] if g.get("앞선시각"))
    return {"받은것": len(새), "새로": 원장["더한것"], "원장": len(원장["글"]),
            "사건": len(사건), "나라": 나라, "앞선시각": 앞선, "깊게": 깊게}


def _집벌충(host: str) -> str:
    """`search._집` 이 없어질 때의 물러설 자리. **거칠다** -- 꼬리표를 안 본다."""
    ps = [x for x in (host or "").lower().split(".") if x]
    return ".".join(ps[-2:]) if len(ps) >= 2 else (host or "").lower()


def 집자():
    """주소 -> 집. `search._집` 이 있으면 그것, 없으면 벌충."""
    쪽 = getattr(DIGS, "_집", None) if DIGS is not None else None
    골 = 쪽 if callable(쪽) else _집벌충

    def _(u: str) -> str:
        try:
            host = (u or "").split("//", 1)[-1].split("/", 1)[0].split("?", 1)[0]
            return 골(host)
        except Exception:                                             # noqa: BLE001
            return ""
    return _


def 찾아보기(몇: int = 25) -> dict:
    """**선언 안 한 출처를 찾는다.** 표는 내가 적은 것뿐이라 내가 모르는 곳은 영영 없다.

    `dig/search.py` 가 검색 문들을 두드려 바깥 주소를 거둬 온다. 여기서는 그 주소의
    **집(도메인)만** 보고, 표에 없는 것을 골라 `corpus/후보.json` 에 쌓는다.

    **자동으로 표에 넣지 않는다.** 넣으면 아무 데서나 온 글이 사건 원장에 들어가고,
    그러면 D0 를 정하는 시각을 아무도 검사 안 한 곳이 정하게 된다. 사람이 보고
    `source.py` 에 줄을 더하는 것이 맞다 -- 표는 **선언**이어야 한다.

    그러니까 이것은 출처가 아니라 **빈틈 후보 목록**이다.
    """
    if DIGS is None:
        return {"왜": "dig/search 가 없다", "후보": {}}
    집내기 = 집자()
    아는집 = {집내기(x.url) for x in SRC.목록}
    아는집.discard("")
    후보 = {}
    for 나라, 말 in 찾을말.items():
        try:
            _, _, 거둔것 = DIGS.찾기(말, 몇=몇)
        except Exception as e:                                        # noqa: BLE001
            후보[나라] = {"왜": f"{type(e).__name__}: {str(e)[:60]}"}
            continue
        본 = {}
        for x in 거둔것:
            u = x.get("url") if isinstance(x, dict) else str(x)
            if not u:
                continue
            집 = 집내기(u)
            if 집 and 집 not in 아는집:
                본[집] = 본.get(집, 0) + 1
        후보[나라] = {"새집": sorted(본, key=lambda k: -본[k])[:12], "본것": len(거둔것)}
    길2 = CORPUS / "후보.json"
    길2.parent.mkdir(parents=True, exist_ok=True)
    길2.write_text(json.dumps(
        {"찾은때": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "후보": 후보}, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"후보": 후보, "길": str(길2)}


def 줄(r: dict) -> str:
    나라 = " ".join(f"{k}:{v}" for k, v in sorted(r["나라"].items())) or "-"
    return (f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
            f"{'깊은' if r['깊게'] else '얕은'} 바퀴 · 받은 것 {r['받은것']:>4} · "
            f"새로 {r['새로']:>3} · 원장 {r['원장']:>6} · 사건 {r['사건']:>5} · "
            f"나라 {나라}"
            + (f" · **시각이 미래인 줄 {r['앞선시각']}개**" if r["앞선시각"] else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--시간", type=float, default=24.0, help="몇 시간 돌 것인가")
    ap.add_argument("--틈", type=float, default=300.0, help="얕은 바퀴 사이 (초)")
    ap.add_argument("--깊은틈", type=float, default=3600.0, help="깊은 바퀴 사이 (초)")
    ap.add_argument("--한바퀴", action="store_true")
    ap.add_argument("--찾기", action="store_true",
                    help="선언 안 한 출처를 찾아 빈틈 후보로 적는다 (표에 안 넣는다)")
    ap.add_argument("--흐름", action="store_true", help="깊은 바퀴에서 돈 흐름도")
    ap.add_argument("--나라", default=None, help="US · US,XX 처럼")
    a = ap.parse_args(argv)

    signal.signal(signal.SIGTERM, _멈춰)
    signal.signal(signal.SIGINT, _멈춰)

    if a.찾기:
        got = 찾아보기()
        if got.get("왜"):
            print(got["왜"], file=sys.stderr)
            return 3
        for 나라, v in got["후보"].items():
            if v.get("왜"):
                print(f"  {나라}  못 찾음 -- {v['왜']}")
                continue
            print(f"  {나라}  거둔 주소 {v['본것']}개 · **표에 없는 집** "
                  + (", ".join(v["새집"]) or "없다"))
        print(f"\n-> {got['길']}\n**자동으로 표에 안 넣는다.** 사람이 보고 "
              "coin/source.py 에 줄을 더해라 -- 표는 선언이어야 한다")
        return 0

    if a.한바퀴:
        print(줄(한바퀴(깊게=True, 나라=a.나라)), flush=True)
        return 0

    끝날때 = time.time() + a.시간 * 3600
    다음깊은, 바퀴 = 0.0, 0
    print(f"[시작] {a.시간}시간 · 얕은 {a.틈:.0f}초 · 깊은 {a.깊은틈:.0f}초 · "
          f"출처 {len(SRC.쓸수있는것(나라=a.나라))}곳"
          + (f" ({a.나라} 만)" if a.나라 else ""), flush=True)
    while time.time() < 끝날때 and not 멈춤["이제"]:
        바퀴 += 1
        깊게 = time.time() >= 다음깊은
        try:
            r = 한바퀴(깊게, 나라=a.나라)
            print(줄(r), flush=True)
        except Exception as e:                                        # noqa: BLE001
            # **죽지 않는다.** 한 바퀴가 터져도 다음 바퀴로 간다
            print(f"[{바퀴}바퀴 터짐] {type(e).__name__}: {str(e)[:120]}", flush=True)
        if 깊게:
            다음깊은 = time.time() + a.깊은틈
            if a.흐름:
                try:
                    from coin import flow as FL
                    FL.저장(FL.받기("BTC"))
                    print("  흐름 원장 갱신", flush=True)
                except Exception as e:                                # noqa: BLE001
                    print(f"  흐름 못 받음: {type(e).__name__}: {str(e)[:80]}", flush=True)
        남은 = min(a.틈, max(0.0, 끝날때 - time.time()))
        if 남은 <= 0 or 멈춤["이제"]:
            break
        time.sleep(남은)
    print(f"[끝] {바퀴}바퀴 돌았다", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
