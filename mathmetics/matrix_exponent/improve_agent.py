"""
자기 개선 에이전트: '다음 개선을 스스로 추론'해 searcher.py 를 고치되, 개선이 검증될
때만 채택하는 닫힌 피드백 루프.

지금까지의 문제: self_improve_loop.py 는 searcher.py 를 실행/기록만 할 뿐, 정체를 인지해
코드를 바꾸는 주체가 없었다(피드백 루프가 끊겨 있었다). 이 에이전트가 그 고리를 잇는다:

  1. history.jsonl 을 읽어 '정체'(현재 목표에서 최근 시도들이 잔차를 못 낮춤)를 감지한다.
  2. 정체면 proposer 에게 새 searcher.py 를 요청한다.
       - LLM proposer(Gemini): 현재 코드 + 잔차 추이 + 지금까지 시도한 전략 대장을 주고
         "다음 개선을 추론해 searcher.py 전체를 다시 써라" 시킨다. (실제 '스스로 추론'.)
       - mock/deterministic proposer: 테스트/무-LLM 환경용 주입 가능.
  3. 후보를 적용하되 '가드'를 통과할 때만 채택한다 (apply_candidate):
       - gatekeeper.py 전체 통과 (G008 심판 무효화 금지, G009 심판 약화 금지,
         G010 능력 후퇴 금지 등). 실패하면 되돌리고 그 사유를 대장에 남긴다.
       - b=3 벤치 잔차가 기존 최고보다 '실제로' 낮아졌을 때만 커밋. 아니면 되돌린다.
  4. 채택/기각 결과를 improve_ledger.json 에 남겨 같은 실패를 반복하지 않게 한다.

대부분의 개선 아이디어는 실패한다(실측: reg 어닐링은 b=3 을 더 나쁘게 만들었다). 그래서
'제안'이 아니라 '검증된 채택'이 핵심이다 -- 나쁜 아이디어는 자동으로 되돌려지고 기록된다.

절대 규칙: 이 에이전트는 searcher.py 만 건드린다. verifier.py/게이트는 손대지 않는다
(그리고 gatekeeper 가 그것을 강제한다).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SEARCHER_PATH = HERE / "searcher.py"
HISTORY_PATH = HERE / "logs" / "history.jsonl"
LEDGER_PATH = HERE / "improve_ledger.json"

STAGNATION_WINDOW = 15      # 최근 몇 건을 보고 정체를 판단할지
IMPROVE_REL = 0.9           # 새 잔차가 기존 최고의 이 배수보다 낮아야 '개선'으로 인정
SOLVED_RES = 1e-6           # 이보다 낮으면 사실상 해결
BENCH_B, BENCH_M = 3, 23    # 개선 여부를 재는 벤치(난제 구간)
BENCH_RESTARTS = 4


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_ledger():
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text())
        except Exception:
            pass
    return {"best_bench_residual": None, "attempts": []}


def _write_ledger(led):
    LEDGER_PATH.write_text(json.dumps(led, ensure_ascii=False, indent=2))


def _recent_residuals(target_b, target_m, n=STAGNATION_WINDOW):
    if not HISTORY_PATH.exists():
        return []
    out = []
    for line in HISTORY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("b") == target_b and rec.get("m") == target_m and rec.get("als_residual") is not None:
            out.append(rec["als_residual"])
    return out[-n:]


def is_stagnant(led) -> bool:
    """벤치 목표에서 최근 잔차들이 기존 최고를 의미있게 못 넘으면 정체."""
    recents = _recent_residuals(BENCH_B, BENCH_M)
    if len(recents) < STAGNATION_WINDOW:
        return False
    best_prev = led.get("best_bench_residual")
    if best_prev is None:
        best_prev = min(recents)
        led["best_bench_residual"] = best_prev
    return min(recents) >= best_prev * IMPROVE_REL


def benchmark_residual(searcher_mod) -> float:
    """후보 searcher 로 벤치(b=3,m=23) 최소 잔차를 잰다."""
    T = searcher_mod.matmul_tensor(BENCH_B)
    best = 1.0
    for s in range(BENCH_RESTARTS):
        out = searcher_mod.cp_als(T, BENCH_M, iters=1500, seed=1000 + s)
        best = min(best, out[3])
        if best < SOLVED_RES:
            break
    return best


def _run_gatekeeper() -> tuple[bool, str]:
    res = subprocess.run(["python3", "gatekeeper.py"], cwd=REPO, capture_output=True, text=True)
    return res.returncode == 0, (res.stdout + res.stderr)[-1500:]


def apply_candidate(source_text: str, led) -> dict:
    """후보 searcher.py 를 가드 통과 시에만 채택한다. 결과 dict 반환."""
    backup = SEARCHER_PATH.read_text()
    SEARCHER_PATH.write_text(source_text)

    # 가드 1: 전체 게이트 (verifier 무효화/약화/능력 후퇴 금지).
    ok, summary = _run_gatekeeper()
    if not ok:
        SEARCHER_PATH.write_text(backup)
        return {"result": "gate_rejected", "detail": summary.strip()[-400:]}

    # 가드 2: 벤치가 실제로 개선됐는가.
    try:
        cand = _load_module("_cand_searcher", SEARCHER_PATH)
        res = benchmark_residual(cand)
    except Exception as e:
        SEARCHER_PATH.write_text(backup)
        return {"result": "candidate_error", "detail": str(e)[-400:]}

    best_prev = led.get("best_bench_residual")
    improved = res < SOLVED_RES or (best_prev is not None and res < best_prev * IMPROVE_REL)
    if not improved:
        SEARCHER_PATH.write_text(backup)
        return {"result": "no_improvement", "bench_residual": res, "best_prev": best_prev}

    # 채택: 커밋 + push.
    led["best_bench_residual"] = res
    subprocess.run(["git", "add", str(SEARCHER_PATH)], cwd=REPO, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", f"improve_agent: searcher 개선 채택 (b3 잔차 {res:.3e})"],
                   cwd=REPO, capture_output=True, text=True)
    push = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True)
    return {"result": "applied", "bench_residual": res, "pushed": push.returncode == 0}


def run_once(proposer) -> dict:
    """proposer: (context dict) -> 새 searcher.py 소스 문자열."""
    led = _read_ledger()
    if not is_stagnant(led):
        _write_ledger(led)
        return {"action": "none", "reason": "not_stagnant"}

    context = {
        "current_searcher": SEARCHER_PATH.read_text(),
        "recent_residuals": _recent_residuals(BENCH_B, BENCH_M),
        "best_bench_residual": led.get("best_bench_residual"),
        "tried": [a.get("strategy", "?") for a in led.get("attempts", [])],
        "constraints": [
            "b=2 m=7 는 순수 ALS 로 정확 수렴을 유지해야 한다 (G010 이 강제).",
            "verifier.py 와 gates/ 는 절대 수정하지 마라.",
            "cp_als/matmul_tensor/factors_to_scheme/propose 계약을 유지하라.",
            "searcher.py 전체 소스를 반환하라.",
        ],
    }
    source = proposer(context)
    if not source or "def propose" not in source:
        return {"action": "propose_failed"}

    outcome = apply_candidate(source, led)
    led.setdefault("attempts", []).append({
        "ts": time.time(),
        "strategy": (proposer.__name__ if hasattr(proposer, "__name__") else "proposer"),
        **outcome,
    })
    _write_ledger(led)
    return {"action": "attempted", **outcome}


def llm_proposer(context: dict) -> str:
    """Gemini 로 '다음 개선을 추론'해 searcher.py 전체를 다시 쓰게 한다.
    (VM 에서만 동작 -- GEMINI_API_KEY 필요. 여기서는 호출만 정의.)"""
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_FALLBACK")
    model = os.environ.get("IMPROVE_MODEL", "gemini-2.5-flash")
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=key)
    prompt = (
        "너는 행렬곱 텐서 분해 탐색기(searcher.py)를 개선하는 연구 에이전트다. "
        "b=3, m=23 정확 분해를 찾도록 CP-ALS 를 개선하되, 아래 제약을 반드시 지켜라.\n\n"
        f"[제약]\n" + "\n".join(f"- {c}" for c in context["constraints"]) + "\n\n"
        f"[벤치 최근 잔차 추이] {context['recent_residuals']}\n"
        f"[기존 최고 잔차] {context['best_bench_residual']}\n"
        f"[이미 시도해 실패/기각된 전략] {context['tried']}\n"
        "이전에 실패한 전략을 반복하지 마라. 예: 고정 reg 리지는 해를 편향시켜 정확 수렴을 막는다.\n"
        "고려할 수 있는 방향: reg 어닐링(0으로 점감), 비선형 최소제곱(Levenberg-Marquardt) 정제, "
        "basin hopping/섭동 재시작, restart 수 증가, 대칭성 활용.\n\n"
        "[현재 searcher.py]\n```python\n" + context["current_searcher"] + "\n```\n\n"
        "개선된 searcher.py '전체'를 하나의 코드블록으로만 출력하라. 설명 금지."
    )
    resp = llm.invoke(prompt)
    text = resp.content if isinstance(resp.content, str) else "".join(
        p.get("text", "") for p in resp.content if isinstance(p, dict))
    # 코드블록 추출
    if "```" in text:
        text = text.split("```", 2)[1]
        if text.startswith("python"):
            text = text[len("python"):]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["llm"], default="llm")
    args = parser.parse_args()
    proposer = llm_proposer
    result = run_once(proposer)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
