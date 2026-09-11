"""graph(밤일·색인·해시 대조)를 임시 저장소에서 **실제로 돌려** 붙든다.

붙드는 것: (1) 밤일이 노트를 간추려 깃발 색인을 만든다, (2) 다시 돌려도 안 부푼다,
(3) 깃발로 찾고 원문으로 되돌아간다, (4) 원본이 바뀌면 해시 어긋남을 **말한다**,
(5) 깃발 없음·출처 없음·저장소 밖 출처는 거절된다, (6) search_memory 에 색인이 얹힌다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_graph.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from graph import ask, night, store  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-graph-"))
repo = 임시 / "repo"
(repo / "public_agent_memory").mkdir(parents=True)
(repo / "reports").mkdir()

노트 = repo / "public_agent_memory" / "20260901-120000_촉매_실험_기록.md"
노트.write_text(
    "---\ntopic: '촉매 실험'\nsaved_at: 2026-09-01\n---\n\n"
    "# 촉매 실험\n\n백금 촉매 온도 350도에서 수율 82%. 촉매 갈래 중 백금이 제일 낫다.\n",
    encoding="utf-8")
보고 = repo / "reports" / "20260902_배송_지연.md"
보고.write_text("# 배송 지연 분석\n\n지연율 12%가 8월에 7%로 줄었다. 배송 원장 대조 결과.\n",
               encoding="utf-8")

try:
    print("== 밤일이 간추린다 ==")
    r = night.간추리기(repo=repo)
    ok(len(r["적음"]) == 2 and not r["거절"], f"둘 다 간추렸다 ({r})")
    nodes, 깨진 = store.읽기(repo)
    ok(len(nodes) == 2 and 깨진 == 0, f"원장에 두 줄 ({len(nodes)}줄, 깨진 {깨진})")
    촉매노드 = next(n for n in nodes if "촉매" in "".join(n["깃발"]) or "촉매" in n["요약"])
    ok("202609" in 촉매노드["깃발"], f"연월 깃발이 있다 ({촉매노드['깃발']})")
    ok(촉매노드["해시"] == store.해시(노트), "해시가 원본과 맞는다")

    print("\n== 다시 돌려도 안 부푼다 ==")
    r = night.간추리기(repo=repo)
    ok(not r["적음"] and r["그대로"] == 2, f"이미 있는 것은 건너뛴다 ({r})")
    nodes, _ = store.읽기(repo)
    ok(len(nodes) == 2, f"원장이 그대로 두 줄이다 ({len(nodes)})")

    print("\n== 깃발로 찾고 원문으로 되돌아간다 ==")
    hits = ask.찾기("촉매", repo=repo)
    ok(hits and "촉매" in hits[0][1]["요약"], f"'촉매' 로 찾힌다 ({len(hits)}개)")
    경고, 글 = ask.원문(hits[0][1], repo=repo)
    ok(not 경고 and "백금" in 글, "원문이 열리고 해시 경고가 없다")
    ok(not ask.찾기("엉뚱한말없는것", repo=repo), "없는 말은 빈손이다 -- 지어내지 않는다")

    print("\n== 원본이 바뀌면 말한다 ==")
    노트.write_text(노트.read_text(encoding="utf-8") + "\n(나중에 덧붙임)\n", encoding="utf-8")
    hits = ask.찾기("촉매", repo=repo)
    경고, _ = ask.원문(hits[0][1], repo=repo)
    ok("다르다" in 경고, f"**해시 어긋남을 말한다** ({경고[:40]!r})")
    r = night.간추리기(repo=repo)
    ok(len(r["적음"]) == 1, "바뀐 원본은 새 줄로 다시 간추려진다")
    hits = ask.찾기("촉매", repo=repo)
    경고, _ = ask.원문(hits[0][1], repo=repo)
    ok(not 경고, "다시 간추리면 최신 해시로 맞는다 (조회는 출처별 최신만)")
    nodes, _ = store.읽기(repo)
    ok(len(nodes) == 3, f"역사는 append-only 로 남는다 ({len(nodes)}줄)")

    print("\n== 성하지 않은 노드는 거절된다 ==")
    for 요약, 깃발, 출처, 왜 in [
        ("요약", [], "reports/20260902_배송_지연.md", "깃발 없음"),
        ("요약", ["---", ".."], "reports/20260902_배송_지연.md", "문장부호뿐인 깃발"),
        ("요약", ["a"], "reports/없는파일.md", "출처가 실재하지 않음"),
        ("요약", ["a"], "../밖.md", "저장소 밖 출처"),
        ("요약", ["a"], "/etc/passwd", "절대경로 출처"),
    ]:
        try:
            store.적기(요약, 깃발, 출처, repo=repo)
            ok(False, f"{왜} 이 막히지 않았다")
        except ValueError:
            ok(True, f"{왜} 은 ValueError 로 거절된다")

    print("\n== search_memory 에 색인이 얹힌다 (배선) ==")
    import agent_memory
    글월 = agent_memory._graph_hits.__doc__ or ""
    ok("깃발" in 글월, "_graph_hits 가 있다")
    원래 = agent_memory.search_memory.__code__.co_names
    ok("_graph_hits" in 원래, "search_memory 가 _graph_hits 를 실제로 부른다")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("graph: 간추리기 · 안 부풂 · 깃발 조회 · 해시 대조 · 거절 · 배선 -- 통과")
