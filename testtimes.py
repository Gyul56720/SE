"""testtimes -- 빠른 검사 목록을 **재서 고른다.** 손으로 적지 않는다.

사용자(2026-09-11): "가능한 모든 것들(시스템 망가짐을 방지하는 필수 원칙을 빼고) 나머지를
일반해로 바꿔."

`scripts/precheck.sh` 는 돌릴 검사 54개를 **파일 이름으로 나열**하고 있었다. 그래서 검사를
새로 만들 때마다 사람이 그 줄에 또 적어야 했고(이 세션에서만 여덟 번), 안 적으면 그 검사는
밀기 전에 **안 돌았다.** 목록이 곧 구멍이었다.

대신 **잰다.**

  · 검사 하나가 걸린 시간을 `logs/test_times.json` 에 쌓는다(gitignore -- 기계마다 다르다)
  · 빠른 검사는 **아직 안 재 본 것 + 상한보다 빠른 것**을 돌린다
  · 안 재 본 것은 **돌린다** -- 새 검사는 저절로 들어온다(목록에 적을 일이 없다)
  · 상한을 넘은 것은 건너뛰되 **몇 개를 왜 건너뛰는지 말한다**(조용히 빠지지 않는다)

원장은 **기계마다 다르므로** 커밋하지 않는다(gitignore). 그래서 `precheck` 처럼 임시
워크트리에서 돌 때는 **셀 곳(워크트리)과 원장 둘 곳(진짜 저장소)이 다르다** -- `--원장저장소`
로 가른다. 안 주면 둘이 같다.

    python3 testtimes.py --고르기 --상한 25     # 돌릴 것을 한 줄에 하나씩
    python3 testtimes.py --적기 tests/test_x.py 3.4
    python3 testtimes.py --보기
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
원장상대 = "logs/test_times.json"   # 이 기계에서 잰 것. gitignore -- 기계마다 다르다
씨앗상대 = "testtimes.json"        # **커밋된 씨앗.** 처음 온 기계도 맨손으로 시작하지 않는다
기본상한 = 25.0
# **빼는 것은 한 갈래뿐이고, 그것도 이름으로 적지 않는다.**
#
# precheck 를 **실제로 돌려 보는** 검사는 빠른 검사 안에서 돌리면 서로를 부른다.
# 빗장(PRECHECK_RUNNING)이 깊이를 막긴 하지만, 그러면 그 검사의 '실제로 돌려 보기'
# 대목이 **빈 검사**가 된다 -- 통과했다는 말만 남고 아무것도 안 본 것이다.
#
# 처음엔 `{"test_precheck.py"}` 라고 적었다. 그러자 precheck 를 돌리는 검사를 하나 더
# 만든 순간(`test_testtimes.py`) 그것이 빨개졌다 -- **이름을 적는 방식이 곧바로 틀렸다.**
# 그래서 이름이 아니라 **그 검사가 무엇을 하는지 읽어서** 가른다.
_되돌이표 = ("precheck.sh",)


def 되돌이인가(파일: Path) -> bool:
    """이 검사가 precheck 를 실제로 돌리는가 -- 그러면 빠른 검사 안에서 빼야 한다."""
    try:
        본 = 파일.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(표 in 본 for 표 in _되돌이표)


def _읽기(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        return j if isinstance(j, dict) else {}
    except (ValueError, OSError):
        return {}


def 씨앗(repo=None) -> dict:
    return _읽기(Path(repo or REPO) / 씨앗상대)


def 원장(repo=None, 원장저장소=None) -> dict:
    """씨앗 위에 이 기계에서 잰 것을 덮는다.

    씨앗만 있으면 **처음 돌리는 기계도 172개를 다 돌리지 않는다** -- 그것은 없애려던
    바로 그 기다림이다. 잰 것이 있으면 그것이 이긴다(이 기계가 더 느릴 수 있다).

    씨앗은 **검사를 세는 곳**(워크트리 = HEAD)에서, 잰 것은 `원장저장소`(진짜 저장소)에서
    읽는다. precheck 는 이 둘이 다르다."""
    repo = Path(repo or REPO)
    out = dict(씨앗(repo))
    out.update(_읽기(Path(원장저장소 or repo) / 원장상대))
    return out


def 적기(이름: str, 초: float, repo=None) -> None:
    repo = Path(repo or REPO)
    j = 원장(repo)
    j[Path(이름).name] = round(float(초), 2)
    p = repo / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(j, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def 검사들(repo=None) -> "list[str]":
    repo = Path(repo or REPO)
    return sorted(str(p.relative_to(repo)) for p in (repo / "tests").glob("test_*.py") if p.is_file())


def 고르기(repo=None, 상한: float = 기본상한, 다시: bool = False, 원장저장소=None) -> "tuple[list[str], list[tuple[str, float]]]":
    """(돌릴 것, [(건너뛸 것, 잰 시간)]). 안 재 본 것은 **돌린다** -- 새 검사가 저절로 들어온다.

    `원장저장소` 를 주면 **셀 곳과 원장 둘 곳을 가른다**(워크트리에서 돌면서 진짜 저장소의
    원장을 읽는 경우)."""
    repo = Path(repo or REPO)
    잰것 = 원장(repo, 원장저장소)
    돌릴, 건너 = [], []
    for rel in 검사들(repo):
        이름 = Path(rel).name
        if 되돌이인가(repo / rel):
            continue
        t = 잰것.get(이름)
        if not 다시 and t is not None and t > 상한:
            건너.append((rel, t))
        else:
            돌릴.append(rel)
    return 돌릴, 건너


def 씨앗쓰기(repo=None) -> int:
    """이 기계에서 잰 것을 **커밋할 씨앗으로 굳힌다.** 사람이 숫자를 적지 않는다."""
    repo = Path(repo or REPO)
    j = 원장(repo, repo)
    (repo / 씨앗상대).write_text(json.dumps(j, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    return len(j)


def 보고(repo=None, 상한: float = 기본상한, 원장저장소=None) -> str:
    돌릴, 건너 = 고르기(repo, 상한, False, 원장저장소)
    잰것 = 원장(repo, 원장저장소)
    안잰 = [r for r in 돌릴 if Path(r).name not in 잰것]
    줄 = [f"검사 {len(검사들(repo))}개 -- 빠른 검사에서 {len(돌릴)}개 돌리고 {len(건너)}개 건너뛴다 (상한 {상한}초)",
         f"  아직 안 재 본 것 {len(안잰)}개 (돌린다 -- 새 검사는 저절로 들어온다)"]
    for rel, t in sorted(건너, key=lambda x: -x[1])[:10]:
        줄.append(f"    건너뜀 {Path(rel).name} ({t}초)")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="빠른 검사 목록을 재서 고른다")
    ap.add_argument("--고르기", action="store_true")
    ap.add_argument("--적기", nargs=2, metavar=("검사", "초"))
    ap.add_argument("--보기", action="store_true")
    ap.add_argument("--씨앗쓰기", action="store_true", help="잰 것을 커밋할 씨앗으로 굳힌다")
    ap.add_argument("--상한", type=float, default=기본상한)
    ap.add_argument("--다시", action="store_true", help="잰 것을 무시하고 전부 돌린다(다시 재기)")
    ap.add_argument("--저장소", default="", help="검사를 셀 곳(기본: 이 파일의 저장소)")
    ap.add_argument("--원장저장소", default="", help="원장을 읽고 쓸 곳. 워크트리에서 돌 때 진짜 저장소를 가리킨다")
    a = ap.parse_args()
    repo = Path(a.저장소) if a.저장소 else None
    원 = Path(a.원장저장소) if a.원장저장소 else None
    if a.적기:
        적기(a.적기[0], float(a.적기[1]), 원 or repo)
        return 0
    if a.씨앗쓰기:
        print(f"씨앗 {씨앗쓰기(원 or repo)}개를 {씨앗상대} 에 굳혔다")
        return 0
    if a.고르기:
        돌릴, _ = 고르기(repo, a.상한, a.다시, 원)
        print("\n".join(돌릴))
        return 0
    print(보고(repo, a.상한, 원))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
