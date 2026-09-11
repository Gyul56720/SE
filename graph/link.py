"""graph/link -- 다섯 꼴 간선. 판정은 코드가 내고, 못 내는 꼴은 관할 밖이라 말한다.

brain 의 닫힌 다섯 꼴을 기억 색인 도메인에 그대로 옮겼다. **간선 종류를 새로 발명하지
않는다** -- 검사기 자체가 열리면 검사기를 검사할 것이 없어진다(brain 규율).

| 꼴 | 여기서 묻는 것 | 판정 |
|---|---|---|
| 대조   | 노드의 요약·깃발이 원문에 서 있는가 (verify.대조) | 맞음/어긋남/미검증 |
| 재계산 | 해시·글자수를 다시 세면 같은가                    | 같음/다름/못셈 |
| 기준선 | 깃발이 원장 분포에서 이례인가 (새 갈래인가)       | 이례/평범/못잼 |
| 뒤집기 | 깃발 몇 개가 저를 되찾는가 (하나에 매달렸나)      | 굳음/약함/못잼 |
| 연역   | 전제에서 따라 나오는가                            | **관할 밖** |

연역만 판정이 없는 것은 못 만드는 것이 아니라 **만들면 안 되는 것**이다: 색인에는
전제가 없고, 그 판정기는 이미 reason/ask.py 에 있다. 여기서 두 벌을 만들면 두 벌은
갈라진다. 관할 밖은 실패가 아니다 -- 적는 것이 규율이다(brain R004).

간선은 판정 '사건' 의 기록이다: edges.jsonl 에 append-only 로 남고, 어긋남도 지우지
않는다(어긋남은 지우는 것이 아니라 보는 것이다). 같은 (꼴, 출처)의 직전 간선과 판정·
해시가 같으면 다시 안 적는다 -- 밤마다 돌려도 안 부푼다.

쓰기:
    python3 graph/link.py --출처 <상대경로>   # 그 노드를 판정하고 간선을 적는다
    python3 graph/link.py --전부              # 최신 노드 전부
    python3 graph/link.py --보기 [--출처 ...]  # 적힌 간선을 본다 (판정 안 함)
끝값: 0 어긋남 없음 · 1 어긋남/다름 있음 · 3 노드를 못 찾음
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graph import ask, store, verify
else:
    from graph import ask, store, verify

REPO = store.REPO
간선상대 = "graph/edges.jsonl"
기준선_최소원장 = 10

빨간판정 = ("어긋남", "다름")
관할밖_연역 = ("연역: 관할 밖 -- 색인에는 전제가 없다. 전제→결론 판정은 reason/ask.py 가 "
            "한다. 여기서 지어내지 않는다")


def _간선원장(repo=None) -> Path:
    return Path(repo or REPO) / 간선상대


def 간선읽기(repo=None) -> "list[dict]":
    path = _간선원장(repo)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("꼴") and e.get("출처"):
            out.append(e)
    return out


def 최근판정(출처: str, repo=None) -> "dict[str, dict]":
    """꼴 -> 그 출처의 마지막 간선. ask 가 결과 옆에 보여줄 때 쓴다."""
    out: dict = {}
    for e in 간선읽기(repo):
        if e.get("출처") == 출처:
            out[e["꼴"]] = e
    return out


def _대조(node: dict, repo: Path) -> dict:
    p = repo / node["출처"]
    if not p.is_file():
        return {"꼴": "대조", "판정": "미검증", "근거": "원본이 없다 -- 색인만 남았다"}
    r = verify.대조(node.get("요약", ""), node.get("깃발", []),
                   p.read_text(encoding="utf-8", errors="replace"), 이름=p.name)
    근거 = "; ".join(r["위반"]) if r["위반"] else \
        (f"낱말 근거율 {r['근거율']:.0%}" if r["근거율"] is not None else "잰 것 없음")
    return {"꼴": "대조", "판정": r["판정"], "근거": 근거}


def _재계산(node: dict, repo: Path) -> dict:
    p = repo / node["출처"]
    if not p.is_file():
        return {"꼴": "재계산", "판정": "못셈", "근거": "원본이 없다"}
    지금해시 = store.해시(p)
    지금글자 = p.stat().st_size
    같다 = 지금해시 == node.get("해시") and 지금글자 == node.get("글자수")
    return {"꼴": "재계산", "판정": "같음" if 같다 else "다름",
            "근거": f"해시 {node.get('해시')}→{지금해시} · 크기 {node.get('글자수')}→{지금글자}"}


def _기준선(node: dict, repo: Path) -> dict:
    남들 = [n for n in ask.최신들(repo) if n.get("출처") != node.get("출처")]
    if len(남들) + 1 < 기준선_최소원장:
        return {"꼴": "기준선", "판정": "못잼",
                "근거": f"원장이 {len(남들) + 1}개뿐 -- {기준선_최소원장}개는 있어야 분포가 선다"}
    남의깃발 = {f for n in 남들 for f in n.get("깃발", [])}
    내깃발 = [f for f in node.get("깃발", []) if not verify.연월꼴.fullmatch(f)]
    if not 내깃발:
        return {"꼴": "기준선", "판정": "못잼", "근거": "연월 말고는 깃발이 없다"}
    저만의것 = [f for f in 내깃발 if f not in 남의깃발]
    이례 = len(저만의것) * 2 >= len(내깃발)
    return {"꼴": "기준선", "판정": "이례" if 이례 else "평범",
            "근거": f"깃발 {len(내깃발)}개 중 {len(저만의것)}개가 저만의 것"
                   + (f" ({', '.join(저만의것[:4])})" if 저만의것 else "")}


def _뒤집기(node: dict, repo: Path) -> dict:
    내깃발 = [f for f in node.get("깃발", []) if not verify.연월꼴.fullmatch(f)]
    if not 내깃발:
        return {"꼴": "뒤집기", "판정": "못잼", "근거": "연월 말고는 깃발이 없다"}
    되찾는 = [f for f in 내깃발
             if any(n.get("출처") == node.get("출처") for _, n in ask.찾기(f, repo, 최대=5))]
    if not 되찾는:
        판정 = "못잼"
        근거 = "어느 깃발로도 다섯 손가락 안에 안 든다 -- 깃발이 저를 못 되찾는다"
    elif len(되찾는) == 1:
        판정 = "약함"
        근거 = f"깃발 '{되찾는[0]}' 하나에 매달려 있다 -- 그 깃발이 흔해지면 묻힌다"
    else:
        판정 = "굳음"
        근거 = f"깃발 {len(되찾는)}갈래로 되찾힌다 ({', '.join(되찾는[:4])})"
    return {"꼴": "뒤집기", "판정": 판정, "근거": 근거}


def 판정들(node: dict, repo=None) -> "tuple[list[dict], str]":
    """네 꼴의 간선 후보와, 연역의 관할 밖 문장."""
    repo = Path(repo or REPO)
    간선들 = [_대조(node, repo), _재계산(node, repo),
             _기준선(node, repo), _뒤집기(node, repo)]
    for e in 간선들:
        e["출처"] = node["출처"]
        e["해시"] = node.get("해시", "")
    return 간선들, 관할밖_연역


def 기록(node: dict, repo=None) -> "tuple[list[dict], int]":
    """판정하고 간선을 적는다. (새로 적힌 것들, 직전과 같아 건너뛴 수)."""
    repo = Path(repo or REPO)
    간선들, _ = 판정들(node, repo)
    직전 = {}
    for e in 간선읽기(repo):
        직전[(e["꼴"], e["출처"])] = e
    적힘, 건너뜀 = [], 0
    path = _간선원장(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for e in 간선들:
            앞 = 직전.get((e["꼴"], e["출처"]))
            if 앞 and 앞.get("판정") == e["판정"] and 앞.get("해시") == e["해시"]:
                건너뜀 += 1
                continue
            e = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **e}
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            적힘.append(e)
    return 적힘, 건너뜀


def _한줄(e: dict) -> str:
    return f"{e['꼴']:<4} {e['판정']:<4} {e['출처']} -- {e.get('근거', '')[:90]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="다섯 꼴 간선을 판정하고 적는다")
    ap.add_argument("--출처", help="한 노드만 (원장의 출처 상대경로)")
    ap.add_argument("--전부", action="store_true", help="최신 노드 전부")
    ap.add_argument("--보기", action="store_true", help="적힌 간선을 보기만")
    args = ap.parse_args()

    if args.보기:
        edges = [e for e in 간선읽기() if not args.출처 or e["출처"] == args.출처]
        if not edges:
            print("적힌 간선이 없다.")
            return 3
        for e in edges[-40:]:
            print(f"{e.get('때', '')[:10]}  {_한줄(e)}")
        return 0

    nodes = ask.최신들()
    if args.출처:
        nodes = [n for n in nodes if n.get("출처") == args.출처]
    elif not args.전부:
        print("--출처 <상대경로> 나 --전부 를 달라. 보기만 하려면 --보기.")
        return 3
    if not nodes:
        print("그 출처의 노드가 원장에 없다. `python3 graph/night.py` 로 간추렸는가?")
        return 3

    빨강 = 0
    새로 = 0
    for n in nodes:
        적힘, 건너뜀 = 기록(n)
        새로 += len(적힘)
        for e in 적힘:
            print(f"  {_한줄(e)}")
            if e["판정"] in 빨간판정:
                빨강 += 1
    print(f"\n간선 {새로}개 적음 (직전과 같아 건너뜀은 안 셈) · "
          + ("어긋남 없음" if not 빨강 else f"**어긋남/다름 {빨강}개 -- 원문과 색인이 갈라져 있다**"))
    print(관할밖_연역)
    return 1 if 빨강 else 0


if __name__ == "__main__":
    raise SystemExit(main())
