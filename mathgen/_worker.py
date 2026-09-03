"""심판이 띄우는 자식 프로세스. 생성 / 검증 / 기계풀이를 각각 격리해서 돈다.

세 명령이 **서로 다른 프로세스**로 돈다는 것이 요점이다:
  generate  후보 생성기를 돌려 문제를 받는다
  check     ① 정당성 ③ 압축성. 생성기 코드를 임포트하지 않는다 -- 문제 명세만 본다
  machine   ② 비자명성. sympy 의 기계적 호출. 시간 초과가 곧 "기계가 못 푼다"는 신호다

check 가 생성기를 임포트하지 않는 것이 핵심이다. 생성기가 전역 변수나 몽키패치로 검증에
개입할 경로가 닫힌다. 압축 심판에서 decode 전에 원본을 지운 것과 같은 수다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys

import sympy as sp


def _out(d: dict) -> None:
    print(json.dumps(d, ensure_ascii=False))


def _load(path: str):
    spec = importlib.util.spec_from_file_location("_candidate_gen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sym(s: str):
    """문자열 -> sympy 식. 생성기와 심판이 같은 규약을 쓴다."""
    return sp.sympify(str(s), rational=True)


def do_generate(args) -> None:
    mod = _load(args.gen)
    if not hasattr(mod, "generate"):
        _out({"status": "no_generate"})
        return
    item = mod.generate(int(args.seed))
    if not isinstance(item, dict):
        _out({"status": "not_dict"})
        return
    # JSON 왕복이 되는지 여기서 확인한다. 결정성 비교가 딕셔너리 동등성이라 필요하다.
    _out({"status": "ok", "item": json.loads(json.dumps(item, ensure_ascii=False))})


def _soundness(spec: dict, answer: str) -> tuple:
    """① 정당성. **푸는 것이 아니라 확인하는 것**이라 훨씬 싸다 -- 이 비대칭성이
    이 심판이 성립하는 이유다."""
    task = spec["task"]
    var = sp.Symbol(spec.get("var", "x"))
    expr = _sym(spec["expr"])
    ans = _sym(answer)

    if task == "integrate":
        # 답을 미분해 피적분함수와 같은가. 적분보다 미분이 압도적으로 싸다.
        resid = sp.simplify(sp.diff(ans, var) - expr)
        return (resid == 0), f"d/d{var}(답) - 피적분함수 = {resid}"

    if task == "solve":
        # 답을 대입해 0 이 되는가. 근을 찾는 것보다 확인이 싸다.
        vals = ans if isinstance(ans, (list, tuple, sp.Tuple)) else [ans]
        resid = [sp.simplify(expr.subs(var, v)) for v in vals]
        return all(r == 0 for r in resid), f"대입 잔차 = {resid}"

    if task == "limit":
        # 극한은 독립 검증이 약하다. 수치로 접근시켜 확인한다.
        pt = _sym(spec.get("point", 0))
        ok = True
        detail = []
        for eps in (sp.Rational(1, 10) ** k for k in (3, 4, 5)):
            try:
                v = sp.N(expr.subs(var, pt + eps))
                d = abs(sp.N(ans) - v)
                detail.append(float(d))
                ok = ok and (d < sp.Rational(1, 100))
            except Exception as e:                     # noqa: BLE001
                return False, f"수치 확인 실패: {e}"
        return bool(ok), f"수치 잔차 = {detail}"

    return False, f"모르는 task: {task}"


def _compressibility(spec: dict, solution: list) -> dict:
    """③ 압축성. 풀이 비용 / 무식한 계산 비용.

    **절대 길이가 아니라 비율이다.** 절대 길이로 재면 "이미 구조를 아는 문제"만 통과한다 --
    짧은 풀이가 있음을 확인하려면 그 풀이를 알아야 하기 때문이다. 비율로 재면 지저분해도
    되고, 막히는 것은 압축되지 않는 지저분함뿐이다.

    무식한 비용은 식을 통째로 펼쳤을 때의 연산 수로 잡는다 -- 항별로 갈아 넣을 때 실제로
    마주하는 분량의 대리값이다. 대리값이라는 점은 분명히 해 둔다."""
    expr = _sym(spec["expr"])
    try:
        brute = float(sp.count_ops(sp.expand(expr)))
    except Exception:                                   # noqa: BLE001
        brute = float(sp.count_ops(expr))
    sol = 0.0
    for step in solution:
        try:
            sol += float(sp.count_ops(_sym(step)))
        except Exception:                               # noqa: BLE001
            sol += float(len(str(step)))                # 식이 아닌 단계는 길이로 센다
    brute = max(brute, 1.0)
    return {"brute_ops": brute, "sol_ops": sol, "compress_ratio": sol / brute}


def _degenerate(spec: dict, answer: str, solution: list) -> str:
    """퇴화 검사. 통과하기 쉬운 쓰레기를 거른다."""
    if not solution:
        return "풀이 단계가 비었다"
    expr = _sym(spec["expr"])
    var = sp.Symbol(spec.get("var", "x"))
    if var not in expr.free_symbols:
        return f"문제에 변수 {var} 가 없다"
    if sp.count_ops(expr) < 3:
        return f"문제가 너무 단순하다 (연산 {sp.count_ops(expr)}개)"
    ans = _sym(answer)
    if ans.is_number:
        if spec["task"] == "integrate":
            return "부정적분의 답이 상수다"
    elif var not in ans.free_symbols and spec["task"] == "integrate":
        return "답에 변수가 없다"
    return ""


def do_check(args) -> None:
    item = json.loads(args.payload)
    spec, answer, solution = item["spec"], item["answer"], item["solution"]

    bad = _degenerate(spec, answer, solution)
    if bad:
        _out({"status": "degenerate", "detail": bad})
        return

    sound, detail = _soundness(spec, answer)
    metrics = {"sound": 1.0 if sound else 0.0, "sound_detail": detail}
    metrics.update(_compressibility(spec, solution))
    _out({"status": "ok", "metrics": metrics})


def do_machine(args) -> None:
    """② 비자명성. sympy 가 기계적으로 푸는가.

    이 프로세스가 시간 초과로 죽으면 부모가 '기계가 못 푼다'로 읽는다 -- 초과 자체가
    신호다. 그래서 여기서 따로 타임아웃을 걸지 않는다."""
    spec = json.loads(args.payload)
    var = sp.Symbol(spec.get("var", "x"))
    expr = _sym(spec["expr"])
    task = spec["task"]

    if task == "integrate":
        r = sp.integrate(expr, var)
        solved = not r.has(sp.Integral)
    elif task == "solve":
        r = sp.solve(expr, var)
        solved = bool(r)
    elif task == "limit":
        r = sp.limit(expr, var, _sym(spec.get("point", 0)))
        solved = not r.has(sp.Limit)
    else:
        _out({"status": "unknown_task"})
        return
    _out({"status": "ok", "solved": bool(solved), "result": str(r)[:400]})


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate"); g.add_argument("--gen", required=True)
    g.add_argument("--seed", required=True)
    c = sub.add_parser("check"); c.add_argument("--payload", required=True)
    m = sub.add_parser("machine"); m.add_argument("--payload", required=True)

    a = ap.parse_args()
    {"generate": do_generate, "check": do_check, "machine": do_machine}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
