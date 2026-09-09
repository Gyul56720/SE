"""**오답노트는 원장이다.** 기억이 아니라.

    문제  ->  시도  ->  틀린 것만 모아 놓은 것이 오답노트
                        |
                   태그별로 세면 취약점, 확인된 취약점만 모으면 교안

## 왜 원장이어야 하나

"너는 확률에 약해" 는 세 문제 틀리고도 할 수 있는 말이다. 그런데 세 문제로는
**아무것도 못 가른다** -- 그 말이 맞는지 틀린지 아무도 모르고, 학생은 맞는 말인 줄
알고 엉뚱한 데 시간을 쓴다. 그래서 취약점은 **세어서** 말한다(`study/weak.py`).
세려면 남아 있어야 하고, 남기는 자리가 여기다.

## 채점을 억지로 하지 않는다

객관식·단답은 글자를 맞춰 보면 된다. 서술형은 **모른다** 를 돌려준다 -- 사람이
정한다. 여기서 맞다고 우기면 그 우김이 원장에 박히고, 취약점 판정이 그 위에서
돌아간다. 지어낸 수가 보고서에 박히는 것과 똑같은 자리다.

## 한 줄이 한 시도다

같은 문제를 다시 풀면 **줄이 하나 더 는다.** 덮어쓰지 않는다 -- 두 번째에 맞혔다는
것이 첫 번째에 틀렸다는 것을 지우지 않고, 오히려 그 둘이 같이 있어야 늘었는지를 안다.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

기본자리 = Path(__file__).resolve().parent / "공책"


@dataclass
class 문제:
    id: str
    말: str = ""
    정답: str = ""
    태그: list = field(default_factory=list)   # 무엇을 묻는 문제인가 (자유롭게)
    보기: list = field(default_factory=list)   # 객관식이면
    해설: str = ""
    출처: str = ""                             # 어디서 왔나. 비면 지어낸 것으로 다룬다


@dataclass
class 시도:
    문제id: str
    낸답: str = ""
    맞았나: bool | None = None                 # **None = 아직 안 정해졌다**
    언제: str = ""
    걸린초: float = 0.0
    메모: str = ""                             # 학생이 쓴 풀이·왜 틀렸다고 보는지
    짚은것: str = ""                           # 나중에 붙이는 취약점 분석
    # **안 쓴다.** 한때 틀릴 때마다 "오답인가 모름인가" 를 1·2 로 물었는데 사용자가
    # 뺐다(2026-09-09: "그냥 1,2(모른다 틀렸다)번 나누지 말자"). 묻는 걸음이 하나
    # 늘면 그만큼 안 적히고, 안 적히면 셈에 안 들어간다 -- 갈래를 알아도 사유가
    # 없으면 아무것도 못 하는데 갈래부터 물으면 사유까지 못 간다.
    # 필드는 남긴다: 이미 저장된 줄에 있고, 지우면 그 줄을 못 읽는다.
    갈래: str = ""
    # 그 갈래 안에서 **무엇인가.** 오답이면 어긋난 곳, 모름이면 모르는 유형.
    # 이것이 취약점의 알맹이다 -- 태그(과목)가 아니라 이것을 센다.
    사유: str = ""


@dataclass
class 공책:
    문제: dict = field(default_factory=dict)   # id -> 문제
    시도: list = field(default_factory=list)

    def 넣기(self, q: 문제) -> 문제:
        self.문제[q.id] = q
        return q

    def 푼것(self) -> set:
        return {a.문제id for a in self.시도}

    def 안푼것(self, 태그: str = "") -> list:
        푼 = self.푼것()
        return [q for q in self.문제.values()
                if q.id not in 푼 and (not 태그 or 태그 in q.태그)]

    def 사유없는것(self) -> list:
        """틀렸는데 **무엇이 어긋났는지** 안 적힌 것. 셈에 안 들어간다."""
        return [a for a in self.시도 if a.맞았나 is False and not a.사유]

    def 틀린것(self) -> list:
        """**틀린 시도만.** 아직 안 정해진 것(None)은 틀린 것이 아니다."""
        return [a for a in self.시도 if a.맞았나 is False]

    def 마지막(self, qid: str):
        for a in reversed(self.시도):
            if a.문제id == qid:
                return a
        return None


# ── 채점 ─────────────────────────────────────────────────────────────
_정리 = re.compile(r"[\s,]+")


def _고르게(s: str) -> str:
    """견줄 수 있게 고른다. **뜻은 안 본다** -- 뜻을 보는 순간 짐작이 된다."""
    s = unicodedata.normalize("NFKC", str(s or "")).strip().lower()
    s = _정리.sub("", s)
    return s.rstrip(".)。")


def _수인가(s: str):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def 채점(정답: str, 낸답: str):
    """맞았나. **모르면 None** -- 사람이 정한다.

    억지로 참·거짓을 내지 않는다. 서술형을 글자로 맞춰 놓고 '틀렸다' 고 적으면 그
    거짓이 원장에 박히고 취약점 판정이 그 위에서 돈다.
    """
    if not str(정답 or "").strip() or not str(낸답 or "").strip():
        return None
    a, b = _고르게(정답), _고르게(낸답)
    if a == b:
        return True
    x, y = _수인가(정답), _수인가(낸답)
    if x is not None and y is not None:
        return abs(x - y) < 1e-9
    # 짧은 것(객관식 기호·단답)은 다르면 다른 것이다
    if len(a) <= 12 and len(b) <= 12:
        return False
    # 긴 답은 **모른다.** 겹치는 낱말이 많다고 맞은 것이 아니다
    return None


# ── 저장 ─────────────────────────────────────────────────────────────
def 지금() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def 저장(n: 공책, 자리: Path = None) -> Path:
    자리 = Path(자리 or 기본자리)
    자리.mkdir(parents=True, exist_ok=True)
    (자리 / "문제.jsonl").write_text(
        "\n".join(json.dumps(asdict(q), ensure_ascii=False)
                  for q in n.문제.values()) + "\n" if n.문제 else "",
        encoding="utf-8")
    (자리 / "시도.jsonl").write_text(
        "\n".join(json.dumps(asdict(a), ensure_ascii=False)
                  for a in n.시도) + "\n" if n.시도 else "",
        encoding="utf-8")
    return 자리


def _줄들(p: Path):
    if not p.exists():
        return
    for 줄 in p.read_text(encoding="utf-8").splitlines():
        줄 = 줄.strip()
        if not 줄:
            continue
        try:
            d = json.loads(줄)
        except json.JSONDecodeError:
            continue                                   # **한 줄이 깨져도 나머지는 산다**
        if isinstance(d, dict):
            yield d


def 읽기(자리: Path = None) -> 공책:
    자리 = Path(자리 or 기본자리)
    n = 공책()
    for d in _줄들(자리 / "문제.jsonl"):
        if str(d.get("id") or "").strip():
            n.문제[d["id"]] = 문제(
                id=str(d["id"]), 말=str(d.get("말") or ""),
                정답=str(d.get("정답") or ""),
                태그=[str(t) for t in (d.get("태그") or [])],
                보기=[str(t) for t in (d.get("보기") or [])],
                해설=str(d.get("해설") or ""), 출처=str(d.get("출처") or ""))
    for d in _줄들(자리 / "시도.jsonl"):
        if str(d.get("문제id") or "").strip():
            맞 = d.get("맞았나")
            n.시도.append(시도(
                문제id=str(d["문제id"]), 낸답=str(d.get("낸답") or ""),
                맞았나=None if 맞 is None else bool(맞),
                언제=str(d.get("언제") or ""), 걸린초=float(d.get("걸린초") or 0),
                메모=str(d.get("메모") or ""), 짚은것=str(d.get("짚은것") or ""),
                갈래=str(d.get("갈래") or ""), 사유=str(d.get("사유") or "")))
    return n
