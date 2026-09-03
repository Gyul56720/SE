"""어려운 문제 생성기의 독립 심판. 채점에 LLM 이 한 방울도 안 들어간다.

압축 코덱 심판(compression/judge.py)과 같은 구조다. 후보를 만든 쪽이 아니라 여기가 점수를
정하고, 후보는 격리된 별도 프로세스에서 돈다. 다른 점은 채점 대상이 코덱이 아니라
**문제 생성기**라는 것뿐이다.

왜 LLM 을 안 쓰는가: Google DeepMind 의 ICLR'24 결과 -- 내재적 자기교정은 개선이 없거나
성능을 떨어뜨린다. LLM 이 만든 문제를 LLM 이 채점하면 그 실패 형태에 그대로 들어간다.
여기서는 sympy 만 쓴다. sympy 는 우리 편도 저쪽 편도 아니다.

논문 근거:
  Evol-Instruct / WizardMath (Microsoft) -- 난이도를 올리는 In-Depth Evolving 연산자.
      제약 추가 / 심화 / 구체화 / 추론단계 증가 / 입력 복잡화.
  VeriEvol -- **난이도와 정답 신뢰성을 분리한다.** 난이도는 진화 연산자가 올리고, 정답은
      별도 검증이 보증한다. 한쪽을 올리려다 다른 쪽이 무너지는 것을 구조로 막는다.
      우리 두 축 래칫과 같은 형태다.
  MathScale (Microsoft Research) -- 씨앗에서 개념을 뽑아 조합한다.

세 축을 **동시에** 넘어야 한다:

  ① 정당성   답이 실제로 답인가. 문제 명세에서 **독립적으로 재검증**한다.
             적분이면 답을 미분해 피적분함수와 같은지 본다 -- 푸는 것보다 훨씬 싸다.
             이 비대칭성이 이 심판이 성립하는 이유다.

  ② 비자명성  sympy 의 기계적 호출이 실패하는가. 기계가 바로 푸는 문제는 문제가 아니다.

  ③ 압축성   풀이 비용 / 무식한 계산 비용. **절대 길이가 아니라 비율이다.**
             절대 길이(단계 수 <= K)로 재면 "내가 이미 구조를 아는 문제"만 통과한다 --
             짧은 풀이가 있다는 걸 확인하려면 그 풀이를 알아야 하기 때문이다. 그러면
             새 유형이 원천 봉쇄된다. 비율로 재면 지저분해도 된다. 막는 것은
             **압축되지 않는 지저분함**뿐이다.

세 축은 정면으로 싸운다. ②를 올리려고 계수를 키우면 ③이 무너지고, ③을 지키려고 단순하게
만들면 ②가 무너지고, 둘 다 맞추려고 답을 대충 내면 ①이 무너진다.

부정행위 차단(무엇을 막고 무엇을 못 막는지 분명히 적는다):
  막는다 - 문제문에 답 흘리기(문자열 검사), 전역/파일로 검증기에 신호 넘기기(프로세스
           분리), 같은 seed 에 다른 문제 내기(결정성), 퇴화한 문제(상수 답 등),
           답이 우연히 맞기(독립 재검증), 기계가 이미 푸는 문제(비자명성).
  못 막는다 - 생성기가 절대경로에 파일을 숨기는 것. 그리고 "사람에게 좋은 문제인가"는
           애초에 sympy 가 답할 수 있는 질문이 아니다. 여기서 재는 것은 그것이 아니다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE / "_worker.py"

GEN_TIMEOUT = float(os.environ.get("MATHGEN_GEN_TIMEOUT", "30"))
SOLVE_TIMEOUT = float(os.environ.get("MATHGEN_SOLVE_TIMEOUT", "15"))
N_INSTANCES = int(os.environ.get("MATHGEN_INSTANCES", "5"))

TASKS = ("integrate", "solve", "limit")


class GeneratorFailure(RuntimeError):
    """생성기가 계약을 못 지켰다. 점수가 아니라 실격 사유다."""


def _run(argv: list, timeout: float) -> dict:
    """자식 프로세스를 돌리고 JSON 을 받는다. 부모의 메모리를 전혀 공유하지 않는다."""
    tmp = Path(tempfile.mkdtemp(prefix="mathgen_"))
    try:
        env = dict(os.environ)
        env["TMPDIR"] = str(tmp)
        env["HOME"] = str(tmp)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            p = subprocess.run([sys.executable, str(WORKER)] + argv, capture_output=True,
                               text=True, timeout=timeout, env=env, cwd=str(tmp))
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        if p.returncode != 0:
            return {"status": "crashed", "detail": (p.stderr or "")[-800:]}
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            return {"status": "bad_output", "detail": (p.stdout or "")[-400:]}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _leaks_answer(statement: str, answer: str) -> bool:
    """문제문이 답을 그대로 담고 있는가.

    공백과 곱셈기호를 지우고 비교한다. `2*x**3/3` 과 `2x^3/3` 이 같은 것으로 보이게."""
    def norm(s: str) -> str:
        s = s.replace("**", "^").replace("*", "").replace(" ", "")
        return re.sub(r"[{}()\\\[\]]", "", s)
    a = norm(answer)
    return len(a) >= 6 and a in norm(statement)


def score_instance(generator: Path, seed: int, gen_timeout: float = GEN_TIMEOUT,
                   solve_timeout: float = SOLVE_TIMEOUT) -> dict:
    """인스턴스 하나를 채점한다. 생성 / 검증 / 기계풀이가 전부 다른 프로세스다."""
    generator = Path(generator).resolve()

    gen = _run(["generate", "--gen", str(generator), "--seed", str(seed)], gen_timeout)
    if gen.get("status") != "ok":
        raise GeneratorFailure(f"generate 실패({gen.get('status')}): {gen.get('detail', '')}")

    item = gen["item"]
    for key in ("statement", "spec", "answer", "solution"):
        if key not in item:
            raise GeneratorFailure(f"출력에 '{key}' 가 없다")
    spec = item["spec"]
    if spec.get("task") not in TASKS:
        raise GeneratorFailure(f"모르는 task: {spec.get('task')} (지원: {TASKS})")

    # 결정성: 같은 seed 에 같은 문제. 점수가 흔들리면 래칫이 성립하지 않는다.
    again = _run(["generate", "--gen", str(generator), "--seed", str(seed)], gen_timeout)
    if again.get("status") != "ok" or again["item"] != item:
        raise GeneratorFailure("같은 seed 에 다른 문제를 낸다 -- 결정론적이어야 한다")

    if _leaks_answer(item["statement"], item["answer"]):
        raise GeneratorFailure("문제문이 답을 그대로 담고 있다")

    # ① 정당성 ③ 압축성 -- 생성기 코드를 임포트하지 않고 문제 명세만 본다.
    chk = _run(["check", "--payload", json.dumps(item, ensure_ascii=False)], gen_timeout)
    if chk.get("status") == "timeout":
        raise GeneratorFailure("검증이 시간 안에 안 끝난다 -- 식이 과도하게 크다")
    if chk.get("status") == "degenerate":
        raise GeneratorFailure(f"퇴화한 문제: {chk.get('detail', '')}")
    if chk.get("status") != "ok":
        raise GeneratorFailure(f"검증 실패({chk.get('status')}): {chk.get('detail', '')}")

    # ② 비자명성 -- 또 다른 프로세스. **시간 초과 자체가 "기계가 못 푼다"는 신호다.**
    # 무한정 기다리면 못 푸는 것과 오래 걸리는 것을 구별할 수 없으므로 상한이 곧 정의다.
    mach = _run(["machine", "--payload", json.dumps(spec, ensure_ascii=False)], solve_timeout)
    if mach.get("status") == "ok":
        machine_solved = 1.0 if mach["solved"] else 0.0
        machine_note = mach.get("result", "")[:120]
    elif mach.get("status") in ("timeout", "crashed"):
        machine_solved = 0.0                     # 시간 초과/폭발 = 기계가 못 푼다
        machine_note = mach["status"]
    else:
        raise GeneratorFailure(f"기계풀이 판정 불가({mach.get('status')})")

    return {"seed": seed, "statement": item["statement"], "answer": item["answer"],
            "n_steps": len(item["solution"]), "machine_solved": machine_solved,
            "machine_note": machine_note, **chk["metrics"]}


def score_generator(generator: Path, seeds=None, **kw) -> dict:
    """생성기를 여러 인스턴스로 채점한다. 하나라도 실격이면 생성기 전체가 실격이다.

    한 인스턴스만 좋고 나머지가 퇴화하는 생성기를 막는다 -- 문제집은 인스턴스 하나가
    아니라 족(族) 단위로 쓰이기 때문이다."""
    seeds = list(range(N_INSTANCES)) if seeds is None else list(seeds)
    rows = [score_instance(generator, s, **kw) for s in seeds]
    n = len(rows)
    mean = {k: sum(r[k] for r in rows) / n
            for k in ("sound", "machine_solved", "compress_ratio", "brute_ops", "sol_ops")}
    return {"generator": str(generator), "n": n, "instances": rows, "mean": mean}


def evaluate(generator: Path, baseline: Path = None, **kw) -> dict:
    """채점하고 세 축 판정까지 낸다.

    baseline 을 주면 압축성을 그것과 비교한다(래칫). 안 주면 절대 기준만 본다."""
    res = score_generator(generator, **kw)
    m = res["mean"]

    reasons = []
    if m["sound"] < 1.0:
        reasons.append(f"정당성: 답이 틀린 인스턴스가 있다 ({m['sound']:.0%} 통과)")
    if m["machine_solved"] > 0.0:
        reasons.append(f"비자명성: sympy 가 바로 푸는 인스턴스가 있다 "
                       f"({m['machine_solved']:.0%})")

    base_ratio = None
    if baseline is not None:
        base_ratio = score_generator(Path(baseline), **kw)["mean"]["compress_ratio"]
        if m["compress_ratio"] >= base_ratio:
            reasons.append(f"압축성: 기준선보다 나쁘다 "
                           f"({m['compress_ratio']:.3f} >= {base_ratio:.3f})")

    res["baseline_compress_ratio"] = base_ratio
    res["passed"] = not reasons
    res["reason"] = ("세 축을 모두 넘었다: 정당성 100%, sympy 미해결 100%, "
                     f"압축비 {m['compress_ratio']:.3f}") if not reasons else " / ".join(reasons)
    return res


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="어려운 문제 생성기 독립 심판 (sympy 전용)")
    ap.add_argument("--gen", required=True, help="generate(seed) 를 정의한 파이썬 파일")
    ap.add_argument("--baseline", default=None, help="압축성을 비교할 기준 생성기")
    ap.add_argument("--instances", type=int, default=N_INSTANCES)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        res = evaluate(Path(a.gen), Path(a.baseline) if a.baseline else None,
                       seeds=range(a.instances))
    except GeneratorFailure as e:
        out = {"generator": a.gen, "passed": False, "reason": f"실격: {e}"}
        print(json.dumps(out, ensure_ascii=False, indent=2) if a.json else f"실격 -- {e}")
        return 1

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["passed"] else 1

    m = res["mean"]
    print(f"생성기 {res['generator']}")
    print(f"인스턴스 {res['n']}개\n")
    print(f"{'seed':>5}{'정당':>6}{'기계풀이':>9}{'무식ops':>9}{'풀이ops':>9}"
          f"{'압축비':>9}  문제")
    for r in res["instances"]:
        st = (r["statement"] or "")[:44].replace("\n", " ")
        print(f"{r['seed']:>5}{'O' if r['sound'] else 'X':>6}"
              f"{'풀림' if r['machine_solved'] else '미해결':>9}"
              f"{r['brute_ops']:>9.0f}{r['sol_ops']:>9.0f}{r['compress_ratio']:>9.3f}  {st}")
    print(f"\n평균  압축비 {m['compress_ratio']:.3f}"
          + (f"  (기준선 {res['baseline_compress_ratio']:.3f})"
             if res["baseline_compress_ratio"] is not None else ""))
    print(("통과: " if res["passed"] else "미달: ") + res["reason"])
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
