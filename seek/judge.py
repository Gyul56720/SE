r"""판정기를 **격리해서** 부른다. 부모는 후보 코드를 한 번도 실행하지 않는다.

    runs(rec)              판정기가 돌기는 하나 -- 원장이 문제를 받기 전에 이것을 본다
    shake(rec, n)          무작위 후보 n 개. **전부 받거나 아무것도 안 받으면 망가진 문제다**
    judge(rec, 후보)        하나 판정
    cross(부모, 후보)        부모의 판정기가 자식의 답을 **읽기라도 하나**
    embed(rec, 후보)        부모의 후보를 이 문제의 후보로 옮긴다
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CHILD = Path(__file__).resolve().parent / "_child.py"
TIMEOUT = float(os.environ.get("SEEK_TIMEOUT", "20"))


def _run(op: str, payload: dict, seconds: float = 10.0) -> dict:
    try:
        r = subprocess.run(
            [sys.executable, str(CHILD), "--op", op, "--payload",
             json.dumps(payload, ensure_ascii=False, default=str),
             "--seconds", str(seconds)],
            capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "왜": "자식이 시간 안에 안 끝났다"}
    if r.returncode != 0:
        return {"ok": False, "왜": f"자식이 {r.returncode} 로 끝났다: {r.stderr[-160:]}"}
    try:
        return json.loads(r.stdout.strip().split("\n")[-1])
    except Exception as e:                                    # noqa: BLE001
        return {"ok": False, "왜": f"자식 출력을 못 읽었다: {type(e).__name__}: {e}"}


def runs(rec: dict) -> tuple:
    """(도나, 왜). **비었는지가 아니라 도는지를 본다.**

    `def judge(x): pass` 는 비어 있지 않지만 판정기가 아니다. 돌려 보면 안다."""
    got = _run("runs", {"표본": rec.get("표본") or "", "판정": rec.get("판정") or ""})
    if not got.get("ok"):
        return False, got.get("왜", "모름")
    return True, f"표본 {got['본것']}개 중 {got['받음']}개를 받았다"


def shake(rec: dict, n: int = 200, seed: int = 1) -> dict:
    return _run("shake", {"표본": rec.get("표본") or "", "판정": rec.get("판정") or "",
                          "n": n, "씨": seed}, seconds=30.0)


def judge(rec: dict, 후보) -> dict:
    return _run("judge", {"판정": rec.get("판정") or "", "후보": 후보})


def cross(부모: dict, 후보) -> dict:
    return _run("cross", {"판정": 부모.get("판정") or "", "후보": 후보})


def embed(rec: dict, 후보) -> dict:
    return _run("embed", {"옮김": rec.get("옮김") or "", "후보": 후보})
