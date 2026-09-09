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

멈춤 = {"이제": False}


def _멈춰(*_):
    멈춤["이제"] = True
    print("[멈춤 신호] 이 바퀴만 끝내고 멈춘다", flush=True)


def 한바퀴(깊게: bool = False, 원장길=None) -> dict:
    """RSS 한 바퀴. `깊게` 면 GDELT · 흐름까지."""
    잰때 = datetime.now(timezone.utc)
    출처 = [s for s in SRC.쓸수있는것() if s.꼴 == "rss"]
    새 = NW.받기(출처)
    if 깊게:
        어제 = (잰때 - timedelta(days=1)).strftime("%Y-%m-%d")
        새 += NW.받기([s for s in SRC.쓸수있는것() if s.꼴 in ("gdelt", "json")],
                     부터=어제, 까지=잰때.strftime("%Y-%m-%d"))
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
    ap.add_argument("--흐름", action="store_true", help="깊은 바퀴에서 돈 흐름도")
    a = ap.parse_args(argv)

    signal.signal(signal.SIGTERM, _멈춰)
    signal.signal(signal.SIGINT, _멈춰)

    if a.한바퀴:
        print(줄(한바퀴(깊게=True)), flush=True)
        return 0

    끝날때 = time.time() + a.시간 * 3600
    다음깊은, 바퀴 = 0.0, 0
    print(f"[시작] {a.시간}시간 · 얕은 {a.틈:.0f}초 · 깊은 {a.깊은틈:.0f}초 · "
          f"출처 {len(SRC.쓸수있는것())}곳", flush=True)
    while time.time() < 끝날때 and not 멈춤["이제"]:
        바퀴 += 1
        깊게 = time.time() >= 다음깊은
        try:
            r = 한바퀴(깊게)
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
