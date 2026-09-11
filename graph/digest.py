"""graph/digest -- 검증된 기억만 '읽힐 텍스트' 로 승격한다. evolve 의 축소판.

Claude Code 가 자기 미래 행동을 바꾸는 유일한 길은 가중치가 아니라 **읽힐 텍스트**
(스킬 · CLAUDE.md)를 고치는 것이다. SE 의 /intent+/evolve 도 같은 길로 간다 --
그 첫 판이 이 파일이다: 판정 간선이 승격과 강등을 정해서, 프롬프트와 사람이 읽는
요지문(graph/digest.md)을 밤마다 **다시 짓는다.**

승격/강등은 말이 아니라 간선이 정한다 (self_challenge 가 증명된 진단만 gates/ 로
승격하는 것과 같은 규율):

  강등  대조=어긋남 · 재계산=다름   -> 본문에서 빠지고 '경고' 절에 적힌다.
        색인과 원문이 갈라진 기억을 읽히게 두면 낡은 색인이 원문 행세를 한다.
  승격  기준선=이례 (+ 어긋남 아님) -> '새 갈래' 절. 원장에 없던 것이 왔다는 신호다.
  경고  뒤집기=못잼/약함           -> 되찾는 길이 하나뿐이거나 없는 기억. 깃발을
        보태지 않으면 묻힌다.

digest.md 는 **파생 문서다** -- 진실은 ledger/edges 원장에 있고, 이 파일은 원장에서
언제든 다시 지어진다. 파생 문서를 손으로 고치지 마라: 다음 밤일이 덮는다(그래서
머리에 그렇게 적어 둔다). 두 진실을 두지 않는 것이 요점이다.

쓰기:
    python3 graph/digest.py           # digest.md 를 다시 짓는다
    python3 graph/digest.py --보기    # 짓지 않고 화면에만
"""
from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graph import ask, link, verify
else:
    from graph import ask, link, verify

REPO = ask.REPO
요지상대 = "graph/digest.md"


def 짓기(repo=None) -> str:
    repo = Path(repo or REPO)
    nodes = ask.최신들(repo)
    lines = [
        "# 기억 요지 -- 원장에서 지어진 파생 문서",
        "",
        "> **손으로 고치지 마라.** 다음 밤일(`scripts/night.sh`)이 덮는다. 진실은",
        "> `graph/ledger.jsonl`(색인)과 `graph/edges.jsonl`(판정)에 있고, 이 문서는",
        f"> 거기서 다시 지어진다. 지은 때: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
    ]
    # 승인된 목표를 맨 위에 얹는다 -- 무엇을 할 것인가가 원장(intent)에 있고, 이 문서는
    # 그것을 읽히게 할 뿐이다. 승인 없는 제안은 여기 안 올라온다(집기와 같은 경계).
    try:
        from intent import store as intent_store
        골들 = intent_store.집기(repo)
    except Exception:
        골들 = []
    if 골들:
        lines += ["## 승인된 목표 -- 지금 집을 수 있는 일 (승인 없는 제안은 안 올라온다)", ""]
        lines += [f"- {intent_store.한줄(g)}" for g in 골들[:5]] + [""]

    if not nodes:
        lines.append("(아직 간추린 기억이 없다 -- `python3 graph/night.py`)")
        return "\n".join(lines) + "\n"

    경고, 새갈래, 약한것 = [], [], []
    for n in nodes:
        판 = link.최근판정(n["출처"], repo)
        빨강 = [f"{k}={v['판정']}" for k, v in 판.items() if v.get("판정") in link.빨간판정]
        if 빨강:
            경고.append((n, ", ".join(빨강)))
            continue                       # 강등 -- 갈라진 기억은 본문에 안 올린다
        if 판.get("기준선", {}).get("판정") == "이례":
            새갈래.append(n)
        if 판.get("뒤집기", {}).get("판정") in ("약함", "못잼"):
            약한것.append((n, 판["뒤집기"]["근거"]))

    if 경고:
        lines += ["## 경고 -- 색인과 원문이 갈라져 있다 (읽기 전에 원문을 봐라)", ""]
        lines += [f"- `{n['출처']}` ({왜})" for n, 왜 in 경고[:10]] + [""]

    if 새갈래:
        lines += ["## 새 갈래 -- 원장 분포에 없던 기억 (기준선=이례, 검증 통과)", ""]
        for n in 새갈래[:10]:
            lines.append(f"- **{'·'.join(n['깃발'][:5])}** -- {n['요약'][:140]} `<{n['출처']}>`")
        lines.append("")

    잦은 = Counter(f for n in nodes for f in n.get("깃발", [])
                  if not verify.연월꼴.fullmatch(f))
    lines += ["## 깃발 지도 -- 무엇이 얼마나 쌓여 있나", ""]
    lines.append(" · ".join(f"{f}({c})" for f, c in 잦은.most_common(20)) or "(깃발 없음)")
    lines += ["", f"노드 {len(nodes)}개 · 경고 {len(경고)}개 · 새 갈래 {len(새갈래)}개. "
                  f"찾기: `python3 graph/ask.py --말 <깃발>` · 디스코드 `!기억 <말>`", ""]

    if 약한것:
        lines += ["## 되찾는 길이 좁은 기억 (뒤집기=약함/못잼) -- 깃발을 보태라", ""]
        lines += [f"- `{n['출처']}` -- {왜[:90]}" for n, 왜 in 약한것[:8]] + [""]
    return "\n".join(lines)


def 쓰기(repo=None) -> Path:
    repo = Path(repo or REPO)
    path = repo / 요지상대
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(짓기(repo), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="원장에서 읽힐 요지문을 다시 짓는다")
    ap.add_argument("--보기", action="store_true", help="파일로 안 쓰고 화면에만")
    args = ap.parse_args()
    if args.보기:
        print(짓기())
        return 0
    path = 쓰기()
    print(f"다시 지었다: {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
