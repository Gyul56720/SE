r"""**어느 연산자가 도약을 냈나.** 호출 0회.

실측 2026-09-09, 100개: 도약 22 · 재작성 16 · 딴 문제 11 · **모름 50**.
대조군(`control.py`)에서 진짜 22.2% 대 무작위 1~2% 가 씨 셋에서 다 유지됐다 --
그 자는 꼴 차이가 아니라 계보를 본다.

그러면 다음 물음은 하나다. **12개 연산자 중 어느 것이 그 22개를 냈나.**
고르게 나왔으면 연산자 표는 아무 말도 안 하는 것이고, 몇 개에 몰렸으면 그것이
`spread.py` 가 더 자주 걸어야 할 것이다.

## 연산자별로도 대조군을 댄다

"이산화가 도약을 많이 낸다" 는 "이산화가 후보꼴을 많이 바꾼다" 일 수 있다. 그래서
연산자마다 무작위 짝의 도약률을 나란히 놓는다. **둘이 같이 높으면 그 연산자의 공이
아니라 꼴 바꾸기의 그림자다.**

## 모름 50개도 갈라 센다

모름은 판정이 아니라 **아직 못 잰 것**이다. 어느 쪽 답이 없어서인지에 따라 할 일이
다르다 -- 부모가 없으면 부모를 풀어야 하고, 둘 다 없으면 그 가지 전체가 아직 비었다.

    python3 seek/tally.py            # 연산자별 · 깊이별 · 모름 가르기
    python3 seek/tally.py --씨 3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import control as CT                                # noqa: E402
from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402

칸 = ["도약", "재작성", "딴 문제", "퇴화", "모름"]

# 잰 것이 이보다 적으면 비율을 읽지 않는다. 1/1 도 100% 다.
얼마나적나 = 5


def 걸음들(led: dict) -> list:
    """(연산자, 깊이, 판정, 왜) -- 계보가 있는 것만."""
    out = []
    for kid in led.get("problems") or []:
        par_id = (kid.get("계보") or {}).get("부모")
        if not par_id or par_id == "-":
            continue
        par = PR.get(led, par_id)
        if par is None:
            continue
        r = RE.pair(par, kid)
        out.append(((kid.get("계보") or {}).get("연산자") or "?",
                    kid.get("깊이", 0), r.get("판정", "모름"), r.get("왜") or []))
    return out


def 무작위_연산자별(led: dict, seed: int) -> dict:
    """연산자 -> (도약수, 걸음수). 부모만 흔든다 -- 연산자 표는 자식에 붙어 있다."""
    import random
    rng = random.Random(seed)
    ps = led.get("problems") or []
    표 = {}
    for kid in ps:
        par_id = (kid.get("계보") or {}).get("부모")
        if not par_id or par_id == "-":
            continue
        금 = CT.자손(led, kid["id"]) | CT.조상(led, kid["id"])
        남 = [p for p in ps if p["id"] not in 금]
        if not 남:
            continue
        op = (kid.get("계보") or {}).get("연산자") or "?"
        도, 걸 = 표.get(op, (0, 0))
        표[op] = (도 + (1 if RE.pair(rng.choice(남), kid).get("판정") == "도약" else 0),
                  걸 + 1)
    return 표


def show(led: dict, seed: int = 1) -> int:
    걸 = 걸음들(led)
    if not 걸:
        print("계보가 있는 문제가 없다 -- 잴 것이 없다")
        return 1
    무 = 무작위_연산자별(led, seed)

    표 = {}
    for op, _d, 판, _w in 걸:
        r = 표.setdefault(op, {c: 0 for c in 칸})
        r[판] = r.get(판, 0) + 1

    print(f"{'연산자':<12}{'걸음':>5}" + "".join(f"{c:>8}" for c in 칸)
          + f"{'도약률':>8}{'무작위':>8}")
    줄 = []
    for op, r in 표.items():
        n = sum(r.values())
        잰것 = n - r["모름"]
        율 = r["도약"] / 잰것 if 잰것 else 0.0
        도, 걸수 = 무.get(op, (0, 0))
        줄.append((율, r["도약"], op, n, r, 도 / 걸수 if 걸수 else 0.0))
    for 율, _도, op, n, r, 무율 in sorted(줄, reverse=True):
        # **분모가 몇인지 안 보이면 100% 를 잘못 읽는다.** 1/1 도 100% 다.
        잰것 = n - r["모름"]
        꼬리 = "  <- 잰 것이 적어 못 읽는다" if 0 < 잰것 < 얼마나적나 else ""
        print(f"{op:<12}{n:>5}" + "".join(f"{r[c]:>8}" for c in 칸)
              + f"{율:>7.0%}{무율:>8.0%}{꼬리}")

    print("\n  도약률은 **잰 것 중에서**다 (모름을 뺀 분모). 모름은 판정이 아니라"
          " 아직 못 잰 것이다.")
    if all(n - r["모름"] == 0 for _율, _도, _op, n, r, _무 in 줄):
        # 전부 모름이면 0% 가 죽 늘어서는데, 그것은 "어느 연산자도 도약을 못 냈다"
        # 가 아니라 "아직 아무것도 안 쟀다" 다. 위의 0% 들을 그렇게 읽지 않게 적는다.
        print("  **잰 것이 하나도 없다** -- 위의 0%는 연산자의 성적이 아니다."
              " `python3 seek/sweep.py` 를 먼저 돌려라.")
    수상 = [op for 율, _d, op, _n, _r, 무율 in 줄 if 율 > 0 and 무율 >= 율 * 0.5]
    if 수상:
        print(f"  **무작위 짝도 비슷하게 내는 연산자: {', '.join(수상)}** -- 그 도약은"
              " 연산자의 공이 아니라 꼴 바꾸기의 그림자일 수 있다.")

    print(f"\n{'깊이':<12}{'걸음':>5}" + "".join(f"{c:>8}" for c in 칸))
    깊 = {}
    for _op, d, 판, _w in 걸:
        r = 깊.setdefault(d, {c: 0 for c in 칸})
        r[판] = r.get(판, 0) + 1
    for d in sorted(깊):
        r = 깊[d]
        print(f"{d:<12}{sum(r.values()):>5}" + "".join(f"{r[c]:>8}" for c in 칸))

    모름 = [w for _op, _d, 판, w in 걸 if 판 == "모름"]
    if 모름:
        for 이름, n, 말 in 모름_가르기(모름):
            print(f"\n모름 {len(모름)}개" if 이름 == "머리" else f"  {이름:<12}{n:>4}  {말}")
    return 0


def 모름_가르기(모름: list) -> list:
    """**빠짐없이 가른다.** 세 칸이면 답이 안 맞는다.

    실측 2026-09-09, 100개: 모름 50개인데 부모만 7 · 자식만 27 · 둘 다 8 = **42** 였다.
    8개가 어느 칸에도 안 들어갔다. 재현해 보니 **보존도 확장도 False** 인 것들이었다 --
    답이 양쪽에 다 있고 두 검사가 다 돌았는데 둘 다 아니라고 답한 것. 못 잰 것이
    아니라 **다 잰 것**이고, 그것이 곧 퇴화다. 이제 `reach` 가 그 이름으로 판정하므로
    여기 모름으로 안 온다.

    남은 두 갈래는 여전히 여기 온다. 옮김이 터지거나 부모 판정기가 안 서면 확장이
    None 이 되어 어느 칸도 아니게 되는데, 그건 **덜 푼 것이 아니라 고장난 것**이다 --
    sweep 을 아무리 돌려도 안 줄어든다. 같은 칸에 섞어 두면 "더 풀면 되겠지" 로
    읽힌다.

    합이 총계와 안 맞으면 그 자체가 알림이다. 마지막 줄에서 확인한다.
    """
    부, 자, 둘, 고장, 나머지 = 0, 0, 0, 0, 0
    for w in 모름:
        t = " ".join(w)
        없부, 없자 = "부모의 답이 원장에 없다" in t, "자식의 답이 원장에 없다" in t
        if 없부 and 없자:
            둘 += 1
        elif 없부:
            부 += 1
        elif 없자:
            자 += 1
        elif "옮김이 안 돈다" in t or "부모 판정기를 못 돌렸다" in t:
            고장 += 1
        else:
            나머지 += 1
    out = [("머리", len(모름), "")]
    out.append(("부모만 없음", 부, "부모를 먼저 풀어야 보존을 잰다"))
    out.append(("자식만 없음", 자, "자식을 풀어야 확장을 잰다"))
    out.append(("둘 다 없음", 둘, "이 가지는 아직 통째로 비었다"))
    out.append(("고장", 고장,
                "**답은 양쪽에 다 있다.** 옮김이나 판정기가 안 돈다 --"
                " 풀어도 안 줄어든다"))
    # **여기가 알림이다.** 앞의 네 칸이 모자라면 남은 것이 여기로 떨어진다.
    #
    # 처음에는 "합이 총계와 같은가" 를 알림으로 뒀는데, 이 칸이 남은 것을 다 받으므로
    # 합은 **영영 맞는다** -- 안 맞는 가지가 죽은 코드였고, 사보타주를 대도 red 가
    # 안 났다(실측: exit=0). 안 틀리는 검사는 검사가 아니다. 그래서 알림을 살아 있는
    # 칸으로 옮긴다.
    out.append(("까닭 모름", 나머지,
                "0이어야 한다" if not 나머지
                else "**이 분류가 모자라다** -- 여기 있는 것은 아무 말도 못 한다"))
    out.append(("합", 부 + 자 + 둘 + 고장 + 나머지, f"총계 {len(모름)}개"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--씨", dest="seed", type=int, default=1)
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    return show(PR.load(a.path or None), a.seed)


if __name__ == "__main__":
    raise SystemExit(main())
