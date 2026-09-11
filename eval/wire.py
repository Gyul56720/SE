"""eval/wire -- **배선 점검.** 기관들이 말로만 이어져 있는지, 실제로 이어져 있는지 본다.

검사(tests/)는 각 기관을 따로 붙든다. 여기서 보는 것은 다르다: **진짜 저장소에서,
진짜 데이터로, 끝에서 끝까지 한 바퀴가 도는가.** 단위 검사가 전부 초록인데 배선이
끊겨 있는 상태가 이 저장소의 단골 실패다(드러나는 꼴은 늘 "봇이 그것을 모른다" 다).

두 부분이다.

  읽기 점검 -- 진짜 저장소에서 그대로 돈다. 임포트 · 고정 명령 8갈래 · 각 기관의
              진입점 · 원장의 줄 수. 아무것도 안 고친다.
  한 바퀴  -- **격리 판(sandbox)에서** 쓰기 흐름까지 돈다: 새 노트 하나를 넣고
              간추리기 -> 판정 -> 요지문까지 이어지는가, 목표가 승인 없이 안 집히는가.
              저장소를 안 더럽히므로 운영 중에도 돌릴 수 있다(sandbox 가 그 보증이다).

판정은 끝값 관례 그대로: `0` 이어짐 · `3` **못돌림**(재료·키가 없어 안 잰 것 -- 초록이
아니다) · 그 외 **끊김**. 못돌림을 초록으로 뭉개지 않는 것이 이 파일의 요점이다.

쓰기:
    python3 eval/wire.py            # 읽기 점검 + 한 바퀴
    python3 eval/wire.py --읽기만    # 격리 판을 안 깐다 (빠르다)
끝값: 0 끊김 없음 · 1 끊긴 것 있음 · 3 못돌림만 있고 끊김은 없음
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# (이름, argv, 기대끝값들, 무엇을 보는가)
읽기점검 = [
    ("임포트:dispatch", ["python3", "-c", "import dispatch; print(len(dispatch.명령들))"],
     (0,), "봇이 고정 명령 배선을 들여올 수 있는가"),
    ("임포트:bot_tools", ["python3", "-c", "import bot_tools; print('ok')"],
     (0,), "봇 도구(run_shell·run_experiment)가 임포트되는가"),
    ("기관:sandbox", ["python3", "sandbox/run.py", "--", "true"],
     (0,), "격리 판이 실제로 깔리는가"),
    ("기관:graph조회", ["python3", "graph/ask.py", "--말", "메모리"],
     (0, 3), "깃발 색인이 답하는가"),
    ("기관:graph판정", ["python3", "graph/link.py", "--보기"],
     (0, 3), "다섯 꼴 간선이 적혀 있는가"),
    ("기관:audit", ["python3", "audit/run.py", "--초", "30"],
     (0, 1), "변경 감사가 도는가 (1 은 검사 실패 -- 배선은 이어짐)"),
    ("기관:eval답", ["python3", "eval/answers.py"],
     (0,), "답 회귀가 지금 트리에서 통과하는가"),
    ("기관:router", ["python3", "router/check.py"],
     (0, 1, 3), "경로 심판이 도는가"),
    ("기관:intent", ["python3", "intent/store.py", "--목록"],
     (0,), "목표 원장을 읽는가"),
    ("기관:evolve", ["python3", "gatekeeper.py"],
     (0,), "게이트 전부가 통과하는가 (승격 경로의 바탕)"),
    ("기관:toolgate", ["python3", "toolgate.py", "rm -rf gates/"],
     (1,), "도구 게이트가 게이트 삭제를 **차단**하는가 (끝값 1 이 옳다)"),
    ("기관:eval과제", ["python3", "eval/tasks.py", "--목록"],
     (0,), "절대 기준 과제가 읽히는가 (호출 0회)"),
    ("기관:harvest", ["python3", "dig/harvest.py", "--틈만"],
     (0, 3), "수집기가 자의 틈을 읽는가 (망 없음 · 3 은 틈 없음)"),
    ("기관:mailer", ["python3", "mailer.py", "--필요"],
     (0, 3), "메일 수단이 있는가 (3 은 없음 -- 딱 그것만 묻는다)"),
    ("기관:codify", ["python3", "codify/run.py", "--원문", "x"],
     (3,), "codify 가 도는가 (--원문 만 주고 모델 없음 -- 끝값 3)"),
    ("기관:secaudit", ["python3", "secaudit/run.py", "--json"],
     (0, 1, 3), "보안 자가점검이 도는가 (0 높음없음 · 1 높음 · 3 전부 못잼)"),
    ("기관:repair", ["python3", "repair/run.py", "--명령", "true", "--증상", "배선"],
     (0, 3), "고치기 루프가 도는가 (0 이미 해결 · 3 판 못 깜 -- 모델 호출 0회)"),
    ("기관:research", ["python3", "research/run.py", "--목표", "x", "--분해만"],
     (0,), "연구가 목표를 추상 질의로 푸는가 (분해만 -- 수집·쓰기 없음, 모델 없으면 기계 일반화)"),
    ("기관:plan", ["python3", "plan/store.py", "--상태"],
     (0,), "계획판 상태를 읽는가 (켜짐/꺼짐 -- 쓰기 없음)"),
    ("기관:delegate", ["python3", "delegate/run.py", "--범위", "graph/*.py", "--쪼개기만"],
     (0,), "위임의 쪼개기가 도는가 (호출 0회)"),
]

# 고정 명령: 이것을 치면 에이전트로 안 떨어지고 봇이 받아야 한다.
고정명령들 = ("!소설", "!실험", "!감사", "!기억", "!평가", "!경로", "!목표", "!진화", "!중계", "!위임", "!수집", "!열쇠", "!고치기", "!점검", "!코드화", "!연구", "!계획")

원장들 = ("graph/ledger.jsonl", "graph/edges.jsonl", "eval/ledger.jsonl",
        "router/ledger.jsonl", "intent/ledger.jsonl")

한바퀴 = r"""
set -u
printf '%s\n' '---' "topic: '배선 카나리'" '---' '' \
  '배선점검 카나리입니다. 촉매카나리 수율 77% 라고 적어 둔다.' \
  > public_agent_memory/20260911-000000_배선_카나리.md
echo "== 간추리기 =="
python3 graph/night.py | head -3
echo "원장카나리=$(grep -c 배선_카나리 graph/ledger.jsonl || echo 0)"
echo "== 판정 =="
python3 graph/link.py --출처 public_agent_memory/20260911-000000_배선_카나리.md | head -5
echo "간선카나리=$(grep -c 배선_카나리 graph/edges.jsonl || echo 0)"
echo "== 조회 =="
python3 graph/ask.py --말 촉매카나리 | head -3
echo "== 요지문 =="
python3 graph/digest.py
echo "요지노드=$(grep -o '노드 [0-9]*개' graph/digest.md | head -1)"
echo "== 목표: 승인 없이 안 집히는가 =="
ID=$(python3 intent/store.py --제안 '배선 카나리 목표' --판정 'test -f 카나리증거.txt' \
     | grep -o '\[[0-9a-f-]*\]' | tr -d '[]')
echo "제안id=$ID"
python3 intent/store.py --다음 > /dev/null 2>&1 && echo "승인전집힘=그렇다(문제)" || echo "승인전집힘=아니다(옳다)"
python3 intent/store.py --승인 "$ID" | head -1
python3 intent/store.py --다음 | head -2
echo "== 끝은 명령이 정한다 =="
python3 intent/store.py --끝 "$ID" > /dev/null 2>&1 && echo "증거없이끝남=그렇다(문제)" || echo "증거없이끝남=아니다(옳다)"
echo 있다 > 카나리증거.txt
python3 intent/store.py --끝 "$ID" | head -1
echo "== 요지문에 승인 목표가 얹히는가 =="
python3 intent/store.py --제안 '승인된 카나리 목표' | grep -o '\[[0-9a-f-]*\]' | tr -d '[]' > /tmp/id2
python3 intent/store.py --승인 "$(cat /tmp/id2)" > /dev/null
python3 graph/digest.py > /dev/null
echo "요지승인목표=$(grep -c '승인된 카나리 목표' graph/digest.md || echo 0)"
"""


def 가르기(끝값: int, 기대: tuple, 꼬리: str = "") -> str:
    """'안 잰 것' 을 '끊긴 것' 으로 뭉개지 않는다.

    실측(이 파일을 처음 돌린 자리): 이 컨테이너에는 langchain 이 없어 bot_tools 임포트가
    exit 1 을 낸다 -- VM 에는 깔려 있으므로 그것은 **배선이 끊긴 것이 아니라 여기서 못 잰
    것**이다. 이 저장소는 이미 그 갈래를 알고 있다(scripts/tests.sh 의 '건너뜀',
    eval/run.py 의 못돌림표지). 판정표를 두 벌 두지 않고 그것을 그대로 쓴다."""
    if 끝값 in 기대:
        return "이어짐"
    from eval.run import 못돌림표지
    if 끝값 == 3 or any(m in (꼬리 or "") for m in 못돌림표지):
        return "못돌림"
    return "끊김"


def 읽기(repo=None) -> "list[dict]":
    repo = Path(repo or REPO)
    out = []
    for 이름, argv, 기대, 무엇 in 읽기점검:
        try:
            p = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True,
                               errors="replace", timeout=300)
            끝값, 꼬리 = p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
        except subprocess.TimeoutExpired:
            끝값, 꼬리 = 124, "시간 초과"
        except OSError as e:
            끝값, 꼬리 = 127, f"{type(e).__name__}"
        out.append({"이름": 이름, "판정": 가르기(끝값, 기대, 꼬리), "끝값": 끝값, "무엇": 무엇,
                    "꼬리": "" if 끝값 in 기대 else "\n".join(꼬리.splitlines()[-3:])})
    return out


def 명령점검(repo=None) -> dict:
    """고정 명령이 전부 들리는가 + 자연어는 에이전트로 떨어지는가."""
    try:
        import dispatch
    except Exception as e:
        return {"판정": "끊김", "말": f"dispatch 를 못 들인다: {type(e).__name__}: {e}"}
    안들림 = [c for c in 고정명령들 if dispatch.run(c, None, True) is None]
    샌말 = [m for m in ("오늘 날씨 어때", "소설 한 편 써줘", "!기억력이 나빠졌어")
           if dispatch.run(m, None, True) is not None]
    if 안들림 or 샌말:
        return {"판정": "끊김",
                "말": (f"안 들리는 고정 명령 {안들림}" if 안들림 else "")
                      + (f" / 에이전트로 가야 하는데 삼킨 말 {샌말}" if 샌말 else "")}
    return {"판정": "이어짐",
            "말": f"고정 명령 {len(고정명령들)}갈래가 다 들리고, 자연어 3개는 에이전트로 떨어진다"}


def 원장점검(repo=None) -> "list[dict]":
    repo = Path(repo or REPO)
    out = []
    for rel in 원장들:
        p = repo / rel
        if not p.is_file():
            out.append({"이름": rel, "판정": "못돌림", "말": "아직 없다 -- 한 번도 안 돌았다"})
            continue
        줄 = sum(1 for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
        깨진 = 0
        for x in p.read_text(encoding="utf-8").splitlines():
            if x.strip():
                try:
                    json.loads(x)
                except ValueError:
                    깨진 += 1
        out.append({"이름": rel, "판정": "끊김" if 깨진 else ("이어짐" if 줄 else "못돌림"),
                    "말": f"{줄}줄" + (f" · **깨진 줄 {깨진}개**" if 깨진 else "")})
    return out


def 한바퀴돌기(repo=None) -> dict:
    """격리 판에서 쓰기 흐름까지. 저장소를 안 더럽힌다."""
    from sandbox import run as 격리
    r = 격리.실행(["bash", "-lc", 한바퀴], repo=repo, 초=600, 메모리MB=4096)
    if not r["돌았나"]:
        return {"판정": "못돌림", "말": r["메모"] or r["stderr"][:200], "출력": ""}
    출력 = (r["stdout"] or "") + (r["stderr"] or "")
    # 흐름이 실제로 이어졌는지를 **출력의 표지로** 판정한다. 말이 아니라 수다.
    표지 = {
        "색인에 새 노드": "원장카나리=1" in 출력,
        "간선 판정 적힘": any(f"간선카나리={n}" in 출력 for n in ("4", "3", "2", "1")),
        "깃발로 되찾힘": "배선_카나리" in 출력.split("== 조회 ==")[-1].split("== 요지문")[0],
        "요지문 다시 지어짐": "요지노드=" in 출력 and "노드" in 출력,
        "승인 전에는 안 집힌다": "승인전집힘=아니다(옳다)" in 출력,
        "증거 없이는 안 끝난다": "증거없이끝남=아니다(옳다)" in 출력,
        "증거 생기면 끝난다": "끝남:" in 출력,
        "승인 목표가 요지문에": "요지승인목표=1" in 출력,
    }
    끊김 = [k for k, v in 표지.items() if not v]
    return {"판정": "끊김" if 끊김 else "이어짐", "표지": 표지, "끊김": 끊김,
            "말": f"{len(표지) - len(끊김)}/{len(표지)} 이어짐" + (f" · 끊김 {끊김}" if 끊김 else ""),
            "출력": 출력}


def main() -> int:
    ap = argparse.ArgumentParser(description="배선 점검 -- 끝에서 끝까지 이어져 있는가")
    ap.add_argument("--읽기만", action="store_true")
    ap.add_argument("--출력", action="store_true", help="한 바퀴의 원문 출력까지 찍는다")
    args = ap.parse_args()

    끊김, 못 = 0, 0
    print("== 읽기 점검 (진짜 저장소, 아무것도 안 고친다) ==")
    for r in 읽기():
        표 = {"이어짐": "OK  ", "못돌림": "못돌림", "끊김": "끊김"}[r["판정"]]
        print(f"  {표} {r['이름']:<18} 끝값 {r['끝값']:<4} {r['무엇']}")
        if r["꼬리"]:
            print("\n".join(f"       {x}" for x in r["꼬리"].splitlines()))
        끊김 += r["판정"] == "끊김"
        못 += r["판정"] == "못돌림"

    print("\n== 명령의 길 ==")
    c = 명령점검()
    print(f"  {'OK  ' if c['판정'] == '이어짐' else '끊김'} {c['말']}")
    끊김 += c["판정"] == "끊김"

    print("\n== 원장 ==")
    for r in 원장점검():
        표 = {"이어짐": "OK  ", "못돌림": "못돌림", "끊김": "끊김"}[r["판정"]]
        print(f"  {표} {r['이름']:<24} {r['말']}")
        끊김 += r["판정"] == "끊김"
        못 += r["판정"] == "못돌림"

    if not args.읽기만:
        print("\n== 한 바퀴 (격리 판 -- 저장소는 안 더럽힌다) ==")
        w = 한바퀴돌기()
        if w["판정"] == "못돌림":
            print(f"  못돌림 {w['말']}")
            못 += 1
        else:
            for k, v in w["표지"].items():
                print(f"  {'OK  ' if v else '끊김'} {k}")
            끊김 += len(w.get("끊김", []))
        if args.출력 and w.get("출력"):
            print("\n--- 한 바퀴 원문 ---")
            print(w["출력"])

    print(f"\n끊김 {끊김}개 · 못돌림 {못}개")
    if 못 and not 끊김:
        print("(못돌림은 초록이 아니다 -- 재료·키가 없어 **안 잰 것**이다)")
    if 끊김:
        return 1
    return 3 if 못 else 0


if __name__ == "__main__":
    raise SystemExit(main())
