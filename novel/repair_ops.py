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


def scan(novel) -> list:
    """(씬 id, 필드, 잘못된 항목) 목록."""
    out = []
    for sc in novel.scenes:
        for f in FIELDS:
            for item in getattr(sc, f, None) or []:
                if not isinstance(item, dict):
                    out.append((sc.id, f, item))
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
    for sid, field, item in bad[:20]:
        print(f"   {sid:20} {field:14} {type(item).__name__} {str(item)[:60]!r}")
    if len(bad) > 20:
        print(f"   ... 그리고 {len(bad) - 20}개 더")

    if not a.write:
        print("\n지우려면 --write 를 붙인다. 씬과 시나리오는 건드리지 않는다.")
        return 0

    for sc in novel.scenes:
        for f in FIELDS:
            cur = getattr(sc, f, None) or []
            setattr(sc, f, [o for o in cur if isinstance(o, dict)])
    novel.save(path)
    print(f"\n{len(bad)}개를 지우고 저장했다. 씬 {len(novel.scenes)}개는 그대로다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
