"""저장된 원고에서 형식이 깨진 ops 를 걷어낸다.

2026-09-03 밤샘 런은 추출기가 낸 문자열을 world_ops 에 그대로 담았고, 그 씬들이 파일에
저장됐다. 이제 새로 들어오는 것은 _ops() 가 경계에서 거르지만 **이미 저장된 것은 그대로
남아 있다.** 그 상태로 다시 돌리면 관문이 매 씬마다 그 위반을 물고 늘어져 산문이
채워지지 않는다.

씬과 시나리오는 건드리지 않는다 -- 조립에 들인 디렉터 호출을 버릴 이유가 없다.
지우는 것은 형식이 깨진 ops 항목뿐이다.

실행:
    python3 novel/repair_ops.py                 # 무엇을 지울지 보여만 준다
    python3 novel/repair_ops.py --write         # 실제로 지우고 저장한다
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel.state import Novel                                         # noqa: E402

FIELDS = ("world_ops", "relation_ops", "fact_ops")


def why_bad(field: str, item, names: set) -> str:
    """이 항목이 왜 못 쓰는가. 쓸 수 있으면 빈 문자열.

    **산문 수리로는 못 고치는 것만 본다.** 씬의 ops 는 구조화된 선언이라 관문이 거기서
    위반을 잡아도 수리 루프는 산문만 다시 쓴다 -- 문장을 백 번 고쳐도 빈 members 는 그대로다.
    그래서 그런 씬은 시도 횟수를 다 쓰고 결정론적으로 실패한다(2026-09-04 시험 런:
    [V009/hard] 관계 구성원이 두 사람이 아니다: [] 로 4번 시도 111초, 그리고 blocked).
    고칠 수 없는 선언은 지우는 것이 맞다 -- 관계 선언 하나를 잃을 뿐, 씬과 산문은 산다."""
    if not isinstance(item, dict):
        return f"객체가 아니다 ({type(item).__name__})"
    if field == "relation_ops":
        members = list(item.get("members") or [])
        unknown = [m for m in members if m not in names]
        if unknown:
            return f"등장인물에 없는 인물: {unknown}"
        if len(members) != 2 or members[0] == members[1]:
            return f"구성원이 두 사람이 아니다: {members}"
        if item.get("op") not in ("start", "end"):
            return f"알 수 없는 op: {item.get('op')!r}"
    return ""


def scan(novel) -> list:
    """(씬 id, 필드, 항목, 사유) 목록."""
    names = {c.name for c in novel.characters}
    out = []
    for sc in novel.scenes:
        for f in FIELDS:
            for item in getattr(sc, f, None) or []:
                why = why_bad(f, item, names)
                if why:
                    out.append((sc.id, f, item, why))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="novel/romance.json")
    ap.add_argument("--write", action="store_true", help="실제로 고쳐 저장한다")
    a = ap.parse_args()

    path = Path(a.path)
    if not path.exists():
        print(f"{path} 가 없다.")
        return 1
    novel = Novel.load(path)
    bad = scan(novel)

    if not bad:
        print(f"{path}: 형식이 깨진 ops 가 없다. 고칠 것이 없다.")
        return 0

    print(f"{path}: 형식이 깨진 ops {len(bad)}개")
    for sid, field, item, why in bad[:20]:
        print(f"   {sid:20} {field:14} {why}")
        print(f"   {'':20} {'':14} {str(item)[:80]}")
    if len(bad) > 20:
        print(f"   ... 그리고 {len(bad) - 20}개 더")

    if not a.write:
        print("\n지우려면 --write 를 붙인다. 씬과 시나리오는 건드리지 않는다.")
        return 0

    names = {c.name for c in novel.characters}
    for sc in novel.scenes:
        for f in FIELDS:
            cur = getattr(sc, f, None) or []
            setattr(sc, f, [o for o in cur if not why_bad(f, o, names)])
        # 지우고 나면 다시 시도할 수 있다. 이 씬들은 산문이 없어서 잃을 것이 없다.
        if sc.status == "failed" and not sc.prose.strip():
            sc.status, sc.violations = "pending", []
    novel.save(path)
    print(f"\n{len(bad)}개를 지우고 저장했다. 씬 {len(novel.scenes)}개는 그대로다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
