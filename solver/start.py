"""
진입점 -- 디스코드에서 "이거 풀어줘 <스펙>" 한 번으로 자가 개선 루프를 띄운다.

디스코드 봇의 run_shell 은 180초에 잘린다(bot_tools.py). 개선 루프는 몇 시간을 돌아야 하므로
이 스크립트가 CLAUDE.md 의 백그라운드 규칙을 대신 지킨다:
  - 새 세션으로 분리해(start_new_session=True, setsid 와 같다) 부모가 죽어도 살아남게 하고,
  - stdin/stdout/stderr 를 전부 리다이렉트하고(nohup 과 같은 효과),
  - "시작했다"고 보고하기 전에 실제로 살아있는지 확인한다. 확인 전에 성공을 말하지 않는다.
    (이 저장소가 실측으로 겪은 실패다: 백그라운드로 띄웠다고 답했지만 프로세스가 부모와 함께
     정리돼 아무것도 생성되지 않았다.)

사용:
    python3 solver/start.py "<과제 설명 전문>"      # 새 과제 시작
    python3 solver/start.py --spec-file spec.md    # 파일에서 읽기
    python3 solver/start.py --status               # 진행 상황
    python3 solver/start.py --code                 # 지금까지의 최종 코드
    python3 solver/start.py --stop                 # 멈춤
    python3 solver/start.py --list                 # 과제 목록

데이터가 없으면 시작하지 않는다. 로컬 정답이 없으면 '개선'을 판정할 수 없고, 그때 도는 루프는
개선이 아니라 표류이기 때문이다. 무엇을 어디에 두어야 하는지 알려주고 종료한다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task as taskmod                                        # noqa: E402
import scorers                                                # noqa: E402


def _alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def _current_slug(explicit: str = None) -> str:
    if explicit:
        return explicit
    tasks = taskmod.list_tasks()
    if not tasks:
        return ""
    # 가장 최근에 손댄 과제
    return max(tasks, key=lambda s: (taskmod.Task(s).dir / "spec.md").stat().st_mtime)


def cmd_start(spec: str, slug: str, config: dict) -> int:
    slug = slug or taskmod.slugify(spec.splitlines()[0] if spec.strip() else "task")
    t = taskmod.Task(slug)
    existing = t.spec_path.exists()
    if existing and _alive(t.state().get("pid")):
        print(f"이미 '{slug}' 루프가 돌고 있다 (pid {t.state().get('pid')}). "
              f"--status 로 확인하거나 --stop 후 다시 시작하라.")
        return 1
    if not existing:
        t.create(spec, config)
    (t.dir / "stop").unlink(missing_ok=True)

    # 정의 기반 도메인(tensor_rank 등)은 solve 가 읽을 파라미터를 data/train/config.json 에 둔다.
    cfg_now = t.config()
    if cfg_now.get("scorer") == "tensor_rank":
        seed_dir = Path(cfg_now["data_dir"]) / "train"
        seed_dir.mkdir(parents=True, exist_ok=True)
        (seed_dir / "config.json").write_text(
            json.dumps({"n": int(cfg_now.get("n", 2))}, ensure_ascii=False), encoding="utf-8")

    scorer = t.config().get("scorer", "cell_tracking")
    needs_gt = scorers.get(scorer)["needs_ground_truth"]
    data = taskmod.check_data(t.config())
    if needs_gt and not data["ground_truth_exists"]:
        print("루프를 시작하지 않았다 -- 로컬 정답이 없어 개선을 판정할 수 없다.\n")
        print(f"과제는 만들어 뒀다: {t.dir}")
        print("아래를 두고 같은 명령을 다시 실행하라:")
        print(f"  {data['data_dir']}/train/ground_truth.csv   제출과 같은 형식(node/edge 행)")
        print(f"  {data['data_dir']}/train/<dataset>.zarr     학습용 입력")
        print(f"  {data['data_dir']}/test/<dataset>.zarr      제출용 입력")
        t.set_state(status="blocked", reason="ground_truth.csv 없음", data=data)
        return 3

    log = t.log_path
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as lf, open(os.devnull) as devnull:
        lf.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 시작 =====\n")
        lf.flush()
        p = subprocess.Popen([sys.executable, str(HERE / "improve.py"), slug],
                             stdin=devnull, stdout=lf, stderr=lf,
                             start_new_session=True, cwd=str(HERE.parent))

    time.sleep(2.0)                                            # 즉시 죽는 경우를 잡는다
    if not _alive(p.pid):
        print(f"띄웠으나 곧바로 종료됐다. 로그를 보라: {log}")
        print("--- 로그 꼬리 ---")
        print("\n".join(log.read_text(encoding="utf-8").splitlines()[-20:]))
        return 4

    print(f"시작했다 (확인됨).")
    print(f"  과제   : {slug}")
    print(f"  PID    : {p.pid}")
    print(f"  로그   : {log}")
    print(f"  데이터 : train={data['train_datasets']} test={data['test_datasets']}")
    print(f"  진행   : python3 solver/start.py --status")
    print(f"  결과   : python3 solver/start.py --code")
    return 0


def cmd_status(slug: str) -> int:
    slug = _current_slug(slug)
    if not slug:
        print("과제가 없다.")
        return 1
    t = taskmod.Task(slug)
    st = t.state()
    pid = st.get("pid")
    alive = _alive(pid)
    hist = t.history()
    adopted = [h for h in hist if h.get("adopted")]
    print(f"과제      : {slug}")
    print(f"상태      : {st.get('status')} / 프로세스 {'살아있음' if alive else '없음'} (pid {pid})")
    print(f"반복      : {len(hist)}회, 채택 {len(adopted)}회")
    print(f"최고 점수 : {st.get('best')}")
    if st.get("reason"):
        print(f"사유      : {st['reason']}")
    cs = t.champion_score()
    if cs:
        extra = ""
        if cs.get("rank") is not None:                 # tensor_rank 도메인
            extra = f" rank={cs.get('rank')} (표준 {cs.get('baseline_rank')})"
        elif cs.get("edge_jaccard") is not None:       # cell_tracking 도메인
            extra = f" edge={cs.get('edge_jaccard'):.4f} division={cs.get('division_jaccard'):.4f}"
        print(f"챔피언    : combined={cs.get('combined'):.6f}{extra}")
    if adopted:
        print("\n점수가 올라간 지점:")
        for h in adopted[-6:]:
            print(f"  #{h['iteration']} {h.get('previous_best')} -> {h['combined']}"
                  f"  {h.get('hypothesis','')}"[:160])
    if hist:
        print("\n최근 시도:")
        for h in hist[-5:]:
            mark = "채택" if h.get("adopted") else ("실패" if h.get("error") else "기각")
            print(f"  #{h['iteration']} {mark} {h.get('combined')} "
                  f"{h.get('hypothesis') or h.get('error') or ''}"[:160])
    return 0


def cmd_code(slug: str) -> int:
    slug = _current_slug(slug)
    t = taskmod.Task(slug)
    if not t.champion_path.exists():
        print(f"아직 채택된 코드가 없다. --status 로 진행 상황을 보라.")
        return 1
    cs = t.champion_score()
    print(f"# 과제: {slug} | 로컬 점수 combined={cs.get('combined')} "
          f"rank={cs.get('rank')} beats_standard={cs.get('beats_standard')}")
    print(f"# 경로: {t.champion_path}")
    print(t.champion_path.read_text(encoding="utf-8"))
    return 0


def cmd_stop(slug: str) -> int:
    slug = _current_slug(slug)
    t = taskmod.Task(slug)
    (t.dir / "stop").write_text("stop\n", encoding="utf-8")
    pid = t.state().get("pid")
    print(f"'{slug}' 에 stop 을 남겼다. 다음 반복 경계에서 멈춘다 (pid {pid}).")
    print("즉시 끊으려면: kill " + str(pid))
    return 0


def main():
    ap = argparse.ArgumentParser(description="자가 개선 루프 진입점")
    ap.add_argument("spec", nargs="?", help="과제 설명 전문")
    ap.add_argument("--spec-file", help="과제 설명을 담은 파일")
    ap.add_argument("--slug", help="과제 식별자(생략하면 설명에서 만든다)")
    ap.add_argument("--data-dir", help="데이터 디렉토리(기본 solver/tasks/<slug>/data)")
    ap.add_argument("--scorer", default="cell_tracking",
                    help="심판 이름 (cell_tracking | tensor_rank)")
    ap.add_argument("--n", type=int, help="tensor_rank 도메인의 행렬 크기 n")
    ap.add_argument("--candidate-timeout", type=float, default=1800,
                    help="후보 하나의 실행 시간 상한(초)")
    ap.add_argument("--max-iterations", type=int, default=0, help="0이면 멈출 때까지")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--code", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for s in taskmod.list_tasks():
            st = taskmod.Task(s).state()
            print(f"{s}\t{st.get('status')}\tbest={st.get('best')}")
        return 0
    if a.status:
        return cmd_status(a.slug)
    if a.code:
        return cmd_code(a.slug)
    if a.stop:
        return cmd_stop(a.slug)

    spec = a.spec
    if a.spec_file:
        spec = Path(a.spec_file).read_text(encoding="utf-8")
    if not spec and not sys.stdin.isatty():
        spec = sys.stdin.read()
    if not spec or not spec.strip():
        ap.error("과제 설명이 필요하다 (인자, --spec-file, 또는 stdin)")

    cfg = {"candidate_timeout": a.candidate_timeout, "max_iterations": a.max_iterations,
           "scorer": a.scorer}
    if a.n is not None:
        cfg["n"] = a.n
    if a.data_dir:
        cfg["data_dir"] = str(Path(a.data_dir).resolve())
    return cmd_start(spec, a.slug, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
