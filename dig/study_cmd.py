# -*- coding: utf-8 -*-
"""`!논문` -- a fixed command that studies a topic across several papers.

Fixed, not agent-routed, for the same reason `house/discord_cmd.py` is: the bot
hands every message to an agent with an arbitrary shell, and on top of that you
cannot promise **the same words produce the same work**. This command calls Python
functions and stops. It makes **zero LLM calls**, which also means it costs nothing
against the per-minute quota that has been the bot's bottleneck all day.

    !논문                          this help
    !논문 <topic>                  study it: search, open what is open, find the
                                   limitation the papers keep naming
    !논문 열린것만 <topic>          only papers with an open version -- fewer hits,
                                   but the bodies actually open
    !논문 거슬러 <doi|id>           walk one paper's references back through time
    !논문 한편 <doi|id>             one paper: what opened, which sections, what it
                                   says is wrong with the prior art
    !논문 상태                      what earlier runs found (the ledger)

Network calls are slow (a study touches several papers), so a study runs in the
**background** under the same rule the rest of this repo uses -- `setsid` +
`pgrep`-verified, never `ps -p $!`, and never a Hangul pattern in `pgrep -f`.
`거슬러`, `한편` and `상태` answer in place; they are one request or none.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eval.discord_cmd import _배경으로     # one background rule, not two

PREFIX = "!논문"
LOG = REPO / "logs" / "study.log"
LEDGER = REPO / "dig" / "study_ledger.jsonl"
# ASCII-only marker: `pgrep -f` cannot match Hangul in this locale (it silently
# reports "not running" for a process that is running).
MARKER = "dig/study.py"
_TOPIC = re.compile(r"[0-9A-Za-z가-힣_ .,:+/()-]{2,160}")

HELP = f"""**논문 (study)** -- 한 주제를 여러 편으로 읽고 **공통으로 말하는 한계**를 찾는다 (LLM 호출 0회)
`{PREFIX} <주제>` 찾고 · 열리는 본문을 열고 · 되풀이되는 한계를 센다 (백그라운드)
`{PREFIX} 열린것만 <주제>` 본문이 열리는 것만 -- 수는 적지만 실제로 읽힌다
`{PREFIX} 거슬러 <doi|id>` 그 논문의 참고문헌을 **과거로** 타고 오른다
`{PREFIX} 한편 <doi|id>` 한 편: 어디까지 읽혔나 · 무슨 절이 있나 · 무엇이 문제라 하나
`{PREFIX} 상태` 지금까지의 실행 기록

_본문이 안 열리면 **안 열렸다고 적는다**(■ 전문 · ▨ 초록만 · □ 서지만). 초록 다섯 편에서 찾은 패턴은 서론 다섯 편에서 찾은 것보다 약하고, 읽는 사람이 그 차이를 볼 수 있어야 한다._"""


def _one(ref: str) -> str:
    from dig import openalex as OA
    from dig import study as ST
    p = OA.fetch_one(ref)
    r = ST.read_paper(p)
    mark = {"full": "■", "abstract": "▨", "listing": "□"}.get(r["evidence"], "?")
    out = [f"{mark} **{r['title'][:90]}**",
           f"{r['year']} · {r['venue'][:50]} · cited {r['cited_by']} · "
           f"{r['oa_status']}{(' · ' + r['license']) if r['license'] else ''}",
           f"읽힌 정도: **{r['evidence']}**"
           + (f" (via {r['source']}{'/' + r['twin'] if r['twin'] else ''})"
              if r["source"] != "none" else "")]
    if r["sections"]:
        out.append("절: " + ", ".join(r["sections"]))
    if r["limitations"]:
        out.append("\n**무엇이 문제라고 하나**")
        out += [f"  · {s[:180]}" for s in r["limitations"][:5]]
    if r["misses"]:
        out.append("\n못 연 문: " + " / ".join(x[:80] for x in r["misses"][:3]))
    return "\n".join(out)


def _back(ref: str, depth: int = 2) -> str:
    from dig import openalex as OA
    walked = OA.walk_back(ref, depth=depth)
    if not walked.get("levels"):
        return ("참고문헌을 못 받았다 -- OpenAlex 에 이 논문의 참고문헌 목록이 없을 수 있다 "
                "(출판사가 Crossref 에 안 실은 경우가 있다).")
    return "```\n" + OA.timeline_text(walked)[:1800] + "\n```"


def _status() -> str:
    import json
    if not LEDGER.is_file():
        return f"_아직 돌린 적이 없다._ `{PREFIX} <주제>` 로 한 바퀴."
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").strip().splitlines()[-6:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out = [f"**실행 {len(rows)}건** (마지막부터)"]
    for r in reversed(rows):
        out.append(f"  · {r.get('at', '')[:16]} `{str(r.get('topic', ''))[:40]}` "
                   f"-- {r.get('found')}편 중 **본문 {r.get('read_full')}편**, "
                   f"{r.get('seconds')}s")
        if r.get("themes"):
            out.append(f"      {', '.join(r['themes'][:6])}")
    if LOG.is_file():
        tail = (LOG.read_text(encoding="utf-8", errors="replace").strip()
                .splitlines() or ["(비었다)"])[-1]
        out.append("로그 끝: " + tail[:120])
    return "\n".join(out)[:1900]


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.strip()

    if not words:
        return HELP
    if words == "상태":
        return _status()

    head, _, rest = words.partition(" ")
    rest = rest.strip()

    if head in ("한편", "one"):
        if not rest:
            return f"어느 논문인가 -- `{PREFIX} 한편 10.1109/JSSC.2020.3005831`"
        return _one(rest)[:1900]

    if head in ("거슬러", "back"):
        if not rest:
            return f"어느 논문에서 거슬러 오를까 -- `{PREFIX} 거슬러 <doi>`"
        return _back(rest)[:1900]

    open_only = head in ("열린것만", "open")
    topic = rest if open_only else words
    if not topic:
        return HELP
    if not _TOPIC.fullmatch(topic):
        return f"주제 꼴이 아니다: {topic[:40]!r}\n\n{HELP}"
    if not allow_write:
        return "논문 한 바퀴는 관리 채널에서만 -- 망을 쓰고 원장에 적는다."

    argv = ["python3", "dig/study.py", topic, "--n", "6", "--depth", "2"]
    if open_only:
        argv.append("--open-only")
    return (runner or _배경으로)(argv, LOG, MARKER)
