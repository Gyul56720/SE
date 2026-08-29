#!/usr/bin/env python3
"""두 로그 파일을 시간순으로 합쳐 markdown 타임라인 보고서를 생성한다.

사용: python3 scripts/make_timeline.py > report.md
"""
from __future__ import annotations

import json
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"


def load(name: str) -> list[dict]:
    path = LOG_DIR / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    entries = load("red_actions.jsonl") + load("blue_verdicts.jsonl")
    entries.sort(key=lambda e: e["ts"])

    print("# Red vs Blue 대회 타임라인\n")
    for e in entries:
        actor = "🔴 SE (red)" if e["actor"] == "red" else "🔵 Claude Opus (blue)"
        line = f"- `{e['ts']}` **{actor}** — {e['action']}"
        if e.get("detail"):
            line += f": {e['detail']}"
        if e.get("verdict"):
            line += f" _(verdict: {e['verdict']})_"
        line += f" (commit `{e['commit'][:12]}`)"
        print(line)


if __name__ == "__main__":
    main()
