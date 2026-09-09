r"""**그 자가 계보를 재기는 하나.** 대조군. 호출 0회.

실측 2026-09-09: 100개를 훑고 나니 **도약 22개** 가 나왔다. 재작성 16 · 딴 문제 11 ·
모름 50. 99걸음 중 22%가 도약이면 반가운 수인데, **21개 중 21개가 다 받아들여졌던
것과 같은 모양**이다. 그때도 100%는 프롬프트가 좋다는 뜻이 아니라 거르는 데가
없다는 뜻이었다.

그래서 자를 검사한다. 방법은 하나뿐이다 -- **계보를 흔들어 보고 숫자가 변하는가.**

    진짜 짝    자식과 **제 부모**를 대고 잰다
    무작위 짝  자식과 **아무 상관 없는 남**을 대고 잰다 (같은 자, 같은 코드)

무작위 짝이 같은 비율로 도약을 내면, 그 자는 **연산자가 무엇을 했는지 재는 것이
아니라 두 문제의 꼴이 다른지만 재는 것**이다. 꼴은 아무 두 문제나 다르다.

    진짜 22% · 무작위 2%   -> 자가 계보를 잰다. 22개는 무언가를 뜻한다
    진짜 22% · 무작위 20%  -> **자가 계보를 안 본다.** 22개는 아무 뜻이 없다

어느 쪽인지는 돌려 봐야 안다. 이 파일은 그 숫자를 만들 뿐 무엇도 기각하지 않는다.

    python3 seek/control.py            # 진짜 짝과 무작위 짝을 나란히 센다
    python3 seek/control.py --씨 3     # 다른 흔들기로 다시
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402


def 자손(led: dict, pid: str) -> set:
    """pid 의 후손 전부. 무작위 짝이 계보를 다시 밟지 않게 뺀다."""
    아래 = {pid}
    for rec in led.get("problems") or []:                     # 부모가 항상 앞에 있다
        par = (rec.get("계보") or {}).get("부모")
        if par in 아래:
            아래.add(rec["id"])
    return 아래


def 조상(led: dict, pid: str) -> set:
    out, cur = set(), pid
    while cur and cur != "-":
        rec = PR.get(led, cur)
        if rec is None:
            break
        out.add(cur)
        cur = (rec.get("계보") or {}).get("부모")
    return out


def 셈(led: dict, 짝: str = "진짜", seed: int = 1) -> dict:
    """`짝` 이 '진짜' 면 계보대로, '무작위' 면 남을 부모로 대고 잰다."""
    rng = random.Random(seed)
    ps = led.get("problems") or []
    표 = {}
    걸음 = 0
    for kid in ps:
        par_id = (kid.get("계보") or {}).get("부모")
        if not par_id or par_id == "-":
            continue                                          # 씨앗은 견줄 데가 없다
        if 짝 == "진짜":
            par = PR.get(led, par_id)
        else:
            # **제 계보와 상관없는 것만 고른다.** 조상이나 후손을 뽑으면 그것도
            # 계보라서 대조가 안 된다.
            금 = 자손(led, kid["id"]) | 조상(led, kid["id"])
            남 = [p for p in ps if p["id"] not in 금]
            if not 남:
                continue
            par = rng.choice(남)
        if par is None:
            continue
        걸음 += 1
        r = RE.pair(par, kid)
        판 = r.get("판정", "모름")
        표[판] = 표.get(판, 0) + 1
    표["걸음"] = 걸음
    return 표


def 비율(표: dict, 이름: str) -> float:
    걸음 = 표.get("걸음", 0)
    return (표.get(이름, 0) / 걸음) if 걸음 else 0.0


def show(led: dict, seed: int = 1) -> int:
    진짜 = 셈(led, "진짜", seed)
    무작위 = 셈(led, "무작위", seed)
    칸 = ["도약", "재작성", "딴 문제", "모름"]
    print(f"{'':<10}" + "".join(f"{c:>10}" for c in 칸) + f"{'걸음':>8}")
    for 이름, 표 in (("진짜 짝", 진짜), ("무작위 짝", 무작위)):
        print(f"{이름:<10}" + "".join(f"{표.get(c, 0):>10}" for c in 칸)
              + f"{표.get('걸음', 0):>8}")
    r, f = 비율(진짜, "도약"), 비율(무작위, "도약")
    print(f"\n도약 비율 -- 진짜 {r:.1%} · 무작위 {f:.1%}")

    if 진짜.get("걸음", 0) == 0:
        print("잴 것이 없다 -- 계보가 있는 문제가 없다")
        return 1
    if f >= r * 0.5:
        print("**무작위 짝도 비슷하게 도약을 낸다.** 그러면 이 자는 연산자가 무엇을"
              " 했는지가 아니라\n두 문제의 꼴이 다른지만 재는 것이다 -- 꼴은 아무 두"
              " 문제나 다르다. 진짜 짝의 수를\n연산자의 공으로 읽으면 안 된다.")
    else:
        print("무작위 짝은 훨씬 덜 낸다 -- **이 자는 계보를 본다.**"
              " 진짜 짝의 도약은 우연이 아니다.")
    print("\n(이 파일은 아무것도 기각하지 않는다. 숫자를 만들 뿐이다)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--씨", dest="seed", type=int, default=1)
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    return show(PR.load(a.path or None), a.seed)


if __name__ == "__main__":
    raise SystemExit(main())
