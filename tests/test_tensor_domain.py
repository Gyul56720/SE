"""
텐서 rank 도메인의 red-green -- 오라클이 데이터가 아니라 '수학적 정의'인 경우의 증명.

세포 추적은 심판이 ground_truth.csv(데이터)였다. 여기서는 심판이 n×n 행렬곱 텐서의 정의다.
n 만 주면 정답이 유일하게 결정되므로 외부 데이터 없이 돈다 -- 그것이 이 도메인을 이 구조에
가장 잘 맞게 만든다(자율 공격에 정답이 없다는 지적의 반대편: 여기엔 위조 불가 정답이 있다).

증명하는 것:
  1. 오라클이 옳다 -- 표준 알고리즘(rank n^3)은 통과하고 score 1.0, Strassen(2x2 rank 7)은
     통과하고 더 높은 점수, 틀린 분해는 0점(부분점수 없음 -- float 근사로 못 속인다).
  2. 루프가 도메인 무관하다 -- 같은 improve 루프가 scorer 만 갈아끼워 텐서 도메인을 돈다.
     베이스라인(표준)을 바닥으로 깔고, Strassen 후보를 채택하고, 틀린 rank 축소는 기각한다.

실행: python3 tests/test_tensor_domain.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "solver"))
sys.path.insert(0, str(REPO / "solver" / "domains"))
sys.path.insert(0, str(REPO / "orchestrator"))

import llm_pool                                      # noqa: E402
import improve                                       # noqa: E402
import task as taskmod                               # noqa: E402
import tensor_rank as TR                             # noqa: E402


def _check(failures, cond, label, detail=""):
    print(f"    {'OK  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(f"{label}{': ' + detail if detail else ''}")


def _standard_rows(n):
    rows, r = [], 0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                a, b, c = i * n + k, k * n + j, i * n + j
                rows += [{"kind": "U", "r": r, "i": a, "j": -1, "val": 1},
                         {"kind": "V", "r": r, "i": b, "j": -1, "val": 1},
                         {"kind": "W", "r": r, "i": c, "j": -1, "val": 1},
                         {"kind": "lambda", "r": r, "i": -1, "j": -1, "val": 1}]
                r += 1
    return rows


STRASSEN = [
    ({0: 1, 3: 1}, {0: 1, 3: 1}, {0: 1, 3: 1}),
    ({2: 1, 3: 1}, {0: 1}, {2: 1, 3: -1}),
    ({0: 1}, {1: 1, 3: -1}, {1: 1, 3: 1}),
    ({3: 1}, {2: 1, 0: -1}, {0: 1, 2: 1}),
    ({0: 1, 1: 1}, {3: 1}, {0: -1, 1: 1}),
    ({2: 1, 0: -1}, {0: 1, 1: 1}, {3: 1}),
    ({1: 1, 3: -1}, {2: 1, 3: 1}, {0: 1}),
]


def _strassen_rows():
    rows = []
    for r, (u, v, w) in enumerate(STRASSEN):
        for i, val in u.items():
            rows.append({"kind": "U", "r": r, "i": i, "j": -1, "val": val})
        for i, val in v.items():
            rows.append({"kind": "V", "r": r, "i": i, "j": -1, "val": val})
        for i, val in w.items():
            rows.append({"kind": "W", "r": r, "i": i, "j": -1, "val": val})
        rows.append({"kind": "lambda", "r": r, "i": -1, "j": -1, "val": 1})
    return rows


def test_oracle(failures):
    print("[오라클] 표준=1.0, Strassen>1.0, 틀린 분해=0")
    s = TR.score_decomposition(_standard_rows(2), 2)
    _check(failures, s["valid"] and s["rank"] == 8 and abs(s["score"] - 1.0) < 1e-12,
           "2x2 표준 rank=8 -> score 1.0", str(s))
    s = TR.score_decomposition(_standard_rows(3), 3)
    _check(failures, s["valid"] and s["rank"] == 27, "3x3 표준 rank=27 통과", str(s))

    s = TR.score_decomposition(_strassen_rows(), 2)
    _check(failures, s["valid"] and s["rank"] == 7 and s["score"] > 1.0 and s["beats_standard"],
           f"Strassen rank=7 통과, score {s.get('score')}", str(s))

    s = TR.score_decomposition(_standard_rows(2)[:-4], 2)
    _check(failures, s["score"] == 0.0 and not s["valid"], "불완전 분해 -> 0", str(s))
    almost = _standard_rows(2)
    almost[0] = {"kind": "U", "r": 0, "i": 0, "j": -1, "val": "1/2"}
    s = TR.score_decomposition(almost, 2)
    _check(failures, s["score"] == 0.0, "계수 하나만 틀려도 0 (정확 산술, 근사 불가)", str(s))


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def __call__(self, pool, prompt, pool_id="x"):
        self.prompts.append(prompt)
        return (self.replies.pop(0) if self.replies else ""), "fake:model"


def test_loop_on_tensor(failures):
    print("[루프] 같은 improve 루프가 텐서 도메인을 돈다")
    strassen_code = (
        "# 가설: 표준 8곱을 Strassen 7곱으로 결합해 rank 를 1 줄인다\n"
        "import csv, json, os\n"
        "def solve(data_dir, out_csv):\n"
        "    json.load(open(os.path.join(data_dir,'config.json')))\n"
        "    terms = " + repr(STRASSEN) + "\n"
        "    rows=[('kind','r','i','j','val')]\n"
        "    for r,(u,v,w) in enumerate(terms):\n"
        "        for i,val in u.items(): rows.append(('U',r,i,-1,val))\n"
        "        for i,val in v.items(): rows.append(('V',r,i,-1,val))\n"
        "        for i,val in w.items(): rows.append(('W',r,i,-1,val))\n"
        "        rows.append(('lambda',r,-1,-1,1))\n"
        "    csv.writer(open(out_csv,'w',newline='')).writerows(rows)\n")
    wrong_code = (
        "# 가설: 근거 없이 rank 6 으로 줄여본다\n"
        "import csv\n"
        "def solve(data_dir, out_csv):\n"
        "    rows=[('kind','r','i','j','val')]\n"
        "    for r in range(6):\n"
        "        rows += [('U',r,0,-1,1),('V',r,0,-1,1),('W',r,0,-1,1),('lambda',r,-1,-1,1)]\n"
        "    csv.writer(open(out_csv,'w',newline='')).writerows(rows)\n")

    with tempfile.TemporaryDirectory() as tmp:
        t = taskmod.Task("_tensor_test")
        t.dir = Path(tmp) / "task"
        t.candidates = t.dir / "candidates"
        t.create("2x2 최소 rank", {"data_dir": str(Path(tmp) / "data"),
                                   "scorer": "tensor_rank", "n": 2,
                                   "candidate_timeout": 60, "sleep_between": 0})
        seed = Path(tmp) / "data" / "train"
        seed.mkdir(parents=True)
        (seed / "config.json").write_text(json.dumps({"n": 2}))
        cfg = t.config()

        s0 = improve._seed_baseline(t, cfg)
        t.append_history(s0)
        _check(failures, s0["adopted"] and abs(s0["combined"] - 1.0) < 1e-9,
               f"베이스라인=표준 rank 8, score 1.0 ({s0.get('combined')})", str(s0.get("error")))

        real = llm_pool.call
        llm_pool.call = FakeLLM([strassen_code, wrong_code])
        try:
            r1 = improve.one_iteration(t, cfg, 1, ["fake"])
            t.append_history(r1)
            r2 = improve.one_iteration(t, cfg, 2, ["fake"])
            t.append_history(r2)
        finally:
            llm_pool.call = real

        _check(failures, r1["adopted"] and r1["combined"] > 1.0,
               f"Strassen 후보 채택 (1.0 -> {r1.get('combined')})", str(r1))
        _check(failures, r1.get("detail", {}).get("rank") == 7, "채택된 rank=7",
               str(r1.get("detail", {}).get("rank")))
        _check(failures, not r2["adopted"] and r2["combined"] == 0.0,
               "틀린 rank 축소는 0점 기각", str(r2))
        cs = t.champion_score()
        _check(failures, cs["rank"] == 7 and cs["beats_standard"],
               "챔피언은 Strassen(표준을 이김)", str(cs.get("rank")))
        _check(failures, "Strassen" in llm_pool.call.__doc__ if False
               else "행렬곱 텐서" in improve.build_prompt(t),
               "프롬프트에 텐서 도메인 계약이 실린다")


def main() -> int:
    failures = []
    for t in (test_oracle, test_loop_on_tensor):
        t(failures)
    if failures:
        print("\n=== 실패 ===")
        for f in failures:
            print(" -", f)
        return 1
    print("\n텐서 rank 도메인이 red-green 을 통과했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
