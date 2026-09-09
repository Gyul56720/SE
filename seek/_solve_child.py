r"""탐색을 여기서 돈다. 판정기가 임의 코드라 부모에서 안 돌린다.

표본을 뽑아 걸어 보고, 안 되면 **가장 가까운 것에서 한 칸씩 바꿔 본다**(국소 탐색).
정렬망에서는 "몇 개 입력을 못 정렬했나" 가 자연스러운 거리다.
"""
from __future__ import annotations

import argparse
import json
import random
import sys




def _mutate(x, sample, rng):
    """한 칸만 흔든다. **후보가 무엇인지 모르는 채로 흔든다.**

    첫 판은 후보가 `[[i,j], ...]` 라고 가정했다 -- 정렬망 전용이었다. 낳은 문제의
    후보꼴은 미리 알 수가 없으므로(그게 이 파이프라인의 요점이다) 꼴을 안 보고
    흔들어야 한다. 새 표본에서 같은 자리를 가져다 끼우는 것이 제일 싸고 안전하다.
    """
    fresh = sample(rng)
    if isinstance(x, list) and x:
        nxt = list(x)
        k = rng.randrange(len(nxt))
        if isinstance(fresh, list) and fresh:
            nxt[k] = fresh[k % len(fresh)]
        else:
            nxt[k] = fresh
        return nxt
    if isinstance(x, dict) and x:
        nxt = dict(x)
        k = rng.choice(sorted(nxt))
        if isinstance(fresh, dict) and k in fresh:
            nxt[k] = fresh[k]
            return nxt
    return fresh


def _ok(judge, x):
    try:
        return bool(judge(x))
    except Exception:                                         # noqa: BLE001
        return False


def _shorten(x, judge, sample, rng, rounds=40000):
    """**판정기가 있으면 줄일 수 있다.** 이게 이 설계의 값이다 -- 문제에 판정기가
    딸려 오니 "자원을 줄여라" 가 공짜다. 부모(정확히 9개)에는 이 수를 쓸 수가
    없었다. 길이가 문제 정의에 박혀 있었기 때문이다.

    두 단계다. 먼저 그냥 빼 본다. 그것으로 막히면 **한 칸 짧은 길이에서 다시
    찾는다** -- 빼기만 하면 지금 답의 이웃에 갇힌다(실측: 9에서 멈췄는데 8이 있었다).
    """
    cur = list(x)
    while len(cur) > 1:
        # (1) 그냥 빼기
        cut = None
        for k in range(len(cur)):
            trial = cur[:k] + cur[k + 1:]
            if _ok(judge, trial):
                cut = trial
                break
        if cut is not None:
            cur = cut
            continue
        # (2) 한 칸 짧은 길이에서 국소 탐색. **여기도 후보꼴을 안 본다** --
        # 짧게 자른 것에서 한 칸씩 갈아 끼우며 찾는다.
        found = None
        for k0 in range(len(cur)):
            trial = cur[:k0] + cur[k0 + 1:]
            for _ in range(rounds // max(1, len(cur))):
                if _ok(judge, trial):
                    found = trial
                    break
                trial = _mutate(trial, sample, rng)
                if not isinstance(trial, list) or len(trial) != len(cur) - 1:
                    trial = (cur[:k0] + cur[k0 + 1:])
            if found:
                break
        if found is None:
            return cur
        cur = found
    return cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    p = json.loads(ap.parse_args().payload)
    g = {"__name__": "_seek_solve", "random": random}
    exec(compile(p["표본"] + "\n" + p["판정"], "<판정기>", "exec"), g)  # noqa: S102
    sample, judge = g["sample"], g["judge"]
    rng = random.Random(p.get("씨", 0))
    tries = int(p.get("tries", 200000))

    seen = 0
    cur = sample(rng)
    for _ in range(tries):
        seen += 1
        try:
            if judge(cur):
                ans = _shorten(cur, judge, sample, rng) if p.get("짧게") else cur
                print(json.dumps({"ok": True, "답": ans, "본것": seen,
                                  "처음길이": len(cur), "끝길이": len(ans)},
                                 ensure_ascii=False))
                return 0
        except Exception:                                     # noqa: BLE001
            pass
        cur = _mutate(cur, sample, rng) if seen % 50 else sample(rng)
    print(json.dumps({"ok": True, "답": None, "본것": seen}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
