"""**가설 -> 증명.** 자식 식이 부모에서 유도되는가를 걸음마다 판정한다. 호출 0회.

여기까지 파이프라인은 자식 식을 **주장**만 했다. "경계화를 걸면 이런 식이 된다" 고
적을 뿐, 부모 식에서 그리로 가는 길을 보이지 않았다. 그것이 겉핥기다 -- 이름을 짓는
것과 다를 바가 없다.

그래서 공간마다 `유도` 를 받는다. 부모 식에서 자식 식까지 **한 걸음씩**, 각 걸음은
수식이고 근거는 한 낱말이다. 유도란 결국

    E0 = E1 = E2 = ... = En

의 사슬이고, **각 등호가 참인지**가 물음이다. 그것은 취향이 아니라 사실이라 기계가 본다.

## 셋으로 판정한다 -- 미정이 요점이다

  · 참    sympy 가 두 식을 같은 것으로 줄였다
  · 거짓  자유 기호에 유리수를 넣었더니 한 점에서 어긋났다 (반례)
  · 미정  못 가른다. **극한을 걸거나 체를 바꾸거나 정의를 새로 하는 걸음이 여기 온다**

세 번째가 없으면 이 자는 못 쓴다. 경계화(ε -> 0)나 표수 이동(mod 2)은 대수 항등식이
아니다 -- sympy 가 못 가르는 것이 정상이고, 그것을 거짓이라 부르면 진짜 유도가 기각된다.
`mathgen/README.md` 가 "sympy 가 못 푼다 != 사람에게 어렵다" 를 적어 둔 것과 같은 자리다.

## 격리

`sympify` 는 임의 코드를 실행한다(실측: `sympify('__import__("os").getcwd()')` 가 평가된다).
그래서 파싱과 판정이 전부 `_prover.py` 자식 프로세스에서 돈다. 부모는 그 수식을 한 번도
파싱하지 않는다 -- `mathgen/_worker.py` · `mathdrift/_child.py` 와 같은 규율이다.

**정직하게: 이것은 샌드박스가 아니라 프로세스 분리다.** 수식 속 코드는 실제로 돈다 --
다만 부모가 아니라 자식에서 돈다. 그래서 부모의 임포트·전역·심판에 못 닿는다. 같은
기계 위에서 도는 것까지 막지는 않는다.

## 이것도 게이트가 아니다

거짓 걸음이 있다고 그 공간을 지우지 않는다. **거짓이 어디인지 짚어 주는 것**이 일이다 --
그 자리가 다음 걸음이 갈 곳이거나, 유도를 다시 쓸 자리다.

    python3 mathdrift/spread.py --prove          # 유도가 있는 것 전부
    python3 mathdrift/spread.py --prove S7       # 하나만
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHILD = Path(__file__).resolve().parent / "_prover.py"

TIMEOUT = float(os.environ.get("MATHDRIFT_PROVE_TIMEOUT", "60"))
STEP_TIMEOUT = int(os.environ.get("MATHDRIFT_STEP_TIMEOUT", "8"))

# 근거가 이 갈래면 **대수 항등식이 아니다.** sympy 가 미정을 내는 것이 정상이라,
# 보고에서 그렇게 표시한다 -- "못 가름" 과 "가를 것이 아님" 은 다른 말이다.
BEYOND = ("극한", "경계", "체", "표수", "정의", "가정", "점근", "완비", "국소", "매장",
          "범주", "동형", "위상", "모듈러", "mod")

# **도약의 근거.** 이것들은 등식이 아니라 **사상**이다 -- 부모의 대상을 다른 대상 안에
# 심는 것이라, 유도 사슬로 증명할 수가 없다. 증명 의무가 다른 데로 옮겨 간다.
LEAP = ("사상", "매장", "심음", "동형", "함자", "범주", "표현", "군대수", "embed")

# **물음이 바뀌는 근거.** 시금석 자체가 없어지는 자리다 -- omega 에는 "Strassen 점" 이
# 없다. 옛 시금석이 안 통하므로 기계가 볼 것이 남지 않는다.
SHIFT = ("점근", "지수", "omega", "오메가", "극한값", "복잡도")


def tier(rec: dict) -> dict:
    """이 공간의 **증명 의무가 어느 갈래인가.** 판정이 아니라 배치다.

    유도가 항등식 사슬이면 sympy 가 본다. 사상이면 사슬로는 못 보고 **왕복 검산**
    (부호화 -> 해독 -> Brent)이 그 자리를 대신한다 -- Cohn-Umans 의 triple product
    property 가 하는 일이 정확히 그것이다. 물음이 바뀌면 시금석이 없어서 아무것도 못 본다.

    이 셋을 구별하지 않으면 도약이 전부 "미정" 으로 뭉개진다. 미정에는 **가를 수 없는
    것**과 **가를 것이 아닌 것**이 섞여 있고, 그 둘은 다른 말이다.
    """
    words = " ".join(s["근거"] for s in steps_of(rec))
    dist = int((rec.get("계보") or {}).get("거리") or 1)
    op = (rec.get("계보") or {}).get("연산자", "")
    hay = words + " " + op
    if any(k in hay for k in SHIFT):
        return {"갈래": "물음 갈아타기", "증명": "없음",
                "왜": "묻는 것이 바뀌었다 -- 옛 시금석(Strassen)이 안 통한다"}
    if any(k in hay for k in LEAP) or dist >= 2:
        return {"갈래": "사상 도약", "증명": "왕복 검산",
                "왜": "등식이 아니라 사상이다 -- recall(부호화->해독->Brent)이 증명 의무다"}
    return {"갈래": "항등 이주", "증명": "유도 사슬",
            "왜": "같은 것을 다시 쓴 것이다 -- sympy 가 걸음마다 본다"}


def steps_of(rec: dict) -> list:
    """`유도` 를 걸음 목록으로. 꼴이 어긋나면 빈 목록이다 -- 기각하지 않는다."""
    raw = rec.get("유도")
    if not isinstance(raw, list):
        return []
    out = []
    for s in raw:
        if isinstance(s, dict):
            expr = (s.get("식") or "").strip()
            why = (s.get("근거") or "").strip()
        elif isinstance(s, str):
            expr, why = s.strip(), ""
        else:
            continue
        if expr:
            out.append({"식": expr, "근거": why})
    return out


def run(exprs: list, timeout: float = TIMEOUT) -> dict:
    """자식 프로세스에서 판정한다. 부모는 수식을 파싱하지 않는다."""
    with tempfile.TemporaryDirectory() as d:
        try:
            p = subprocess.run(
                [sys.executable, str(CHILD), "--steps", json.dumps(exprs),
                 "--timeout", str(STEP_TIMEOUT)],
                capture_output=True, text=True, timeout=timeout, cwd=d)
        except subprocess.TimeoutExpired:
            return {"status": f"{timeout}초 안에 안 끝났다"}
    if p.returncode != 0:
        return {"status": "자식이 죽었다", "why": (p.stderr or "")[-200:]}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"status": "자식이 JSON 을 안 냈다", "why": (p.stdout or "")[-200:]}


def check(rec: dict, timeout: float = TIMEOUT) -> dict:
    st = steps_of(rec)
    if len(st) < 2:
        t = tier(rec)
        why = "유도가 없다 (걸음이 둘은 있어야 견줄 것이 생긴다)"
        if t["갈래"] != "항등 이주":
            why += f" -- 다만 이 공간은 {t['갈래']} 라 사슬이 증명 자리가 아니다"
        return {"판정": "없음", "걸음": [], "왜": why}
    got = run([s["식"] for s in st], timeout)
    if got.get("status") != "ok":
        return {"판정": "못돎", "걸음": [],
                "왜": got.get("status", "") + " " + got.get("why", "")}

    rows, n = [], {"참": 0, "거짓": 0, "미정": 0}
    for i, v in enumerate(got["걸음"]):
        why_word = st[i + 1]["근거"]
        beyond = any(k in why_word for k in BEYOND + LEAP)
        mark = v["판정"]
        n[mark] = n.get(mark, 0) + 1
        rows.append({"n": i + 1, "근거": why_word, "판정": mark,
                     "대수밖": bool(beyond and mark == "미정"), "왜": v["왜"]})
    # **한 걸음이라도 거짓이면 그 사슬은 끊긴 것이다.** 그래도 지우지 않는다 -- 짚는다.
    if n["거짓"]:
        head = "끊김"
    elif n["미정"]:
        head = "일부 미정"
    else:
        head = "이어짐"
    return {"판정": head, "걸음": rows, "셈": n, "왜": ""}


def note(res: dict) -> str:
    if res["판정"] in ("없음", "못돎"):
        return f"{res['판정']} -- {res.get('왜', '')}"
    c = res["셈"]
    beyond = sum(1 for r in res["걸음"] if r["대수밖"])
    s = f"{res['판정']} (걸음 {len(res['걸음'])} -- 참 {c['참']} · 거짓 {c['거짓']} · 미정 {c['미정']}"
    return s + (f", 그중 대수 밖 {beyond}" if beyond else "") + ")"


def show(rec: dict, res: dict) -> None:
    t = tier(rec)
    print(f"{rec.get('id', '?')}  [{t['갈래']}] 증명은 {t['증명']} -- {t['왜']}")
    print(f"     {note(res)}")
    if not res["걸음"]:
        return
    st = steps_of(rec)
    print(f"\n  0. {st[0]['식'][:88]}")
    for r in res["걸음"]:
        mark = r["판정"] + ("*" if r["대수밖"] else "")
        why = f"  ({r['왜']})" if r["왜"] and r["판정"] != "참" else ""
        print(f"  {r['n']}. {mark:<6} {r['근거']:<8} {st[r['n']]['식'][:70]}{why}")
    if any(r["대수밖"] for r in res["걸음"]):
        print("\n  * 대수 항등식이 아닌 걸음 -- 극한 · 체 바꿈 · 정의는 sympy 가 가를 것이 아니다")
    if t["갈래"] == "사상 도약":
        print("\n  이 공간은 **사슬로 증명되지 않는다.** 등식이 아니라 사상이기 때문이다.")
        print("  증명 의무는 왕복에 있다:  python3 mathdrift/recall.py --only "
              + str(rec.get("id", "")))
    elif t["갈래"] == "물음 갈아타기":
        print("\n  이 공간은 **기계가 볼 것이 없다.** 물음이 바뀌어 시금석이 없어졌다 --")
        print("  여기가 지금 파이프라인의 한계고, 정직하게 미검증으로 남긴다.")
    print("  **판정이 게이트가 아니다.** 거짓이 어디인지 짚어 줄 뿐이다.")


def report(led: dict, only: str = "", timeout: float = TIMEOUT) -> int:
    """원장 전체. **갈래별로 나눠서 센다** -- 셋을 뭉치면 도약이 미정에 묻힌다."""
    rows = []
    for rec in led["spaces"]:
        if only and rec.get("id") != only:
            continue
        if (rec.get("계보") or {}).get("부모") in (None, "-"):
            continue
        t = tier(rec)
        res = check(rec, timeout) if steps_of(rec) else {"판정": "없음", "걸음": [],
                                                        "왜": "유도가 없다"}
        rec["증명"] = {"갈래": t["갈래"], "판정": res["판정"],
                       "셈": res.get("셈"), "걸음수": len(res["걸음"])}
        rows.append((rec, t, res))

    if not rows:
        print("볼 것이 없다" + (f" ({only})" if only else " -- 씨앗뿐이다"))
        return 0
    if only and len(rows) == 1:
        show(rows[0][0], rows[0][2])
        return 0

    by = {}
    for rec, t, res in rows:
        by.setdefault(t["갈래"], []).append((rec, res))
    print(f"공간 {len(rows)}개\n")
    for g in ("항등 이주", "사상 도약", "물음 갈아타기"):
        got = by.get(g) or []
        if not got:
            continue
        print(f"[{g}]  {len(got)}개 -- 증명은 "
              f"{ {'항등 이주': '유도 사슬', '사상 도약': '왕복 검산', '물음 갈아타기': '없음'}[g] }")
        for rec, res in got:
            c = res.get("셈") or {}
            body = (f"참 {c.get('참', 0)} · 거짓 {c.get('거짓', 0)} · 미정 {c.get('미정', 0)}"
                    if c else res["판정"])
            print(f"  {rec['id']:<5} {res['판정']:<8} {body:<28} "
                  f"{str(rec.get('식') or '')[:40]}")
        print()
    n_broken = sum(1 for _, _, r in rows if r["판정"] == "끊김")
    print(f"**사슬이 끊긴 공간 {n_broken}개** -- 거짓 걸음이 어디인지는 --prove <id> 로 본다.")
    print("사상 도약은 사슬로 증명되지 않는다. 그쪽 증명 의무는 recall(왕복 검산)에 있다.")
    print("물음 갈아타기는 기계가 볼 것이 없다 -- 여기가 지금 파이프라인의 한계다.")
    return 0
