r"""**도약인가.** 사람의 눈이 아니라 판정기 둘을 돌려서 가른다. 호출 0회.

어제 `mathdrift` 51개에 도약이 없다고 판정했는데, 그 판정을 제가 눈으로 했다.
자유 기호를 세고 구조를 잃었는지 봤을 뿐이고 "새 점이 생겼나" 는 못 쟀다.
여기서는 잰다.

    보존   부모의 답 x 를 옮겨서 자식 판정기에 넣으면 받는다
           -> 옛 해가 새 문제 안에서도 해다. 다시 쓴 것이 아니라 넓힌 것이다

    확장   자식의 답 y 를 **부모 판정기가 읽지도 못한다**
           -> 부모의 후보꼴로는 쓸 수가 없는 점이 생겼다

둘 다여야 도약이다. 보존만이면 재작성이고, 확장만이면 딴 문제로 간 것이다.
**둘 다 아니면 퇴화다** -- 옛 해를 잃고 새 점도 못 얻었으니 좁아진 것이다.

이게 어제 등급표의 4등급("옛 해가 살아남고 새 점이 생긴다")이고, 이제 사람이 아니라
자식 프로세스 둘이 판정한다.

**기각은 안 한다.** 도약이 아니어도 원장에 그대로 있다. 재서 보여 줄 뿐이다.

## 확장 판정의 한계 -- 부모가 후보꼴을 검사해야 잡힌다

"부모가 읽지도 못한다" 로 확장을 재므로, **부모 판정기가 입력 꼴을 안 보면 확장이
영영 안 잡힌다.** 실측: `def judge(x): return sum(x) == 12` 는 세 수든 네 수든 그냥
읽는다. 그러면 네 수로 넓힌 자식이 `재작성` 으로 나온다 -- 실제로는 넓어졌는데도.

그러니 이 자는 **놓치는 쪽으로 틀린다.** 도약이라고 하면 도약이 맞지만, 재작성이라고
한 것 중에 도약이 섞여 있을 수 있다. 씨앗 문제를 쓸 때 판정기가 후보꼴을 먼저 보게
쓰는 것이 그래서 중요하다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import judge as J                                   # noqa: E402
from seek import problem as PR                                # noqa: E402


def step(led: dict, pid: str) -> dict:
    """한 걸음(계보에 적힌 부모 -> 자식)이 도약인가."""
    kid = PR.get(led, pid)
    if kid is None:
        return {"ok": False, "왜": f"{pid} 가 원장에 없다"}
    par_id = (kid.get("계보") or {}).get("부모")
    par = PR.get(led, par_id) if par_id and par_id != "-" else None
    if par is None:
        return {"ok": False, "왜": f"{pid} 은 씨앗이다 -- 견줄 부모가 없다"}
    return pair(par, kid)


def pair(par: dict, kid: dict) -> dict:
    """**부모를 밖에서 준다.** 계보를 안 본다.

    이렇게 갈라 둔 이유는 대조군 때문이다 -- 계보를 무작위로 흔들어 같은 자를 대면
    이 판정이 **연산자를 재는지 꼴 차이만 재는지** 가 보인다. `seek/control.py`.
    """
    out = {"ok": True, "부모": par["id"], "자식": kid["id"],
           "보존": None, "확장": None, "왜": []}

    # ── 보존 ──────────────────────────────────────────────────────────
    px = par.get("답")
    if px is None:
        out["왜"].append("부모의 답이 원장에 없다 -- 먼저 풀어야 보존을 잰다")
    else:
        emb = J.embed(kid, px)
        if not emb.get("ok"):
            out["보존"] = False
            out["왜"].append(f"옮김이 안 돈다: {emb.get('왜')}")
        else:
            got = J.judge(kid, emb["후보"])
            out["보존"] = bool(got.get("받음"))
            out["옮긴것"] = emb["후보"]
            if not out["보존"]:
                out["왜"].append("옮긴 부모의 답을 자식이 안 받는다 -- 옛 해가 안 살아남았다")

    # ── 확장 ──────────────────────────────────────────────────────────
    ky = kid.get("답")
    if ky is None:
        out["왜"].append("자식의 답이 원장에 없다 -- 먼저 풀어야 확장을 잰다")
    else:
        got = J.cross(par, ky)
        if not got.get("ok"):
            out["확장"] = None
            out["왜"].append(f"부모 판정기를 못 돌렸다: {got.get('왜')}")
        else:
            # 못 읽으면 부모의 후보꼴 밖이다. 읽고 안 받으면 부모가 답이 아니라고 한 것뿐이다.
            out["확장"] = not got.get("읽음", True)
            out["부모가읽나"] = got.get("읽음")
            out["부모가받나"] = got.get("받음")
            if not out["확장"]:
                out["왜"].append("부모가 자식의 답을 읽는다 -- 부모의 후보꼴 안이다")
            else:
                out["왜"].append(f"부모가 못 읽는다: {got.get('왜', '')}")

    # **넷째 칸이 있었다.** 보존도 확장도 False -- 옛 해가 안 살아남았고 새 점도
    # 아니다. 좁아진 것이지 넓어진 것이 아니므로 **퇴화**다.
    #
    # 실측 2026-09-09, 100개: 모름 50개 중 8개가 이것이었다. `모름` 으로 떨어져
    # "아직 못 잰 것" 과 한 칸에 섞여 있었는데, 이쪽은 **다 잰 것**이다 -- 답이
    # 양쪽에 다 있고 두 검사가 다 돌았고 둘 다 아니라고 답했다. 섞어 두면 "더 풀면
    # 판정이 서겠지" 로 읽히는데 풀 것이 없다.
    #
    # 이 칸을 세는 것이 이 파이프라인의 목표와 곧바로 닿아 있다 -- 목표가
    # "퇴화가 아니라 도약" 이므로, 퇴화를 안 세면 목표의 반쪽을 안 보는 것이다.
    out["판정"] = ("도약" if (out["보존"] and out["확장"]) else
                   "재작성" if out["보존"] and out["확장"] is False else
                   "딴 문제" if out["확장"] and out["보존"] is False else
                   "퇴화" if out["보존"] is False and out["확장"] is False else
                   "모름")
    return out


def show(led: dict, pid: str) -> int:
    r = step(led, pid)
    if not r.get("ok"):
        print(r.get("왜"))
        return 1
    kid = PR.get(led, pid)
    par = PR.get(led, r["부모"])
    print(f"{r['부모']} -> {r['자식']}  ({(kid.get('계보') or {}).get('연산자')})\n")
    print(f"  부모: {par.get('물음')}")
    print(f"  자식: {kid.get('물음')}\n")
    mark = {True: "예", False: "아니오", None: "모름"}
    print(f"  보존  {mark[r['보존']]:<5} 부모의 답을 옮겨서 자식 판정기에 넣으면 받는가")
    if r.get("옮긴것") is not None:
        print(f"          {r['옮긴것']}")
    print(f"  확장  {mark[r['확장']]:<5} 자식의 답을 부모 판정기가 **읽지도 못하는가**")
    if r.get("부모가읽나") is not None:
        print(f"          부모가 읽나: {r['부모가읽나']} · 받나: {r['부모가받나']}")
    for w in r["왜"]:
        print(f"          {w}")
    print(f"\n  **{r['판정']}**")
    말 = {"도약": "옛 해가 살아남았고, 부모의 후보꼴로는 쓸 수 없는 점이 생겼다.",
          "재작성": "옛 해는 살아남았는데 새 점이 없다 -- 넓힌 것이 아니라 다시 쓴 것이다.",
          "딴 문제": "새 점은 생겼는데 옛 해를 잃었다 -- 넓힌 것이 아니라 옮겨간 것이다.",
          "퇴화": "옛 해를 잃고 새 점도 못 얻었다 -- **좁아졌다.** 다 잰 것이지"
                  " 못 잰 것이 아니다.",
          "모름": "아직 못 잰다 -- 답이 양쪽에 다 있어야 잰다."}
    if r["판정"] in 말:
        print(f"  {말[r['판정']]}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?", default="")
    a = ap.parse_args(argv)
    led = PR.load()
    if a.pid:
        return show(led, a.pid)
    for p in led.get("problems", []):
        if (p.get("계보") or {}).get("부모") not in ("-", None):
            show(led, p["id"])
            print("-" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
