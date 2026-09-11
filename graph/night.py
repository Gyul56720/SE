"""graph/night -- 밤일. 쌓인 기록을 간추려 깃발 색인으로 만든다.

사람이 잘 때 기억이 굳는 것에서 이름을 땄지만, **버리는 압축이 아니다** -- 원본은
git 에 그대로 있고 여기서는 깃발+요약+해시(찾는 길)만 만든다. 지우는 쪽 밤일은
따로 있다(`memory_hygiene.py` -- 코드와 모순된 노트를 지운다). 둘은 다른 일이라
두 벌이 아니다: 거기는 잊기, 여기는 간추리기.

무엇을 간추리나: public_agent_memory/*.md (에이전트가 쌓는 노트) · reports/*.md.
이미 같은 해시로 간추린 것은 건너뛴다 -- 밤마다 돌려도 원장이 안 부푼다. 원본이
바뀌었으면 새 줄로 다시 간추린다(조회는 최신만 본다).

깃발은 **코드가 뽑는다**(파일 이름 · topic 머리말 · 본문 잦은 낱말 · 연월). 모델로
깃발을 보태는 것은 아직 안 한다 -- 지어낸 깃발은 지어낸 색인이고, 그때는 요약이
원문과 맞는지 재는 검사부터 있어야 한다(HARNESS_PLAN 2단계의 남은 일).

쓰기:
    python3 graph/night.py            # 간추린다 (몇 개 적었는지 말한다)
    python3 graph/night.py --보고만    # 무엇을 간추릴지 보기만
밤 루프로 돌리려면 scripts/night.sh (setsid 패턴은 CLAUDE.md).
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graph import store
else:
    from graph import store

REPO = store.REPO
간추릴곳 = ("public_agent_memory", "reports")

_불용 = {"그", "이", "저", "것", "수", "등", "및", "때", "안", "위해", "대한", "있다",
        "없다", "한다", "된다", "하는", "않는", "the", "and", "for", "with", "this",
        "that", "was", "are", "not"}
_말꼴 = re.compile(r"[0-9A-Za-z가-힣_.-]{2,}")


def _머리말(text: str) -> "tuple[str, str]":
    """(topic, 본문). frontmatter(--- ... ---)가 있으면 topic 을 뽑고 본문에서 뗀다."""
    topic = ""
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            head, body = text[:end], text[end + 4:]
            m = re.search(r"^topic:\s*['\"]?(.+?)['\"]?\s*$", head, re.M)
            if m:
                topic = m.group(1)
    return topic, body


def 깃발뽑기(이름: str, topic: str, 본문: str) -> "list[str]":
    """파일 이름 조각 + topic 조각 + 본문에서 잦은 낱말 + 연월. 전부 코드가 뽑는다."""
    깃발: list[str] = []
    m = re.match(r"(\d{6})", 이름)
    if m:
        깃발.append(m.group(1))          # 연월 -- "그때쯤 그거" 로 찾는 길
    for 조각 in _말꼴.findall(이름) + _말꼴.findall(topic):
        if not 조각.isdigit() and 조각.lower() not in _불용:
            깃발.append(조각)
    잦은 = Counter(w.lower() for w in _말꼴.findall(본문)
                  if not w.isdigit() and w.lower() not in _불용)
    깃발.extend(w for w, c in 잦은.most_common(5) if c >= 2)
    return store.깃발정리(깃발)


def 요약뽑기(본문: str, 길이: int = 500) -> str:
    return " ".join(본문.split())[:길이]


def 대상들(repo: Path) -> "list[Path]":
    out: list[Path] = []
    for d in 간추릴곳:
        base = repo / d
        if base.is_dir():
            out.extend(sorted(base.glob("*.md")))
    return out


def 간추리기(repo=None, 적기=True) -> dict:
    """돌고 나서 {적음: [...], 그대로: n, 거절: [...]} 를 돌려준다."""
    repo = Path(repo or REPO)
    nodes, _ = store.읽기(repo)
    이미 = {(n.get("출처"), n.get("해시")) for n in nodes}
    적음, 거절 = [], []
    그대로 = 0
    for p in 대상들(repo):
        rel = str(p.relative_to(repo))
        if (rel, store.해시(p)) in 이미:
            그대로 += 1
            continue
        topic, body = _머리말(p.read_text(encoding="utf-8", errors="replace"))
        if not 적기:
            적음.append(rel)
            continue
        try:
            r = store.적기(요약뽑기(body), 깃발뽑기(p.name, topic, body), rel, repo=repo)
        except ValueError as e:
            거절.append(f"{rel}: {e}")
            continue
        if r == "적었다":
            적음.append(rel)
        else:
            그대로 += 1
    return {"적음": 적음, "그대로": 그대로, "거절": 거절}


def main() -> int:
    ap = argparse.ArgumentParser(description="쌓인 기록을 깃발 색인으로 간추린다")
    ap.add_argument("--보고만", action="store_true", help="적지 않고 무엇을 간추릴지만")
    args = ap.parse_args()
    r = 간추리기(적기=not args.보고만)
    동사 = "간추릴 것" if args.보고만 else "간추림"
    print(f"{동사} {len(r['적음'])}개 · 이미 있음 {r['그대로']}개 · 거절 {len(r['거절'])}개")
    for rel in r["적음"][:20]:
        print(f"  + {rel}")
    for why in r["거절"]:
        print(f"  ! {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
