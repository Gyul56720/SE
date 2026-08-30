import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
try:
    from .optimizer import escalate_budget, update_params
except ImportError:
    # systemd 의 ExecStart 는 이 파일을 패키지가 아니라 '스크립트'로 직접 실행한다
    # (python3 .../self_improve_loop.py). 그 경로에서는 상대 임포트가 ImportError 로
    # 죽고, Restart=on-failure 와 맞물려 10초마다 무한 재시작하는 꼴이 된다. 스크립트로
    # 실행되면 sys.path[0] 이 이 파일의 디렉터리이므로 절대 임포트로 넘어간다.
    from optimizer import escalate_budget, update_params

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "logs" / "history.jsonl"
BEST_DIR = HERE / "best"

def _load(name, path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _append_log(record):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# 정체 판정 파라미터. 최근 WINDOW회와 그 직전 WINDOW회의 '최소 잔차'를 비교해서, 상대
# 개선폭이 MIN_GAIN 미만이면 정체로 본다.
STAGNATION_WINDOW = 50
STAGNATION_MIN_GAIN = 0.02  # 2% 상대 개선


def _residuals_for(b: int, m: int) -> list:
    """현재 전선(b, m)에 대해 기록된 als_residual을 오래된 순서대로 모은다. 다른 목표의
    기록과 깨진 줄은 조용히 무시한다(로그는 여러 버전의 코드가 이어 쓴 파일이라 형식이
    섞여 있다)."""
    out = []
    if not LOG_PATH.exists():
        return out
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if entry.get("b") != b or entry.get("m") != m:
                continue
            res = entry.get("als_residual")
            if isinstance(res, (int, float)) and math.isfinite(res):
                out.append(float(res))
    return out


def check_stagnation(b: int, m: int) -> bool:
    """탐색이 실질적으로 제자리인지 판정한다.

    예전 구현은 'REJECTED가 5회 연속이면 정체'였는데, 이 문제에서 REJECTED는 예외가 아니라
    기본값이다(정확한 스킴을 찾는 일 자체가 드물다). 그래서 한 번 실패가 쌓이기 시작하면
    이후 영원히 True를 돌려줬고 -- 실측: b=3,m=22에서 1185회 연속 REJECTED -- 매 회
    "Stagnation detected"를 찍으며 예산을 다시 올리는, 신호 역할을 못 하는 상태가 됐다.

    대신 '잔차가 더 내려가고 있는가'를 본다. 최근 WINDOW회의 최소 잔차가 직전 WINDOW회의
    최소 잔차보다 MIN_GAIN 이상 낮아지지 않았으면 정체다. 표본이 2*WINDOW에 못 미치면
    아직 판단할 근거가 없으므로 False(=정체 아님)."""
    hist = _residuals_for(b, m)
    if len(hist) < 2 * STAGNATION_WINDOW:
        return False
    best_recent = min(hist[-STAGNATION_WINDOW:])
    best_prior = min(hist[-2 * STAGNATION_WINDOW:-STAGNATION_WINDOW])
    if best_prior <= 0:
        return False
    return (best_prior - best_recent) / best_prior < STAGNATION_MIN_GAIN

def run_once():
    ts = time.time()
    verifier = _load("_me_verifier", HERE / "verifier.py")
    searcher_mod = _load("_me_searcher", HERE / "searcher.py")
    searcher = searcher_mod.Searcher()

    b, m = searcher.current_target()
    scheme = searcher.propose()
    resid = scheme.get("_als_residual")
    
    # 1. Tier 2: 근사 검증 (성공 시 루프 전진, 그러나 최종 성공은 아님)
    ok_approx, msg_approx = verifier.verify_approx(scheme, epsilon=1e-3)
    # 2. Tier 1: 정확 검증 (최종 성공)
    ok_exact, msg_exact = verifier.verify_scheme(scheme)

    status = "REJECTED"
    tuning = None
    if ok_exact:
        status = "VERIFIED_EXACT"
    elif ok_approx:
        status = "VERIFIED_APPROX"
        changed, params = update_params(iters=4000, noise_scale=0.01)  # 더 정밀하게 탐색
        if changed:
            print(f"Approximation achieved! Refining precision: {params}", flush=True)
            tuning = "refine"
    elif check_stagnation(b, m):
        changed, params = escalate_budget()
        if changed:
            print(f"Stagnation detected! Increasing search budget: {params}", flush=True)
            tuning = "escalate"
        else:
            tuning = "escalate_exhausted"  # 사다리 끝 -- 예산으로는 더 할 게 없다.

    record = {"ts": ts, "b": b, "m": m, "als_residual": resid, "status": status,
              "reason": msg_exact if not ok_exact else "ok"}
    if tuning:
        record["tuning"] = tuning
    searcher.record(ok_exact) # 정확한 해일 때만 타겟 랭크 전진
    _append_log(record)
    return record

def _try_improve(backend: str) -> dict:
    """improve_agent 를 한 번 돌린다. 자가개선이 죽어도 탐색 루프는 계속 돌아야 하므로
    어떤 예외도 여기서 삼키고 사유만 돌려준다 (예: GEMINI_API_KEY 가 없는 환경)."""
    try:
        agent = _load("_me_improve_agent", HERE / "improve_agent.py")
        proposer = agent.BACKENDS[backend]
        return agent.run_once(proposer)
    except Exception as e:
        return {"action": "error", "detail": f"{type(e).__name__}: {e}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1,
                        help="0 이면 무한 (상시 서비스용).")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--improve-every", type=int, default=0,
                        help="N 회 반복마다 improve_agent 를 호출해 '정체하면 searcher 를 "
                             "고치는' 피드백 고리를 닫는다. 0 이면 자가개선 없음 -- 이 경우 "
                             "이 루프는 같은 탐색기를 영원히 반복만 한다.")
    parser.add_argument("--improve-backend", default="llm", choices=["llm", "mock"])
    args = parser.parse_args()

    i = 0
    while args.iterations == 0 or i < args.iterations:
        print(json.dumps(run_once(), ensure_ascii=False), flush=True)
        i += 1

        if args.improve_every > 0 and i % args.improve_every == 0:
            print(json.dumps({"improve": _try_improve(args.improve_backend)},
                             ensure_ascii=False), flush=True)

        if (args.iterations == 0 or i < args.iterations) and args.sleep > 0:
            time.sleep(args.sleep)

if __name__ == "__main__":
    main()
