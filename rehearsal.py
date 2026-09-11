"""rehearsal -- **고치기 전에 격리 판에서 돌려 본다.** 실제 트리에 닿기 전의 리허설.

사용자(2026-09-11): "너는 코드를 바꾸기 전에 바뀔 코드가 배선된 시스템을 시뮬레이션해 보고
문제가 없으면 바꾸잖아. 우리는 샌드박스 공간도 있는데 왜 이걸 안 하지?"

맞는 지적이다. 이 저장소에는 이미 둘이 있었는데 **이어져 있지 않았다**:
  · `sandbox.실행` -- 격리 판에서 명령을 돌린다
  · `plan` -- 그림자 워크트리에서 고치고 diff 를 보인다
그런데 `!계획 보기` 는 diff 를 **보여 주기만** 했고, 그 diff 를 **돌려 보지는 않았다.**
그래서 `!계획 승인` 은 '돌려 보지 않은 코드' 를 실제 트리에 붙였다. 여기서 잇는다.

리허설이 하는 것(전부 **판 안에서**, 실제 트리는 안 건드린다):
  1. 문법   -- 바뀐 .py 를 py_compile. **임포트 못 해도 잡힌다**(실측: on_ready 들여쓰기
              사고를 이것이 잡는다). 제3자 꾸러미가 없어도 도는 검사다
  2. 게이트 -- 그 판에서 gatekeeper 를 돌린다(G012 가 진짜 임포트까지 본다)
  3. 검사   -- 바뀐 파일이 거는 검사만 그 판에서 돌린다(audit.검사찾기 -- 두 벌 금지)

판정은 코드가 한다(끝값). 못 돌린 것은 **못잼**으로 따로 세고, 통과로 치지 않는다.

    python3 rehearsal.py                 # 계획판이 켜져 있으면 그 그림자를, 아니면 지금 작업 트리 사본을
    python3 rehearsal.py --판 <경로>
    끝값 0 통과 · 1 빨강 · 3 판을 못 깜
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent


def _바뀐것(판: Path) -> "list[str]":
    """그 판에서 바뀐(또는 새로 생긴) .py 들. 계획판은 add -N 을 이미 해 둔다."""
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain"],
                       capture_output=True, text=True, timeout=60)
    out = []
    for line in (r.stdout or "").splitlines():
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ")[-1]
        if rel.endswith(".py"):
            out.append(rel)
    return sorted(set(out))


def _돌리기(argv: "list[str]", 판: Path, 초: int) -> dict:
    from sandbox import run as SB
    return SB.실행(argv, repo=판, 지금트리=True, 초=초, 메모리MB=4096)


def 시험(repo=None, 판=None, 초: int = 180, 검사상한: int = 10) -> dict:
    """격리 판에서 문법·게이트·검사를 돌린다. 실제 트리는 안 건드린다."""
    repo = Path(repo or REPO)
    if 판 is None:
        try:
            from plan import store as P
            판 = P.현재판(repo)
        except Exception:                                  # noqa: BLE001
            판 = None
    판 = Path(판) if 판 else repo
    그림자인가 = 판 != repo
    결과 = {"판": str(판), "그림자": 그림자인가, "바뀐것": [], "걸음": [], "통과": True,
           "못잼": [], "걸린초": 0.0}
    시작 = time.monotonic()

    # **판이 없거나 git 판이 아니면 초록이라고 하지 않는다**(실측: 없는 경로에 '바뀐 것 없음 -> 통과' 를 냈다).
    if not 판.is_dir():
        결과.update(통과=False, 못잼=[f"판이 없다: {판}"], 걸린초=round(time.monotonic() - 시작, 1))
        return 결과
    확인 = subprocess.run(["git", "-C", str(판), "rev-parse", "--is-inside-work-tree"],
                        capture_output=True, text=True, timeout=30)
    if 확인.returncode != 0:
        결과.update(통과=False, 못잼=[f"git 판이 아니다: {판}"], 걸린초=round(time.monotonic() - 시작, 1))
        return 결과

    바뀐 = _바뀐것(판)
    결과["바뀐것"] = 바뀐
    if not 바뀐:
        결과["걸음"].append(("바뀐 .py 없음", 0, "리허설할 코드 변경이 없다"))
        결과["걸린초"] = round(time.monotonic() - 시작, 1)
        return 결과

    # 1. 문법 -- 임포트가 안 되는 환경에서도 도는 검사(들여쓰기·문법 사고를 여기서 잡는다)
    잴것 = [f for f in 바뀐 if (판 / f).is_file()]
    r = _돌리기(["python3", "-m", "py_compile", *잴것], 판, 초=60)
    if not r["돌았나"]:
        결과["못잼"].append(f"문법: {r.get('메모', '판을 못 깜')}")
        결과["통과"] = False
    else:
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-4:]
        결과["걸음"].append(("문법(py_compile)", r["끝값"], "\n".join(꼬리) or f"{len(잴것)}개 깨끗"))
        if r["끝값"] != 0:
            결과["통과"] = False

    # 2. 게이트 -- 그 판에서. G012 가 진짜 임포트까지 본다
    r = _돌리기(["python3", "gatekeeper.py"], 판, 초=초)
    if not r["돌았나"]:
        결과["못잼"].append(f"게이트: {r.get('메모', '판을 못 깜')}")
        결과["통과"] = False
    else:
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-6:]
        결과["걸음"].append(("게이트", r["끝값"], "\n".join(꼬리)))
        if r["끝값"] != 0:
            결과["통과"] = False

    # 3. 바뀐 파일이 거는 검사만 -- 그 판에서
    try:
        from audit import run as A
        걸림, 안덮임 = A.검사찾기(판, 바뀐)
        검사들 = sorted({t for ts in 걸림.values() for t in ts})[:검사상한]
    except Exception as e:                                 # noqa: BLE001
        검사들, 안덮임 = [], []
        결과["못잼"].append(f"검사 고르기: {type(e).__name__}")
        결과["통과"] = False
    결과["안덮임"] = 안덮임
    for t in 검사들:
        r = _돌리기(["python3", t], 판, 초=초)
        if not r["돌았나"]:
            결과["못잼"].append(f"{t}: {r.get('메모', '판을 못 깜')}")
            결과["통과"] = False
            continue
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-4:]
        결과["걸음"].append((t, r["끝값"], "\n".join(꼬리)))
        if r["끝값"] != 0:
            결과["통과"] = False

    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    return 결과


def 보고(r: dict) -> str:
    머리 = ("리허설(격리 판에서 미리 돌려 봤다) -- "
           + ("**그림자 계획판**" if r["그림자"] else "지금 작업 트리 사본")
           + f" · {r['걸린초']}초")
    줄 = [머리]
    if r["바뀐것"]:
        줄.append("  바뀐 코드: " + ", ".join(r["바뀐것"][:8]))
    for 이름, 끝값, 꼬리 in r["걸음"]:
        표 = "✓" if 끝값 == 0 else "✗"
        줄.append(f"  {표} {이름} (끝값 {끝값})")
        for x in (꼬리 or "").splitlines()[-3:]:
            if x.strip():
                줄.append(f"      {x[:160]}")
    for x in r["못잼"]:
        줄.append(f"  ? 못잼 {x[:140]} -- **못 돌린 것은 통과가 아니다**")
    if r.get("안덮임"):
        줄.append("  검사 없는 변경(버그가 샌다면 여기): " + ", ".join(r["안덮임"][:5]))
    줄.append("  판정: " + ("**초록 -- 실제 트리에 붙여도 된다**" if r["통과"]
                         else "**빨강 -- 붙이지 마라.** 위를 고치고 다시 시험하라"))
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="고치기 전에 격리 판에서 돌려 본다")
    ap.add_argument("--판", default="", help="리허설할 워크트리(비우면 계획판, 그것도 없으면 작업 트리)")
    ap.add_argument("--초", type=int, default=180)
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    r = 시험(Path(a.저장소) if a.저장소 else None, 판=(a.판 or None), 초=a.초)
    print(보고(r))
    if r["못잼"] and not r["걸음"]:
        return 3
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
