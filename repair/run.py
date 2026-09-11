"""repair -- 문제는 하네스가 스스로 푼다. 사람에게는 남은 한 가지만.

사용자 규정(2026-09-11): "문제 생기면 -> tool 호출(dig 든 제2의 뇌든) -> sandbox 에서 시도
-> tool 호출 -> ... (loop) -> 문제 해결. 유저에게는 최소한의 요구만. 그리고 실패 이유들을
정리해서 기억에 넣고, 추후 night 로 압축해서 장기기억으로 남겨야지."

그것을 코드로 둔 루프다. 모델은 **제안만** 하고, 판정은 재현 명령의 끝값이 한다.

    재현 명령 (끝값 0 = 해결) + 증상(오류 문구)
      바퀴 1..N:
        1 실측   sandbox 에서 재현 명령 -> 끝값·꼬리. 0 이면 끝
        2 원인   제2의 뇌: dig/harvest 한 바퀴(증상) + graph 조회 -> 참고들
        3 제안   수리기(모델)에 증상·꼬리·참고·해 본 것을 주고 JSON 하나를 받는다
                 {"꼴": "패치"|"명령"|"사람", "패치": [{"파일","old","new"}], "명령": "...",
                  "왜": "...", "사람이_할_것": "..."}
        4 시도   패치: 작업 트리에 적용(toolgate 가 지키는 filetools.편집) -> sandbox 에서
                 재현 -> 실패면 되돌린다.  명령: sandbox 에서 `명령 && 재현` -> 통과면 진짜로
                 돌린다(toolgate.검사 뒤).  사람: 루프를 멈추고 그 한 가지를 남긴다
      끝:  repair/ledger.jsonl (바퀴마다) + public_agent_memory/<때>_고치기_<증상>.md
           (증상 · 해 본 것 · 판정 · 남은 것) -- graph/night 가 밤에 간추려 장기기억이 된다.
           dig/harvest --틈 은 해결 못 한 증상도 검색어로 삼는다.

쓰기:
    python3 repair/run.py --명령 'python3 mailer.py --진단' --증상 '5.7.8 Username and Password not accepted'
    python3 repair/run.py --명령 'python3 tests/test_x.py' --증상 'AssertionError ...' --바퀴 3
끝값: 0 해결 · 1 못 풀었다(남은 것을 적었다) · 3 못돌림(판 못 깜 · 모델 못 부름)
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import filetools  # noqa: E402
import toolgate  # noqa: E402
from sandbox import run as SB  # noqa: E402

원장상대 = "repair/ledger.jsonl"
메모곳 = "public_agent_memory"
기본바퀴 = 3
최대바퀴 = 5          # 사용자 규정: 3~5 바퀴에서 멈춘다 -- 무한 루프는 없다
꼬리글자 = 1500

제안기 = None      # 검사 주입: (prompt) -> str(JSON).  None 이면 router 수리기
모으기 = None      # 검사 주입: (증상) -> list[str].   None 이면 dig/harvest + graph/ask


# ---------------------------------------------------------------- 원인 모으기 (제2의 뇌)
진단기 = None      # 검사 주입: (글, repo) -> dict. None 이면 diagnose.진단


def _진단기본(글: str, repo=None) -> dict:
    try:
        import diagnose
        return diagnose.진단(글, repo)
    except Exception as e:                                        # noqa: BLE001
        return {"증상": {}, "증거": [], "가설": [], "말": f"진단을 못 돌렸다: {type(e).__name__}"}


def _핵심(증상: str) -> str:
    """오류 문구에서 검색어가 될 만한 조각 -- 경로·해시·수는 빼고 낱말만."""
    말 = re.findall(r"[A-Za-z][A-Za-z0-9._-]{2,}|[가-힣]{2,}", 증상 or "")
    빼 = {"file", "line", "most", "recent", "call", "last", "traceback", "error", "in"}
    말 = [m for m in 말 if m.lower() not in 빼 and not m.startswith(("/", "http"))]
    return " ".join(dict.fromkeys(말))[:120]


def _모으기기본(증상: str) -> "list[str]":
    핵심 = _핵심(증상)
    if not 핵심:
        return []
    try:
        from dig import harvest
        from graph import ask
        harvest.한바퀴([핵심], 몇=3, 상한=4)
        return [f"{n.get('요약', '')[:220]} <{n.get('출처', '')}>" for _, n in ask.찾기(핵심, 최대=4)]
    except Exception as e:                                        # noqa: BLE001
        return [f"(제2의 뇌를 못 물었다: {type(e).__name__})"]


# ---------------------------------------------------------------- 제안
def 프롬프트(명령: str, 증상: str, 꼬리: str, 참고: "list[str]", 해본: "list[dict]") -> str:
    줄 = ["[고치기 루프 -- 너는 제안만 한다. 판정은 아래 재현 명령의 끝값이 한다]",
         f"재현 명령: {명령}", f"증상: {증상}", "", "[방금 실측한 꼬리]", 꼬리[-꼬리글자:] or "(없음)"]
    if 참고:
        줄 += ["", "[제2의 뇌에서 찾은 참고 -- 맞는 것만 써라]"] + [f"- {x}" for x in 참고]
    if 해본:
        줄 += ["", "[이미 해 본 것 -- 같은 것을 또 내지 마라]"]
        for h in 해본:
            줄.append(f"- 바퀴 {h['바퀴']}: {h['꼴']} {h.get('요약', '')[:120]} -> {h['판정']}")
    줄 += ["", "[답 규약] JSON 하나만 내라. 설명은 JSON 밖에 두지 마라.",
          '{"꼴": "패치", "패치": [{"파일": "상대경로", "old": "정확히 한 번 나오는 원문", "new": "바꿀 글"}], "왜": "..."}',
          '{"꼴": "명령", "명령": "셸 한 줄 (설치·설정 등)", "왜": "..."}',
          '{"꼴": "사람", "사람이_할_것": "코드로는 안 되는 딱 한 가지 (비밀번호·계정·결제)", "왜": "..."}',
          '{"꼴": "입력", "틀린것": "SMTP_APP_PASSWORD", "왜": "16자 영문이 아니다 -- 계정 비밀번호를 준 듯", '
          '"다시_달라": "!열쇠 SMTP_APP_PASSWORD=<앱 비밀번호 16자>"}',
          "코드로 할 수 있는 것을 사람에게 넘기지 마라. 이미 해 본 것을 다시 내지 마라. "
          "**주어진 정보(비밀번호·주소·경로·키)가 틀렸다고 판단되면 '입력' 으로 그렇다고 말하라** -- "
          "그것은 네 실패가 아니라 이용자 측 과실이고, 되풀이 시도는 낭비다."]
    return "\n".join(줄)


def _제안기본(prompt: str) -> str:
    from router import call as R
    return R.부르기("수리기", prompt)["답"]


def 해석(답: str) -> "dict | None":
    m = re.search(r"\{.*\}", 답 or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("꼴") not in ("패치", "명령", "사람", "입력"):
        return None
    if d["꼴"] == "입력" and not (str(d.get("틀린것", "")).strip() and str(d.get("다시_달라", "")).strip()):
        return None
    if d["꼴"] == "패치" and not (isinstance(d.get("패치"), list) and d["패치"]):
        return None
    if d["꼴"] == "명령" and not str(d.get("명령", "")).strip():
        return None
    if d["꼴"] == "사람" and not str(d.get("사람이_할_것", "")).strip():
        return None
    return d


# ---------------------------------------------------------------- 실측 · 시도
def 실측(명령: str, repo=None, 초: int = 120) -> dict:
    r = SB.실행(["bash", "-lc", 명령], 지금트리=True, 초=초, repo=repo)
    꼬리 = ((r.get("stdout") or "") + (r.get("stderr") or "")).strip()
    return {"끝값": r["끝값"], "돌았나": r["돌았나"], "꼬리": "\n".join(꼬리.splitlines()[-30:])[-꼬리글자:],
            "메모": r.get("메모", "")}


def 패치적용(패치들: "list[dict]", repo=None) -> "tuple[list[tuple[str, str, str]], str]":
    """적용한 (파일, old, new) 목록과 거절 까닭. 하나라도 거절이면 앞의 것을 되돌린다."""
    적용 = []
    for p in 패치들:
        파일, old, new = str(p.get("파일", "")), str(p.get("old", "")), str(p.get("new", ""))
        try:
            toolgate.경로풀기(파일, 쓰기=True, repo=repo)
            filetools.편집(파일, old, new, repo=repo)      # 실패면 ValueError -- 성공은 예외 없음
        except (ValueError, OSError) as e:
            되돌리기(적용, repo)
            return [], f"{파일}: {str(e)[:120]}"
        적용.append((파일, old, new))
    return 적용, ""


def 되돌리기(적용: "list[tuple[str, str, str]]", repo=None) -> None:
    for 파일, old, new in reversed(적용):
        try:
            filetools.편집(파일, new, old, repo=repo)
        except (ValueError, OSError):
            pass


def 시도(제안: dict, 명령: str, repo=None, 초: int = 120) -> dict:
    """제안을 격리해서 해 보고 판정한다. {"판정": "해결"|"실패"|"거절"|"사람", "요약", "꼬리"}."""
    if 제안["꼴"] == "사람":
        return {"판정": "사람", "요약": 제안["사람이_할_것"][:200], "꼬리": ""}
    if 제안["꼴"] == "입력":
        return {"판정": "입력오류",
                "요약": f"{제안['틀린것']} -- {str(제안.get('왜', ''))[:100]} -> {제안['다시_달라']}"[:240], "꼬리": ""}
    if 제안["꼴"] == "패치":
        적용, 까닭 = 패치적용(제안["패치"], repo)
        if 까닭:
            return {"판정": "거절", "요약": f"패치 거절 -- {까닭}", "꼬리": ""}
        r = 실측(명령, repo, 초)
        요약 = "패치 " + ", ".join(f"{f}" for f, _, _ in 적용)
        if r["끝값"] == 0 and r["돌았나"]:
            return {"판정": "해결", "요약": 요약, "꼬리": r["꼬리"]}
        되돌리기(적용, repo)
        return {"판정": "실패", "요약": 요약 + " (되돌림)", "꼬리": r["꼬리"]}
    cmd = str(제안["명령"]).strip()
    막힘 = toolgate.검사(cmd)
    if 막힘:
        return {"판정": "거절", "요약": f"명령 거절 -- {막힘[:100]}", "꼬리": ""}
    r = 실측(f"{cmd} && {명령}", repo, 초)
    if r["끝값"] == 0 and r["돌았나"]:
        # 격리 판에서 통과 -> 진짜 트리에서 그 명령을 돌린다 (설치·설정은 판에 안 남는다)
        try:
            p = subprocess.run(["bash", "-lc", cmd], cwd=str(repo or REPO), capture_output=True,
                               text=True, errors="replace", timeout=초)
            진짜 = 실측(명령, repo, 초)
            if p.returncode == 0 and 진짜["끝값"] == 0:
                return {"판정": "해결", "요약": f"명령 {cmd[:100]}", "꼬리": 진짜["꼬리"]}
            return {"판정": "실패", "요약": f"명령 {cmd[:100]} (판에선 됐는데 진짜에선 {p.returncode}/{진짜['끝값']})",
                    "꼬리": 진짜["꼬리"]}
        except (subprocess.TimeoutExpired, OSError) as e:
            return {"판정": "실패", "요약": f"명령 {cmd[:100]} ({type(e).__name__})", "꼬리": ""}
    return {"판정": "실패", "요약": f"명령 {cmd[:100]}", "꼬리": r["꼬리"]}


# ---------------------------------------------------------------- 원장 · 기억
def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


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


def 미해결증상들(repo=None) -> "list[str]":
    """끝 줄이 '못 풀었다' 인 증상들 -- dig/harvest --틈 이 검색어로 삼는다."""
    마지막: dict = {}
    for r in 원장읽기(repo):
        if r.get("꼴") == "끝":
            마지막[r.get("증상", "")] = r.get("해결", False)
    return [s for s, 됐 in 마지막.items() if s and not 됐]


def 기억쓰기(증상: str, 명령: str, 해본: "list[dict]", 해결: bool, 남은: str, repo=None) -> str:
    """public_agent_memory 에 메모 -- graph/night 가 밤에 간추려 장기기억으로 남긴다."""
    repo = Path(repo or REPO)
    때 = time.strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", 증상)[:40].strip("_") or "증상"
    p = repo / 메모곳 / f"{때}_고치기_{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = ["---", f"topic: '고치기: {증상[:60]}'", "---", "",
         f"# 고치기 루프 -- {증상[:80]}", "", f"재현 명령: `{명령}`", "",
         "## 해 본 것"]
    for h in 해본:
        줄.append(f"{h['바퀴']}. [{h['꼴']}] {h.get('요약', '')} -> **{h['판정']}**"
                 + (f" -- {h.get('왜', '')[:160]}" if h.get("왜") else ""))
        if h.get("꼬리"):
            줄.append("   " + h["꼬리"].splitlines()[-1][:160])
    줄 += ["", "## 판정", ("해결됐다" if 해결 else "못 풀었다") + f" (바퀴 {len(해본)})"]
    if 남은:
        줄 += ["", "## 남은 것 (사람만 할 수 있는 한 가지)", 남은]
    줄 += ["", "## 다음에 같은 증상이면", "위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라."]
    p.write_text("\n".join(줄) + "\n", encoding="utf-8")
    return str(p.relative_to(repo))


# ---------------------------------------------------------------- 루프
def 고치기(명령: str, 증상: str, repo=None, 바퀴: int = 기본바퀴, 초: int = 120,
         증거글: str = "") -> dict:
    """`증거글` 은 **실제로 터진 자리의 트레이스백**(로그 꼬리)이다.

    격리 판에서 재현이 안 되는 사고가 있다 -- 낡은 판이 배포돼 터진 경우가 바로 그렇다
    (여기 트리는 최신이니 재현이 안 된다). 그때도 **로그에 적힌 줄번호**는 진실을 말한다.
    그래서 재현 꼬리 말고 원래 글을 따로 받는다."""
    repo = Path(repo or REPO)
    시작 = time.monotonic()
    바퀴 = max(1, min(int(바퀴), 최대바퀴))
    해본: list[dict] = []
    결과 = {"해결": False, "돌았나": True, "바퀴": 0, "해본것": 해본, "남은것": "", "메모": "", "걸린초": 0.0}
    첫 = 실측(명령, repo, 초)
    if not 첫["돌았나"]:
        결과.update(돌았나=False, 남은것=f"판을 못 깔았다: {첫['메모']}")
        return 결과
    if 첫["끝값"] == 0:
        결과.update(해결=True, 남은것="")
        결과["메모"] = "이미 끝값 0 -- 고칠 것이 없다"
        return 결과
    꼬리 = 첫["꼬리"]
    # **모델에게 묻기 전에 저장소에서 증거를 캔다.** 사용자(2026-09-11): "왜 나의 에이전트는
    # 이런 식의 사고과정을 거치면서 스스로 해결하지 못하는거야?"
    #
    # 같은 자리에서 두 번 막혔을 때 사람이 실제로 한 일은 모델에게 묻는 것이 아니었다 --
    # 트레이스백의 줄번호를 옛 커밋과 맞춰 보고 **도는 코드가 낡았다**는 것을 알아냈다.
    # 그건 저장소에 적혀 있는 사실이고 모델이 필요 없다. 그래서 먼저 캔다.
    #
    # 두 가지가 달라진다: (1) 결정적 가설이 서면 **모델이 없어도** 답을 낸다(키가 없을 때가
    # 바로 도움이 가장 필요한 때다), (2) 모델에게 물을 때도 증거를 들려 보낸다.
    진 = (진단기 or _진단기본)((증거글 or "") + "\n" + 꼬리 + "\n" + (증상 or ""), repo)
    결과["진단"] = 진
    참고 = [f"[진단] {h['무엇']} -> {h['고칠거리']}" for h in 진.get("가설", [])]
    참고 += (모으기 or _모으기기본)(증상 or 꼬리)
    if 진.get("가설"):
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "진단",
                    "증상": 증상, "가설": [h["탐침"] for h in 진["가설"]],
                    "첫가설": 진["가설"][0]["고칠거리"][:160]})
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "시작", "증상": 증상,
                "명령": 명령, "참고수": len(참고)})
    for n in range(1, 바퀴 + 1):
        결과["바퀴"] = n
        try:
            답 = (제안기 or _제안기본)(프롬프트(명령, 증상, 꼬리, 참고, 해본))
        except Exception as e:                                    # noqa: BLE001
            # **모델을 못 불러도 빈손으로 물러나지 않는다.** 결정적 진단이 섰으면 그것을
            # 답으로 낸다 -- 실측 2026-09-11: 키가 없다는 이유로 "제안없음" 만 내고,
            # 심지어 그 탓을 사람에게 돌렸다("주어진 정보가 틀렸다(이용자 측)").
            if 진.get("가설"):
                결과.update(돌았나=True, 남은것=(
                    "모델을 못 불렀지만 **저장소가 답했다**: " + 진["가설"][0]["고칠거리"]
                    + (f"\n  근거: {진['가설'][0]['무엇'][:160]}")
                    + (f"\n  확인: {진['가설'][0]['판정명령']}" if 진["가설"][0]["판정명령"] else "")))
                결과["진단만"] = True
            else:
                결과.update(돌았나=False, 남은것=f"수리기를 못 불렀다: {type(e).__name__}: {str(e)[:100]}")
            break
        제안 = 해석(답)
        if 제안 is None:
            h = {"바퀴": n, "꼴": "깨진제안", "요약": (답 or "")[:120], "판정": "거절", "왜": "JSON 꼴이 아니다"}
        else:
            r = 시도(제안, 명령, repo, 초)
            h = {"바퀴": n, "꼴": 제안["꼴"], "요약": r["요약"], "판정": r["판정"],
                 "왜": str(제안.get("왜", ""))[:200], "꼬리": r.get("꼬리", "")}
            꼬리 = r.get("꼬리") or 꼬리
        # **같은 제안을 되풀이하면 멈춘다** -- 바퀴가 남았어도 더 가 봐야 같은 실패다.
        if h["판정"] not in ("해결",) and any(x.get("요약") == h.get("요약") and x["꼴"] == h["꼴"] for x in 해본):
            h["판정"] = "반복"
        해본.append(h)
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "바퀴", "증상": 증상,
                    "바퀴": h["바퀴"], "제안꼴": h["꼴"], "요약": h.get("요약", ""), "판정": h["판정"],
                    "왜": h.get("왜", "")})
        if h["판정"] == "해결":
            결과["해결"] = True
            break
        if h["판정"] == "사람":
            결과["남은것"] = h["요약"]
            break
        if h["판정"] == "입력오류":
            # **사람 탓으로 돌리기 전에 증거가 있어야 한다.** 실측 2026-09-11: 모델이
            # "주어진 정보가 틀렸다(이용자 측) -- GEMINI_API_KEY 가 없다. 발급받아 넣어라"
            # 라고 했는데, 키는 .env 에 **다른 이름으로 있었다.** 있는 것을 없다고 하고
            # 그 탓을 사람에게 돌린 것이다. 진단이 설명을 내놓았으면 그쪽이 이긴다 --
            # 모델의 단정보다 저장소가 말해 준 사실이 앞선다.
            if 진.get("가설"):
                결과["남은것"] = ("모델은 '이용자 측' 이라 했지만 **저장소가 다르게 말한다**: "
                              + 진["가설"][0]["고칠거리"]
                              + f"\n  근거: {진['가설'][0]['무엇'][:160]}")
                결과["진단이_뒤집음"] = True
            else:
                결과["남은것"] = "주어진 정보가 틀렸다 (이용자 측) -- " + h["요약"]
                결과["입력오류"] = True
            break
        if h["판정"] == "반복":
            결과["남은것"] = (f"같은 제안을 되풀이한다 -- 코드로는 더 못 간다 (바퀴 {n}). "
                          f"마지막 꼬리: {꼬리.splitlines()[-1][:120] if 꼬리 else '(없음)'}")
            break
    if not 결과["해결"] and not 결과["남은것"]:
        결과["남은것"] = f"{len(해본)}바퀴를 다 해 봤다 -- 마지막 꼬리: {꼬리.splitlines()[-1][:120] if 꼬리 else '(없음)'}"
    결과["메모"] = 기억쓰기(증상, 명령, 해본, 결과["해결"], 결과["남은것"], repo)
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "꼴": "끝", "증상": 증상,
                "해결": 결과["해결"], "바퀴": 결과["바퀴"], "남은것": 결과["남은것"][:200], "메모": 결과["메모"]})
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    return 결과


def 보고(결과: dict) -> str:
    줄 = []
    진 = 결과.get("진단") or {}
    if 진.get("가설"):
        줄.append(f"  진단(모델 안 씀) {len(진['가설'])}가지 -- 앞엣것부터:")
        for i, h in enumerate(진["가설"][:3], 1):
            줄.append(f"    {i}. {h['고칠거리'][:110]}")
            줄.append(f"       근거: {h['무엇'][:110]}")
    if not 결과.get("돌았나", True):
        줄.append(f"  못돌림 -- {결과['남은것']}")
        return "\n".join(줄)
    for h in 결과["해본것"]:
        줄.append(f"  바퀴 {h['바퀴']} [{h['꼴']}] {h.get('요약', '')[:90]} -> {h['판정']}")
    if 결과["해결"]:
        줄.append(f"  **해결** (바퀴 {결과['바퀴']}) · 기억: {결과['메모']}")
    elif 결과.get("진단이_뒤집음"):
        줄.append(f"  **모델의 '이용자 측' 판정을 진단이 뒤집었다** (바퀴 {결과['바퀴']}) · 기억: {결과['메모']}")
        줄.append(f"  {결과['남은것']}")
    elif 결과.get("진단만"):
        줄.append(f"  모델은 못 불렀지만 **저장소가 답했다** · 기억: {결과['메모']}")
        줄.append(f"  {결과['남은것']}")
    elif 결과.get("입력오류"):
        줄.append(f"  **주어진 정보가 틀렸다 (이용자 측)** -- 되풀이하지 않고 멈췄다 (바퀴 {결과['바퀴']}) · 기억: {결과['메모']}")
        줄.append(f"  고쳐 달라: {결과['남은것'].split(' -> ', 1)[-1]}")
    else:
        줄.append(f"  못 풀었다 (바퀴 {결과['바퀴']}) · 기억: {결과['메모']}")
        줄.append(f"  남은 한 가지: {결과['남은것']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="문제를 스스로 푼다 -- 실측·원인·시도 루프")
    ap.add_argument("--명령", required=True, help="재현 명령 (끝값 0 이면 해결)")
    ap.add_argument("--증상", default="", help="오류 문구")
    ap.add_argument("--증거", default="", help="터진 자리의 트레이스백이 든 로그 파일 (재현이 안 되는 사고용)")
    ap.add_argument("--바퀴", type=int, default=기본바퀴, help=f"최대 {최대바퀴} -- 무한 루프는 없다")
    ap.add_argument("--초", type=int, default=120)
    ap.add_argument("--저장소", default="", help="다른 git 저장소에서 (검사용 -- 감사는 git 아닌 사본에서 돈다)")
    args = ap.parse_args()
    증거 = ""
    if args.증거:
        try:
            증거 = Path(args.증거).read_text(encoding="utf-8", errors="replace")[-8000:]
        except OSError as e:
            print(f"증거 파일을 못 읽었다: {e}")
    r = 고치기(args.명령, args.증상, repo=args.저장소 or None, 바퀴=args.바퀴, 초=args.초, 증거글=증거)
    print(보고(r))
    if not r["돌았나"]:
        return 3
    return 0 if r["해결"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
