"""intent/store -- 목표 원장. 제안은 누구나(에이전트 포함), **집히는 것은 승인된 것만.**

HARNESS_PLAN 6단계: 에이전트가 스스로 목표를 만들 수는 있어도 실행은 사람이 승인한
목표만이다. 그 경계를 말이 아니라 코드가 지킨다 -- `집기()` 는 승인 사건이 원장에
없는 목표를 **돌려주지 않는다.** 밤 루프든 에이전트든 다음 일감은 집기로만 받는다.

원장(intent/ledger.jsonl)은 append-only 사건 기록이다. 상태는 사건을 접어서 나온다:

    제안 ──승인──> 승인됨 ──끝──> 끝남
      │              └──버림──> 버림
      └──버림──> 버림

**"끝났다" 는 말이 아니라 명령이 정한다.** 목표에 판정명령이 있으면 끝 처리 때 그
명령을 실제로 돌려 exit 0 일 때만 끝 사건이 적힌다 -- 실패하면 출력 꼬리와 함께
거절된다. 판정명령이 없는 목표는 코드가 못 재는 것이므로(관할 밖을 적는 규율) 사람
선언으로 끝난다. 둘을 섞지 않는다: 판정명령이 있으면 사람 말로는 못 끝낸다.

코드가 강제하는 경계와 못 하는 경계를 갈라 적는다: "승인 없는 목표는 안 집힌다" 는
여기 코드가 지키고, "승인 주체가 사람이다" 는 관리 채널 화이트리스트(discord_cmd)가
지킨다 -- CLI 승인은 셸을 가진 자의 것이므로 원장에 누가 승인했는지를 남겨 추적한다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
원장상대 = "intent/ledger.jsonl"
목표상한 = 300
판정시간 = 120


def _원장(repo=None) -> Path:
    return Path(repo or REPO) / 원장상대


def 사건들(repo=None) -> "list[dict]":
    path = _원장(repo)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("꼴") and e.get("id"):
            out.append(e)
    return out


def _적기(repo, 사건: dict) -> None:
    path = _원장(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    사건 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **사건}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(사건, ensure_ascii=False) + "\n")


def 상태표(repo=None) -> "dict[str, dict]":
    """id -> {목표, 왜, 판정명령, 누가, 상태, 때}. 사건을 순서대로 접는다."""
    out: dict = {}
    for e in 사건들(repo):
        if e["꼴"] == "제안":
            out[e["id"]] = {"id": e["id"], "목표": e.get("목표", ""), "왜": e.get("왜", ""),
                            "판정명령": e.get("판정명령", ""), "누가": e.get("누가", "?"),
                            "상태": "제안됨", "때": e.get("때", "")}
        elif e["id"] in out:
            g = out[e["id"]]
            if e["꼴"] == "승인" and g["상태"] == "제안됨":
                g["상태"] = "승인됨"
                g["승인한이"] = e.get("누가", "?")
            elif e["꼴"] == "끝" and g["상태"] == "승인됨":
                g["상태"] = "끝남"
            elif e["꼴"] == "버림" and g["상태"] in ("제안됨", "승인됨"):
                g["상태"] = "버림"
    return out


def 제안(목표: str, 왜: str = "", 판정명령: str = "", 누가: str = "cli", repo=None) -> str:
    목표 = " ".join((목표 or "").split())[:목표상한]
    if not 목표:
        raise ValueError("목표가 비었다")
    기록id = time.strftime("%Y%m%d%H%M%S") + "-" + __import__("os").urandom(2).hex()
    _적기(repo, {"꼴": "제안", "id": 기록id, "목표": 목표, "왜": 왜,
                "판정명령": 판정명령, "누가": 누가})
    return 기록id


def 승인(기록id: str, 누가: str = "cli", repo=None) -> str:
    g = 상태표(repo).get(기록id)
    if g is None:
        return f"그런 목표가 없다: {기록id}"
    if g["상태"] != "제안됨":
        return f"제안됨 상태가 아니다({g['상태']}) -- 승인할 것이 없다"
    _적기(repo, {"꼴": "승인", "id": 기록id, "누가": 누가})
    return f"승인됨: {g['목표'][:60]}"


def 버림(기록id: str, 왜: str = "", 누가: str = "cli", repo=None) -> str:
    g = 상태표(repo).get(기록id)
    if g is None:
        return f"그런 목표가 없다: {기록id}"
    if g["상태"] in ("끝남", "버림"):
        return f"이미 {g['상태']}이다"
    _적기(repo, {"꼴": "버림", "id": 기록id, "왜": 왜, "누가": 누가})
    return f"버림: {g['목표'][:60]}"


def 끝(기록id: str, 누가: str = "cli", repo=None) -> "tuple[bool, str]":
    """(끝났는가, 말). 판정명령이 있으면 **그 명령이 판정한다** -- 사람 말로는 못 끝낸다."""
    repo = Path(repo or REPO)
    g = 상태표(repo).get(기록id)
    if g is None:
        return False, f"그런 목표가 없다: {기록id}"
    if g["상태"] != "승인됨":
        return False, f"승인됨 상태가 아니다({g['상태']}) -- 승인 없이 끝나는 목표는 없다"
    명령 = g.get("판정명령", "")
    if 명령:
        try:
            p = subprocess.run(["bash", "-lc", 명령], cwd=str(repo), capture_output=True,
                               text=True, errors="replace", timeout=판정시간)
        except subprocess.TimeoutExpired:
            return False, f"판정명령이 {판정시간}초 안에 안 끝났다 -- 끝나지 않은 것으로 다룬다"
        if p.returncode != 0:
            꼬리 = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-3:]
            return False, (f"판정명령이 exit {p.returncode} -- **아직 안 끝났다.** "
                           f"말이 아니라 명령이 정한다\n" + "\n".join(꼬리))
        근거 = f"판정명령 exit 0: {명령[:80]}"
    else:
        근거 = f"판정명령 없음 -- {누가} 의 선언 (코드가 못 재는 목표라고 제안 때 적힌 것)"
    _적기(repo, {"꼴": "끝", "id": 기록id, "누가": 누가, "근거": 근거})
    return True, f"끝남: {g['목표'][:60]} ({근거})"


def 집기(repo=None) -> "list[dict]":
    """**승인된** 미완 목표, 오래된 것부터. 승인 사건이 없는 목표는 여기 안 나온다 --
    그것이 이 모듈의 존재 이유다."""
    return sorted([g for g in 상태표(repo).values() if g["상태"] == "승인됨"],
                  key=lambda g: g["때"])


def 한줄(g: dict) -> str:
    재는법 = "명령판정" if g.get("판정명령") else "사람선언"
    return f"[{g['id']}] ({g['상태']}·{재는법}) {g['목표'][:80]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="목표 원장 -- 승인 없는 목표는 집히지 않는다")
    ap.add_argument("--목록", action="store_true")
    ap.add_argument("--다음", action="store_true", help="집기 -- 승인된 미완 목표")
    ap.add_argument("--제안", default="")
    ap.add_argument("--왜", default="")
    ap.add_argument("--판정", default="", help="끝났는가를 재는 셸 명령 (exit 0 = 끝)")
    ap.add_argument("--승인", default="", metavar="ID")
    ap.add_argument("--끝", default="", metavar="ID")
    ap.add_argument("--버림", default="", metavar="ID")
    args = ap.parse_args()
    if args.제안:
        기록id = 제안(args.제안, 왜=args.왜, 판정명령=args.판정)
        print(f"제안됨 [{기록id}] -- 승인 전에는 집히지 않는다: "
              f"python3 intent/store.py --승인 {기록id}")
        return 0
    if args.승인:
        print(승인(args.승인))
        return 0
    if args.끝:
        됐다, 말 = 끝(args.끝)
        print(말)
        return 0 if 됐다 else 1
    if args.버림:
        print(버림(args.버림))
        return 0
    if args.다음:
        골들 = 집기()
        if not 골들:
            print("승인된 미완 목표가 없다 -- 제안은 있어도 승인 없이는 안 집힌다")
            return 3
        for g in 골들:
            print("  " + 한줄(g))
        return 0
    for g in sorted(상태표().values(), key=lambda x: x["때"]):
        print("  " + 한줄(g))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
