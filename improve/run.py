"""improve -- `!자가개선`. 시스템을 개선할 자리를 **스스로 찾아** 제안하고, **격리 판에서 시뮬레이션**해
성능이 나아진 것을 **코드가 확인한 뒤**, 사람의 동의를 받아 붙인다.

사용자(2026-09-11): "시스템을 개선할 방법을 스스로 탐색해서 제안한 뒤에 샌드박스 공간에서
시뮬레이션하고 성능 평가가 이루어졌다고 판단되면 사용자의 동의를 구하고 자가 개선한다."

이 저장소의 규율대로 **판정은 모델이 아니라 코드가 한다.** 모델은 딱 한 자리 -- 패치를 짓는 자리 --
에만 있고, 그 패치가 '개선' 인지는 아래 셋이 증언한다.

  ① 틈(개선할 자리)마다 **판정 명령**이 있다 -- 지금 실제 트리에서 그 명령이 빨강이어야 틈이다
     (초록이면 틈이 아니다: '이미초록' 으로 넘어간다)
  ② 패치는 **그림자 계획판(plan)** 에만 닿는다. 거기서 판정 명령이 **초록으로 뒤집혀야** 한다
     (red -> green. self_challenge 가 게이트를 승격시킬 때 쓰는 그 증명이다)
  ③ **리허설**이 초록이어야 한다 -- 문법·게이트·바뀐 파일의 검사에 더해 **레포 전체**(171개)를
     격리 판에서 돌려 HEAD 바탕과 견준다. **멀리서 새로 깨진 것이 하나라도 있으면 개선이 아니다**
     (사용자: "코드 하나 바뀌면 전체가 영향을 받을 수도 있잖아"). `--좁게` 로 끌 수 있고, `--자` 는
     eval/run 후퇴까지 본다.

`!개선 <말>` 은 틈이 아니라 **사람이 말한 개선**이다 -- red->green 이 없으므로 판정은
**레포 전체에 회귀가 없는 것**이다(사용자개선).

셋 다 통과하면 **붙이지 않고 멈춘다** -- 동의 대기. 사람이 `!자가개선 승인` 을 치면 plan.승인
(리허설 초록 + 같은 diff 일 때만 붙는 그 문)을 지나 실제 트리에 오르고 git_sync 가 커밋한다.
봇은 이 승인을 대신 칠 수 없다(dispatch.도구로쳐도되나 가 막는다).

틈은 어디서 오나(전부 코드가 이미 남긴 것):
  · main CI 의 실패 검사(ci_watch)                     -> 판정: python3 tests/<그 검사>
  · 수리 loop 가 못 푼 증상(repair 원장, 재현 명령 있는 것) -> 판정: 그 재현 명령
  · 봇이 임포트하는 핵심 모듈 중 검사가 없는 것(audit)   -> 판정: python3 tests/test_<모듈>.py (새로 짓는다)
  · 배선 읽기점검이 끊긴 기관(eval/wire, `--배선` 일 때)   -> 판정: 그 점검 명령
  · **진입점 위험**(entrypoints: 늦은 임포트를 밟으면 죽는 갈래) -> 판정: `entrypoints.py --위험만`
    -- 목록이 아니라 ast 로 세어 찾으므로 **새 모듈이 생겨도 저절로 덮인다**

**틈이 없으면 멈추지 않는다** -- 제2의 뇌가 모은 최신 것에서 이 저장소에 적용할 만한 것 하나를 골라
그것을 부탁으로 삼아 같은 길(그림자 -> 레포 전체 시뮬 -> 동의)을 간다(성능개선).

한 번에 **후보 하나만** 동의 대기로 남긴다(계획판이 하나뿐이다). 무한 loop 금지 -- 후보 3(최대 5).
못 한 것은 원장과 메모에 그대로 남는다.

    python3 improve/run.py               # 탐색 -> 제안 -> 시뮬 -> (동의 대기)   끝값 0 후보 있음 · 3 못돌림
    python3 improve/run.py --틈만        # 틈만 센다(모델·sandbox 안 씀)
    python3 improve/run.py --승인        # 동의(사람) -> 실제 트리에 붙인다
    python3 improve/run.py --버림 · --상태
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# **스크립트로 돌 때 sys.path[0] 은 이 파일의 디렉터리(improve/)다 -- 뿌리가 아니다.**
# 실측 2026-09-11(VM): `python3 improve/run.py --부탁 ...` 가
# `ModuleNotFoundError: No module named 'plan'` 로 죽었다. `--틈만` 은 plan 을 안 써서
# 배선 읽기점검이 초록이었다 -- 얕은 점검이 깊은 길을 못 봤다. 뿌리를 먼저 넣는다.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
원장상대 = "improve/ledger.jsonl"
메모곳 = "public_agent_memory"
기본후보 = 3
최대후보 = 5

제안기 = None      # 검사 주입: (prompt) -> str(JSON). None 이면 router 수리기
틈모으기_ = None   # 검사 주입: (repo) -> list[dict]. None 이면 진짜 틈모으기
자기 = None        # 검사 주입: (repo, 판) -> dict {"돌았나","후퇴","말"}. None 이면 eval/run 을 판에서

def 핵심모듈들(repo=None) -> "list[str]":
    """**봇이 실제로 임포트하는 것**을 세어 찾는다 -- 손으로 적은 목록이 아니다.

    사용자(2026-09-11): "가능한 모든 것을 일반해로 바꿔." 전에는 파일 이름 16개를 여기 적어 뒀다.
    그러면 새 모듈이 봇에 붙어도 누가 여기 또 적어야 한다. 그래서 impact 의 임포트 그래프로
    `discord_bot_server` 가 (전이적으로) 끌어오는 저장소 모듈을 세고, 그 가운데 뿌리의 .py 만 고른다."""
    repo = Path(repo or REPO)
    try:
        import impact
        앞, _뒤 = impact.임포트그래프(repo)
    except Exception:                                  # noqa: BLE001
        return []
    본, 층 = {"discord_bot_server"}, ["discord_bot_server"]
    for _ in range(4):                                 # 전이적으로 -- 너무 멀리는 안 간다
        다음 = []
        for m in 층:
            for x in 앞.get(m, ()):
                if x not in 본:
                    본.add(x)
                    다음.append(x)
        if not 다음:
            break
        층 = 다음
    out = []
    for m in sorted(본):
        rel = m.replace(".", "/") + ".py"
        if "/" not in rel and (repo / rel).is_file():   # 뿌리의 모듈만 -- 꾸러미는 제 검사가 따로 있다
            out.append(rel)
    return out


# ---------------------------------------------------------------- 원장 · 도움
def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **줄}, ensure_ascii=False) + "\n")


def 원장읽기(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 원장상대
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", s or "x")[:40].strip("_") or "x"


# ---------------------------------------------------------------- ① 틈: 개선할 자리를 코드가 찾는다
def 틈모으기(repo=None, 배선: bool = False, 점검: bool = False) -> "list[dict]":
    """{"종류","무엇","판정명령","왜"} 목록. 값이 큰 것부터: CI 실패 > 못 푼 수리 > 검사 없는 핵심 모듈 > 끊긴 배선."""
    repo = Path(repo or REPO)
    out: list[dict] = []
    본: set[str] = set()

    def 더하기(종류, 무엇, 명령, 왜):
        if 명령 and 명령 not in 본:
            본.add(명령)
            out.append({"종류": 종류, "무엇": 무엇, "판정명령": 명령, "왜": 왜})

    # 1. main CI 의 실패 검사
    try:
        import ci_watch
        c = ci_watch.캐시보기(repo)
        if c["상태"] != "빨강" or not c["실패"]:
            c = ci_watch.보기(repo)
        if c["상태"] == "빨강":
            for t in c["실패"]:
                더하기("CI실패검사", t, f"python3 tests/{t}", "main CI 가 빨강이다 -- 이 검사부터")
    except Exception:                                  # noqa: BLE001 -- 망이 없으면 이 출처만 비운다
        pass

    # 2. 수리 loop 가 못 푼 증상(재현 명령이 남아 있는 것)
    try:
        from repair import run as R
        명령표: dict[str, str] = {}
        for r in R.원장읽기(repo):
            if r.get("꼴") == "시작" and r.get("증상") and r.get("명령"):
                명령표[r["증상"]] = r["명령"]
        for 증상 in R.미해결증상들(repo):
            if 증상 in 명령표:
                더하기("미해결수리", 증상, 명령표[증상], "repair 가 3바퀴에 못 풀었다")
    except Exception:                                  # noqa: BLE001
        pass

    # 3. 검사 없는 핵심 모듈
    try:
        from audit import run as A
        있는 = 핵심모듈들(repo)
        _, 안덮임 = A.검사찾기(repo, 있는)
        for rel in 안덮임:
            stem = Path(rel).stem
            더하기("검사없음", rel, f"python3 tests/test_{stem}.py", "봇이 임포트하는 모듈인데 붙드는 검사가 없다")
    except Exception:                                  # noqa: BLE001
        pass

    # 4. 진입점 위험 -- 늦은 임포트를 밟으면 죽는 갈래(코드가 세어 찾는다, 목록 없음)
    try:
        import entrypoints
        for e in entrypoints.위험들(repo):
            더하기("진입점위험", e["파일"], "python3 entrypoints.py --위험만", e["왜"][:140])
    except Exception:                                  # noqa: BLE001
        pass

    # 5. 점검(인수 검사) 에서 실패한 장면 -- 사용자: "점검을 통해 부족한 점도 찾는다". 느리다(2~3분) -- 부를 때만
    if 점검:
        try:
            from sandbox import run as SB
            z = SB.실행(["python3", "eval/acceptance.py", "--json"], repo=repo, 지금트리=True, 초=900, 메모리MB=4096)
            if z["돌았나"] and (z["stdout"] or "").strip():
                j = json.loads(z["stdout"][z["stdout"].index("{"):])
                for x in j.get("결과", []):
                    if x.get("판정") != "통과":
                        더하기("점검실패", x.get("장면", "")[:60], "python3 eval/acceptance.py", f"인수 검사 장면이 빨강: {x.get('말', '')[:120]}")
        except Exception:                              # noqa: BLE001
            pass

    # 6. 끊긴 배선(느리다 -- 부를 때만)
    if 배선:
        try:
            from eval import wire
            for row in wire.읽기(repo):
                if row["판정"] == "끊김":
                    argv = next((a for 이름, a, _, _ in wire.읽기점검 if 이름 == row["이름"]), None)
                    if argv:
                        더하기("배선끊김", row["이름"], " ".join(argv), "배선 읽기점검이 끊겼다")
        except Exception:                              # noqa: BLE001
            pass
    return out


# ---------------------------------------------------------------- 근거: 제2의 뇌에서 (모자라면 스스로 넓힌다)
최소근거 = 2
확장바퀴 = 2
넓히기_ = None     # 검사 주입: (질의들, repo) -> dict(harvest.한바퀴 의 꼴). None 이면 진짜 harvest
느린모델초 = 15.0  # 분해 한 번이 이보다 오래 걸리면 풀이 죽은 것이다 -- 이 실행 안에선 모델을 다시 안 부른다
모델막힘 = False   # 위 판정의 결과(실행 단위). 검사가 초기화한다


def 근거모으기(틈: dict, repo=None) -> dict:
    """{"참고": [{"출처","해시","요약"}], "확장": n, "질의": [...]}.

    사용자(2026-09-11): "자가 개선 아이디어는 제2의 뇌를 적용한다 · 논문과 알고리즘을 근거로 스스로를
    업데이트한다 · 탐색 범위가 부족하면 스스로 판단해서 확장한다." 그래서 (1) graph 에서 찾고,
    (2) 최소근거 에 못 미치면 research.분해 로 틈을 **일반 방법론 질의**로 풀어 harvest 로 넓게 모은 뒤
    다시 찾는다 -- 확장바퀴 까지. 확장 여부와 횟수는 원장·메모에 남는다."""
    from graph import ask
    repo = Path(repo or REPO)
    질의 = f"{틈['무엇']} {틈['왜']} {틈['종류']}"
    r = {"참고": [], "확장": 0, "질의": [질의]}

    def 찾기():
        return [{"출처": n.get("출처", ""), "해시": n.get("해시", ""), "요약": (n.get("요약") or "")[:240]}
                for _, n in ask.찾기(질의, repo=repo, 최대=5)]

    r["참고"] = 찾기()
    for _ in range(확장바퀴):
        if len(r["참고"]) >= 최소근거:
            break
        try:
            from research import run as Rs
            global 모델막힘
            t0 = time.monotonic()
            질의들 = Rs.분해(질의, f"제2의 뇌에 참고가 {len(r['참고'])}개뿐이다 -- 더 일반적인 방법론으로", 모델=not 모델막힘)
            if not 모델막힘 and time.monotonic() - t0 > 느린모델초:
                모델막힘 = True                        # 20초짜리 기다림을 후보마다 되풀이하지 않는다(정직히 기계 일반화로)
                r["모델막힘"] = True
            if 넓히기_ is not None:
                넓히기_(질의들, repo)
            else:
                from dig import harvest as H
                H.한바퀴(질의들, repo=repo, 몇=3, 상한=6, 출처=("arxiv", "github", "hf"))
            r["확장"] += 1
            r["질의"] += 질의들
            r["참고"] = 찾기()
        except Exception:                              # noqa: BLE001 -- 망이 없으면 넓히지 못한 채 간다(정직히 기록)
            break
    return r


# ---------------------------------------------------------------- 판정: 명령을 격리 판에서 돌린다
def 판정(명령: str, 판, 초: int = 120) -> "tuple[int, str]":
    """(끝값, 꼬리). 판을 못 깔면 끝값 3. 명령은 toolgate 를 먼저 지난다(게이트 삭제 같은 것은 안 돈다)."""
    import toolgate
    막힘 = toolgate.검사(명령)
    if 막힘:
        return 3, f"[도구 게이트 차단] {막힘}"
    from sandbox import run as SB
    r = SB.실행(["bash", "-lc", 명령], repo=Path(판), 지금트리=True, 초=초, 메모리MB=4096)
    if not r["돌았나"]:
        return 3, r.get("메모", "판을 못 깜")
    꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-8:]
    return int(r["끝값"]), "\n".join(꼬리)


# ---------------------------------------------------------------- ② 제안: 모델이 패치를 짓는다 (딱 여기만)
def _관련파일들(틈: dict, repo: Path) -> "list[str]":
    out = []
    m = re.search(r"tests/(test_[\w가-힣]+\.py)", 틈["판정명령"])
    if m:
        out.append(f"tests/{m.group(1)}")
        stem = m.group(1)[len("test_"):-3]
        for cand in (f"{stem}.py", f"{stem}/run.py", f"{stem}/store.py"):
            if (repo / cand).is_file():
                out.append(cand)
    if 틈["종류"] == "검사없음":
        out.insert(0, 틈["무엇"])
    return [x for x in out if (repo / x).is_file()][:3]


def 프롬프트(틈: dict, 꼬리: str, repo: Path, 근거: dict = None) -> str:
    발췌 = []
    근거줄 = ""
    if 근거 and 근거.get("참고"):
        근거줄 = "\n\n제2의 뇌가 모은 참고(이 가운데서 방법을 고르고, 답의 \"근거\" 에 출처를 그대로 적어라):\n" + "\n".join(
            f"- {x['출처']} #{x['해시']}: {x['요약']}" for x in 근거["참고"])
        if 근거.get("확장"):
            근거줄 += f"\n(참고가 모자라 {근거['확장']}바퀴 넓혀 모았다: {', '.join(근거['질의'][1:4])})"
    elif 근거 is not None:
        근거줄 = "\n\n제2의 뇌에 이 틈의 참고가 없다(넓혀 모아도) -- 그렇다면 \"근거\" 를 빈 목록으로 두고 그 사실을 \"왜\" 에 적어라."
    for rel in _관련파일들(틈, repo):
        try:
            줄들 = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()[:160]
            발췌.append(f"### {rel} (앞 {len(줄들)}줄)\n" + "\n".join(줄들))
        except OSError:
            continue
    return (
        "너는 이 저장소의 **자가 개선** 제안자다. 아래 틈 하나를 메우는 **최소 패치**를 JSON 으로만 답하라.\n\n"
        f"틈: [{틈['종류']}] {틈['무엇']}\n왜 틈인가: {틈['왜']}\n판정 명령(지금 빨강): {틈['판정명령']}\n"
        f"지금 그 명령의 끝자락:\n{꼬리 or '(출력 없음)'}\n\n"
        + ("\n\n".join(발췌) if 발췌 else "(관련 파일 발췌 없음)")
        + 근거줄
        + "\n\n규칙:\n"
        "- 답은 JSON 하나: {\"꼴\": \"패치\", \"왜\": \"한 줄\", \"근거\": [\"출처#해시\", ...], "
        "\"편집\": [{\"path\": \"상대경로\", \"old\": \"파일에 정확히 한 번 있는 글\", \"new\": \"바꿀 글\"}], "
        "\"새파일\": [{\"path\": \"상대경로\", \"내용\": \"전체\"}]}\n"
        "- old 는 파일의 글자 그대로(들여쓰기 포함), 정확히 한 번만 있어야 한다. 없거나 두 번이면 거절된다.\n"
        "- 검사(tests/*.py)를 통과시키려고 **검사를 지우거나 assert 를 빼지 마라** -- 그 자리는 거절된다.\n"
        "- gates/ · .env · 판정 원장(*.jsonl) 은 못 만진다. 검사가 없는 모듈이면 tests/test_<모듈>.py 를 새파일로 지어라.\n"
        "- 못 고치겠으면 {\"꼴\": \"사람\", \"사람이_할_것\": \"...\"} 로 답하라.\n"
    )


def _제안기본(prompt: str) -> str:
    from router import call as R
    return R.부르기("수리기", prompt)["답"]


def _JSON뽑기(답: str) -> "dict | None":
    """펜스(```json)·앞뒤 말·뒤에 붙은 다른 중괄호가 있어도 **첫 번째로 온전한 사전**을 뽑는다.
    탐욕 정규식(여는 중괄호부터 마지막 닫는 중괄호까지)은 답 끝의 아무 중괄호까지 삼켜서 json 이
    안 열렸다(실측 꼴)."""
    글 = re.sub(r"```(?:json)?", "", 답)
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", 글):
        try:
            d, _ = dec.raw_decode(글, m.start())
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("꼴"):
            return d
    return None


def 해석(답: str) -> "dict | None":
    """답에서 JSON 하나를 뽑아 이 자리의 꼴로 검사한다. repair.해석 은 repair 의 꼴("패치" 목록)을
    강제하므로 그대로 못 쓴다 -- 여기 꼴은 "편집"/"새파일" 이다(실측: 재사용했더니 전부 '제안없음')."""
    d = _JSON뽑기(답 or "")
    if not isinstance(d, dict) or d.get("꼴") not in ("패치", "사람"):
        return None
    if d["꼴"] == "사람":
        return d if str(d.get("사람이_할_것", "")).strip() else None
    편집 = d.get("편집") or []
    새 = d.get("새파일") or []
    if not isinstance(편집, list) or not isinstance(새, list) or not (편집 or 새):
        return None
    for e in 편집:
        if not (isinstance(e, dict) and e.get("path") and isinstance(e.get("old"), str) and isinstance(e.get("new"), str)):
            return None
    for f in 새:
        if not (isinstance(f, dict) and f.get("path") and isinstance(f.get("내용"), str)):
            return None
    return d


_검사훼손 = re.compile(r"^\s*(assert\b|raise SystemExit\(1\)|FAIL\.append)", re.M)


def _검사를_약화하나(제안: dict, 판: Path) -> "str | None":
    """검사 파일에서 assert 를 빼거나 실패 줄을 지우는 패치는 '개선' 이 아니라 '눈 가리기' 다."""
    for e in 제안.get("편집") or []:
        p = str(e.get("path", ""))
        if p.startswith("tests/") and len(_검사훼손.findall(e.get("old", ""))) > len(_검사훼손.findall(e.get("new", ""))):
            return f"{p}: assert/실패 줄을 빼는 편집 -- 검사를 약화시키는 패치는 거절한다"
    return None


def 적용(제안: dict, 판: Path) -> "tuple[bool, str]":
    """그림자 판에만 쓴다. toolgate 가 gates/·.env·원장을 막고, filetools 가 old 정확히-한-번을 강제한다."""
    import filetools
    import toolgate
    까닭 = _검사를_약화하나(제안, 판)
    if 까닭:
        return False, 까닭
    한것 = []
    try:
        for f in 제안.get("새파일") or []:
            p = toolgate.경로풀기(str(f["path"]), 쓰기=True, repo=판)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(f.get("내용", "")), encoding="utf-8")
            한것.append(f"+{f['path']}")
        for e in 제안.get("편집") or []:
            한것.append(filetools.편집(str(e["path"]), str(e["old"]), str(e["new"]), repo=판))
    except (ValueError, KeyError, TypeError, OSError) as e:
        return False, f"{type(e).__name__}: {str(e)[:160]}"
    if not 한것:
        return False, "패치에 편집도 새파일도 없다"
    return True, " · ".join(한것)[:300]


적용되풀이횟수 = 3
시뮬되풀이횟수 = 2      # 레포 전체 시뮬이 빨가면 꼬리를 들려 이만큼 더 청한다
공허검사기 = None       # 검사 주입: (repo, 판) -> dict{공허, 말, ...}. None 이면 rehearsal.공허검사
절제검사기 = None       # 검사 주입: (repo, 판) -> dict{성립, 말, ...}. None 이면 rehearsal.절제검사
열쇠검사기 = None       # 검사 주입: (repo, 판) -> dict{성립, 말, ...}. None 이면 rehearsal.열쇠대조
이름검사기 = None       # 검사 주입: (repo, 판) -> dict{성립, 말, ...}. None 이면 rehearsal.미정의이름
순환검사기 = None       # 검사 주입: (repo, 판) -> dict{성립, 말, ...}. None 이면 rehearsal.순환검사


def _초록의뜻(repo: Path, 시험보고: str) -> "str | None":
    """시뮬 뒤 **막힌 까닭** 한 덩어리, 없으면 None. 빨강이면 그 보고. 초록이어도 **공허**(코드는 바뀌었는데
    그 변경이 없어도 초록인 검사뿐)면 공허 검사의 말 -- 검사하지 않은 초록불은 빨강과 같이 다룬다.

    사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 오늘 초록으로 지나간 것 셋(#194 함수만
    정의한 검사 · #201 글자 검사 · 구글 문 셋)이 전부 여기서 걸린다. 모델이 '초록의 뜻' 을 판단할 필요가 없다 --
    코드가 잰다(rehearsal.공허검사)."""
    from plan import store as P
    st = P.읽기(repo) or {}
    시 = st.get("시험") or {}
    if not 시.get("통과"):
        return 시험보고
    import rehearsal
    판 = P.현재판(repo)
    공 = (공허검사기 or rehearsal.공허검사)(repo, 판)
    if 공.get("공허"):
        _적기(repo, {"꼴": "공허", "말": 공["말"][:240], "검사들": 공.get("검사들", [])[:6], "코드들": 공.get("코드들", [])[:6]})
        return "[공허 검사 -- 초록이지만 뜻이 없다] " + 공["말"]
    # **기능을 하나씩 빼 본다.** 공허검사는 패치 전체를 빼고 보므로, 함수 셋 중 하나만 검사에 걸려도 통과한다.
    # 사용자(2026-09-12): "기능의 존재를 주장하지 말고, 제거했을 때 검사가 무너지고 다시 넣었을 때 복구되는지."
    절 = (절제검사기 or rehearsal.절제검사)(repo, 판)
    if not 절.get("성립", True):
        _적기(repo, {"꼴": "절제", "말": 절["말"][:240], "안잡힌것": 절.get("안잡힌것", [])[:6],
                    "잰것": [x["이름"] for x in 절.get("잰것", [])][:8]})
        return "[절제 검사 -- 빼도 검사가 안 무너진다] " + 절["말"]
    # **읽는 열쇠가 그 원장에 있나.** 검사가 코드를 부르는지(위 둘)와 다른 축이다 -- 실측 2026-09-12: 지어낸 행
    # 한 줄로 초록을 받은 도구가 실제 원장에 없는 열쇠 다섯을 읽어 여섯 칸이 늘 0 이었다.
    열 = (열쇠검사기 or rehearsal.열쇠대조)(repo, 판)
    if not 열.get("성립", True):
        _적기(repo, {"꼴": "열쇠", "말": 열["말"][:240],
                    "죽은읽기": [f"{x['파일']}:{x['줄']} {x['열쇠']}" for x in 열.get("죽은읽기", [])][:6],
                    "있는열쇠": 열.get("있는열쇠", [])[:8]})
        return "[열쇠 대조 -- 원장에 없는 열쇠를 읽는다] " + 열["말"]
    # **없는 이름을 부르나.** 초록이어도 안 불린 함수 안에 NameError 가 숨는다 -- 실측 2026-09-12: git_sync 가
    # 밀기 성공 경로에서만 터졌고, 같은 결이 저장소에 다섯 군데 있었다.
    이 = (이름검사기 or rehearsal.미정의이름)(repo, 판)
    if not 이.get("성립", True):
        _적기(repo, {"꼴": "미정의", "말": 이["말"][:240],
                    "찾은것": [f"{x['파일']}:{x['줄']} {x['이름']}" for x in 이.get("찾은것", [])][:6]})
        return "[미정의 이름 -- 없는 이름을 부른다] " + 이["말"]
    # **제 부산물을 보고 초록이 되나.** 실측 2026-09-12 PR #214: 조사가 제 원장에 적은 `귀속` 을 제 검사가 읽어
    # '해결' 이 됐다 -- 고쳤다는 파일은 머지에 없었다.
    순 = (순환검사기 or rehearsal.순환검사)(repo, 판)
    if not 순.get("성립", True):
        _적기(repo, {"꼴": "순환", "말": 순["말"][:240],
                    "찾은것": [f"{x['검사']}:{x['줄']} {x['읽은것']}" for x in 순.get("찾은것", [])][:6]})
        return "[순환 -- 검사가 제 실행이 고친 원장을 읽는다] " + 순["말"]
    return None


def _못맞춘자리(판: Path, 편집: dict, 전체상한: int = 300) -> str:
    """old 가 안 맞은 파일의 **실제 글**을 돌려준다.

    비슷한 대목이 있으면 그 앞뒤 여섯 줄. **비슷한 대목조차 없으면**(모델이 없는 글을 지어냈다)
    파일 앞 300줄을 통째로 주고 '없는 자리를 고치지 말고 새파일로 지어라' 고 말한다 --
    실측 2026-09-12(VM): 새 기능(pdf 변환)을 부탁했는데 모델이 기존 파일의 없는 줄을 고치려 했다."""
    import difflib
    try:
        줄들 = (판 / str(편집.get("path", ""))).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return f"### {편집.get('path')} -- 파일이 없다. 편집이 아니라 **새파일** 로 지어라"
    old줄 = str(편집.get("old", "")).splitlines() or [""]
    n = max(1, len(old줄))
    최고 = (0.0, 0)
    for i in range(0, max(1, len(줄들) - n + 1)):
        r = difflib.SequenceMatcher(None, "\n".join(줄들[i:i + n]), "\n".join(old줄)).ratio()
        if r > 최고[0]:
            최고 = (r, i)
    본 = "\n".join(줄들)
    한줄도없다 = not any(x.strip() and x.strip() in 본 for x in old줄)
    # 짧은 글은 구조만 닮아도 비슷함이 높게 나온다(`def a():\n    return 0` 과 `def f():\n    return 2`).
    # 그래서 **old 의 어느 줄 하나도 파일에 없으면** 지어낸 글로 본다.
    if 최고[0] < 0.5 or 한줄도없다:
        return (f"### {편집.get('path')} -- 네 old 는 이 파일 어디에도 없다 (가장 비슷한 대목도 {최고[0]:.2f}). "
                f"**없는 자리를 고치지 마라.** 새 기능이면 편집 대신 새파일 로 지어라. 파일의 앞 {min(len(줄들), 전체상한)}줄:\n"
                + "\n".join(줄들[:전체상한]))
    a, b = max(0, 최고[1] - 6), min(len(줄들), 최고[1] + n + 6)
    return (f"### {편집.get('path')} 의 실제 글 {a + 1}~{b}줄 (네 old 와 비슷함 {최고[0]:.2f})\n"
            + "\n".join(줄들[a:b]))


def 적용되풀이(제안: dict, 원프롬프트: str, 판새로, 횟수: int = 적용되풀이횟수) -> "tuple[bool, str, dict, int]":
    """적용이 `old 가 파일에 없다` 로 막히면 **그 파일의 실제 글을 들려 다시 청한다.** (ok, 말, 제안, 시도수)

    실측 2026-09-12(VM): `!개선 md가 안보이니 …` 가 제2의 뇌 근거까지 들고 패치를 냈는데
    `ValueError: old 가 파일에 없다` 로 끝났다. 모델은 파일의 앞 200줄만 보고 old 를 짓는다 --
    한 글자만 달라도 정확히-한-번 규칙에 걸린다. 한 번 틀리면 끝나던 자리를 되풀이로 바꾼다.
    되풀이마다 판을 새로 깐다 -- 앞 시도가 편집 일부를 이미 적용했을 수 있어서다(그러면
    같은 old 가 두 번째엔 정말 없다).
    검사를 약화하는 패치(까닭이 있는 거절)는 되풀이하지 않는다 -- 글이 아니라 뜻이 틀린 것이다."""
    말 = ""
    자리 = ""
    for k in range(1, max(1, 횟수) + 1):
        판 = 판새로()
        if 판 is None:
            return False, "그림자를 못 꺼냈다", 제안, k
        ok, 말 = 적용(제안, 판)
        if ok:
            return True, 말, 제안, k
        if "old 가 파일에 없다" not in 말 and "두 번" not in 말 and "KeyError" not in 말 and "여러 번" not in 말:
            return False, 말, 제안, k                      # 뜻이 틀린 거절 -- 되풀이해도 같다
        if k == 횟수:
            break
        자리 = "\n\n".join(_못맞춘자리(판, e) for e in (제안.get("편집") or []))
        되묻기 = (원프롬프트 + f"\n\n[적용 실패 {k}/{횟수}] {말}\n"
                "old 는 **아래 실제 글에서 글자 그대로** 베껴라(공백·따옴표까지). 없는 글을 짓지 마라. "
                "없는 자리를 고쳐야 한다면 편집 대신 **새파일** 로 지어라. "
                "답은 **JSON 하나뿐**이다 -- 설명·펜스 없이 {\"꼴\": \"패치\", ...} 로.\n\n" + 자리)
        # **꼴이 아닌 답도 예산 안에서 다시 청한다.** 실측 2026-09-12(VM): 되물었더니 패치 꼴이 아닌
        # 답이 와서 한 번에 포기했다. 무엇이라 답했는지는 원장에 남긴다 -- 다음에 볼 수 있게.
        새 = None
        for 다시 in range(2):
            try:
                답 = (제안기 or _제안기본)(되묻기)
            except Exception as e:                         # noqa: BLE001
                return False, f"{말} · 되묻기 실패: {type(e).__name__}", 제안, k
            새 = 해석(답)
            _적기(_원장자리(판), {
                "꼴": "되묻기", "시도": k, "다시": 다시, "실패": 말[:120],
                "답머리": (답 or "").strip()[:300], "패치꼴": bool(새 and 새.get("꼴") == "패치")})
            if 새 and 새.get("꼴") == "패치":
                break
            if 새 and 새.get("꼴") == "사람":
                return False, f"{말} · 되물었더니 사람 몫이라 한다: {str(새.get('사람이_할_것', ''))[:160]}", 제안, k
            되묻기 = 되묻기 + "\n\n[답이 JSON 꼴이 아니었다] 설명 없이 JSON 하나만 다시."
        if not (새 and 새.get("꼴") == "패치"):
            return False, f"{말} · 되물었더니 두 번 다 패치 꼴이 아니었다", 제안, k
        제안 = 새
    return False, f"{횟수}번 청했는데 old 가 계속 안 맞는다 -- 마지막: {말}", 제안, 횟수


_원장repo = None   # 적용되풀이가 원장을 쓸 저장소 -- 사용자개선·한후보가 넣어 준다


def _원장자리(판: Path) -> Path:
    return _원장repo or REPO


# 사람만 가진 것. 모델이 '사람' 이라 물러날 때 그 이유에 이것이 없으면 회피다 -- 코드가 가른다.
_사람만꼴 = re.compile(r"열쇠|키\b|api[_ ]?key|토큰|token|승인|approve|계정|account|비밀번호|password|권한|결제|카드|로그인", re.I)


def 사람몫인가(말: str) -> bool:
    """'사람이_할_것' 이 정말 사람만 할 수 있는 일인가. 프롬프트로 설득하지 않고 코드가 판정한다.

    실측 2026-09-12(VM): pdf 변환 부탁에 모델이 "무거운 라이브러리·정책이 걱정" 을 이유로 '사람'
    이라며 물러났다. 열쇠도 승인도 아니다 -- 그건 사람 몫이 아니라 회피다. 사용자: "프롬프트
    의존도를 최소화해야 한다." 그래서 규칙을 프롬프트에 더 적는 대신 여기서 가른다."""
    return bool(_사람만꼴.search(말 or ""))


# ---------------------------------------------------------------- 사용자가 말한 개선 (!개선 <말>)
def 저장소파이썬(repo: Path) -> "list[str]":
    """이 저장소의 파이썬 파일. **git 이 추적하는 것만** -- 목록을 손으로 적지 않는다.

    실측 2026-09-12(VM): `!개선 수집망 url에 인스타그램, x, meta 추가해줘` 가 고른 파일이
    `.venv-torch/lib/python3.12/site-packages/torch/_meta_registrations.py` 였다. 건너뛸 곳을
    `("venv", "__pycache__", ...)` 로 손으로 적어 두었는데 `.venv-torch` 는 그 중 어느 이름도
    아니었다. **남의 코드가 발췌로 들어가니 모델이 패치를 못 냈다**(판정: 제안없음).

    git 에게 물으면 목록이 필요 없다. .gitignore 에 걸린 것(`.venv*`)은 추적 대상이 아니고,
    앞으로 생길 `.venv-무엇` · `node_modules` · 캐시도 자동으로 빠진다. 저장소의 코드란
    **커밋된 나무**다 -- 이 저장소가 precheck 에서 이미 쓰는 기준과 같다."""
    try:
        r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "*.py"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return [x for x in r.stdout.split("\0") if x]
    except (OSError, subprocess.SubprocessError):
        pass
    # git 이 없는 곳(임시 판 등): 그때만 눈에 보이는 이름으로 걸러 훑는다
    return [str(f.relative_to(repo)) for f in repo.rglob("*.py")
            if f.is_file() and not any(x.startswith(".") or x in ("__pycache__", "node_modules")
                                       for x in f.relative_to(repo).parts[:-1])]


def _낱말뽑기(말: str, 몇: int = 14) -> "list[str]":
    """부탁에서 찾을 낱말. **한글 조사가 붙은 라틴 토막을 따로 떼어 낸다.**

    실측 2026-09-12(VM): `수집망 url에 인스타그램, x, meta 추가해줘` 를 쪼개면 `url에` 가 한 낱말이
    되어 `url` 을 가진 파일이 **하나도 안 맞았다**(`dig/search.py` 가 그래서 빠졌다). 이 저장소의
    부탁은 늘 이렇게 섞인다 -- `md가` · `pdf로` · `url에`. 조사를 떼면 그 말들이 다시 맞는다.
    한글 복합어(`수집망` -> `수집`)는 여기서 쪼개지 않는다 -- 그 연결은 `_부탁의모듈` 이 맡는다."""
    out: list[str] = []
    for w in re.split(r"[^0-9A-Za-z가-힣_./]+", 말 or ""):
        w = w.lower()
        if len(w) >= 2:
            out.append(w)
        for 토막 in re.findall(r"[0-9a-z_./]{2,}", w):     # `url에` -> `url`
            if 토막 != w:
                out.append(토막)
    본 = []
    for w in out:                                        # 차례를 지키며 중복만 없앤다
        if w not in 본:
            본.append(w)
    return 본[:몇]


def _부탁의모듈(말: str) -> "list[str]":
    """부탁에 든 말이 **고정 명령의 이름**이면 그 명령이 사는 꾸러미를 돌려준다.

    실측 2026-09-12(VM): `!개선 수집망 url에 인스타그램, x, meta 추가해줘` 가 고른 파일이
    `brief/ledger.py` · `compression/*` 였다 -- 글자 맞춤만으로는 "수집망" 이 `!수집`(dig/) 인 것을
    모른다. 그 연결은 이미 `dispatch.명령들` 에 있다(`!수집` -> dig.discord_cmd). 목록을 새로
    적지 않고 그것에 묻는다 -- 명령이 늘면 이 자리도 같이 늘어난다."""
    낮 = (말 or "").lower()
    꾸러미 = []
    try:
        import dispatch
    except Exception:                                      # noqa: BLE001
        return []
    for m in getattr(dispatch, "명령들", ()):
        이름 = str(getattr(m, "PREFIX", "")).lstrip("!").strip()
        if len(이름) >= 2 and 이름.lower() in 낮:
            뿌리 = (getattr(m, "__name__", "") or "").split(".")[0]
            if 뿌리 and 뿌리 not in 꾸러미:
                꾸러미.append(뿌리)
    return 꾸러미


def _관련파일찾기(말: str, repo: Path, 몇: int = 4) -> "list[str]":
    """부탁의 낱말로 저장소 .py 를 점수 매겨 고른다. 이름 맞음 3점 · 본문 등장 1점(앞 400줄).

    보는 것은 **git 이 추적하는 파일뿐**이다(저장소파이썬) -- 남의 코드를 발췌로 주면 못 고친다."""
    낱말 = _낱말뽑기(말)
    if not 낱말:
        return []
    꾸러미 = _부탁의모듈(말)               # "수집망" -> dig/ (dispatch 가 아는 연결)
    점수: dict = {}
    for rel in 저장소파이썬(repo):
        if any(x in rel.split("/") for x in ("tests", "inbox", "__pycache__")):
            continue
        f = repo / rel
        if not f.is_file() or f.stat().st_size > 400_000:
            continue
        if rel.endswith("__init__.py") and f.stat().st_size < 400:
            continue                       # 빈 꾸러미 표지 -- 발췌로 줄 것이 없다
        s_, 맞음 = 0, False
        낮 = rel.lower()
        if 꾸러미 and rel.split("/")[0] in 꾸러미:
            s_ += 6                        # 그 명령이 사는 꾸러미 -- 글자 맞춤보다 세게 본다
        for w in 낱말:
            if w in 낮:
                s_ += 3
                맞음 = True
        try:
            본 = "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[:400]).lower()
        except OSError:
            continue
        for w in 낱말:
            n = 본.count(w)
            if n:
                s_ += min(n, 3)            # 몇 번 나오나도 본다 -- 그 말을 '다루는' 파일이 위로 온다
                맞음 = True
        if s_ and 맞음:                    # 꾸러미 보너스만으로는 안 된다 -- 부탁의 말이 실제로 있어야
            점수[rel] = s_
    # 부탁이 어느 명령을 가리키면 **그 꾸러미 안에서 고른다** -- 남의 꾸러미가 점수로 끼어들지 않게.
    def _차례(kv):
        rel, 점 = kv
        return (0 if (꾸러미 and rel.split("/")[0] in 꾸러미) else 1, -점, rel)
    return [k for k, _ in sorted(점수.items(), key=_차례)[:몇]]



def 제안받기(원프롬프트: str, 횟수: int = 2) -> "tuple[dict | None, int, str]":
    """패치(또는 사람) 꼴의 답을 받는다. 꼴이 아니면 **무엇이 왔는지 보여 주며 다시 청한다.**
    (제안, 시도수, 마지막 답머리).

    실측 2026-09-12(VM): `!개선 수집망 url에 …` 이 첫 답이 패치 꼴이 아니어서 **그 자리에서 끝났다**
    (판정: 제안없음). 적용 실패와 시뮬 빨강은 이미 되풀이하는데 이 자리만 한 번에 포기했다.
    사용자: "최대한 스스로 해결해야 한다." 그래서 여기도 되풀이로 바꾼다."""
    답 = ""
    for k in range(1, max(1, 횟수) + 1):
        프 = 원프롬프트 if k == 1 else (
            원프롬프트 + f"\n\n[꼴이 아니다 {k - 1}/{횟수}] 네 앞 답은 이렇게 시작했다: {답.strip()[:200]!r}\n"
            "설명·인사·펜스 없이 **JSON 하나만** 답하라. 꼴은 둘 중 하나다:\n"
            '  {"꼴": "패치", "왜": "...", "근거": [], "편집": [{"path": "...", "old": "...", "new": "..."}], '
            '"새파일": [{"path": "...", "본문": "..."}]}\n'
            '  {"꼴": "사람", "사람이_할_것": "..."}   <- 사람만 가진 값(열쇠·승인·계정)이 필요할 때만')
        try:
            답 = (제안기 or _제안기본)(프) or ""
        except Exception as e:                             # noqa: BLE001
            return None, k, f"제안기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}"
        제안 = 해석(답)
        if 제안:
            return 제안, k, 답[:200]
        if _원장repo is not None:
            _적기(_원장repo, {"꼴": "되묻기", "왜": "패치 꼴이 아니다", "시도": k, "답머리": 답.strip()[:160]})
    return None, 횟수, 답[:200]


def 부탁프롬프트(말: str, repo: Path, 근거: dict, 파일들: "list[str]") -> str:
    발췌 = []
    for rel in 파일들:
        try:
            줄들 = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()[:200]
            발췌.append(f"### {rel} (앞 {len(줄들)}줄)\n" + "\n".join(줄들))
        except OSError:
            continue
    근거줄 = ""
    if 근거.get("참고"):
        근거줄 = "\n\n제2의 뇌가 모은 참고(논문·코드 -- 여기서 방법을 고르고 \"근거\" 에 출처를 적어라):\n" + "\n".join(
            f"- {x['출처']} #{x['해시']}: {x['요약']}" for x in 근거["참고"])
        if 근거.get("확장"):
            근거줄 += f"\n(참고가 모자라 {근거['확장']}바퀴 넓혀 모았다)"
    return (
        "너는 이 저장소(디스코드 하네스 에이전트)의 **개선자**다. 사람이 말한 개선을 **최소 패치**로 옮겨라.\n\n"
        f"사람이 말한 개선: {말}\n\n"
        + ("\n\n".join(발췌) if 발췌 else "(관련 파일을 못 골랐다 -- 새 파일로 지어도 된다)")
        + 근거줄
        + "\n\n규칙:\n"
        "- 답은 JSON 하나: {\"꼴\": \"패치\", \"왜\": \"한 줄\", \"근거\": [\"출처#해시\", ...], "
        "\"편집\": [{\"path\": \"...\", \"old\": \"정확히 한 번 있는 글\", \"new\": \"...\"}], "
        "\"새파일\": [{\"path\": \"...\", \"내용\": \"전체\"}]}\n"
        "- old 는 **위 발췌에서 그대로 복사한 글**만. 발췌에 없는 자리는 고치지 마라 -- 거절된다. "
        "새 기능은 편집이 아니라 **새파일** 로 지어라(모듈 + tests/test_<이름>.py).\n"
        "- **검사를 지우거나 assert 를 빼지 마라.** 새 기능이면 tests/test_<이름>.py 를 새파일로 같이 지어라.\n"
        "- gates/ · .env · 판정 원장(*.jsonl) 은 못 만진다.\n"
        "- 레포 전체 검사가 돌아간다 -- **다른 데를 깨뜨리면 거절된다.** 좁게 고쳐라. "
        "새 기능은 새 모듈 + tests/test_<이름>.py + (필요하면) requirements.txt 한 줄로 된다.\n"
        "- 사람만 가진 값(열쇠·승인·계정)이 필요할 때만 {\"꼴\": \"사람\", \"사람이_할_것\": \"...\"}.\n"
    )


def 사용자개선(말: str, repo=None, 초: int = 180, 전부: bool = True, 전부초: int = 1800) -> dict:
    """`!개선 <말>` -- 사람이 말한 개선. red->green 이 없으므로 **레포 전체에 회귀가 없는 것**이 판정이다.

    사용자(2026-09-11): "난 내 에이전트가 내가 한 말의 개선을 하길 바란다. red-green 개선이 아니라
    하네스 에이전트 성능 자체의 개선이야."
    """
    from plan import store as P
    repo = Path(repo or REPO)
    말 = (말 or "").strip()
    r = {"부탁": 말, "판정": "", "왜": "", "id": "", "diff": "", "말": "", "근거": [], "댄근거": [],
        "확장": 0, "파일들": [], "회귀": None, "제안시도": 0}
    if not 말:
        r.update(판정="빈부탁", 말="무엇을 개선할지 한 줄로 적어라 -- `!개선 <말>`")
        return r
    막힘, 판말 = 판정리(repo)
    if 막힘:
        r.update(판정="판열림", 말=판말)
        return r
    _적기(repo, {"꼴": "부탁", "말": 말[:300]})
    if 판말:
        r["말"] = 판말

    근거 = 근거모으기({"무엇": 말, "왜": "사람이 말한 개선", "종류": "부탁"}, repo)
    r["근거"] = [f"{x['출처']}#{x['해시']}" for x in 근거["참고"]]
    r["확장"] = 근거["확장"]
    r["파일들"] = _관련파일찾기(말, repo)
    원프롬프트 = 부탁프롬프트(말, repo, 근거, r["파일들"])
    global _원장repo
    _원장repo = repo
    제안, r["제안시도"], 답머리 = 제안받기(원프롬프트)
    if 제안 is None:
        if 답머리.startswith("제안기를 못 불렀다"):
            r.update(판정="제안없음", 말=답머리)
            return r
        # 두 번 청해도 꼴이 아니다 -- 여기서 끝내지 않고 긴 호흡으로 넘긴다(코드가 정한 길).
        r.update(판정="조사로", 말=f"두 번 청해도 패치 꼴의 답이 아니다(마지막 답머리: {답머리[:120]!r}) "
                               "-- 긴 호흡(조사)으로 넘긴다")
        _적기(repo, {"꼴": "조사로", "말": 말[:200], "이유": f"패치 꼴 아님 · 답머리 {답머리[:120]}"})
        return r
    if 제안 and 제안.get("꼴") == "사람" and not 사람몫인가(제안.get("사람이_할_것", "")):
        # **회피는 받지 않는다.** 사람 몫이 아닌 이유로 물러났으면 긴 호흡(조사)으로 넘긴다 --
        # 거기서는 두뇌가 도구를 들고 새 모듈·검사·의존성을 직접 짓고 끝값으로 판정받는다.
        r.update(판정="조사로", 말=f"모델이 물러났지만 사람 몫이 아니다: {str(제안.get('사람이_할_것', ''))[:160]} "
                               "-- 긴 호흡(조사)으로 넘긴다")
        _적기(repo, {"꼴": "조사로", "말": 말[:200], "이유": str(제안.get("사람이_할_것", ""))[:200]})
        return r
    if 제안.get("꼴") != "패치":
        r.update(판정="제안없음", 말=제안.get("사람이_할_것") or "패치 꼴의 답이 아니다")
        return r
    r["왜"] = str(제안.get("왜", ""))[:200]
    r["댄근거"] = [str(x) for x in (제안.get("근거") or [])][:6]

    def _판새로():
        if P.현재판(repo) is not None:
            P.버림(repo)
        P.켜기(f"자가개선: [부탁] {말[:80]}", repo=repo, 누가="개선")
        return P.현재판(repo)
    ok, 적용말, 제안, r["적용시도"] = 적용되풀이(제안, 원프롬프트, _판새로)
    r["왜"] = str(제안.get("왜", ""))[:200]
    if not ok:
        if P.현재판(repo) is not None:
            P.버림(repo)
        if "그림자" in 적용말:
            r.update(판정="판못깜", 말=적용말)
        else:
            # 되풀이해도 패치를 못 붙였다 -- 여기서 끝내지 않고 긴 호흡으로 넘긴다(코드가 정한 길).
            r.update(판정="조사로", 말=f"패치를 못 붙였다({적용말[:120]}) -- 긴 호흡(조사)으로 넘긴다")
            _적기(repo, {"꼴": "조사로", "말": 말[:200], "이유": 적용말[:200]})
        return r

    시험보고 = P.시험하기(repo, 초=초, 전부=전부, 전부초=전부초)
    st = P.읽기(repo) or {}
    시 = st.get("시험") or {}
    r["회귀"] = 시.get("회귀")
    r["시뮬시도"] = 1
    막힘 = _초록의뜻(repo, 시험보고)          # 빨강이거나, 초록이어도 공허하면 막힌 것이다
    # **시뮬이 빨가면 그 꼬리를 들려 다시 청한다.** 사용자(2026-09-12): "코드 고치고 문제 있으면 또
    # 수정하고." 실측(VM): 새 파일 둘을 붙였는데 지은 검사가 빨갛게 나와 거기서 버렸다. 두 번 더
    # 청하고, 그래도 빨가면 긴 호흡(조사)으로 넘긴다 -- 사람에게가 아니다. 공허한 초록도 같은 길이다.
    for 다시 in range(1, 시뮬되풀이횟수 + 1):
        if not 막힘:
            break
        P.버림(repo)
        _적기(repo, {"꼴": "시뮬되풀이", "말": 말[:120], "다시": 다시, "꼬리": 막힘[-300:]})
        되묻기 = (원프롬프트 + f"\n\n[시뮬 판정 {다시}/{시뮬되풀이횟수}] 네 패치를 붙이고 저장소 검사를 돌렸더니 아래처럼 "
                f"막혔다. 고친 **패치 전체**를 같은 JSON 꼴로 다시 답하라(편집+새파일 다 포함).\n"
                + 막힘[-1500:])
        try:
            새 = 해석((제안기 or _제안기본)(되묻기))
        except Exception as e:                             # noqa: BLE001
            r.update(판정="조사로", 말=f"시뮬 빨강 뒤 되묻기 실패({type(e).__name__}) -- 긴 호흡(조사)으로 넘긴다")
            return r
        if not 새 or 새.get("꼴") != "패치":
            r.update(판정="조사로", 말="시뮬 빨강 뒤 패치 꼴의 답이 안 왔다 -- 긴 호흡(조사)으로 넘긴다")
            return r
        제안 = 새
        ok, 적용말, 제안, 시도 = 적용되풀이(제안, 원프롬프트, _판새로)
        r["적용시도"] = r.get("적용시도", 0) + 시도
        if not ok:
            if P.현재판(repo) is not None:
                P.버림(repo)
            r.update(판정="조사로", 말=f"시뮬 빨강 뒤 고친 패치를 못 붙였다({적용말[:100]}) -- 긴 호흡(조사)으로 넘긴다")
            return r
        시험보고 = P.시험하기(repo, 초=초, 전부=전부, 전부초=전부초)
        st = P.읽기(repo) or {}
        시 = st.get("시험") or {}
        r["회귀"] = 시.get("회귀")
        r["시뮬시도"] = 다시 + 1
        막힘 = _초록의뜻(repo, 시험보고)
    if 막힘:
        P.버림(repo)
        _적기(repo, {"꼴": "조사로", "말": 말[:200], "이유": "시뮬 막힘 " + str(r["시뮬시도"]) + "번: " + 막힘[:120]})
        r.update(판정="조사로", 말=f"시뮬이 {r['시뮬시도']}번 다 막혔다 -- 긴 호흡(조사)으로 넘긴다\n" + 막힘[-500:])
        return r
    r.update(판정="동의대기", id=st.get("id", ""), diff=P.보기(repo)[:1500],
             말=("레포 전체 시뮬 초록(회귀 없음) -- **사람의 동의를 기다린다** (`!개선 승인`)"))
    _적기(repo, {"꼴": "부탁끝", "말": 말[:200], "판정": r["판정"], "id": r["id"], "근거": r["근거"],
               "댄근거": r["댄근거"], "확장": r["확장"], "회귀": r["회귀"]})
    return r


# ---------------------------------------------------------------- 남은 계획판: 봇이 켠 것은 봇이 치운다
기다림초 = 25 * 60          # 산 실행이 판을 쥐고 있을 때 기다리는 한도. 이 일 자체가 배경이라 기다릴 수 있다
_기다림틈 = 10.0


def _살아있나(pid, 태어난시각=None) -> bool:
    """그 pid 의 프로세스가 지금 돌고 있나. 나 자신이면 False(내가 켠 판을 내가 막을 일은 없다).

    `태어난시각` 이 적혀 있으면 **그것까지 맞아야** 같은 프로세스로 본다 -- pid 는 돌려 쓰이므로
    pid 만 보면 죽은 실행의 판을 '남이 쓰는 중' 으로 읽고 영영 안 치운다."""
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass                                           # 남의 것이지만 살아 있다
    from plan import store as P
    상태, 지금태어난 = P.프로세스표(pid)
    # **좀비는 죽은 것이다.** 이미 끝났는데 부모가 안 거둬 간 것이라 os.kill(pid, 0) 은 여전히 된다 --
    # 그것을 살아 있다고 읽으면 끝난 실행을 한도까지 기다린다(실측: 검사가 25분 기다리다 멈췄다).
    if 상태 == "Z":
        return False
    if 태어난시각 is not None and 지금태어난 is not None and 지금태어난 != 태어난시각:
        return False                                   # 같은 pid, 다른 프로세스 -- 그 실행은 죽었다
    return True



def _기다리기(repo: Path, s: dict, 머리: str) -> "dict | None":
    """판을 쥔 산 실행이 끝날 때까지 기다린다. 판이 비면 None, 아니면 마지막으로 읽은 판 상태.
    기다린 것은 원장에 남긴다 -- 보고에 "왜 늦었나" 가 있어야 한다."""
    from plan import store as P
    시작 = time.monotonic()
    _적기(repo, {"꼴": "기다림", "왜": "다른 실행이 계획판을 쓰는 중", "누구": str(s.get("누가", ""))[:40],
                "pid": s.get("pid"), "한도초": 기다림초})
    while time.monotonic() - 시작 < 기다림초:
        time.sleep(_기다림틈)
        새 = P.읽기(repo)
        if not 새:
            _적기(repo, {"꼴": "기다림끝", "기다린초": round(time.monotonic() - 시작, 1), "왜": "판이 비었다"})
            return None
        if 새.get("id") != s.get("id") or not _살아있나(새.get("pid"), 새.get("태어난시각")):
            _적기(repo, {"꼴": "기다림끝", "기다린초": round(time.monotonic() - 시작, 1),
                        "왜": "판이 바뀌거나 쥔 실행이 끝났다"})
            return 새
        s = 새
    _적기(repo, {"꼴": "기다림끝", "기다린초": round(time.monotonic() - 시작, 1), "왜": "한도를 넘겼다"})
    return s


def 판정리(repo) -> "tuple[bool, str]":
    """켜져 있는 계획판을 코드가 가른다. (막힘, 말).

    실측 2026-09-12(VM): `!개선` 이 0.3분 만에 "판열림 -- 사람이 `!계획 승인/버림` 으로 끝내라" 로 끝났다.
    그 판은 사람이 켠 것이 아니라 앞 실행이 남긴 것이었다. 사용자: "사람 몫으로 넘기는 건 최종이다."
    **동의를 기다릴 자격이 있는 판은 하나뿐이다: 지금 diff 그대로 리허설 초록을 받은 판.** 그것만 사람의
    `!개선 승인/버림` 을 기다린다(붙일지는 사람이 정한다). 그 밖의 판 -- 시험을 안 했거나, 빨갰거나, 시험한
    뒤 코드가 또 바뀐 것 -- 은 죽은 실행의 찌꺼기다. 버리고 원장에 적은 뒤 이어 간다."""
    from plan import store as P
    repo = Path(repo)
    s = P.읽기(repo)
    if not s:
        return False, ""
    시 = s.get("시험") or {}
    판 = Path(s["판"])                                   # 디렉터리가 사라진 판은 P.읽기 가 이미 None 으로 친다
    초록 = bool(시.get("통과")) and 시.get("해시") == P._해시(판)
    머리 = f"[{s.get('id', '?')}] {s.get('누가', '?')} · {str(s.get('요청', ''))[:60]!r}"
    # **켠 프로세스가 살아 있으면 남의 일이 도는 중이다.** 실측 2026-09-12(VM): PDF 부탁이 시험 중일 때
    # 자가개선이 나란히 돌아 그 판을 '시험 안 한 판' 이라며 치웠다. 산 실행의 판은 찌꺼기가 아니다.
    # **그래서 기다린다.** 실측 2026-09-12(VM, 두 시간 뒤): 기다리지 않고 "그 실행이 끝나면 다시 부탁하라" 로
    # 끝냈더니 사용자가 그 말을 받았다. 사용자: "사람 몫으로 넘기는 건 최종이다." 이 일 자체가 배경이므로
    # 기다릴 수 있다 -- 앞 실행이 끝나면 이어 간다. 한도를 넘기면 그때만 사람에게 말한다.
    if _살아있나(s.get("pid"), s.get("태어난시각")):
        s = _기다리기(repo, s, 머리)
        if s is None:
            return False, f"앞 실행이 끝나 판이 비었다 -- 이어 간다 ({머리})"
        if _살아있나(s.get("pid"), s.get("태어난시각")):
            return True, (f"계획판을 다른 실행이 {기다림초 // 60}분 넘게 쓰고 있다 {머리} (pid {s.get('pid')}) -- "
                          f"그 실행이 끝나면 이 부탁을 다시 걸어라(한 번에 하나)")
        시 = s.get("시험") or {}               # 기다린 뒤의 판을 다시 본다 -- 그 사이 바뀌었을 수 있다
        판 = Path(s["판"])
        초록 = bool(시.get("통과")) and 시.get("해시") == P._해시(판)
        머리 = f"[{s.get('id', '?')}] {s.get('누가', '?')} · {str(s.get('요청', ''))[:60]!r}"
    if 초록:
        return True, (f"계획판이 이미 켜져 있다 -- 리허설 초록으로 동의를 기다리는 중 {머리}. `!개선 승인` 으로 "
                      f"붙이거나 `!개선 버림` 으로 치워야 다음 부탁을 받는다(한 번에 하나)")
    왜 = "시험을 안 한 판" if not 시 else "리허설 빨강" if not 시.get("통과") else "시험한 뒤 코드가 또 바뀜"
    # 버리기 전에 diff 를 남긴다 -- 사람이 `!계획 켜기` 로 손수 고치던 판일 수도 있다. 지우는 것은 못 되돌린다.
    남김 = ""
    try:
        d = P._diff(판, 이진=True)
        if d.strip():
            f = repo / "logs" / f"계획판_{s.get('id', '0')}.diff"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(d, encoding="utf-8")
            남김 = str(f.relative_to(repo))
    except (OSError, ValueError):
        pass
    P.버림(repo)
    _적기(repo, {"꼴": "판정리", "id": s.get("id", ""), "누가": s.get("누가", ""), "요청": str(s.get("요청", ""))[:120], "왜": 왜, "diff": 남김})
    return False, f"남아 있던 계획판을 치웠다 {머리} ({왜})" + (f" · diff 는 {남김} 에 남겼다" if 남김 else "")


def 부탁보고(r: dict) -> str:
    줄 = [f"개선 부탁: {r['부탁'][:90]}", f"  판정: **{r['판정']}**" + (f" -- {r['왜']}" if r["왜"] else "")]
    if r["파일들"]:
        줄.append("  고른 파일: " + ", ".join(r["파일들"]))
    줄.append("  근거(제2의 뇌): " + (", ".join(r["댄근거"][:4]) if r["댄근거"] else "없음")
             + (f" · 탐색 {r['확장']}바퀴 넓힘" if r["확장"] else ""))
    회 = r.get("회귀") or {}
    if 회:
        줄.append(f"  레포 전체 회귀: 새로 깨짐 {회.get('새로깨짐') or '없음'} · 고쳐짐 {회.get('고쳐짐') or '없음'}")
    if r["말"]:
        줄.append("  " + r["말"][:400].replace("\n", "\n  "))
    if r["판정"] == "동의대기":
        줄.append("  붙이려면 `!개선 승인` · 아니면 `!개선 버림`")
        줄.append("  diff:\n" + "\n".join("    " + x for x in r["diff"].splitlines()[:25]))
    return "\n".join(줄)


# ---------------------------------------------------------------- 틈이 없으면: 제2의 뇌로 성능 개선거리
고르기기 = None    # 검사 주입: (prompt) -> str(JSON {"꼴":"부탁","부탁":...}). None 이면 router 수리기


def 저장소요약(repo: Path, 몇: int = 14) -> str:
    """이 저장소가 무엇으로 이루어졌는지 한 줄씩 -- 모델이 '어디에 적용할지' 를 고르는 바탕."""
    줄 = []
    for d in sorted(x for x in repo.iterdir() if x.is_dir() and (x / "__init__.py").is_file()):
        if d.name in (".git", "venv", "tests", "gates"):
            continue
        머리 = ""
        for 이름 in ("run.py", "store.py", "__init__.py"):
            f = d / 이름
            if f.is_file():
                본 = f.read_text(encoding="utf-8", errors="replace").lstrip()
                if 본.startswith('"""'):
                    머리 = 본[3:].split("\n")[0][:90]
                    break
        줄.append(f"- {d.name}/: {머리}")
    return "\n".join(줄[:몇])


def 고르기프롬프트(요약: str, 근거: dict) -> str:
    참 = "\n".join(f"- {x['출처']} #{x['해시']}: {x['요약']}" for x in 근거.get("참고", []))
    return (
        "너는 이 저장소(디스코드 하네스 에이전트)의 **성능 개선 제안자**다. 지금 고칠 빨간 검사(틈)가 없다.\n"
        "그래서 **제2의 뇌가 모은 최신 것** 가운데 **이 저장소에 실제로 적용할 만한 것 하나**를 골라라.\n\n"
        f"저장소 얼개:\n{요약}\n\n제2의 뇌가 모은 것:\n{참 or '(없음)'}\n\n"
        "규칙:\n"
        '- 답은 JSON 하나: {"꼴": "부탁", "부탁": "무엇을 어떻게 고칠지 한 문장(명령문)", '
        '"왜": "무엇이 좋아지는가 한 줄", "근거": ["출처#해시", ...]}\n'
        "- **모은 것에 근거가 있는 것만** 골라라. 근거가 없으면 {\"꼴\": \"없음\", \"왜\": \"...\"} 로 답하라.\n"
        "- 좁게 -- 파일 한둘로 끝나는 것. 큰 개편은 고르지 마라(레포 전체 검사를 지나야 한다).\n"
        "- 검사를 지우거나 게이트를 무르게 하는 것은 고르지 마라.\n"
    )


def 부탁고르기(repo=None) -> dict:
    """{"됐나","부탁","왜","근거","확장","말"}. 제2의 뇌에서 '적용할 만한 것' 하나를 고른다."""
    repo = Path(repo or REPO)
    근거 = 근거모으기({"무엇": "agent harness performance latest methods",
                   "왜": "틈이 없다 -- 최신 기술에서 적용거리를 찾는다", "종류": "성능"}, repo)
    r = {"됐나": False, "부탁": "", "왜": "", "근거": [f"{x['출처']}#{x['해시']}" for x in 근거["참고"]],
        "확장": 근거["확장"], "말": ""}
    if not 근거["참고"]:
        r["말"] = "제2의 뇌에 참고가 없다(넓혀 모아도) -- 수집이 먼저다(`!수집` · `!연구 <주제>`)"
        return r
    try:
        답 = (고르기기 or _제안기본)(고르기프롬프트(저장소요약(repo), 근거))
    except Exception as e:                             # noqa: BLE001
        r["말"] = f"고르기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}"
        return r
    m = re.search(r"\{.*\}", 답 or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    if d.get("꼴") != "부탁" or not str(d.get("부탁", "")).strip():
        r["말"] = str(d.get("왜") or "적용할 만한 것을 못 골랐다")
        return r
    r.update(됐나=True, 부탁=str(d["부탁"]).strip()[:300], 왜=str(d.get("왜", ""))[:200])
    if d.get("근거"):
        r["근거"] = [str(x) for x in d["근거"]][:6]
    return r


def 성능개선(repo=None, 초: int = 180, 전부: bool = True, 전부초: int = 1800) -> dict:
    """**틈이 없을 때 가는 길.** 제2의 뇌에서 적용거리를 골라 그것을 부탁으로 삼아 개선한다.

    사용자(2026-09-11): "남은 틈이 없으면 성능 개선으로 넘어가 제2의 brain 써서 최신 기술로
    우리가 적용 가능한 기술 탐색해서." 판정은 그대로 -- **레포 전체 회귀 없음 + 사람 동의**."""
    repo = Path(repo or REPO)
    고 = 부탁고르기(repo)
    _적기(repo, {"꼴": "성능고르기", "됐나": 고["됐나"], "부탁": 고["부탁"][:200], "왜": 고["왜"],
               "근거": 고["근거"], "확장": 고["확장"], "말": 고["말"][:200]})
    if not 고["됐나"]:
        return {"부탁": "", "판정": "고를것없음", "왜": "", "id": "", "diff": "", "말": 고["말"],
                "근거": 고["근거"], "댄근거": [], "확장": 고["확장"], "파일들": [], "회귀": None}
    r = 사용자개선(고["부탁"], repo, 초=초, 전부=전부, 전부초=전부초)
    r["왜"] = r["왜"] or 고["왜"]
    r["근거"] = r["근거"] or 고["근거"]
    r["성능거리"] = True
    return r


# ---------------------------------------------------------------- ③ 시뮬레이션 + 성능 판정
def _자기본(repo: Path, 판: Path) -> dict:
    """eval/run 을 판에서 돌려 후퇴(끝값 1)가 없는지 본다. 키가 없으면 못잼."""
    from sandbox import run as SB
    r = SB.실행(["python3", "eval/run.py"], repo=판, 지금트리=True, 초=600, 메모리MB=4096)
    if not r["돌았나"]:
        return {"돌았나": False, "후퇴": False, "말": r.get("메모", "판을 못 깜")}
    끝 = int(r["끝값"])
    return {"돌았나": 끝 != 3, "후퇴": 끝 == 1,
            "말": {0: "자(eval) 후퇴 없음", 1: "**자(eval) 후퇴** -- 개선이 아니다", 3: "자를 못 댔다(모델 키 없음) -- 못잼"}.get(끝, f"끝값 {끝}")}


def 한후보(틈: dict, repo=None, 초: int = 120, 자: bool = False,
        전부: bool = True, 전부초: int = 1800) -> dict:
    """틈 하나: 빨강 확인 -> 제안 -> 그림자에 적용 -> 초록 확인 -> 리허설 -> (자) -> 동의 대기 또는 버림."""
    from plan import store as P
    repo = Path(repo or REPO)
    r = {"틈": 틈, "판정": "", "왜": "", "id": "", "diff": "", "말": "", "근거": [], "댄근거": [], "확장": 0, "회귀": None}

    전끝, 전꼬리 = 판정(틈["판정명령"], repo, 초)
    if 전끝 == 0:
        r.update(판정="이미초록", 말="지금 실제 트리에서 이미 초록이다 -- 틈이 아니다")
        return r
    if 전끝 == 3 and "차단" in 전꼬리:
        r.update(판정="판정불가", 말=전꼬리)
        return r

    근거 = 근거모으기(틈, repo)
    r["근거"] = [f"{x['출처']}#{x['해시']}" for x in 근거["참고"]]
    r["확장"] = 근거["확장"]
    원프롬프트 = 프롬프트(틈, 전꼬리, repo, 근거)
    try:
        답 = (제안기 or _제안기본)(원프롬프트)
    except Exception as e:                             # noqa: BLE001
        r.update(판정="제안없음", 말=f"제안기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}")
        return r
    제안 = 해석(답)
    if not 제안 or 제안.get("꼴") != "패치":
        r.update(판정="제안없음", 말=(제안 or {}).get("사람이_할_것") or "패치 꼴의 답이 아니다")
        return r
    r["왜"] = str(제안.get("왜", ""))[:200]
    r["댄근거"] = [str(x) for x in (제안.get("근거") or [])][:6]

    def _판새로():
        if P.현재판(repo) is not None:
            P.버림(repo)
        P.켜기(f"자가개선: [{틈['종류']}] {틈['무엇']}", repo=repo, 누가="자가개선")
        return P.현재판(repo)
    global _원장repo
    _원장repo = repo
    ok, 말, 제안, r["적용시도"] = 적용되풀이(제안, 원프롬프트, _판새로)
    r["왜"] = str(제안.get("왜", ""))[:200]
    판 = P.현재판(repo)
    if not ok:
        if 판 is not None:
            P.버림(repo)
        r.update(판정="적용실패" if "그림자" not in 말 else "판못깜", 말=말)
        return r

    후끝, 후꼬리 = 판정(틈["판정명령"], 판, 초)
    if 후끝 != 0:
        P.버림(repo)
        r.update(판정="빨강그대로", 말=f"패치를 붙여도 판정 명령이 빨강이다(끝값 {후끝}): {후꼬리[-200:]}")
        return r

    시험보고 = P.시험하기(repo, 초=초, 전부=전부, 전부초=전부초)
    s = P.읽기(repo) or {}
    r["회귀"] = (s.get("시험") or {}).get("회귀")
    if not (s.get("시험") or {}).get("통과"):
        P.버림(repo)
        r.update(판정="리허설빨강", 말=시험보고[-400:])
        return r

    if 자:
        z = (자기 or _자기본)(repo, 판)
        if z["후퇴"]:
            P.버림(repo)
            r.update(판정="자후퇴", 말=z["말"])
            return r
        r["말"] = z["말"]

    r.update(판정="동의대기", id=s.get("id", ""), diff=P.보기(repo)[:1500],
             말=(r["말"] + " · " if r["말"] else "") + "red->green · 리허설 초록 -- **사람의 동의를 기다린다** (`!자가개선 승인`)")
    return r


def 자가개선(repo=None, 몇: int = 기본후보, 초: int = 120, 자: bool = False, 배선: bool = False,
          점검: bool = False, 전부: bool = True, 전부초: int = 1800) -> dict:
    from plan import store as P
    repo = Path(repo or REPO)
    몇 = max(1, min(int(몇), 최대후보))
    결과 = {"돌았나": True, "틈수": 0, "해본": [], "동의대기": None, "메모": "", "남은것": "", "성능": False}
    막힘, 판말 = 판정리(repo)
    if 막힘:
        결과.update(돌았나=False, 남은것=판말)
        return 결과
    if 판말:
        결과["판정리"] = 판말
    틈들 = 틈모으기(repo, 배선, 점검) if 틈모으기_ is None else 틈모으기_(repo)
    결과["틈수"] = len(틈들)
    _적기(repo, {"꼴": "탐색", "틈수": len(틈들), "틈": [f"[{g['종류']}] {g['무엇']}" for g in 틈들[:10]]})
    if not 틈들:
        # **멈추지 않는다** -- 틈이 없으면 제2의 뇌로 적용거리를 찾아 성능 개선으로 넘어간다.
        결과["성능"] = True
        p = 성능개선(repo, 초=초, 전부=전부, 전부초=전부초)
        결과["해본"].append(p)
        if p["판정"] == "동의대기":
            결과["동의대기"] = p
        else:
            결과["남은것"] = ("고칠 틈은 없다. 제2의 뇌로 성능 개선거리를 찾았지만 "
                          + {"고를것없음": "적용할 만한 것을 못 골랐다", "시뮬빨강": "레포 전체에서 새로 깨졌다"}
                          .get(p["판정"], p["판정"]) + f" -- {p['말'][:160]}")
        결과["메모"] = 기억쓰기(결과, repo)
        _적기(repo, {"꼴": "끝", "동의대기": (결과["동의대기"] or {}).get("id"), "남은것": 결과["남은것"],
                   "메모": 결과["메모"], "성능": True})
        return 결과
    for 틈 in 틈들[:몇]:
        r = 한후보(틈, repo, 초, 자, 전부=전부, 전부초=전부초)
        결과["해본"].append(r)
        _적기(repo, {"꼴": "후보", "종류": 틈["종류"], "무엇": 틈["무엇"], "판정": r["판정"], "왜": r["왜"], "id": r["id"],
                   "근거": r.get("근거", []), "댄근거": r.get("댄근거", []), "확장": r.get("확장", 0), "말": r["말"][:300]})
        if r["판정"] == "동의대기":
            결과["동의대기"] = r
            break
    if not 결과["동의대기"]:
        결과["남은것"] = f"{len(결과['해본'])}개 후보를 시뮬레이션했지만 셋(red->green · 리허설 · 자)을 다 지난 것이 없다"
    결과["메모"] = 기억쓰기(결과, repo)
    _적기(repo, {"꼴": "끝", "동의대기": (결과["동의대기"] or {}).get("id"), "남은것": 결과["남은것"], "메모": 결과["메모"]})
    return 결과


# ---------------------------------------------------------------- 동의 -> 붙이기 (사람만)
def 승인(repo=None, 누가: str = "cli") -> str:
    from plan import store as P
    repo = Path(repo or REPO)
    s = P.읽기(repo)
    if not s or not str(s.get("요청", "")).startswith("자가개선:"):
        return "동의를 기다리는 자가개선 후보가 없다 -- `!자가개선` 으로 먼저 찾아라"
    말 = P.승인(repo, 누가=누가)                     # 리허설 초록 + 같은 diff 일 때만 붙는 그 문을 그대로 지난다
    _적기(repo, {"꼴": "승인", "id": s.get("id"), "누가": 누가, "말": 말[:200]})
    return 말


def 버림(repo=None) -> str:
    from plan import store as P
    repo = Path(repo or REPO)
    s = P.읽기(repo)
    if not s or not str(s.get("요청", "")).startswith("자가개선:"):
        return "버릴 자가개선 후보가 없다"
    말 = P.버림(repo)
    _적기(repo, {"꼴": "버림", "id": s.get("id")})
    return 말


def 상태(repo=None) -> str:
    from plan import store as P
    repo = Path(repo or REPO)
    s = P.읽기(repo)
    줄 = []
    if s and str(s.get("요청", "")).startswith("자가개선:"):
        시 = s.get("시험") or {}
        줄.append(f"동의 대기 [{s['id']}] {s['요청'][6:80]} · 리허설 {'초록' if 시.get('통과') else '빨강/없음'} -- `!자가개선 승인` 또는 `!자가개선 버림`")
    else:
        줄.append("동의 대기 중인 후보 없음")
    끝 = [r for r in 원장읽기(repo) if r.get("꼴") == "끝"]
    if 끝:
        줄.append(f"마지막 탐색 {끝[-1].get('때', '')}: " + (f"후보 {끝[-1]['동의대기']}" if 끝[-1].get("동의대기") else 끝[-1].get("남은것", "")))
    승 = [r for r in 원장읽기(repo) if r.get("꼴") == "승인"]
    줄.append(f"지금까지 승인된 개선 {len(승)}건")
    return "\n".join(줄)


# ---------------------------------------------------------------- 메모 · 보고
def 기억쓰기(결과: dict, repo=None) -> str:
    repo = Path(repo or REPO)
    때 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    p = repo / 메모곳 / f"{때}_자가개선.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = ["---", "topic: '자가개선 탐색'", "---", "", f"# 자가개선 탐색 ({결과['틈수']}개 틈)", ""]
    for r in 결과["해본"]:
        if "틈" not in r:
            줄.append(f"- [성능거리] {r.get('부탁', '')[:70]} -> **{r['판정']}**" + (f" · {r.get('왜', '')}" if r.get("왜") else ""))
            continue
        g = r["틈"]
        줄.append(f"- [{g['종류']}] {g['무엇']} -> **{r['판정']}**" + (f" · {r['왜']}" if r["왜"] else "")
                 + (f" · 근거 {', '.join(r['댄근거'][:3])}" if r.get("댄근거") else "")
                 + (f" · 뇌 확장 {r['확장']}바퀴" if r.get("확장") else ""))
        if r["말"]:
            줄.append(f"    {r['말'][:200]}")
    줄 += ["", "## 결론", (f"동의 대기: {결과['동의대기']['id']}" if 결과["동의대기"] else 결과["남은것"] or "(없음)"), ""]
    p.write_text("\n".join(줄), encoding="utf-8")
    return str(p.relative_to(repo))


def 보고(결과: dict) -> str:
    if not 결과["돌았나"]:
        return "자가개선 못 돌림 -- " + 결과["남은것"]
    줄 = [f"자가개선 -- 틈 {결과['틈수']}개 중 {len(결과['해본'])}개 시뮬레이션"
         + (" · **틈이 없어 제2의 뇌로 성능 개선거리를 찾았다**" if 결과.get("성능") else "")]
    for r in 결과["해본"]:
        if "틈" not in r:
            줄.append(f"  {'✓' if r['판정'] == '동의대기' else '✗'} [성능거리] {r.get('부탁', '')[:70]}: {r['판정']}"
                     + (f" -- {r['말'][:120]}" if r.get("말") else ""))
            continue
        g = r["틈"]
        줄.append(f"  {'✓' if r['판정'] == '동의대기' else '✗'} [{g['종류']}] {g['무엇']}: {r['판정']}" + (f" -- {r['말'][:120]}" if r["말"] else ""))
    d = 결과["동의대기"]
    if d:
        줄.append(f"\n**동의를 기다린다** [{d['id']}] 왜: {d['왜']}")
        회 = d.get("회귀") or {}
        if 회:
            줄.append(f"  레포 전체 회귀: 새로 깨짐 {회.get('새로깨짐') or '없음'} · 고쳐짐 {회.get('고쳐짐') or '없음'}")
        줄.append("  근거(제2의 뇌): " + (", ".join(d["댄근거"][:4]) if d.get("댄근거") else "없음 -- 참고 없이 낸 제안이다(정직히)")
                 + (f" · 탐색 범위를 {d['확장']}바퀴 넓혔다" if d.get("확장") else ""))
        줄.append("  붙이려면 `!자가개선 승인` · 아니면 `!자가개선 버림` (봇은 대신 승인하지 못한다)")
        줄.append("  diff:\n" + "\n".join("    " + x for x in d["diff"].splitlines()[:25]))
    else:
        줄.append("  " + 결과["남은것"])
    if 결과["메모"]:
        줄.append(f"  메모: {결과['메모']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="!자가개선 -- 탐색 -> 제안 -> 격리 시뮬 -> 동의 대기")
    ap.add_argument("--부탁", default="", help="사람이 말한 개선(!개선 <말>) -- 레포 전체 시뮬로 회귀를 본다")
    ap.add_argument("--임포트", action="store_true", help="깊은 임포트만 확인(plan·rehearsal -- 읽기 점검)")
    ap.add_argument("--틈만", action="store_true")
    ap.add_argument("--성능", action="store_true", help="틈과 무관하게 제2의 뇌로 적용거리를 찾는다")
    ap.add_argument("--승인", action="store_true")
    ap.add_argument("--버림", action="store_true")
    ap.add_argument("--상태", action="store_true")
    ap.add_argument("--몇", type=int, default=기본후보)
    ap.add_argument("--초", type=int, default=120)
    ap.add_argument("--자", action="store_true", help="eval/run 까지 돌려 후퇴 없음을 본다(모델 키 필요)")
    ap.add_argument("--좁게", action="store_true", help="레포 전체 시뮬을 건너뛴다(바뀐 파일의 검사만 -- 빠르지만 멀리서 깨진 것을 못 본다)")
    ap.add_argument("--배선", action="store_true", help="wire 읽기점검 끊김도 틈으로(느리다)")
    ap.add_argument("--점검", action="store_true", help="인수 검사(eval/acceptance) 실패 장면도 틈으로(느리다)")
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    repo = Path(a.저장소) if a.저장소 else None
    if a.임포트:
        from plan import store as _P            # noqa: F401 -- 이 임포트가 사고의 자리였다
        import rehearsal                        # noqa: F401
        from graph import ask                   # noqa: F401
        from sandbox import run as _SB          # noqa: F401
        print("improve 배선: plan · rehearsal · graph · sandbox 임포트 됨")
        return 0
    if a.부탁:
        r = 사용자개선(a.부탁, repo, 초=a.초, 전부=not a.좁게)
        print(부탁보고(r))
        return 0 if r["판정"] == "동의대기" else 1
    if a.성능:
        r = 성능개선(repo, 초=a.초, 전부=not a.좁게)
        print(부탁보고(r))
        return 0 if r["판정"] == "동의대기" else 1
    if a.틈만:
        틈들 = 틈모으기(repo, a.배선, a.점검)
        for g in 틈들:
            print(f"  [{g['종류']}] {g['무엇']}  <- {g['판정명령']}")
        print(f"  틈 {len(틈들)}개")
        return 0
    if a.승인:
        print(승인(repo)); return 0
    if a.버림:
        print(버림(repo)); return 0
    if a.상태:
        print(상태(repo)); return 0
    r = 자가개선(repo, 몇=a.몇, 초=a.초, 자=a.자, 배선=a.배선, 점검=a.점검, 전부=not a.좁게)
    print(보고(r))
    return 0 if r["돌았나"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
