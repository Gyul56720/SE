"""
orchestrator(문제 분해·실행·검증 파이프라인)를 Discord 에이전트가 부를 수 있게 하는 얇은 층.

왜 별도 모듈인가 (bot_tools.py 안에 함수로 두지 않고): secret_filter.py / agent_context.py 와
같은 이유다. bot_tools 는 langchain·discord 가 깔린 환경에서만 임포트되므로, 그 안에 든 로직은
게이트와 테스트가 검사할 수 없다. 경로 제한처럼 "실제로 막는지"를 증명해야 하는 코드는 표준
라이브러리만 쓰는 모듈에 둔다. 여기에 서드파티 임포트를 추가하지 마라.

왜 백그라운드 실행인가: solve.drive() 는 계획->실행->검증->수리 루프를 도는 동안 LLM 을 여러 번
부른다(수 분). 도구가 그동안 블로킹하면 Discord 턴 전체가 매달리고, 봇이 재시작되면 무엇이
돌고 있었는지도 남지 않는다. 그래서 런을 띄우고 **런 디렉토리와 로그 경로를 즉시 돌려준다**.
진행 상황은 run_status() 로 따로 본다 -- 산출물이 전부 파일이라 이게 가능하다.

솔직한 한계 두 개:
  - 자식은 setsid(start_new_session)로 새 세션에 들어가지만 systemd 의 cgroup 은 벗어나지
    못한다. 배포로 se-discord-bot 이 재시작되면 돌던 런도 같이 죽는다. 죽어도 plan.json 은
    남으므로 resume_run() 으로 이어서 돌릴 수 있다(verified 노드는 건너뛴다).
  - 공개 채널에서 부르면 자식 환경에 GEMINI_API_KEY 가 없다(secret_filter.child_env).
    계획 단계에서 정직하게 실패한다 -- 도구는 관리 채널에만 붙인다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import agent_context
from secret_filter import redact_secrets

REPO_DIR = Path(__file__).resolve().parent
ORCH_DIR = REPO_DIR / "orchestrator"
RUNS_DIR = ORCH_DIR / "runs"
SOLVE_PY = ORCH_DIR / "solve.py"
LOG_DIR = REPO_DIR / "logs" / "orchestrator"

MAX_PROBLEM_CHARS = 4000
LOG_TAIL_CHARS = 1500
# 런이 즉시 죽는 경우(임포트 실패·키 없음)를 "시작했다"고 보고하지 않으려고 잠깐 지켜본다.
# 정상 런은 이 시간 안에 절대 안 끝난다(첫 LLM 호출만 해도 초 단위다).
_LIVENESS_WAIT_SEC = 1.5
_NAME_BAD = re.compile(r"[^0-9A-Za-z_.-]")


def _safe_run_name(name: str) -> str:
    """런 이름에서 디렉터리 성분과 이상한 문자를 걷어낸다. _resolve_run_dir 의 앞단일 뿐,
    이것만으로 안전을 주장하지 않는다 -- 최종 판정은 항상 _resolve_run_dir 이 한다."""
    name = Path(name or "").name
    return _NAME_BAD.sub("_", name).strip("._")[:80]


def _resolve_run_dir(name: str) -> Path:
    """runs/ 바로 아래로만 해석되는 런 디렉토리 경로. 벗어나면 ValueError.

    도구 인자는 Discord 메시지에서 온 LLM 출력이다. status/stop 이 임의 경로를 받으면
    저장소 밖 파일을 읽거나(../../etc/...) 남의 프로세스를 죽이는 통로가 된다.
    G014 가 이 함수에 탈출 카나리를 직접 먹여서 '이름만 남은 제한'이 되지 않게 감시한다."""
    path = (RUNS_DIR / (name or "")).resolve()
    if path.parent != RUNS_DIR.resolve() or path == RUNS_DIR.resolve():
        raise ValueError("orchestrator/runs/ 바로 아래의 런 디렉토리만 지정할 수 있다.")
    return path


def _meta_path(run_dir: Path) -> Path:
    return run_dir / "tool_meta.json"


def _read_meta(run_dir: Path) -> dict:
    try:
        return json.loads(_meta_path(run_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _alive(pid) -> bool:
    """프로세스가 살아 있는가. PID 재사용까지는 구분하지 못한다(그래서 이 값만으로
    '돌고 있다'고 단정하지 말고 plan.json 의 상태와 함께 읽는다)."""
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    return True


def _log_tail(path, chars: int = LOG_TAIL_CHARS) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-chars:]


def list_runs(limit: int = 10) -> "list[Path]":
    """최근에 손댄 런 디렉토리(plan.json 이 있는 것만), 최신 순."""
    if not RUNS_DIR.is_dir():
        return []
    dirs = [d for d in RUNS_DIR.iterdir() if d.is_dir() and (d / "plan.json").is_file()]
    return sorted(dirs, key=lambda d: (d / "plan.json").stat().st_mtime, reverse=True)[:limit]


def _newest_run() -> "Path | None":
    runs = list_runs(limit=1)
    return runs[0] if runs else None


def _launch(run_dir: Path, args: "list[str]", env=None) -> dict:
    """solve.py 를 백그라운드 세션으로 띄우고 tool_meta.json 을 남긴다."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_dir.name}.log"
    cmd = [sys.executable, str(SOLVE_PY), *args]
    with open(log_path, "a", encoding="utf-8") as log, open(os.devnull, "rb") as devnull:
        log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(args[:1])} ===\n")
        log.flush()
        proc = subprocess.Popen(
            cmd, cwd=str(REPO_DIR), stdout=log, stderr=subprocess.STDOUT, stdin=devnull,
            env=env, start_new_session=True,   # setsid -- 부모 턴이 끝나도 살아 있게
        )
    meta = {"pid": proc.pid, "log": str(log_path), "started_at": time.time(),
            "cmd": args}
    _meta_path(run_dir).write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    # "백그라운드로 시작했다"고 말하기 전에 실제로 살아 있는지 확인한다. 키가 없거나
    # 임포트가 깨지면 자식은 1초 안에 죽는데, 확인 없이 보고하면 아무 일도 일어나지 않은
    # 런을 '시작됨'으로 알리게 된다(CLAUDE.md 의 백그라운드 규칙과 같은 이유).
    deadline = time.time() + _LIVENESS_WAIT_SEC
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.05)
    if proc.poll() is not None:
        return {"ok": False, "pid": proc.pid, "log": str(log_path),
                "returncode": proc.returncode, "tail": _log_tail(log_path)}
    return {"ok": True, "pid": proc.pid, "log": str(log_path)}


def _launched_message(run_dir: Path, res: dict, what: str) -> str:
    rel_log = os.path.relpath(res["log"], REPO_DIR)
    if not res["ok"]:
        # 자식이 곧바로 끝난 경우를 뭉뚱그리지 않는다. exit=0 이면서 plan.json 이 있으면
        # 실제로 다 푼 것이고(작은 런은 1초 안에 끝난다), 나머지는 시작 실패다.
        if res["returncode"] == 0 and (run_dir / "plan.json").is_file():
            return f"{what}: 바로 끝났다(오래 걸리지 않는 런이었다).\n\n" + run_status(run_dir.name)
        why = ("계획 단계에서 끝났다 -- plan.json 이 만들어지지 않았다(키 없음/쿼터 소진 등)"
               if res["returncode"] == 0 else f"시작 직후 죽었다(exit={res['returncode']})")
        # 계획도 못 세운 런은 껍데기만 남는다. tool_meta.json 밖에 없으면 치운다 --
        # 키 하나 빠졌을 때 runs/ 가 빈 디렉토리로 뒤덮이지 않게(solve.py 도 같은 이유로
        # 빈 런을 지우는데, 우리가 넣은 meta 파일 때문에 그 정리가 걸리지 않는다).
        if not (run_dir / "plan.json").is_file():
            # planner 가 만들다 만 빈 components/ 도 껍데기로 본다.
            leftovers = {p.name for p in run_dir.rglob("*") if p.is_file()} if run_dir.is_dir() else set()
            if leftovers <= {"tool_meta.json"}:
                shutil.rmtree(run_dir, ignore_errors=True)
        return redact_secrets(
            f"{what}: {why}. 런: {run_dir.name}\n"
            f"로그: {rel_log}\n--- 로그 끝부분 ---\n{res['tail']}")
    return (f"{what}: 백그라운드로 시작했다(PID {res['pid']}, 확인됨).\n"
            f"런: {run_dir.name}   (orchestrator/runs/{run_dir.name})\n"
            f"로그: {rel_log}\n"
            f"진행은 orchestrator_status('{run_dir.name}') 로 확인하라. "
            f"수 분 걸린다 -- 기다리지 말고 다른 일을 하다가 나중에 물어보라.")


def start_run(problem: str, env=None, node_timeout: float = None) -> str:
    """새 런을 만들고 solve.py 를 백그라운드로 띄운다. 런 디렉토리/로그 경로를 즉시 반환."""
    if agent_context.is_blocked():
        return "실패: 게스트는 orchestrator 런을 시작할 수 없습니다."
    problem = (problem or "").strip()
    if not problem:
        return "실패: 풀 문제를 문자열로 달라."
    if len(problem) > MAX_PROBLEM_CHARS:
        return f"실패: 문제 설명이 너무 길다({len(problem)}자, 상한 {MAX_PROBLEM_CHARS}자)."
    if not SOLVE_PY.is_file():
        return f"실패: {SOLVE_PY} 가 없다."

    base = time.strftime("%Y%m%d-%H%M%S")
    name, n = base, 1
    while (RUNS_DIR / name).exists():
        n += 1
        name = f"{base}-{n}"
    run_dir = _resolve_run_dir(_safe_run_name(name))
    run_dir.mkdir(parents=True, exist_ok=True)

    args = [problem, "--run-dir", str(run_dir)]
    if node_timeout is not None:
        args += ["--node-timeout", str(node_timeout)]
    return _launched_message(run_dir, _launch(run_dir, args, env=env), "새 orchestrator 런")


def resume_run(run: str, env=None) -> str:
    """죽었거나 미완인 런을 이어서 돌린다(verified 노드는 건너뛴다)."""
    if agent_context.is_blocked():
        return "실패: 게스트는 orchestrator 런을 재개할 수 없습니다."
    try:
        run_dir = _resolve_run_dir(_safe_run_name(run))
    except ValueError as e:
        return f"실패: {e}"
    if not (run_dir / "plan.json").is_file():
        return f"실패: {run_dir.name} 에 plan.json 이 없다 -- 이어서 돌릴 런이 아니다."
    meta = _read_meta(run_dir)
    if _alive(meta.get("pid")):
        return (f"이미 PID {meta['pid']} 로 돌고 있다. 먼저 orchestrator_stop('{run_dir.name}') "
                f"으로 멈추고 다시 걸어라.")
    return _launched_message(run_dir, _launch(run_dir, ["--resume", str(run_dir)], env=env),
                             f"런 {run_dir.name} 재개")


def run_status(run: str = "") -> str:
    """런의 현재 상태: 프로세스 생사, 노드별 status, 마지막 실패 사유, 최종 결과, 로그 끝부분."""
    if run.strip():
        try:
            run_dir = _resolve_run_dir(_safe_run_name(run))
        except ValueError as e:
            return f"실패: {e}"
        if not run_dir.is_dir():
            return f"실패: 그런 런이 없다({run_dir.name}). 최근 런: {', '.join(d.name for d in list_runs()) or '없음'}"
    else:
        found = _newest_run()
        if found is None:
            return "런이 하나도 없다. orchestrator_solve 로 시작하라."
        run_dir = found

    meta = _read_meta(run_dir)
    lines = [f"런 {run_dir.name} (orchestrator/runs/{run_dir.name})"]

    plan_path = run_dir / "plan.json"
    plan = None
    if plan_path.is_file():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except ValueError as e:
            lines.append(f"plan.json 을 읽을 수 없다: {e}")
    else:
        lines.append("plan.json 이 아직 없다 -- 계획 단계이거나 계획이 실패했다.")

    alive = _alive(meta.get("pid"))
    if meta.get("pid"):
        lines.append(f"프로세스: {'실행 중' if alive else '종료됨'} (PID {meta['pid']})")

    if plan:
        lines.append(f"문제: {plan.get('problem', '')[:300]}")
        final_id = plan.get("final")
        done = False
        for node in plan.get("nodes", []):
            mark = {"verified": "OK", "failed": "실패", "pending": "대기"}.get(node.get("status"), "?")
            tag = " (최종)" if node.get("id") == final_id else ""
            lines.append(f"  [{mark}] {node.get('id')}{tag} <- {node.get('deps') or '-'} : "
                         f"{(node.get('goal') or '')[:70]}")
            last = (node.get("attempts") or [])[-1:]
            if last:
                why = last[0].get("error") or last[0].get("rejected") or ""
                if why:
                    lines.append(f"        마지막 사유: {str(why)[:200]}")
            if node.get("id") == final_id and node.get("status") == "verified":
                done = True
                ref = node.get("result_ref")
                if ref:
                    try:
                        result = (run_dir / ref).read_text(encoding="utf-8")
                        lines.append(f"  최종 결과: {result[:800]}")
                    except OSError:
                        pass
        if done:
            lines.append("=> 풀렸다(최종 노드 verified).")
        elif not alive:
            lines.append(f"=> 아직 미완이고 프로세스도 없다. orchestrator_resume('{run_dir.name}') "
                         f"으로 이어서 돌릴 수 있다.")

    lines.extend(_rounds_tail(run_dir))

    tail = _log_tail(meta.get("log") or (LOG_DIR / f"{run_dir.name}.log"))
    if tail:
        lines.append(f"--- 로그 끝부분 ---\n{tail}")
    return redact_secrets("\n".join(lines))


def _rounds_tail(run_dir: Path, keep: int = 6) -> "list[str]":
    """rounds.jsonl 끝부분을 한 줄씩 요약한다.

    plan.json 은 **지금** 상태만 보여준다 -- 노드가 지금 실패라는 것은 알려주지만 몇 번째
    라운드인지, 수리가 몇 번 붙었는지, 재계획으로 승격했는지는 안 보인다. 한도가 30/20/10 이면
    그 구분이 곧 "진전이 있는가"의 답이라 상태 보고에 같이 싣는다."""
    path = run_dir / "rounds.jsonl"
    if not path.is_file():
        return []
    recs = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    pass          # 프로세스가 줄 중간에 죽으면 마지막 줄이 깨질 수 있다
    except OSError:
        return []
    if not recs:
        return []

    n_rounds = sum(1 for r in recs if r.get("event") == "round")
    out = [f"--- 라운드 기록 ({n_rounds}라운드, rounds.jsonl 끝 {min(keep, len(recs))}줄) ---"]
    for r in recs[-keep:]:
        ev = r.get("event")
        if ev == "start":
            lim = r.get("limits") or {}
            out.append(f"  [시작 {r.get('at')}] 라운드 {lim.get('max_repair_rounds')} / "
                       f"노드당 수리 {lim.get('max_node_repairs')} / 재계획 {lim.get('max_replans')}")
        elif ev == "end":
            out.append(f"  [끝 {r.get('at')}] {r.get('status')} "
                       f"(라운드 {r.get('rounds')}, 재계획 {r.get('replans')})"
                       + (f" -- {r.get('reason')}" if r.get("reason") else ""))
        else:
            failed = r.get("failed") or []
            out.append(f"  [R{r.get('round')} {r.get('at')}] {r.get('run_status')} / "
                       f"{r.get('action', '-')} / 실패 {failed or '-'} / "
                       f"{r.get('seconds')}초")
    return out


def stop_run(run: str = "") -> str:
    """돌고 있는 런을 멈춘다(프로세스 그룹째). 산출물은 그대로 남아 재개할 수 있다."""
    if agent_context.is_blocked():
        return "실패: 게스트는 orchestrator 런을 멈출 수 없습니다."
    if run.strip():
        try:
            run_dir = _resolve_run_dir(_safe_run_name(run))
        except ValueError as e:
            return f"실패: {e}"
    else:
        found = _newest_run()
        if found is None:
            return "멈출 런이 없다."
        run_dir = found
    meta = _read_meta(run_dir)
    pid = meta.get("pid")
    if not _alive(pid):
        return f"런 {run_dir.name} 은 이미 돌고 있지 않다."
    try:
        os.killpg(os.getpgid(int(pid)), signal.SIGTERM)   # setsid 로 띄웠으므로 그룹째 끊는다
    except OSError as e:
        return f"실패: PID {pid} 를 멈추지 못했다 ({e})."
    return (f"런 {run_dir.name}(PID {pid}) 에 SIGTERM 을 보냈다. 산출물은 남아 있으니 "
            f"orchestrator_resume('{run_dir.name}') 으로 이어서 돌릴 수 있다.")
