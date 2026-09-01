"""
과제(task) 디렉토리 규약과 입출력 -- 자가 개선 루프가 딛는 파일 기반.

왜 전부 파일인가: 이 저장소가 반복해서 겪은 결론과 같다. 인메모리 상태는 프로세스가 죽으면
사라지고, VM 은 회수된다. 루프는 몇 시간씩 돌 수 있으므로 매 반복의 결과를 즉시 파일로 쓴다.
그래야 중간에 죽어도 챔피언 코드와 이력이 남고, 다시 띄우면 이어서 돈다.

디렉토리 규약 (solver/tasks/<slug>/):
    spec.md            사람이 준 과제 설명 원문. 프롬프트에 그대로 실린다.
    config.json        데이터 경로·채점기 이름·시간 예산 등
    champion.py        지금까지 가장 점수가 높은 해법 (이것이 최종 산출물)
    champion.json      그 해법의 점수 상세
    history.jsonl      매 반복 1줄: 점수, 채택 여부, 실패 사유, 실행 로그 꼬리
    state.json         현재 진행 상황 (pid, 반복 수, 최고 점수, 마지막 오류)
    candidates/        각 반복이 만든 코드 (채택 안 된 것도 남긴다 -- 왜 나빴는지가 정보다)
    log                백그라운드 실행 로그

데이터 규약 (config.json 의 data_dir, 기본 solver/tasks/<slug>/data):
    train/ground_truth.csv   제출 CSV 와 같은 형식(node/edge 행). 로컬 채점의 정답.
    train/<dataset>.zarr     학습용 입력 (dataset 이름은 ground_truth.csv 의 dataset 열과 일치)
    test/<dataset>.zarr      제출용 입력

해법의 계약:
    후보 코드는 solve(data_dir: str, out_csv: str) -> None 를 정의해야 한다.
    data_dir 안의 각 .zarr 를 읽어 out_csv 에 제출 형식으로 쓴다.
    루프는 이것을 별도 프로세스로 실행하고(타임아웃 있음), 나온 CSV 를 채점한다.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
SUBMISSION_COLUMNS = ["id", "dataset", "row_type", "node_id", "t", "z", "y", "x",
                      "source_id", "target_id"]


def slugify(text: str, fallback: str = "task") -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in text.strip().lower()[:40]]
    s = "".join(keep).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s or fallback


class Task:
    def __init__(self, slug: str):
        self.slug = slug
        self.dir = TASKS / slug
        self.candidates = self.dir / "candidates"

    # ---- 경로 ----
    @property
    def spec_path(self): return self.dir / "spec.md"
    @property
    def config_path(self): return self.dir / "config.json"
    @property
    def champion_path(self): return self.dir / "champion.py"
    @property
    def champion_score_path(self): return self.dir / "champion.json"
    @property
    def history_path(self): return self.dir / "history.jsonl"
    @property
    def state_path(self): return self.dir / "state.json"
    @property
    def log_path(self): return self.dir / "log"

    # ---- 생성 / 읽기 ----
    def create(self, spec: str, config: dict = None) -> "Task":
        self.candidates.mkdir(parents=True, exist_ok=True)
        self.spec_path.write_text(spec, encoding="utf-8")
        cfg = {"data_dir": str(self.dir / "data"),
               "scorer": "cell_tracking",
               "candidate_timeout": 1800,
               "max_iterations": 0,          # 0 = 무한 (사람이 멈출 때까지)
               "sleep_between": 5}
        cfg.update(config or {})
        self.config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        return self

    def config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def spec(self) -> str:
        return self.spec_path.read_text(encoding="utf-8")

    def state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def set_state(self, **kw):
        s = self.state()
        s.update(kw)
        self.state_path.write_text(json.dumps(s, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    def append_history(self, rec: dict):
        with self.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def history(self, limit: int = None) -> list:
        if not self.history_path.exists():
            return []
        rows = [json.loads(l) for l in self.history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return rows[-limit:] if limit else rows

    def champion_score(self) -> dict:
        if not self.champion_score_path.exists():
            return {}
        return json.loads(self.champion_score_path.read_text(encoding="utf-8"))


def list_tasks() -> list:
    if not TASKS.exists():
        return []
    return sorted(p.name for p in TASKS.iterdir() if (p / "spec.md").exists())


# ---------------------------------------------------------------- 제출 CSV

def read_submission(path) -> dict:
    """제출 형식 CSV -> {dataset: Tracks}. 형식 오류는 예외로 올린다(조용히 넘기지 않는다)."""
    from metric import Tracks
    per = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("dataset", "row_type") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"제출 CSV 에 필수 열이 없다: {missing} (헤더: {reader.fieldnames})")
        rows = defaultdict(list)
        for r in reader:
            rows[r["dataset"]].append(r)
    for name, rr in rows.items():
        per[name] = Tracks.from_rows(rr)
    return per


def write_submission(path, per_dataset: dict):
    """{dataset: (nodes dict, edges list)} -> 제출 CSV. id 는 연속 정수로 채운다."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(SUBMISSION_COLUMNS)
        i = 0
        for name, (nodes, edges) in per_dataset.items():
            for nid, (t, z, y, x) in nodes.items():
                w.writerow([i, name, "node", nid, int(t), int(round(z)), int(round(y)),
                            int(round(x)), -1, -1])
                i += 1
            for s, d in edges:
                w.writerow([i, name, "edge", -1, -1, -1, -1, -1, s, d])
                i += 1


def datasets_in(data_dir) -> list:
    """폴더 안의 .zarr 이름 목록(확장자 제외). 제출의 dataset 열이 이것과 일치해야 한다."""
    p = Path(data_dir)
    if not p.exists():
        return []
    return sorted(d.name.rsplit(".", 1)[0] for d in p.iterdir()
                  if d.name.endswith(".zarr") or d.name.endswith(".npy"))


def check_data(cfg: dict) -> dict:
    """데이터가 실제로 있는지 점검. 루프를 띄우기 전에 부르고, 없으면 무엇을 어디 둘지 알린다."""
    data = Path(cfg["data_dir"])
    train, test = data / "train", data / "test"
    gt = train / "ground_truth.csv"
    return {"data_dir": str(data), "train_exists": train.exists(), "test_exists": test.exists(),
            "ground_truth": str(gt), "ground_truth_exists": gt.exists(),
            "train_datasets": datasets_in(train), "test_datasets": datasets_in(test)}
