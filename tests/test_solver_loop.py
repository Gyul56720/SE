"""
자가 개선 루프의 red-green 증명 -- LLM 도 실제 데이터도 없이, 합성 데이터와 가짜 LLM 으로만.

이 루프의 주장은 하나다: "제안이 아니라 검증된 채택". LLM 이 낸 코드는 로컬 채점기에서
챔피언보다 엄격히 높을 때만 챔피언이 된다. 그 주장을 매번 다시 증명한다.

증명하는 것:
  1. 채점기가 옳다 -- 완벽한 예측은 1.0, 오배선·누락·거리 초과·과다 예측은 각각 깎인다.
     헝가리안 대체 구현이 완전탐색 최적과 일치한다(scipy 가 없는 환경을 위해).
  2. 베이스라인이 실제로 돈다 -- 합성 데이터에서 노드를 찾고 이어 붙여 채점 가능한 CSV 를 낸다.
  3. RED: 해법 코드가 solver/ 밖으로 복사되면 여전히 도는가. 실측으로 겪은 사고다 --
     baseline 이 solver/metric 을 상대 임포트하고 있어서, 후보로 복사되는 순간 전부
     ModuleNotFoundError 로 죽었다. 시딩은 제자리에서 돌아 성공하고 후보만 죽으므로
     "LLM 이 못 고친다"로 오독되기 딱 좋았다. 해법 코드는 자립해야 한다.
  4. 루프의 채택 규칙 -- 좋아진 후보는 채택, 나빠진 후보는 기각, 문법이 깨진 후보는 실행 전
     반려, 멈추지 않는 후보는 타임아웃으로 끊긴다.
  5. 진입점의 안전장치 -- 로컬 정답이 없으면 시작하지 않는다. 채점기 없이 도는 루프는
     개선이 아니라 표류이기 때문이다.

실행: python3 tests/test_solver_loop.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "solver"))
sys.path.insert(0, str(REPO / "orchestrator"))

import numpy as np                                   # noqa: E402
import llm_pool                                      # noqa: E402
import metric                                        # noqa: E402
import improve                                       # noqa: E402
import task as taskmod                               # noqa: E402


def _check(failures: list, cond: bool, label: str, detail: str = ""):
    print(f"    {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(f"{label}{': ' + detail if detail else ''}")


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def __call__(self, pool, prompt, pool_id="x"):
        self.prompts.append(prompt)
        return (self.replies.pop(0) if self.replies else ""), "fake:model"


def _with_fake(fake, fn):
    real = llm_pool.call
    llm_pool.call = fake
    try:
        return fn()
    finally:
        llm_pool.call = real


def make_synthetic(data_dir: Path) -> dict:
    """세포 3개가 이동하고 그중 하나가 t=2 에서 분열하는 5프레임 볼륨 + 정답."""
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3)
    T, Z, Y, X = 5, 24, 96, 96
    vol = rng.normal(20, 3, (T, Z, Y, X)).astype(np.float32)
    zz, yy, xx = np.ogrid[:Z, :Y, :X]

    def blob(v, z, y, x, amp=220):
        v += amp * np.exp(-(((zz - z) / 2.0) ** 2 + ((yy - y) / 3.0) ** 2
                            + ((xx - x) / 3.0) ** 2))

    seeds = {1: (12, 20, 20), 2: (12, 20, 70), 3: (10, 70, 25)}
    nodes, edges, nid, prev = {}, [], 1, {}
    for t in range(T):
        cur = {}
        for k, (z, y, x) in seeds.items():
            z, y, x = z + 0.4 * t, y + 1.2 * t, x + 0.9 * t
            blob(vol[t], z, y, x)
            nodes[nid] = (t, z, y, x)
            cur[k] = nid
            nid += 1
        if t >= 2:                                   # 3번 세포가 t=2 에서 분열
            z, y, x = 10 + 0.4 * t, 70 + 1.2 * t + 9, 25 + 0.9 * t + 9
            blob(vol[t], z, y, x)
            nodes[nid] = (t, z, y, x)
            cur[4] = nid
            nid += 1
        for k, v in cur.items():
            p = prev.get(k) or (prev.get(3) if k == 4 and t == 2 else None)
            if p:
                edges.append((p, v))
        prev = cur
    np.save(data_dir / "ds01.npy", vol)
    taskmod.write_submission(data_dir / "ground_truth.csv", {"ds01": (nodes, edges)})
    return {"nodes": nodes, "edges": edges}


def test_metric(failures: list):
    print("[채점기] 정답은 1.0, 오답은 깎인다")
    gt_nodes = {1: (0, 10, 10, 10), 2: (1, 10, 10, 10), 3: (1, 12, 20, 20),
                4: (2, 10, 10, 10), 5: (2, 12, 20, 20)}
    gt_edges = [(1, 2), (1, 3), (2, 4), (3, 5)]
    gt = metric.Tracks(gt_nodes, gt_edges)
    perfect = metric.Tracks(dict(gt_nodes), list(gt_edges))
    s = metric.score_sample(perfect, gt)
    _check(failures, abs(s["edge_jaccard"] - 1.0) < 1e-9, "완벽 예측 -> 1.0", str(s))
    _check(failures, (s["div_tp"], s["div_fn"]) == (1, 0), "분열 1건 TP")

    s = metric.score_sample(metric.Tracks(dict(gt_nodes), [(1, 2), (1, 3), (2, 5), (3, 5)]), gt)
    _check(failures, s["edge_fp"] == 1 and s["edge_fn"] == 1, "오배선 -> FP/FN", str(s))

    far = {k: (v[0], v[1] + 5, v[2], v[3]) for k, v in gt_nodes.items()}   # 8.125 µm
    s = metric.score_sample(metric.Tracks(far, list(gt_edges)), gt)
    _check(failures, s["matched_nodes"] == 0, "7 µm 밖은 매칭되지 않는다", str(s))

    spam = dict(gt_nodes)
    nid = 100
    for t in (0, 1, 2):
        for k in range(5):
            spam[nid] = (t, 60 + k, 200, 200)
            nid += 1
    s = metric.score_sample(metric.Tracks(spam, list(gt_edges)), gt)
    _check(failures, s["edge_jaccard_raw"] == 1.0 and abs(s["edge_jaccard"] - 5 / 20) < 1e-9,
           "과다 예측 페널티가 걸린다", str(s))

    # scipy 없는 환경을 위한 대체 헝가리안이 최적인가
    import itertools
    import random
    rng = random.Random(0)
    same = 0
    for _ in range(100):
        n, m = rng.randint(1, 5), rng.randint(1, 5)
        c = np.array([[rng.random() * 10 for _ in range(m)] for _ in range(n)])
        got = sum(c[i, j] for i, j in metric._hungarian(c))
        k = min(n, m)
        best = (min(sum(c[i, p[i]] for i in range(k)) for p in itertools.permutations(range(m), k))
                if n <= m else
                min(sum(c[p[j], j] for j in range(k)) for p in itertools.permutations(range(n), k)))
        same += abs(got - best) < 1e-9
    _check(failures, same == 100, f"대체 헝가리안 = 완전탐색 최적 100/100 (실제 {same})")


def test_baseline_is_self_contained(failures: list):
    """RED: 해법 코드가 solver/ 밖에서 실행돼도 도는가 (실측 사고의 회귀 방지)."""
    print("[베이스라인] solver/ 밖으로 복사해도 돈다")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        data = tmp / "train"
        make_synthetic(data)
        away = tmp / "elsewhere" / "candidate.py"
        away.parent.mkdir(parents=True)
        shutil.copy(REPO / "solver" / "baseline.py", away)
        out = tmp / "sub.csv"
        run = improve.run_candidate(away, data, out, timeout=180)
        _check(failures, run["ok"], "복사된 위치에서 실행 성공", str(run.get("error"))[:200])
        if not run["ok"]:
            return
        s = improve.evaluate(out, data / "ground_truth.csv")
        ps = s["per_dataset"]["ds01"]
        _check(failures, ps["matched_nodes"] == ps["gt_nodes"],
               f"정답 노드를 전부 찾는다 ({ps['matched_nodes']}/{ps['gt_nodes']})", str(ps))
        _check(failures, ps["edge_tp"] > 0, f"엣지를 실제로 잇는다 (TP={ps['edge_tp']})", str(ps))


def test_loop_adopts_only_better(failures: list):
    """루프: 좋아진 것만 채택. 나빠진 것·깨진 것·멈추지 않는 것은 각각 다르게 걸러진다."""
    print("[루프] 채택 규칙")
    base = (REPO / "solver" / "baseline.py").read_text(encoding="utf-8")
    better = ("# 가설: 과다 검출이 노드 페널티를 지배하므로 임계를 올린다\n"
              + base.replace("DETECT_PERCENTILE = 99.3", "DETECT_PERCENTILE = 99.93"))
    # 나빠지되 '빨리 끝나는' 변경이어야 기각 경로를 시험할 수 있다. 임계를 낮추면 검출이
    # 폭증해 타임아웃에 걸려버려서(실측) 연결 상한을 줄이는 쪽으로 바꿨다.
    worse = ("# 가설: 연결 상한을 줄이면 오연결이 준다\n"
             + base.replace("MAX_LINK_UM = 7.0", "MAX_LINK_UM = 0.1"))
    broken = "def solve(data_dir, out_csv:\n    pass"
    hang = "# 가설: 멈추지 않는다\nimport time\ndef solve(d, o):\n    time.sleep(9999)\n"
    noop = "# 가설: CSV 를 안 쓴다\ndef solve(d, o):\n    return None\n"

    with tempfile.TemporaryDirectory() as tmp:
        slug = "_test_loop"
        t = taskmod.Task(slug)
        t.dir = Path(tmp) / slug                     # 저장소를 더럽히지 않는다
        t.candidates = t.dir / "candidates"
        t.create("합성 과제", {"data_dir": str(Path(tmp) / "data"),
                              "candidate_timeout": 30, "sleep_between": 0})
        make_synthetic(Path(tmp) / "data" / "train")
        cfg = t.config()

        seed = improve._seed_baseline(t, cfg)
        t.append_history(seed)
        _check(failures, seed.get("adopted") and seed["combined"] > 0,
               f"베이스라인이 바닥을 만든다 ({seed.get('combined')})", str(seed.get("error")))

        fake = FakeLLM([better, worse, broken, hang, noop])
        recs = []
        for n in (1, 2, 3, 4, 5):
            r = _with_fake(fake, lambda: improve.one_iteration(t, cfg, n, ["fake"]))
            t.append_history(r)
            recs.append(r)

        _check(failures, recs[0]["adopted"] and recs[0]["combined"] > seed["combined"],
               f"더 좋은 후보는 채택 ({seed['combined']} -> {recs[0].get('combined')})", str(recs[0]))
        _check(failures, not recs[1]["adopted"] and recs[1]["combined"] is not None,
               "더 나쁜 후보는 기각(점수는 남긴다)", str(recs[1]))
        _check(failures, "문법 오류" in str(recs[2].get("error")),
               "문법이 깨진 후보는 실행 전 반려", str(recs[2].get("error")))
        _check(failures, "시간 초과" in str(recs[3].get("error")),
               "멈추지 않는 후보는 타임아웃으로 끊긴다", str(recs[3].get("error")))
        _check(failures, "제출 CSV" in str(recs[4].get("error")),
               "CSV 를 안 만든 후보는 그렇게 기록된다", str(recs[4].get("error")))

        champ = t.champion_score()
        _check(failures, abs(champ["combined"] - recs[0]["combined"]) < 1e-9,
               "챔피언은 가장 좋았던 후보로 남는다", str(champ.get("combined")))
        _check(failures, "가설:" in fake.prompts[1] and "임계를 올린다" in fake.prompts[1],
               "다음 프롬프트에 이전 시도의 가설이 실린다")
        _check(failures, len(list(t.candidates.glob("*.py"))) == 4,
               "실행된 후보 코드가 전부 보존된다(반려된 문법 오류 제외)",
               str(sorted(p.name for p in t.candidates.glob('*.py'))))


def test_start_refuses_without_ground_truth(failures: list):
    """진입점: 로컬 정답이 없으면 시작하지 않는다 -- 채점기 없는 루프는 표류다."""
    print("[진입점] 정답이 없으면 띄우지 않는다")
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.run([sys.executable, str(REPO / "solver" / "start.py"),
                            "합성 스모크", "--slug", "_test_start",
                            "--data-dir", str(Path(tmp) / "nodata")],
                           capture_output=True, text=True, timeout=120)
        out = p.stdout + p.stderr
        _check(failures, p.returncode == 3, f"종료 코드 3 (실제 {p.returncode})", out[-300:])
        _check(failures, "시작하지 않았다" in out, "시작하지 않았다고 분명히 말한다", out[-300:])
        _check(failures, "ground_truth.csv" in out, "무엇을 어디 둘지 알려준다", out[-300:])
        shutil.rmtree(taskmod.TASKS / "_test_start", ignore_errors=True)


def main() -> int:
    failures: list = []
    for t in (test_metric, test_baseline_is_self_contained,
              test_loop_adopts_only_better, test_start_refuses_without_ground_truth):
        t(failures)
    if failures:
        print("\n=== 실패 ===")
        for f in failures:
            print(" -", f)
        return 1
    print("\n자가 개선 루프가 red-green 을 통과했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
