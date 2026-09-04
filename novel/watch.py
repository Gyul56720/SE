"""지금 어디까지 왔는지, 끝났는지 한 화면에 보여준다.

로그는 성기다 -- 회차 조립 시작과 끝에만 줄이 남고, 그 사이 20~40분 동안은 llm_pool 의
호출 줄만 흐른다. 그것만 보고는 "도는 중" 과 "멈춤" 과 "끝남" 이 구별되지 않는다.

여기서는 세 곳을 한꺼번에 읽는다. 전부 파일이라 **도는 프로세스를 건드리지 않는다.**
  · pgrep          살아 있는가
  · scenes.jsonl   씬이 하나씩 끝날 때마다 한 줄. 조립이 끝나면 episode 줄
  · romance.json   지금까지 채워진 산문
  · 로그 파일       마지막 줄이 몇 초 전인가 -- 5분 넘게 안 자라면 멈춘 것이다

실행:
    python3 novel/watch.py              # 한 번 찍고 끝
    python3 novel/watch.py -f           # 20초마다 갱신 (Ctrl+C 로 나감)
    python3 novel/watch.py -f -i 60     # 간격 지정
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
DEFAULT_PATH = HERE / "romance.json"
STALL_SECONDS = 300          # 이만큼 로그가 안 자라면 멈춘 것으로 본다


def alive() -> list:
    r = subprocess.run(["pgrep", "-af", "overnight.py"], capture_output=True, text=True)
    return [ln for ln in r.stdout.splitlines() if "pgrep" not in ln]


def newest_log(logs: Path) -> "Path | None":
    if not logs.is_dir():
        return None
    files = [p for p in logs.glob("*.log") if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def tail(path: Path, n: int = 3) -> list:
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
                 if ln.strip() and "AFC" not in ln]
    except OSError:
        return []
    return lines[-n:]


def events(jsonl: Path, n: int = 4) -> list:
    out = []
    try:
        for line in jsonl.read_text(encoding="utf-8").splitlines()[-40:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        return []
    return out[-n:]


def report(path: Path, logs: Path) -> str:
    from novel.state import Novel
    from novel import arc

    lines = []
    procs = alive()
    lg = newest_log(logs)
    age = time.time() - lg.stat().st_mtime if lg else None

    if procs:
        if age is not None and age > STALL_SECONDS:
            head = f"도는 중이지만 **로그가 {age / 60:.0f}분째 안 자란다** -- 멈췄을 수 있다"
        else:
            head = "도는 중"
    else:
        head = "프로세스 없음 -- 끝났거나 죽었다"
    lines.append(f"상태   {head}")
    if lg:
        lines.append(f"로그   {lg.name} (마지막 줄 {age:.0f}초 전)")

    if not path.exists():
        lines.append("원고   아직 없다")
        return "\n".join(lines)

    n = Novel.load(path)
    eps = sorted({s.episode for s in n.scenes if s.episode})
    ver = sum(1 for s in n.scenes if s.status == "verified")
    chars = sum(len(s.prose or "") for s in n.scenes)
    lines.append(f"씬     {len(n.scenes)}개 · verified {ver} · 산문 {chars:,}자")
    if eps:
        wrote = sorted({s.episode for s in n.scenes if s.episode and (s.prose or '').strip()})
        lines.append(f"회차   조립 {eps[0]}~{eps[-1]}화 · "
                     f"산문 {f'{wrote[0]}~{wrote[-1]}화' if wrote else '없음'}")
        cur = eps[-1]
        same = [s for s in n.scenes if s.episode == cur]
        got = sum(len(s.prose or "") for s in same)
        done = sum(1 for s in same if s.status == "verified")
        lines.append(f"{cur}화    씬 {done}/{len(same)} 완성 · "
                     f"{got:,}/{arc.CHARS_PER_EPISODE:,}자")

    ev = events(path.with_suffix(".scenes.jsonl"))
    if ev:
        lines.append("최근   " + " | ".join(
            f"{e.get('event')}:{e.get('id') or e.get('eps') or e.get('status') or ''}"
            for e in ev))
    for ln in tail(lg, 2) if lg else []:
        lines.append(f"       {ln[:96]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(DEFAULT_PATH))
    ap.add_argument("--logs", default=str(HERE.parent / "logs"))
    ap.add_argument("-f", "--follow", action="store_true")
    ap.add_argument("-i", "--interval", type=float, default=20)
    a = ap.parse_args()

    path, logs = Path(a.path), Path(a.logs)
    while True:
        text = report(path, logs)
        if a.follow:
            print("\033[2J\033[H" + time.strftime("%H:%M:%S") + "\n" + text, flush=True)
            if "프로세스 없음" in text.splitlines()[0]:
                print("\n(끝났다)")
                return 0
            time.sleep(a.interval)
        else:
            print(text)
            return 0


if __name__ == "__main__":
    sys.exit(main())
