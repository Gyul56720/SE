"""
자가 개선 루프 -- 제안(LLM)을 로컬 채점기로 검증해 '더 나을 때만' 채택한다.

이 저장소의 원칙을 그대로 옮긴 것이다: 제안이 아니라 검증된 채택. orchestrator 에서는 노드
verifier 가 심판이었고, 여기서는 metric.py 가 심판이다. LLM 은 코드를 제안할 뿐이고, 그것이
챔피언을 대체하려면 로컬 점수가 '엄격히' 더 높아야 한다. 같으면 유지한다(무의미한 교체로
이력을 흐리지 않기 위해서다).

한 반복:
    1. 프롬프트를 만든다 -- 과제 원문 + 지금 챔피언 코드 + 그 점수 상세 + 지금까지 시도한
       접근과 각각의 점수/실패 사유. 마지막 항목이 핵심이다. 이것이 없으면 LLM 은 같은 것을
       계속 다시 낸다(orchestrator 에서 실패 이력을 되먹여야 했던 것과 같은 이유).
    2. 후보 코드를 받아 candidates/ 에 쓴다. 형식 검사(파싱되는가, solve 가 있는가)를
       통과해야 실행한다.
    3. 별도 프로세스로 실행한다. 타임아웃과 격리가 둘 다 필요하다 -- 후보 코드는 LLM 이 쓴
       것이라 무한 루프거나 프로세스를 오염시킬 수 있다(orchestrator 의 노드 예산과 같은 이유,
       다만 여기서는 subprocess 라 메모리 폭주까지 막힌다).
    4. 나온 제출 CSV 를 학습 데이터의 정답으로 채점한다.
    5. 챔피언보다 높으면 교체한다. 어느 쪽이든 history.jsonl 에 남긴다.

멈춤 조건: max_iterations(0이면 무한), 또는 stop 파일 생성, 또는 사람이 kill.
LLM 호출은 orchestrator/llm_pool 을 그대로 쓴다 -- 쿼터/모델 자동 전환과 후보 상한이 이미 있다.

정직하게 적어두는 한계:
  - 로컬 점수가 리더보드 점수와 다를 수 있다(metric.py 의 가정 A/B/C 참고). 루프는 로컬
    점수만 최적화하므로, 그 차이가 크면 루프는 엉뚱한 방향으로 열심히 간다.
  - 학습 데이터에 과적합할 수 있다. 데이터셋이 여러 개면 config 의 holdout 로 일부를 떼어
    검증에만 쓰는 것이 안전하다.
  - 이 루프는 '더 나은 코드를 쓸 수 있는 모델'을 전제한다. 모델이 그 과제를 못 풀면 루프는
    점수를 올리지 못한다. 루프는 탐색을 자동화할 뿐 능력을 만들어내지 않는다.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "orchestrator"))

import llm_pool                                    # noqa: E402
import metric                                      # noqa: E402
import task as taskmod                             # noqa: E402

SYSTEM = (
    "너는 주어진 과제를 푸는 파이썬 해법을 개선하는 엔지니어다. 아래에 과제 설명 원문, 지금 "
    "가장 점수가 높은 코드(챔피언), 그 코드의 로컬 채점 결과, 그리고 지금까지 시도한 접근과 "
    "각각의 결과가 주어진다.\n"
    "이력을 먼저 읽고 이미 실패한 접근을 반복하지 마라. 점수가 어디서 깎이는지(채점 상세의 "
    "FP/FN, 놓친 분열 수 등)를 보고 그 부분을 노려라. 한 번에 여러 가지를 바꾸지 말고, "
    "무엇이 점수를 올렸는지 알 수 있게 한 가지 가설을 분명히 겨냥해라.\n"
    "출력 계약: 오직 파이썬 코드만 출력한다(설명·코드펜스 금지). 최상위에 "
    "def solve(data_dir: str, out_csv: str) -> None 가 있어야 하고, 필요한 import 는 코드 "
    "안에 포함한다. data_dir 안의 각 .zarr 를 읽어 out_csv 에 제출 형식으로 쓴다.\n"
    "코드 첫 줄에 '# 가설: ...' 형태의 한 줄 주석으로 이번에 무엇을 노렸는지 적어라 -- "
    "그 줄이 이력에 남아 다음 시도의 근거가 된다.\n"
    "쓸 수 있는 외부 패키지는 이 환경에 실제로 설치된 것뿐이다. 없는 패키지를 import 하면 "
    "그 후보는 즉시 실패로 기록된다. 확신이 없으면 numpy 만 쓰는 경로를 함께 넣어라."
)


def _parse_code(text: str) -> str:
    t = text.strip()
    if "```" in t:
        seg = t.split("```", 2)
        t = seg[1] if len(seg) > 1 else t
        for tag in ("python", "py"):
            if t.startswith(tag):
                t = t[len(tag):]
                break
        t = t.rsplit("```", 1)[0]
    return t.strip("\n")


def _code_defect(code: str) -> str:
    if not code.strip():
        return "빈 응답"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"문법 오류: {e}"
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "solve"
               for n in tree.body):
        return "최상위에 def solve(data_dir, out_csv) 가 없다"
    return ""


def _hypothesis(code: str) -> str:
    for line in code.splitlines()[:5]:
        if line.strip().startswith("#") and "가설" in line:
            return line.strip("# ").strip()
    return ""


def installed_packages() -> str:
    names = ("numpy", "scipy", "skimage", "zarr", "numcodecs", "networkx", "pandas",
             "sklearn", "tifffile", "torch", "cv2", "numba")
    have = []
    for n in names:
        try:
            __import__(n)
            have.append(n)
        except Exception:                                       # noqa: BLE001
            pass
    return ", ".join(have) or "(numpy 조차 없음 -- 환경을 먼저 고쳐야 한다)"


def _history_digest(t: taskmod.Task, limit: int = 12) -> str:
    rows = t.history(limit=limit)
    if not rows:
        return "(아직 시도 없음)"
    out = []
    for r in rows:
        head = f"- #{r.get('iteration')} 점수 {r.get('combined')}"
        if r.get("adopted"):
            head += " [채택]"
        if r.get("hypothesis"):
            head += f" | 가설: {r['hypothesis']}"
        if r.get("error"):
            head += f" | 실패: {str(r['error'])[:160]}"
        out.append(head)
    return "\n".join(out)


def build_prompt(t: taskmod.Task) -> str:
    champ = t.champion_path.read_text(encoding="utf-8") if t.champion_path.exists() else "(아직 없음 -- 처음부터 작성하라)"
    score = t.champion_score()
    return (SYSTEM
            + "\n\n[이 환경에 설치된 패키지]\n" + installed_packages()
            + "\n\n[과제 설명 원문]\n" + t.spec()
            + "\n\n[지금 챔피언 코드]\n" + champ
            + "\n\n[챔피언의 로컬 채점 결과]\n"
            + json.dumps(score, ensure_ascii=False, indent=2)[:4000]
            + "\n\n[지금까지의 시도]\n" + _history_digest(t))


def run_candidate(code_path: Path, data_dir: Path, out_csv: Path, timeout: float) -> dict:
    """후보를 별도 프로세스로 실행. 타임아웃·격리가 둘 다 필요하다."""
    runner = (f"import sys, runpy;"
              f"m = runpy.run_path({str(code_path)!r});"
              f"m['solve']({str(data_dir)!r}, {str(out_csv)!r})")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-c", runner], capture_output=True, text=True,
                           timeout=timeout, errors="replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"실행 시간 초과({timeout:g}초)", "seconds": timeout}
    sec = round(time.time() - t0, 1)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "")[-1500:]
        return {"ok": False, "error": f"exit={p.returncode}: {tail}", "seconds": sec}
    return {"ok": True, "seconds": sec, "stdout_tail": (p.stdout or "")[-800:]}


def evaluate(out_csv: Path, gt_csv: Path) -> dict:
    pred = taskmod.read_submission(out_csv)
    gt = taskmod.read_submission(gt_csv)
    return metric.score(pred, gt)


def one_iteration(t: taskmod.Task, cfg: dict, n: int, pool) -> dict:
    rec = {"iteration": n, "ts": time.time(), "adopted": False, "combined": None}
    data_dir = Path(cfg["data_dir"]) / "train"
    gt_csv = data_dir / "ground_truth.csv"

    try:
        text, label = llm_pool.call(pool, build_prompt(t), pool_id=f"solver-{t.slug}")
    except Exception as e:                                      # noqa: BLE001
        rec["error"] = f"LLM 호출 실패: {type(e).__name__}: {e}"
        return rec
    rec["model"] = label
    code = _parse_code(text)
    rec["hypothesis"] = _hypothesis(code)

    defect = _code_defect(code)
    if defect:
        rec["error"] = f"형식 검사 반려: {defect}"
        return rec

    cand = t.candidates / f"{n:04d}.py"
    cand.write_text(code, encoding="utf-8")
    rec["candidate"] = str(cand.relative_to(t.dir))

    with tempfile.TemporaryDirectory() as tmp:
        out_csv = Path(tmp) / "submission.csv"
        run = run_candidate(cand, data_dir, out_csv, float(cfg.get("candidate_timeout", 1800)))
        rec["seconds"] = run.get("seconds")
        if not run["ok"]:
            rec["error"] = run["error"]
            return rec
        if not out_csv.exists():
            rec["error"] = "실행은 끝났으나 제출 CSV 를 만들지 않았다"
            return rec
        try:
            s = evaluate(out_csv, gt_csv)
        except Exception as e:                                  # noqa: BLE001
            rec["error"] = f"채점 실패(제출 형식 오류일 가능성): {type(e).__name__}: {e}"
            return rec

    rec["combined"] = round(s["combined"], 6)
    rec["edge_jaccard"] = round(s["edge_jaccard"], 6)
    rec["division_jaccard"] = round(s["division_jaccard"], 6)
    if s["missing_datasets"]:
        rec["missing_datasets"] = s["missing_datasets"]

    best = (t.champion_score() or {}).get("combined")
    if best is None or s["combined"] > best:
        t.champion_path.write_text(code, encoding="utf-8")
        t.champion_score_path.write_text(json.dumps(s, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        rec["adopted"] = True
        rec["previous_best"] = best
    return rec


def _seed_baseline(t: taskmod.Task, cfg: dict) -> dict:
    """챔피언이 없으면 baseline.py 를 0번째 시도로 실행·채점해 바닥을 만든다.
    LLM 이 첫 제안을 낼 때 비교 대상이 있어야 '개선'이라는 말이 성립한다."""
    rec = {"iteration": 0, "ts": time.time(), "adopted": False, "combined": None,
           "hypothesis": "베이스라인(사람이 쓴 출발점)"}
    data_dir = Path(cfg["data_dir"]) / "train"
    code = (HERE / "baseline.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        out_csv = Path(tmp) / "submission.csv"
        run = run_candidate(HERE / "baseline.py", data_dir, out_csv,
                            float(cfg.get("candidate_timeout", 1800)))
        rec["seconds"] = run.get("seconds")
        if not run["ok"]:
            rec["error"] = run["error"]
            return rec
        try:
            s = evaluate(out_csv, data_dir / "ground_truth.csv")
        except Exception as e:                                  # noqa: BLE001
            rec["error"] = f"채점 실패: {type(e).__name__}: {e}"
            return rec
    rec["combined"] = round(s["combined"], 6)
    t.champion_path.write_text(code, encoding="utf-8")
    t.champion_score_path.write_text(json.dumps(s, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    rec["adopted"] = True
    return rec


def loop(slug: str, max_iterations: int = None):
    t = taskmod.Task(slug)
    if not t.spec_path.exists():
        print(f"과제 '{slug}' 가 없다. solver/start.py 로 먼저 만들어라.", file=sys.stderr)
        return 2
    cfg = t.config()
    limit = cfg.get("max_iterations", 0) if max_iterations is None else max_iterations

    data = taskmod.check_data(cfg)
    if not data["ground_truth_exists"]:
        msg = (f"로컬 정답이 없다: {data['ground_truth']}\n"
               f"채점기 없이는 개선을 판정할 수 없으므로 루프를 시작하지 않는다.\n"
               f"학습용 데이터와 정답 CSV 를 {data['data_dir']}/train/ 에 두고 다시 실행하라.")
        print(msg, file=sys.stderr)
        t.set_state(status="blocked", reason=msg, pid=os.getpid())
        return 3

    pool = llm_pool.build_pool()
    if not pool:
        msg = "LLM 후보 풀이 비었다 -- GEMINI_API_KEY(또는 _FALLBACK)를 설정하라."
        print(msg, file=sys.stderr)
        t.set_state(status="blocked", reason=msg, pid=os.getpid())
        return 3

    if not t.champion_path.exists() and (HERE / "baseline.py").exists():
        seed = _seed_baseline(t, cfg)
        t.append_history(seed)
        print(f"[solver] 베이스라인 시딩: {seed.get('combined') or seed.get('error')}", flush=True)

    start_at = len(t.history())
    t.set_state(status="running", pid=os.getpid(), started=time.time(),
                iteration=start_at, best=(t.champion_score() or {}).get("combined"),
                data=data)
    print(f"[solver] '{slug}' 시작. 데이터셋 train={data['train_datasets']} "
          f"test={data['test_datasets']}, 후보 풀 {len(pool)}개", flush=True)

    n = start_at
    while True:
        if (t.dir / "stop").exists():
            t.set_state(status="stopped", reason="stop 파일 발견")
            print("[solver] stop 파일 발견 -- 멈춘다.", flush=True)
            break
        if limit and n - start_at >= limit:
            t.set_state(status="finished", reason=f"max_iterations({limit}) 도달")
            break
        n += 1
        try:
            rec = one_iteration(t, cfg, n, pool)
        except Exception as e:                                  # noqa: BLE001
            rec = {"iteration": n, "ts": time.time(), "adopted": False, "combined": None,
                   "error": f"루프 예외: {type(e).__name__}: {e}",
                   "traceback": traceback.format_exc()[-1500:]}
        t.append_history(rec)
        best = (t.champion_score() or {}).get("combined")
        t.set_state(iteration=n, best=best, last=rec, status="running")
        mark = "채택" if rec.get("adopted") else ("실패" if rec.get("error") else "기각")
        print(f"[solver] #{n} {mark} 점수={rec.get('combined')} 최고={best} "
              f"{rec.get('hypothesis') or rec.get('error') or ''}"[:300], flush=True)
        time.sleep(float(cfg.get("sleep_between", 5)))
    return 0


def main():
    ap = argparse.ArgumentParser(description="자가 개선 루프 (보통 start.py 가 백그라운드로 부른다)")
    ap.add_argument("slug")
    ap.add_argument("--max-iterations", type=int, default=None)
    a = ap.parse_args()
    raise SystemExit(loop(a.slug, a.max_iterations))


if __name__ == "__main__":
    main()
