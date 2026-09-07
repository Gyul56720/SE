"""공간이 적어 낸 해독기를 **격리해서** 돌린다. 부모는 이 코드를 임포트하지 않는다.

`mathgen/_worker.py` 와 같은 수다 -- 거기서 check 프로세스가 생성기를 임포트조차 안 하는
이유가 그것이다: 생성기가 전역 변수나 몽키패치로 검증에 개입할 경로를 닫는다. 여기서는
해독기가 심판(Brent 검산)에 손댈 길이 없어야 한다. 그래서 해독기는 여기서 돌고 **수만**
표준출력으로 건너간다.

    python3 mathdrift/_child.py --code <파일> --points <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction


def _num(x):
    """Fraction 도 숫자도 문자열로 내보낸다 -- 부모가 정확 산술로 되읽는다."""
    if isinstance(x, Fraction):
        return f"{x.numerator}/{x.denominator}"
    if isinstance(x, bool):
        return str(int(x))
    if isinstance(x, (int, float)):
        return str(x)
    return str(x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--points", default="")
    # **반대 방향.** 실측 2026-09-07: 모델에게 새 식과 해독기와 91개짜리 수 리스트를
    # 한 번에 지어내라고 했더니 20개 중 20개가 점을 안 냈다("없음 -- 점이 없다").
    # 그 점은 지어낼 것이 아니라 **계산할 것**이다 -- 부모의 Strassen 을 새 인코딩으로
    # 옮기면 나온다. 그래서 encode(U,V,W,lambda) -> p 를 받아 여기서 만든다.
    ap.add_argument("--scheme", default="", help="encode 에 넣을 (U,V,W,lambda) JSON")
    a = ap.parse_args()

    src = open(a.code, encoding="utf-8").read()
    ns: dict = {"Fraction": Fraction}
    try:
        exec(compile(src, "<해독기>", "exec"), ns)          # noqa: S102
    except Exception as e:                                   # noqa: BLE001
        print(json.dumps({"status": "코드가 안 돈다",
                          "why": f"{type(e).__name__}: {e}"[:200]}))
        return 0
    fn = ns.get("decode")
    if not callable(fn):
        print(json.dumps({"status": "decode 가 없다"}))
        return 0

    if a.scheme:
        fe = ns.get("encode")
        if not callable(fe):
            print(json.dumps({"status": "encode 가 없다"}))
            return 0
        U, V, W, lam = json.loads(a.scheme)
        F = lambda M: [[Fraction(str(x)) for x in r] for r in M]      # noqa: E731
        try:
            got = fe(F(U), F(V), F(W), [Fraction(str(x)) for x in lam])
        except Exception as e:                                        # noqa: BLE001
            print(json.dumps({"status": "encode 가 안 돈다",
                              "why": f"{type(e).__name__}: {e}"[:200]}))
            return 0
        try:
            pt = [_num(x) for x in got]
        except TypeError:
            print(json.dumps({"status": "encode 가 수의 리스트를 안 냈다"}))
            return 0
        print(json.dumps({"status": "ok", "point": pt}, ensure_ascii=False))
        return 0

    out = []
    for p in json.loads(a.points or "[]"):
        try:
            got = fn([Fraction(str(x)) for x in p])
        except Exception as e:                               # noqa: BLE001
            out.append({"ok": False, "why": f"{type(e).__name__}: {e}"[:160]})
            continue
        try:
            U, V, W, lam = got
            out.append({"ok": True,
                        "U": [[_num(x) for x in r] for r in U],
                        "V": [[_num(x) for x in r] for r in V],
                        "W": [[_num(x) for x in r] for r in W],
                        "lambda": [_num(x) for x in lam]})
        except Exception as e:                               # noqa: BLE001
            out.append({"ok": False, "why": f"내놓은 꼴이 (U,V,W,lambda) 가 아니다: {e}"[:160]})
    print(json.dumps({"status": "ok", "results": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
