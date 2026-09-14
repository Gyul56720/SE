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
          "intent/ledger.jsonl",
          # **실측 2026-09-13 -- 신뢰 루트가 지난 세대를 지키고 있었다.** 위 넷은 2026-09-11
          # 의 채점표다. 그 뒤에 오늘의 채점표가 생겼는데(반례 사냥의 D_t · 성능 판정의
          # ACCEPT/REJECT · 먼검사의 빨강 이력) 이 목록은 안 따라왔다. 그래서 이 게이트가
          # 막으려던 바로 그 길 -- "채점표를 고쳐 실패를 없애는 것" -- 이 **오늘의 채점표에
          # 대해서는 열려 있었다.** G009 가 `mathmetics/.../verifier.py` 를 지키고 있는
          # 것과 같은 표류다. 목록이 도구를 안 따라가는 것이 표류의 꼴이므로,
          # tests/test_gate_g020.py 가 도구의 경로 상수와 이 목록을 맞춰 붙든다.
          "falsegreen/요약.jsonl",      # mutate.요약경로   -- D_t (잰변형·Killed·FG·못잼)
          "falsegreen/성능.jsonl",      # perf.성능경로     -- 성능 판정 ACCEPT/REJECT
          "falsegreen/정책.jsonl",      # policy.정책경로   -- π 의 채택 이력
          "falsegreen/먼검사.jsonl",    # farcheck.기록경로 -- 먼 검사의 빨강 이력
          "attic/vne/측정.jsonl")       # 2026-09-14 attic/ 으로 얼렸다. **자리가 바뀌어도
                                        # 지운 역사는 남는다** -- 원장은 얼려도 append-only 다

# **목록은 도구를 안 따라간다 -- 그래서 자리를 통째로 지킨다.** 실측 2026-09-14: `--묶음 vne`
# 가 제 계보(`falsegreen/요약-cut+vne.jsonl`)를 쓰기 시작했는데, 위 목록은 이름을 하나씩
# 적어 둔 것이라 **새 계보가 태어나는 순간 보호 밖이었다.** 묶음은 앞으로도 늘어난다.
# 이름을 따라 적는 대신 **`falsegreen/*.jsonl` 은 전부 append-only 로 친다** -- 이 폴더에
# 들어오는 것은 정의상 판정의 역사다. 새 계보가 생겨도 목록을 고칠 일이 없다.
보호접두 = (("falsegreen/", ".jsonl"),)


def 보호원장인가(path: str) -> bool:
    """이 경로가 판정 원장인가. 이름표(보호원장)와 자리(보호접두) 둘 다로 본다."""
    return path in 보호원장 or any(
        path.startswith(앞) and path.endswith(뒤) for 앞, 뒤 in 보호접두)


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
        if 보호원장인가(path):
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
