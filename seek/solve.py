r"""**답을 찾는다.** 판정기가 있으니 찾는 것은 그냥 탐색이다 -- 호출 0회.

여기가 이 설계의 요점이다. `mathdrift` 는 식을 낳았고 그 식으로 무엇을 할지가
없었다. 여기서는 문제마다 판정기가 있으므로 **문제를 원장에 올린 순간 풀 수 있다.**

찾는 법은 문제마다 다를 수 있어서 여기 있는 것은 제일 멍청한 것이다: 표본을 뽑아
판정에 걸어 본다. 그것으로 안 되면 국소 탐색으로 넘어간다. **찾는 법이 좋아서
찾는 것이 아니라 판정기가 있어서 찾는 것이다.**
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import judge as J                                   # noqa: E402
from seek import problem as PR                                # noqa: E402

CHILD = Path(__file__).resolve().parent / "_solve_child.py"


def search(rec: dict, tries: int = 200000, seed: int = 0, seconds: float = 60.0,
           short: bool = False) -> dict:
    """표본 + 국소 탐색. **자식에서 돈다** -- 판정기가 임의 코드다."""
    payload = {"표본": rec.get("표본") or "", "판정": rec.get("판정") or "",
               "tries": tries, "씨": seed, "짧게": bool(short)}
    try:
        r = subprocess.run([sys.executable, str(CHILD), "--payload",
                            json.dumps(payload, ensure_ascii=False)],
                           capture_output=True, text=True, timeout=seconds + 10)
    except subprocess.TimeoutExpired:
        return {"ok": False, "왜": "시간 초과"}
    if r.returncode != 0:
        return {"ok": False, "왜": f"자식이 {r.returncode}: {r.stderr[-200:]}"}
    return json.loads(r.stdout.strip().split("\n")[-1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pid")
    ap.add_argument("--tries", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--짧게", dest="short", action="store_true",
                    help="찾은 뒤 하나씩 빼 보며 줄인다 (판정기가 있으니 공짜다)")
    a = ap.parse_args(argv)
    led = PR.load()
    rec = PR.get(led, a.pid)
    if rec is None:
        print(f"{a.pid} 는 원장에 없다")
        return 1
    print(f"{a.pid}  {rec.get('물음')}\n")
    got = search(rec, tries=a.tries, seed=a.seed, short=a.short)
    if not got.get("ok"):
        print(f"못 돌렸다: {got.get('왜')}")
        return 1
    if got.get("답") is None:
        print(f"못 찾았다 ({got.get('본것', 0):,}개 봤다)  ← 없다는 뜻이 아니다")
        return 2
    tail = ""
    if got.get("처음길이") and got.get("끝길이") != got.get("처음길이"):
        tail = f" · {got['처음길이']}개 -> **{got['끝길이']}개**로 줄였다"
    print(f"**찾았다** ({got.get('본것', 0):,}개 봤다{tail})")
    print(f"  {json.dumps(got['답'], ensure_ascii=False)}")
    back = J.judge(rec, got["답"])
    okc = bool(back.get("받음"))
    print(f"\n부모 프로세스에서 다시 검산: {'받음' if okc else '**안 받음**'}"
          "  ← 자식이 거짓말하지 않았는지 본다")
    if okc:
        # **답을 원장에 적는다.** `reach` 가 보존과 확장을 재려면 양쪽 답이 있어야 한다.
        rec["답"] = got["답"]
        PR.save(led)
        print(f"원장에 적었다 ({a.pid}.답)")
    return 0 if okc else 1


if __name__ == "__main__":
    raise SystemExit(main())
