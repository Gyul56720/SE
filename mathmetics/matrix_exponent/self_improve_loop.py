"""
자가 수정 루프: searcher(ALS 탐색기)가 낸 후보를 '신뢰된' verifier 로 검증하고,
정직한 결과를 logs/history.jsonl 에 누적한다. 성공하면 searcher 를 다음 사다리 단으로 올린다.

- 판정은 언제나 verifier.py(신뢰·보호)가 한다. searcher 는 판정에 개입하지 못한다.
- searcher._als_residual 은 참고용으로 로그에만 남긴다(verifier 는 무시).
- 개선(더 낮은 omega)이면 best/ 에 스킴을 저장한다.
- --improve-every N 을 주면 N 회마다 improve_agent 를 불러 '정체하면 searcher 를 고치는'
  피드백 고리를 닫는다. 이게 없으면 이 루프는 같은 탐색기를 영원히 반복만 한다.

[2026-08-30] improve_agent.py 는 만들어진 뒤 한 번도 실행된 적이 없었다 -- 그것을 부르는
주체가 저장소 어디에도 없었고(systemd 유닛도, 워크플로도, 다른 모듈도), 산문으로만
존재했다. improve_ledger.json 이 없다는 것이 그 증거였다(run_once 는 정체가 아니어도
대장을 쓴다). gatekeeper.py 헤더에 적힌 그 실패가 그대로 재발한 셈이다: "진단이 마크다운에
남아 있을 뿐 실행 경로 어디에도 연결돼 있지 않았다." 그래서 자가개선을 별도 프로세스가
아니라 '이미 살아 있는 이 루프' 안에 얹는다 -- 실패 지점이 하나 적다.

CLAUDE.md 규칙에 따라 백그라운드로 오래 돌릴 때는 setsid+nohup 패턴을 쓸 것.
상시 구동은 deploy/se-matrix-search.service 가 담당한다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

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


def _best_omega():
    meta = BEST_DIR / "meta.json"
    if not meta.exists():
        return math.inf
    try:
        return json.loads(meta.read_text())["omega_eff"]
    except Exception:
        return math.inf


def _save_best(scheme, omega, ts):
    BEST_DIR.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in scheme.items() if not k.startswith("_")}
    (BEST_DIR / "scheme.py").write_text(
        "# verifier 로 검증된 최고 기록 스킴. 자동 생성물.\nSCHEME = " + repr(clean) + "\n",
        encoding="utf-8")
    (BEST_DIR / "meta.json").write_text(
        json.dumps({"omega_eff": omega, "b": scheme["b"], "m": scheme["m"], "ts": ts}, indent=2))


def run_once():
    ts = time.time()
    verifier = _load("_me_verifier", HERE / "verifier.py")
    searcher_mod = _load("_me_searcher", HERE / "searcher.py")
    searcher = searcher_mod.Searcher()

    b, m = searcher.current_target()
    scheme = searcher.propose()
    resid = scheme.get("_als_residual")
    try:
        ok, msg = verifier.verify_scheme(scheme)
    except Exception as e:
        ok, msg = False, f"verifier exception: {e}"

    record = {"ts": ts, "b": b, "m": m, "als_residual": resid}
    if ok:
        omega = verifier.effective_omega(scheme)
        record["omega_eff"] = omega
        record["status"] = "VERIFIED"
        if omega < _best_omega() - 1e-9:
            _save_best(scheme, omega, ts)
            record["status"] = "NEW_BEST"
        searcher.record(True)  # 다음(더 어려운) 단으로.
    else:
        record["status"] = "REJECTED"
        record["reason"] = msg
        searcher.record(False)

    _append_log(record)
    return record


def _try_improve(backend: str) -> dict:
    """improve_agent 를 한 번 돌린다. 자가개선이 죽어도 탐색 루프는 계속 돌아야 하므로
    어떤 예외도 여기서 삼키고 사유만 돌려준다."""
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
                        help="N 회 반복마다 improve_agent 를 호출한다. 0 이면 자가개선 없음.")
    parser.add_argument("--improve-backend", default="llm", choices=["llm", "mock"])
    args = parser.parse_args()

    i = 0
    while args.iterations == 0 or i < args.iterations:
        rec = run_once()
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        i += 1

        if args.improve_every > 0 and i % args.improve_every == 0:
            out = _try_improve(args.improve_backend)
            print(json.dumps({"improve": out}, ensure_ascii=False), flush=True)

        if (args.iterations == 0 or i < args.iterations) and args.sleep > 0:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
