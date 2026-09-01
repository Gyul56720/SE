"""
오케스트레이터 실전 벤치마크 -- 실제 LLM 으로 어려운 문제를 풀리고, 그 답을 '시스템 밖에서'
채점한다.

왜 밖에서 채점하는가 (이 파일의 존재 이유):
  이 시스템의 심판은 각 노드에 딸린 check() 다. 그런데 그 check() 도 LLM 이 쓴 코드다. 그래서
  "verified 로 끝났다"는 사실만으로는 아무것도 증명하지 못한다 -- verifier 가 허술하면 틀린
  답도 통과한다. 그것을 잡아내려면 시스템이 만들지 않은 정답이 필요하다.
  여기 담긴 기대 정답은 전부 이 파일 밖에서(작성 시점에) 독립적으로 계산해 박아 넣은 것이고,
  채점기는 시스템의 verifier 를 일절 신뢰하지 않는다.

  따라서 이 벤치마크가 재는 것은 정답률만이 아니다. 가장 중요한 수치는 다음 하나다:
      거짓 양성(false pass) = 시스템은 solved 라고 했는데 오라클 기준 오답
  이게 하나라도 나오면 "제안이 아니라 검증된 채택"이라는 전제 자체가 깨진 것이다.

문제 선정 기준 -- 검증은 쉽고 풀이는 어려운 것만 골랐다:
  - 전수 탐색이 노드 예산(기본 60초) 안에 절대 안 들어오게 규모를 잡았다. 알고리즘 선택이
    강제된다.
  - 하나는 여러 알고리즘의 합성이 필요해 DAG 분해를 강제한다.
  - 하나는 float 로는 원리상 못 맞추는 정밀도를 요구한다(도구 선택 함정).
  - 기준선 문제 하나를 맨 앞에 둔다. 이게 실패하면 시스템이 아니라 키/네트워크/설치가 문제다.

채점의 관대함(의도적):
  최종 결과의 JSON 키 이름은 LLM 이 정한다. 그래서 채점기는 키 이름을 보지 않고, 결과 안의
  모든 값을 재귀적으로 훑어 기대 답이 들어 있는지만 본다. 형식이 달라서 틀렸다고 하지 않기
  위해서다 -- 우리가 재려는 건 포맷 준수가 아니라 정답이다.

실행:
    cd ~/SE
    set -a; . ./.env; set +a
    python3 tests/bench_orchestrator.py                 # 전부
    python3 tests/bench_orchestrator.py --only b0,b1    # 일부만
    python3 tests/bench_orchestrator.py --resume        # 이미 끝난 문제는 건너뛰고 이어서

산출물(모두 logs/bench/ 아래 -- .gitignore 대상이라 저장소를 더럽히지 않는다):
    logs/bench/report.json      기계용 종합 결과 (이걸 그대로 보내면 된다)
    logs/bench/report.md        사람이 읽는 요약표
    logs/bench/runs/<id>/       각 문제의 plan.json + components/*.py + results/*.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORCH = REPO / "orchestrator"
sys.path.insert(0, str(ORCH))

import orchestrator  # noqa: E402
import planner  # noqa: E402
import solve as solve_mod  # noqa: E402
from plan_schema import Plan  # noqa: E402

OUT = REPO / "logs" / "bench"


# ---------------------------------------------------------------- 채점 보조

def walk(obj):
    """결과 dict 안의 모든 값을 재귀적으로 흘려보낸다(키 이름에 의존하지 않기 위해)."""
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from walk(v)


def int_lists(obj):
    """결과 안의 '정수 리스트'를 전부 모은다(문자열로 적힌 정수도 정수로 본다)."""
    out = []
    for v in walk(obj):
        if isinstance(v, (list, tuple)) and v:
            got = []
            for x in v:
                if isinstance(x, bool):
                    break
                if isinstance(x, int):
                    got.append(x)
                elif isinstance(x, str) and x.strip().lstrip("-").isdigit():
                    got.append(int(x))
                else:
                    break
            else:
                out.append(got)
    return out


def scalars_as_int(obj):
    out = []
    for v in walk(obj):
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            out.append(v)
        elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
            out.append(int(v.strip()))
    return out


def digit_strings(obj, length):
    """길이가 length 인 숫자 문자열을 찾는다. 9x9 중첩 리스트도 펴서 본다."""
    found = []
    for v in walk(obj):
        if isinstance(v, str):
            s = "".join(ch for ch in v if ch.isdigit())
            if len(s) == length:
                found.append(s)
        elif isinstance(v, (list, tuple)) and v:
            flat = []
            for row in v:
                if isinstance(row, (list, tuple)):
                    flat.extend(row)
                elif isinstance(row, (int, str)):
                    flat.append(row)
                else:
                    flat = []
                    break
            s = "".join(str(x) for x in flat if isinstance(x, (int, str)))
            if len(s) == length and s.isdigit():
                found.append(s)
    return found


def decimals(obj):
    """결과 안의 수를 Decimal 로. 문자열이면 원문 정밀도가 보존된다(float 면 거기서 끝)."""
    out = []
    for v in walk(obj):
        try:
            if isinstance(v, str) and v.strip():
                out.append((Decimal(v.strip()), "str"))
            elif isinstance(v, float):
                out.append((Decimal(repr(v)), "float"))
            elif isinstance(v, int) and not isinstance(v, bool):
                out.append((Decimal(v), "int"))
        except (InvalidOperation, ValueError):
            continue
    return out


# ---------------------------------------------------------------- 문제 정의
# 기대 정답은 전부 이 파일 밖에서 독립적으로 계산해 박아 넣은 값이다.

B2_NUMS = [605951702291, 896741913187, 691321348166, 419153852626, 450448526466,
           292340704948, 537395255299, 402080703477, 508437854801, 736737158740,
           501307459078, 780241968812, 208215902898, 862834820107, 102034376898,
           880621818410, 714495743871, 520050502863, 107672987731, 589950880375,
           761439399445, 188256689943, 523080305966, 481790456512, 394803774294,
           386875282893, 558174031820, 418728980888, 409707411520, 254201665900,
           538542418233, 965241182715, 194271677437, 269286664837, 917184179783,
           576476112840, 533708690434, 384562231426, 923944340450, 252953939584]
B2_TARGET = 6250811786711

B3_PUZZLE = "800000000003600000070090200050007000000045700000100030001000068008500010090000400"
B3_SOLUTION = "812753649943682175675491283154237896369845721287169534521974368438526917796318452"

B4_EDGES = [(0, 1, 16), (0, 2, 13), (1, 2, 10), (2, 1, 4), (1, 3, 12), (3, 2, 9),
            (2, 4, 14), (4, 3, 7), (3, 5, 20), (4, 5, 4),
            (0, 6, 11), (6, 4, 8), (6, 7, 15), (7, 5, 6), (1, 7, 5), (7, 3, 9)]
B4_MAXFLOW = 30

B5_ROOT = "1.167303978261418684256045899855"   # x^5 - x - 1 = 0, 30자리


def grade_b0(res):
    return (168 in scalars_as_int(res)), "1000 이하 소수는 168개"


def grade_b1(res):
    want = {123456789, 30305547335, 969730452764, 999912543310}
    for lst in int_lists(res):
        if set(lst) == want:
            return True, "네 해가 정확히 일치"
    got = [l for l in int_lists(res) if len(l) <= 8]
    return False, f"기대 {sorted(want)} / 결과에서 찾은 정수 리스트 {got[:3]}"


def grade_b2(res):
    """값의 부분집합이든 인덱스 목록이든, target 을 만들면 정답으로 친다."""
    pool = set(B2_NUMS)
    for lst in int_lists(res):
        if not lst:
            continue
        if all(x in pool for x in lst) and len(set(lst)) == len(lst) and sum(lst) == B2_TARGET:
            return True, f"값 {len(lst)}개의 합이 target 과 일치"
        if all(0 <= x < 40 for x in lst) and len(set(lst)) == len(lst):
            if sum(B2_NUMS[i] for i in lst) == B2_TARGET:
                return True, f"인덱스 {len(lst)}개의 합이 target 과 일치"
    return False, "target 을 만드는 부분집합을 결과에서 찾지 못함"


def grade_b3(res):
    for s in digit_strings(res, 81):
        if s == B3_SOLUTION:
            return True, "81칸이 유일해와 완전히 일치"
    found = digit_strings(res, 81)
    if found:
        diff = sum(1 for a, b in zip(found[0], B3_SOLUTION) if a != b)
        return False, f"81자 격자를 찾았으나 {diff}칸이 다름"
    return False, "81자 격자를 결과에서 찾지 못함"


def grade_b4(res):
    return (B4_MAXFLOW in scalars_as_int(res)), f"최대유량 {B4_MAXFLOW} 이 결과에 있는가"


def grade_b5(res):
    """정밀도는 단계별로 채점한다 -- float 로 어디까지 갔는지가 정보다."""
    want = Decimal(B5_ROOT)
    best, best_src = -1, None
    for val, src in decimals(res):
        if val == 0:
            continue
        for digits in (30, 20, 15, 10, 6):
            if abs(val - want) < Decimal(10) ** -digits:
                if digits > best:
                    best, best_src = digits, src
                break
    if best >= 30:
        return True, f"30자리 일치 ({best_src} 로 전달됨)"
    if best > 0:
        return False, f"{best}자리까지만 일치 ({best_src} 로 전달됨) -- 30자리 요구 미달"
    return False, "실근 비슷한 값을 결과에서 찾지 못함"


PROBLEMS = [
    {
        "id": "b0",
        "level": "기준선",
        "why_hard": "어렵지 않다. 이게 실패하면 시스템이 아니라 키·네트워크·설치를 먼저 의심하라.",
        "problem": "1000 이하의 소수가 모두 몇 개인지 구하라.",
        "grade": grade_b0,
    },
    {
        "id": "b1",
        "level": "상",
        "why_hard": ("N 이 10^12 라 전수 탐색은 예산 안에 절대 못 들어온다. 인수분해 -> 소수별 "
                     "제곱근 -> CRT 결합의 3단 분해가 사실상 강제되고, 두 소수 중 하나가 "
                     "4k+1 이라 (p+1)/4 지름길이 안 통해 Tonelli-Shanks 가 필요하다. "
                     "게다가 소수별 결과를 dict 로 넘기면 JSON 왕복에서 키가 문자열이 되는 "
                     "바로 그 함정을 다시 지난다."),
        "problem": ("N = 1000036000099 일 때, x^2 ≡ 30072681662 (mod N) 을 만족하는 "
                    "0 이상 N 미만의 모든 정수 x 를 구하라. N 은 서로 다른 두 소수의 곱이다. "
                    "해를 오름차순으로 모두 제시하라."),
        "grade": grade_b1,
    },
    {
        "id": "b2",
        "level": "상",
        "why_hard": ("40개에서 2^40 = 약 1.1조 가지라 전수 탐색은 불가능하고, 값이 10^11 대라 "
                     "합에 대한 DP 도 불가능하다. meet-in-the-middle(2^20 두 번) 같은 "
                     "제대로 된 알고리즘을 골라야만 예산 안에 든다."),
        "problem": ("다음 40개의 정수 중 일부를 골라 그 합이 정확히 6250811786711 이 되게 하라. "
                    "고른 수들을 모두 제시하라.\n" + ", ".join(str(n) for n in B2_NUMS)),
        "grade": grade_b2,
    },
    {
        "id": "b3",
        "level": "상",
        "why_hard": ("단서가 20개뿐인 최난도급 스도쿠다. 순진한 백트래킹은 예산을 넘기기 쉬워 "
                     "제약 전파나 후보 최소 칸 우선 같은 가지치기가 필요하다. 검증은 규칙 "
                     "확인이라 쉬우므로 verifier 가 정직한지도 함께 드러난다."),
        "problem": ("다음 스도쿠를 풀어라. 81자 문자열이며 0 은 빈칸이다. 답도 81자 문자열로 "
                    "제시하라.\n" + B3_PUZZLE),
        "grade": grade_b3,
    },
    {
        "id": "b4",
        "level": "상",
        "why_hard": ("최대유량과 최소컷 두 가지를 함께 요구해 DAG 분해를 강제한다. 잔여 그래프를 "
                     "제대로 다루지 않으면(역방향 간선 누락) 답이 작게 나오는데, 그 오답은 "
                     "'그럴듯해' 보여서 verifier 가 허술하면 그대로 통과한다."),
        "problem": ("정점 0..7 의 유향 그래프에 다음 (출발, 도착, 용량) 간선들이 있다.\n"
                    + ", ".join(f"({u},{v},{c})" for u, v, c in B4_EDGES)
                    + "\n정점 0 에서 정점 5 로 흐를 수 있는 최대 유량을 구하고, 그 값과 같은 "
                      "최소 컷의 용량도 함께 제시하라."),
        "grade": grade_b4,
    },
    {
        "id": "b5",
        "level": "상 (함정)",
        "why_hard": ("float64 는 유효숫자가 약 15~16자리라 30자리는 원리적으로 불가능하다. "
                     "Decimal 이나 분수 연산으로 갈아타야 하고, 결과도 float 로 넘기면 "
                     "JSON 을 지나며 정밀도가 잘린다 -- 문자열로 넘겨야 한다. "
                     "도구 선택과 직렬화를 동시에 시험한다."),
        "problem": ("방정식 x^5 - x - 1 = 0 의 실근을 소수점 아래 30자리까지 정확하게 구하라. "
                    "부동소수점 오차로 자릿수가 잘리지 않도록 주의하고, 답은 문자열로 제시하라."),
        "grade": grade_b5,
    },
]


# ---------------------------------------------------------------- 실행

def run_one(spec: dict, args) -> dict:
    run_dir = OUT / "runs" / spec["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    rec = {"id": spec["id"], "level": spec["level"], "started": time.strftime("%H:%M:%S")}
    t0 = time.time()

    print(f"\n{'='*70}\n[{spec['id']}] ({spec['level']}) 시작 — {spec['problem'][:60]}...",
          flush=True)
    try:
        plan_res = planner.make_plan(spec["problem"], str(run_dir))
        rec["planning"] = {k: plan_res.get(k) for k in ("status", "nodes", "final", "model")}
        if plan_res.get("status") != "planned":
            rec.update(outcome="planning_failed", detail=plan_res.get("errors"))
            return rec
        print(f"  계획: 노드 {plan_res['nodes']} (모델 {plan_res['model']})", flush=True)

        run_res = solve_mod.drive(str(run_dir), max_repair_rounds=args.max_repair_rounds,
                                  max_node_repairs=args.max_node_repairs,
                                  max_replans=args.max_replans,
                                  node_timeout=args.node_timeout)
    except Exception as e:                                   # noqa: BLE001
        rec.update(outcome="crashed", error=f"{type(e).__name__}: {e}",
                   traceback=traceback.format_exc()[-2000:], seconds=round(time.time()-t0, 1))
        print(f"  !! 예외: {e}", flush=True)
        return rec

    rec["seconds"] = round(time.time() - t0, 1)
    rec["system_status"] = run_res.get("status")
    rec["rounds"] = run_res.get("rounds")
    rec["replans"] = run_res.get("replans")
    rec["reason"] = run_res.get("reason")
    rec["final_result"] = run_res.get("final_result")

    plan = Plan.load(run_dir / "plan.json")
    rec["nodes"] = [{"id": n.id, "goal": n.goal[:70], "status": n.status,
                     "deps": n.deps,
                     "repairs": planner.repair_count(n),
                     "failures": [a.get("error") or a.get("rejected")
                                  for a in n.attempts if "error" in a or "rejected" in a]}
                    for n in plan.nodes]
    rec["node_count"] = len(plan.nodes)
    rec["total_repairs"] = sum(n["repairs"] for n in rec["nodes"])
    rec["timeouts"] = sum(1 for n in rec["nodes"] for f in n["failures"] if f and "예산" in str(f))

    # ---- 시스템 밖에서의 채점 ----
    ok, note = spec["grade"](rec["final_result"]) if rec["final_result"] is not None \
        else (False, "최종 결과 없음")
    rec["oracle_pass"] = ok
    rec["oracle_note"] = note
    rec["outcome"] = ("correct" if ok and rec["system_status"] == "solved" else
                      "FALSE_PASS" if rec["system_status"] == "solved" else
                      "correct_but_unclaimed" if ok else "incomplete")

    mark = {"correct": "정답", "FALSE_PASS": "!! 거짓 양성 !!",
            "correct_but_unclaimed": "정답(미완 보고)", "incomplete": "미완"}[rec["outcome"]]
    print(f"  결과: {mark} | 시스템={rec['system_status']} 라운드={rec['rounds']} "
          f"수리={rec['total_repairs']} 재계획={rec['replans']} {rec['seconds']}초", flush=True)
    print(f"  채점: {note}", flush=True)
    return rec


def write_report(records: list):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(records, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    n = len(records)
    correct = sum(1 for r in records if r.get("outcome") == "correct")
    false_pass = [r for r in records if r.get("outcome") == "FALSE_PASS"]
    lines = ["# 오케스트레이터 벤치마크 결과", "",
             f"실행: {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
             f"- 정답 {correct}/{n}",
             f"- **거짓 양성 {len(false_pass)}건** (시스템은 solved 인데 오라클 기준 오답)",
             f"- 총 수리 {sum(r.get('total_repairs') or 0 for r in records)}회, "
             f"재계획 {sum(r.get('replans') or 0 for r in records)}회, "
             f"예산초과 {sum(r.get('timeouts') or 0 for r in records)}회", "",
             "| 문제 | 난이도 | 결과 | 시스템 | 노드 | 라운드 | 수리 | 재계획 | 초 | 채점 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        lines.append("| {id} | {level} | {outcome} | {sys} | {nc} | {rd} | {rp} | {rl} | {s} | {note} |".format(
            id=r["id"], level=r.get("level", ""), outcome=r.get("outcome", "?"),
            sys=r.get("system_status", r.get("outcome", "?")), nc=r.get("node_count", "-"),
            rd=r.get("rounds", "-"), rp=r.get("total_repairs", "-"),
            rl=r.get("replans", "-"), s=r.get("seconds", "-"),
            note=(r.get("oracle_note", "") or "").replace("|", "/")[:60]))
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[3:]))


def main() -> int:
    ap = argparse.ArgumentParser(description="오케스트레이터 실전 벤치마크 (실제 LLM 사용)")
    ap.add_argument("--only", help="쉼표로 구분한 문제 id (예: b0,b1)")
    ap.add_argument("--resume", action="store_true", help="이미 결과가 있는 문제는 건너뛴다")
    ap.add_argument("--max-repair-rounds", type=int, default=3)
    ap.add_argument("--max-node-repairs", type=int, default=2)
    ap.add_argument("--max-replans", type=int, default=1)
    ap.add_argument("--node-timeout", type=float, default=None,
                    help=f"노드 실행 예산(초). 기본 {orchestrator.NODE_TIMEOUT:g}")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    wanted = [p for p in PROBLEMS
              if not args.only or p["id"] in {s.strip() for s in args.only.split(",")}]
    if not wanted:
        print("실행할 문제가 없다. --only 값을 확인하라.")
        return 2

    prev = {}
    prev_path = OUT / "report.json"
    if args.resume and prev_path.exists():
        prev = {r["id"]: r for r in json.loads(prev_path.read_text(encoding="utf-8"))}

    print(f"문제 {len(wanted)}개: {[p['id'] for p in wanted]}")
    print(f"노드 예산 {args.node_timeout or orchestrator.NODE_TIMEOUT:g}초 / "
          f"수리 라운드 {args.max_repair_rounds} / 노드당 수리 {args.max_node_repairs} / "
          f"재계획 {args.max_replans}")
    print("채점은 시스템의 verifier 가 아니라 이 파일에 박아둔 독립 정답으로 한다.")

    records = []
    for spec in wanted:
        if spec["id"] in prev and prev[spec["id"]].get("outcome") in ("correct", "FALSE_PASS"):
            print(f"\n[{spec['id']}] --resume: 이미 끝남 ({prev[spec['id']]['outcome']}) — 건너뜀")
            records.append(prev[spec["id"]])
            continue
        records.append(run_one(spec, args))
        write_report(records)          # 중간에 죽어도 여기까지는 남는다

    print(f"\n{'='*70}")
    write_report(records)
    print(f"\n기계용 결과: {OUT / 'report.json'}")
    print(f"사람용 요약: {OUT / 'report.md'}")
    return 1 if any(r.get("outcome") == "FALSE_PASS" for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
