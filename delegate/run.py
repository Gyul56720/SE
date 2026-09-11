"""delegate -- 넓은 탐색을 싼 역할(탐색기)에 맡기고, **요약이 아니라 대조된 인용**을 받는다.

왜 있나: 관리 에이전트는 ReAct 라 순차이고, 파일 수십 개를 살피는 일도 비싼 모델이
직접 cat 으로 한다. Claude Code 는 그 일을 싼 서브에이전트에 던지고 결론만 받는다. 그런데
"결론만 받는" 것이 이 저장소에서는 위험하다 -- 요약은 지어낼 수 있고, 지어낸 요약은
화면에서 진짜와 똑같이 생겼다(brain·verify 가 온 자리). 그래서 받는 것을 바꾼다:

    탐색기는 [{"파일": ..., "인용": <글자 그대로>, "왜": ...}] 만 낸다
    코드가 인용을 파일과 **대조**한다 -- 실재하면 줄 번호와 해시를 붙여 채택, 아니면 퇴짜
    채택/퇴짜는 router 원장에 채택표시로 남는다 (싼 모델이 값을 하는가를 4단계 심판이 잰다)

병렬: 범위를 파일 묶음으로 쪼개 동시에 던진다. 쿼터·분당 간격·모델 전환은 llm_pool 이
진다(여기서 한 줄도 다시 짜지 않는다). 묶음 수가 곧 동시 호출 수의 상한이다.

쓰기:
    python3 delegate/run.py --범위 'graph/*.py' --물음 '해시를 어디서 대조하나'
    python3 delegate/run.py --범위 'graph/*.py' --쪼개기만       # 호출 0회, 묶음만 본다
끝값: 0 채택된 인용 있음 · 1 전부 퇴짜(모델이 지어냈다) · 3 못 돌림(키·파일 없음)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

묶음글자 = 24000          # 한 호출에 넣는 파일 글자 상한
파일글자 = 12000          # 파일 하나는 이만큼만(앞부분). 넘으면 잘렸다고 적는다
병렬상한 = 4
# .env 는 이름이 정확히 그것뿐 아니라 `무엇.env` 꼴도 있다(실측: 검사가 src/비밀.env 를 읽었다).
_안읽음 = re.compile(r"(^|/)(\.git|node_modules|venv|__pycache__|sandbox/out)(/|$)|(^|/)[^/]*\.env(\.[^/]*)?$")
_이진 = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".pyc", ".hwp", ".xlsx", ".pptx")

# 검사가 가짜를 꽂는 자리. 기본은 router.부르기("탐색기", ...).
부르기 = None


def 쪼개기(범위들, repo=None, 상한: "int | None" = None) -> "list[list[Path]]":
    """글롭들을 파일 묶음으로. 비밀·이진·산출물은 안 읽는다. 상한(기본 묶음글자) 안에서 채운다
    -- 상한이 작을수록 묶음이 많아지고 동시 호출이 늘어난다."""
    repo = Path(repo or REPO)
    상한 = 상한 or 묶음글자
    파일들: list = []
    본것 = set()
    for 글롭 in 범위들:
        for p in sorted(repo.glob(글롭)):
            rel = str(p.relative_to(repo))
            if p in 본것 or not p.is_file() or _안읽음.search(rel) or p.suffix.lower() in _이진:
                continue
            본것.add(p)
            파일들.append(p)
    묶음들: list = []
    지금, 찬것 = [], 0
    for p in 파일들:
        n = min(p.stat().st_size, 파일글자)
        if 지금 and 찬것 + n > 상한:
            묶음들.append(지금)
            지금, 찬것 = [], 0
        지금.append(p)
        찬것 += n
    if 지금:
        묶음들.append(지금)
    return 묶음들


def _프롬프트(물음: str, 파일들, repo: Path) -> str:
    토막 = []
    for p in 파일들:
        글 = p.read_text(encoding="utf-8", errors="replace")
        잘림 = len(글) > 파일글자
        토막.append(f"=== {p.relative_to(repo)} ===\n{글[:파일글자]}"
                   + ("\n… (여기서 잘렸다 -- 뒤는 안 보인다)" if 잘림 else ""))
    return ("아래 파일들에서 다음 물음에 닿는 자리를 찾아라.\n"
            f"물음: {물음}\n\n"
            "JSON 배열 하나만 내라. 원소는 {\"파일\": \"<위 === 에 적힌 경로>\", "
            "\"인용\": \"<그 파일에 적힌 글 그대로, 1~3줄>\", \"왜\": \"<한 줄>\"}. "
            "닿는 자리가 없으면 [] 를 내라. 인용은 파일의 글자를 그대로 옮겨라 -- "
            "바꿔 쓰거나 요약하지 마라.\n\n" + "\n\n".join(토막))


def _해석(답: str) -> "list[dict]":
    m = re.search(r"\[.*\]", 답 or "", re.S)
    if not m:
        return []
    try:
        got = json.loads(m.group(0))
    except ValueError:
        return []
    return [g for g in got if isinstance(g, dict)] if isinstance(got, list) else []


def _공백접기(s: str) -> str:
    return " ".join((s or "").split())


def 대조(찾은것들: "list[dict]", 허용파일, repo: Path) -> "tuple[list[dict], list[str]]":
    """인용이 파일에 글자 그대로 있는가. 있으면 줄 번호·해시를 붙인다. (채택, 퇴짜사유)."""
    채택, 퇴짜 = [], []
    허용 = {str(p.relative_to(repo)): p for p in 허용파일}
    for g in 찾은것들:
        rel, 인용 = str(g.get("파일", "")).strip(), str(g.get("인용", "")).strip()
        p = 허용.get(rel)
        if p is None:
            퇴짜.append(f"{rel or '(파일 없음)'}: 이번 묶음에 없는 파일을 댔다")
            continue
        if not 인용:
            퇴짜.append(f"{rel}: 인용이 비었다")
            continue
        글 = p.read_text(encoding="utf-8", errors="replace")
        줄 = None
        if 인용 in 글:
            줄 = 글[:글.index(인용)].count("\n") + 1
        else:
            # 공백만 다른 것은 봐준다 -- 줄바꿈 위치가 갈리는 것은 흔하다. 낱말이 다르면 안 된다.
            접은글, 접은인용 = _공백접기(글), _공백접기(인용)
            if 접은인용 and 접은인용 in 접은글:
                # 줄을 짚을 때도 공백을 접어 견준다 -- 안 그러면 인용은 봐주면서 줄은 0 이 된다
                # (실측: 검사가 그 0 을 잡았다).
                첫줄 = _공백접기(인용.splitlines()[0])
                for i, ln in enumerate(글.splitlines(), 1):
                    if 첫줄 and 첫줄 in _공백접기(ln):
                        줄 = i
                        break
                줄 = 줄 or 0                     # 0 = 인용은 있는데 줄을 못 짚음. 지어내지 않는다
        if 줄 is None:
            퇴짜.append(f"{rel}: 인용이 원문에 없다 -- {인용[:60]!r}")
            continue
        채택.append({"파일": rel, "줄": 줄, "인용": 인용[:400], "왜": str(g.get("왜", ""))[:200],
                    "해시": hashlib.sha256(글.encode("utf-8")).hexdigest()[:12]})
    return 채택, 퇴짜


def _한묶음(물음: str, 파일들, repo: Path, 부르기_) -> dict:
    시작 = time.monotonic()
    try:
        r = 부르기_("탐색기", _프롬프트(물음, 파일들, repo))
    except Exception as e:                                        # noqa: BLE001
        return {"채택": [], "퇴짜": [f"호출 실패: {type(e).__name__}: {str(e)[:120]}"],
                "id": None, "걸린초": round(time.monotonic() - 시작, 1), "파일수": len(파일들)}
    채택, 퇴짜 = 대조(_해석(r.get("답", "")), 파일들, repo)
    return {"채택": 채택, "퇴짜": 퇴짜, "id": r.get("id"),
            "걸린초": round(time.monotonic() - 시작, 1), "파일수": len(파일들)}


def 위임(물음: str, 범위들, 병렬: int = 병렬상한, repo=None, 묶음상한: "int | None" = None) -> dict:
    """묶음들을 동시에 던지고 대조된 것만 모은다. 채택 여부를 router 원장에 잇는다."""
    repo = Path(repo or REPO)
    from router import call as R
    부르기_ = 부르기 or (lambda 역할, p: R.부르기(역할, p, repo=repo))
    묶음들 = 쪼개기(범위들, repo, 상한=묶음상한)
    if not 묶음들:
        return {"채택": [], "퇴짜": ["범위에 읽을 파일이 없다"], "묶음": 0, "파일": 0,
                "호출": 0, "걸린초": 0.0, "돌았나": False}
    시작 = time.monotonic()
    결과들: list = []
    with cf.ThreadPoolExecutor(max_workers=max(1, min(병렬, len(묶음들)))) as ex:
        for r in ex.map(lambda 파일들: _한묶음(물음, 파일들, repo, 부르기_), 묶음들):
            결과들.append(r)
    채택, 퇴짜 = [], []
    본자리 = set()
    for r in 결과들:
        for g in r["채택"]:
            키 = (g["파일"], g["줄"])
            if 키 not in 본자리:
                본자리.add(키)
                채택.append(g)
        퇴짜.extend(r["퇴짜"])
        if r["id"]:
            # 싼 역할이 값을 했는가 -- 4단계 심판(채택률)의 재료. 인용을 하나라도 실재하게
            # 냈으면 채택, 전부 지어냈거나 빈손이면 불채택.
            try:
                R.채택표시(r["id"], bool(r["채택"]), repo=repo)
            except Exception:                                     # noqa: BLE001
                pass
    return {"채택": 채택, "퇴짜": 퇴짜, "묶음": len(묶음들),
            "파일": sum(len(b) for b in 묶음들), "호출": len(결과들),
            "걸린초": round(time.monotonic() - 시작, 1), "돌았나": True}


def 보고(r: dict, 물음: str = "") -> str:
    lines = [f"묶음 {r['묶음']}개(파일 {r['파일']}개)를 동시에 던져 {r['걸린초']}초 · "
             f"채택 {len(r['채택'])} · 퇴짜 {len(r['퇴짜'])}"]
    for g in r["채택"][:20]:
        lines.append(f"  {g['파일']}:{g['줄']}  {g['인용'].splitlines()[0][:100]}"
                     + (f"  -- {g['왜'][:80]}" if g.get("왜") else ""))
    if r["퇴짜"]:
        lines.append(f"  퇴짜 {len(r['퇴짜'])}건 (원문에 없는 인용은 버렸다 -- 모델이 지어낸 것이다):")
        lines += [f"    ! {x[:120]}" for x in r["퇴짜"][:6]]
    if not r["채택"] and r.get("돌았나"):
        lines.append("  채택된 인용이 없다 -- 범위에 답이 없거나 탐색기가 못 찾았다. 범위를 바꿔 다시.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="넓은 탐색을 싼 역할에 맡기고 대조된 인용을 받는다")
    ap.add_argument("--범위", action="append", required=True, help="글롭. 여러 번 줄 수 있다")
    ap.add_argument("--물음", default="")
    ap.add_argument("--병렬", type=int, default=병렬상한)
    ap.add_argument("--쪼개기만", action="store_true", help="호출 0회. 묶음만 본다")
    args = ap.parse_args()
    if args.쪼개기만:
        묶음들 = 쪼개기(args.범위)
        print(f"묶음 {len(묶음들)}개 · 파일 {sum(len(b) for b in 묶음들)}개")
        for i, b in enumerate(묶음들, 1):
            print(f"  [{i}] " + ", ".join(str(p.relative_to(REPO)) for p in b[:6])
                  + (f" … +{len(b) - 6}" if len(b) > 6 else ""))
        return 0 if 묶음들 else 3
    if not args.물음:
        print("--물음 이 필요하다 (--쪼개기만 이면 없어도 된다)")
        return 3
    try:
        r = 위임(args.물음, args.범위, 병렬=args.병렬)
    except Exception as e:                                        # noqa: BLE001
        print(f"못 돌린다: {type(e).__name__}: {str(e)[:200]}")
        return 3
    print(보고(r, args.물음))
    if not r["돌았나"]:
        return 3
    return 0 if r["채택"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
