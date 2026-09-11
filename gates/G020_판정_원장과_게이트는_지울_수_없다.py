"""G020 -- 판정 원장과 게이트는 지울 수 없다 (evolve 의 상한).

자기 개조(evolve)를 허용하는 저장소에서 제일 먼저 막아야 하는 길은 **채점표를 고쳐
실패를 없애는 것**이다. orchestrator 가 "verifier 는 절대 다시 쓰지 않는다" 고 적어
둔 그 원칙의 저장소 전체 판이다: 판정의 역사가 지워질 수 있으면 후퇴 감시(eval) ·
채택률(router) · 해시 대조(graph) · 승인 기록(intent)이 전부 뜻을 잃는다.

무엇을 잡는가:
  1. 판정 원장에서 줄이 **지워지는** 커밋 -- 이 원장들은 append-only 다. 어긋남과
     빨강을 지우는 것은 고치는 것이 아니라 눈을 감는 것이다.
     (graph/ledger.jsonl 은 대상이 아니다 -- 그것은 원본에서 재구축되는 파생 색인이라
     다시 짓는 것이 정당하다. 역사와 색인을 가르는 것이 이 게이트의 반이다.)
  2. gates/*.py 파일이 통째로 **지워지는** 커밋 -- 게이트를 지우는 것이 가장 싼 우회다.
     이 저장소는 제약이 조용히 사라지는 사고를 이미 겪었다(1a82685, G014 의 기록).

무엇을 안 잡는가: 원장에 줄을 더하는 것(그것이 원장의 일이다) · 게이트 파일의 수정
(약화는 G008/G009 와 사람 리뷰의 영역) · 파생 문서(digest.md 등)의 재작성.
사람이 의도적으로 원장을 옮기거나 게이트를 갈아치울 때는 이 게이트도 함께 고친다 --
그때는 이 파일이 같은 diff 에 보이므로 리뷰에서 드러난다(G009 와 같은 절차).
"""
from __future__ import annotations

RULE_ID = "G020"
TITLE = "판정 원장과 게이트는 지울 수 없다"
ORIGIN = "2026-09-11 HARNESS_PLAN 6단계 -- evolve 의 상한 (채점표를 고쳐 실패를 없애는 길 차단)"
EVIDENCE = ""

# 판정의 역사가 담기는 원장들. 파생 색인(graph/ledger.jsonl)은 일부러 없다.
보호원장 = ("eval/ledger.jsonl", "router/ledger.jsonl", "graph/edges.jsonl",
          "intent/ledger.jsonl")


def _경로풀기(path: str) -> str:
    """git 은 비ASCII 경로를 "\\353..." 꼴로 인용한다(core.quotepath 기본값). 풀지
    않으면 한글 이름의 게이트(G012_봇을_... 등 -- 이 저장소 게이트의 태반이다)를
    지워도 startswith("gates/") 에 안 걸린다. sandbox 의 지금트리 복사가 같은 자리에서
    물렸던 바로 그 버그이고, 이 게이트의 검사가 실측으로 잡았다."""
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        try:
            path = (path[1:-1].encode("latin-1", "backslashreplace")
                    .decode("unicode_escape").encode("latin-1").decode("utf-8", "replace"))
        except (UnicodeDecodeError, UnicodeEncodeError):
            return path
    return path


def check(ctx) -> "list[str]":
    violations: list = []
    for line in ctx.diff_numstat().splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts[0].strip(), parts[1].strip(), _경로풀기(parts[2].strip())
        try:
            del_n = int(deleted)
        except ValueError:
            continue                      # 바이너리("-")나 이름 바꿈 꼴은 여기 원장이 아니다
        if del_n <= 0:
            continue
        if path in 보호원장:
            어디로갔나 = "" if (ctx.repo / path).is_file() else " (파일째 사라졌다)"
            violations.append(
                f"{path}: 줄 {del_n}개가 지워졌다{어디로갔나} -- 판정 원장은 append-only 다. "
                f"어긋남·빨강을 지우는 것은 고치는 것이 아니다")
        elif path.startswith("gates/") and path.endswith(".py") \
                and not (ctx.repo / path).is_file():
            violations.append(
                f"{path}: 게이트가 통째로 지워졌다 -- 게이트를 지우는 것이 가장 싼 우회다. "
                f"낡은 게이트는 지우지 말고 사람이 검토해 고쳐라")
    return violations
