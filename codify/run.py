"""codify -- 논문의 **자연어·수식·알고리즘을 실행 가능한 코드로** 바꾼다. 제2의 뇌 3단계. 도메인 무관.

사용자 규정(2026-09-11): "자연어(비언어) 수식·표·다이어그램·시스템 등 논문 이론을 code 로
바꿔주는 제2의 brain. 수집은 따로(dig/paper·harvest), 이건 수집한 것을 코드화. 표/데이터
같은 결과로 검증(원장 역할)."

흐름 (repair 와 같은 뼈대 -- 판정은 모델이 아니라 코드가):
    스펙(수식 LaTeX | 알고리즘 의사코드 + 이름 + 예시 입출력 + 출처)
      바퀴 1..N:
        1 짓기  코드공(모델)에 스펙·예시·해 본 것을 주고 함수 1개 + 검사(예시로 assert) 를 받는다
        2 검증  eval.tasks.실행판정 으로 **sandbox 에서 돌린다** -- 검사 끝값 0 이면 코드화 성공
        3 못 되면 꼬리를 다음 바퀴에 넣는다. 같은 코드 되풀이·바퀴 상한이면 멈춘다(repair 규율)
      끝:  codify/ledger.jsonl (스펙·성공 여부·바퀴) + 성공하면 codify/out/<id>.py 저장 +
           graph 색인(지은이="코드(검증통과)" -- 검사를 통과한 코드만 기억에 들어온다).
           못 한 것은 dig/harvest --틈 의 검색어가 되어 제2의 뇌가 더 모은다.

판정이 '표/데이터 결과' 인 이유: 예시 입출력(논문이 준 값·자기 일관성)으로 assert 하므로,
"돌아간다" 가 아니라 "맞는 값을 낸다" 까지 코드가 확인한다. 예시가 없으면 최소한 import·형
검사라도 -- 그땐 '약한 검증' 으로 표시한다(안 속인다).

쓰기:
    python3 codify/run.py --종류 수식 --이름 ou반감기 --원문 'X_t = mu + (X_0-mu) e^{-theta t}' \
        --예시 '[{"입력":{"theta":0.05},"답":13.86,"허용":0.1,"부른다":"반감기"}]'
    python3 codify/run.py --논문 2401.00001     # 그 논문의 수식·알고리즘을 차례로 코드화
끝값: 0 코드화 성공 · 1 못 함(해 본 것·남은 것 적음) · 3 못돌림(모델 못 부름)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eval import tasks as ET  # noqa: E402  실행판정·코드뽑기 재사용(두 벌 금지)

원장상대 = "codify/ledger.jsonl"
산출상대 = "codify/out"
기본바퀴 = 3
최대바퀴 = 5

코드공 = None      # 검사 주입: (prompt) -> str. None 이면 router 코드공


# ---------------------------------------------------------------- 검사 만들기
def 예시검사(예시들: "list[dict]") -> str:
    """예시 입출력을 함수를 import 해 assert 하는 검사 스크립트로. 예시가 없으면 import 만(약한 검증)."""
    줄 = ["import 답", "import math"]
    if not 예시들:
        줄.append("assert any(callable(getattr(답, n)) for n in dir(답) if not n.startswith('_')), '함수가 없다'")
        줄.append("print('ok(약한 검증: 예시 없음 -- import·호출 가능만 봤다)')")
        return "\n".join(줄) + "\n"
    for i, e in enumerate(예시들):
        부른다 = e.get("부른다") or ""
        인 = e.get("입력", {})
        인자 = ", ".join(f"{k}={v!r}" for k, v in 인.items()) if isinstance(인, dict) else ", ".join(repr(x) for x in (인 or []))
        호출 = f"답.{부른다}({인자})" if 부른다 else f"답.{_첫함수자리}({인자})"
        답값 = e.get("답")
        허용 = e.get("허용")
        if 허용 is not None and isinstance(답값, (int, float)):
            줄.append(f"_r = {호출}\nassert abs(float(_r) - {답값!r}) <= {허용!r}, f'예시 {i}: {{_r}} != {답값!r}'")
        else:
            줄.append(f"_r = {호출}\nassert _r == {답값!r}, f'예시 {i}: {{_r}} != {답값!r}'")
    줄.append("print('ok')")
    return "\n".join(줄) + "\n"


_첫함수자리 = "__첫함수__"       # 부른다 안 주면 검사가 못 고른다 -- 아래에서 부른다를 요구한다


# ---------------------------------------------------------------- 프롬프트
def 프롬프트(스펙: dict, 꼬리: str = "", 해본: "list[dict]" = ()) -> str:
    종류 = 스펙.get("종류", "수식")
    예시 = 스펙.get("예시") or []
    줄 = [f"[{종류}을(를) 실행 가능한 파이썬 함수로 바꿔라 -- 판정은 아래 검사의 끝값이 한다]",
         f"이름: {스펙.get('이름', '(없음)')}", f"원문: {스펙.get('원문', '')[:2000]}"]
    if 스펙.get("출처"):
        줄.append(f"출처: {스펙['출처']}")
    if 예시:
        부른다 = 예시[0].get("부른다") or "<함수이름>"
        줄 += ["", f"[예시 입출력 -- 이 값이 나와야 맞다. 함수 이름은 `{부른다}` 로 지어라]"]
        for e in 예시:
            줄.append(f"- {e.get('부른다', '')}({e.get('입력')}) == {e.get('답')}"
                     + (f" (±{e['허용']})" if e.get("허용") is not None else ""))
    if 꼬리:
        줄 += ["", "[지난 바퀴 검사 실패]", 꼬리[-800:]]
    if 해본:
        줄 += ["", "[이미 낸 코드 -- 같은 것을 또 내지 마라]"] + [f"- {h.get('요약', '')[:80]}" for h in 해본]
    줄 += ["", "[답 규약] ```python 블록 **하나**로 함수만 내라. 표준 라이브러리(math 등)만 써라. "
          "설명은 블록 밖에. 예시의 함수 이름을 그대로 써라."]
    return "\n".join(줄)


def _코드공기본(prompt: str) -> str:
    from router import call as R
    return R.부르기("코드공", prompt)["답"]


# ---------------------------------------------------------------- 원장·저장·색인
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


def 미해결들(repo=None) -> "list[str]":
    마지막: dict = {}
    for r in 원장읽기(repo):
        if r.get("꼴") == "코드화":
            마지막[r.get("이름", "")] = r.get("성공", False)
    return [n for n, ok in 마지막.items() if n and not ok]


def _이름안전(이름: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", 이름 or "x")[:50].strip("_") or "x"


# ---------------------------------------------------------------- 한 스펙 코드화
def 코드화(스펙: dict, repo=None, 바퀴: int = 기본바퀴) -> dict:
    repo = Path(repo or REPO)
    바퀴 = max(1, min(int(바퀴), 최대바퀴))
    예시 = 스펙.get("예시") or []
    검사 = 예시검사(예시)
    약한검증 = not 예시
    결과 = {"성공": False, "돌았나": True, "바퀴": 0, "약한검증": 약한검증, "코드": "",
           "해본것": [], "남은것": "", "파일": ""}
    시작 = time.monotonic()
    꼬리 = ""
    해본: list[dict] = []
    for n in range(1, 바퀴 + 1):
        결과["바퀴"] = n
        try:
            답 = (코드공 or _코드공기본)(프롬프트(스펙, 꼬리, 해본))
        except Exception as e:                                    # noqa: BLE001
            결과.update(돌았나=False, 남은것=f"코드공을 못 불렀다: {type(e).__name__}: {str(e)[:100]}")
            break
        코드 = ET.코드뽑기(답)
        if not 코드.strip():
            h = {"바퀴": n, "요약": "```python 블록 없음", "판정": "깨짐"}
        else:
            ok, 꼬리2 = ET.실행판정(코드, 검사, 초=int(스펙.get("초", 20)))
            꼬리 = 꼬리2 or 꼬리
            h = {"바퀴": n, "요약": (코드.splitlines() or [""])[0][:80], "판정": "통과" if ok else "실패", "꼬리": 꼬리2[-300:]}
            if ok:
                결과.update(성공=True, 코드=코드)
                해본.append(h)
                break
        h["코드해시"] = hash(코드.strip())
        if h["판정"] != "통과" and any(x.get("코드해시") == h["코드해시"] for x in 해본):
            h["판정"] = "반복"
            해본.append(h)
            결과["남은것"] = f"같은 코드를 되풀이한다 (바퀴 {n}) -- 코드공이 더 못 간다"
            break
        해본.append(h)
    결과["해본것"] = 해본
    if 결과["성공"]:
        이름 = _이름안전(스펙.get("이름", "x"))
        p = repo / 산출상대 / f"{이름}.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        머리 = (f"# codify: {스펙.get('이름', '')}\n# 출처: {스펙.get('출처', '')}\n"
              f"# 검증: {'예시 입출력 통과' if not 약한검증 else '약한 검증(예시 없음)'}\n\n")
        p.write_text(머리 + 결과["코드"], encoding="utf-8")
        결과["파일"] = f"{산출상대}/{이름}.py"
        _색인(결과["파일"], 스펙, 약한검증, repo)
    elif not 결과["남은것"]:
        결과["남은것"] = f"{len(해본)}바퀴에도 검사를 못 통과했다 -- 마지막 꼬리: {꼬리.splitlines()[-1][:120] if 꼬리 else '(없음)'}"
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "코드화",
                "이름": 스펙.get("이름", ""), "종류": 스펙.get("종류", ""), "출처": 스펙.get("출처", ""),
                "성공": 결과["성공"], "약한검증": 약한검증, "바퀴": 결과["바퀴"],
                "파일": 결과["파일"], "남은것": 결과["남은것"][:200]})
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    return 결과


def _색인(상대경로: str, 스펙: dict, 약한검증: bool, repo=None) -> None:
    """검사를 통과한 코드만 graph 에 -- 지은이='코드(검증통과)'. 검증 안 된 것은 기억에 안 들어온다."""
    try:
        from graph import store
        요약 = f"{스펙.get('종류', '')} 코드화: {스펙.get('이름', '')} -> {상대경로}" + (" (약한 검증)" if 약한검증 else " (예시 통과)")
        깃발 = re.findall(r"[0-9A-Za-z가-힣_-]{2,}", f"{스펙.get('이름', '')} {스펙.get('종류', '')} 코드화 codify")
        store.적기(요약, 깃발, 상대경로, repo=repo, 지은이="코드(검증통과)")
    except Exception:                                            # noqa: BLE001
        pass


# ---------------------------------------------------------------- 논문 한 편 코드화
def 논문코드화(arxiv_url: str, repo=None, 최대: int = 4, 바퀴: int = 기본바퀴) -> dict:
    """dig/paper 로 논문을 내린 뒤 수식·알고리즘을 차례로 코드화. 예시가 없으니 약한 검증이 많다."""
    from dig import paper
    논 = paper.논문받기(arxiv_url)
    스펙들 = []
    for i, 수 in enumerate(논.get("수식", [])[:최대]):
        스펙들.append({"종류": "수식", "이름": f"{논.get('id', 'paper')}_수식{i+1}", "원문": 수, "출처": arxiv_url,
                    "예시": [{"부른다": "f"}]})
    for i, a in enumerate(논.get("알고리즘", [])[:최대]):
        스펙들.append({"종류": "알고리즘", "이름": f"{논.get('id', 'paper')}_algo{i+1}", "원문": a, "출처": arxiv_url,
                    "예시": [{"부른다": "run"}]})
    # 예시 "부른다" 만 주고 값은 없으면 예시검사는 import·호출 가능만 본다(약한 검증). 함수 이름은 강제.
    for s in 스펙들:
        s["예시"] = []          # 논문은 보장된 입출력을 안 주므로 약한 검증으로 (안 속인다)
    결과들 = [코드화(s, repo=repo, 바퀴=바퀴) for s in 스펙들]
    성공 = sum(1 for r in 결과들 if r["성공"])
    return {"논문": 논.get("id") or arxiv_url, "제목": 논.get("제목", ""), "스펙수": len(스펙들),
            "성공": 성공, "결과들": 결과들, "못읽음": 논.get("못읽음", [])}


def 보고(결과: dict) -> str:
    if "결과들" in 결과:          # 논문
        줄 = [f"논문 코드화: {결과['제목'][:60]} <{결과['논문']}> -- 스펙 {결과['스펙수']} · 성공 {결과['성공']}"]
        for r in 결과["결과들"]:
            줄.append(f"  {'✓' if r['성공'] else '✗'} {r.get('파일') or r.get('남은것', '')[:60]}")
        return "\n".join(줄)
    줄 = [f"코드화: {'성공' if 결과['성공'] else '못 함'} (바퀴 {결과['바퀴']})"
         + (" [약한 검증: 예시 없음]" if 결과["약한검증"] else " [예시 통과]")]
    for h in 결과["해본것"]:
        줄.append(f"  바퀴 {h['바퀴']} {h['판정']}: {h.get('요약', '')[:70]}")
    if 결과["성공"]:
        줄.append(f"  -> {결과['파일']}")
    else:
        줄.append(f"  남은: {결과['남은것']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="논문의 수식·알고리즘을 검증된 코드로 바꾼다")
    ap.add_argument("--논문", default="", help="arXiv id 또는 url")
    ap.add_argument("--종류", default="수식", choices=("수식", "알고리즘"))
    ap.add_argument("--이름", default="")
    ap.add_argument("--원문", default="")
    ap.add_argument("--예시", default="", help="JSON: [{부른다,입력,답,허용}]")
    ap.add_argument("--바퀴", type=int, default=기본바퀴, help=f"최대 {최대바퀴}")
    args = ap.parse_args()
    if args.논문:
        url = args.논문 if "arxiv" in args.논문 else f"https://arxiv.org/abs/{args.논문}"
        r = 논문코드화(url, 바퀴=args.바퀴)
        print(보고(r))
        return 0 if r["성공"] else 1
    if not args.원문:
        print("--원문 또는 --논문 이 필요하다")
        return 3
    예시 = json.loads(args.예시) if args.예시 else []
    r = 코드화({"종류": args.종류, "이름": args.이름 or "x", "원문": args.원문, "예시": 예시}, 바퀴=args.바퀴)
    print(보고(r))
    if not r["돌았나"]:
        return 3
    return 0 if r["성공"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
