"""eval/run -- 흩어진 면역계를 한 러너로 묶고, 후퇴를 원장으로 잰다.

이 저장소의 면역계는 이미 여럿이다: gatekeeper(커밋 게이트) · scripts/tests.sh(검사
전부) · capability_ratchet(능력 래칫) · lol/score.py(기준선 심판) · 그리고 새로 지은
eval/answers.py(답 회귀). 흩어져 있으면 어느 것이 언제 빨간불이 됐는지 아무도 모른다
-- 낡은 메모가 "mathdrift 가 빨갛다" 고 가리키는 동안 진짜 빨간 것은 law_hwp 였다
(CLAUDE.md 실측 2026-09-09). 그래서 **결과를 원장(eval/ledger.jsonl)에 쌓고, 직전과
견줘 초록→빨강을 '후퇴' 라고 크게 말한다.**

판정 규칙 (이 저장소의 끝값 관례 그대로):

    끝값 0  초록
    끝값 3  못돌림 -- 재료·키·의존성이 없어 **안 잰 것**이다. 초록이 아니다
            (검사하지 않은 초록불이 검사한 빨간불보다 나쁘다). 그 밖에
            ModuleNotFoundError 등도 못돌림으로 가른다
    그 외   빨강 -- 꼬리(로그 끝)를 원장에 같이 적는다. 기억으로 적지 않는다

무게: 빠름(기본으로 돈다) · 느림(--전부 라야 돈다 -- 검사 전부는 6분이 넘고, 그것을
매번 기다리면 CI 를 기다리던 것과 똑같아진다).

쓰기:
    python3 eval/run.py                # 빠른 갈래만 (게이트 · 답 · lol기준선)
    python3 eval/run.py --전부         # 느린 갈래까지 (검사전부 · 래칫)
    python3 eval/run.py --갈래 게이트,답
    python3 eval/run.py --보고만       # 갈래 목록 + 원장의 마지막 판정만
끝값: 0 빨강 없음 · 1 빨강 있음(--엄격 이면 못돌림도) · 3 갈래를 못 골랐다
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
원장상대 = "eval/ledger.jsonl"

못돌림표지 = ("ModuleNotFoundError", "No module named", "GEMINI_API_KEY",
            "원장이 비어 있다")

# 갈래 등록부. 여기 없는 것은 안 돈다 -- 닫혀 있어야 "다 돌았다" 가 뜻을 가진다.
갈래들 = [
    {"이름": "게이트", "명령": ["python3", "gatekeeper.py"], "초": 300, "무게": "빠름"},
    {"이름": "답", "명령": ["python3", "eval/answers.py"], "초": 180, "무게": "빠름"},
    {"이름": "lol기준선", "명령": ["python3", "lol/score.py"], "초": 300, "무게": "빠름"},
    {"이름": "경로", "명령": ["python3", "router/check.py"], "초": 60, "무게": "빠름"},
    # 배선 점검은 격리 판을 깔고 한 바퀴를 돌리므로 느림이다. 빠른 쪽만 보려면
    # `python3 eval/wire.py --읽기만` 을 손으로 돌린다.
    {"이름": "배선", "명령": ["python3", "eval/wire.py"], "초": 900, "무게": "느림"},
    {"이름": "검사전부", "명령": ["bash", "scripts/tests.sh"], "초": 1500, "무게": "느림"},
    {"이름": "래칫", "명령": ["python3", "scripts/capability_ratchet.py"],
     "초": 900, "무게": "느림"},
    # 절대 기준 과제 -- 모델을 과제 수 x 2 번 부른다(참고 없음·있음). 키가 없으면 3.
    {"이름": "과제", "명령": ["python3", "eval/tasks.py", "--참고", "둘다"],
     "초": 1500, "무게": "느림"},
]


def _원장(repo=None) -> Path:
    return Path(repo or REPO) / 원장상대


def 원장읽기(repo=None) -> "list[dict]":
    path = _원장(repo)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def 마지막판정(repo=None) -> "dict[str, dict]":
    out: dict = {}
    for r in 원장읽기(repo):
        if r.get("갈래"):
            out[r["갈래"]] = r
    return out


def _가르기(끝값: int, 꼬리: str) -> str:
    if 끝값 == 0:
        return "초록"
    if 끝값 == 3 or any(m in 꼬리 for m in 못돌림표지):
        return "못돌림"
    return "빨강"


def 한갈래(갈래: dict, repo=None) -> dict:
    """한 갈래를 돌리고 결과 줄을 만든다 (원장에는 아직 안 적는다)."""
    repo = Path(repo or REPO)
    시작 = time.monotonic()
    try:
        p = subprocess.run(갈래["명령"], cwd=str(repo), capture_output=True,
                           text=True, errors="replace", timeout=갈래.get("초", 600))
        끝값 = p.returncode
        꼬리 = ((p.stdout or "") + (p.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        끝값, 꼬리 = 124, f"{갈래.get('초')}초 안에 안 끝났다"
    except OSError as e:
        끝값, 꼬리 = 127, f"못 돌렸다: {type(e).__name__}: {e}"
    판정 = _가르기(끝값, 꼬리)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()
    return {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "갈래": 갈래["이름"], "판정": 판정, "끝값": 끝값,
            "걸린초": round(time.monotonic() - 시작, 1), "HEAD": head,
            # 빨간불은 로그를 보고 적는다 -- 기억으로 적지 않는다(CLAUDE.md).
            "꼬리": "" if 판정 == "초록" else "\n".join(꼬리.splitlines()[-8:])[-800:]}


def 돌리기(이름들: "list[str]", repo=None, 적기: bool = True) -> "list[dict]":
    """갈래들을 돌리고 원장에 적고, 직전 판정과 견줘 흐름(후퇴/회복/여전)을 단다."""
    repo = Path(repo or REPO)
    직전 = 마지막판정(repo)
    결과 = []
    for 갈래 in 갈래들:
        if 갈래["이름"] not in 이름들:
            continue
        r = 한갈래(갈래, repo)
        앞 = 직전.get(r["갈래"], {}).get("판정")
        if 앞 == "초록" and r["판정"] != "초록":
            r["흐름"] = "후퇴"          # 되던 것이 안 된다 -- 제일 큰 소식이다
        elif 앞 and 앞 != "초록" and r["판정"] == "초록":
            r["흐름"] = "회복"
        elif 앞 == r["판정"] and r["판정"] != "초록":
            r["흐름"] = "여전"
        결과.append(r)
    if 적기 and 결과:
        path = _원장(repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for r in 결과:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return 결과


def 보고(결과: "list[dict]") -> str:
    lines = []
    for r in 결과:
        표 = {"초록": "OK  ", "빨강": "빨강", "못돌림": "못돌림"}[r["판정"]]
        흐름 = f"  ** {r['흐름']} **" if r.get("흐름") in ("후퇴", "회복") else ""
        lines.append(f"  {표} {r['갈래']:<8} {r['걸린초']}초{흐름}")
        if r["꼬리"]:
            lines += [f"       {x}" for x in r["꼬리"].splitlines()[-4:]]
    빨강 = sum(1 for r in 결과 if r["판정"] == "빨강")
    못 = sum(1 for r in 결과 if r["판정"] == "못돌림")
    후퇴 = sum(1 for r in 결과 if r.get("흐름") == "후퇴")
    lines.append(f"  갈래 {len(결과)}개 · 빨강 {빨강} · 못돌림 {못}"
                 + (f" · **후퇴 {후퇴}**" if 후퇴 else ""))
    if 못:
        lines.append("  (못돌림은 초록이 아니다 -- 안 잰 것이다. 재료·키가 생기면 다시 재라)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="면역계를 한 러너로 돌리고 후퇴를 잰다")
    ap.add_argument("--전부", action="store_true", help="느린 갈래(검사전부·래칫)까지")
    ap.add_argument("--갈래", default="", help="쉼표로 고른 갈래만")
    ap.add_argument("--보고만", action="store_true", help="돌리지 않고 마지막 판정만")
    ap.add_argument("--엄격", action="store_true", help="못돌림도 빨간불로 친다")
    args = ap.parse_args()

    if args.보고만:
        마지막 = 마지막판정()
        for 갈래 in 갈래들:
            r = 마지막.get(갈래["이름"])
            print(f"  {갈래['이름']:<8} [{갈래['무게']}] "
                  + (f"마지막 {r['판정']} ({r['때'][:10]})" if r else "잰 적 없음"))
        return 0

    if args.갈래:
        이름들 = [x.strip() for x in args.갈래.split(",") if x.strip()]
        모르는 = [x for x in 이름들 if x not in {g["이름"] for g in 갈래들}]
        if 모르는:
            print(f"모르는 갈래: {모르는} -- 있는 것: {[g['이름'] for g in 갈래들]}")
            return 3
    else:
        이름들 = [g["이름"] for g in 갈래들 if args.전부 or g["무게"] == "빠름"]

    결과 = 돌리기(이름들)
    print(보고(결과))
    빨강 = any(r["판정"] == "빨강" for r in 결과)
    못 = any(r["판정"] == "못돌림" for r in 결과)
    return 1 if (빨강 or (args.엄격 and 못)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
