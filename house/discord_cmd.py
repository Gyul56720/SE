# -*- coding: utf-8 -*-
"""**디스코드에서 설계 하우스를 돌린다 -- 에이전트를 안 거치는 고정 명령.**

    !회사                     조직도 -- 다섯 명이 누구고 무엇을 하나
    !회사 <사람>              그 사람을 돌린다 (보고서 PDF 를 낸다)
    !회사 <사람> 메일         돌리고 **PDF 를 메일로** 보낸다
    !회사 전체                다섯 명 다 (오래 걸린다 -- 백그라운드로 돈다)
    !회사 전체 메일           다섯 명 다 + 메일
    !회사 상태                지금 돌고 있나 · 마지막에 무엇을 냈나
    !회사 보고서              지금까지 낸 보고서 목록

    !회사 설계 <자연어>       **새 회로를 구상한다** -- 제안서 PDF 를 먼저 낸다
    !회사 회로                맡고 있는 회로 목록
    !회사 <사람> <회로>       그 회로로 그 사람을 돌린다 (예: `!회사 검증 fir`)

사람은 이름·직무·한글 어느 쪽으로도 부른다:
    !회사 검증   !회사 priya   !회사 dv      -> Priya Raghavan
    !회사 합성   !회사 marcus  !회사 sta     -> Marcus Webb
    !회사 물리설계  !회사 kenji  !회사 gds   -> Kenji Tanaka

## 왜 고정 명령인가

봇은 모든 메시지를 임의 셸을 가진 에이전트에 넘긴다. 그 위에서는 **같은 말에 같은
일이 난다**를 보장할 수 없다(`novel/discord_cmd.py` 의 사고 기록). 여기 있는 명령은
파이썬 함수를 직접 부르고 끝이다 -- 사용자 글이 셸에 끼지 않는다.

## 오래 걸리는 것은 백그라운드로 -- 그런데 `setsid` 로

CLAUDE.md 의 규칙 그대로다. `claude -p` 든 디스코드 봇이든 부모가 죽으면 셸 job 은
같이 죽는다. 그래서 `setsid nohup ... < /dev/null &` 로 띄우고 **로그 파일 경로를
같이 답한다**. 그리고 살아있는지 확인하는 것은 `ps -p $!` 가 아니라 `pgrep -f` 이고,
**패턴에 한글을 넣지 않는다**(`/proc/<pid>/cmdline` 이 이 로캘에서 물음표가 된다).
그래서 아래 `_도나()` 는 `house/run.py` 라는 **아스키 토막**으로만 찾는다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PREFIX = "!회사"
REPO = Path(__file__).resolve().parent.parent
집 = REPO / "house"
로그방 = REPO / "logs"
원장 = 집 / "ledger.jsonl"
내는곳 = 집 / "out"

# 백그라운드를 찾을 때 쓰는 **아스키만 든** 패턴. 한글을 넣으면 영영 안 맞는다.
표식 = "house/run.py"


def _people():
    sys.path.insert(0, str(REPO))
    from house import people
    return people


def _도나() -> "list[str]":
    """지금 도는 하우스 작업. `pgrep -af` 로 찾고 **패턴은 아스키뿐이다**."""
    try:
        r = subprocess.run(["pgrep", "-af", 표식], capture_output=True, text=True, timeout=10)
    except Exception:                                        # noqa: BLE001
        return []
    줄 = [l for l in (r.stdout or "").splitlines() if 표식 in l and "pgrep" not in l]
    return 줄


def _원장읽기(몇=8) -> "list[dict]":
    if not 원장.exists():
        return []
    줄 = [l for l in 원장.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for l in 줄[-몇:]:
        try:
            out.append(json.loads(l))
        except Exception:                                    # noqa: BLE001
            pass
    return out


def _띄우기(인자: "list[str]", 이름: str) -> dict:
    """`setsid nohup` 으로 띄운다.  **답하기 전에 살아있는지 확인한다.**"""
    로그방.mkdir(parents=True, exist_ok=True)
    로그 = 로그방 / f"house-{이름}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    명 = ["setsid", "nohup", sys.executable, str(집 / "run.py"), *인자]
    with open(로그, "wb") as f:
        subprocess.Popen(명, stdout=f, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, cwd=str(REPO),
                         start_new_session=True,
                         env={**os.environ, "PYTHONUNBUFFERED": "1"})
    # setsid 는 제가 프로세스 그룹 리더면 fork 한다 -- Popen 의 pid 는 이미 끝난
    # 래퍼일 수 있다. 그래서 **PID 가 아니라 pgrep 으로** 확인한다.
    산것 = []
    for _ in range(20):
        time.sleep(0.25)
        산것 = _도나()
        if 산것:
            break
    return {"떴나": bool(산것), "로그": 로그, "프로세스": 산것[:3]}


def _표(줄들: "list[dict]") -> str:
    if not 줄들:
        return "_아직 낸 보고서가 없다._"
    out = []
    for d in 줄들:
        if not d.get("됐나"):
            out.append(f"· ❌ {d.get('이름')} — {d.get('까닭', '')[:80]}")
            continue
        메 = d.get("메일")
        꼬 = " · 📧" if 메 else ""
        out.append(f"· ✅ {d.get('이름')} — `{Path(d.get('pdf', '')).name}` "
                  f"{d.get('쪽')}쪽 / 그림 {d.get('그림')} / 표 {d.get('표')} / "
                  f"{d.get('초')}s{꼬}  ({d.get('때', '')[:16]})")
    return "\n".join(out)


def _도움() -> str:
    people = _people()
    return (people.org_chart() + "\n\n"
            "**쓰기**\n"
            "`!회사 <사람>` 그 사람을 돌린다 (보고서 PDF)\n"
            "`!회사 <사람> 메일` 돌리고 PDF 를 메일로 보낸다\n"
            "`!회사 전체` / `!회사 전체 메일` 다섯 명 다 (백그라운드)\n"
            "`!회사 상태` 지금 도나 · 마지막에 무엇을 냈나\n"
            "`!회사 보고서` 낸 보고서 목록\n"
            "`!회사 회로` 맡고 있는 회로 목록\n"
            "**`!회사 설계 <자연어>`** 새 회로를 구상한다 — 제안서를 먼저 낸다\n\n"
            "_보고서는 그림이 0장이면 안 나간다. 메일은 첨부가 없으면 안 나간다 — "
            "이 회사는 글만 보내지 않는다._")


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """모르는 말에는 None. 그러면 봇이 예전처럼 에이전트로 넘긴다."""
    t = (text or "").strip()
    if not t.startswith(PREFIX):
        return None
    나머지 = t[len(PREFIX):].strip()
    if not 나머지 or 나머지 in ("도움", "help", "?"):
        return _도움()

    낱말 = 나머지.split()
    머리 = 낱말[0].lower()
    메일 = any(w in ("메일", "mail", "보내", "gmail") for w in 낱말)

    # ---- 상태 ----
    if 머리 in ("상태", "status"):
        도 = _도나()
        줄 = ["**돌고 있다** — " + f"{len(도)}개" if 도 else "**지금 도는 작업이 없다.**"]
        for l in 도[:3]:
            줄.append(f"  `{l[:150]}`")
        최근 = sorted(로그방.glob("house-*.log"), key=lambda p: p.stat().st_mtime)[-1:] \
            if 로그방.exists() else []
        if 최근:
            꼬리 = 최근[0].read_text(encoding="utf-8", errors="replace").splitlines()[-6:]
            줄.append(f"\n마지막 로그 `{최근[0].name}`:")
            줄 += ["  " + x[:150] for x in 꼬리]
        줄.append("\n**마지막에 낸 것**\n" + _표(_원장읽기(5)))
        return "\n".join(줄)

    # ---- 회로 목록 ----
    if 머리 in ("회로", "설계목록", "designs"):
        sys.path.insert(0, str(REPO))
        from house import designs as DES
        return ("**맡고 있는 회로**\n" + DES.목록글()
                + "\n\n`!회사 <사람> <회로>` 로 회로를 고른다 (예: `!회사 검증 fir`).\n"
                  "새 회로는 `!회사 설계 <무엇을 만들지 한국어로>`.")

    # ---- 새 회로 구상 ----
    if 머리 in ("설계", "구상", "design", "새회로"):
        요청 = 나머지[len(낱말[0]):].strip()
        if not 요청:
            return ("**무엇을 만들지 한 줄로 적어 주세요.**\n"
                    "예) `!회사 설계 자동차 범퍼에 들어가는 TTD 회로의 전력 문제를 "
                    "해결해줄 수 있는 회로를 구상해줘`\n\n"
                    "_먼저 **제안서**(스펙·아키텍처·검증 계획·위험)를 PDF 로 냅니다. "
                    "RTL 은 그 다음, 승인 뒤에 짓습니다._")
        if not allow_write:
            return "`!회사 설계` 는 파일을 냅니다 — 지금은 쓰기가 막혀 있습니다."
        if _도나():
            return "**이미 돌고 있다.** `!회사 상태` 로 확인해라."
        r = _띄우기(["--설계", 요청], "arch")
        if not r["떴나"]:
            return f"**못 띄웠다.** 로그: `{r['로그']}`"
        sys.path.insert(0, str(REPO))
        from house import spec as SPEC
        from house import gen as GEN
        s0 = SPEC.읽기(요청)
        쓸 = GEN.쓸수있나()
        줄 = [f"**요청을 받았습니다.** 제안서를 짓고 있습니다 (백그라운드, `pgrep` 으로 살아있는 것 확인).",
             f"· 로그: `{r['로그']}`",
             "",
             "**코드가 글에서 먼저 읽은 것** (모델 없이):",
             f"· 쓰임새: {', '.join(s0.쓰임새) or '못 읽음'}",
             f"· 풀려는 문제: {', '.join(s0.문제) or '못 읽음'}",
             f"· 회로 갈래: {', '.join(s0.회로) or '못 읽음'}"]
        if s0.수:
            줄.append("· 읽은 수: " + ", ".join(f"{k}={v}" for k, v in s0.수.items()))
        if s0.모른다:
            줄.append("")
            줄.append("**아직 모르는 것** — 정해 주시면 스펙이 닫힙니다:")
            줄 += [f"  {i+1}. {x}" for i, x in enumerate(s0.모른다)]
        if not 쓸["됨"]:
            줄 += ["", f"⚠ **{쓸['말']}** — 아키텍처 칸은 비어서 나옵니다. "
                     "요청 판독까지는 그래도 됩니다."]
        줄 += ["", "_RTL 은 아직 한 줄도 짓지 않습니다. 제안서를 보시고 "
               "승인하시면 그때 짓습니다._"]
        return "\n".join(줄)

    # ---- 보고서 목록 ----
    if 머리 in ("보고서", "reports", "목록"):
        pdfs = sorted(내는곳.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True) \
            if 내는곳.exists() else []
        if not pdfs:
            return "_아직 낸 보고서가 없다._ `!회사 전체` 로 다섯 명을 돌려라."
        줄 = [f"**{len(pdfs)}개** (`house/out/`)"]
        for p in pdfs[:12]:
            줄.append(f"· `{p.name}` — {p.stat().st_size/1e3:,.0f} kB · "
                     f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(p.stat().st_mtime))}")
        return "\n".join(줄)

    if not allow_write:
        return ("`!회사` 는 도구를 실제로 돌리고 파일을 낸다 — 지금은 쓰기가 막혀 있다. "
                "`!회사` 만 쳐서 조직도를 보거나 `!회사 보고서` 로 이미 낸 것을 봐라.")

    # ---- 전체 ----
    if 머리 in ("전체", "다", "all", "모두"):
        if _도나():
            return ("**이미 돌고 있다.** 두 벌 띄우면 같은 파일을 서로 덮는다.\n"
                    "`!회사 상태` 로 어디까지 왔는지 봐라.")
        인자 = (["--메일"] if 메일 else []) + (["--빠르게"] if "빠르게" in 낱말 else [])
        r = _띄우기(인자, "all")
        if not r["떴나"]:
            return (f"**못 띄웠다.** 로그를 봐라: `{r['로그']}`\n"
                    "(살아있는지 `pgrep -af house/run.py` 로 확인했고 아무것도 안 나왔다.)")
        return (f"**다섯 명을 백그라운드로 시작했다** (살아있는 것을 `pgrep` 으로 확인했다).\n"
                f"· 로그: `{r['로그']}`\n"
                f"· 프로세스: `{r['프로세스'][0][:120]}`\n"
                + ("· 끝나면 각자 PDF 를 첨부해 메일로 보낸다.\n" if 메일 else "")
                + "`!회사 상태` 로 진행을 본다. 다섯 명 다 도는 데 수십 분 걸린다.")

    # ---- 한 사람 ----
    people = _people()
    후보 = " ".join(w for w in 낱말 if w not in ("메일", "mail", "보내", "gmail", "빠르게"))
    p = people.find(후보)
    if p is None:
        return (f"**누구를 말하는지 모르겠다**: `{후보}`\n\n" + _도움())
    if _도나():
        return ("**이미 돌고 있다.** `!회사 상태` 로 확인해라 — "
                "두 벌 띄우면 같은 `house/out/` 파일을 서로 덮는다.")
    # 회로 이름이 같이 왔나
    회로 = None
    try:
        sys.path.insert(0, str(REPO))
        from house import designs as DES
        표 = DES.읽기()
        for w in 낱말[1:]:
            k = w.strip().lower()
            if k in 표:
                회로 = k
                break
    except Exception:                                        # noqa: BLE001
        pass
    인자 = [p.키] + (["--회로", 회로] if 회로 else []) \
        + (["--메일"] if 메일 else []) + (["--빠르게"] if "빠르게" in 낱말 else [])
    r = _띄우기(인자, p.키)
    if not r["떴나"]:
        return f"**못 띄웠다.** 로그: `{r['로그']}`"
    return (f"**{p.name}** ({p.team} / {p.title}) 에게 "
            + (f"회로 `{회로}` 를 " if 회로 else "") + "넘겼다.\n"
            f"· 맡은 것: {p.tagline}\n"
            f"· 로그: `{r['로그']}`\n"
            + ("· 끝나면 보고서 PDF 를 첨부해 메일로 보낸다.\n" if 메일
               else "· 끝나면 `house/out/` 에 PDF 가 생긴다. 메일까지 보내려면 "
                    f"`!회사 {p.키} 메일`.\n")
            + "`!회사 상태` 로 진행을 본다.")
