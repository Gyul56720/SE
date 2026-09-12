"""investigate -- **긴 호흡으로 끝까지 판다.** 한 턴이 아니라 한 시간.

사용자(2026-09-12): "저렇게 50분~1시간이 걸리더라도 문제를 해결했으면 좋겠어. 아주 긴
템포지만, 계속해서 문제를 해결하는 것. 다양한 도구를 가지고. 똑같이 따라해도 좋아."

'저렇게' 는 사람이 한 것이다: 증거를 읽고 -> 가설을 세우고 -> **끝값으로** 확인하고 ->
고치고 -> 검사·게이트·감사를 돌리고 -> 빨강이면 다시 -> 초록이면 커밋·PR. 한 바퀴가
아니라 될 때까지. 도구 수십 번.

봇의 두뇌(`run_admin_agent`)는 **한 턴짜리**다. 답하고 멈춘다. `repair` 는 세 바퀴다.
그래서 바깥에 루프를 하나 더 둔다. 두뇌를 갈아 끼우지 않는다 -- 두뇌는 그대로 두고,

  · **끝은 코드가 정한다.** 두뇌가 "됐다" 고 해도 판정 명령(재현·게이트·감사)이 전부
    끝값 0 이 아니면 안 끝난다. 이 저장소의 규율이다: 검사하지 않은 초록불은 없다.
  · **바퀴마다 증거를 새로 캔다.** diagnose(모델 안 씀)가 앞에 선다 -- 도는 코드가
    낡았는지, 머지를 안 했는지, 모듈이 저장소 안에 있는지.
  · **되풀이를 센다.** 판정 결과와 diff 가 두 바퀴 같으면 '갈래를 바꿔라' 를 넣고, 세
    바퀴 같으면 멈춘다. 같은 실패를 한 시간 반복하는 것은 끈기가 아니다.
  · **시한은 사람이 준다.** 기본 한 시간. 넘으면 해 본 것과 남은 것을 적고 멈춘다.
  · 해결되면 마무리 턴 하나 -- 커밋·밀기·PR. **머지는 사람이 누른다**(저장소 규칙).

    python3 -m investigate.run --증상 "ModuleNotFoundError: No module named 'plan'" --증거 logs/improve.log
    python3 -m investigate.run --증상 "..." --명령 "python3 tests/test_x.py" --시한 3600
끝값: 0 해결 · 1 못 풀었다(적었다) · 3 못돌림(두뇌를 못 불렀다)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 스크립트로 돌 때 sys.path[0] 은 investigate/ 다 -- 뿌리가 아니다 (improve/run.py 의 사고).
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

기본시한초 = 3600
기본최대바퀴 = 40
되풀이한도 = 3          # 판정·diff 가 이만큼 연속 같으면 멈춘다

두뇌 = None     # 검사 주입: (prompt, thread_id) -> str.  None 이면 봇의 run_admin_agent
판정기 = None   # 검사 주입: (repo, 재현명령) -> list[dict{"이름","끝값","꼬리"}]
진단기 = None   # 검사 주입: (글, repo) -> dict.  None 이면 diagnose.진단


# ------------------------------------------------------------------ 두뇌·판정 기본
def _두뇌기본(prompt: str, thread_id: str) -> str:
    """봇의 관리 에이전트(도구 전권) 한 턴. 봇 모듈은 여기서만, 늦게 들인다 --
    Discord 토큰이 없는 기계(검사)에서는 못 들이므로 그때는 못돌림이다."""
    import discord_bot_server as B          # noqa: WPS433 -- 무거워서 늦게
    return B.run_admin_agent(prompt, thread_id)


_claude세션: "set[str]" = set()
claude실행기 = None   # 검사 주입: (argv, cwd, 초) -> (끝값, 출력)


def _두뇌claude(prompt: str, thread_id: str, repo=None) -> str:
    """`claude -p` 한 턴. 봇의 두뇌(Gemini)를 못 쓰는 기계에서, 또는 사람이 고를 때.

    같은 조사는 같은 세션이다 -- 첫 턴은 `--session-id`, 그 뒤는 `--resume` 으로 기억을 잇는다
    (discord_bot_server.run_claude 와 같은 꼴). 권한은 bypass -- 도구 게이트는 저장소 쪽
    (toolgate · gatekeeper · commit_guard)이 지킨다."""
    import uuid as _u
    repo = Path(repo or REPO)
    sid = str(_u.uuid5(_u.NAMESPACE_URL, f"investigate-{thread_id}"))
    잇기 = ["--resume", sid] if sid in _claude세션 else ["--session-id", sid]
    # **root 에서는 권한 우회를 못 쓴다.** 실측 2026-09-12: 첫 실제 조사가 세 바퀴 내내
    # "--dangerously-skip-permissions cannot be used with root/sudo privileges" 만 받았다.
    # 그때는 허용 도구를 이름으로 준다(탐침으로 확인: Bash 가 돈다). VM 은 systemd-run
    # --uid=ubuntu 로 띄우므로(run_claude) root 가 아니고 우회가 된다. 기계 이름이 아니라
    # **누구로 도는가**로 가른다.
    if _루트인가():
        # 한 문자열로 준다. `--allowedTools <tools...>` 는 가변 인자라 뒤에 오는 것을 전부
        # 도구 이름으로 삼킨다 -- 실측 2026-09-12: 프롬프트가 도구 이름으로 먹혀
        # "Input must be provided" 로 죽었다(탐침은 프롬프트를 앞에 둬서 통과했었다).
        권한 = ["--permission-mode", "acceptEdits",
              "--allowedTools", "Bash,Edit,Write,Read,Glob,Grep,MultiEdit"]
    else:
        권한 = ["--permission-mode", "bypassPermissions"]
    # **프롬프트가 깃발보다 앞이다.** 가변 인자 깃발 뒤에 두면 삼켜진다.
    argv = ["claude", "-p", prompt, *잇기, *권한]
    rc, out = (claude실행기 or (lambda a, c, t: _돌리기(a, c, t)))(argv, repo, 1800)
    # **끝값이 0 이 아니면 그 출력은 답이 아니라 오류다.** 실측: 오류 문구를 답으로 넘겨서
    # 루프가 그것을 세 바퀴 '두뇌의 말' 로 적었다. 올려서 못돌림으로 적히게 한다.
    if rc != 0:
        raise RuntimeError(f"claude -p 끝값 {rc}: {out.strip()[-200:] or '(출력 없음)'}")
    _claude세션.add(sid)
    return out


def _루트인가() -> bool:
    import os
    try:
        return os.geteuid() == 0
    except AttributeError:      # 윈도우
        return False


def _돌리기(argv: "list[str]", repo: Path, 초: int, env: "dict | None" = None) -> "tuple[int, str]":
    try:
        p = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True, errors="replace", timeout=초,
                           stdin=subprocess.DEVNULL, env=env)      # claude -p 가 stdin 을 3초 기다린다
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 124, f"시간 초과 ({초}초)"
    except OSError as e:
        return 127, f"{type(e).__name__}: {e}"


def _판정기본(repo: Path, 재현명령: str = "") -> "list[dict]":
    """끝을 정하는 명령들. **전부 끝값 0 이어야 끝이다.** 두뇌의 말은 여기 없다."""
    표 = []
    if 재현명령:
        표.append(("재현", ["bash", "-lc", 재현명령], 600))
    표.append(("게이트", ["python3", "gatekeeper.py"], 900))
    표.append(("감사", ["python3", "audit/run.py", "--커밋"], 1200))
    import os
    # 재현 명령(특히 목표 모드가 지은 tests/test_목표_*.py)이 뿌리 모듈을 임포트할 수 있게 뿌리를
    # PYTHONPATH 에 둔다. 저장소 검사들은 제 손으로 뿌리를 넣지만, 두뇌가 방금 지은 검사는 안 그럴 수
    # 있다 -- 그 한 줄 때문에 기능이 다 됐는데 빨강이 되면 판정이 거짓말이다.
    env = {**os.environ, "PYTHONPATH": str(repo) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")}
    out = []
    for 이름, argv, 초 in 표:
        rc, 꼬리 = _돌리기(argv, repo, 초, env=env)
        out.append({"이름": 이름, "끝값": rc, "꼬리": "\n".join(꼬리.splitlines()[-8:])})
    return out


def _diff지문(repo: Path) -> str:
    rc, out = _돌리기(["git", "diff", "HEAD", "--stat"], repo, 60)
    rc2, head = _돌리기(["git", "rev-parse", "HEAD"], repo, 30)
    return hashlib.sha1((out + head).encode("utf-8", "replace")).hexdigest()[:12]


# ------------------------------------------------------------------ 프롬프트
def 프롬프트(증상: str, 진: dict, 판정: "list[dict]", 해본: "list[dict]", 바퀴: int, 남은초: float,
          되풀이: int, 재현명령: str) -> str:
    빨강 = [p for p in 판정 if p["끝값"] != 0]
    줄 = [f"[조사 바퀴 {바퀴} · 남은 시간 {int(남은초 // 60)}분] **끝까지 판다. 판정은 끝값이 한다.**",
         f"증상: {증상}",
         "",
         "지금 빨강인 판정 (이것들이 전부 끝값 0 이 되어야 끝난다):"]
    for p in 빨강:
        줄.append(f"  · {p['이름']} 끝값 {p['끝값']}")
        줄 += [f"      {x}" for x in p["꼬리"].splitlines()[-6:]]
    if not 빨강:
        줄.append("  (없음)")
    if 진.get("가설"):
        줄.append("")
        줄.append("저장소가 캔 증거 (모델 안 씀 -- 이것부터 믿어라):")
        for i, h in enumerate(진["가설"][:4], 1):
            줄.append(f"  {i}. {h['무엇'][:200]}")
            줄.append(f"     -> {h['고칠거리'][:200]}")
            if h.get("판정명령"):
                줄.append(f"     확인: {h['판정명령']}")
    if 해본:
        줄.append("")
        줄.append("지난 바퀴에 해 본 것 (같은 것을 되풀이하지 마라):")
        for h in 해본[-4:]:
            줄.append(f"  바퀴 {h['바퀴']}: {h['요약'][:160]}  -> 빨강 {h['빨강']}")
    if 되풀이 >= 2:
        줄.append("")
        줄.append("**두 바퀴째 아무것도 안 바뀌었다.** 같은 갈래는 막혔다. 다른 가설로 가라: "
                  "증거를 다시 읽어라(트레이스백 줄번호를 `git log -L`·`git show` 로 옛 판과 맞춰 보라), "
                  "`python3 -m diagnose --글 '<트레이스백>'` · `python3 impact.py --파일 <파일>` · "
                  "`python3 dig/harvest.py --틈` 으로 제2의 뇌를 열어라. 고치는 자리를 바꿔라 -- "
                  "파일 안이 아니라 부르는 쪽, 코드가 아니라 배포·머지·부르는 꼴일 수 있다.")
    줄 += ["",
           "이렇게 하라 -- 사람이 하듯이, 한 호흡에, 도구를 몇 번이든:",
           "  1. 가설을 하나 세우고, 그것을 **끝값으로 확인할 명령**을 먼저 돌려라. 추측을 말로 하지 마라.",
           "  2. 확인되면 고쳐라 (edit_file -- 바꿀 줄만). 확인이 안 되면 다음 가설로.",
           "  3. 고친 뒤 그 파일이 거는 검사와 `python3 gatekeeper.py` 를 돌려라. 빨강이면 왜 빨간지 읽고 다시.",
           "  4. 검사가 없는 자리를 고쳤으면 검사를 지어 붙여라 -- 되살리면 잡히는 검사(빼면 빨강, 넣으면 초록).",
           "  5. 되풀이하지 마라. 같은 명령이 같은 꼬리를 내면 그 갈래는 끝난 것이다.",
           "  6. **'됐다' 고 말하지 마라.** 위 판정들이 끝값 0 을 내면 코드가 안다. 네 턴은 한 걸음이다 -- "
           "다음 바퀴가 이어 받는다. 이 턴에서 한 일과 다음에 볼 것을 두 줄로 적고 끝내라.",
           "  7. 사람에게 묻지 마라. 사람만 가진 값(열쇠·승인)이 정말 필요하면 그 한 가지만 마지막에 적어라."]
    if 재현명령:
        줄.append(f"재현 명령: `{재현명령}`")
    return "\n".join(줄)


def 마무리프롬프트(증상: str, 아이디: str) -> str:
    return ("\n".join([
        "[조사 마무리] 판정이 전부 끝값 0 이다. 이제 남기는 일만 한다:",
        f"  · 증상: {증상}",
        "  1. `git status --porcelain` 으로 바뀐 것을 보고, `python3 gatekeeper.py` 가 0 인지 한 번 더 확인하라.",
        "  2. 커밋하라. 메시지에는 무엇이 왜 깨졌고 어떻게 고쳤는지, 검사가 무엇을 붙드는지 적어라.",
        f"  3. create_pr 도구로 PR 을 열어라 (제목에 `[조사 {아이디}]`). 도구가 준 URL 만 말하라.",
        "  4. **머지는 사람이 누른다.** 네가 머지하지 마라.",
        "  한 줄로 보고하라: 커밋 해시 · PR URL · 남은 것(없으면 없음).",
    ]))


# ------------------------------------------------------------------ 원장·메모 (repair 의 것을 그대로 쓴다)
def _적기(repo: Path, 줄: dict) -> None:
    from repair import run as R
    줄 = {"꼴": "조사", **줄}
    R._적기(repo, 줄)


def 원장읽기(repo=None, 아이디: str = "") -> "list[dict]":
    from repair import run as R
    return [d for d in R.원장읽기(repo) if d.get("꼴") == "조사" and (not 아이디 or d.get("조사") == 아이디)]


# ------------------------------------------------------------------ 루프
def 조사(증상: str, 재현명령: str = "", 증거글: str = "", 시한초: int = 기본시한초,
       최대바퀴: int = 기본최대바퀴, repo=None, 아이디: str = "", 진행=None, 목표: bool = False) -> dict:
    """될 때까지. 끝은 코드가 정한다. 되풀이는 센다. 시한은 지킨다.

    `목표=True` 는 **새 기능**이다 -- 재현할 빨강이 없다. 그러면 첫 일은 그 부탁을 검사 파일
    `tests/test_목표_<id>.py` 로 못박는 것이고, 그 검사가 재현 명령이 된다: 파일이 없으면 빨강,
    있는데 안 지나면 빨강, 지나면 끝. 사용자(2026-09-12): "프롬프트 의존도를 최소화" -- 부탁의
    성패를 모델의 말이 아니라 **검사의 끝값**으로 판정하는 길이다."""
    repo = Path(repo or REPO)
    아이디 = 아이디 or uuid.uuid4().hex[:8]
    if 목표 and not 재현명령:
        재현명령 = f"python3 tests/test_목표_{아이디}.py"
        증상 = (f"[목표] {증상}\n첫 일: 이 부탁을 `tests/test_목표_{아이디}.py` 로 못박아라 -- 부탁이 이뤄졌을 때만 "
              f"끝값 0 인 검사(기능이 없으면 ImportError/AssertionError). 그다음 그 검사가 지나게 기능을 지어라 "
              f"(새 모듈 · 필요하면 requirements.txt 한 줄). 검사를 지우거나 비우면 판정이 무의미해진다 -- 그러지 마라.")
    시작 = time.monotonic()
    해본: list[dict] = []
    결과 = {"조사": 아이디, "해결": False, "돌았나": True, "바퀴": 0, "해본것": 해본,
          "남은것": "", "메모": "", "걸린초": 0.0, "마무리": ""}
    말하기 = 진행 or (lambda s: print(s, flush=True))
    thread_id = f"investigate-{아이디}"

    def 판정하기():
        return (판정기 or _판정기본)(repo, 재현명령)

    판정 = 판정하기()
    지문 = _diff지문(repo)
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "시작",
                "증상": 증상[:200], "명령": 재현명령[:200], "빨강": [p["이름"] for p in 판정 if p["끝값"]]})
    if all(p["끝값"] == 0 for p in 판정):
        결과.update(해결=True, 남은것="")
        결과["메모"] = "시작부터 판정이 전부 0 -- 고칠 것이 없다"
        return 결과

    되풀이 = 0
    for n in range(1, max(1, 최대바퀴) + 1):
        남은초 = 시한초 - (time.monotonic() - 시작)
        if 남은초 <= 0:
            결과["남은것"] = f"시한 {시한초}초를 다 썼다 ({n - 1}바퀴). 마지막 빨강: {[p['이름'] for p in 판정 if p['끝값']]}"
            break
        결과["바퀴"] = n
        마지막꼬리 = "\n".join(p["꼬리"] for p in 판정 if p["끝값"])
        진 = (진단기 or _진단기본)((증거글 or "") + "\n" + 마지막꼬리 + "\n" + 증상, repo)
        p = 프롬프트(증상, 진, 판정, 해본, n, 남은초, 되풀이, 재현명령)
        말하기(f"[조사 {아이디}] 바퀴 {n} · 빨강 {[x['이름'] for x in 판정 if x['끝값']]} · 가설 {len(진.get('가설', []))}")
        try:
            답 = (두뇌 or _두뇌기본)(p, thread_id)
        except Exception as e:                                        # noqa: BLE001
            결과.update(돌았나=False, 남은것=f"두뇌를 못 불렀다: {type(e).__name__}: {str(e)[:160]}")
            break
        판정 = 판정하기()
        새지문 = _diff지문(repo)
        빨강 = [x["이름"] for x in 판정 if x["끝값"]]
        같다 = (새지문 == 지문) and (빨강 == [x for x in (해본[-1]["빨강"] if 해본 else 빨강)])
        되풀이 = 되풀이 + 1 if 같다 else 0
        지문 = 새지문
        h = {"바퀴": n, "요약": (답 or "").strip().replace("\n", " ")[:300], "빨강": 빨강,
             "diff": 새지문, "되풀이": 되풀이, "가설": [x["탐침"] for x in 진.get("가설", [])]}
        해본.append(h)
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "바퀴",
                    "바퀴": n, "빨강": 빨강, "되풀이": 되풀이, "요약": h["요약"][:200], "가설": h["가설"]})
        말하기(f"[조사 {아이디}] 바퀴 {n} 끝 · 빨강 {빨강} · 되풀이 {되풀이}")
        if not 빨강:
            결과["해결"] = True
            break
        if 되풀이 >= 되풀이한도:
            결과["남은것"] = (f"{되풀이한도}바퀴 연속 아무것도 안 바뀌었다 (판정 {빨강}, diff 그대로). "
                          f"코드로는 더 못 간다 -- 마지막 꼬리: {마지막꼬리.splitlines()[-1][:160] if 마지막꼬리 else '(없음)'}")
            break
    else:
        결과["남은것"] = f"{최대바퀴}바퀴를 다 썼다. 마지막 빨강: {[p['이름'] for p in 판정 if p['끝값']]}"

    if 결과["해결"]:
        try:
            결과["마무리"] = ((두뇌 or _두뇌기본)(마무리프롬프트(증상, 아이디), thread_id) or "").strip()[:600]
        except Exception as e:                                        # noqa: BLE001
            결과["마무리"] = f"(마무리 턴을 못 돌렸다: {type(e).__name__}) 판정은 초록이다 -- 커밋·PR 은 손으로"
    from repair import run as R
    결과["메모"] = R.기억쓰기(f"조사 {아이디}: {증상}", 재현명령 or "(판정: 게이트·감사)",
                        [{"바퀴": h["바퀴"], "꼴": "조사", "요약": h["요약"][:120], "판정": "초록" if not h["빨강"] else f"빨강 {h['빨강']}",
                          "왜": ", ".join(h["가설"])} for h in 해본],
                        결과["해결"], 결과["남은것"], repo)
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "끝",
                "해결": 결과["해결"], "바퀴": 결과["바퀴"], "남은것": 결과["남은것"][:200], "메모": 결과["메모"]})
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    return 결과


def _진단기본(글: str, repo=None) -> dict:
    try:
        import diagnose
        return diagnose.진단(글, repo)
    except Exception as e:                                            # noqa: BLE001
        return {"증상": {}, "증거": [], "가설": [], "말": f"진단을 못 돌렸다: {type(e).__name__}"}


def 보고(r: dict) -> str:
    줄 = [f"조사 {r['조사']} -- {'**해결**' if r['해결'] else '못 풀었다'} ({r['바퀴']}바퀴 · {r['걸린초']}초)"]
    for h in r["해본것"][-6:]:
        줄.append(f"  바퀴 {h['바퀴']} 빨강 {h['빨강'] or '없음'}" + (f" · 되풀이 {h['되풀이']}" if h["되풀이"] else "")
                  + f" · {h['요약'][:100]}")
    if r["해결"] and r.get("마무리"):
        줄.append(f"  마무리: {r['마무리'][:300]}")
    if not r["해결"]:
        줄.append(f"  남은 것: {r['남은것'][:300]}")
    if r.get("메모"):
        줄.append(f"  메모: {r['메모']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="긴 호흡으로 끝까지 판다 -- 판정은 끝값, 시한은 사람")
    ap.add_argument("--증상", default="", help="오류 문구 또는 문제 한 줄")
    ap.add_argument("--명령", default="", help="재현 명령 (끝값 0 이면 그 판정은 초록)")
    ap.add_argument("--증거", default="", help="트레이스백이 든 로그 파일")
    ap.add_argument("--시한", type=int, default=기본시한초)
    ap.add_argument("--바퀴", type=int, default=기본최대바퀴)
    ap.add_argument("--저장소", default="")
    ap.add_argument("--목표", action="store_true", help="새 기능: 부탁을 검사로 못박고 그 검사가 지날 때까지")
    ap.add_argument("--배선", action="store_true", help="두뇌 없이 배선만 확인한다(끝값 0)")
    ap.add_argument("--두뇌", choices=["봇", "claude"], default="봇",
                    help="봇 = 관리 에이전트(Gemini, 기본) · claude = `claude -p` (토큰이 있을 때)")
    a = ap.parse_args()
    global 두뇌
    if a.두뇌 == "claude" and 두뇌 is None:
        두뇌 = _두뇌claude
    if a.배선:
        import diagnose  # noqa: F401
        from repair import run as R  # noqa: F401
        print("investigate: diagnose · repair 원장·메모 · 판정(게이트·감사) 배선됨")
        return 0
    if not a.증상:
        print("--증상 이 필요하다")
        return 3
    증거 = ""
    if a.증거:
        try:
            증거 = Path(a.증거).read_text(encoding="utf-8", errors="replace")[-8000:]
        except OSError as e:
            print(f"증거 파일을 못 읽었다: {e}")
    r = 조사(a.증상, a.명령, 증거, a.시한, a.바퀴, a.저장소 or None, 목표=a.목표)
    print(보고(r))
    if not r["돌았나"]:
        return 3
    return 0 if r["해결"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
