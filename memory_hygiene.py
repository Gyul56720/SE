"""
메모리 위생 -- 코드/게이트와 모순되는 노트를 지우고, 승격된 노트는 근거로 격하한다.

이 저장소의 메모리는 39개까지 늘었지만 행동은 개선되지 않았다. 원인은 노트가 늘어나는
속도가 아니라, 노트끼리 그리고 노트와 코드가 서로 어긋난 채 방치된다는 데 있다. 코퍼스
자신이 이미 그 진단을 담고 있다 (20260828-152712_보고_규범과_메모리_정책의_한계.md):

    "메모리에 적은 정책은 코드가 강제하지 않으면 지켜지지 않는다. push 금지 노트가
     있었는데도 challenge3 산출물이 main에 push됐다. ... 그 노트는 코드와 모순되어
     2026-08-28에 삭제됐다. 동작을 바꾸려면 메모리가 아니라 코드를 고쳐야 한다."

이 모듈은 그 선례를 절차로 만든 것이다. 세 부류를 구분한다.

  1. CONTRADICTED -- 코드나 게이트가 금지하는 행동을 지시하는 노트. 지운다.
     읽히면 해로우므로 남겨둘 이유가 없다.
  2. DUPLICATE    -- 다른 경로에 바이트 단위로 같은 사본. 유령 사본을 지운다.
  3. PROMOTED     -- 게이트가 EVIDENCE로 참조하는 노트. 지우지 않고 배너만 붙인다.
     G003의 교훈이 "실측 근거가 적힌 주석은 재발 방지 기록이다, 지우지 마라"인데
     같은 것을 메모리에서 지우면 자기모순이다. 다만 이제 그 노트는 규범이 아니라
     게이트의 근거 문서다 -- 규범은 gates/ 에 있다.

모순 판정은 모델에게 묻지 않는다. 선언된 대조표 + 파일 내용에 실제로 걸리는 기계적
탐지자로만 판정한다. 탐지자가 걸리지 않으면 지우지 않는다(과잉 삭제에 대해 fail-closed).

사용:
    python3 memory_hygiene.py            # 무엇을 할지 보고만 (dry-run)
    python3 memory_hygiene.py --apply    # 실제로 삭제/주석 적용
"""
from __future__ import annotations

import argparse
import filecmp
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
MEMORY_DIR = REPO_DIR / "public_agent_memory"
# 오타로 생긴 유령 폴더. 이름이 ".py"로 끝나는 디렉터리라 gates/G001이 파일인 줄 알고
# 열다가 IsADirectoryError로 죽었다 (실측 확인됨) -- 실제로 해를 끼친 사본이다.
STRAY_DIR = REPO_DIR / "public_agent.py"

sys.path.insert(0, str(REPO_DIR))


@dataclass
class Contradiction:
    path: str            # 저장소 기준 상대 경로
    detector: str        # 이 문자열이 노트 안에 실제로 있어야만 삭제한다
    contradicted_by: str  # 무엇이 이 노트를 무효화하는가
    reason: str


CONTRADICTIONS = [
    Contradiction(
        path="public_agent_memory/20260827-172721_self-modification_방법론과_코드.md",
        detector="path.write_text(new_content",
        contradicted_by="gates/G005_rewrite_scale.py + "
                        "public_agent_memory/20260828-202743_자기_코드_수정은_재작성이_아니라_패치로.md",
        reason="파일 전체를 새 내용으로 덮어쓰고 곧바로 add/commit/push하는 절차를 "
               "self-modification 방법론으로 제시한다. 이것이 1a82685 자기 재작성 붕괴의 "
               "실행 절차 그 자체이고, 그 사고 후 저장한 노트는 정반대를 지시한다"
               "('기존 파일을 고칠 때 전체를 다시 쓰지 마라'). 검증 단계도 git diff까지만이라 "
               "임포트 확인이 빠져 있다 -- b32aa78이 그래서 났다.",
    ),
    Contradiction(
        path="public_agent.py/20260827-172649_public_agent_memory_폴더_구조_규칙.md",
        detector="2-depth",
        contradicted_by="agent_memory._resolve_inside_memory()",
        reason="메모리를 하위 폴더로 구성하라고 지시하지만, agent_memory.py는 "
               "path.parent != MEMORY_DIR 이면 ValueError를 던져 하위 폴더 쓰기를 "
               "코드로 막는다. 지킬 수 없는 지시다.",
    ),
]


@dataclass
class Action:
    kind: str      # DELETE / ANNOTATE
    path: Path
    why: str


def _gate_evidence() -> "dict[str, list[str]]":
    """게이트가 EVIDENCE로 참조하는 노트 -> 그 노트를 근거로 삼는 게이트 ID 전부.
    한 노트가 여러 게이트를 낳을 수 있다 -- G001/G002/G006은 모두 같은 노트에서 왔다.
    덮어쓰면 배너에 게이트 하나만 적혀 나머지 연결이 보이지 않는다."""
    import gatekeeper
    out: dict[str, list[str]] = {}
    for mod in gatekeeper.load_gates():
        ev = getattr(mod, "EVIDENCE", "")
        if ev:
            out.setdefault(ev, []).append(getattr(mod, "RULE_ID", mod.__name__))
    return {k: sorted(v) for k, v in out.items()}


BANNER = "> [승격됨] 이 노트의 규범은 {gate} 게이트로 코드화되어 커밋 경로에서 강제된다.\n" \
         "> 이 문서는 그 게이트의 근거 기록이며, 규범 자체는 여기가 아니라 gates/ 에 있다.\n\n"


def plan() -> "list[Action]":
    actions: list[Action] = []

    # 1. 코드/게이트와 모순되는 노트
    for c in CONTRADICTIONS:
        path = REPO_DIR / c.path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if c.detector not in text:
            # 탐지자가 안 걸리면 내가 아는 그 노트가 아니다 -- 지우지 않는다.
            actions.append(Action("SKIP", path,
                                  f"탐지자 '{c.detector}' 가 내용에 없다 -- 안전을 위해 건드리지 않음"))
            continue
        actions.append(Action("DELETE", path, f"{c.reason}\n      무효화 근거: {c.contradicted_by}"))

    # 2. 유령 폴더의 바이트 동일 사본
    if STRAY_DIR.is_dir():
        for path in sorted(STRAY_DIR.rglob("*")):
            if not path.is_file():
                continue
            twin = MEMORY_DIR / path.name
            if twin.is_file() and filecmp.cmp(path, twin, shallow=False):
                actions.append(Action("DELETE", path,
                                      f"public_agent_memory/{path.name} 와 바이트 단위로 동일한 유령 사본"))

    # 3. 게이트로 승격된 노트 -> 배너
    for rel, gate_ids in _gate_evidence().items():
        path = REPO_DIR / rel
        if not path.is_file():
            continue
        if "[승격됨]" in path.read_text(encoding="utf-8"):
            continue
        actions.append(Action("ANNOTATE", path,
                              f"{', '.join(gate_ids)} 게이트로 코드화됨 -- 근거 문서로 격하"))

    return actions


def apply(actions: "list[Action]") -> "list[str]":
    done = []
    for a in actions:
        if a.kind == "DELETE":
            a.path.unlink()
            done.append(f"삭제 {a.path.relative_to(REPO_DIR)}")
        elif a.kind == "ANNOTATE":
            text = a.path.read_text(encoding="utf-8")
            gate_id = a.why.split(" 게이트로")[0]
            if text.startswith("---"):
                end = text.find("\n---", 3)
                head, body = text[:end + 4], text[end + 4:]
            else:
                head, body = "", text
            a.path.write_text(head + "\n" + BANNER.format(gate=gate_id) + body.lstrip("\n"),
                              encoding="utf-8")
            done.append(f"배너 {a.path.relative_to(REPO_DIR)}")
    # 빈 유령 폴더 정리
    if STRAY_DIR.is_dir() and not any(STRAY_DIR.rglob("*.md")):
        remaining = [p for p in STRAY_DIR.rglob("*") if p.is_file()]
        if not remaining:
            for d in sorted(STRAY_DIR.rglob("*"), reverse=True):
                d.rmdir()
            STRAY_DIR.rmdir()
            done.append("삭제 public_agent.py/ (빈 유령 폴더)")
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="실제로 적용한다 (기본은 보고만)")
    args = parser.parse_args()

    actions = plan()
    if not actions:
        print("정리할 것이 없다.")
        return 0

    for kind in ("DELETE", "ANNOTATE", "SKIP"):
        group = [a for a in actions if a.kind == kind]
        if not group:
            continue
        print(f"\n[{kind}] {len(group)}건")
        for a in group:
            print(f"  {a.path.relative_to(REPO_DIR)}\n      {a.why}")

    if not args.apply:
        print("\n(dry-run) 실제로 적용하려면 --apply")
        return 0
    print()
    for line in apply(actions):
        print(" ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
