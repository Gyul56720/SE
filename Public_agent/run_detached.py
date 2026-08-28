"""
Loop.py의 self-correction 루프처럼 몇 분 이상 걸리는 스크립트를, se-discord-bot.service의
cgroup 밖에서 백그라운드로 띄워주는 순수 헬퍼. LLM 호출이 전혀 없다 -- agent가 매번
`systemd-run --scope ... setsid nohup ...` 같은 긴 셸 명령을 직접 조합하려면 그때마다
토큰을 쓰게 되는데, 그 조합 로직 자체를 코드로 고정해서 `run_shell`로 이 스크립트 하나만
호출하면 되게 만든 것이다.

CLAUDE.md의 백그라운드 실행 규칙(setsid nohup + disown)과 discord_bot_server.py의
run_claude()가 쓰는 `systemd-run --scope`(se-discord-bot.service 재배포로 봇이 재시작돼도
안 죽게 cgroup을 분리하는 것) 두 패턴을 합쳤다.

사용법 (run_shell로):
    python3 Public_agent/run_detached.py <실행할 스크립트.py> [로그파일 경로]

반환: 실제로 살아있는지 ps로 확인한 뒤에만 "PID: <pid>\n로그: <경로>"를 출력한다.
확인 전에는 아무것도 성공했다고 말하지 않는다.
"""
from __future__ import annotations

import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = REPO_DIR / "logs"


def launch_detached(script_path: str, log_path: "str | None" = None, extra_args: "list[str] | None" = None) -> dict:
    """script_path(파이썬 스크립트)를 systemd-run --scope + setsid nohup으로 띄우고,
    실제로 살아있는지 확인한 뒤 {"pid": int, "log_path": str} 를 돌려준다.
    살아있음을 확인 못 하면 RuntimeError를 낸다 -- 확인 없이 성공을 주장하지 않는다."""
    script = Path(script_path)
    if not script.is_absolute():
        script = REPO_DIR / script
    if not script.exists():
        raise FileNotFoundError(f"스크립트를 찾을 수 없다: {script}")

    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = Path(log_path) if log_path else DEFAULT_LOG_DIR / f"{script.stem}-{uuid.uuid4().hex[:8]}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    scope_unit = f"se-loop-{uuid.uuid4().hex[:12]}"
    cmd_parts = ["python3", str(script), *(extra_args or [])]
    quoted_cmd = " ".join(shlex.quote(p) for p in cmd_parts)

    # sudo -E systemd-run --scope: se-discord-bot.service의 cgroup 밖으로 분리해서
    # 재배포(systemctl restart)에 딸려 죽지 않게 한다 (run_claude()와 동일 패턴).
    # setsid nohup ... & disown: claude -p 자체가 응답 후 곧바로 종료돼도(셸 job table
    # 연결이 끊겨도) 살아있게 한다 (CLAUDE.md 규칙).
    full_cmd = (
        f"sudo -E systemd-run --scope --quiet --collect --unit={scope_unit} -- "
        f"setsid nohup {quoted_cmd} > {shlex.quote(str(log_file))} 2>&1 < /dev/null & "
        f"disown; echo $!"
    )
    result = subprocess.run(["bash", "-c", full_cmd], cwd=REPO_DIR, capture_output=True, text=True, timeout=30)
    pid_str = (result.stdout or "").strip().splitlines()[-1] if result.stdout.strip() else ""
    if not pid_str.isdigit():
        raise RuntimeError(f"실행 실패, stderr:\n{result.stderr}")
    pid = int(pid_str)

    time.sleep(1)  # systemd-run이 실제로 프로세스를 띄울 시간을 준다.
    check = subprocess.run(["ps", "-p", pid_str], capture_output=True, text=True)
    if check.returncode != 0:
        raise RuntimeError(f"PID {pid}가 확인 안 됨 (바로 죽었을 수 있음). 로그 확인: {log_file}")

    return {"pid": pid, "log_path": str(log_file)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 run_detached.py <스크립트.py> [로그파일]")
        sys.exit(1)
    target_script = sys.argv[1]
    target_log = sys.argv[2] if len(sys.argv) > 2 else None
    info = launch_detached(target_script, target_log)
    print(f"PID: {info['pid']}\n로그: {info['log_path']}")
