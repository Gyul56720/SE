"""secaudit/run -- 로컬 호스트 보안 자가점검 파이프라인. 사용자 규정의 5단계를 잇는다.

    1 수집   dig/harvest 로 보안 점검 방법론·권고를 모은다 (제2의 뇌에 쌓인다)   [선택]
    2 정제   수집한 자연어를 에이전트가 쓸 구조로 -- 여기서는 '어떤 점검을 돌릴지' 로 푼다
    3 대조   search_memory(graph/ask) 로 지난 점검 규칙·예외와 맞춘다              [선택]
    4 점검   secaudit/checks 의 읽기 전용 진단을 실측한다 -- **판정은 코드가 한다**
    5 보고   심각도별로 구조화한 보고 + 원장(secaudit/ledger.jsonl)

무엇을 하고 무엇을 안 하나(checks 문서 그대로): 돌고 있는 **호스트 자신**을 읽기만 한다.
남의 기계 접속·익스플로잇 실행·상태 변경은 없다. "내 노트북" 을 점검하려면 그 노트북에서
이것을 돌리면 된다 -- 여기서 남의 기계로 건너가지 않는다.

수집·대조는 network/LLM 이 있어야 하므로, 없으면 **건너뛰고 그렇다고 말한다**(4·5 는 돈다).

쓰기:
    python3 secaudit/run.py                 # 점검만 (수집·대조 없이, network 불필요)
    python3 secaudit/run.py --뇌             # dig 수집 + search_memory 대조까지
    python3 secaudit/run.py --json
끝값: 0 높음 없음 · 1 높음 있음 · 3 점검을 하나도 못 돌림(전부 '못잼')
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from secaudit import checks as C  # noqa: E402

원장상대 = "secaudit/ledger.jsonl"
수집어 = "linux host hardening checklist open ports suid world-writable ssh key permissions CIS benchmark"

수집 = None      # 검사 주입: (말) -> None.  None 이면 dig/harvest 한 바퀴
대조 = None      # 검사 주입: (물음) -> list[dict].  None 이면 graph/ask.찾기


# ---------------------------------------------------------------- 1·3 제2의 뇌 (선택)
def 방법론모으기(repo=None) -> "dict":
    """dig/harvest 로 점검 방법론을 모은다. 망이 없으면 건너뛴다."""
    try:
        if 수집 is not None:
            수집(수집어)
            return {"했나": True, "메모": "수집기를 불렀다"}
        from dig import harvest
        r = harvest.한바퀴([수집어], repo=repo, 몇=3, 상한=4)
        if not r["돌았나"]:
            return {"했나": False, "메모": f"수집 건너뜀: {r.get('메모') or r.get('막힘')}"}
        return {"했나": True, "메모": f"색인 {r['색인']}개 (거절 {len(r['거절'])})"}
    except Exception as e:                                        # noqa: BLE001
        return {"했나": False, "메모": f"수집 건너뜀: {type(e).__name__}"}


def 규칙대조(낱낱: dict, repo=None) -> "list[str]":
    """search_memory 에서 이 점검 제목과 맞는 지난 규칙·예외를 찾는다."""
    try:
        물음 = 낱낱["제목"] + " " + " ".join(낱낱.get("증거", [])[:1])
        if 대조 is not None:
            노드들 = 대조(물음)
        else:
            from graph import ask
            노드들 = [n for _, n in ask.찾기(물음, repo=repo, 최대=2)]
        return [f"{n.get('요약', '')[:120]} <{n.get('출처', '')}>" for n in 노드들]
    except Exception:                                            # noqa: BLE001
        return []


# ---------------------------------------------------------------- 원장
def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 원장읽기(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 원장상대
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


# ---------------------------------------------------------------- 파이프라인
def 점검하기(repo=None, 뇌: bool = False, 적기: bool = True) -> dict:
    repo = Path(repo or REPO)
    시작 = time.monotonic()
    수집메모 = 방법론모으기(repo)["메모"] if 뇌 else "수집 안 함(--뇌 로 켠다)"
    낱낱들 = C.전부(repo)
    for f in 낱낱들:
        f["참고"] = 규칙대조(f, repo) if 뇌 else []
    셈 = {s: sum(1 for f in 낱낱들 if f["심각도"] == s) for s in C.심각도차례}
    전부못 = all(f["심각도"] == "못잼" for f in 낱낱들)
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "수집": 수집메모, "셈": 셈,
         "낱낱": [{k: v for k, v in f.items() if k != "참고"} for f in 낱낱들]}
    if 적기:
        _적기(repo, 줄)
    return {"돌았나": not 전부못, "낱낱들": 낱낱들, "셈": 셈, "수집메모": 수집메모,
            "걸린초": round(time.monotonic() - 시작, 1)}


def 보고(결과: dict) -> str:
    줄 = [f"보안 자가점검 (읽기 전용) -- {결과['수집메모']}"]
    if not 결과["돌았나"]:
        줄.append("  **못돌림** -- 모든 점검이 '못잼' 이다(도구·권한 부재). 이것은 '안전' 이 아니다.")
    for f in 결과["낱낱들"]:
        표 = {"높음": "⚠ 높음", "중간": "· 중간", "낮음": "· 낮음", "정보": "  정보", "못잼": "? 못잼"}[f["심각도"]]
        줄.append(f"  [{표}] {f['제목']}")
        for e in f["증거"][:4]:
            줄.append(f"        {e}")
        if f["심각도"] in ("높음", "중간", "못잼"):
            줄.append(f"        고침: {f['고침']}")
        for p in f.get("참고", [])[:2]:
            줄.append(f"        참고: {p}")
    s = 결과["셈"]
    줄.append(f"  합계: 높음 {s['높음']} · 중간 {s['중간']} · 낮음 {s['낮음']} · 정보 {s['정보']} · 못잼 {s['못잼']}")
    if s["못잼"]:
        줄.append("  ('못잼' 은 안전이 아니라 안 잰 것이다 -- 도구·권한이 되는 호스트에서 다시 잰다)")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="로컬 호스트 보안 자가점검 (읽기 전용)")
    ap.add_argument("--뇌", action="store_true", help="dig 수집 + search_memory 대조까지 (network 필요)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = 점검하기(뇌=args.뇌)
    if args.json:
        print(json.dumps({"셈": r["셈"], "낱낱들": r["낱낱들"]}, ensure_ascii=False, indent=1))
    else:
        print(보고(r))
    if not r["돌았나"]:
        return 3
    return 1 if r["셈"]["높음"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
