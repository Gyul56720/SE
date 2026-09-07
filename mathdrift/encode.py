"""**숫자로 재고, 돌려서 확인한다.** 이름은 장식할 수 있어도 숫자는 못 한다.

실측 2026-09-07(85개): 이름과 산문으로 공간을 주고받았더니 모델이 부모 이름에 연산자
어휘를 덧붙이는 데로 수렴했다 -- "멀티리니어 랭크 스펙트럼의 특성류 코호몰로지 공간".
낱말 겹침을 재는 자는 그것을 최고점으로 줬고, 이름이 정말 바뀐 것("지수 대역")을 깎았다.
프롬프트도 자도 전부 낱말이었으니 표류가 어휘 공간에서 일어난 것이다.

그래서 오가는 것을 **수와 코드**로 바꾼다.

  · 공간의 몸은 `치수`(매개변수 몇 개) · `정의역`(연속/격자/유한체) 와
    **해독기** `decode(p) -> (U, V, W, lambda)` 다
  · 판정은 그 해독기를 **돌려서** 한다. 산문 되사상 "요네다 매몰로 재해석" 은
    돌릴 것이 없으므로 그 자리에서 떨어진다

## 외운 답으로 빠져나갈 구멍을 막는다

`recall.py` 의 한계를 여기서 하나 메운다. 거기서는 모델이 공간을 무시하고 외운 Strassen 을
적어도 통과했다. 해독기를 받으면 **점을 흔들어 볼 수 있다**:

    decode(p) 와 decode(p') 가 **같으면** 그 해독기는 자기 입력을 안 쓴다.
    Strassen 을 하드코딩해 놓고 점을 무시한 것이다.

이것은 취향이 아니라 사실이라 기계가 본다.

## 격리

해독기는 별도 프로세스(`_child.py`)에서 돌고 수만 건너온다. 부모는 그 코드를 임포트하지
않는다 -- `mathgen/_worker.py` 가 생성기를 임포트조차 안 하는 것과 같은 이유다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHILD = Path(__file__).resolve().parent / "_child.py"

TIMEOUT = float(os.environ.get("MATHDRIFT_DECODE_TIMEOUT", "10"))
B, M = 2, 7
N = B * B


def run(code: str, points: list[list], timeout: float = TIMEOUT) -> dict:
    """해독기를 격리해서 돌린다. 돌아온 것은 수뿐이다."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "decoder.py"
        f.write_text(code, encoding="utf-8")
        try:
            p = subprocess.run(
                [sys.executable, str(CHILD), "--code", str(f),
                 "--points", json.dumps(points)],
                capture_output=True, text=True, timeout=timeout, cwd=d)
        except subprocess.TimeoutExpired:
            return {"status": f"{timeout}초 안에 안 끝났다"}
    if p.returncode != 0:
        return {"status": "자식이 죽었다", "why": (p.stderr or "")[-200:]}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"status": "자식이 JSON 을 안 냈다", "why": (p.stdout or "")[-200:]}


def _mat(raw, rows, cols):
    m = [[Fraction(str(x)) for x in r] for r in raw]
    if len(m) == rows and all(len(r) == cols for r in m):
        return m
    if len(m) == cols and all(len(r) == rows for r in m):
        return [[m[j][i] for j in range(cols)] for i in range(rows)]
    raise ValueError(f"크기가 {len(m)}x{len(m[0])} 다 ({rows}x{cols} 여야 한다)")


def brent(res: dict) -> bool:
    """**판정에 LLM 이 없다.** 이미 있는 심판을 쓴다 -- 새로 짜면 두 벌이 갈라진다."""
    sys.path.insert(0, str(ROOT / "mathmetics" / "matrix_exponent"))
    from verifier import ExactArithVerifier
    U = _mat(res["U"], N, M)
    V = _mat(res["V"], N, M)
    W = _mat(res["W"], N, M)
    lam = [Fraction(str(x)) for x in res["lambda"]]
    if len(lam) != M:
        raise ValueError(f"lambda 가 {len(lam)}개다")
    return bool(ExactArithVerifier(B).verify(U, V, W, lam))


def _shake(p: list) -> list:
    """점을 흔든다. **꼴은 그대로 두고 값만 바꾼다** -- 길이가 달라지면 해독기가
    입력을 쓰는지가 아니라 길이 검사에 걸린 것이 되어 버린다."""
    out = []
    for i, x in enumerate(p):
        try:
            v = Fraction(str(x))
        except (ValueError, ZeroDivisionError):
            out.append(x)
            continue
        out.append(str(v + (1 if i % 2 == 0 else -1) * Fraction(1, 3)))
    return out


def check(code: str, point: list, timeout: float = TIMEOUT) -> dict:
    """세 가지를 한 번에 본다 -- 돌아가는가 · Strassen 이 나오는가 · 점을 쓰는가."""
    if not (code or "").strip():
        return {"판정": "없음", "왜": "해독기가 비어 있다"}
    if not isinstance(point, list) or not point:
        return {"판정": "없음", "왜": "점이 없다"}

    got = run(code, [list(point), _shake(point)], timeout)
    if got.get("status") != "ok":
        return {"판정": "못돎", "왜": got.get("status", "") + " " + got.get("why", "")}

    a, b = (got["results"] + [{}, {}])[:2]
    if not a.get("ok"):
        return {"판정": "못돎", "왜": a.get("why", "")}
    try:
        ok = brent(a)
    except Exception as e:                                    # noqa: BLE001
        return {"판정": "못읽음", "왜": f"{type(e).__name__}: {e}"[:160]}

    # 점을 흔들었는데 결과가 그대로면 해독기가 자기 입력을 안 쓴 것이다.
    same = b.get("ok") and all(a.get(k) == b.get(k) for k in ("U", "V", "W", "lambda"))
    return {"판정": ("재현" if ok else "틀림"),
            "치수": len(point),
            "하드코딩": bool(same),
            "왜": ("점을 흔들어도 같은 것이 나왔다 -- 해독기가 입력을 안 쓴다" if same else "")}
