# -*- coding: utf-8 -*-
"""house/approve -- **사람이 본 제안서와 지금 짓는 스펙을 잇는다.**

## 왜 있나

`house/flow.py` 의 흐름 그림에 `제안서 -> 사람 승인 -> RTL·TB 생성` 이 있고
`run.승인하기()` 의 docstring 은 이렇게 적고 있었다.

    **제안서를 낸 그 스펙 그대로 짓는다.** 요청 글을 다시 읽지 않는다 --
    다시 읽으면 모델이 또 다르게 채우고, 그러면 **사람이 본 것과 다른 것을
    짓게 된다.**

맞는 말인데 **그것을 확인하는 것이 아무것도 없었다.** 스펙 파일이 제안서와
승인 사이에 바뀌어도 아무도 모른다. 그리고 **누가 언제 승인했는지도 안 남는다.**

## 이 파일이 죄는 것 · 죄지 못하는 것

    죈다     사람이 본 제안서의 스펙과 지금 짓는 스펙이 **같은 것인가** (sha256)
    죈다     승인할 때 **모르는 칸이 무엇이었는지** 기록에 남았는가
    못 죈다  **누가** 승인했는지 -- 디스코드 이름을 그대로 적을 뿐이다

셋째를 숨기지 않는다. 이 저장소에 신원을 확인할 길이 없다. 그러니 이 기록은
*서명*이 아니라 **이력**이다 -- 그렇게 읽히게 관문 글에 적는다.

## 모르는 칸을 조용히 기본값으로 채우지 않는다

제안서에 `모른다` 가 넷 남아 있으면 디스코드가 이렇게 알린다.

    ⚠ **아직 모르는 것이 4개 남아 있습니다** — 그 칸은 기본값으로 채워집니다

그런데 승인하면 그냥 지어졌다. 지금은 **승인 기록이 그 목록을 안고 있고**,
관문 0b 가 *제안 때의 모른다* 와 *승인 기록의 알고승인한것* 이 같은지 본다.
새 모른다가 생겼는데 아무도 안 봤으면 빨갛다.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
스펙방 = 뿌리 / "스펙"


def 스펙해시(s) -> str:
    """스펙의 내용 해시.  **정렬해서 찍는다** -- 칸 차례가 바뀌어도 같은 스펙이다."""
    사전 = s.사전() if hasattr(s, "사전") else dict(s)
    글 = json.dumps(사전, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(글.encode("utf-8")).hexdigest()


def 제안길(키: str) -> Path:
    return 스펙방 / f"{키}.제안.json"


def 승인길(키: str) -> Path:
    return 스펙방 / f"{키}.승인.json"


def 제안적기(키: str, s) -> Path:
    """제안서를 낼 때 **그때의 스펙 해시와 모르는 칸**을 박아 둔다."""
    스펙방.mkdir(parents=True, exist_ok=True)
    길 = 제안길(키)
    길.write_text(json.dumps({
        "키": 키, "스펙_sha256": 스펙해시(s),
        "낸때": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "모른다": list(getattr(s, "모른다", []) or []),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 길


def 승인적기(키: str, 누가: str, 말: str = "") -> dict:
    """사람이 승인했다는 이력.  **제안 기록이 없으면 안 적는다.**

    제안 없이 승인 기록만 있으면 '사람이 본 것' 이 무엇인지 모른다 -- 그
    기록은 아무것도 잇지 못하므로 만들지 않는다.
    """
    p = 제안길(키)
    if not p.is_file():
        return {"됐나": False, "까닭": f"제안 기록이 없다: {p.name}"}
    try:
        제안 = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"됐나": False, "까닭": f"제안 기록을 못 읽었다: {e}"}
    스펙방.mkdir(parents=True, exist_ok=True)
    d = {"키": 키, "누가": (누가 or "").strip(),
         "언제": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "스펙_sha256": 제안.get("스펙_sha256"),
         "알고승인한것": list(제안.get("모른다") or []),
         "말": (말 or "").strip()}
    승인길(키).write_text(json.dumps(d, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    return {"됐나": True, "기록": d, "길": str(승인길(키))}


def 읽기(키: str) -> dict:
    """{제안, 승인, 오류}.  없으면 None -- **없는 것을 지어내지 않는다.**"""
    난것 = {"제안": None, "승인": None, "오류": ""}
    for 이름, 길 in (("제안", 제안길(키)), ("승인", 승인길(키))):
        if not 길.is_file():
            continue
        try:
            난것[이름] = json.loads(길.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            난것["오류"] += f"{길.name} 을 못 읽었다: {e}; "
    return 난것
