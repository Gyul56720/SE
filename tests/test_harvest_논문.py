"""harvest 의 arXiv 논문 수집 + 관심(분야 선택)을 가짜 검색·가짜 paper 로 붙든다. 도메인 무관.

사용자 규정: 수집은 사용자 관심(어느 도메인이든) + 자가 틈 둘 다에서. 최신 논문부터.

붙드는 것: (1) arxiv찾기 가 검색 결과마다 dig/paper 로 요지를 내려 arxiv-paper 항목으로,
(2) 관심더하기/읽기 가 dig/interests.jsonl 에 주제를 쌓고 틈찾기 가 그것을 검색어로,
(3) arXiv 라이선스는 허용 목록 -- 요지가 색인된다, (4) 막히면 그 출처만 멈춘다, (5) 배선.

network·LLM 없이 돈다(가짜 arxiv검색·paper 주입). 실행: python3 tests/test_harvest_논문.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from dig import fetch as F  # noqa: E402
from dig import harvest as H  # noqa: E402
from dig import paper as PP  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-hv논문-"))
repo = 임시 / "repo"
repo.mkdir()

try:
    print("== 관심: 어느 도메인이든 주제를 쌓는다 ==")
    ok(H.관심더하기("mechanism design in auctions", repo=repo) == "더했다", "주제 더하기")
    ok(H.관심더하기("protein folding", repo=repo) == "더했다", "다른 도메인도")
    ok(H.관심더하기("mechanism design in auctions", repo=repo) == "이미 있다", "중복은 안 쌓는다")
    ok(H.관심읽기(repo) == ["mechanism design in auctions", "protein folding"], f"읽기 ({H.관심읽기(repo)})")

    print("\n== 틈찾기: 관심이 검색어가 된다 (자가 틈과 함께) ==")
    (repo / "eval" / "tasks").mkdir(parents=True)
    틈 = H.틈찾기(repo)
    ok(any(g["갈래"] == "관심" and g["말"] == "protein folding" for g in 틈),
       f"**관심 분야가 수집 검색어로** ({[g['말'][:20] for g in 틈]})")

    print("\n== arxiv찾기: 검색 -> dig/paper 요지 -> arxiv-paper 항목 ==")
    H.arxiv검색 = lambda 말, 몇: [{"id": "2501.111", "제목": "Latest Method", "url": "https://arxiv.org/abs/2501.111"}]
    논 = {"id": "2501.111", "제목": "Latest Method", "url": "u", "초록": "we study it",
         "수식": ["\\nabla f"], "알고리즘": ["for x: step"], "그림": [], "표": [], "본문": "body",
         "된문": ["html"], "못읽음": []}
    PP.논문받기 = lambda url, 문들=("html",): 논
    try:
        items = H.arxiv찾기("x", 2, H.한도(), repo=repo)
        ok(len(items) == 1 and items[0]["종류"] == "arxiv-paper" and items[0]["라이선스"] == "arxiv",
           f"arxiv-paper 항목 ({items[0]['종류'] if items else None})")
        ok("Latest Method" in items[0]["이름"] and "\\nabla f" in items[0]["내용"],
           "요지에 제목·수식이 담긴다(비언어가 글자로)")
        ok(items[0]["수식수"] == 1 and items[0]["알고리즘수"] == 1, "수식·알고리즘 수를 센다")
    finally:
        PP.논문받기 = None
        H.arxiv검색 = None

    print("\n== arXiv 라이선스는 허용 -> 색인된다 ==")
    ok("arxiv" in H.허용라이선스, "arxiv 가 허용 목록")
    돼, _ = H.검증({"종류": "arxiv-paper", "내용": "# Latest Method\n수식...", "라이선스": "arxiv"})
    ok(돼, "arxiv 요지는 검증 통과")
    돼2, 까 = H.검증({"종류": "arxiv-paper", "내용": "", "라이선스": "arxiv"})
    ok(not 돼2 and "내용 없음" in 까, "빈 요지는 거절")

    print("\n== 한바퀴: arxiv 출처로 끝까지(색인) ==")
    H.arxiv검색 = lambda 말, 몇: [{"id": "2501.222", "제목": "P2", "url": "https://arxiv.org/abs/2501.222"}]
    PP.논문받기 = lambda url, 문들=("html",): {"id": "2501.222", "제목": "P2", "url": url, "초록": "abs",
                                           "수식": ["x=y"], "알고리즘": [], "그림": [], "표": [], "본문": "b",
                                           "된문": ["html"], "못읽음": []}
    try:
        r = H.한바퀴(["some topic"], repo=repo, 몇=1, 상한=5, 출처=("arxiv",))
        ok(r["돌았나"] and r["색인"] == 1, f"arxiv 논문 1편 색인 ({r['색인']})")
        from graph import ask
        찾 = ask.찾기("Latest Method OR P2 x y", repo=repo)
        ok(any("dig/corpus" in n["출처"] for _, n in 찾), "색인이 조회된다")
    finally:
        PP.논문받기 = None
        H.arxiv검색 = None
finally:
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import subprocess  # noqa: E402
ok("arxiv" in H.출처들, "출처에 arxiv")
p = subprocess.run(["python3", "dig/harvest.py", "--관심", "test topic here"], cwd=str(뿌리),
                   capture_output=True, text=True, timeout=30)
ok(p.returncode == 0 and ("더했다" in p.stdout or "이미 있다" in p.stdout), "--관심 CLI 가 돈다")
# 청소: 방금 더한 실제 관심 줄을 되돌린다(저장소 원장 오염 방지)
_i = 뿌리 / "dig" / "interests.jsonl"
if _i.is_file():
    줄들 = [x for x in _i.read_text(encoding="utf-8").splitlines() if "test topic here" not in x]
    _i.write_text(("\n".join(줄들) + "\n") if 줄들 else "", encoding="utf-8")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"dig/**.py"' in _wf, "dig/harvest 가 배포 경로에")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("harvest 논문: arxiv 요지 · 관심 분야 · 라이선스 · 한바퀴 색인 · 배선 -- 통과")
