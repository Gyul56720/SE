"""
자기 개선 에이전트: '다음 개선을 스스로 추론'해 searcher.py 를 고치되, 개선이 검증될
때만 채택하는 닫힌 피드백 루프.

self_improve_loop.py 는 searcher.py 를 실행/기록만 할 뿐, 정체를 인지해 코드를 바꾸는
주체가 없다(피드백 루프가 끊겨 있다). 이 에이전트가 그 고리를 잇는다:

  1. history.jsonl 을 읽어 '정체'(현재 전선에서 최근 시도들이 잔차를 못 낮춤)를 감지한다.
  2. 정체면 proposer 에게 새 searcher.py 를 요청한다.
       - LLM proposer(Gemini): 현재 코드 + 잔차 추이 + 지금까지 시도한 전략 대장을 주고
         "다음 개선을 추론해 searcher.py 전체를 다시 써라" 시킨다. (실제 '스스로 추론'.)
       - mock proposer: LLM 없이 전 경로(정체 감지→적용→게이트→벤치→롤백)를 돌려보는
         결정론적 백엔드. 테스트/무-API-키 환경용.
  3. 후보를 적용하되 '가드'를 통과할 때만 채택한다 (apply_candidate):
       - 계약 보존: matmul_tensor/cp_als/factors_to_scheme/propose/Searcher 가 있어야 한다.
       - gatekeeper.py 전체 통과 (G008 심판 무효화 금지, G009 심판 약화 금지,
         G010 능력 후퇴 금지 등). 실패하면 되돌리고 그 사유를 대장에 남긴다.
       - 현재 전선의 벤치 잔차가 기존 최고보다 '실제로' 낮아졌을 때만 커밋. 아니면 되돌린다.
  4. 채택/기각 결과를 improve_ledger.json 에 남겨 같은 실패를 반복하지 않게 한다.

대부분의 개선 아이디어는 실패한다(실측: reg 어닐링은 b=3 을 더 나쁘게 만들었다). 그래서
'제안'이 아니라 '검증된 채택'이 핵심이다 -- 나쁜 아이디어는 자동으로 되돌려지고 기록된다.

[2026-08-30 수정 이력 — 이 파일이 한 번도 실행된 적 없어 드러나지 않았던 결함들]

  (a) 벤치 대상이 하드코딩(b=3, m=23)이라 낡았다. m=23 은 이미 정복됐고(잔차 8.3e-10,
      VERIFIED) 전선은 m=22 로 올라갔는데, 정체 감지도 개선 측정도 여전히 m=23 을 보고
      있었다 -- 엉뚱한 목적함수를 최적화한다. => 사다리 상태(als_state.json)에서 현재
      전선을 읽는다.
  (b) 채택 게이트가 공허했다. `res < SOLVED_RES` 단독 통과 조건이 있는데 m=23 은 안정적으로
      1e-6 아래로 수렴하므로 사실상 '항상 참'이었다 -- LLM 이 뱉은 어떤 후보든 통과해
      자동 push 됐을 것이다. 이 파일의 존재 이유인 '검증된 채택'이 성립하지 않았다.
      => 전선을 벤치로 삼으면 이 조건은 '미해결 난제를 실제로 풀었다'는 뜻이 되어 의미를
      되찾는다. 거기에 기존 최고 대비 실질 개선을 함께 요구한다.
  (c) 한 번 채택되면 best 가 1e-10 이 되고, 이후 낡은 m=23 이력(~1e-2)과 비교하므로
      is_stagnant 가 '항상 True' -- 매 실행마다 무조건 LLM 호출. => 최고 잔차를 목표별로
      분리 보관하고(best_by_target), 정체 판단도 현재 전선 이력으로만 한다.
  (d) docstring 은 mock proposer 를 약속했지만 argparse 는 choices=["llm"] 뿐이라
      GEMINI_API_KEY 없이는 스모크 테스트조차 불가능했다. 그래서 한 번도 안 돌았고,
      그래서 (a)(b)(c) 가 안 잡혔다. (d) 가 나머지의 원인이다. => --backend mock 추가.
  (e) 벤치를 원시 cp_als 로 쟀다. 탐색기의 실력은 propose() 의 다단계 섭동에 들어
      있고, 비교 대상인 history.jsonl 잔차도 propose() 산물이라 단위가 안 맞았다.
      => 후보의 propose() 경로로 잰다(als_state.json 은 스냅샷 후 복원).

[이전 사다리 단 후퇴는 왜 따로 안 막는가]
b=2 m=7 은 benchmarks.json 에 등록돼 G010 이 매 커밋 강제한다. b=3 m=23 은 별도 가드를
두지 않는다 -- 랭크 22 분해가 존재하면 0 인 랭크-1 항을 하나 붙여 랭크 23 분해가 항상
따라오므로, 전선(m=22)에서의 개선이 m=23 능력을 후퇴시킬 수 없다. 게다가 m=23 은 707 회
시도 끝에 한 번 맞은 것이라 게이트가 감당할 예산으로 재현 가능하지 않다(G010 에 넣으면
모든 커밋이 막힌다).

절대 규칙: 이 에이전트는 searcher.py 만 건드린다. verifier.py/게이트는 손대지 않는다
(그리고 gatekeeper 가 그것을 강제한다).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SEARCHER_PATH = HERE / "searcher.py"
STATE_PATH = HERE / "als_state.json"
HISTORY_PATH = HERE / "logs" / "history.jsonl"
LEDGER_PATH = HERE / "improve_ledger.json"

STAGNATION_WINDOW = 15      # 최근 몇 건을 보고 정체를 판단할지
IMPROVE_REL = 0.9           # 새 잔차가 기존 최고의 이 배수보다 낮아야 '개선'으로 인정
SOLVED_RES = 1e-6           # 이보다 낮으면 사실상 해결
BENCH_TRIALS = 5            # 후보를 몇 번 propose() 시켜 볼지 (최소 잔차 채택)
# 벤치에 쓸 '고정' attempt 값들. searcher.propose() 는 attempt 로 seed 를 만들므로, 이걸
# 고정하면 벤치가 결정적이 되고 기존 판과 후보가 '같은 시드'로 짝지어 비교된다.
BENCH_ATTEMPTS = (0, 1, 2, 3, 4)
LEDGER_VERSION = 3

# searcher.py 가 지켜야 하는 계약. 하나라도 없으면 self_improve_loop / G010 이 깨진다.
SEARCHER_CONTRACT = ("matmul_tensor", "cp_als", "factors_to_scheme", "propose", "Searcher")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_ledger() -> dict:
    if LEDGER_PATH.exists():
        try:
            led = json.loads(LEDGER_PATH.read_text())
        except Exception:
            led = {}
    else:
        led = {}
    if led.get("version") != LEDGER_VERSION:
        # v1 은 목표 구분 없는 단일 best_bench_residual 을 썼다 -- 낡은 m=23 기준이라
        # 이월하지 않고 버린다(이월하면 결함 (c) 가 그대로 살아난다). 시도 이력은 남긴다.
        # v2 의 best_by_target 도 버린다: 정체 판정이 '확률적 루프 이력의 최소값'을 그 칸에
        # 덮어써서 결정적 벤치와 단위가 섞여 있었다(아래 is_stagnant 주석 참고). 오염된
        # 기준선을 이월하면 그 결함이 그대로 남는다.
        led = {"version": LEDGER_VERSION, "best_by_target": {}, "best_seen_by_target": {},
               "attempts": led.get("attempts", [])}
    led.setdefault("best_by_target", {})
    led.setdefault("best_seen_by_target", {})
    led.setdefault("attempts", [])
    return led


def _write_ledger(led):
    LEDGER_PATH.write_text(json.dumps(led, ensure_ascii=False, indent=2))


def _target_key(b, m) -> str:
    return f"{b},{m}"


def frontier_target() -> tuple:
    """현재 사다리 전선 (b, m). als_state.json 의 stage 를 그대로 따른다."""
    mod = _load_module("_frontier_searcher", SEARCHER_PATH)
    return tuple(mod.Searcher().current_target())


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


def incumbent_bench(led, b, m) -> float:
    """지금 저장소에 있는 searcher.py 의 '결정적' 벤치값. 후보는 이것과 겨룬다.

    없으면 그 자리에서 재보고 기록한다. 채택이 일어날 때만 갱신되므로, 확률적 루프 이력에
    오염되지 않는다(아래 is_stagnant 주석 참고)."""
    key = _target_key(b, m)
    val = led["best_by_target"].get(key)
    if val is None:
        mod = _load_module("_incumbent_searcher", SEARCHER_PATH)
        val = benchmark_residual(mod)
        led["best_by_target"][key] = val
    return val


def is_stagnant(led, b, m) -> bool:
    """전선에서 최근 잔차들이 '지금까지 본 최소'를 의미있게 못 넘으면 정체.

    기준선이 아직 없으면 이번 호출로 세우기만 하고 정체로 보지 않는다 -- 비교 대상 없이
    첫 호출부터 LLM 을 부르는 낭비를 막는다.

    [왜 best_by_target 이 아니라 별도의 best_seen_by_target 을 쓰는가]
    예전에는 이 함수가 best_by_target 을 덮어썼다. 그런데 그 칸은 apply_candidate 가
    후보를 판정할 때 쓰는 '결정적 벤치' 기준선이다. 반면 여기서 넣는 값은 self_improve_loop
    가 남긴 '확률적 propose() 이력의 최근 15 개 중 최소'다 -- 서로 다른 척도의 값이 같은
    칸에 섞였다.

    운영 서버 실측(2026-08-30)이 그 결과를 그대로 보여줬다. 기준선을 결정적 벤치값
    0.012777 로 재설정했는데, 루프가 우연히 0.010065 를 뽑자 is_stagnant 가 그 값으로
    기준선을 덮어썼다. 그 순간 채택 문턱이 0.010065 x 0.9 = 0.00906 이 됐다 -- 현직
    searcher 의 실제 벤치값은 여전히 0.012777 이므로, 후보는 의도한 10% 가 아니라 29% 를
    개선해야 통과하게 된다. 게다가 그 문턱은 루프의 운에 따라 계속 흔들린다. 결정적 벤치를
    도입해 없앤 '운이 판정하는' 문제가 다른 경로로 되살아난 셈이다.

    그래서 두 값을 분리한다:
      best_by_target      -- 결정적 벤치 기준선. 채택될 때만 갱신된다.
      best_seen_by_target -- 루프 이력에서 본 최소. 정체 판정에만 쓴다.

    [last_check 를 남기는 이유]
    정체가 아니면 run_once 는 attempts 에 아무것도 남기지 않는다. 그래서 대장만 보면
    "attempts 가 비었다"는 사실이 '한 번도 안 돌았다'인지 '돌았지만 정체가 아니었다'인지
    구분되지 않는다 -- 실제로 이 저장소에서 두 번 오독됐다(2026-08-30: 서버가 best_by_target
    한 줄만 바꾼 커밋을 올렸는데 attempts 가 비어 있어 'LLM 이 실패했다'로 읽혔지만, 실제로는
    정체 판정에서 매번 되돌아 나가 LLM 에 도달한 적이 없었다). 매 판정의 근거를 last_check
    에 남기면 대장 하나만 보고도 '돌았는가 / 왜 제안하지 않았는가'를 알 수 있다.
    """
    key = _target_key(b, m)
    now = time.time()
    led["checks"] = led.get("checks", 0) + 1

    recents = _recent_residuals(b, m)
    if len(recents) < STAGNATION_WINDOW:
        led["last_check"] = {"ts": now, "target": key, "stagnant": False,
                             "reason": "표본 부족", "samples": len(recents),
                             "need": STAGNATION_WINDOW}
        return False

    observed = min(recents)
    seen_prev = led["best_seen_by_target"].get(key)
    if seen_prev is None:
        led["best_seen_by_target"][key] = observed
        led["last_check"] = {"ts": now, "target": key, "stagnant": False,
                             "reason": "기준선 수립(첫 판정)", "observed": observed}
        return False

    stagnant = observed >= seen_prev * IMPROVE_REL
    led["last_check"] = {
        "ts": now, "target": key, "stagnant": stagnant,
        "reason": "정체" if stagnant else "아직 개선 중",
        "observed": observed, "best_seen_prev": seen_prev,
        "threshold": seen_prev * IMPROVE_REL,
    }
    if observed < seen_prev:
        led["best_seen_by_target"][key] = observed
    return stagnant


def benchmark_residual(searcher_mod, trials=BENCH_TRIALS) -> float:
    """후보 searcher 의 실제 탐색 경로(propose)로 전선 최소 잔차를 잰다.

    원시 cp_als 가 아니라 propose() 를 쓰는 이유: 탐색기의 실력은 propose() 안의 재시작·
    섭동 전략에 들어 있고, 비교 기준인 history.jsonl 잔차도 propose() 가 낸 값이다.
    propose() 는 als_state.json 을 전진시키므로 스냅샷 후 복원한다.

    [왜 시드를 고정하는가 -- 채택 게이트를 실제로 작동하게 만드는 부분]
    예전에는 이 함수가 propose() 를 '그냥' 여러 번 불러 최소값을 썼다. propose() 는
    확률적이라 그 최소값의 편차가 채택 문턱보다 훨씬 컸다 -- 실측(2026-08-30, b=3 m=22):
    min-of-3 이 0.0104 ~ 0.1925 로 18.5 배 출렁였는데 채택 문턱은 '기존 최고의 0.9 배',
    즉 10% 개선이었다. 대장의 기존 최고 0.0254 기준 문턱 0.0229 아래로 7 회 중 6 회가
    떨어졌다. 다시 말해 코드를 한 줄도 바꾸지 않은 후보(mock_proposer 는 현재 소스를
    그대로 돌려준다)조차 운만으로 '개선됨' 판정을 받아 자동 커밋·push 될 수 있었다.
    측정 노이즈가 신호보다 크면 그 게이트는 개선을 고르는 게 아니라 운을 고른다.

    searcher.propose() 는 als_state.json 의 attempt 로 seed 를 만든다. 그래서 attempt 를
    고정된 집합(BENCH_ATTEMPTS)으로 못박으면 벤치가 결정적이 되고, 기존 판과 후보가
    '같은 시드'로 짝지어 비교된다 -- 같은 코드는 항상 같은 값을 내므로 no_improvement 가
    보장되고, 통과했다면 그건 운이 아니라 실제 개선이다.
    """
    snapshot = STATE_PATH.read_text() if STATE_PATH.exists() else None
    try:
        try:
            base_state = json.loads(snapshot) if snapshot else {"stage": 0, "attempt": 0}
        except Exception:
            base_state = {"stage": 0, "attempt": 0}

        best = 1.0
        for attempt in BENCH_ATTEMPTS[:trials]:
            pinned = dict(base_state)
            pinned["attempt"] = attempt
            STATE_PATH.write_text(json.dumps(pinned, indent=2))
            scheme = searcher_mod.Searcher().propose()
            res = scheme.get("_als_residual")
            if res is not None:
                best = min(best, float(res))
            if best < SOLVED_RES:
                break
        return best
    finally:
        if snapshot is None:
            STATE_PATH.unlink(missing_ok=True)
        else:
            STATE_PATH.write_text(snapshot)


def _run_gatekeeper() -> tuple:
    res = subprocess.run(["python3", "gatekeeper.py"], cwd=REPO, capture_output=True, text=True)
    return res.returncode == 0, (res.stdout + res.stderr)[-1500:]


def _current_branch() -> str:
    res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                         cwd=REPO, capture_output=True, text=True)
    return res.stdout.strip() or "HEAD"


def _missing_contract(mod) -> list:
    return [fn for fn in SEARCHER_CONTRACT if not hasattr(mod, fn)]


def apply_candidate(source_text: str, led, b, m) -> dict:
    """후보 searcher.py 를 가드 통과 시에만 채택한다. 결과 dict 반환."""
    key = _target_key(b, m)
    # 기준선은 반드시 후보를 덮어쓰기 '전에' 잰다 -- 아래 write_text 뒤에 재면 현직이
    # 아니라 후보 자신을 재게 되고, 후보는 언제나 자기 자신과 비교돼 통과하지 못한다.
    best_prev = incumbent_bench(led, b, m)
    backup = SEARCHER_PATH.read_text()
    SEARCHER_PATH.write_text(source_text)

    def rollback(result: dict) -> dict:
        SEARCHER_PATH.write_text(backup)
        return result

    # 가드 1: 계약 보존 (임포트 가능하고, 루프/게이트가 부르는 이름이 다 있는가).
    try:
        cand = _load_module("_cand_searcher", SEARCHER_PATH)
    except Exception as e:
        return rollback({"result": "candidate_error", "detail": str(e)[-400:]})
    missing = _missing_contract(cand)
    if missing:
        return rollback({"result": "contract_broken", "detail": f"없는 이름: {', '.join(missing)}"})

    # 가드 2: 전체 게이트 (verifier 무효화/약화/능력 후퇴 금지).
    ok, summary = _run_gatekeeper()
    if not ok:
        return rollback({"result": "gate_rejected", "detail": summary.strip()[-400:]})

    # 가드 3: 전선 벤치가 실제로 개선됐는가.
    try:
        res = benchmark_residual(cand)
    except Exception as e:
        return rollback({"result": "candidate_error", "detail": str(e)[-400:]})

    solved = res < SOLVED_RES
    improved = solved or (best_prev is not None and res < best_prev * IMPROVE_REL)
    if not improved:
        return rollback({"result": "no_improvement", "target": key,
                         "bench_residual": res, "best_prev": best_prev})

    # 채택: 커밋 + push.
    led["best_by_target"][key] = res
    _write_ledger(led)
    branch = _current_branch()
    # 대장(improve_ledger.json)은 커밋하지 않는다 -- 서버가 매 실행마다 쓰는 기계 로컬
    # 런타임 상태라 .gitignore 대상이다(als_state.json / logs 와 같은 부류). 추적하면
    # 배포의 작업 트리 정렬이 서버의 대장을 매번 덮어써 '이미 실패한 전략' 기억이 조용히
    # 사라진다. 채택의 기록은 아래 커밋(searcher.py 변경 + 메시지)이 남긴다.
    subprocess.run(["git", "add", str(SEARCHER_PATH)],
                   cwd=REPO, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m",
                    f"improve_agent: searcher 개선 채택 (b={b} m={m} 잔차 {res:.3e})"],
                   cwd=REPO, capture_output=True, text=True)
    push = subprocess.run(["git", "push", "-u", "origin", branch],
                          cwd=REPO, capture_output=True, text=True)
    return {"result": "applied", "target": key, "bench_residual": res,
            "solved": solved, "pushed": push.returncode == 0}


def run_once(proposer) -> dict:
    """proposer: (context dict) -> 새 searcher.py 소스 문자열."""
    led = _read_ledger()
    try:
        b, m = frontier_target()
    except Exception as e:
        return {"action": "error", "detail": f"전선을 읽지 못했다: {e}"}

    if not is_stagnant(led, b, m):
        _write_ledger(led)
        return {"action": "none", "reason": "not_stagnant", "target": _target_key(b, m)}

    context = {
        "b": b,
        "m": m,
        "current_searcher": SEARCHER_PATH.read_text(),
        "recent_residuals": _recent_residuals(b, m),
        # 프롬프트에는 후보가 실제로 넘어야 할 '결정적' 기준선을 준다. 여기서 재두면
        # apply_candidate 가 후보를 덮어쓰기 전에 현직 값이 대장에 확정되기도 한다.
        "best_bench_residual": incumbent_bench(led, b, m),
        "tried": [a.get("note") or a.get("result") for a in led["attempts"]],
        # 제약은 게이트가 '실제로' 강제하는 것만 적는다. 예전 문구는 "b=2 m=7 는 순수 ALS 로
        # 정확 수렴을 유지해야 한다"였는데, G010 은 순수 ALS 를 요구한 적이 없다 --
        # cp_als(T, m, iters=, seed=) 로 불러 잔차가 1e-9 아래로 내려가는지만 본다. 현재
        # searcher 자체가 순수 ALS 가 아니라 감쇠 어닐링 + 연마인데도 통과한다. 실제보다
        # 좁은 제약을 주면 알고리즘을 고치라고 부르고선 고치지 못하게 막는 꼴이 된다.
        # 또 b=3 m=23 이 래칫에 추가됐는데 제약에 빠져 있어, 그걸 깨뜨린 후보가 이유도
        # 모른 채 gate_rejected 를 맞을 수 있었다.
        "constraints": [
            "cp_als(T, m, iters=..., seed=...) 호출 규약을 유지하라 -- G010 이 이 시그니처로 직접 부른다.",
            "능력 래칫: b=2 m=7 (seeds 12 x iters 2000) 과 b=3 m=23 (seeds 8 x iters 1500) 이 "
            "각각 잔차 1e-9 미만으로 수렴해 verifier 를 통과해야 한다. 이 둘만 지키면 cp_als "
            "내부 알고리즘은 무엇으로든 바꿔도 된다 -- 현재 판도 순수 ALS 가 아니라 감쇠 "
            "어닐링 + 연마다.",
            "verifier.py 와 gates/ 는 절대 수정하지 마라.",
            "matmul_tensor/cp_als/factors_to_scheme/propose/Searcher 이름을 모두 유지하라.",
            "searcher.py 전체 소스를 반환하라.",
        ],
    }
    source = proposer(context)
    if not source or "def propose" not in source:
        return {"action": "propose_failed", "target": _target_key(b, m)}

    outcome = apply_candidate(source, led, b, m)
    led["attempts"].append({
        "ts": time.time(),
        "backend": getattr(proposer, "__name__", "proposer"),
        "target": _target_key(b, m),
        **outcome,
    })
    _write_ledger(led)
    return {"action": "attempted", **outcome}


def mock_proposer(context: dict) -> str:
    """LLM 없이 전 경로를 돌려보는 결정론적 백엔드.

    현재 소스를 그대로 돌려준다 -- 계약·게이트는 통과하고 벤치는 개선되지 않으므로
    'no_improvement 후 롤백'까지가 정상 결과다. 즉 이 백엔드로 run_once 를 돌리면
    정체 감지 → 적용 → 가드 3종 → 롤백 → 대장 기록의 전 경로가 검증된다.
    """
    return context["current_searcher"]


def llm_proposer(context: dict) -> str:
    """Gemini 로 '다음 개선을 추론'해 searcher.py 전체를 다시 쓰게 한다.
    (VM 에서만 동작 -- GEMINI_API_KEY 필요.)"""
    import os

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_FALLBACK")
    # 모델 이름을 코드에 박지 않고, 하나만 고르지도 않는다.
    #   - 박아두면 모델이 바뀔 때 조용히 404 난다(기본값이 gemini-2.5-flash 였는데 이
    #     계정엔 2.5 계열이 없었다).
    #   - 하나만 고르면 그게 무료 티어에서 못 쓰는 유료 전용 모델일 때 매번 실패한다.
    #     ListModels 는 pro 계열도 나열하고 품질 순위상 pro 가 1 순위라 반드시 그걸 고른다
    #     (실측 2026-08-30: gemini-3.1-pro / -pro-preview 에서 RESOURCE_EXHAUSTED).
    # bot_tools.invoke_text 가 후보를 순회하며 못 쓰는 조합을 quota_tracker 에 기록하고
    # 건너뛴다 -- 에이전트 경로가 쓰는 fallback 과 같은 방식이다.
    sys.path.insert(0, str(REPO))
    import bot_tools

    model = os.environ.get("IMPROVE_MODEL")  # 명시하면 그 모델만 쓴다
    b, m = context["b"], context["m"]
    prompt = (
        "너는 행렬곱 텐서 분해 탐색기(searcher.py)를 개선하는 연구 에이전트다. "
        f"b={b}, m={m} 정확 분해를 찾도록 탐색 전략을 개선하되, 아래 제약을 반드시 지켜라.\n\n"
        "[제약]\n" + "\n".join(f"- {c}" for c in context["constraints"]) + "\n\n"
        f"[전선 최근 잔차 추이] {context['recent_residuals']}\n"
        f"[기존 최고 잔차] {context['best_bench_residual']}\n"
        f"[이미 시도해 실패/기각된 전략] {context['tried']}\n"
        "이전에 실패한 전략을 반복하지 마라. 예: 고정 reg 리지는 해를 편향시켜 정확 수렴을 막는다.\n"
        "현재 판에 이미 들어 있는 것(다시 제안하지 마라): 감쇠 어닐링 ALS, 열 균형화, "
        "반올림-리프팅, 정확해 분지 진입 후 연마, 예산 분할 다중 재시작.\n"
        "고려할 수 있는 방향: 비선형 최소제곱(Levenberg-Marquardt) 정제, 분지 이탈 전략, "
        "텐서의 순환 대칭성 활용, 그 밖에 잔차 추이에서 네가 읽어낸 것.\n\n"
        "[현재 searcher.py]\n```python\n" + context["current_searcher"] + "\n```\n\n"
        "개선된 searcher.py '전체'를 하나의 코드블록으로만 출력하라. 설명 금지."
    )
    text = bot_tools.invoke_text(prompt, key, model=model,
                                 pool_id="improve-agent", log_prefix="[improve_agent]")
    # 코드블록 추출
    if "```" in text:
        text = text.split("```", 2)[1]
        if text.startswith("python"):
            text = text[len("python"):]
        text = text.rsplit("```", 1)[0]
    return text.strip()


BACKENDS = {"llm": llm_proposer, "mock": mock_proposer}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=sorted(BACKENDS), default="llm")
    args = parser.parse_args()
    result = run_once(BACKENDS[args.backend])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
