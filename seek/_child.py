r"""판정기를 **여기서** 돈다. 부모는 이 코드를 임포트조차 안 한다.

`mathgen/_worker.py` · `mathdrift/_child.py` 와 같은 배치다. **샌드박스가 아니라
프로세스 분리다** -- 부모의 임포트 · 전역 · 원장에 못 닿을 뿐, 같은 기계 위에서
실제로 돈다. 그 한계를 여기 적어 둔다.

    python3 seek/_child.py --op runs      # 판정기가 돌기는 하나
    python3 seek/_child.py --op judge     # 후보 하나를 판정한다
    python3 seek/_child.py --op sample    # 후보를 뽑는다
    python3 seek/_child.py --op shake     # 무작위 후보 N 개로 흔든다
    python3 seek/_child.py --op cross     # 부모 판정기에 자식 답을 먹인다
"""
from __future__ import annotations

import argparse
import json
import random
import signal
import sys
import traceback


def _env(code: str) -> dict:
    g: dict = {"__name__": "_seek_judge", "random": random}
    exec(compile(code, "<판정기>", "exec"), g)      # noqa: S102
    return g


def _need(g: dict, name: str):
    fn = g.get(name)
    if not callable(fn):
        raise ValueError(f"`{name}` 이 없거나 부를 수 없다")
    return fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--op", required=True)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--seconds", type=float, default=10.0)
    a = ap.parse_args()
    p = json.loads(a.payload)

    def bell(signum, frame):                                  # noqa: ARG001
        raise TimeoutError("시간 초과")

    try:
        signal.signal(signal.SIGALRM, bell)
        signal.setitimer(signal.ITIMER_REAL, a.seconds)
    except (ValueError, OSError, AttributeError):
        pass

    try:
        if a.op == "runs":
            g = _env(p["표본"] + "\n" + p["판정"])
            sample, judge = _need(g, "sample"), _need(g, "judge")
            rng = random.Random(0)
            # **5개에서 32개로 늘렸다.** 이 수로 "다 받는다" 를 판정하기 때문이다.
            # 5개가 다 통과하는 것은 우연일 수 있지만 32개는 아니다.
            got = [sample(rng) for _ in range(32)]
            # **참/거짓을 돌려주는지까지 본다.** `def judge(x): pass` 는 안 터지고
            # None 을 돌려주는데, bool() 로 감싸면 False 가 되어 멀쩡해 보인다.
            # 비었는지만 보면 통과하고 돌려 보기만 해도 통과한다 -- 돌려준 것을 봐야 잡힌다.
            raw = [judge(x) for x in got]
            bad = [r for r in raw if not isinstance(r, bool)]
            if bad:
                raise ValueError(f"판정이 참/거짓이 아닌 것을 돌려준다: {bad[0]!r}")
            out = {"ok": True, "받음": sum(1 for r in raw if r), "본것": len(raw)}
        elif a.op == "shake":
            g = _env(p["표본"] + "\n" + p["판정"])
            sample, judge = _need(g, "sample"), _need(g, "judge")
            rng = random.Random(p.get("씨", 1))
            n = int(p.get("n", 200))
            hits, died = 0, 0
            for _ in range(n):
                x = sample(rng)
                try:
                    hits += 1 if judge(x) else 0
                except Exception:                             # noqa: BLE001
                    died += 1
            out = {"ok": True, "받음": hits, "본것": n, "터짐": died}
        elif a.op == "judge":
            g = _env(p["판정"])
            out = {"ok": True, "받음": bool(_need(g, "judge")(p["후보"]))}
        elif a.op == "sample":
            g = _env(p["표본"])
            out = {"ok": True, "후보": _need(g, "sample")(random.Random(p.get("씨", 0)))}
        elif a.op == "cross":
            # **부모의 판정기에 자식의 답을 그대로 먹인다.** 못 읽으면 그것이 확장의 증거다.
            g = _env(p["판정"])
            try:
                out = {"ok": True, "읽음": True, "받음": bool(_need(g, "judge")(p["후보"]))}
            except Exception as e:                            # noqa: BLE001
                out = {"ok": True, "읽음": False, "받음": False,
                       "왜": f"{type(e).__name__}: {e}"[:120]}
        elif a.op == "embed":
            g = _env(p["옮김"])
            out = {"ok": True, "후보": _need(g, "embed")(p["후보"])}
        else:
            out = {"ok": False, "왜": f"모르는 op: {a.op}"}
    except Exception as e:                                    # noqa: BLE001
        out = {"ok": False, "왜": f"{type(e).__name__}: {e}"[:200],
               "자취": traceback.format_exc(limit=2)[-300:]}
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
        except (ValueError, OSError, AttributeError):
            pass

    print(json.dumps(out, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
