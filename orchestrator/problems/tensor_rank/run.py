"""오케스트레이터에게 텐서 랭크 분해를 시킨다 -- **답을 내가 모르는 문제**로 옮긴 첫 시험.

직선거리 문제는 내가 답을 알았다. 그래서 그것으로 잰 것은 "장치가 도는가"까지였다.
여기서 재려는 것은 그 다음이다: 내가 답을 모르는 구간에서 탐색이 무언가를 찾는가.

문제. 텐서 T 를 rank-1 항 M 개의 합으로 **정확히** 적을 때 M 을 얼마나 줄일 수 있는가.

    T = sum_{r=1}^{M} u_r (x) v_r (x) w_r

표적은 <3,3,3> 행렬곱 텐서다. 이 M 의 최솟값(텐서 랭크)은 50 년째 열려 있다 --
문헌이 아는 것은

    19 <= R(<3,3,3>) <= 23           하한 Blaeser, 상한 Laderman

뿐이고, 그 사이 다섯 값 중 어느 것이 참인지는 아무도 모른다. **나도 모른다.** 그래서
이 구간이 "내가 알 수 없는 최적화 구간"의 정의에 정확히 맞는다.

세 case 로 사다리를 놓는다:
    w_state  랭크 3 / 경계랭크 2   -- 심판을 재는 카나리. 수치 최적화가 속는 지점
    mm222    랭크 7 (증명됨)       -- 도달 가능한 발판. 여기서 못 하면 위는 볼 것 없다
    mm333    19 <= R <= 23         -- 미지의 구간

역할 분담:
    사람/도구      문제를 세우고 심판을 만든다 (이 파일과 verify.py)
    오케스트레이터  분해를 찾는다
    심판           채택을 정한다 (verify.py, LLM 없음, 유리수 정확 연산)

verify.py 에는 분해도 분해법도 들어 있지 않다. repair_node 가 노드에 verifier 를
읽기 전용으로 보여주므로, 심판이 답을 담으면 시험이 통째로 무의미해진다. 회귀 검사
(tests/test_tensor_rank_verifier.py)가 그것을 확인한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "orchestrator"))
sys.path.insert(0, str(HERE))

RUNS = REPO / "orchestrator" / "runs"

PROBLEM = '''텐서를 rank-1 항의 합으로 **정확히** 분해하라. 항의 개수를 예산 이하로 줄이는 것이 목표다.

[정의] 3차 텐서 T (모양 d0 x d1 x d2) 에 대해 길이 d0, d1, d2 인 벡터 u_r, v_r, w_r 을 M 개
골라 다음이 **모든 칸에서 정확히** 성립하게 하라.

    T[a][b][c] = sum_{{r=1}}^{{M}}  u_r[a] * v_r[b] * w_r[c]

[입력] 아래 파일에 case 들이 들어 있다.

    {target_path}

파일 내용:
```json
{target_json}
```

각 case 의 tensor 는 성긴 형식이다. entries 의 각 원소 [a, b, c, val] 은 T[a][b][c] = val 을
뜻하고, 적히지 않은 칸은 전부 0 이다. shape 는 [d0, d1, d2], budget 은 항 개수 상한이다.

[budget 은 상한이지 목표가 아니다]
M <= budget 이기만 하면 만점이고, M 을 더 줄여도 점수가 오르지 않는다. **틀린 분해는
M 이 아무리 작아도 0점이다.**

[case 가 무엇인가]
  · w_state  모양 2x2x2, 성분 셋. 랭크는 3, **경계랭크는 2** 다. 계수를 발산시키면 2 항으로
             오차를 0 에 임의로 가깝게 만들 수 있지만 정확히 0 으로는 못 만든다.
  · mm222    2x2 행렬곱 텐서. 최소 항 개수가 7 임이 증명되어 있다.
  · mm333    3x3 행렬곱 텐서. **최소 항 개수는 알려져 있지 않다.** 19 이상 23 이하까지만
             안다. 맞춰야 할 것은 이 case 의 budget 이다.

행렬곱 텐서의 뜻: 색인을 a=(i,j), b=(j,k), c=(i,k) 로 펴면 M 항 분해가 곧 곱셈을 M 번만
쓰는 행렬곱 알고리즘이다.

[네가 쓸 수 있는 것 -- 방법이 아니라 판의 규칙이다]

계산 시간. 네가 쓴 solve(inputs) 는 **최대 {budget:.0f} 초 동안 실행된다.** 그 안에서는
   무엇을 얼마나 계산하든 상관없다. 초과하면 끊기고 그 사실이 실패 사유로 남는다.
   답을 즉시 반환해야 한다는 제약은 없다.

표적 읽기. 위 경로의 target.json 은 solve 안에서 열어 읽을 수 있다. 즉 **네 답이 맞는지
   네가 직접 확인할 수 있다** -- 재구성해서 표적과 비교하면 된다. 심판이 쓰는 것과 같은
   기준(유리수 정확 일치, 허용치 0)을 네 코드 안에서도 쓸 수 있다.

이어서 하기. 아래 디렉토리는 **시도와 시도 사이에 지워지지 않는다.**

    {scratch}

   네 solve 는 여기에 무엇이든 읽고 쓸 수 있다. 한 번의 실행이 {budget:.0f} 초로 끊기더라도
   다음 시도가 그 결과를 이어받을 수 있다는 뜻이다. 매번 빈손에서 시작할 필요가 없다.

[출력] 최종 노드의 solve 는 다음을 반환하라.

    {{"cases": [
        {{"id": "<case id>", "rank": <M>,
         "u": [[...d0개...], ... M줄 ...],
         "v": [[...d1개...], ... M줄 ...],
         "w": [[...d2개...], ... M줄 ...]}}, ...
    ]}}

모든 case 를 포함해야 한다. u, v, w 는 줄 수가 M 으로 같아야 한다.

[성분 제약 -- 반드시 지켜라] 성분은 정수이거나 "3/2" 꼴의 유리수 문자열로 적어라.
    · |성분| <= 8
    · 분모 <= 12
0.1 같은 부동소수는 이진으로 정확하지 않아 분모가 2^55 급이 되고 그대로 실격이다.
**부동소수로 최적화했다면 마지막에 반드시 격자 위로 반올림하고, 반올림한 뒤에도 정확한지
직접 확인한 다음 제출하라.**

[채점] 채점은 네가 아니라 밖에 있는 심판이 한다. LLM 을 쓰지 않고 전부 유리수 정확
연산이다. case 마다 다음을 본다.
  · 성분이 격자 안인가
  · M 이 전개행렬 랭크 하한 이상인가 (심판이 직접 증명한다)
  · 재구성이 **한 칸도 틀리지 않고** 정확한가 -- 허용치는 0 이다
  · M 이 예산 이하인가
어떤 방법으로 찾았는지는 보지 않는다.

[알려진 사실 -- 방법은 여기에 없다]

크기. M 항 분해의 미지수는 M x (9+9+9) = 27M 개이고, 맞춰야 할 방정식은 9x9x9 = 729 개다.
   M=22 면 미지수 594 개에 방정식 729 개 -- 방정식이 135 개 더 많은 과결정계다.
   성분이 격자 위에 있으므로 이것은 연속 최적화가 아니라 유한한 충족 문제다. 성분을
   {{0,±1,±2}} 로만 잡아도 후보는 5^594 ~ 10^415 가지다. 훑어서 될 크기가 아니다.

재는 양이 다르다. 심판은 **랭크**를 잰다. 잔차를 줄이는 방법은 **경계랭크**를 잰다.
   이 둘은 다른 양이고, w_state 가 그 증거다: 랭크는 3 인데 경계랭크는 2 다. M=2 로
   잔차를 0 에 임의로 가깝게 만들 수 있지만 정확한 2 항 분해는 존재하지 않는다.
   계수를 1/eps 로 발산시키면 오차가 O(eps) 로 줄지만 어떤 유한한 eps 에서도 틀리다.
   <3,3,3> 에서도 경계랭크는 랭크보다 작다. 따라서 **M=22 에서 잔차가 0 으로 수렴하는데
   정확한 분해는 없을 수 있다.** 잔차만 보는 방법은 그 경우 영원히 답에 닿지 못하면서
   계속 좋아지는 것처럼 보인다. 허용치가 0 이고 성분에 격자가 걸린 이유가 이것이다.

알려진 값. <2,2,2> 의 최소 항 개수는 7 이고 증명되어 있다. <3,3,3> 은 19 이상 23 이하
   까지만 알려져 있다. 23 은 1976 년에 나왔고, 그 뒤 50 년 동안 손계산 · 수치최적화 ·
   충족문제 풀이 · 강화학습 네 갈래가 각자 시도했지만 **아무도 22 를 찾지 못했다.**
   22 가 존재하는지도, 존재하지 않는지도 증명되지 않았다.

그러므로. 이미 있는 방법을 그대로 쓰면 이미 있는 결과에 닿는다. 22 를 찾으려면 위 네
   갈래 중 어느 것도 아닌 것이 필요하다. 무엇이 그것인지는 알려져 있지 않고, 이 문제
   기술서도 알지 못한다. **방법은 네가 만들어야 한다.**

[제약] numpy 와 표준 라이브러리만 쓴다. 외부 최적화 라이브러리(scipy, tensorly 등)는 없다.
'''


def _apply_budgets(spec: dict, overrides: list) -> dict:
    for item in overrides or []:
        cid, _, val = item.partition("=")
        hit = [c for c in spec["cases"] if c["id"] == cid.strip()]
        if not hit:
            raise SystemExit(f"그런 case 가 없다: {cid}")
        hit[0]["budget"] = int(val)
    return spec


def _plant_verifier(run_dir: Path, spec: dict) -> str:
    """런 디렉토리에 외부 심판과 표적을 깔고 상대 경로를 돌려준다.

    LLM 이 쓴 채점표를 버리고 밖에서 만든 심판을 넣는다. plan_schema 의 verifier 가
    경로 문자열이라 가능하다 -- 압축 코덱과 직선거리에서 쓴 것과 같은 수다."""
    vdir = run_dir / "verifiers"
    vdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "verify.py", vdir / "rank_check.py")
    (vdir / "target.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    return "verifiers/rank_check.py#check"


def _inject(run_dir: Path, verifier_rel: str) -> dict:
    path = run_dir / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    before = None
    for node in plan["nodes"]:
        if node["id"] == plan["final"]:
            before = node.get("verifier")
            node["verifier"] = verifier_rel
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"final": plan["final"], "replaced": before, "with": verifier_rel,
            "n_nodes": len(plan["nodes"])}


def _table(spec: dict, final: dict) -> None:
    """최종 답을 case 별로 다시 채점해 표로 보인다. 실패해도 어디까지 갔는지 보여야 한다."""
    import importlib
    import verify
    importlib.reload(verify)
    rows = {str(r.get("id")): r for r in (final or {}).get("cases", [])
            if isinstance(r, dict)}
    print(f"\n{'case':9} {'M':>4} {'예산':>5}  결과")
    for c in spec["cases"]:
        r = rows.get(c["id"])
        if r is None:
            print(f"{c['id']:9} {'-':>4} {c['budget']:>5}  답 없음")
            continue
        d = verify.score_case(c, r)
        print(f"{c['id']:9} {str(d['rank']):>4} {c['budget']:>5}  "
              f"{'OK' if d['ok'] else 'X '} {d['reason']}")
        if d.get("alert"):
            print(f"{'':9} {'':>4} {'':>5}  !! {d['alert']}")


def _recheck(final: dict, run_dir: Path) -> tuple:
    """밖에서 만든 심판으로 최종 답을 **다시** 채점한다. drive 의 판정을 그대로 믿지 않는다.

    재계획이 주입 심판을 지우면 LLM 이 제 답에 스스로 합격을 준다. 그 상태에서도
    drive 는 "solved" 를 돌려주므로, 마지막에 한 번 더 재는 것이 유일한 안전망이다.

    **런의 target.json 을 봐야 한다.** 처음 판은 verify.TARGET 을 그대로 뒀는데, 그것은
    저장소의 원본(mm222<=7, mm333<=23)을 가리킨다. --budget 으로 예산을 풀어 돌린 런에서는
    당연히 예산 초과로 기각되고, 그러면 멀쩡한 통과에 "심판이 지워졌다"는 경고가 붙는다
    (실측 2026-09-03: mm222 M=8, mm333 M=27 이 전부 OK 인데 경고가 떴다).

    **거짓 경보는 경보를 죽인다.** 다음에 진짜로 심판이 지워졌을 때 아무도 안 믿는다."""
    import verify
    run_target = run_dir / "verifiers" / "target.json"
    old = verify.TARGET
    try:
        if run_target.is_file():
            verify.TARGET = run_target
        ok, why = verify.check(final, {})
    finally:
        verify.TARGET = old
    return bool(ok), why


def _verdict(spec: dict, final: dict) -> None:
    """통과했을 때 **무엇을 통과한 것인지** 말한다.

    예산 통과와 구간 진입은 다른 말이다. 예산은 --budget 으로 느슨하게 걸 수 있고,
    구간은 문헌이 아는 사실이라 안 움직인다. 둘을 섞어 말하면 자명한 27 항을 두고
    "미지의 구간에서 나온 결과"라고 부르게 된다 -- 실제로 한 번 그랬다."""
    import verify
    rows = {str(r.get("id")): r for r in (final or {}).get("cases", [])
            if isinstance(r, dict)}
    for c in spec["cases"]:
        if "lower" not in c.get("known", {}) or c["id"] not in rows:
            continue
        d = verify.score_case(c, rows[c["id"]])
        lo, hi = c["known"]["lower"], c["known"]["upper"]
        M, where = d["rank"], d.get("interval")
        if where == "new":
            print(f"\n{c['id']}: M={M} 이 문헌 상한 {hi} **아래**다. 50 년 동안 아무도 "
                  f"못 한 것이다.\n   그러니 축하보다 **의심이 먼저다.** 확인할 것:")
            print(f"   1) 심판이 주입본인가  -- plan.json 최종 노드 verifier")
            print(f"   2) 재구성이 정말 정확한가 -- 유리수 연산이므로 한 칸도 안 틀려야 한다")
            print(f"   3) 성분이 정말 격자 안인가 -- 발산한 계수는 경계랭크이지 분해가 아니다")
            print(f"   4) 다른 사람이 독립적으로 재현하는가")
        elif where == "at_upper":
            print(f"\n{c['id']}: M={M} 은 문헌 상한과 같다. 알려진 결과를 재현한 것이지 "
                  f"내린 것이 아니다.\n   다음은 --budget {c['id']}={M - 1} 이고, "
                  f"거기부터는 존재 여부조차 모른다.")
        elif where == "below":
            print(f"\n{c['id']}: M={M} 이 문헌 하한 {lo} 아래다. **먼저 심판을 "
                  f"의심하라** -- 문헌이 틀렸을 확률보다 구멍이 있을 확률이 크다.")
        else:
            print(f"\n{c['id']}: M={M} 은 예산은 넘겼지만 [{lo},{hi}] **위**다. "
                  f"상한 {hi} 를 아직 못 내렸다 -- --budget {c['id']}={M - 1} 로 "
                  f"한 칸 내려서 다시 돌려라.")


def _print_failures(res: dict, limit: int = 6) -> None:
    """심판이 남긴 기각 사유를 그대로 보여준다. 잘라내면 되먹임의 재료가 사라진다.

    node_status 의 "failed" 세 글자만 찍던 시절에는, 심판이 만든 진단이 파일 안에서
    사라졌다 -- 무엇이 틀렸는지 모르면 다음 수를 정할 수 없다."""
    fails = res.get("failures") or []
    if not fails:
        return
    print(f"\n심판이 남긴 기각 사유 (마지막 {min(limit, len(fails))}건 / 전체 {len(fails)}건):")
    for f in fails[-limit:]:
        print(f"  [{f['plan']}] {f['node']} -- {f['kind']}")
        for line in str(f["message"]).split(" | "):
            print(f"      {line}")


def _nature_of_pass(run_dir: Path) -> str:
    """통과가 **탐색인가 기억인가.** 최종 노드 코드의 성격을 한 줄로 말한다.

    이것을 안 말하면 mm222=7 통과를 보고 mm333=22 를 기대하는 오류를 범한다. 7 은
    교과서라 외워서도 통과하지만, 22 는 아무도 모르므로 외울 수가 없다. 같은 "통과"라도
    앞의 것은 기억이고 뒤의 것만 탐색이다.

    실측(2026-09-03, tensorrank mm333=24): 판본 다섯이 전부 상수표였고 갈아타기 0 회였다.
    상수 개수만 0 -> 222 -> 75 -> 201 -> 306 으로 늘었다. 되먹임이 방법 공간에서 움직이지
    않고 숫자만 고쳐 쓰고 있었다."""
    try:
        import method_trace
        rows = method_trace.report(run_dir)["versions"]
    except Exception:
        return ""
    if not rows:
        return ""
    tags = rows[-1]["tags"]
    if "상수표(계산 없음)" in tags:
        return ("이 통과는 **기억이지 탐색이 아니다** -- 최종 코드가 답을 상수로 적고 "
                "있다. 아무도 모르는 값에는 이 방법이 통하지 않는다.")
    if "골격/미완" in tags:
        return "최종 코드에 실질 계산이 없다 -- 통과했다면 심판을 의심하라."
    return f"최종 코드는 계산을 한다 (갈래: {', '.join(tags)})."


def _print_trace(run_dir: Path) -> None:
    """수리가 **같은 알고리즘을 다듬었는지, 다른 알고리즘으로 갈아탔는지** 찍는다.

    되먹임이 국소 수선만 하는 기계라면 알려진 방법 밖으로 나갈 수 없다. 판본 사이에서
    호출하는 함수 집합 자체가 바뀌는지가 그 구별이고, 그것을 안 재면 "라운드 4" 라는
    숫자만 남는다 -- 네 번 다듬은 것과 네 번 갈아탄 것이 같은 숫자로 보인다."""
    try:
        import method_trace
        res = method_trace.report(run_dir)
    except Exception as e:
        print(f"\n(판본 추적 실패: {type(e).__name__}: {e})")
        return
    if len(res["versions"]) < 2:
        return
    print(f"\n수리 판본 추적 ({len(res['versions'])}판, 갈아타기 {res['n_jumps']}회):")
    for r in res["versions"]:
        d = "  -  " if r["dist"] is None else f"{r['dist']:.3f}"
        print(f"  {r['name']:24} 거리 {d:>6}  {r['kind']:12} {', '.join(r['tags'])}")
        if r["new_calls"]:
            print(f"  {'':24} + {', '.join(r['new_calls'][:6])}")
    print(f"  등장한 갈래: {', '.join(res['families'])}")
    nature = _nature_of_pass(run_dir)
    if nature:
        print(f"  {nature}")
    if "미분류" in res["families"]:
        print("  '미분류' 는 알려진 갈래 어디에도 안 걸린 판본이다 -- 그쪽이 흥미롭다")


def main() -> int:
    ap = argparse.ArgumentParser(description="오케스트레이터에게 텐서 랭크 분해를 시킨다")
    ap.add_argument("--max-repair-rounds", type=int, default=4)
    ap.add_argument("--node-timeout", type=float, default=600.0)
    ap.add_argument("--budget", action="append", default=[],
                    metavar="ID=N", help="예산을 바꾼다 (예: --budget mm333=22). "
                                         "사다리는 24 -> 23 -> 22 이고 22 가 최종이다")
    ap.add_argument("--only", action="append", default=[], metavar="ID",
                    help="이 case 만 돌린다 (예: --only mm333). 세 case 를 동시에 "
                         "통과해야 하므로, 도달 가능한 rung 이 섞여 있으면 라운드가 "
                         "거기서 소진된다 -- mm333=22 처럼 한 자리만 볼 때 쓴다")
    ap.add_argument("--run-dir", default=None, help="기존 런을 이어서 돌린다")
    a = ap.parse_args()

    import planner
    import solve as orch_solve

    spec = _apply_budgets(json.loads((HERE / "target.json").read_text(encoding="utf-8")),
                          a.budget)
    if a.only:
        keep = [c for c in spec["cases"] if c["id"] in a.only]
        missing = sorted(set(a.only) - {c["id"] for c in keep})
        if missing:
            raise SystemExit(f"그런 case 가 없다: {missing}")
        spec["cases"] = keep

    if a.run_dir:
        run_dir = Path(a.run_dir).resolve()
        spec = json.loads((run_dir / "verifiers" / "target.json").read_text("utf-8"))
        rel = "verifiers/rank_check.py#check"
        print(f"기존 런을 이어서 돈다: {run_dir}")
    else:
        run_dir = RUNS / time.strftime("tensorrank-%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        # **시도와 시도 사이에 살아남는 자리.** 한 번의 실행이 예산에서 끊겨도 다음
        # 시도가 이어받을 수 있어야, 매번 빈손에서 시작하지 않는다.
        (run_dir / "scratch").mkdir(exist_ok=True)
        # 예산 값을 기술서에 **인자에서 그대로** 넣는다. 손으로 숫자를 적어두면
        # --node-timeout 을 바꿨을 때 기술서와 실제가 조용히 어긋난다.
        problem = PROBLEM.format(
            target_path=run_dir / "verifiers" / "target.json",
            budget=a.node_timeout, scratch=run_dir / "scratch",
            target_json=json.dumps(spec, ensure_ascii=False, indent=1))
        (run_dir / "problem.txt").write_text(problem, encoding="utf-8")

        print(f"런 디렉토리: {run_dir}")
        print("예산: " + ", ".join(f"{c['id']}<={c['budget']}" for c in spec["cases"])
              + f"  ·  노드 실행 {a.node_timeout:.0f}초  ·  scratch 유지")
        print("계획을 세운다 ...")
        plan_res = planner.make_plan(problem, str(run_dir))
        if plan_res.get("status") != "planned":
            print(f"계획 실패: {plan_res}")
            return 1

        rel = _plant_verifier(run_dir, spec)
        info = _inject(run_dir, rel)
        print(f"계획: 노드 {info['n_nodes']}개, 최종 노드 '{info['final']}'")
        print(f"심판 주입: {info['replaced']} -> {info['with']}")

    print("실행/검증/수리 루프를 돈다 ...")
    # **심판 경로를 drive 에 넘긴다.** 한 번 꽂아두는 것으로는 부족하다 -- 재계획이
    # plan.json 을 통째로 새로 쓰면서 주입한 심판을 지우기 때문이다(실측으로 걸렸다).
    res = orch_solve.drive(str(run_dir), max_repair_rounds=a.max_repair_rounds,
                           node_timeout=a.node_timeout, final_verifier=rel)

    print(f"\n결과: {res.get('status')}  (라운드 {res.get('rounds')}, "
          f"재계획 {res.get('replans')})")
    final = res.get("final_result") or {}
    _table(spec, final)
    # **"solved" 를 그대로 믿지 않는다.** 우리 심판으로 다시 재서 한 case 라도 못 맞추면
    # 심판이 우리 것이 아니었다는 뜻이다. 실측(2026-09-03): 재계획 1회가 든 런이
    # "solved" 로 끝났는데 세 case 전부 "답 없음"이었다.
    recheck_ok, recheck_why = ((True, "") if res.get("status") != "solved"
                               else _recheck(final, run_dir))
    if not recheck_ok:
        print(f"\n!! solved 라는데 우리 심판으로 다시 재면 통과가 아니다.\n   {recheck_why[:300]}")
        print("   재계획이 주입 심판을 지웠을 때 나오는 모습이다. "
              "plan.json 의 최종 노드 verifier 를 확인하라:")
        print(f"   python3 -c \"import json;p=json.load(open('{run_dir}/plan.json'));"
              f"print([n.get('verifier') for n in p['nodes'] if n['id']==p['final']])\"")
        (run_dir / "result.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return 1
    if res.get("status") != "solved":
        print(f"\n이유: {res.get('reason')}")
        print(f"기록: {json.dumps(res.get('log', []), ensure_ascii=False)[:800]}")
        _print_failures(res)
    else:
        _verdict(spec, res.get("final_result") or {})
    _print_trace(run_dir)
    (run_dir / "result.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if res.get("status") == "solved" else 1


if __name__ == "__main__":
    sys.exit(main())
