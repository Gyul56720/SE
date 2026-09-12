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
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 스크립트로 돌 때 sys.path[0] 은 investigate/ 다 -- 뿌리가 아니다 (improve/run.py 의 사고).
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

기본시한초 = 6 * 3600   # 사용자(2026-09-12): "6시간이 걸려도 좋으니 스스로 해결해보라고"
기본최대바퀴 = 400
되풀이한도 = 6          # 판정·diff 가 이만큼 연속 같으면 멈춘다 -- 그 전에 제2의 뇌를 두 번 쓴다
제2의뇌때 = (2, 4)      # 되풀이가 이만큼 쌓이면 **코드가** dig·graph 로 찾아 다음 바퀴에 들려 보낸다

두뇌 = None     # 검사 주입: (prompt, thread_id) -> str.  None 이면 봇의 run_admin_agent
모으기 = None   # 검사 주입: (증상) -> list[str].  None 이면 repair._모으기기본 (dig/harvest + graph/ask)
판정기 = None   # 검사 주입: (repo, 재현명령) -> list[dict{"이름","끝값","꼬리"}]
진단기 = None   # 검사 주입: (글, repo) -> dict.  None 이면 diagnose.진단
머지기 = None   # 검사 주입: (repo, 아이디, 부탁) -> dict.  None 이면 _머지기본 (github_write 로 PR 을 찾아 판단·머지)


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
        out.append({"이름": 이름, "끝값": rc, "꼬리": "\n".join(꼬리.splitlines()[-8:]), "명령": argv, "초": 초})
        if 이름 == "감사" and rc != 0:
            out += _감사좁히기(repo, 꼬리, env, 이미=[p["명령"] for p in out])
    return out


_감사실패꼴 = re.compile(r"^\s*실패 (tests/[\w가-힣./-]+\.py) \(끝값 (\d+)\)", re.M)


def _감사좁히기(repo: Path, 감사꼬리: str, env: dict, 이미: "list[list]") -> "list[dict]":
    """**최소 재현 축소.** 감사가 빨가면 그 안의 어느 검사 파일이 빨간지 코드가 읽어 **파일마다 판정**을 더한다.
    두뇌는 '감사 빨강' 한 덩어리 대신 `감사:tests/test_x.py` 와 그 파일만의 꼬리·귀속을 받는다.

    사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 8개 중 7번. 이 저장소의 검사는 파일 단위
    스크립트라 파일보다 작게 쪼갤 것이 없다 -- 파이프라인 전체에서 파일 하나로 좁히는 것이 축소다.
    신호가 좁아지면 두뇌의 탐색 공간도 좁아지고, 대조(HEAD 에서 다시 돌리기)도 그 파일에 대해 따로 된다."""
    out = []
    for 파일, _rc in _감사실패꼴.findall(감사꼬리 or ""):
        argv = ["python3", 파일]
        if argv in 이미 or not (repo / 파일).is_file():
            continue
        rc, 꼬리 = _돌리기(argv, repo, 300, env=env)
        out.append({"이름": f"감사:{파일}", "끝값": rc, "꼬리": "\n".join(꼬리.splitlines()[-8:]), "명령": argv, "초": 300})
    return out


# ------------------------------------------------------------------ 귀속: 이 빨강이 내 탓인가 -- 추론이 아니라 조회
대조기 = None   # 검사 주입: (repo, 판정, 검사상대) -> {이름: HEAD끝값|None}.  None 이면 _대조기본
_대조캐시: dict = {}


def _대조기본(repo: Path, 판정: "list[dict]", 검사상대: str = "") -> dict:
    """빨간 판정을 **HEAD 판(이 조사의 변경이 없는 나무)** 에서 같은 명령으로 다시 돌린다. {이름: 끝값|None}.

    사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 빨강을 보고 "내 변경 탓인가, 원래
    빨강인가" 를 모델이 **추론**하면 틀린다(실측: "구글이 차단" 같은 지어낸 귀속). 같은 명령을 변경 없는
    나무에서 돌리면 귀속은 **조회**다. 오늘 내가 compression_judge 를 `git stash` 로 손수 잰 것을 코드가 한다.
    목표 모드의 재현(두뇌가 지은 검사)은 HEAD 에 파일이 없어 뜻이 없으므로 뺀다. 같은 HEAD 에서는 한 번만 잰다."""
    rc0, head = _돌리기(["git", "rev-parse", "HEAD"], repo, 30)
    head = head.strip() if rc0 == 0 else "?"
    out: dict = {}
    for p in 판정:
        if p.get("끝값", 0) == 0 or not p.get("명령"):
            continue
        if p["이름"] == "재현" and 검사상대:
            continue
        열쇠 = (str(repo), head, p["이름"])
        if 열쇠 not in _대조캐시:
            try:
                from sandbox import run as SB
                r = SB.실행(list(p["명령"]), repo=repo, 지금트리=False, 초=int(p.get("초", 600)), 메모리MB=4096)
                _대조캐시[열쇠] = int(r["끝값"]) if r.get("돌았나") else None
            except Exception:                              # noqa: BLE001
                _대조캐시[열쇠] = None
        out[p["이름"]] = _대조캐시[열쇠]
    return out


def 귀속말(이름: str, 지금끝값: int, head끝값) -> str:
    if head끝값 is None:
        return "귀속 못 잼(HEAD 판을 못 돌렸다)"
    if head끝값 == 0:
        return f"**내 변경 탓** -- 변경 없는 HEAD 판에서는 초록(끝값 0)이다. 이 조사에서 바꾼 것 안에 원인이 있다"
    return f"**원래 빨강** -- 변경 없는 HEAD 판에서도 빨강(끝값 {head끝값})이다. 되돌려도 안 낫는다, 고쳐야 한다"


# ------------------------------------------------------------------ 예측-관측 대조: 믿음을 사실에 부딪힌다
_예측꼴 = re.compile(r"예측\s*[:：]\s*(.+)$", re.M)
_예측쌍 = re.compile(r"([가-힣A-Za-z_]+)\s*=\s*(-?\d+)")


def 예측뽑기(답: str) -> "dict[str, int]":
    """두뇌의 답에서 마지막 `예측: 재현=0 게이트=0 감사=1` 줄을 {이름: 끝값} 으로. 없으면 빈 dict."""
    m = None
    for m in _예측꼴.finditer(답 or ""):
        pass
    if not m:
        return {}
    return {k: int(v) for k, v in _예측쌍.findall(m.group(1))}


def 예측대조(예측: "dict[str, int]", 판정: "list[dict]") -> "list[dict]":
    """[{이름, 예측, 관측, 맞음}] -- 0 인지 아닌지로 견준다(끝값의 정확한 수까지는 안 묻는다).

    왜 이것이 약한 모델에 듣나: 정답을 **짓는** 것보다 예/아니오를 **맞히는** 것이 쉽고, 틀린 예측은
    모호함이 없는 오류 신호다. "됐습니다" 라고 지어내면 예측 0 이 관측 1 과 부딪혀 **지어내기가 드러난다**."""
    out = []
    for p in 판정:
        if p["이름"] not in 예측:
            continue
        예 = 0 if 예측[p["이름"]] == 0 else 1
        관 = 0 if p["끝값"] == 0 else 1
        out.append({"이름": p["이름"], "예측": 예, "관측": 관, "맞음": 예 == 관})
    return out


def _diff지문(repo: Path) -> str:
    rc, out = _돌리기(["git", "diff", "HEAD", "--stat"], repo, 60)
    rc2, head = _돌리기(["git", "rev-parse", "HEAD"], repo, 30)
    return hashlib.sha1((out + head).encode("utf-8", "replace")).hexdigest()[:12]


# ------------------------------------------------------------------ 프롬프트
def _제2의뇌(증상: str, 꼬리: str) -> "list[str]":
    """막혔을 때 **코드가** 제2의 뇌를 연다. 두뇌에게 '찾아보라' 고 권하는 것이 아니라 찾아서 들려 준다.

    사용자(2026-09-12): "모르면 제2의 뇌나 dig 로 검색해서 정보 찾고 코드 고치고 문제 있으면 또
    수정하고." repair 의 모으기(dig/harvest 한 바퀴 + graph 조회)를 그대로 쓴다 -- 두 벌 아님."""
    try:
        from repair import run as R
        물음 = (증상 + " " + (꼬리.splitlines()[-1] if 꼬리 else ""))[:300]
        return list((모으기 or R._모으기기본)(물음))[:6]
    except Exception as e:                                          # noqa: BLE001
        return [f"(제2의 뇌를 못 열었다: {type(e).__name__})"]


def 목표검사유효한가(repo: Path, 시작커밋: str, 검사상대: str) -> "tuple[bool, str]":
    """목표 검사가 **검사 구실을 하는가** -- 기능이 없는 판(조사 시작 커밋)에서 빨갛고, 지금 초록이어야 한다.

    실측 2026-09-12(VM, PR #194): 두뇌가 `def test_…` 만 있고 아무것도 안 부르는 검사를 지었다.
    스크립트로 돌면 늘 끝값 0 이라 '해결' 이 찍혔다 -- 검사하지 않은 초록불. 검사와 기능을 같은
    두뇌가 짓는 이상, **기능 없이도 지나는 검사는 검사가 아니다** 를 코드가 봐야 한다."""
    import os, shutil, tempfile
    src = repo / 검사상대
    if not src.is_file():
        return False, f"검사 파일이 없다: {검사상대}"
    tmp = Path(tempfile.mkdtemp(prefix="se-goal-base-"))
    try:
        rc, out = _돌리기(["git", "worktree", "add", "--detach", str(tmp), 시작커밋], repo, 120)
        if rc != 0:
            return False, f"시작 판을 못 꺼냈다: {out[-160:]}"
        dst = tmp / 검사상대
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        rc2, out2 = _돌리기(["python3", 검사상대], tmp, 300, env=env)
        if rc2 == 0:
            return False, ("**검사 무효** -- 기능이 없는 판(조사 시작 커밋)에서도 초록이다. 함수만 정의하고 안 부르거나, "
                           "글자가 있는지만 보는 검사다. 기능이 없으면 빨갛게 죽는 검사(모듈 임포트 · 함수 호출 · "
                           "결과 단언, 모듈 수준에서 실제로 실행)로 다시 써라.")
        return True, f"시작 판에서 빨강(끝값 {rc2}) · 지금 초록 -- 검사가 검사 구실을 한다"
    finally:
        _돌리기(["git", "worktree", "remove", "--force", str(tmp)], repo, 60)
        shutil.rmtree(tmp, ignore_errors=True)


def _명령기록(thread_id: str) -> "dict | None":
    """이 조사가 지금까지 돌린 명령과 막힌 중복 -- run_shell 이 shellmemo 에 적는다. 안 켜졌으면 None."""
    import shellmemo
    return shellmemo.보기(thread_id)


def 프롬프트(증상: str, 진: dict, 판정: "list[dict]", 해본: "list[dict]", 바퀴: int, 남은초: float,
          되풀이: int, 재현명령: str, 참고: "list[str] | None" = None, 명령기록: "dict | None" = None,
          귀속: "dict | None" = None) -> str:
    빨강 = [p for p in 판정 if p["끝값"] != 0]
    줄 = [f"[조사 바퀴 {바퀴} · 남은 시간 {int(남은초 // 60)}분] **끝까지 판다. 판정은 끝값이 한다.**",
         f"증상: {증상}",
         "",
         "지금 빨강인 판정 (이것들이 전부 끝값 0 이 되어야 끝난다):"]
    for p in 빨강:
        줄.append(f"  · {p['이름']} 끝값 {p['끝값']}")
        if 귀속 and p["이름"] in 귀속:
            줄.append(f"      귀속: {귀속말(p['이름'], p['끝값'], 귀속[p['이름']])}")
        줄 += [f"      {x}" for x in p["꼬리"].splitlines()[-6:]]
    if 해본 and 해본[-1].get("대조"):
        줄.append("")
        줄.append("지난 바퀴의 **예측 대조** (네가 적은 예측 vs 코드가 잰 관측):")
        for d in 해본[-1]["대조"]:
            줄.append(f"  · {d['이름']}: 예측 {d['예측']} → 관측 {d['관측']} " + ("맞음" if d["맞음"] else "**틀림 -- 이 믿음은 사실과 다르다. 그 가설을 버려라**"))
    elif 해본 and 해본[-1].get("예측없음"):
        줄.append("")
        줄.append("지난 바퀴에 **예측을 안 적었다.** 마지막 줄에 반드시 적어라 -- 예측이 없으면 틀린 믿음을 잡을 길이 없다.")
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
    if 명령기록 and 명령기록.get("돌린것"):
        줄.append("")
        줄.append(f"이 조사에서 이미 돌린 명령 (마지막 12개 · 끝값). **같은 나무에 같은 명령은 코드가 막는다**"
                  + (f" -- 지금까지 {len(명령기록['막음'])}번 막았다" if 명령기록.get("막음") else "") + ":")
        for 명, rc in 명령기록["돌린것"][-12:]:
            줄.append(f"  · [{rc}] {명[:110]}")
    if 참고:
        줄.append("")
        줄.append("제2의 뇌가 찾아 온 것 (막혀서 코드가 dig·graph 로 찾았다 -- 읽고 갈래를 바꿔라):")
        for x in 참고[:6]:
            줄.append(f"  · {str(x)[:240]}")
    if 되풀이 >= 2:
        줄.append("")
        줄.append("**두 바퀴째 아무것도 안 바뀌었다.** 같은 갈래는 막혔다. 다른 가설로 가라: "
                  "증거를 다시 읽어라(트레이스백 줄번호를 `git log -L`·`git show` 로 옛 판과 맞춰 보라), "
                  "`python3 -m diagnose --글 '<트레이스백>'` · `python3 impact.py --파일 <파일>` · "
                  "`python3 dig/harvest.py --틈` 으로 제2의 뇌를 열어라. 고치는 자리를 바꿔라 -- "
                  "파일 안이 아니라 부르는 쪽, 코드가 아니라 배포·머지·부르는 꼴일 수 있다.")
    줄 += ["",
           "이렇게 하라 -- 사람이 하듯이, 한 호흡에, 도구를 몇 번이든:",
           "  1. 가설을 하나 세우고, 그것을 **끝값으로 확인할 명령**을 먼저 돌려라. 추측을 말로 하지 마라. "
           "갈릴 만한 탐침이 여럿이면 **run_probes 로 한꺼번에**(줄마다 하나) -- 한 바퀴에 명령 하나씩 돌리지 마라.",
           "  2. 확인되면 고쳐라 (edit_file -- 바꿀 줄만). 확인이 안 되면 다음 가설로.",
           "  3. 고친 뒤 그 파일이 거는 검사와 `python3 gatekeeper.py` 를 돌려라. 빨강이면 왜 빨간지 읽고 다시.",
           "  4. 검사가 없는 자리를 고쳤으면 검사를 지어 붙여라 -- 되살리면 잡히는 검사(빼면 빨강, 넣으면 초록).",
           "  5. 되풀이하지 마라. 같은 명령이 같은 꼬리를 내면 그 갈래는 끝난 것이다.",
           "  6. **'됐다' 고 말하지 마라.** 위 판정들이 끝값 0 을 내면 코드가 안다. 네 턴은 한 걸음이다 -- "
           "다음 바퀴가 이어 받는다. 이 턴에서 한 일과 다음에 볼 것을 두 줄로 적고 끝내라.",
           "  7. 사람에게 묻지 마라. 사람만 가진 값(열쇠·승인)이 정말 필요하면 그 한 가지만 마지막에 적어라.",
           "  8. **맨 마지막 줄에 예측을 적어라**: `예측: " + " ".join(f"{p['이름']}=0" for p in 판정) + "` 꼴로, 이 턴이 끝난 뒤 "
           "각 판정의 끝값이 얼마일지(0 = 초록). 코드가 실제 끝값과 대조한다 -- 틀리면 다음 바퀴에 그 사실이 온다."]
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
        "  4. 네가 머지하지 마라. PR 이 열리면 **코드가** 문제를 재고, 문제가 없으면 코드가 머지한다.",
        "  한 줄로 보고하라: 커밋 해시 · PR URL · 남은 것(없으면 없음).",
    ]))


# ------------------------------------------------------------------ 머지: 문제는 코드가 재고, 없으면 코드가 누른다
# 사용자(2026-09-12): "최대한 스스로 하고 문제가 있을 경우에만 의견 물어봐. 그리고 그 문제가 뭔지 정확히 설명해."
# 그래서 둘로 가른다. **문제** = 붙이면 안 되는 사실(막는다). **알림** = 붙으면 일어나는 일(적기만 한다).
# 문제가 없으면 코드가 머지한다. 있으면 무엇이 문제인지 그대로 적고 `!조사 머지 <번호>` 를 사람이 친다.
줄수상한 = 1500                      # 이보다 크면 사람이 봐야 할 크기다
_봇본체 = ("discord_bot_server.py", "bot_tools.py", "main_public.py", "dispatch.py")
_딸림꼴 = re.compile(r"(^|/)(public_agent_memory/|.*ledger\.jsonl$|logs/)")


def 머지위험(상태: dict) -> "tuple[list[str], list[str]]":
    """pr상태() 의 사실에서 (문제, 알림). 순수 함수 -- 검사가 사실을 꽂아 붙든다."""
    문제, 알림 = [], []
    if 상태.get("겹침"):
        문제.append("main 과 겹친다(충돌) -- 그대로는 못 붙는다. 갈래에 main 을 merge 해서 풀어야 한다")
    빨강 = [c["이름"] for c in 상태.get("검사", []) if c.get("결론") in ("failure", "timed_out", "action_required")]
    if 빨강:
        문제.append(f"CI 빨강: {', '.join(sorted(set(빨강)))} -- 여기서 초록이었던 판정이 CI 러너에서는 빨갛다. 로그를 봐야 한다")
    파일들 = 상태.get("파일들", [])
    지움 = [f["경로"] for f in 파일들 if f.get("상태") == "removed"]
    if 지움:
        문제.append(f"파일 삭제 {len(지움)}개: {', '.join(지움[:5])} -- 지운 것은 되돌리기 어렵다")
    줄 = int(상태.get("더함", 0)) + int(상태.get("뺌", 0))
    if 줄 > 줄수상한:
        문제.append(f"바뀐 줄이 {줄:,}줄 -- 상한 {줄수상한:,} 을 넘는다. 사람이 봐야 할 크기다")
    도는중 = [c["이름"] for c in 상태.get("검사", []) if c.get("상태") != "completed"]
    if 도는중:
        알림.append(f"CI 가 아직 도는 중({', '.join(sorted(set(도는중)))}) -- 기다리지 않는다(여기 판정이 초록이다). 빨개지면 CI 가 알린다")
    본체 = [f["경로"] for f in 파일들 if f["경로"] in _봇본체]
    if 본체:
        알림.append(f"봇 본체가 바뀐다: {', '.join(본체)} -- 배포가 봇을 재시작한다. 임포트가 깨지면 봇이 죽는다(G012 가 막는다)")
    if any(f["경로"] == "requirements.txt" for f in 파일들):
        알림.append("새 의존성(requirements.txt) -- 배포가 pip 로 깐다")
    if any(f["경로"].startswith(".github/workflows/") for f in 파일들):
        알림.append("배포·CI 워크플로가 바뀐다 -- 다음 배포부터 적용")
    딸림 = [f["경로"] for f in 파일들 if _딸림꼴.search(f["경로"])]
    if 딸림:
        알림.append(f"메모·원장 {len(딸림)}개가 딸려 간다(덧붙이기만 하는 파일이라 해롭지 않다)")
    return 문제, 알림


def _main으로(repo: Path) -> str:
    """머지 뒤 저장소를 main 으로 되돌린다 -- 안 그러면 다음 실행과 봇의 자동 반영이 이 갈래에 계속 쌓인다
    (실측 2026-09-12: 봇 커밋 "SE-agent: Discord 요청 처리 결과 자동 반영" 이 조사 갈래에 붙었다)."""
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)  # noqa: E731
    g("fetch", "-q", "origin", "main")
    co = g("checkout", "-q", "main")
    ff = g("merge", "-q", "--ff-only", "origin/main") if co.returncode == 0 else co
    return "main 으로 돌아왔다" if ff.returncode == 0 else f"main 으로 못 돌아왔다: {(ff.stderr or '').strip()[:120]}"


def _머지기본(repo: Path, 아이디: str, 부탁: str = "") -> dict:
    """이 갈래의 열린 PR 을 찾아 문제를 재고, 없으면 머지한다. {됐나, 번호, url, 문제, 알림, 왜, 갈래정리}."""
    import github_write as GW
    br = subprocess.run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    pr = GW.열린pr(갈래=br if br != "main" else "", 제목에=f"[조사 {아이디}]", repo=repo)
    if not pr["됐나"]:
        return {"됐나": False, "번호": 0, "url": "", "문제": [], "알림": [], "왜": pr["왜"]}
    상태 = GW.pr상태(pr["번호"], repo=repo)
    if not 상태.get("됐나"):
        return {"됐나": False, "번호": pr["번호"], "url": pr["url"], "문제": [], "알림": [], "왜": 상태.get("왜", "")}
    문제, 알림 = 머지위험(상태)
    out = {"됐나": False, "번호": pr["번호"], "url": pr["url"], "문제": 문제, "알림": 알림, "왜": "",
           "크기": f"+{상태['더함']} / -{상태['뺌']} · 파일 {len(상태['파일들'])}"}
    if 문제:
        out["왜"] = f"문제 {len(문제)}개 -- 사람이 `!조사 머지 {pr['번호']}` 로 확정해야 붙는다"
        return out
    m = GW.pr머지하기(pr["번호"], repo=repo)
    out["됐나"] = m["됐나"]; out["왜"] = m["왜"]
    if m["됐나"]:
        out["갈래정리"] = _main으로(repo)
    return out


def 머지확정(번호: int, repo=None) -> str:
    """`!조사 머지 <번호>` -- 사람이 문제를 보고도 붙이기로 한 것. 코드는 더 판단하지 않고 누른다."""
    import github_write as GW
    repo = Path(repo or REPO)
    m = GW.pr머지하기(int(번호), repo=repo)
    if not m["됐나"]:
        return f"PR #{번호} 머지 못 함 -- {m['왜']}"
    return f"PR #{번호} 머지됨 ({m['sha']}) · {_main으로(repo)} · 배포는 main 밀기가 트리거한다"


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
    검사상대 = ""
    if 목표 and not 재현명령:
        검사상대 = f"tests/test_목표_{아이디}.py"
        재현명령 = f"python3 {검사상대}"
        증상 = (f"[목표] {증상}\n첫 일: 이 부탁을 `tests/test_목표_{아이디}.py` 로 못박아라 -- 부탁이 이뤄졌을 때만 "
              f"끝값 0 인 검사(기능이 없으면 ImportError/AssertionError). 그다음 그 검사가 지나게 기능을 지어라 "
              f"(새 모듈 · 필요하면 requirements.txt 한 줄). 검사는 모듈 수준에서 실제로 실행되고 단언해야 한다 -- "
              f"함수만 정의하면 아무것도 안 돈다. 기능이 없는 판에서 초록인 검사는 코드가 무효로 친다.")
    rc0, 시작커밋 = _돌리기(["git", "rev-parse", "HEAD"], repo, 30)
    시작커밋 = 시작커밋.strip() if rc0 == 0 else ""
    시작 = time.monotonic()
    해본: list[dict] = []
    결과 = {"조사": 아이디, "증상": 증상, "해결": False, "돌았나": True, "바퀴": 0, "해본것": 해본,
          "남은것": "", "메모": "", "걸린초": 0.0, "마무리": ""}
    말하기 = 진행 or (lambda s: print(s, flush=True))
    thread_id = f"investigate-{아이디}"
    import shellmemo
    shellmemo.켜기(thread_id)                # 같은 나무에 같은 명령은 돌리지 않는다 -- 두뇌의 기억이 아니라 코드

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
    참고: list = []
    뇌연횟수 = 0
    for n in range(1, max(1, 최대바퀴) + 1):
        남은초 = 시한초 - (time.monotonic() - 시작)
        if 남은초 <= 0:
            결과["남은것"] = f"시한 {시한초}초를 다 썼다 ({n - 1}바퀴). 마지막 빨강: {[p['이름'] for p in 판정 if p['끝값']]}"
            break
        결과["바퀴"] = n
        마지막꼬리 = "\n".join(p["꼬리"] for p in 판정 if p["끝값"])
        진 = (진단기 or _진단기본)((증거글 or "") + "\n" + 마지막꼬리 + "\n" + 증상, repo)
        if 되풀이 in 제2의뇌때 and 뇌연횟수 < len(제2의뇌때):
            # **막히면 사람이 아니라 제2의 뇌다.** 같은 실패가 쌓이면 코드가 찾아서 들려 보낸다.
            참고 = _제2의뇌(증상, 마지막꼬리)
            뇌연횟수 += 1
            _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "제2의뇌",
                        "바퀴": n, "되풀이": 되풀이, "참고수": len(참고), "참고": [str(x)[:160] for x in 참고[:3]]})
            말하기(f"[조사 {아이디}] 막혔다(되풀이 {되풀이}) -- 제2의 뇌를 열었다: 참고 {len(참고)}개")
        try:
            귀속 = (대조기 or _대조기본)(repo, 판정, 검사상대)
        except Exception:                                         # noqa: BLE001
            귀속 = {}
        p = 프롬프트(증상, 진, 판정, 해본, n, 남은초, 되풀이, 재현명령, 참고, _명령기록(thread_id), 귀속)
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
        기록 = _명령기록(thread_id) or {}
        막음수 = len(기록.get("막음", []))
        예측 = 예측뽑기(답 or "")
        대조 = 예측대조(예측, 판정)
        h = {"바퀴": n, "요약": (답 or "").strip().replace("\n", " ")[:300], "빨강": 빨강,
             "diff": 새지문, "되풀이": 되풀이, "가설": [x["탐침"] for x in 진.get("가설", [])],
             "막음": 막음수, "명령수": len(기록.get("돌린것", [])),
             "귀속": {k: v for k, v in 귀속.items()}, "대조": 대조, "예측없음": not 예측}
        해본.append(h)
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "바퀴",
                    "바퀴": n, "빨강": 빨강, "되풀이": 되풀이, "요약": h["요약"][:200], "가설": h["가설"],
                    "막음": 막음수, "명령수": h["명령수"], "귀속": h["귀속"],
                    "예측": 예측, "맞춘수": sum(1 for d in 대조 if d["맞음"]), "틀린수": sum(1 for d in 대조 if not d["맞음"])})
        말하기(f"[조사 {아이디}] 바퀴 {n} 끝 · 빨강 {빨강} · 되풀이 {되풀이}" + (f" · 중복 막음 {막음수}" if 막음수 else "")
              + (f" · 예측 {sum(1 for d in 대조 if d['맞음'])}/{len(대조)} 맞음" if 대조 else " · 예측 없음"))
        if not 빨강:
            if 검사상대 and 시작커밋:
                유효, 유효말 = 목표검사유효한가(repo, 시작커밋, 검사상대)
                _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디,
                            "단계": "검사유효" if 유효 else "검사무효", "바퀴": n, "말": 유효말[:200]})
                말하기(f"[조사 {아이디}] 목표 검사 {'유효' if 유효 else '무효'}: {유효말[:80]}")
                if not 유효:
                    # 초록이지만 검사가 아니다 -- 해결로 치지 않고 두뇌에게 그 사실을 들려 계속 돈다.
                    판정 = [{"이름": "목표검사", "끝값": 1, "꼬리": "[검사 무효] " + 유효말}] + [p for p in 판정 if p["이름"] != "재현"]
                    h["빨강"] = ["목표검사"]
                    continue
            결과["해결"] = True
            break
        if 되풀이 >= 되풀이한도:
            결과["남은것"] = (f"{되풀이한도}바퀴 연속 아무것도 안 바뀌었다 (판정 {빨강}, diff 그대로). "
                          f"제2의 뇌를 {뇌연횟수}번 열었는데도 갈래가 안 바뀐다 -- 마지막 꼬리: "
                          f"{마지막꼬리.splitlines()[-1][:160] if 마지막꼬리 else '(없음)'}. "
                          f"이어 돌리려면 `!조사 {증상[:60]}`")
            break
    else:
        결과["남은것"] = f"{최대바퀴}바퀴를 다 썼다. 마지막 빨강: {[p['이름'] for p in 판정 if p['끝값']]}"

    if 결과["해결"]:
        try:
            결과["마무리"] = ((두뇌 or _두뇌기본)(마무리프롬프트(증상, 아이디), thread_id) or "").strip()[:600]
        except Exception as e:                                        # noqa: BLE001
            결과["마무리"] = f"(마무리 턴을 못 돌렸다: {type(e).__name__}) 판정은 초록이다 -- 커밋·PR 은 손으로"
        # 머지는 코드가 판단한다 -- 두뇌의 말("PR 열었다")이 아니라 GitHub 에서 갈래로 찾아서.
        try:
            결과["머지"] = (머지기 or _머지기본)(repo, 아이디, 증상)
        except Exception as e:                                        # noqa: BLE001
            결과["머지"] = {"됐나": False, "번호": 0, "url": "", "문제": [], "알림": [], "왜": f"{type(e).__name__}: {e}"[:160]}
        m = 결과["머지"]
        _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "머지",
                    "됐나": m["됐나"], "번호": m["번호"], "문제": m["문제"][:6], "왜": m["왜"][:160]})
        말하기(f"[조사 {아이디}] 머지 {'됨 #' + str(m['번호']) if m['됐나'] else '안 됨: ' + m['왜'][:80]}")
    from repair import run as R
    결과["메모"] = R.기억쓰기(f"조사 {아이디}: {증상}", 재현명령 or "(판정: 게이트·감사)",
                        [{"바퀴": h["바퀴"], "꼴": "조사", "요약": h["요약"][:120], "판정": "초록" if not h["빨강"] else f"빨강 {h['빨강']}",
                          "왜": ", ".join(h["가설"])} for h in 해본],
                        결과["해결"], 결과["남은것"], repo)
    _적기(repo, {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "조사": 아이디, "단계": "끝",
                "해결": 결과["해결"], "바퀴": 결과["바퀴"], "남은것": 결과["남은것"][:200], "메모": 결과["메모"]})
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    import shellmemo
    shellmemo.끄기(thread_id)
    return 결과


def _진단기본(글: str, repo=None) -> dict:
    try:
        import diagnose
        return diagnose.진단(글, repo)
    except Exception as e:                                            # noqa: BLE001
        return {"증상": {}, "증거": [], "가설": [], "말": f"진단을 못 돌렸다: {type(e).__name__}"}


def 보고(r: dict) -> str:
    """사람이 읽는 보고. 사용자(2026-09-12): 로그 꼬리를 그대로 보내면 못 알아먹는다 -- 상황 · 문제 · 다음 한 줄."""
    분 = r.get("걸린초", 0) / 60
    줄 = [f"조사 {r['조사']} -- {'**해결**' if r['해결'] else '**못 풀었다**'} ({r['바퀴']}바퀴 · {분:.1f}분)"]
    줄.append(f"부탁: {str(r.get('증상', ''))[:160]}")
    if r["해본것"]:
        h = r["해본것"][-1]
        줄.append(f"한 일: {h['요약'][:220]}")
    if not r["해결"]:
        줄.append(f"막힌 것: {r['남은것'][:300]}")
    m = r.get("머지")
    if m:
        if m.get("번호"):
            줄.append(f"PR #{m['번호']} {m.get('url', '')}" + (f" ({m['크기']})" if m.get("크기") else ""))
        for x in m.get("알림", []):
            줄.append(f"  · 알림: {x}")
        if m["됐나"]:
            줄.append("머지: **됨** -- 문제가 없어 코드가 붙였다" + (f" · {m['갈래정리']}" if m.get("갈래정리") else ""))
        elif m.get("문제"):
            줄.append(f"머지: **안 붙였다** -- 문제 {len(m['문제'])}개:")
            for x in m["문제"]:
                줄.append(f"  · {x}")
            줄.append(f"그래도 붙이려면: `!조사 머지 {m['번호']}`")
        else:
            줄.append(f"머지: 못 했다 -- {m['왜'][:200]}")
    if r.get("메모"):
        줄.append(f"메모: {r['메모']}")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="긴 호흡으로 끝까지 판다 -- 판정은 끝값, 시한은 사람")
    ap.add_argument("--증상", default="", help="오류 문구 또는 문제 한 줄")
    ap.add_argument("--명령", default="", help="재현 명령 (끝값 0 이면 그 판정은 초록)")
    ap.add_argument("--증거", default="", help="트레이스백이 든 로그 파일")
    ap.add_argument("--시한", type=int, default=기본시한초, help="기본 6시간 -- 사람에게 넘기는 것은 최후다")
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
    import relay
    print(f"\n{relay.보고표지}\n" + 보고(r), flush=True)      # relay.배경보고 가 이 표지 뒤만 사람에게 보낸다
    if not r["돌았나"]:
        return 3
    return 0 if r["해결"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
