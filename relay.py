"""도구 중계 -- 에이전트가 **무엇을 돌렸고 끝값이 얼마인지** 답변 채널에 실시간으로 보인다.

왜 있나: 답이 올 때까지 봇은 멈춘 것처럼 보인다. 실은 셸을 여섯 번 돌리고 모델을 두 번
갈아탄 것인데, 화면에는 아무것도 없다(llm_pool 이 "멈춘 것이 아니라 그만큼 느린 것" 이라고
적어 둔 그 상태). 로그 채널(log_streamer)에는 흐르지만 묻는 사람은 거기를 안 본다.

**보이는 것은 검사 가능한 것뿐이다** -- 도구 호출 · 끝값 · 걸린 초 · 모델 전환. 모델의
'생각' 은 여기 안 싣는다. 이 저장소의 제1규율이 그것이다: "차단돼서 못 받았다"(셸 0회) 는
내면에서 확신된 채 나온 말이었고, 독백을 크게 보이면 검사 안 받은 말이 판정받은 것처럼
읽힌다. 독백을 싣는 것은 실측으로 파트가 오는지 확인한 뒤 따로 정한다.

기본은 꺼짐. `!중계 켜기` (관리 채널) 로 켠다 -- 프로세스 전역 스위치라 켠 뒤 오는 모든
관리 채널 물음에 붙는다.

디스코드 제약: 메시지를 도구마다 새로 보내면 레이트리밋(채널당 대략 5개/5초)에 걸린다.
그래서 **메시지 하나를 갱신**한다 -- 편집도 한도가 있어 최소 간격을 두고 몰아서 한다.
편집은 이벤트 루프에서만 되는데 도구는 실행기 스레드에서 도므로, 스레드 -> 루프 다리를
`run_coroutine_threadsafe` 로 놓는다.

봇에 매이지 않는다: 편집기는 `async def 편집(text)` 이면 무엇이든 된다(검사가 가짜를 꽂는다).
"""
from __future__ import annotations

import asyncio
import re
import threading
import time
from pathlib import Path

PREFIX = "!중계"
상태 = {"켜짐": False}

HELP = f"""**중계 (relay)** -- 무엇을 돌렸고 끝값이 얼마인지 답 앞에 실시간으로 보인다
`{PREFIX} 켜기` / `{PREFIX} 끄기` (관리 채널만 · 프로세스 전역)
`{PREFIX} 상태`
보이는 것은 검사 가능한 것뿐이다: 도구 · 끝값 · 걸린 초 · 모델 전환. 모델의 생각은 안 실린다."""

# OS 스레드 ident -> 그 실행의 중계판. 실행기 스레드에서 도는 도구가 저를 찾는 길이다.
_판들: dict = {}
_판들_lock = threading.Lock()


class 중계판:
    """메시지 하나를 갱신하는 판. 스레드 어디서든 적기() 하면 루프에서 몰아서 편집한다."""

    def __init__(self, 편집, loop, 최소간격: float = 1.5, 상한: int = 1800):
        self._편집 = 편집            # async (text) -> None
        self._loop = loop
        self._최소간격 = 최소간격
        self._상한 = 상한
        self.줄들: list = []
        self.도구수 = 0                # 도구 줄만 센다 -- 모델 전환·되묻기 줄은 도구가 아니다
        self.시작 = time.monotonic()
        self.편집횟수 = 0
        self._lock = threading.Lock()
        self._마지막편집 = 0.0
        self._예약됨 = False
        self.끝났다 = False

    def 적기(self, 줄: str) -> None:
        with self._lock:
            self.줄들.append(줄)
            if 줄[:1] in 도구표지:
                self.도구수 += 1
            if self._예약됨:
                return                 # 이미 편집이 잡혀 있다 -- 그때 최신 줄들을 읽는다
            self._예약됨 = True
        try:
            asyncio.run_coroutine_threadsafe(self._몰아서편집(), self._loop)
        except RuntimeError:           # 루프가 닫혔다 -- 중계는 부수 기능이라 조용히 접는다
            with self._lock:
                self._예약됨 = False

    def 본문(self, 머리: str = "⏳ 진행 중") -> str:
        with self._lock:
            줄들 = list(self.줄들)
        경과 = time.monotonic() - self.시작
        머리줄 = f"{머리} · 도구 {self.도구수}개 · {경과:.0f}초"
        본 = "\n".join(줄들)
        # **뒤를 남긴다** -- 방금 한 일이 끝에 있다. 잘랐으면 잘랐다고 적는다.
        여유 = self._상한 - len(머리줄) - 20
        if len(본) > 여유:
            본 = "…(앞을 줄였다)\n" + 본[-여유:]
        return f"{머리줄}\n```\n{본}\n```" if 본 else 머리줄

    async def _몰아서편집(self) -> None:
        쉼 = self._최소간격 - (time.monotonic() - self._마지막편집)
        if 쉼 > 0:
            await asyncio.sleep(쉼)
        with self._lock:
            self._예약됨 = False
        if self.끝났다:
            return                     # 마무리가 이미 마지막 편집을 했다
        await self._편집한번(self.본문())

    async def _편집한번(self, text: str) -> None:
        try:
            await self._편집(text)
            self.편집횟수 += 1
            self._마지막편집 = time.monotonic()
        except Exception as e:                                    # noqa: BLE001
            # 편집 실패(삭제된 메시지 · 레이트리밋)로 답 자체가 막히면 안 된다.
            print(f"[relay] 편집 실패: {type(e).__name__}: {e}")

    async def 마무리(self) -> None:
        self.끝났다 = True
        머리 = "✅ 끝" if self.도구수 else "✅ 끝 (도구 호출 없음 -- 답이 실측 없이 나왔다면 의심하라)"
        await self._편집한번(self.본문(머리))


# 도구 줄의 첫 글자. 여기 있는 줄만 '도구 N개' 로 센다.
도구표지 = ("$", "🧪", "✎", "⇉", "🔧", "⛔", "✉", "🔑")
# 스스로 중계 줄을 적는 도구. 그 밖의 도구(search_memory · read_file · orchestrator_*)는
# 코드가 결과 메시지에서 세어 🔧 줄로 적는다 -- 실측 2026-09-11: 사용자가 "도구 호출이
# 계속 0" 이라 했는데, 이 네 개만 세고 있어서 셌든 안 셌든 0 으로 보였다.
스스로적는도구 = ("run_shell", "run_experiment", "edit_file", "delegate")
# thread_id -> 이번 턴에 모델이 부른 도구 이름들 (invoke 결과의 tool_calls 에서 코드가 센 것)
마지막도구: dict[str, list] = {}


def 도구호출들(messages) -> "list[str]":
    """agent.invoke 결과의 messages 에서 **마지막 사람 말 뒤에** 모델이 부른 도구 이름들.
    langchain 메시지를 오리 타이핑으로 본다: type == "human" · AIMessage.tool_calls."""
    턴 = []
    for m in reversed(list(messages or [])):
        if getattr(m, "type", "") == "human":
            break
        턴.append(m)
    out = []
    for m in reversed(턴):
        for tc in (getattr(m, "tool_calls", None) or []):
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if name:
                out.append(str(name))
    return out


def 턴기록(thread_id: str, messages) -> "list[str]":
    """한 턴의 도구 호출을 세어 남기고, 스스로 줄을 안 적는 도구는 🔧 줄로 중계한다."""
    이름들 = 도구호출들(messages)
    마지막도구[thread_id] = 이름들
    for n in 이름들:
        if n not in 스스로적는도구:
            적기(f"🔧 {n}")
    return 이름들


# 실측이 있어야 할 물음의 낌새. 넓게 잡아도 손해는 되묻기 한 번뿐이다.
실측말 = ("시세", "가격", "뉴스", "분석", "만들어", "짜줘", "짜 줘", "돌려", "확인", "검증", "계측",
        "현재", "상태", "파일", "코드", "실행", "테스트", "조회", "찾아", "찾고", "수집", "예측")
되묻는말 = ("[하네스 검사] 앞의 답은 도구를 한 번도 안 불렀다(코드가 셌다). 시세·수치·뉴스·"
          "파일 내용·현재 상태는 도구로 실측해서 다시 답하라 -- run_shell 로 저장소의 "
          "기관(coin/ · dig/ · eval/ …)을 돌리고 그 출력을 근거로 적어라. **오류·실패·거절"
          "(예: 5.7.8, 403, Connection refused)에 관한 물음은 실측 불필요가 아니다** -- "
          "`python3 mailer.py --진단` 같은 진단 도구를 돌리고, `python3 dig/harvest.py --말 '<오류 "
          "문구>'` 로 제2의 뇌에 원인을 모아 search_memory 로 읽고 답하라. 실측이 정말 필요 없는 "
          "물음(개념 설명 · 인사)이면 첫 줄에 '실측 불필요:' 와 까닭을 적고 같은 답을 하라. "
          "**'준비했다'·'반영했다'·'필요하면 말씀해 주세요' 처럼 소개·제안으로 끝내지 마라** -- "
          "지금 한 호흡에 실행하고(dig/paper 로 논문을 읽고, codify 로 수식을 코드로 바꾸고, "
          "harvest 로 수집하고) 그 **출력·파일·원장 줄을 답에 붙여라.** 못 한 것이 있으면 무엇을 왜 "
          "못 했는지 적어라. 사람에게는 최종 승인만 남겨라.")
도구없음표 = ("**[검사] 이 답은 되물었는데도 도구 호출 0회로 나왔다** -- 실측 없는 답이다. "
          "숫자·상태를 근거로 쓰기 전에 의심하라.")
# 실측 2026-09-11: 봇이 일(수집·논문 읽기·코드화)을 **소개만 하고** "필요하면 말씀해 주세요" 로
# 떠넘겼다(도구 0회). 이 문구들이 도구 0회와 같이 나오면 실행 안 하고 말만 한 답이다.
떠넘김말 = ("말씀해 주세요", "말씀해주세요", "말씀해 주시", "필요하시면", "필요하면", "언제든지",
          "준비했습니다", "준비 했습니다", "반영했습니다", "반영 했습니다", "수행하겠", "도와드리겠",
          "진행하겠", "알려주시면", "알려 주시면", "요청해 주", "해 드리겠", "해드리겠",
          # 실측 2026-09-11 네이버 예약 -- 수동 절차를 안내하고 '사용자가 직접' 하라고 넘긴 두 답.
          # 맨몸 '직접' 은 안 쓴다("직접 돌려 봤다" 는 실행한 답이다).
          "부탁드립니다", "부탁드려요", "해 주시길", "해주시길", "하시길 바랍니다", "사용자가 직접",
          "회원님이 직접", "님이 직접", "직접 예약", "직접 검색", "직접 진행해", "유일한 방법", "유일하고")


# 실측 2026-09-11: 봇이 논문·수집·코드화를 **소개만** 하고 떠넘겼다(도구 0회가 아니라, 값싼
# 도구 몇 개만 부르고 정작 무거운 일은 안 했다 -- harvest --관심/eval/graph ask 뒤 떠넘김).
# 그래서 '무거운 일(논문 읽기·코드화·수집 한 바퀴·연구·수리·위임)' 이 하나라도 돌았는지 따로 센다.
무거운도구 = ("codify_paper", "repair", "delegate", "security_audit", "research", "run_experiment")
무거운셸 = ("dig/paper", "codify/run", "codify.py", "harvest --논문", "harvest --틈",
          "harvest.py --말", "research/run", "eval/tasks", "repair/run",
          "dispatch !수집", "dispatch !연구", "dispatch !코드화", "dispatch !고치기", "dispatch !평가", "dispatch !점검")


def 무거운일(thread_id: str, 셸줄들=None) -> bool:
    """이번 턴에 진짜 일(논문·코드화·수집·연구·수리)이 하나라도 돌았는가."""
    names = 마지막도구.get(thread_id) or []
    if any(n in 무거운도구 for n in names):
        return True
    for 줄 in (셸줄들 or []):
        명령 = 줄[0] if isinstance(줄, (list, tuple)) else str(줄)
        if any(s in 명령 for s in 무거운셸):
            return True
    return False


def 떠넘김(reply: str) -> bool:
    """답이 '실행' 대신 '소개·제안·떠넘김' 으로 끝났는가. 도구 0회와 같이 나오면 말만 한 것이다."""
    return any(w in (reply or "") for w in 떠넘김말)


def 실측필요(prompt: str, reply: str) -> bool:
    """도구 0회인 답을 되물을 것인가 -- 물음에 실측 낌새, 답에 수 셋 이상, 또는 떠넘김 문구."""
    if any(w in (prompt or "") for w in 실측말):
        return True
    if 떠넘김(reply):
        return True
    return len(re.findall(r"\d+(?:[.,]\d+)?%?", reply or "")) >= 3


# ---------------------------------------------------------------- 배경 일: 끝나면 알린다
# 실측 2026-09-11: `!평가 과제` · `!수집` · `!고치기` 가 백그라운드로 돌고 나서 끝났다고 아무도
# 말하지 않았다 -- 사람은 돌고 있는지 끝났는지 알 길이 없었다. 띄운 쪽이 여기 등록하고,
# 서버가 pgrep 으로 지켜보다 끝나면 채널에 로그 끝을 붙여 보낸다.
배경들: list = []
_배경_lock = threading.Lock()


def 배경등록(무엇: str, 로그: str, 명령: str = "", 시작바이트: "int | None" = None, 찾을말: str = "") -> dict:
    """`시작바이트` 는 **이 실행이 쓰기 시작한 자리**다. 로그는 덧쓰기(append)라 앞에 옛 실행이
    남아 있다 -- 실측 2026-09-12: 새 실행은 멀쩡히 끝났는데 옛 트레이스백을 읽고 "터졌다" 고
    했고, 진단은 그 옛 줄번호로 "도는 코드가 낡았다" 고 했다. 전부 옛 글이었다.
    **안 주면 0 이다(전부 본다).** 등록 시점에 크기를 재면 안 된다 -- 띄운 뒤에 등록하므로
    자식이 이미 쓴 줄이 잘린다(실측: test_도구수 가 그 자리를 잡았다). 정확한 자리는
    **띄우는 쪽**(`_배경으로`)이 파일을 열기 전에 재서 넘긴다."""
    if 시작바이트 is None:
        시작바이트 = 0
    # `찾을말` 은 pgrep 으로 찾을 이름이다. 실측 2026-09-12(VM): 실행을 `python3 -m improve.run` 으로
    # 바꾸자 명령줄에 "improve/run.py" 가 없어져 첫 확인(20초)에 '끝났다' 고 보고 빈 로그를 읽었다
    # ("(로그가 비었다)" · 0.3분). 보이는 이름과 찾는 이름을 가른다.
    e = {"무엇": 무엇, "로그": str(로그), "명령": 명령, "시작": time.monotonic(), "시작바이트": int(시작바이트),
         "찾을말": 찾을말 or 무엇}
    with _배경_lock:
        배경들.append(e)
    return e


def 배경로그(e: dict) -> str:
    """이 실행이 쓴 부분만. 옛 실행의 글은 안 본다."""
    try:
        with open(e["로그"], "rb") as f:
            f.seek(int(e.get("시작바이트", 0) or 0))
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def 배경꺼내기() -> list:
    with _배경_lock:
        out, 배경들[:] = list(배경들), []
    return out


def 배경끝났나(무엇) -> bool:
    """`무엇` 은 등록 사전이거나 pgrep 으로 찾을 말. 사전이면 **찾을말**로 찾는다(보이는 이름이 아니다)."""
    import subprocess
    if isinstance(무엇, dict):
        무엇 = 무엇.get("찾을말") or 무엇.get("무엇", "")
    p = subprocess.run(["pgrep", "-af", 무엇], capture_output=True, text=True)
    return not [ln for ln in p.stdout.splitlines() if "pgrep" not in ln]


def 어느판(repo=None) -> str:
    """지금 도는 코드가 **어느 커밋인가.** 짧게, 못 알면 빈 말.

    왜: 실측 2026-09-11, 같은 오류가 두 번 왔을 때 '고침이 아직 안 왔나' 인지 '고침이
    틀렸나' 인지 **로그만으로는 못 갈랐다.** 트레이스백의 줄번호를 옛 커밋과 맞춰 보고서야
    알았다. 판을 한 줄 적어 두면 그 한 바퀴를 안 버린다."""
    import subprocess
    try:
        p = subprocess.run(["git", "-C", str(repo or Path(__file__).resolve().parent),
                            "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def 배경보고(e: dict, 줄수: int = 8) -> str:
    경과 = time.monotonic() - e["시작"]
    줄들 = 배경로그(e).strip().splitlines()[-줄수:]
    본 = "\n".join(x[:160] for x in 줄들) or "(로그가 비었다)"
    판 = 어느판()
    return (f"✅ 끝 `{e['무엇']}` ({경과 / 60:.1f}분" + (f" · 판 {판}" if 판 else "") + ")"
            + (f" -- {e['명령'][:80]}" if e.get("명령") else "") + f"\n```\n{본}\n```")


산출물꼴 = re.compile(r"(public_agent_memory/[^\s`'\"]+\.md|codify/out/[^\s`'\"]+\.py|[\w./-]+/ledger\.jsonl)")


# 실측 2026-09-11: `!개선` 이 ModuleNotFoundError 로 죽었고 **그 트레이스백이 그대로 사용자에게
# 갔다.** 사용자: "문제가 생기면 능동적으로 해결해서 결과로 오류 메시지를 출력하지 않게 하라."
# 그래서 오류를 **내보내기 전에** 코드가 알아본다 -- 어느 명령의 어느 버그인지는 안 적는다(일반해).
_터짐꼴 = (
    re.compile(r"^(?P<e>\w*(?:Error|Exception)): (?P<m>.+)$", re.M),          # 파이썬 예외 마지막 줄
    re.compile(r"^\s*(?P<e>Traceback) \(most recent call last\):", re.M),
    re.compile(r"(?P<e>command not found|No such file or directory|Permission denied)", re.M),
)


def 터졌나(e: dict, 줄수: int = 60) -> "tuple[bool, str]":
    """배경 일의 로그 끝에 **터진 자국**이 있는가. (터졌나, 증상 한 줄).

    증상은 repair 에 그대로 넘길 수 있는 글이어야 한다 -- 사람이 읽는 말이 아니라 **재현의 실마리**다."""
    줄들 = 배경로그(e).splitlines()[-줄수:]       # **이 실행이 쓴 부분만** -- 옛 트레이스백은 안 센다
    if not 줄들:
        return False, ""
    본 = "\n".join(줄들)
    마지막예외 = None
    for m in _터짐꼴[0].finditer(본):
        마지막예외 = f"{m.group('e')}: {m.group('m')}".strip()
    if 마지막예외:
        return True, 마지막예외[:300]
    for 꼴 in _터짐꼴[1:]:
        m = 꼴.search(본)
        if m:
            꼬리 = [x for x in 줄들 if x.strip()][-1:] or [m.group("e")]
            return True, 꼬리[0].strip()[:300]
    return False, ""


def 산출물찾기(e: dict, 뿌리=None, 최대: int = 4, 바이트상한: int = 7_000_000) -> "list[str]":
    """배경 일의 로그에서 **사람이 읽을 산출물**(메모 .md · 코드화 .py) 경로를 뽑는다.

    실측 2026-09-11: `!연구` 가 끝나고 로그 끝만 보냈더니 사용자가 "내가 문서를 볼 수 있게
    discord 에 출력해 달라" 고 했다 -- 결론이 담긴 메모는 저장소에만 있었다. 여기서 경로를
    찾아 서버가 파일로 붙여 보낸다. 원장(.jsonl)은 사람이 읽을 것이 아니라 뺀다."""
    뿌리 = Path(뿌리 or Path(__file__).resolve().parent)
    try:
        본 = 배경로그(e)
    except OSError:
        return []
    out = []
    for m in 산출물꼴.finditer(본):
        rel = m.group(1)
        if rel.endswith(".jsonl") or rel in out:
            continue
        p = 뿌리 / rel
        try:
            if p.is_file() and p.stat().st_size <= 바이트상한:
                out.append(rel)
        except OSError:
            continue
    return out[-최대:]


def 등록(판: "중계판 | None") -> None:
    """지금 OS 스레드에 판을 묶는다. run_admin_agent 가 실행기 스레드에서 부른다."""
    with _판들_lock:
        if 판 is None:
            _판들.pop(threading.get_ident(), None)
        else:
            _판들[threading.get_ident()] = 판


def 해제() -> None:
    with _판들_lock:
        _판들.pop(threading.get_ident(), None)


def 적기(줄: str) -> None:
    """지금 스레드에 판이 있으면 적는다. 없으면 아무 일도 안 한다 -- 도구가 이 호출 때문에
    죽으면 안 된다(중계는 부수 기능이다)."""
    with _판들_lock:
        판 = _판들.get(threading.get_ident())
    if 판 is not None:
        try:
            판.적기(줄)
        except Exception as e:                                    # noqa: BLE001
            print(f"[relay] 적기 실패: {type(e).__name__}: {e}")


def 줄(명령: str, 끝값, 초: float, 표지: str = "$") -> str:
    """중계 한 줄의 꼴. 명령은 이미 마스킹돼서 온다."""
    return f"{표지} {명령[:110]}  → exit {끝값} ({초:.1f}s)"


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """고정 명령 `!중계`. dispatch 규약대로 모르는 말은 None."""
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    words = tail.split()
    if not words:
        return HELP
    if words[0] == "상태":
        return f"중계: {'켜짐' if 상태['켜짐'] else '꺼짐'}"
    if words[0] in ("켜기", "끄기"):
        if not allow_write:
            return "중계는 관리 채널에서만 켜고 끈다 -- 프로세스 전역 스위치라서다."
        상태["켜짐"] = words[0] == "켜기"
        return (f"중계 {'켜짐' if 상태['켜짐'] else '꺼짐'}. "
                + ("이제부터 관리 채널 물음마다 진행 메시지가 붙는다 -- 도구·끝값·걸린 초만."
                   if 상태["켜짐"] else "진행 메시지를 안 붙인다."))
    return f"`{words[0]}` 는 모르는 말이다.\n\n{HELP}"
