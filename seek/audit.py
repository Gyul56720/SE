r"""**원장에 있는 문제가 진짜 문제인가.** 호출 0회.

실측 2026-09-09: `--n 20` 한 번에 21개가 낳아지고 **21개가 다 받아들여졌다.**
100% 는 두 가지로 읽힌다 -- 프롬프트가 좋거나, **거르는 데가 없거나.** 그때는 그
둘을 가를 방법이 없었다. 확인해 보니 `def judge(x): return True` 도 `return False`
도 원장이 그대로 받고 있었다. 도는 것과 거르는 것은 다른 물음인데 도는 것만 봤다.

여기서 재는 것은 **판정기가 무엇을 거르는가** 다. 표본을 N개 뽑아 판정기에 먹인다.

    다 받는다     공허    아무것이나 답이면 찾을 것이 없다. 문제가 아니다
    하나도 안     막힘    어려운 것일 수도, 꼴이 안 맞는 것일 수도 있다 -- 갈라 말한다
    갈린다        문제    이것만 문제다. 적중률이 난이도다

**막힘을 자동으로 버리지 않는다.** P1 이 막힘이다 -- 무작위 정렬망 22,991개를 봐야
하나가 걸린다. 어려운 것과 틀린 것을 기계가 여기서 가를 수 없으므로 세어서 보여만
주고 버리는 것은 사람이 한다. 과잉 기각은 이 저장소가 싫어하는 쪽이다.

    python3 seek/audit.py                # 원장 전체
    python3 seek/audit.py --n 500        # 더 흔들어 본다
    python3 seek/audit.py P7             # 하나만
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import judge as J                                   # noqa: E402
from seek import problem as PR                                # noqa: E402

# 갈린 것으로 치는 최소 적중 수. 200개 중 1개도 갈린 것이다 -- 정렬망이 그렇다.
갈림 = 1


def grade(rec: dict, n: int = 200, seed: int = 1) -> dict:
    """한 문제를 흔들어 본다. **판정을 안 내리고 센 것만 돌려준다.**"""
    got = J.shake(rec, n=n, seed=seed)
    if not got.get("ok"):
        return {"등급": "안돎", "왜": got.get("왜", "모름"), "받음": 0, "본것": 0, "터짐": 0}
    받음, 본것, 터짐 = got["받음"], got["본것"], got.get("터짐", 0)
    산것 = 본것 - 터짐
    if 산것 <= 0:
        등급 = "터짐"
    elif 받음 >= 산것:
        등급 = "공허"
    elif 받음 < 갈림:
        등급 = "막힘"
    else:
        등급 = "문제"
    return {"등급": 등급, "받음": 받음, "본것": 본것, "터짐": 터짐,
            "적중": (받음 / 산것) if 산것 else 0.0}


def 베낌(led: dict, rec: dict) -> bool:
    """부모의 판정기를 **글자 그대로** 물려받았는가. 그러면 새 문제가 아니다."""
    par = PR.get(led, (rec.get("계보") or {}).get("부모") or "")
    if par is None:
        return False
    return str(par.get("판정") or "").strip() == str(rec.get("판정") or "").strip()


def show(led: dict, n: int, only: str = "") -> int:
    ps = [p for p in led.get("problems") or [] if not only or p["id"] == only]
    if not ps:
        print(f"{only or '원장'} 에 볼 것이 없다")
        return 1

    셈 = {}
    베낀것 = []
    print(f"{'id':<6} {'등급':<5} {'적중':>9}  {'터짐':>4}  물음")
    for rec in ps:
        g = grade(rec, n=n)
        셈[g["등급"]] = 셈.get(g["등급"], 0) + 1
        if 베낌(led, rec):
            베낀것.append(rec["id"])
        적중 = (f"{g['받음']}/{g['본것']}" if g["등급"] != "안돎" else "-")
        print(f"{rec['id']:<6} {g['등급']:<5} {적중:>9}  {g['터짐']:>4}  "
              f"{str(rec.get('물음'))[:52]}")
        if g["등급"] == "안돎":
            print(f"       └ {g['왜'][:100]}")

    print(f"\n문제 {len(ps)}개 -- " + " · ".join(f"{k} {v}개" for k, v in sorted(셈.items())))
    if 셈.get("공허"):
        print(f"**공허 {셈['공허']}개는 문제가 아니다** -- 뽑은 것을 다 받는다."
              " 지금은 원장이 안 받지만, 그 규칙이 생기기 전에 들어온 것이 남아 있다")
    if 셈.get("막힘"):
        print(f"막힘 {셈['막힘']}개는 **버리지 않는다** -- 어려운 것이 여기 섞여 있다"
              " (P1 이 그렇다: 22,991개를 봐야 하나가 걸린다)")
    if 베낀것:
        print(f"부모 판정기를 글자 그대로 쓴 것 {len(베낀것)}개: {', '.join(베낀것[:12])}"
              + (" ..." if len(베낀것) > 12 else ""))
        print("  같은 판정기면 물음만 바꿔 적은 것이다 -- 도약은커녕 새 문제도 아니다")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?", default="")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    return show(PR.load(a.path or None), a.n, a.pid)


if __name__ == "__main__":
    raise SystemExit(main())
