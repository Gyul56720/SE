"""로그 파일을 따라가며 새 줄을 디스코드 채널로 보낸다. 표준 라이브러리만 쓴다.

왜 필요한가. 오케스트레이터 런은 한 시간 넘게 돌고 ssh 를 붙들고 있을 수 없다.
setsid 로 띄워두면 죽지는 않지만, 그 사이 무슨 일이 있었는지는 나중에 로그를 열어야
안다. 실시간으로 보이면 헛도는 런을 일찍 끊을 수 있다.

디스코드 봇 토큰(DISCORD_BOT_TOKEN)과 채널 id(DISCORD_CHANNEL_ID)를 그대로 쓴다 --
새 웹훅을 만들지 않는다. urllib 로 REST 를 직접 때리므로 discord.py 도 필요 없고,
봇 프로세스와 무관하게 돈다.

    # 기본: 의미 있는 줄만 골라서 보낸다
    python3 tools/tail_to_discord.py ~/SE/logs/tr-22.log

    # 전부 보내기(주의: 시끄럽다), 처음부터, 다른 채널
    python3 tools/tail_to_discord.py LOG --all --from-start --channel 123...

    # 토큰 없이 무엇이 나갈지만 본다
    python3 tools/tail_to_discord.py LOG --dry-run

**시끄러우면 안 된다.** 로그를 통째로 흘리면 채널이 죽고 다음부터 아무도 안 본다.
그래서 기본은 무늬로 거르고, 분당 메시지 수에 상한을 둔다. 상한에 걸리면 버리지 않고
"N줄 생략"으로 접어서 보낸다 -- 조용히 사라지면 그것이 또 다른 거짓 초록이다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://discord.com/api/v10"

# 기본 필터. 런에서 사람이 실제로 볼 줄만 남긴다.
DEFAULT_GREP = (r"결과:|라운드|재계획|계획:|심판 주입|판본 추적|기각 사유|갈아타기|"
                r"등장한 갈래|이 통과는|최종 코드|^\s*\[OK\]|^\s*\[X |^\s*!!|"
                r"^case |^\S+\s+\d+\s+\d+\s+(OK|X )|Traceback|Error|"
                r"llm_pool\]|살아있다|스윕")

MAX_MSG = 1900          # 디스코드 2000자 제한에 여유
_stop = False


def _sigterm(*_):
    global _stop
    _stop = True


def post(channel: str, token: str, text: str, dry: bool) -> None:
    """한 메시지를 보낸다. 429 면 retry_after 만큼 기다렸다 한 번 더."""
    if dry:
        print(f"--- [{len(text)}자] ---\n{text}\n", flush=True)
        return
    body = json.dumps({"content": text}).encode()
    req = urllib.request.Request(
        f"{API}/channels/{channel}/messages", data=body, method="POST",
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (se-tail, 1.0)"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            return
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code == 429 and attempt == 1:
                try:
                    wait = float(json.loads(raw).get("retry_after", 2))
                except Exception:
                    wait = 2.0
                time.sleep(min(wait + 0.5, 30))
                continue
            # 토큰은 절대 찍지 않는다. 상태와 본문만.
            print(f"[tail_to_discord] HTTP {e.code}: {raw[:200]}", file=sys.stderr,
                  flush=True)
            return
        except Exception as e:
            print(f"[tail_to_discord] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            return


def chunks(lines: list) -> list:
    """줄들을 1900자 이하 코드블록 여러 개로 나눈다. 한 줄이 너무 길면 자른다."""
    out, cur = [], ""
    for ln in lines:
        ln = ln[:MAX_MSG - 20]
        if len(cur) + len(ln) + 1 > MAX_MSG - 10:
            if cur:
                out.append(cur)
            cur = ln
        else:
            cur = f"{cur}\n{ln}" if cur else ln
    if cur:
        out.append(cur)
    return [f"```\n{c}\n```" for c in out]


def follow(path: Path, from_start: bool):
    """파일을 따라간다. 아직 없으면 생길 때까지 기다리고, 잘리면 처음부터 다시 읽는다."""
    f = None
    while not _stop:
        if f is None:
            if not path.is_file():
                time.sleep(1.0)
                continue
            f = path.open("r", encoding="utf-8", errors="replace")
            if not from_start:
                f.seek(0, os.SEEK_END)
        line = f.readline()
        if line:
            yield line.rstrip("\n")
            continue
        # 로그가 회전되거나 잘렸는지 본다
        try:
            if path.stat().st_size < f.tell():
                f.close()
                f = None
                from_start = True
                continue
        except OSError:
            f.close()
            f = None
            continue
        yield None                       # 잠시 조용함 -- 여기서 모아둔 것을 내보낸다
        time.sleep(0.5)


def main() -> int:
    ap = argparse.ArgumentParser(description="로그를 디스코드 채널로 실시간 중계")
    ap.add_argument("log", help="따라갈 로그 파일")
    ap.add_argument("--channel", default=os.getenv("DISCORD_CHANNEL_ID"),
                    help="채널 id (기본: DISCORD_CHANNEL_ID)")
    ap.add_argument("--grep", default=DEFAULT_GREP, help="이 무늬에 걸리는 줄만 보낸다")
    ap.add_argument("--all", action="store_true", help="필터 없이 전부 (시끄럽다)")
    ap.add_argument("--from-start", action="store_true", help="파일 처음부터")
    ap.add_argument("--interval", type=float, default=5.0, help="모아 보내는 주기(초)")
    ap.add_argument("--max-per-min", type=int, default=8, help="분당 메시지 상한")
    ap.add_argument("--prefix", default="", help="첫 메시지 앞에 붙일 말")
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 화면에 찍는다")
    a = ap.parse_args()

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not a.dry_run and not token:
        print("DISCORD_BOT_TOKEN 이 없다 -- set -a; source ~/SE/.env; set +a",
              file=sys.stderr)
        return 1
    if not a.dry_run and not a.channel:
        print("채널 id 가 없다 -- --channel 로 주거나 DISCORD_CHANNEL_ID 를 설정하라",
              file=sys.stderr)
        return 1

    pat = None if a.all else re.compile(a.grep)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    path = Path(a.log).expanduser()
    if a.prefix:
        post(a.channel, token, a.prefix[:MAX_MSG], a.dry_run)

    buf, dropped, sent_at, last_flush = [], 0, [], time.time()
    for line in follow(path, a.from_start):
        if _stop:
            break
        if line is not None:
            if pat is None or pat.search(line):
                if len(buf) < 60:
                    buf.append(line)
                else:
                    dropped += 1        # 버리지 않고 센다. 조용히 사라지면 거짓 초록이다
            continue
        if not buf or time.time() - last_flush < a.interval:
            continue
        now = time.time()
        sent_at[:] = [t for t in sent_at if now - t < 60]
        if len(sent_at) >= a.max_per_min:
            continue                    # 상한에 걸렸다 -- 다음 주기까지 더 모은다
        if dropped:
            buf.append(f"... ({dropped}줄 생략 -- 버퍼 초과)")
            dropped = 0
        for msg in chunks(buf):
            now = time.time()
            sent_at[:] = [t for t in sent_at if now - t < 60]
            if len(sent_at) >= a.max_per_min:
                break
            post(a.channel, token, msg, a.dry_run)
            sent_at.append(time.time())
        buf.clear()
        last_flush = time.time()

    if buf:
        for msg in chunks(buf):
            post(a.channel, token, msg, a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
