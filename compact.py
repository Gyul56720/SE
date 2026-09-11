"""compact -- 대화가 길어지면 **코드가** 간추려 메모로 남기고 실(thread)을 새로 잇는다.

격차표(SE vs Claude Code) '맥락 관리': MemorySaver 는 인메모리라 재시작에 사라지고, 긴 대화는
컨텍스트가 넘쳐 깨진다. Claude Code 는 자동 요약(compaction)을 한다. 여기서는 **이미 있는
기관으로** 한다 -- 메모는 public_agent_memory 에 쓰고(graph/night 가 밤에 색인·장기기억으로),
새 실의 첫 말에는 깃발만 넣는다. 요지는 모델이 아니라 코드가 만든다(사람 말·부른 도구·
실패 줄·마지막 답 머리) -- 지어낼 자리가 없다.

    판정: len(messages) >= 상한(CONTEXT_TURN_CAP, 기본 40) 이면 간추린다.
    끝:  public_agent_memory/<때>_대화_<thread>.md + 씨앗[thread] (다음 프롬프트 머리에 한 번)
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
메모곳 = "public_agent_memory"
상한 = int(os.environ.get("CONTEXT_TURN_CAP", "40") or 40)
씨앗: dict[str, str] = {}          # base_thread_id -> 새 실 첫 프롬프트에 붙일 한 줄


def _꼴(m) -> str:
    t = getattr(m, "type", None) or (m.get("type") if isinstance(m, dict) else None) or ""
    return str(t)


def _글(m) -> str:
    c = getattr(m, "content", None)
    if c is None and isinstance(m, dict):
        c = m.get("content")
    if isinstance(c, list):
        c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return str(c or "")


def _도구이름들(m) -> "list[str]":
    calls = getattr(m, "tool_calls", None) or (m.get("tool_calls") if isinstance(m, dict) else None) or []
    out = []
    for c in calls:
        n = c.get("name") if isinstance(c, dict) else getattr(c, "name", None)
        if n:
            out.append(str(n))
    return out


def 간추릴때(messages, 상한값: int = None) -> bool:
    return len(messages or []) >= (상한값 if 상한값 is not None else 상한)


def 요지(messages) -> dict:
    """코드가 만드는 요지 -- 사람 말 · 부른 도구 · 실패 줄 · 마지막 답 머리. 모델 호출 0회."""
    사람말, 도구들, 실패들, 마지막답 = [], [], [], ""
    for m in messages or []:
        꼴 = _꼴(m)
        if 꼴 == "human":
            g = _글(m).strip()
            if g and not g.startswith("[이어짐]") and not g.startswith("[하네스 검사]"):
                사람말.append(re.sub(r"\s+", " ", g)[:120])
        elif 꼴 == "ai":
            도구들 += _도구이름들(m)
            g = _글(m).strip()
            if g:
                마지막답 = re.sub(r"\s+", " ", g)[:200]
        elif 꼴 == "tool":
            g = _글(m)
            if re.search(r"실패|거절|Error|Traceback|막힘|못 ", g):
                실패들.append(re.sub(r"\s+", " ", g.strip())[:100])
    본 = set()
    깃발 = [d for d in 도구들 if not (d in 본 or 본.add(d))]
    return {"사람말": 사람말, "깃발": 깃발, "실패": 실패들[-5:], "마지막답": 마지막답, "줄수": len(messages or [])}


def 간추리기(base_thread_id: str, messages, repo=None) -> "tuple[str, str]":
    """메모를 쓰고 씨앗을 남긴다. 돌려주는 것: (메모 상대경로, 씨앗 한 줄)."""
    repo = Path(repo or REPO)
    r = 요지(messages)
    때 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    안전 = re.sub(r"[^0-9A-Za-z_-]+", "_", str(base_thread_id))[:40] or "thread"
    p = repo / 메모곳 / f"{때}_대화_{안전}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = ["---", f"topic: '대화 간추림: {안전}'", "---", "",
         f"# 대화 간추림 ({r['줄수']}줄 -> 새 실)", "",
         "## 사람이 시킨 것"] + [f"- {s}" for s in r["사람말"][-12:]]
    줄 += ["", "## 부른 도구(깃발)", "- " + (", ".join(r["깃발"]) or "(없음)")]
    if r["실패"]:
        줄 += ["", "## 실패·거절 줄"] + [f"- {s}" for s in r["실패"]]
    줄 += ["", "## 마지막 답 머리", r["마지막답"] or "(없음)", ""]
    p.write_text("\n".join(줄), encoding="utf-8")
    상대 = str(p.relative_to(repo))
    씨앗줄 = (f"[이어짐] 앞 대화 {r['줄수']}줄은 코드가 간추려 `{상대}` 에 남겼다 -- 깃발: "
            + (", ".join(r["깃발"][:8]) or "(도구 없음)")
            + (f" · 마지막 부탁: {r['사람말'][-1]}" if r["사람말"] else "")
            + ". 자세한 것은 search_memory 로 읽어라.\n\n")
    씨앗[str(base_thread_id)] = 씨앗줄
    return 상대, 씨앗줄


def 씨앗꺼내기(base_thread_id: str) -> str:
    return 씨앗.pop(str(base_thread_id), "")
