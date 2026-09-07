"""**공간 원장** -- 후보가 아니라 *형식화*를 적는다.

`mathgen` 은 문제를 만들고 `novel/flow.py` 는 원고를 만든다. 여기서 만드는 것은 둘 다
아니다. **탐색공간 자체**다.

왜 한 층 올렸나. b=3 m=22 는 같은 공간(실수 CP 분해)을 CP-ALS · 무작위 재시작 · 강화학습 ·
flip graph 로 여러 번 훑어 소진됐다. 고정된 공간 안의 탐색은 정의상 최적화이고, 최적화는
자기가 받은 형식화를 떠나지 못한다. 역사적으로 이 문제를 뚫은 것은 전부 **공간을 갈아탄
것**이었다 -- 랭크에서 경계 랭크로(Schönhage), 텐서에서 군대수로(Cohn-Umans).

그래서 원장의 원소는 점이 아니라 공간이다. 그리고 **공간은 틀릴 수 없다.** 쓸모없을 뿐이다.
틀린 정리는 원장을 오염시키지만 빈 공간은 탐색해봐야 아무것도 안 나올 뿐이라, 발산
단계에서 엄밀성을 요구할 이유가 없다.

## 인과성은 검사하지 않는다 -- 구성으로 보장한다

`mathgen` 의 거꾸로 만들기와 같은 수다. 거기서는 답 F 를 먼저 골라 f = F' 를 문제로 내니
정답이 구성상 확실했다. 여기서는:

    새 공간 = 연산자(원장에 이미 있는 공간)

모델에게 "공간을 발명하라" 고 묻지 않는다. "여기 공간 S 가 있다, 여기 *경계화* 를 걸어라,
무엇이 되나" 라고 묻는다. 부모는 항상 원장에 있고 연산자는 고정 목록에서 나오므로
**계보 칸은 비거나 지어낼 수가 없다.** 인과성이 검사 항목이 아니라 문법이 된다.

## 칸을 비워도 기각하지 않는다

빈 칸은 나중에 채울 것이지 탈락 사유가 아니다. 이번 단계에서 죽이는 것은 없다 --
`novel/DRIFT.md` 의 첫 규칙 그대로다: *과잉 기각은 글 자체를 없앤다.* 다만 `되사상`
(이 공간의 점이 원래 문제로 어떻게 돌아가나)이 비면 나중에 검증이 아예 불가능하므로,
기각은 안 하되 **등급을 '검증불가'로 적어 둔다.**
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PATH = Path(os.environ.get("MATHDRIFT_LEDGER",
                           Path(__file__).resolve().parent / "ledger.json"))

# 공간 하나가 갖는 칸. **전부 비어도 받는다.**
FIELDS = ("이름", "점", "표기", "되사상", "크기", "왜")

# `되사상` 만은 특별하다 -- 비면 이 공간의 후보를 원래 문제와 견줄 길이 없다.
# 그래도 버리지 않는다. 다음 세대의 부모로는 쓸 수 있기 때문이다.
NEEDED = "되사상"

GRADES = ("미검증", "검증불가", "생존", "사망")


def blank() -> dict:
    return {"seq": 0, "spaces": [], "ops_used": {}}


def load(path=None) -> dict:
    p = Path(path or PATH)
    if not p.exists():
        return blank()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return blank()
    for k, v in blank().items():
        d.setdefault(k, v)
    return d


def save(led: dict, path=None) -> None:
    p = Path(path or PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")


def get(led: dict, sid: str) -> dict | None:
    for s in led["spaces"]:
        if s.get("id") == sid:
            return s
    return None


def grade(rec: dict) -> str:
    """등급은 내용을 판정하지 않는다. **칸이 찼는가만 본다.**

    "이 공간이 쓸모있는가" 는 검증 단계(다음 커밋)의 물음이다. 여기서 그것을 흉내내면
    발산이 죽는다.
    """
    if not (rec.get(NEEDED) or "").strip():
        return "검증불가"
    return "미검증"


def add(led: dict, rec: dict, parent: str, op: str, dist: int = 1) -> dict:
    """공간 하나를 원장에 올린다. **부모와 연산자 없이는 올릴 수 없다.**

    이 서명이 인과성을 강제하는 자리다. `parent` 가 원장에 없으면 거절한다 -- 내용을
    판정해서 거절하는 것이 아니라, 계보가 끊긴 것을 원장이 못 받게 하는 것이다.
    """
    if parent != "-" and get(led, parent) is None:
        raise ValueError(f"부모 {parent} 가 원장에 없다 -- 계보가 끊긴 공간은 안 받는다")
    led["seq"] += 1
    out = {"id": f"S{led['seq']}"}
    for f in FIELDS:
        out[f] = (rec.get(f) or "").strip() if isinstance(rec.get(f), str) else rec.get(f, "")
    out["계보"] = {"부모": parent, "연산자": op, "거리": dist}
    out["등급"] = grade(out)
    out["잰것"] = {}
    led["spaces"].append(out)
    led["ops_used"][op] = led["ops_used"].get(op, 0) + 1
    return out


def lineage(led: dict, sid: str) -> list[str]:
    """씨앗까지 거슬러 올라간 사슬. 계보가 사슬로 남는다는 것이 이 설계의 요점이다."""
    chain, cur, seen = [], sid, set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        rec = get(led, cur)
        if not rec:
            break
        cur = (rec.get("계보") or {}).get("부모")
        if cur == "-":
            break
    return list(reversed(chain))


def brief(led: dict, limit: int = 30) -> str:
    out = []
    for s in led["spaces"][-limit:]:
        g = s["계보"]
        out.append(f"  {s['id']:<5} {s.get('이름','')[:34]:<36} "
                   f"<- {g['부모']} / {g['연산자']} (거리 {g['거리']}) [{s['등급']}]")
    return "\n".join(out)
