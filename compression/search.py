"""
압축 코덱 자가개선 루프 -- orchestrator 가 코덱을 쓰고, judge 가 채택을 결정한다.

JPEG 을 사람이 설계한 자리에 탐색 루프를 놓는 것이다. 다만 무엇이 더 나은가를 LLM 이
판단하지 않는다. 판단은 compression/judge.py 가 한다 -- 코덱을 만든 쪽과 채점하는 쪽이
분리돼 있어야 "제안이 아니라 검증된 채택"이 성립한다(orchestrator/MANUAL.md 축 A).

한 라운드:
  1. 현재 챔피언의 소스와 점수를 문제 기술서에 싣는다.
  2. planner 가 코덱을 쓰는 DAG 를 만든다.
  3. **그 DAG 의 최종 노드 verifier 를 여기서 갈아끼운다** -- LLM 이 쓴 채점표를 버리고
     judge 를 쓰는 심판을 넣는다. plan_schema 의 verifier 가 경로 문자열이라 가능하다.
  4. drive() 가 실행->검증->수리 루프를 돈다. 노드 심판은 **design 셋**으로 채점한다.
  5. 통과한 코덱만 **holdout 셋**으로 다시 채점한다. 설계 과정이 본 적 없는 행렬이다.
  6. 챔피언을 두 축에서 모두 이겼을 때만 교체한다(래칫). 아니면 라운드를 버린다.

design/holdout 을 나누는 이유: 노드 심판이 채점하는 행렬로 최종 채택까지 결정하면, 그
행렬에만 좋은 코덱(상수 테이블을 박아넣은 것 등)이 챔피언이 된다. 탐색은 design 으로 하고
채택은 holdout 으로 한다.

래칫 규칙: 새 코덱은 bits/weight 와 함수오차 **둘 다** 챔피언보다 작아야 한다. 한 축만
좋아지는 교환(압축을 두 배로 하고 오차를 열 배로)은 채택하지 않는다 -- 그 교환을 허용하면
루프가 곧 3진 양자화로 굴러떨어져 멈춘다(ternary_b158 이 그 지점이다).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "orchestrator"))

import judge  # noqa: E402
import weights  # noqa: E402

CODECS = HERE / "codecs"
CHAMPION = CODECS / "champion.py"
LEDGER = HERE / "ledger.json"
RUNS = REPO / "orchestrator" / "runs"

# 노드 심판이 런 디렉토리에서 쓰는 파일. judge 를 그대로 부른다 -- LLM 은 이 파일을
# 보기만 하고 고칠 수 없다(repair_node 는 component 만 덮어쓴다).
NODE_VERIFIER = '''"""이 노드의 심판. LLM 이 쓴 것이 아니라 밖에서 주입된 것이다.
compression/judge.py 가 코덱을 격리 실행해 실제 blob 길이와 P(x)=P'(x) 오차를 잰다."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "__COMPRESSION__")
import judge
import weights

CHAMPION_BITS = __BITS__
CHAMPION_ERR = __ERR__


def check(output, inputs):
    code = output.get("codec_code")
    if not isinstance(code, str) or "def encode" not in code or "def decode" not in code:
        return False, "출력에 codec_code(encode/decode 를 정의한 파이썬 소스)가 없다"
    tmp = Path(tempfile.mkdtemp(prefix="codec_node_"))
    path = tmp / "candidate.py"
    path.write_text(code, encoding="utf-8")
    try:
        rows = []
        for name, W in weights.load("design"):
            try:
                rows.append(judge.score_tensor(path, name, W))
            except judge.CodecFailure as e:
                return False, f"실격({name}): {e}"
        bits = sum(r["bits_per_weight"] for r in rows) / len(rows)
        err = sum(r["func_err"] for r in rows) / len(rows)
        if bits >= CHAMPION_BITS:
            return False, f"압축력이 챔피언 이하다: {bits:.4f} >= {CHAMPION_BITS:.4f} bits/weight"
        if err >= CHAMPION_ERR:
            return False, f"복원력이 챔피언 이하다: 오차 {err:.6f} >= {CHAMPION_ERR:.6f}"
        return True, f"design 셋에서 챔피언을 이겼다: {bits:.4f} bits/weight, 오차 {err:.6f}"
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)
'''

PROBLEM = '''가중치 행렬을 압축하는 코덱을 설계하라. 지금 챔피언보다 **압축력과 복원력을
동시에** 개선해야 한다.

[출력] 최종 노드의 solve 는 {{"codec_code": "<파이썬 소스 전체>"}} 를 반환하라.
그 소스는 두 함수만 정의하면 된다:
    def encode(W: np.ndarray) -> bytes      # W 는 2차원 float32 행렬
    def decode(blob: bytes) -> np.ndarray   # 같은 모양의 float32 를 복원
decode 는 blob 말고 아무것도 받지 않는다. shape·스케일 등 복원에 필요한 모든 것을 blob 에
담아야 한다. 표준 라이브러리와 numpy 만 쓸 수 있다.

[채점] 채점은 네가 아니라 밖에 있는 심판이 한다. 심판은 코덱을 별도 프로세스에서
격리 실행하고 다음을 잰다:
  - 압축력: bits/weight = 8 * (실제 blob 바이트 수) / W.size   (네가 주장하는 값이 아니다)
  - 복원력: 무작위 X 에 대해 ||W@X - W'@X|| / ||W@X||          (행렬곱 출력이 보존되는가)
두 값이 **모두** 챔피언보다 작아야 통과다.

[실격 사유] 아래는 점수가 아니라 실격이다:
  - encode 와 decode 가 전역 변수/파일로 원본을 주고받는 것 (프로세스가 분리돼 있고
    decode 전에 원본 파일은 삭제된다)
  - 같은 입력에 매번 다른 blob 을 내는 것 (결정론적이어야 한다)
  - decode 가 원래 모양을 복원하지 못하는 것
  - encode 가 blob 외의 파일을 남기는 것

[현재 챔피언] {champion_name} -- {bits:.4f} bits/weight, 함수오차 {err:.6f}
소스:
```python
{source}
```

[힌트가 되는 사실]
  - int8 per-channel(max-abs 스케일)이 표준 기준선이다. 채널 안의 소수 큰 값이 그 채널의
    해상도를 잡아먹는다.
  - 스케일 자체도 저장 비용이다. 채널당 fp32 는 낭비일 수 있다.
  - 3진(1.6 bits/weight)은 압축력을 크게 이기지만 복원력에서 크게 진다. 한 축만 이기는
    것은 통과가 아니다.
  - 행렬곱 출력이 보존되는 것이 목표다. 가중치 자체의 오차가 아니라 W@X 의 오차다.

[규모] 각 노드의 solve 와 check 는 시간 예산 안에 끝나야 한다. 행렬은 수백 x 수백이고
평가 텐서는 여러 개다.
'''


def _load_ledger() -> dict:
    if LEDGER.is_file():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"champion": None, "history": []}


def _save_ledger(led: dict) -> None:
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_champion() -> Path:
    """챔피언이 없으면 int8 기준선으로 시작한다."""
    if not CHAMPION.is_file():
        shutil.copy2(CODECS / "int8.py", CHAMPION)
        led = _load_ledger()
        led["champion"] = {"from": "int8.py", "adopted_at": time.time()}
        _save_ledger(led)
    return CHAMPION


def champion_scores(split: str = "holdout") -> dict:
    res = judge.score_codec(ensure_champion(), split)
    return res["mean"]


def _plant_verifier(run_dir: Path, bits: float, err: float) -> str:
    """런 디렉토리에 주입 심판을 깔고 그 상대 경로를 돌려준다."""
    vdir = run_dir / "verifiers"
    vdir.mkdir(parents=True, exist_ok=True)
    body = (NODE_VERIFIER
            .replace("__COMPRESSION__", str(HERE))
            .replace("__BITS__", repr(float(bits)))
            .replace("__ERR__", repr(float(err))))
    (vdir / "codec_check.py").write_text(body, encoding="utf-8")
    return "verifiers/codec_check.py#check"


def _inject(run_dir: Path, verifier_rel: str) -> None:
    """계획의 **최종 노드** verifier 를 주입 심판으로 갈아끼운다."""
    path = run_dir / "plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    for node in plan["nodes"]:
        if node["id"] == plan["final"]:
            node["verifier"] = verifier_rel
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def one_round(max_repair_rounds: int = 3, node_timeout: float = 600.0) -> dict:
    """한 라운드: 계획 -> 심판 주입 -> 실행/수리 -> holdout 채점 -> 래칫."""
    import planner
    import solve as orch_solve

    champ = ensure_champion()
    design = judge.score_codec(champ, "design")["mean"]
    hold = judge.score_codec(champ, "holdout")["mean"]

    run_dir = RUNS / time.strftime("codec-%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    problem = PROBLEM.format(champion_name=champ.name, bits=design["bits_per_weight"],
                             err=design["func_err"], source=champ.read_text(encoding="utf-8"))

    plan_res = planner.make_plan(problem, str(run_dir))
    if plan_res.get("status") != "planned":
        return {"status": "planning_failed", "run_dir": str(run_dir), "detail": plan_res}

    verifier_rel = _plant_verifier(run_dir, design["bits_per_weight"], design["func_err"])
    _inject(run_dir, verifier_rel)

    run_res = orch_solve.drive(str(run_dir), max_repair_rounds=max_repair_rounds,
                               node_timeout=node_timeout)
    if run_res.get("status") != "solved":
        return {"status": "no_candidate", "run_dir": str(run_dir), "detail": run_res}

    code = (run_res.get("final_result") or {}).get("codec_code", "")
    cand = run_dir / "candidate.py"
    cand.write_text(code, encoding="utf-8")

    # 여기서부터가 채택 판정. design 이 아니라 holdout 으로 다시 잰다.
    try:
        final = judge.score_codec(cand, "holdout")["mean"]
    except judge.CodecFailure as e:
        return {"status": "rejected", "run_dir": str(run_dir), "reason": f"holdout 실격: {e}"}

    better = (final["bits_per_weight"] < hold["bits_per_weight"]
              and final["func_err"] < hold["func_err"])
    entry = {"ts": time.time(), "run_dir": str(run_dir), "adopted": better,
             "candidate": final, "champion_before": hold}
    led = _load_ledger()
    led["history"].append(entry)

    if not better:
        _save_ledger(led)
        return {"status": "rejected", "run_dir": str(run_dir),
                "reason": (f"holdout 에서 챔피언을 두 축으로 이기지 못했다: "
                           f"{final['bits_per_weight']:.4f} vs {hold['bits_per_weight']:.4f} "
                           f"bits, 오차 {final['func_err']:.6f} vs {hold['func_err']:.6f}"),
                "candidate": final}

    n = len([h for h in led["history"] if h["adopted"]])
    keep = CODECS / f"champion_v{n}.py"
    shutil.copy2(cand, keep)
    shutil.copy2(cand, CHAMPION)
    led["champion"] = {"from": keep.name, "adopted_at": time.time(), "scores": final}
    _save_ledger(led)
    return {"status": "adopted", "run_dir": str(run_dir), "champion": keep.name,
            "scores": final, "previous": hold}


def main() -> int:
    ap = argparse.ArgumentParser(description="압축 코덱 자가개선 루프")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--max-repair-rounds", type=int, default=3)
    ap.add_argument("--node-timeout", type=float, default=600.0)
    ap.add_argument("--status", action="store_true", help="현재 챔피언 점수만 보고 끝낸다")
    a = ap.parse_args()

    man = weights.manifest()
    if man["synthetic"]:
        print("⚠ 합성 가중치로 돌고 있다. 실제 코덱 성능이 아니다 -- "
              "`python3 compression/weights.py fetch` 를 먼저 돌려라.")

    if a.status:
        champ = ensure_champion()
        for split in ("design", "holdout"):
            m = judge.score_codec(champ, split)["mean"]
            print(f"챔피언 {champ.name} [{split}] {m['bits_per_weight']:.4f} bits/weight "
                  f"({m['compression_x']:.2f}x), 함수오차 {m['func_err']:.6f}")
        led = _load_ledger()
        print(f"채택 {len([h for h in led['history'] if h['adopted']])}회 / "
              f"시도 {len(led['history'])}회")
        return 0

    for i in range(1, a.rounds + 1):
        res = one_round(a.max_repair_rounds, a.node_timeout)
        print(f"[라운드 {i}] {res['status']} -- {res.get('reason') or res.get('champion') or ''}")
        if res["status"] == "adopted":
            s, p = res["scores"], res["previous"]
            print(f"  {p['bits_per_weight']:.4f} -> {s['bits_per_weight']:.4f} bits/weight, "
                  f"오차 {p['func_err']:.6f} -> {s['func_err']:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
