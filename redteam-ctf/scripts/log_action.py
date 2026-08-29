#!/usr/bin/env python3
"""
red/blue 양쪽이 공통으로 쓰는 로그 기록기.

사용:
  python3 scripts/log_action.py red  --action "modify session.json" --detail "role user->admin 시도" [--commit <hash>]
  python3 scripts/log_action.py blue --action "reject commit" --detail "session.json 역할 상승 발견" --verdict block [--commit <hash>]

red 쪽 필드: actor, ts, action, detail, commit
blue 쪽 필드: actor, ts, action, detail, verdict(allow|block|rollback), commit
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"


def current_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=LOG_DIR.parent
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("actor", choices=["red", "blue"])
    parser.add_argument("--action", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--verdict", choices=["allow", "block", "rollback"], default=None)
    parser.add_argument("--commit", default=None)
    args = parser.parse_args()

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": args.actor,
        "action": args.action,
        "detail": args.detail,
        "commit": args.commit or current_commit(),
    }
    if args.actor == "blue":
        entry["verdict"] = args.verdict or "allow"

    log_file = LOG_DIR / f"{args.actor}_{'actions' if args.actor == 'red' else 'verdicts'}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"logged -> {log_file}")


if __name__ == "__main__":
    main()
