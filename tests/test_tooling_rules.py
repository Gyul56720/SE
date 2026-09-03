"""도구 규칙 검사(tools/lint_tooling.py)가 **실제로 빨개지는가.**

빨개지지 못하는 검사는 장식이다. 초록만 뜨는 lint 는 아무것도 지키지 않으면서 지키고
있다는 착각을 준다 -- 이 저장소에서 하루 종일 고친 병이 정확히 그것이다(헛도는 심판).

그래서 규칙마다 **그 규칙이 막으려던 버그를 되살려** 빨개지는지 본다. 되살리는 방법은
그 버그를 고친 커밋을 되돌리는 것과 같은 한 줄 치환이다.

  RPM-분리     _is_rpm 을 지운다        -> 429 를 전부 일일 소진으로 적던 시절
  심판-재주입   final_verifier 를 지운다  -> 재계획이 심판을 지우던 시절
  재채점-출처   verify.TARGET 을 지운다   -> 거짓 경보를 내던 시절
  키-쌍        _FALLBACK 을 지운다       -> 내 컨테이너에서만 초록이던 시절
  마감-실측     TIMEOUT 을 60 으로       -> 504 를 우리가 만들던 시절
  예산-일치     기술서 예산을 손으로 적는다 -> 기술서와 실제가 조용히 어긋나는 자리
  계산-강제     계산 검사를 뗀다          -> 다섯 판 내리 상수표가 채택되던 시절
  미지-범주     미분류/상수표를 지운다     -> 하드코딩을 새 방법이라 부르던 시절
  구간-네자리   at_upper 를 지운다        -> 27 을 "구간 [19,23] 안"이라 하던 시절
  상태코드-분기 상태 분기를 지운다        -> 전부 "구글 쪽 문제"이던 시절
  판본-보존     _snapshot_code 를 지운다  -> 수리가 이전 판을 덮어쓰던 시절
  심판-무해     verify.py 에 lstsq 호출을 넣는다 -> 심판이 답을 담던 시절

첫 판에서 넷(RPM-분리 · 미지-범주 · 상태코드-분기 · 심판-무해)이 빨개지지 못했다.
셋은 규칙이 OR 라서 하나만 남겨도 통과했고 하나는 되살리는 방법이 약했다. **이 검사가
없었으면 이빨 없는 규칙 넷을 초록으로 착각했을 것이다** -- 헛도는 심판과 같은 병이다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import lint_tooling as lint  # noqa: E402

FAILURES: list[str] = []

# (규칙 id, 파일 상대경로, 바꿀 것, 바뀔 것)
MUTATIONS = [
    ("RPM-분리", "orchestrator/llm_pool.py", "_is_rpm(", "_gone_rpm("),
    ("심판-재주입", "orchestrator/problems/tensor_rank/run.py",
     "final_verifier=rel", "node_timeout=a.node_timeout"),
    ("재채점-출처", "orchestrator/problems/tensor_rank/run.py",
     "verify.TARGET", "verify.__doc__"),
    ("키-쌍", "tests/test_planner_repair.py",
     "GEMINI_API_KEY_FALLBACK", "GEMINI_API_KEY_SECOND"),
    ("마감-실측", "orchestrator/llm_pool.py",
     'GEMINI_TIMEOUT", "240"', 'GEMINI_TIMEOUT", "60"'),
    ("예산-일치", "orchestrator/problems/tensor_rank/run.py",
     "budget=a.node_timeout", "budget=600.0"),
    ("계산-강제", "orchestrator/planner.py",
     'or _computation_defect(run_dir, code)', ""),
    ("미지-범주", "orchestrator/method_trace.py", "미분류", "unknown_kind"),
    ("구간-네자리", "orchestrator/problems/tensor_rank/verify.py",
     '"at_upper"', '"inside2"'),
    ("상태코드-분기", "orchestrator/probe_gemini.py", "st in (", "st_was in ("),
    ("판본-보존", "orchestrator/planner.py", "_snapshot_code(", "_gone_snapshot("),
    # lstsq_rank 로 바꾸는 것으로는 안 걸린다 -- \blstsq\b 는 lstsq_rank 안에서 단어
    # 경계가 안 잡힌다. 심판이 실제로 풀이를 담은 모양(호출)으로 되살려야 한다.
    ("심판-무해", "orchestrator/problems/tensor_rank/verify.py",
     "def _rank_exact(rows)",
     "def _rank_exact(rows):\n    np.linalg.lstsq(A, b)\n\n\ndef _unused(rows)"),
]

# lint 가 읽는 파일들. 통째로 복사하지 않고 필요한 것만 옮긴다.
NEEDED = ["orchestrator/*.py", "orchestrator/problems/*/run.py",
          "orchestrator/problems/*/verify.py", "tests/*.py"]


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _stage(tmp: Path) -> None:
    for g in NEEDED:
        for src in REPO.glob(g):
            dest = tmp / src.relative_to(REPO)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def test_clean_repo_is_green() -> None:
    """지금 저장소는 통과해야 한다. 늘 빨간 검사는 곧 무시된다."""
    bad = lint.run()
    check(not bad, "깨끗한 저장소에서 위반이 나온다: " +
          "; ".join(f"{r['id']}: {m}" for r, m in bad[:4]))
    print(f"    [초록] 규칙 {len(lint.RULES)}개 통과")


def test_every_rule_can_go_red() -> None:
    """규칙마다 그 규칙이 막으려던 버그를 되살려 빨개지는지 본다.

    다른 규칙까지 같이 빨개지는 것은 상관없다 -- 확인할 것은 **해당 규칙이 잡는가**다."""
    ids = {r["id"] for r in lint.RULES}
    covered = {m[0] for m in MUTATIONS}
    check(ids == covered,
          f"검사가 없는 규칙이 있다: {sorted(ids - covered)} / "
          f"규칙이 없는 검사: {sorted(covered - ids)}")

    real = lint.REPO
    for rid, rel, old, new in MUTATIONS:
        rule = next((r for r in lint.RULES if r["id"] == rid), None)
        if rule is None:
            continue
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _stage(tmp)
            path = tmp / rel
            src = path.read_text(encoding="utf-8")
            if old not in src:
                check(False, f"{rid}: 되살릴 자리를 못 찾았다 ({rel}: {old!r})")
                continue
            path.write_text(src.replace(old, new), encoding="utf-8")
            lint.REPO = tmp
            try:
                bad = lint.run([rule])
            finally:
                lint.REPO = real
            check(bool(bad), f"{rid}: 버그를 되살렸는데 검사가 통과한다 ({rel})")
            if bad:
                print(f"    [빨강] {rid:12} {bad[0][1][:70]}")


def test_rules_carry_evidence() -> None:
    """규칙마다 근거 커밋과 실측 사유가 붙어 있는가.

    근거 없는 규칙은 다음 사람이 "이거 왜 있지" 하고 지운다. 실제로 이 규칙들은 전부
    하루 동안 물린 자국이고, 그 자국을 잃으면 규칙만 남아 미신이 된다."""
    for r in lint.RULES:
        check(bool(r.get("commit")), f"{r['id']}: 근거 커밋이 없다")
        check(len(r.get("why", "")) > 30, f"{r['id']}: 실측 사유가 너무 짧다")
        check(r.get("rule") in "①②③④⑤⑥⑦", f"{r['id']}: 문서의 규칙 번호가 없다")
    doc = (REPO / "docs" / "tooling-rules.md").read_text(encoding="utf-8")
    for r in lint.RULES:
        check(r["rule"] in doc, f"{r['id']}: 규칙 {r['rule']} 이 문서에 없다")


def main() -> int:
    for fn in (test_clean_repo_is_green, test_every_rule_can_go_red,
               test_rules_carry_evidence):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print(f"도구 규칙 검사: 깨끗하면 초록, 규칙 {len(lint.RULES)}개가 각자 빨개진다, "
          "근거 커밋 보존 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
