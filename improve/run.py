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
import re
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


def 해석(답: str) -> "dict | None":
    """답에서 JSON 하나를 뽑아 이 자리의 꼴로 검사한다. repair.해석 은 repair 의 꼴("패치" 목록)을
    강제하므로 그대로 못 쓴다 -- 여기 꼴은 "편집"/"새파일" 이다(실측: 재사용했더니 전부 '제안없음')."""
    m = re.search(r"\{.*\}", 답 or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
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


# ---------------------------------------------------------------- 사용자가 말한 개선 (!개선 <말>)
def _관련파일찾기(말: str, repo: Path, 몇: int = 4) -> "list[str]":
    """부탁의 낱말로 저장소 .py 를 점수 매겨 고른다. 이름 맞음 3점 · 본문 등장 1점(앞 400줄)."""
    낱말 = [w.lower() for w in re.split(r"[^0-9A-Za-z가-힣_./]+", 말 or "") if len(w) >= 2][:12]
    if not 낱말:
        return []
    점수: dict = {}
    for f in repo.rglob("*.py"):
        rel = str(f.relative_to(repo))
        if any(x in rel.split("/") for x in (".git", "venv", "__pycache__", "tests", "inbox", "node_modules")):
            continue
        if not f.is_file() or f.stat().st_size > 400_000:
            continue
        s_ = 0
        낮 = rel.lower()
        for w in 낱말:
            if w in 낮:
                s_ += 3
        try:
            본 = "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[:400]).lower()
        except OSError:
            continue
        for w in 낱말:
            if w in 본:
                s_ += 1
        if s_:
            점수[rel] = s_
    return [k for k, _ in sorted(점수.items(), key=lambda kv: -kv[1])[:몇]]


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
        "- old 는 글자 그대로, 정확히 한 번만. 없거나 두 번이면 거절된다.\n"
        "- **검사를 지우거나 assert 를 빼지 마라.** 새 기능이면 tests/test_<이름>.py 를 새파일로 같이 지어라.\n"
        "- gates/ · .env · 판정 원장(*.jsonl) 은 못 만진다.\n"
        "- 레포 전체 검사가 돌아간다 -- **다른 데를 깨뜨리면 거절된다.** 좁게 고쳐라.\n"
        "- 못 하겠으면 {\"꼴\": \"사람\", \"사람이_할_것\": \"...\"}.\n"
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
        "확장": 0, "파일들": [], "회귀": None}
    if not 말:
        r.update(판정="빈부탁", 말="무엇을 개선할지 한 줄로 적어라 -- `!개선 <말>`")
        return r
    if P.현재판(repo) is not None:
        r.update(판정="판열림", 말="계획판이 이미 켜져 있다 -- `!계획 승인/버림` 으로 먼저 끝내라(한 번에 하나)")
        return r
    _적기(repo, {"꼴": "부탁", "말": 말[:300]})

    근거 = 근거모으기({"무엇": 말, "왜": "사람이 말한 개선", "종류": "부탁"}, repo)
    r["근거"] = [f"{x['출처']}#{x['해시']}" for x in 근거["참고"]]
    r["확장"] = 근거["확장"]
    r["파일들"] = _관련파일찾기(말, repo)
    try:
        답 = (제안기 or _제안기본)(부탁프롬프트(말, repo, 근거, r["파일들"]))
    except Exception as e:                             # noqa: BLE001
        r.update(판정="제안없음", 말=f"제안기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}")
        return r
    제안 = 해석(답)
    if not 제안 or 제안.get("꼴") != "패치":
        r.update(판정="제안없음", 말=(제안 or {}).get("사람이_할_것") or "패치 꼴의 답이 아니다")
        return r
    r["왜"] = str(제안.get("왜", ""))[:200]
    r["댄근거"] = [str(x) for x in (제안.get("근거") or [])][:6]

    P.켜기(f"자가개선: [부탁] {말[:80]}", repo=repo, 누가="개선")
    판 = P.현재판(repo)
    if 판 is None:
        r.update(판정="판못깜", 말="그림자를 못 꺼냈다")
        return r
    ok, 적용말 = 적용(제안, 판)
    if not ok:
        P.버림(repo)
        r.update(판정="적용실패", 말=적용말)
        return r

    시험보고 = P.시험하기(repo, 초=초, 전부=전부, 전부초=전부초)
    st = P.읽기(repo) or {}
    시 = st.get("시험") or {}
    r["회귀"] = 시.get("회귀")
    if not 시.get("통과"):
        P.버림(repo)
        r.update(판정="시뮬빨강", 말=시험보고[-600:])
        return r
    r.update(판정="동의대기", id=st.get("id", ""), diff=P.보기(repo)[:1500],
             말=("레포 전체 시뮬 초록(회귀 없음) -- **사람의 동의를 기다린다** (`!개선 승인`)"))
    _적기(repo, {"꼴": "부탁끝", "말": 말[:200], "판정": r["판정"], "id": r["id"], "근거": r["근거"],
               "댄근거": r["댄근거"], "확장": r["확장"], "회귀": r["회귀"]})
    return r


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
    try:
        답 = (제안기 or _제안기본)(프롬프트(틈, 전꼬리, repo, 근거))
    except Exception as e:                             # noqa: BLE001
        r.update(판정="제안없음", 말=f"제안기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}")
        return r
    제안 = 해석(답)
    if not 제안 or 제안.get("꼴") != "패치":
        r.update(판정="제안없음", 말=(제안 or {}).get("사람이_할_것") or "패치 꼴의 답이 아니다")
        return r
    r["왜"] = str(제안.get("왜", ""))[:200]
    r["댄근거"] = [str(x) for x in (제안.get("근거") or [])][:6]

    켜 = P.켜기(f"자가개선: [{틈['종류']}] {틈['무엇']}", repo=repo, 누가="자가개선")
    판 = P.현재판(repo)
    if 판 is None:
        r.update(판정="판못깜", 말=켜)
        return r
    ok, 말 = 적용(제안, 판)
    if not ok:
        P.버림(repo)
        r.update(판정="적용실패", 말=말)
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
    if P.현재판(repo) is not None:
        결과.update(돌았나=False, 남은것="계획판이 이미 켜져 있다 -- 사람이 `!계획 승인/버림` 으로 먼저 끝내라(한 번에 하나)")
        return 결과
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
