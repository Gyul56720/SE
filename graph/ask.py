"""graph/ask -- 깃발만 보고 쏙 뽑는다. 그리고 원문으로 되돌아간다.

조회는 출처별 **최신** 노드만 본다(원본이 바뀌면 새 해시로 새 줄이 쌓이므로).
`--원문` 이면 출처 파일을 열어 주는데, **지금 해시가 색인의 해시와 다르면 그렇다고
말한다** -- 색인이 낡은 채 원문 행세를 하는 것이 압축 보관의 병이고, 여기는 그것을
해시 대조로 막는다.

쓰기:
    python3 graph/ask.py --말 "코인 실측"        # 깃발(가중치 3)과 요약에서 찾는다
    python3 graph/ask.py --말 촉매 --원문         # 출처 발췌까지
끝값: 0 찾았다 · 3 못 찾았다
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graph import store
else:
    from graph import store

REPO = store.REPO


def _토막(text: str) -> "list[str]":
    return [w for w in re.findall(r"[0-9a-z가-힣_.-]+", (text or "").lower()) if len(w) > 1]


def 최신들(repo=None) -> "list[dict]":
    nodes, _ = store.읽기(repo)
    최신: dict = {}
    for n in nodes:          # append-only 라 뒤가 최신이다
        최신[n["출처"]] = n
    return list(최신.values())


def 찾기(물음: str, repo=None, 최대: int = 5) -> "list[tuple[int, dict]]":
    """깃발 맞음 3점 · 요약 등장 1점. 점수 있는 것만, 높은 순."""
    terms = _토막(물음)
    if not terms:
        return []
    scored = []
    for n in 최신들(repo):
        flags = [f.lower() for f in n.get("깃발", [])]
        요약 = (n.get("요약") or "").lower()
        s = 0
        for t in terms:
            s += 3 * sum(1 for f in flags if t == f or t in f)
            s += 요약.count(t)
        if s:
            scored.append((s, n))
    scored.sort(key=lambda x: (-x[0], x[1].get("때", "")))
    return scored[:최대]


def 원문(node: dict, repo=None, 길이: int = 1200) -> "tuple[str, str]":
    """(경고, 발췌). 원본이 없거나 해시가 어긋나면 경고에 그대로 적는다."""
    repo = Path(repo or REPO)
    p = repo / node.get("출처", "")
    if not p.is_file():
        return ("원본이 없다 -- 색인만 남았다. 지운 것인지 옮긴 것인지 확인하라", "")
    경고 = ""
    if store.해시(p) != node.get("해시"):
        경고 = ("**원본이 그때와 다르다**(해시 어긋남) -- 색인이 낡았다. "
               "`graph/night.py` 를 다시 돌리면 새 줄로 간추려진다")
    return 경고, p.read_text(encoding="utf-8", errors="replace")[:길이]


def 한줄(score: int, n: dict) -> str:
    return f"[{'·'.join(n.get('깃발', [])[:6])}] {n.get('요약', '')[:160]} <{n.get('출처', '')}>"


def main() -> int:
    ap = argparse.ArgumentParser(description="깃발 색인에서 찾는다")
    ap.add_argument("--말", required=True, help="깃발이나 낱말 (띄어쓰기로 여럿)")
    ap.add_argument("--원문", action="store_true")
    ap.add_argument("--최대", type=int, default=5)
    args = ap.parse_args()
    hits = 찾기(args.말, 최대=args.최대)
    _, 깨진 = store.읽기()
    if 깨진:
        print(f"(원장에 깨진 줄 {깨진}개 -- 세어만 두고 건너뛰었다)")
    if not hits:
        print("깃발에 걸린 것이 없다. `python3 graph/night.py` 로 간추린 것이 있는지부터 보라.")
        return 3
    for s, n in hits:
        print(f"{s:>3}  {한줄(s, n)}")
        if args.원문:
            경고, 글 = 원문(n)
            if 경고:
                print(f"     ! {경고}")
            for line in 글.splitlines()[:12]:
                print(f"     | {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
