"""graph/store -- 기억의 원장. append-only JSONL, git 이 버전이다.

**압축 '색인'이지 압축 '보관'이 아니다.** 원본을 줄여서 보관하면 줄인 것을 아무도 못
되찾는다(dig/README.md 가 같은 자리에서 배운 것). 그래서 원본은 git 에 그대로 두고,
여기에는 **찾는 길**만 쌓는다: 깃발(꼬리표) + 요약 + 출처 경로 + 원본 해시.

노드 한 줄 = {"때", "깃발": [...], "요약", "출처", "해시", "글자수"}

거절 규칙(원장 대조 규율 그대로):
  - 깃발 없는 노드는 거절한다 -- 깃발 없는 기억은 못 되찾는다.
  - 출처가 실재하지 않으면 거절한다 -- 출처 없는 간선 금지(HARNESS_PLAN 2단계).
  - 출처는 저장소 안 상대경로만(G014 규율).
  - 같은 (출처, 해시) 는 다시 안 적는다 -- 원본이 바뀌면 해시가 달라져 새 줄이 쌓이고,
    조회는 출처별 최신을 본다(역사는 append-only 라 그대로 남는다).

읽을 때 깨진 줄은 건너뛰되 개수를 함께 돌려준다 -- 조용히 사라지면 없는 것으로 읽힌다.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
원장상대 = "graph/ledger.jsonl"

깃발꼴 = re.compile(r"[0-9a-z가-힣_.-]{1,40}")
요약상한 = 800
깃발상한 = 12


def _원장(repo=None) -> Path:
    return Path(repo or REPO) / 원장상대


def 해시(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def _출처검사(repo: Path, 출처: str) -> Path:
    rel = (출처 or "").strip()
    if not rel or rel.startswith(("/", "~")) or any(p == ".." for p in Path(rel).parts):
        raise ValueError(f"출처는 저장소 안 상대경로만 된다: {출처!r}")
    p = (repo / rel).resolve()
    rp = repo.resolve()
    if p != rp and rp not in p.parents:
        raise ValueError(f"저장소 밖으로 풀리는 출처다: {출처!r}")
    return p


def 읽기(repo=None) -> "tuple[list[dict], int]":
    """(노드들, 깨진 줄 수). 깨진 줄은 건너뛰지만 세어서 말한다."""
    path = _원장(repo)
    if not path.is_file():
        return [], 0
    nodes, 깨진 = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            n = json.loads(line)
        except ValueError:
            깨진 += 1
            continue
        if isinstance(n, dict) and n.get("출처") and n.get("깃발"):
            nodes.append(n)
        else:
            깨진 += 1
    return nodes, 깨진


def 깃발정리(깃발들) -> "list[str]":
    out: list[str] = []
    for f in 깃발들 or []:
        f = str(f).strip().lower()
        if f and 깃발꼴.fullmatch(f) and f not in out:
            out.append(f)
    return out[:깃발상한]


def 적기(요약: str, 깃발들, 출처: str, repo=None) -> str:
    """노드 한 줄을 원장에 붙인다. '적었다' 또는 '이미 있다'. 성하지 않으면 ValueError."""
    repo = Path(repo or REPO)
    요약 = " ".join((요약 or "").split())[:요약상한]
    if not 요약:
        raise ValueError("요약이 비었다")
    깃발 = 깃발정리(깃발들)
    if not 깃발:
        raise ValueError("깃발이 없다 -- 깃발 없는 기억은 못 되찾는다")
    src = _출처검사(repo, 출처)
    if not src.is_file():
        raise ValueError(f"출처가 실재하지 않는다: {출처!r}")
    h = 해시(src)
    nodes, _ = 읽기(repo)
    if any(n.get("출처") == 출처 and n.get("해시") == h for n in nodes):
        return "이미 있다"
    node = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "깃발": 깃발, "요약": 요약, "출처": 출처, "해시": h,
            "글자수": src.stat().st_size}
    path = _원장(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(node, ensure_ascii=False) + "\n")
    return "적었다"
