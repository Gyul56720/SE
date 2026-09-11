"""research -- 목표 하나를 받아 **추상 질의**로 제2의 뇌를 돌리고, 막히면 그 막힘을 다시
추상화해 더 넓게 모으기를 되풀이한다. 모은 방법론을 코드화(검증)하고, 과정-결과를 압축해
public_agent_memory 에 결론으로 남긴다. 사용자가 시킨 것을 완수하거나 바퀴가 다할 때까지.

왜 이렇게 쓰나 (실측 2026-09-11):
- 봇이 목표를 **그대로** 검색어로 썼다 -- "naver booking automation playwright headless
  browser workaround" 한 줄. 너무 구체적이라 논문이 0건이었고, 봇은 "불가능하다" 로 끝냈다.
- 고쳐야 할 것은 결론이 아니라 **과정**이다. 구체 목표를 **일반 방법론 질의 여럿**으로
  풀어(분해기) 넓게 모으고, 한 바퀴가 막히면 그 막힘을 다시 추상화해 더 넓게 모은다.
- 무한 loop 는 금지다(이 저장소 규율) -- 3~5 바퀴. 같은 질의가 되풀이되면 멈춘다.

규율: 판정은 모델이 아니라 코드가 한다 -- 수집 색인 수(harvest)와 코드화 sandbox 끝값
(codify). 분해·종합은 모델이 돕되, '모았다/코드가 섰다' 는 코드가 증언한다. 도메인 무관.

    끝: public_agent_memory/<때>_연구_<slug>.md -- 질의·바퀴별 수집·코드화·결론(과정->결과)·
        남은 틈. + research/ledger.jsonl (바퀴마다 append-only).
    끝값: 0 한 바퀴라도 돌았다 · 3 첫 바퀴부터 못 돌림(수집기·모델 다 막힘).
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
원장상대 = "research/ledger.jsonl"
메모곳 = "public_agent_memory"
기본바퀴 = 3
최대바퀴 = 5

# 모델이 하는 두 가지. 테스트는 여기에 가짜를 꽂아 망·LLM 없이 돈다(codify 의 코드공과 같은 방식).
분해기 = None      # (목표:str, 막힌것:str) -> str   일반 방법론 질의 여러 줄
종합기 = None      # (목표:str, 모은요약:str) -> str  과정->결과 결론


# ---------------------------------------------------------------- 분해: 구체 목표 -> 추상 질의
def _분해기본(목표: str, 막힌것: str) -> str:
    from router import call as R
    프 = (f"목표: {목표}\n"
         + (f"지난 바퀴가 이렇게 막혔다: {막힌것}\n" if 막힌것 else "")
         + "이 목표를 풀기 위한 **일반적인 방법론·기술 검색어**를 3~5개, 한 줄에 하나씩 영어로 적어라. "
           "고유명사(상표·사이트 이름)는 빼고, arXiv·GitHub 에서 논문·코드가 실제로 나올 만큼 "
           "추상적으로 적어라. 설명 없이 검색어 줄만.")
    return R.부르기("탐색기", 프)["답"]


def _질의뽑기(답: str, 목표: str) -> "list[str]":
    """모델 답(줄 목록)에서 검색어를 뽑는다. 비면 목표에서 기계적으로 일반화한다(LLM 없이도 돈다)."""
    줄들 = []
    for raw in (답 or "").splitlines():
        s = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw).strip().strip("`\"'")
        if 3 <= len(s) <= 120 and not s.endswith(":"):
            줄들.append(s)
    # 중복 제거(순서 유지)
    본 = set()
    질의 = []
    for s in 줄들:
        k = s.lower()
        if k not in 본:
            본.add(k)
            질의.append(s)
    if 질의:
        return 질의[:5]
    return _기계일반화(목표)


def _기계일반화(목표: str) -> "list[str]":
    """LLM 이 없을 때의 바닥 -- 목표에서 흔한 구체어를 덜어 일반 검색어 몇 개를 만든다."""
    낱말 = [w for w in re.split(r"[\s,]+", (목표 or "").strip()) if w]
    질의 = []
    if 낱말:
        질의.append(" ".join(낱말))                 # 원문
    if len(낱말) > 2:
        질의.append(" ".join(낱말[-2:]))             # 끝 두 낱말(대개 방법론 쪽)
        질의.append(" ".join(낱말[:-1]))             # 가장 구체적인 끝 낱말을 덜어낸다
    # 방법론으로 넓히는 일반 꼬리
    바탕 = 낱말[-1] if 낱말 else (목표 or "method")
    질의.append(f"{바탕} survey methodology")
    본 = set()
    out = []
    for s in 질의:
        if s and s.lower() not in 본:
            본.add(s.lower())
            out.append(s)
    return out[:5]


def 분해(목표: str, 막힌것: str = "") -> "list[str]":
    try:
        답 = (분해기 or _분해기본)(목표, 막힌것)
    except Exception:                                 # noqa: BLE001 -- 모델 못 부르면 기계 일반화
        답 = ""
    return _질의뽑기(답, 목표)


# ---------------------------------------------------------------- 종합: 모은 것 -> 결론
def _종합기본(목표: str, 모은요약: str) -> str:
    from router import call as R
    프 = (f"목표: {목표}\n\n제2의 뇌가 모은 것(검증된 방법론·논문·코드):\n{모은요약}\n\n"
         "이것을 근거로 목표를 어떻게 풀지 **과정->결과** 결론을 한국어로 간결히 적어라. "
         "모은 것에 없는 것은 지어내지 말고 '아직 없음' 이라 적어라.")
    return R.부르기("풀이기", 프)["답"]


def 종합(목표: str, 모은요약: str) -> str:
    try:
        return (종합기 or _종합기본)(목표, 모은요약).strip()
    except Exception as e:                            # noqa: BLE001
        return f"(종합기 못 부름: {type(e).__name__}) -- 아래 '모은 것' 이 결론의 근거다."


# ---------------------------------------------------------------- 원장 · 메모
def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def _slug(목표: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", (목표 or "x"))[:50].strip("_") or "x"


def 기억쓰기(목표: str, 바퀴들: "list[dict]", 결론: str, repo=None) -> str:
    """과정-결과를 압축해 메모로 남긴다 -- graph/night 가 밤에 간추려 장기기억으로."""
    repo = Path(repo or REPO)
    때 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    p = repo / 메모곳 / f"{때}_연구_{_slug(목표)}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = ["---", f"topic: '연구: {목표[:60]}'", "---", "", f"# 연구: {목표}", ""]
    줄.append("## 질의 (추상 방법론으로 넓힘)")
    for b in 바퀴들:
        줄.append(f"- 바퀴 {b['바퀴']}: " + ", ".join(b["질의들"]))
    줄.append("")
    줄.append("## 모은 것 (수집 색인 · 코드화 검증)")
    for b in 바퀴들:
        줄.append(f"- 바퀴 {b['바퀴']}: 색인 {b['색인']} · 거절 {b['거절']} · "
                 f"코드화 성공 {b['코드성공']}/{b['코드스펙']}"
                 + (f" · 막힘 {b['막힘']}" if b["막힘"] else ""))
        for 논 in b["논문들"]:
            줄.append(f"    - 논문 {논['제목'][:60]} <{논['url']}>")
        for f in b["파일들"]:
            줄.append(f"    - 코드 {f}")
    줄 += ["", "## 결론 (과정 -> 결과)", 결론 or "(결론 없음)", ""]
    틈 = [b for b in 바퀴들 if b["색인"] == 0 and b["막힘"]]
    if 틈:
        줄.append("## 남은 틈 (다음 수집 대상)")
        for b in 틈:
            줄.append(f"- 바퀴 {b['바퀴']} 막힘: {b['막힘']}")
    p.write_text("\n".join(줄) + "\n", encoding="utf-8")
    return str(p.relative_to(repo))


# ---------------------------------------------------------------- 한 목표 연구 (바퀴 loop)
def 연구(목표: str, repo=None, 바퀴: int = 기본바퀴, 논문수: int = 2) -> dict:
    from dig import harvest as H
    from codify import run as C

    repo = Path(repo or REPO)
    바퀴 = max(1, min(int(바퀴), 최대바퀴))
    목표 = (목표 or "").strip()
    H.관심더하기(목표, repo=repo)                     # 사람이 준 방향은 관심 원장에도 남긴다

    결과 = {"목표": 목표, "돌았나": False, "충분": False, "바퀴수": 0, "바퀴들": [],
           "결론": "", "메모": "", "남은것": ""}
    질의들 = 분해(목표, "")
    지난질의 = None
    막힌것 = ""
    _적기(repo, {"꼴": "연구시작", "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "목표": 목표, "첫질의": 질의들})

    for n in range(1, 바퀴 + 1):
        if 질의들 == 지난질의:                         # 같은 질의 되풀이 -> 멈춘다(무한 loop 금지)
            결과["남은것"] = "질의가 바뀌지 않아 멈췄다 -- 분해기가 더 넓힐 거리를 못 찾았다"
            break
        지난질의 = 질의들
        결과["바퀴수"] = n
        수확 = H.한바퀴(질의들, repo=repo, 몇=3, 상한=8, 출처=("arxiv", "github", "hf"))
        if 수확["돌았나"]:
            결과["돌았나"] = True
        논문url들 = _이번논문(repo, 질의들)
        코드결과들 = []
        논문메타 = []
        for u in 논문url들[:논문수]:
            try:
                r = C.논문코드화(u, repo=repo)
            except Exception as e:                    # noqa: BLE001
                r = {"논문": u, "제목": "", "스펙수": 0, "성공": 0, "결과들": [], "못읽음": [str(e)[:80]]}
            코드결과들.append(r)
            논문메타.append({"url": u, "제목": r.get("제목", "")})
        파일들 = [x.get("파일") for r in 코드결과들 for x in r.get("결과들", []) if x.get("파일")]
        코드성공 = sum(r.get("성공", 0) for r in 코드결과들)
        코드스펙 = sum(r.get("스펙수", 0) for r in 코드결과들)
        기록 = {"바퀴": n, "질의들": 질의들, "색인": 수확["색인"], "거절": len(수확["거절"]),
               "막힘": 수확.get("막힘") or {}, "논문들": 논문메타, "파일들": 파일들,
               "코드성공": 코드성공, "코드스펙": 코드스펙}
        결과["바퀴들"].append(기록)
        _적기(repo, {"꼴": "연구바퀴", "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **기록})

        충분 = 수확["색인"] > 0 and (코드성공 > 0 or 수확["색인"] >= 2)
        if 충분:
            결과["충분"] = True
            break
        # 막혔다 -> 그 막힘을 다시 추상화해 더 넓게 (사용자 규정: 오류마다 추상 수집 후 재시도)
        막힌것 = (f"수집 색인 0, 막힘 {수확.get('막힘')}" if 수확["색인"] == 0
                else f"방법론은 모았으나(색인 {수확['색인']}) 코드화가 0 -- 더 구현 가능한 방법론 필요")
        질의들 = 분해(목표, 막힌것)

    모은요약 = _모은요약(결과["바퀴들"])
    결과["결론"] = 종합(목표, 모은요약) if 결과["바퀴들"] else "아무것도 못 모았다 -- 수집기가 다 막혔다"
    if 결과["바퀴들"]:
        결과["메모"] = 기억쓰기(목표, 결과["바퀴들"], 결과["결론"], repo=repo)
    if not 결과["남은것"] and not 결과["충분"]:
        결과["남은것"] = f"{결과['바퀴수']}바퀴 돌았지만 목표를 덮는 검증된 방법론을 아직 못 채웠다"
    _적기(repo, {"꼴": "연구끝", "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "목표": 목표, "충분": 결과["충분"], "바퀴수": 결과["바퀴수"], "메모": 결과["메모"]})
    return 결과


def _이번논문(repo, 질의들: "list[str]") -> "list[str]":
    """방금 harvest 가 색인한 arxiv 논문 url 을, 이 질의로 받은 것만 최신부터."""
    from dig import harvest as H
    질의집 = set(질의들)
    out = []
    본 = set()
    for r in reversed(H.원장읽기(repo)):
        if (r.get("종류") == "arxiv-paper" and r.get("판정") == "색인"
                and r.get("검색어") in 질의집 and r.get("url") and r["url"] not in 본):
            본.add(r["url"])
            out.append(r["url"])
        if len(out) >= 6:
            break
    return out


def _모은요약(바퀴들: "list[dict]") -> str:
    줄 = []
    for b in 바퀴들:
        줄.append(f"바퀴 {b['바퀴']} ({', '.join(b['질의들'])[:80]}): 색인 {b['색인']}, "
                 f"코드화 {b['코드성공']}/{b['코드스펙']}")
        for 논 in b["논문들"]:
            줄.append(f"  논문: {논['제목'][:70]} <{논['url']}>")
        for f in b["파일들"]:
            줄.append(f"  코드: {f}")
    return "\n".join(줄) or "(모은 것 없음)"


def 보고(결과: dict) -> str:
    줄 = [f"연구: {결과['목표'][:70]}",
         f"  {'충분히 모음' if 결과['충분'] else '부분'} · {결과['바퀴수']}바퀴 · "
         f"{'돌았다' if 결과['돌았나'] else '못 돌림(수집기 막힘)'}"]
    for b in 결과["바퀴들"]:
        줄.append(f"  바퀴 {b['바퀴']}: 색인 {b['색인']} · 코드화 {b['코드성공']}/{b['코드스펙']}"
                 + (f" · 막힘 {list(b['막힘'])}" if b["막힘"] else ""))
        for f in b["파일들"]:
            줄.append(f"      코드 {f}")
    if 결과["결론"]:
        줄.append("  결론: " + 결과["결론"][:300].replace("\n", " "))
    if 결과["메모"]:
        줄.append(f"  메모: {결과['메모']}")
    if 결과["남은것"]:
        줄.append(f"  남은: {결과['남은것']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="목표 하나를 추상 질의로 연구한다(수집->코드화->결론 메모)")
    ap.add_argument("--목표", required=True, help="사람이 준 목표(어느 도메인이든)")
    ap.add_argument("--바퀴", type=int, default=기본바퀴, help=f"최대 바퀴(상한 {최대바퀴})")
    ap.add_argument("--논문수", type=int, default=2, help="바퀴마다 코드화할 논문 수")
    ap.add_argument("--분해만", action="store_true", help="목표를 질의로 풀어 보이기만(수집·쓰기 없음 -- 배선)")
    ap.add_argument("--저장소", default="", help="저장소 뿌리(검사·감사용)")
    args = ap.parse_args()
    repo = Path(args.저장소) if args.저장소 else None
    if args.분해만:
        for q in 분해(args.목표, ""):
            print("  질의 ->", q)
        return 0
    결과 = 연구(args.목표, repo=repo, 바퀴=args.바퀴, 논문수=args.논문수)
    print(보고(결과))
    return 0 if 결과["돌았나"] else 3


if __name__ == "__main__":
    import sys
    from pathlib import Path
    REPO_ROOT = Path(__file__).resolve().parent.parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
