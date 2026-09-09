r"""**원장을 통째로 풀어 본다.** 호출 0회. 중간에 끊겨도 이어서 돈다.

실측 2026-09-09, 100개 감사: 공허 9 · **막힘 52** · 문제 39.

막힘 52개가 이 파이프라인에서 제일 큰 덩어리인데, 그 안에 두 가지가 섞여 있다.

    어렵다   해가 있는데 무작위 200개로는 안 걸린다. P1 이 그렇다(22,991개째)
    모른다   표본이 판정기에 영영 못 닿는 꼴일 수도 있다

**감사는 그 둘을 못 가른다.** 200개를 흔들어 0개인 것과 20만 개를 봐서 0개인 것은
같은 말이 아닌데 같은 칸에 들어간다. 여기가 그 칸을 여는 자리다 -- 실제로 찾아
본다. 찾으면 **해가 있다는 것이 증명된다**(찾은 것이 증거다). 못 찾으면 여전히
모르지만, 몇 개를 봤는지가 원장에 남는다.

    푼다      해가 있다. 어려웠을 뿐 -- **답이 원장에 적힌다**
    못 푼다   아직 모른다. 본 수를 적는다. **없다는 뜻이 아니다**

답이 원장에 쌓여야 `reach.py` 가 도약을 잴 수 있다 -- 보존은 부모의 답을, 확장은
자식의 답을 필요로 한다. 지금 100개 중 답이 있는 것은 둘뿐이라 도약을 잴 데가 없다.

    python3 seek/sweep.py                    # 안 푼 것을 다 푼다
    python3 seek/sweep.py --초 10 --tries 50000
    python3 seek/sweep.py --만 막힘          # 막힘만
    python3 seek/sweep.py --다시             # 이미 푼 것도 다시
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import audit as AU                                  # noqa: E402
from seek import judge as J                                   # noqa: E402
from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402
from seek import solve as SO                                  # noqa: E402


def one(rec: dict, tries: int, seconds: float, seed: int = 0) -> dict:
    """한 문제. **답을 부모 프로세스에서 다시 검산한다** -- 자식 말을 안 믿는다."""
    got = SO.search(rec, tries=tries, seed=seed, seconds=seconds)
    if not got.get("ok"):
        return {"됨": False, "왜": got.get("왜", "모름"), "본것": 0}
    답 = got.get("답")
    if 답 is None:
        return {"됨": False, "왜": "못 찾았다", "본것": got.get("본것", 0)}
    back = J.judge(rec, 답)
    if not back.get("받음"):
        # 자식이 받았다는 것을 부모가 안 받으면 **답이 아니라 버그다.** 적어 둔다.
        return {"됨": False, "왜": "자식은 받았는데 부모가 안 받는다", "본것": got.get("본것", 0)}
    return {"됨": True, "답": 답, "본것": got.get("본것", 0)}


def sweep(led: dict, path=None, tries: int = 200000, seconds: float = 30.0,
          만: str = "", 다시: bool = False, n: int = 0, log=print) -> dict:
    ps = led.get("problems") or []
    셈 = {"품": 0, "못품": 0, "건너뜀": 0}
    t0 = time.time()
    본 = 0
    for rec in ps:
        if n and 본 >= n:
            break
        등급 = AU.grade(rec, n=60)["등급"]
        rec["등급"] = 등급                                     # 원장에 남긴다
        if 등급 == "공허":
            # **찾아 봐야 뜻이 없다.** 아무것이나 답이면 찾은 것이 아무 말도 안 한다.
            셈["건너뜀"] += 1
            log(f"  {rec['id']:<6} 건너뜀  공허 -- 아무것이나 답이라 찾을 것이 없다")
            continue
        if 만 and 등급 != 만:
            셈["건너뜀"] += 1
            continue
        if rec.get("답") is not None and not 다시:
            셈["건너뜀"] += 1
            continue
        본 += 1
        got = one(rec, tries=tries, seconds=seconds)
        if got["됨"]:
            rec["답"] = got["답"]
            rec["푼것"] = {"본것": got["본것"]}
            셈["품"] += 1
            log(f"  {rec['id']:<6} **찾았다** ({got['본것']:,}개 봤다) "
                f"-- {등급} 이었지만 해가 있다")
        else:
            rec["못푼것"] = {"본것": got["본것"], "왜": got["왜"]}
            셈["못품"] += 1
            log(f"  {rec['id']:<6} 못 찾았다 ({got['본것']:,}개) {got['왜']}"
                "  <- 없다는 뜻이 아니다")
        PR.save(led, path)                                    # 끊겨도 남게
    셈["초"] = round(time.time() - t0, 1)
    return 셈


def 도약(led: dict, log=print) -> dict:
    """푼 것이 쌓였으니 이제 잰다. **호출 0회.**"""
    셈 = {}
    잰것 = []
    for rec in led.get("problems") or []:
        r = RE.step(led, rec["id"])
        if not r.get("ok"):
            continue
        판 = r.get("판정", "모름")
        셈[판] = 셈.get(판, 0) + 1
        if 판 in ("도약", "딴 문제"):
            잰것.append((판, rec["id"], r["부모"], str(rec.get("물음"))[:50]))
    if 잰것:
        log("")
        for 판, kid, par, 물음 in 잰것:
            log(f"  {판:<5} {par} -> {kid}  {물음}")
    return 셈


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=200000)
    ap.add_argument("--초", dest="seconds", type=float, default=30.0)
    ap.add_argument("--만", dest="only", default="",
                    help="등급 하나만 (공허/막힘/문제/터짐/안돎)")
    ap.add_argument("--다시", dest="again", action="store_true")
    ap.add_argument("--n", type=int, default=0, help="이만큼만 풀고 멈춘다")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    led = PR.load(a.path or None)

    print(f"문제 {len(led.get('problems') or [])}개 -- 안 푼 것을 푼다"
          f" (한 문제당 최대 {a.seconds:.0f}초 · {a.tries:,}개)\n")
    셈 = sweep(led, a.path or None, tries=a.tries, seconds=a.seconds,
               만=a.only, 다시=a.again, n=a.n)
    PR.save(led, a.path or None)
    print(f"\n푼 것 {셈['품']}개 · 못 푼 것 {셈['못품']}개 · 건너뛴 것 {셈['건너뜀']}개"
          f" · {셈['초']}초")
    if 셈["품"]:
        print(f"**막힘 중 {셈['품']}개는 해가 있었다** -- 어려웠던 것이지 틀린 것이 아니다")
    if 셈["못품"]:
        print(f"못 푼 {셈['못품']}개는 **없다는 뜻이 아니다** -- 이 찾는 법으로 못 찾은 것이다")

    print("\n== 이제 도약을 잰다 ==")
    j = 도약(led)
    print("\n" + " · ".join(f"{k} {v}개" for k, v in sorted(j.items())) if j else "잰 것이 없다")
    if not j.get("도약"):
        print("도약 0개 -- 보존과 확장이 **둘 다** 서야 도약이다."
              " 한쪽만이면 재작성이거나 딴 문제다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
