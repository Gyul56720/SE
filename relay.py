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
도구표지 = ("$", "🧪", "✎", "⇉", "🔧", "⛔", "✉")
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
          "기관(coin/ · dig/ · eval/ …)을 돌리고 그 출력을 근거로 적어라. 실측이 정말 필요 "
          "없는 물음이면 첫 줄에 '실측 불필요:' 와 까닭을 적고 같은 답을 하라.")
도구없음표 = ("**[검사] 이 답은 되물었는데도 도구 호출 0회로 나왔다** -- 실측 없는 답이다. "
          "숫자·상태를 근거로 쓰기 전에 의심하라.")


def 실측필요(prompt: str, reply: str) -> bool:
    """도구 0회인 답을 되물을 것인가 -- 물음에 실측 낌새가 있거나 답에 수가 셋 이상이면."""
    if any(w in (prompt or "") for w in 실측말):
        return True
    return len(re.findall(r"\d+(?:[.,]\d+)?%?", reply or "")) >= 3


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
