"""
Oracle VM에서 systemd로 상시 실행되는 Discord 봇 (실시간 Gateway 연결).

관리 채널(admin, 화이트리스트 있음)과 공개 채널(public, 화이트리스트 없음) 둘 다 이제
Gemini + LangGraph 에이전트로 처리한다 (Claude Code 토큰 소진으로 claude -p에서 전환,
2026-08-27). 공개 채널 로직은 main_public.py로, 두 채널이 공유하는 도구(run_shell,
write_public_answer 등)는 bot_tools.py로 분리했다 -- 이 파일은 admin 에이전트 정의 +
Discord 이벤트 라우팅만 담당한다.

admin/public 둘 다 run_shell(임의 셸 실행) 도구를 가지고 있어 self-modification이
가능하다. public은 화이트리스트가 없어 누구나 트리거할 수 있지만, 이 위험(비밀키 유출,
repo 훼손 가능성)을 사용자가 명시적으로 인지하고 감수하겠다고 요청했다. public은 추가로
write_public_answer로 Public_agent/ 폴더 안에만 결과물을 남길 수도 있다.
API 쿼터를 나누려고 admin은 GEMINI_API_KEY_FALLBACK을, public은 GEMINI_API_KEY를 쓴다.

실행: systemd 유닛(deploy/se-discord-bot.service)으로 등록해서 상시 구동할 것.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import discord
from dotenv import load_dotenv

# main_public/bot_tools가 모듈 임포트 시점에 os.environ을 바로 읽으므로, 그것들을 import하기
# 전에 .env를 먼저 로드해야 한다 (실측 확인됨: 순서를 바꾸면 KeyError로 임포트 자체가 실패함).
load_dotenv()

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

import agent_context  # noqa: E402
import channels  # noqa: E402
import agent_memory
import gitsync  # noqa: E402
import gatekeeper  # noqa: E402
import main_public  # noqa: E402
import bot_tools  # noqa: E402
import dispatch  # noqa: E402
import keys  # noqa: E402
import relay  # noqa: E402
from bot_tools import (  # noqa: E402
    REPO_DIR, run_shell, run_experiment, read_file, edit_file, delegate, send_email, repair, set_key, search_memory, save_memory,
    build_agent_pool, run_with_fallback_pool,
    register_thread, unregister_thread, request_cancel,
    orchestrator_solve, orchestrator_status, orchestrator_resume, orchestrator_stop,
)

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
# 관리자 채널(화이트리스트 있음, DISCORD_ALLOWED_USER_IDS): run_shell 전권 + git sync.
# **빈 값으로 죽지 않게** channels.수() 로 읽는다. `int(os.getenv(...))` 는 키가 있고
# 값이 비면 `""` 를 그대로 넘겨 ValueError 를 내고, 그것이 모듈 읽는 중이라 봇이
# 통째로 멎는다(실측 2026-09-09, systemd 가 5초마다 되살리기를 13번 되풀이했다).
ADMIN_CHANNEL_ID = channels.수("DISCORD_CHANNEL_ID", 1542081266315427912)
# 이 서버(길드)에서 온 것만 받는다. **비우면 안 본다** -- 예전처럼 채널 id 로만 가린다.
#
# 채널 id 는 디스코드 전체에서 유일하므로 이것 없이도 남의 서버 글이 섞이지는 않는다.
# 그런데 공개 채널에는 **사용자 화이트리스트가 없다**(main_public.py). 그러면 남은
# 경계가 '그 채널인가' 하나뿐이고, 봇이 실수로 다른 서버에 초대되거나 채널 id 를
# 잘못 넣으면 그 하나가 통째로 없어진다. 길드까지 보면 경계가 둘이 된다.
GUILD_ID = channels.수("DISCORD_GUILD_ID", 0)
ADMIN_ALLOWED_USER_IDS = {int(x) for x in os.getenv("DISCORD_ALLOWED_USER_IDS", "").split(",") if x.strip()}
ADMIN_MODEL_NAME = os.getenv("DISCORD_ADMIN_MODEL", "gemini-3.5-flash-lite")
# GEMINI_MODEL_POOL을 명시하면 그 모델들만 쓴다(수동 제한용). 비워두면 build_agent_pool이
# 키마다 실제 쓸 수 있는 모델 전체를 API로 조회해서 자동으로 순환한다.
_admin_extra_models = [m.strip() for m in os.getenv("GEMINI_MODEL_POOL", "").split(",") if m.strip()]
ADMIN_MODEL_CANDIDATES = [ADMIN_MODEL_NAME] + [m for m in _admin_extra_models if m != ADMIN_MODEL_NAME] \
    if _admin_extra_models else None
# public과 API 쿼터를 분리하려고 별도 fallback 키를 쓴다 -- 한쪽이 무제한 루프를 돌려도(self
# -modification 특성상 발생 가능) 다른 채널까지 같이 막히지 않게. 다만 fallback 키를 못 챙겨서
# 비어있는 채로 배포되면 admin 채널 전체가 KeyError로 기동 자체를 못 하고 죽었다(실측 확인됨,
# 2026-08-27) -- 그래서 없거나 비어있을 땐 GEMINI_API_KEY를 대신 쓴다. 게다가 admin 자기
# 기본 키(FALLBACK)가 429로 소진돼도 public처럼 실시간으로 다른 키/모델로 못 넘어가서 계속
# 막혔었다(실측 확인됨, 2026-08-28) -- 그래서 public과 동일한 (키 x 모델) 후보 풀로 바꿨다.
ADMIN_PRIMARY_KEY = os.getenv("GEMINI_API_KEY_FALLBACK") or os.environ["GEMINI_API_KEY"]
ADMIN_SECONDARY_KEY = os.environ["GEMINI_API_KEY"] if os.getenv("GEMINI_API_KEY_FALLBACK") else None

ADMIN_TOOLS = [run_shell, run_experiment, read_file, edit_file, delegate, send_email, repair, set_key, search_memory, save_memory,
               orchestrator_solve, orchestrator_status, orchestrator_resume,
               orchestrator_stop]
ADMIN_SYSTEM_PROMPT = (
    "너는 이 저장소(SE)를 관리하는 전권을 가진 에이전트다. run_shell로 파일을 읽고 쓰고,\n"
    "git commit/push하고, 네 자신의 코드(discord_bot_server.py, main_public.py, "
    "bot_tools.py 등)를 수정할 수 있다.\n"
    "run_shell 권한은 사용자가 명시적으로 요청한 것이다 -- 에러가 나도 스스로 이 도구를 "
    "제거하거나 권한을 축소하지 마라. 대신 에러 원인을 파악해서 고쳐라.\n"
    "요청받은 작업을 run_shell로 직접 수행하고, 명령 결과를 근거로 다음 행동을 결정하라.\n"
    "코드를 고쳤으면 그 결과를 run_shell로 git add/commit/push까지 해서 반영하라.\n"
    "무엇을 했는지 간결하게 보고하라.\n"
    "\n"
    "[자기 수정 절차 -- 반드시 이 순서로]\n"
    "1. 기존 파일은 전체를 다시 쓰지 마라. **read_file 로 그 자리를 본 뒤 edit_file 로 "
    "바꿀 줄만 고쳐라** -- old 가 정확히 한 번일 때만 바뀐다. run_shell 의 sed -i · heredoc "
    "덮어쓰기는 쓰지 마라(그 형태가 4cd4473 · 1a82685 사고다). 고친 뒤 git diff --stat의 "
    "삭제 줄 수가 요청 크기와 맞는지 확인하라.\n"
    "1-1. run_shell 은 돌기 전에 도구 게이트를 지난다(toolgate). 게이트 삭제·판정 원장 "
    "덮어쓰기·통째 삭제·--force·rebase·pkill -f 는 거절된다 -- 우회하지 말고 다른 길을 써라.\n"
    "2. push 전에 `python3 gatekeeper.py`를 돌려라. 통과(exit 0)해야 커밋된다. "
    "py_compile은 문법만 잡는다 -- 게이트는 임포트 순환, 독스트링 소실, 안전장치 삭제, "
    "자격증명 노출, 대량 삭제를 잡는다.\n"
    "3. 무언가 고장 냈다면 원인을 진단하고, 그 진단을 말로 주장하지 말고 검사 코드로 "
    "써서 `python3 self_challenge.py prove --candidate <검사> --broken-commit <사고커밋>` "
    "으로 증명하라. 고치기 전 코드에서 실패(RED)하고 고친 뒤 통과(GREEN)해야 PROVEN=1 이다. "
    "고치기 전 코드에서 통과해버리면 그건 원인이 아니었다 -- 진단을 다시 세워라.\n"
    "4. PROVEN=1 이면 그 검사는 gates/ 로 승격되어 이후 모든 커밋을 막는다. "
    "증명되지 않은 진단은 메모리 노트로도 남기지 마라 -- 읽히지 않는 노트가 늘어나는 것이 "
    "이 저장소가 실제로 겪은 실패다(2026-08-28: 검증 규칙을 저장하고 2분 뒤 그 규칙을 "
    "어긴 코드를 push했다).\n"
    "5. 보고는 기억이 아니라 git diff 출력을 보고 적어라. 함께 커밋된 파일이 있으면 "
    "요청과 무관해도 보고에 포함하라.\n"
    "\n"
    "[orchestrator -- 여러 단계로 쪼개야 풀리는 문제]\n"
    "한 번에 답이 안 나오고 계획->계산->검증이 필요한 문제(수학 문제, 알고리즘 설계, "
    "데이터 처리 파이프라인 등)는 네가 채팅 안에서 추론으로 때우지 말고 orchestrator_solve "
    "로 넘겨라. 플래너가 DAG 로 쪼개고 노드마다 verifier 가 판정해서 검증된 결과만 채택한다 "
    "-- 네 추론과 달리 결과에 근거가 남는다.\n"
    "런은 백그라운드로 돈다(수 분). orchestrator_solve 가 돌려준 런 이름을 사용자에게 알리고 "
    "그 턴을 끝내라 -- run_shell로 sleep을 걸어 기다리지 마라. 나중에 물어보면 "
    "orchestrator_status 로 확인해서 답하고, 미완인데 프로세스가 없으면 orchestrator_resume "
    "으로 이어 돌려라. 상태를 추측해서 말하지 말고 반드시 도구 출력을 근거로 답하라.\n"
    "\n"
    "[기관 -- 자연어로 부탁받으면 이 이름들을 직접 돌려라]\n"
    "사용자는 `!실험` 처럼 치지 않고 그냥 말로 부탁한다. 그때 **네가 아래를 골라 돌려라.**\n"
    "아래 것을 직접 짜지 마라 -- 이미 있고, 검사가 붙어 있고, 원장에 근거가 남는다.\n"
    "  · 실험·검증·'고치면 어떻게 되나' -> run_experiment 도구 (깨끗한 판, 저장소 안 다침)\n"
    "  · 파일 여럿을 살펴야 하는 물음 -> delegate 도구 (싼 탐색기에 동시에 던지고 원문에 "
    "실재하는 인용만 받는다). 네가 cat 으로 수십 개를 읽지 마라 -- 비싸고 느리다\n"
    "  · 바꾼 것이 성한가 -> `python3 audit/run.py` (바뀐 파일을 붙드는 검사만 골라 돌린다)\n"
    "  · 기억·전에 뭐라고 했나 -> search_memory 먼저. 간추리기는 `python3 graph/night.py`, "
    "깃발 조회는 `python3 graph/ask.py --말 '<말>'`, 요지문은 graph/digest.md\n"
    "  · 뭐가 깨졌나·상태 점검 -> `python3 eval/run.py` (빠른 갈래. 전부는 몇 분 걸린다). "
    "'참고(기억)를 주면 더 맞히나'·과제 성적 -> `python3 eval/tasks.py --참고 둘다` (모델을 "
    "과제 수 x 2 번 부른다 -- 배경으로)\n"
    "  · 밖에서 참고 모으기·제2의 뇌 -> `python3 dig/harvest.py --틈` (자가 틀린 자리를 GitHub·HF "
    "에서 채운다) 또는 `--말 '<검색어>'`. 라이선스·문법은 코드가 거른다\n"
    "  · 메일 -> send_email 도구. SMTP 코드를 짜거나 사용법을 설명하지 마라\n"
    "  · **오류·실패를 만나면 -> repair 도구**(재현 명령 + 오류 문구). 실측→제2의 뇌→시도→실측을 "
    "코드가 돌리고 실패 이유를 기억에 남긴다. 네가 손으로 세 번 해 보거나 '정책 때문' 이라 하지 마라\n"
    "\n"
    "[사람에게 묻기 전에 -- 자가 해결 단계가 먼저다]\n"
    "순서는 고정이다: (1) repair 도구(재현 명령 + 증상)로 실측→제2의 뇌(dig/harvest + search_memory)"
    "→시도→실측을 돌린다 (2) 그래도 남으면 '해 본 것' 과 함께 **사람만 할 수 있는 한 가지**만 묻는다. "
    "(1) 없이 (2) 로 가지 마라. 코드 자가 수정·자가 분석도 같다 -- 저장소를 고치기 전에 search_memory 와 "
    "delegate 로 제2의 뇌와 저장소를 먼저 읽어라.\n"
    "\n"
    "[수단이 없을 때 -- 설명하고 멈추지 마라]\n"
    "실측 2026-09-11: 메일 부탁에 앱 비밀번호 발급 절차와 smtplib 코드를 설명하고 멈췄고, 다음엔 "
    "'인프라가 없다' 고 멈췄고, 다음엔 '무료 SMTP 가입하거나 앱 비밀번호를 주면' 하고 선택지를 "
    "나열했다. 셋 다 틀렸다. 규칙: **네가 얻을 수 있는 것은 네가 얻어라**(pip · 설정 파일 · "
    "접속 · 재시도). **사람만 할 수 있는 것**(계정 가입 · 2단계 인증 · 앱 비밀번호/토큰 발급 · "
    "결제)은 선택지를 나열하지 말고 **제일 짧은 길 하나를 골라 딱 그 값만** `!열쇠 이름=값` "
    "꼴로 청하라. 받았다고 하면 묻지 말고 바로 이어서 하라. 도구가 '무엇이 없다' 고 돌려주면 "
    "그 말을 그대로 전하면 된다. **사용자가 채팅으로 값을 주면(비밀번호·토큰·주소) 되묻지 말고 "
    "set_key 로 즉시 .env 에 적어라** -- 네 대화 기억은 재시작(배포)마다 사라지고 .env 만 남는다 "
    "(실측 2026-09-11: 준 값을 잊고 다시 물었다). **오류 문구(5.7.8 · 403 · refused …)를 받으면 '정책 때문' 이라 "
    "보고하고 멈추지 마라** -- 진단 도구(`python3 mailer.py --진단`)를 돌리고, `python3 dig/harvest.py "
    "--말 '<오류 문구>'` 로 제2의 뇌에 원인을 모은 뒤 search_memory 로 읽고, 해 본 것과 남은 한 "
    "가지를 적어라.\n"
    "  · 어느 모델로 나가나·비용 -> `python3 router/call.py --요약` · `python3 router/check.py`\n"
    "  · 할 일·목표 -> `python3 intent/store.py --목록` / `--다음`. **새 목표는 제안까지만 "
    "하고 승인은 사람에게 받아라** -- 승인 없는 목표는 집히지 않는다(그것이 설계다)\n"
    "  · 게이트·자기 개조 -> `python3 gatekeeper.py`, 승격은 self_challenge 의 red-green\n"
    "  · 소설·이어쓰기 -> `scripts/drift.sh` (novel 파이프라인). **네가 산문을 지어내지 "
    "말고 그 스크립트도 덮지 마라** -- 실측 2026-09-10 `4cd4473`: '라노벨 상황극' 부탁 "
    "하나가 drift.sh 287줄을 20줄 촌극으로 덮어 열 곳 넘는 참조가 끊겼다\n"
    "  · 진행 상황을 보고 싶다는 말 -> 네가 켜지 말고 `!중계 켜기` 를 치라고 안내하라 "
    "(사람이 켜는 스위치다. 도구·끝값·걸린 초만 보이고 네 생각은 안 실린다)\n"
    "각 폴더의 README.md 가 무엇을 하는지 적고 있다 -- 모르면 먼저 읽어라. 그리고 "
    "**사용자가 `!` 로 시작하는 고정 명령을 쳤다면 그것은 너에게 오지 않는다**(봇이 먼저 "
    "받는다). 너에게 왔다면 고정 명령이 아닌 말이므로, 네가 위에서 골라 돌리면 된다."
)
_admin_checkpointer = MemorySaver()
ADMIN_AGENT_POOL = build_agent_pool(
    keys=[ADMIN_PRIMARY_KEY, ADMIN_SECONDARY_KEY],
    models=ADMIN_MODEL_CANDIDATES,
    tools=ADMIN_TOOLS,
    prompt=ADMIN_SYSTEM_PROMPT,
    checkpointer=_admin_checkpointer,
    fallback_models=[ADMIN_MODEL_NAME],
)

PROJECT_SLUG = REPO_DIR.replace("/", "-")
# claude -p용 세션 ID. 토큰이 복구되면 run_claude()를 다시 쓸 수 있도록 남겨둔다.
SESSION_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, f"discord-channel-{ADMIN_CHANNEL_ID}"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# git_sync()가 동시에 여러 번 돌면 커밋/푸시가 충돌하므로 직렬화한다.
GIT_LOCK = asyncio.Lock()

_admin_thread_map: dict[str, str] = {}

# thread_id별 현재 처리 중인 on_message 태스크와 그 프롬프트. "stop" 입력 시 이 태스크만
# 취소한다 -- 서비스(systemd 유닛) 전체를 내리는 게 아니라 그 대화의 응답 대기만 중단한다.
# 주의: run_shell로 이미 시작된 서브프로세스는 취소해도 백그라운드 스레드에서 계속 돌다가
# 자연 종료된다(진짜 kill이 아님) -- 취소는 "그 결과를 기다리지 않고 지금까지 상황을
# 보고한다"는 뜻이다.
_active_tasks: dict[str, asyncio.Task] = {}
_active_prompts: dict[str, str] = {}
# thread_id 별 자물쇠. 같은 대화에 두 실행이 겹치면 도구 호출과 그 답이 어긋나
# 대화가 통째로 깨진다(INVALID_CHAT_HISTORY). 방마다 하나씩이라 서로 안 막는다.
_thread_locks: dict[str, asyncio.Lock] = {}

# **"못 받았다" 는 말이 사실인지 잰다.**
#
# 실측 2026-09-09: 공개 채널이 "외부 네트워크 차단 및 보안 정책(403 Forbidden 등)으로
# 직접적인 데이터 수집이 제한되고 있습니다" 라고 답했다. 사용자가 같은 주소를 VM 에서
# 직접 돌려 보고 **"안막혔어"** 라고 했다. 즉 **안 해 보고 막혔다고 한 것**이다.
#
# 프롬프트에는 이미 적혀 있었다 -- "해 보기 전에 '수단이 없다' 고 하지 마라",
# "안 되면 실패한 명령과 오류를 그대로 대라"(규칙 4·5). **적혀 있는데 어겼다.**
# 그러면 규칙을 더 적을 것이 아니라 **말이 사실인지 코드가 재야 한다** -- 이 저장소가
# 봇의 자동 rebase 에서 배운 것과 같다(규칙은 사람에게 적혀 있었고 그 줄은 봇에게
# 적혀 있었다).
#
# 잡는 것은 **거짓말이 아니라 어긋남**이다: 못 받았다고 하는데 부른 것이 없거나,
# 부른 것이 다 성공했는데 못 받았다고 하는 것. 답을 지우지는 않는다 -- 옆에 적는다.
못받았다말 = ("차단", "막혀", "막았", "403", "수집이 제한", "접근이 제한",
             "긁어올 수 없", "가져올 수 없", "조회할 수 없", "제한되고 있",
             "직접 접근이 불가", "실시간 데이터를 제공할 수 없")


def _말과_한것이_맞나(reply: str, 부른것: list) -> str:
    """답이 '못 받았다' 고 하는데 실제로 한 것과 어긋나면 그 말을 돌려준다."""
    if not reply or not any(w in reply for w in 못받았다말):
        return ""
    if not 부른것:
        return ("**[검사] 이 답은 '못 받았다' 고 하는데 이번 턴에 셸을 한 번도 "
                "안 불렀다.** 막힌 것이 아니라 **안 해 본 것**이다. "
                "`python3 dig/run.py --url '<주소>'` 를 실제로 돌리고, "
                "그래도 안 되면 그 명령과 오류를 그대로 붙여라.")
    실패 = [c for c, ok in 부른것 if not ok]
    if not 실패:
        return (f"**[검사] 이 답은 '못 받았다' 고 하는데 부른 {len(부른것)}개가 "
                "전부 성공했다.** 무엇이 막혔는지 그 출력으로 보여라.")
    return ""


async def _handle_stop(message: discord.Message, thread_id: str) -> None:
    task = _active_tasks.get(thread_id)
    if task is None or task.done():
        await message.channel.send("[중단] 현재 진행 중인 요청이 없습니다.")
        return
    prompt = _active_prompts.get(thread_id, "(알 수 없음)")
    # request_cancel: (1) 다음 fallback 후보로 넘어가기 전에 루프를 멈추게 하는 플래그를
    # 세우고, (2) 이 스레드가 run_shell로 이미 띄운 서브프로세스가 있으면 실제로
    # terminate/kill한다 -- proc.wait(timeout=3)이 섞여 있어 이벤트 루프를 막지 않게
    # 실행기(executor)에서 돌린다.
    loop = asyncio.get_running_loop()
    killed = await loop.run_in_executor(None, request_cancel, thread_id)
    task.cancel()
    note = "실행 중이던 run_shell 서브프로세스를 강제 종료했습니다." if killed else \
        "죽일 서브프로세스는 없었고, 다음 모델/키 후보로 넘어가기 전 루프를 멈춥니다(이미 나간 API 요청 자체는 취소 불가)."
    await message.channel.send(
        "[중단됨] 이번 응답 생성을 멈췄습니다. 봇 자체는 계속 실행 중입니다.\n"
        f"진행 중이던 프롬프트: {prompt[:300]}\n"
        f"{note}"
    )


def run_claude(prompt: str) -> str:
    """Claude Code 토큰이 있을 때 쓰던 경로. 지금은 호출되지 않지만 토큰 복구 시 다시
    _handle_admin_message에서 run_admin_agent 대신 이걸 쓰도록 되돌리면 된다."""
    jsonl_path = os.path.expanduser(f"~/.claude/projects/{PROJECT_SLUG}/{SESSION_ID}.jsonl")
    resume_flag = ["--resume", SESSION_ID] if os.path.isfile(jsonl_path) else ["--session-id", SESSION_ID]
    # se-discord-bot.service의 cgroup 밖에서 돌려서, 이 안에서 백그라운드로 뜬 작업이
    # 서비스 재배포(systemctl restart)에 딸려 죽지 않게 한다 (실측 확인됨: cgroup 안에 있으면
    # KillMode=control-group 기본값 때문에 setsid로 분리해도 재배포 시 다 같이 죽었음).
    scope_unit = f"se-claude-{uuid.uuid4().hex[:12]}"
    result = subprocess.run(
        [
            "sudo", "-E", "systemd-run", "--scope", "--quiet", "--collect",
            "--uid=ubuntu", "--gid=ubuntu", f"--unit={scope_unit}",
            "--", "claude", "-p", *resume_flag, "--permission-mode", "bypassPermissions", prompt,
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    return out if out else (err or "(출력 없음)")


def git_sync() -> str | None:
    """작업 트리에 변경이 있으면 커밋 + push. 변경 없으면 None 반환.

    이 VM 말고 다른 곳(예: 개발 세션)에서도 같은 repo에 직접 push할 수 있어서, origin이
    이 VM의 로컬 HEAD보다 앞서 있는 경우(non-fast-forward)가 실제로 발생한다. 그럴 때 단순
    `git push`는 거부되고 그대로 실패만 반환했는데, 그러면 이 VM에서 만든 변경이 origin에
    영영 반영이 안 되고(Obsidian이 못 받아봄) 조용히 로컬에만 쌓이게 된다. 그래서 push가
    non-fast-forward로 거부되면 **지금 브랜치의 origin을 merge**하고 한 번 더 시도한다.
    rebase가 아니고 origin/main도 아니다 -- `_reconcile()` 의 사고 기록을 볼 것.

    공개/관리 채널 에이전트의 save_memory나 run_shell도 같은 워킹트리에 커밋할 수 있으므로,
    스레드 간에도 통하는 agent_memory.GIT_MUTEX를 함께 잡아서 여러 경로가 동시에 git을
    만지지 않게 한다."""
    with agent_memory.GIT_MUTEX:
        return _git_sync_locked()




def _verify_pushed() -> str:
    """push가 성공 리턴코드를 줬어도 그걸로 끝내지 않고, 로컬 HEAD가 실제로 origin에
    반영됐는지 fetch로 재확인한다.

    2026-08-29 사고: 관리 채널 에이전트가 'requirements.txt에 X 추가하고 커밋했다,
    해시 539e168'이라고 보고했는데 그 해시는 origin 어디에도 없었다. push 성공을 그대로
    믿고 보고하면 로컬에만 쌓인 커밋이나 지어낸 해시를 사용자가 걸러낼 수 없다. 이 저장소
    메모리에 이미 '산출물은 원격 반영까지 확인하고 보고하라'가 있었지만(20260828-190336)
    코드가 강제하지 않아 또 어겨졌다. 그래서 보고 문자열 자체를 fetch 확인 결과로 만든다.

    실제 반영 여부만 보고한다 -- 지어낼 해시가 없다."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                          capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    contains = subprocess.run(
        ["git", "branch", "-r", "--contains", head, "origin/main"],
        cwd=REPO_DIR, capture_output=True, text=True,
    )
    short = head[:7]
    if contains.returncode == 0 and "origin/main" in contains.stdout:
        return f"[git push 확인됨] origin/main에 {short} 반영됨. Obsidian에서 pull하면 보입니다."
    return (f"[경고] push는 리턴코드 0이었으나 origin/main에서 {short}를 확인하지 못했다 -- "
            f"원격 반영 실패 가능. 로컬에만 커밋됐을 수 있으니 수동 확인하라.")


# 에이전트가 "저장소에 무언가를 남겼다"고 주장할 때 쓰는 신호어. 이게 응답에 있는데 정작
# 이번 턴에 커밋된 변경이 없으면(git_sync가 None), 주장과 실제 저장소 상태가 어긋난 것이다.
# 2026-08-29에 admin/public 에이전트가 "result.md 저장", "searcher 전면 개편", "history
# 축적"을 보고했지만 원격엔 해당 커밋/파일이 없었다(4회 반복). 메모리 노트로는 못 막혀서
# 봇 레벨에서 실제 원격 상태를 자동 대조해 사용자에게 알린다.
_PERSISTENCE_CLAIM_HINTS = (
    "커밋", "commit", "푸시", "push", "저장했", "저장 완료", "저장하였", "반영",
    "구현했", "구현하였", "생성했", "생성하였", "작성했", "작성하였", "추가했", "추가하였",
    "개편", "수정했", "수정하였", "변경했", "변경하였", "고쳤", "갱신했", "업데이트했",
    "history.jsonl", "result.md", ".py를", ".py에", "파일에 저장",
)


def _claims_persistence(reply: str) -> bool:
    low = reply.lower()
    return any(h.lower() in low for h in _PERSISTENCE_CLAIM_HINTS)


def _remote_status_note() -> str:
    """현재 로컬 HEAD가 원격에 반영돼 있는지, 미커밋 변경이 남아있는지 사실만 보고한다.
    에이전트의 주장이 아니라 저장소의 실제 상태다."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                          capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True, text=True)
    contains = subprocess.run(["git", "branch", "-r", "--contains", head],
                              cwd=REPO_DIR, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR,
                           capture_output=True, text=True).stdout.strip()
    on_remote = contains.returncode == 0 and "origin/" in contains.stdout
    short = head[:7]
    parts = [f"HEAD {short}"]
    parts.append("원격 반영됨" if on_remote else "⚠️ 원격 미반영")
    parts.append("미커밋 변경 있음" if dirty else "미커밋 변경 없음")
    return "[저장소 상태 자동확인] " + " · ".join(parts)


def _integrity_note(reply: str, sync_note: str | None) -> str | None:
    """에이전트가 저장소에 뭔가 남겼다고 '주장'했는데 이번 턴 git_sync가 아무것도 커밋하지
    않았다면(sync_note is None), 실제 원격 상태를 대조해 붙인다. git_sync가 이미 커밋/차단
    결과를 냈으면(sync_note가 있으면) 그게 진실을 보여주므로 중복하지 않는다."""
    if sync_note is not None:
        return None
    if not _claims_persistence(reply):
        return None
    note = _remote_status_note()
    return (f"{note}\n(에이전트가 저장/커밋을 주장했으나 이번 턴에 커밋된 변경은 없습니다 -- "
            f"위 상태로 실제 반영 여부를 확인하세요.)")


def _git_sync_locked() -> str | None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if not status.stdout.strip():
        return None

    # 강제 게이트. 에이전트가 메모리 노트를 읽었는지와 무관하게 여기서 막힌다 -- 그것이
    # 요점이다. 2026-08-28에 에이전트는 "push 전에 임포트부터 시켜봐라"를 저장하고 2분 뒤
    # 임포트 불가 코드를 push했다. 진단은 저장소의 마크다운에 있었을 뿐 커밋 경로 위에
    # 없었다. 게이트를 통과 못 하면 커밋하지 않고 위반 목록을 그대로 돌려준다.
    report = gatekeeper.run_gates(Path(REPO_DIR))
    if not report.passed:
        print(f"[git_sync] 게이트 차단 -- 커밋하지 않음\n{report.summary()}")
        return report.summary()

    # check=True 로 두면 실패가 CalledProcessError 로 튀어나와 호출자의 답변 전송까지
    # 무너뜨린다. 게다가 이제 이 저장소에는 git 작성자가 둘이다 -- 이 봇과, 별도
    # 프로세스(se-matrix-search)로 도는 improve_agent 다. GIT_MUTEX 는 파이썬 스레드
    # 락이라 프로세스 경계를 못 넘으므로, add 와 commit 사이에 improve_agent 가 커밋해
    # 인덱스를 비워버리면 여기 commit 이 "nothing to commit"(exit 1)으로 실패한다
    # (실측 2026-08-30). 그건 정상 상황이므로 조용히 넘어가되, 그 외의 실패는 반드시
    # 보고한다 -- "실패를 전부 무시"로 뭉뚱그리면 게이트/훅이 막은 것도 성공한 척하게 된다.
    add = subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, capture_output=True, text=True)
    if add.returncode != 0:
        return f"[git add 실패] {add.stderr.strip()}"

    commit = subprocess.run(
        ["git", "commit", "-m", "SE-agent: Discord 요청 처리 결과 자동 반영"],
        cwd=REPO_DIR, capture_output=True, text=True,
    )
    if commit.returncode != 0:
        combined = f"{commit.stdout}\n{commit.stderr}"
        if "nothing to commit" in combined or "no changes added to commit" in combined:
            # 다른 작성자가 먼저 커밋해 갔다. 남길 변경이 없으니 할 일이 끝난 것이다.
            return None
        return f"[git commit 실패] {combined.strip()[:500]}"
    push = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if push.returncode == 0:
        return f"{report.summary()}\n{_verify_pushed()}"

    caught, why = gitsync.reconcile(
        lambda a: subprocess.run(["git", *a], cwd=REPO_DIR, capture_output=True, text=True))
    if not caught:
        return (f"[git push 실패] origin이 앞서 있어 따라잡으려 했으나 안 됐다: {why}\n"
                f"{push.stderr.strip()}")

    retry = subprocess.run(["git", "push"], cwd=REPO_DIR, capture_output=True, text=True)
    if retry.returncode != 0:
        return f"[git push 실패] {why} 뒤에도 실패: {retry.stderr.strip()}"
    return f"({why} 뒤 재시도) " + _verify_pushed()


def run_admin_agent(prompt: str, thread_id: str, 중계판=None) -> str:
    """관리 채널용 -- LangGraph ReAct 에이전트(Gemini, run_shell 전권)로 답한다.
    중계판이 있으면 이 실행기 스레드에 묶어, 도구가 돌 때마다 진행 메시지가 갱신된다."""
    print(f"[admin-agent] thread={thread_id} prompt={prompt[:120]!r}")
    relay.등록(중계판)
    # 요청 맥락을 채운다. 예전에는 admin 경로만 이걸 빼먹어서 호출자 ID가 늘 "unknown"이었고
    # (실측 2026-09-02), save_memory가 남기는 작성자도 전부 "unknown"이었다 -- 추적하려고
    # 작성자를 남기는 설계가 admin 쪽에서만 성립하지 않았다.
    agent_context.current_author.set(thread_id.removeprefix("admin-"))
    # 채널 종류. run_shell이 이 값을 보고 공개 채널에서만 자식 환경의 비밀값을 지운다 --
    # admin은 배포/탐색 스크립트가 실제로 그 키들을 필요로 하므로 그대로 둔다.
    agent_context.current_channel.set("admin")
    # stop 명령이 이 스레드가 띄운 run_shell 서브프로세스를 죽이고 fallback 루프를 멈출 수
    # 있도록, 지금 실행 중인 OS 스레드를 discord thread_id에 등록해둔다.
    register_thread(thread_id)
    try:
        reply = run_with_fallback_pool(ADMIN_AGENT_POOL, _admin_thread_map, thread_id, prompt, "[admin-agent]")
        # **도구 0회 답은 한 번 되묻는다.** 실측 2026-09-11: chainlink 시세·뉴스 분석 같은
        # 물음에 에이전트가 도구를 한 번도 안 부르고 지식으로 답했다. 규칙을 더 적지 않고
        # 코드가 센 도구 수(relay.마지막도구)로 판정해 실측을 요구한다. 그래도 0 이면 답에
        # 그렇다고 적는다 -- 답을 지우지는 않는다.
        if not relay.마지막도구.get(thread_id) and relay.실측필요(prompt, reply):
            print(f"[admin-agent] thread={thread_id} 도구 0회 -- 실측 요구 되묻기")
            relay.적기("↺ 도구 0회 -- 실측을 요구하고 한 번 되묻는다")
            reply = run_with_fallback_pool(ADMIN_AGENT_POOL, _admin_thread_map, thread_id,
                                           relay.되묻는말, "[admin-agent]")
            if not relay.마지막도구.get(thread_id):
                reply = f"{reply}\n\n{relay.도구없음표}"
        print(f"[admin-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[admin-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류) {e}"
    finally:
        relay.해제()
        unregister_thread(thread_id)


@client.event
async def on_ready():
    print(
        f"[SE-agent] 로그인됨: {client.user} "
        f"(관리 채널 {ADMIN_CHANNEL_ID}, 공개 채널 "
        f"{', '.join(str(c) for c in main_public.PUBLIC_CHANNEL_IDS)} 감시 중"
        + (f", 길드 {GUILD_ID} 만" if GUILD_ID else ", 길드 안 가림") + ")"
    )
    # **켜질 때 확인한다.** 길드 id 를 잘못 넣으면 봇이 조용히 아무 말도 안 듣는데,
    # 그것은 '봇이 죽었다' 와 화면에서 똑같이 보인다. 여기서 한 번 말해 주면 갈린다.
    # **켜질 때 채널을 하나씩 확인한다.** 채널 id 를 잘못 넣으면 봇이 그 채널에서
    # 조용히 아무 말도 안 듣는데, 그것이 '봇이 죽었다' 와 화면에서 똑같이 보인다.
    # 길드 id 를 채널 자리에 넣는 것이 특히 흔하다 -- 둘 다 같은 꼴의 수라 눈으로는
    # 안 갈리고, 넣어도 아무 오류가 안 난다(그냥 영영 안 맞을 뿐이다).
    if channels.이상한값:
        print(f"[SE-agent] **경고: 수로 못 읽은 설정** {channels.이상한값} -- "
              "기본값으로 돌아갔다. 딴 채널을 보고 있을 수 있다")
    if main_public.PUBLIC_CHANNEL_이상:
        print(f"[SE-agent] **경고: 채널 id 로 못 읽은 값** "
              f"{main_public.PUBLIC_CHANNEL_이상} -- 그 채널은 안 듣는다")
    for cid in [ADMIN_CHANNEL_ID] + list(main_public.PUBLIC_CHANNEL_IDS):
        ch = client.get_channel(cid) or client.get_partial_messageable(cid)
        if getattr(ch, "guild", None) is None and not hasattr(ch, "name"):
            # **DM 은 캐시에 없으면 get_channel 이 None 을 준다.** 그것을 '못 찾았다'
            # 로 찍으면 멀쩡한 관리 채널에 거짓 경고가 난다(실측 2026-09-09).
            # DM 은 길드가 없으므로 길드 필터와도 무관하다 -- 아무 말 안 한다.
            continue
        if ch:
            # **보이는 것과 듣는 것은 다르다.** 길드 필터가 켜져 있는데 그 채널이
            # 다른 길드에 있으면, 봇은 채널을 멀쩡히 보면서 그 채널의 메시지를
            # 전부 버린다 -- `on_message` 가 길드부터 보기 때문이다. 그러면 화면에는
            # '감시 중' 이라고 찍히는데 실제로는 아무 말도 안 듣는다.
            # 실측 2026-09-09: 8월에 만든 채널들과 9월에 만든 길드를 같이 켰다.
            그길드 = getattr(getattr(ch, "guild", None), "id", None)
            if GUILD_ID and 그길드 != GUILD_ID:
                print(f"[SE-agent] **경고: 채널 {cid} 는 길드 {그길드} 에 있는데 "
                      f"DISCORD_GUILD_ID 는 {GUILD_ID} 다.** 채널은 보이지만 "
                      "**그 채널 메시지는 전부 버려진다.** 길드를 그 값으로 바꾸거나 "
                      "DISCORD_GUILD_ID 를 비워라")
            continue
        왜 = ("**이건 길드 id 다** -- 채널 자리에 넣으면 영영 안 맞는다"
              if cid == GUILD_ID else
              "봇이 그 채널을 못 본다 (id 가 틀렸거나 권한이 없다)")
        print(f"[SE-agent] **경고: 채널 {cid} 를 못 찾았다.** {왜}. "
              "이대로면 그 채널에서 아무 말도 안 듣는다")

    if GUILD_ID and not client.get_guild(GUILD_ID):
        # **이건 봇이 통째로 안 듣는 자리다.** 채널 하나가 아니라 전부.
        채널인가 = client.get_channel(GUILD_ID)
        print(f"[SE-agent] ***** 봇이 아무 말도 안 듣는다 *****")
        print(f"[SE-agent] DISCORD_GUILD_ID={GUILD_ID} 인데 그런 길드가 없다.")
        if 채널인가:
            print(f"[SE-agent] **이건 길드가 아니라 채널이다** "
                  f"('{채널인가}') -- 길드 자리에 채널 id 를 넣으면 "
                  "message.guild.id 와 절대 안 맞아 모든 메시지를 버린다.")
        print(f"[SE-agent] 들어가 있는 길드: {[g.id for g in client.guilds]}")
        print("[SE-agent] **DISCORD_GUILD_ID 를 비워라** -- 비면 검사를 아예 안 "
              "하므로 예전과 똑같이 돈다. 틀린 값을 넣느니 비우는 것이 낫다.")


ATTACHMENTS_DIR = os.path.join(REPO_DIR, "inbox", "discord_attachments")


async def _save_attachments(message: discord.Message) -> list[str]:
    """스크린샷 등 첨부파일을 로컬에 저장하고 절대경로 목록을 반환한다.
    에이전트는 텍스트 프롬프트만 받으므로, 이미지 자체를 전달할 방법이 없다 -- 대신 파일로
    저장한 뒤 그 경로를 프롬프트에 적어주면 run_shell(cat 등)로 직접 열어볼 수 있다."""
    if not message.attachments:
        return []
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    saved_paths = []
    for att in message.attachments:
        safe_name = f"{message.id}_{att.filename}"
        path = os.path.join(ATTACHMENTS_DIR, safe_name)
        await att.save(path)
        saved_paths.append(path)
    return saved_paths


async def _handle_admin_message(message: discord.Message) -> None:
    """관리 채널: Gemini+LangGraph 에이전트(run_shell 전권) + git sync."""
    if ADMIN_ALLOWED_USER_IDS and message.author.id not in ADMIN_ALLOWED_USER_IDS:
        return
    content = message.content.strip()
    thread_id = f"admin-{message.author.id}"

    if content.lower() == "stop":
        await _handle_stop(message, thread_id)
        return

    attachment_paths = await _save_attachments(message)
    if not content and not attachment_paths:
        return
    if attachment_paths:
        attachments_note = "\n\n첨부 파일(로컬 경로, run_shell로 cat/열어볼 것):\n" + "\n".join(
            f"- {p}" for p in attachment_paths
        )
        content = (content or "(첨부파일 확인)") + attachments_note

    loop = asyncio.get_running_loop()
    _active_tasks[thread_id] = asyncio.current_task()
    _active_prompts[thread_id] = content
    reply = None
    sync_note = None
    integrity_note = None
    # 도구 중계: 켜져 있으면 진행 메시지 하나를 먼저 띄우고, 도구가 돌 때마다 그것을 갱신한다.
    # 답이 오기 전까지 봇이 멈춘 듯 보이는 것을 없앤다 -- 보이는 것은 검사 가능한 것뿐이다.
    중계판 = None
    if relay.상태["켜짐"]:
        try:
            진행메시지 = await message.channel.send("⏳ 진행 중 · 도구 0개")
            중계판 = relay.중계판(lambda t: 진행메시지.edit(content=t), loop)
        except Exception as e:                                    # noqa: BLE001
            print(f"[relay] 진행 메시지를 못 띄웠다: {type(e).__name__}: {e}")
    try:
        async with message.channel.typing():
            reply = await loop.run_in_executor(None, run_admin_agent, content, thread_id, 중계판)
            if 중계판 is not None:
                await 중계판.마무리()
            # 사용자가 채팅으로 준 값을 에이전트가 set_key 로 적었으면 그 메시지는 채널에 남으면
            # 안 된다 (실측 2026-09-11: 앱 비밀번호가 채널에 그대로 남았다).
            if "set_key" in (relay.마지막도구.get(thread_id) or []):
                try:
                    await message.delete()
                except Exception as e:                              # noqa: BLE001
                    print(f"[keys] 값을 적은 메시지를 못 지움: {type(e).__name__}: {e}")
            # 답변은 이미 완성됐다. 이후 단계(git 동기화 등)에서 무슨 일이 나든 답변 전달을
            # 막아서는 안 된다 -- 예전엔 이 블록 전체가 하나의 try 였고 except가
            # CancelledError만 잡아서, git_sync가 던진 예외가 그대로 전파되며 전송 루프에
            # 도달하지 못했다(실측 2026-08-30: 답변이 로그에는 찍혔는데 Discord로는 안 감).
            # 그래서 여기서부터는 실패를 예외가 아니라 '보고할 메모'로 바꾼다.
            sync_note, integrity_note = await _sync_and_note(loop, message, reply)
    except asyncio.CancelledError:
        # "stop"으로 취소됨 -- _handle_stop이 이미 상태 메시지를 보냈으므로 조용히 반환한다.
        return
    finally:
        _active_tasks.pop(thread_id, None)
        _active_prompts.pop(thread_id, None)

    # reply 가 None 이면 에이전트 호출 자체가 실패한 것이다. 그 경우에도 사용자가 무응답을
    # 겪지 않도록 사유를 알린다(예전엔 여기서 NameError 가 나며 아무것도 못 보냈다).
    if not reply:
        await message.channel.send("(응답 생성 실패 -- 로그를 확인하세요)")
    for chunk_start in range(0, len(reply or ""), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)
    if integrity_note:
        await message.channel.send(integrity_note)


async def _sync_and_note(loop, message: discord.Message, reply: str) -> "tuple[str | None, str | None]":
    """답변 생성 이후 단계(git 동기화 + 무결성 확인)를 돌리고 그 결과를 메모로 돌려준다.

    여기서 예외를 밖으로 내보내지 않는 것이 핵심이다. 답변은 이미 만들어져 있는데 부수
    단계의 실패로 사용자가 답을 못 받는 일은 없어야 한다. 다만 '조용히 삼키는' 것도 안 된다
    -- 실패하면 그 사유를 메모에 담아 답변과 함께 보낸다. 그래야 "답은 왔는데 저장은 안 됨"을
    사용자가 알 수 있다.

    CancelledError는 stop 명령의 정상 경로이므로 그대로 올려보낸다.
    """
    sync_note = None
    integrity_note = None
    try:
        # 게스트 보안 정책: 차단 목록(agent_context.BLOCKED_USER_IDS, 환경변수
        # GUEST_BLOCKED_USER_IDS로 지정)에 든 사용자는 git sync를 타지 않는다.
        if agent_context.is_blocked(message.author.id):
            sync_note = "[보안 제한] 게스트 사용자의 Git 접근이 제한되었습니다."
        else:
            async with GIT_LOCK:
                sync_note = await loop.run_in_executor(None, git_sync)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        sync_note = f"[git 동기화 실패] {type(e).__name__}: {e} -- 답변은 정상이며 저장만 실패했다."
        print(f"[git_sync] 예외: {type(e).__name__}: {e}")

    try:
        async with GIT_LOCK:
            integrity_note = await loop.run_in_executor(None, _integrity_note, reply, sync_note)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        integrity_note = f"[무결성 확인 실패] {type(e).__name__}: {e}"
        print(f"[_integrity_note] 예외: {type(e).__name__}: {e}")

    return sync_note, integrity_note


async def _handle_public_message(message: discord.Message) -> None:
    """공개 채널: 화이트리스트 없음 -- main_public.py의 에이전트(run_shell 포함)로 답한다.
    유저별로 대화 맥락이 이어진다."""
    content = message.content.strip()
    if not content:
        return

    # **방마다 다른 대화.** 한때 사람 id 하나였는데, 같은 사람이 두 채널에서 물으면
    # **같은 LangGraph 스레드 위에서 두 실행이 겹쳤다**(실측 2026-09-09: 10:17:30 에
    # 채널 2 요청이 dig 를 두 번 부른 뒤, 8초 만에 채널 1 요청이 같은 스레드로 들어와
    # 채널 2 쪽이 잘렸다). 겹치면 도구 호출과 그 답이 어긋나서
    # `Found AIMessages with tool_calls that do not have a corresponding ToolMessage`
    # 가 난다 -- 10:05:19 에 실제로 났다.
    thread_id = f"{message.channel.id}:{message.author.id}"
    author_id = str(message.author.id)
    # **어느 채널에서 온 것인지 남긴다.** 공개 채널이 여럿이 된 뒤로 로그만 보고는
    # 어느 채널의 요청인지 알 수가 없었다 -- 둘의 성능이 다를 때 견줄 것이 없다.
    # thread_id 가 채널이 아니라 **사람**이라는 것도 여기 같이 보인다: 같은 사람이
    # 두 채널에서 물으면 맥락이 이어지고, 다른 사람이 물으면 빈 맥락에서 시작한다.
    print(f"[public] ch={message.channel.id} author={message.author.id} "
          f"thread={thread_id}")

    if content.lower() == "stop":
        await _handle_stop(message, thread_id)
        return

    loop = asyncio.get_running_loop()
    # **stop 이 줄 서 있는 것도 끊을 수 있게** 자물쇠보다 먼저 등록한다.
    _active_tasks[thread_id] = asyncio.current_task()
    _active_prompts[thread_id] = content
    reply = None
    sync_note = None
    integrity_note = None
    try:
        # **한 대화에서 한 번에 하나만.** 같은 방에 두 물음이 잇달아 오면 예전에는
        # 둘이 같은 스레드 위에서 동시에 돌았다(실측 10:13:32/10:13:35 -- 3초 사이에
        # 두 번 들어와 답이 두 번 나갔다). 도구 호출과 답이 어긋나면 그 대화가
        # 통째로 깨진다. 줄을 세운다 -- 늦어질 뿐 안 깨진다.
        async with _thread_locks.setdefault(thread_id, asyncio.Lock()):
            async with message.channel.typing():
                reply = await loop.run_in_executor(
                    None, main_public.run_public_agent, content, thread_id, author_id)
            부른것 = bot_tools.마지막셸.get(thread_id) or []
            어긋남 = _말과_한것이_맞나(reply, 부른것)
            if 어긋남:
                print(f"[public] ch={message.channel.id} **어긋남** "
                      f"셸 {len(부른것)}회 -- {어긋남[:80]}")
                reply = f"{reply}\n\n{어긋남}"
            # admin 경로와 같은 이유로 git 단계의 실패가 답변 전달을 막지 못하게 한다.
            sync_note, integrity_note = await _sync_and_note(loop, message, reply)
    except asyncio.CancelledError:
        return
    finally:
        _active_tasks.pop(thread_id, None)
        _active_prompts.pop(thread_id, None)

    # reply 가 None 이면 에이전트 호출 자체가 실패한 것이다. 그 경우에도 사용자가 무응답을
    # 겪지 않도록 사유를 알린다(예전엔 여기서 NameError 가 나며 아무것도 못 보냈다).
    if not reply:
        await message.channel.send("(응답 생성 실패 -- 로그를 확인하세요)")
    for chunk_start in range(0, len(reply or ""), 1900):
        await message.channel.send(reply[chunk_start:chunk_start + 1900] or "(빈 응답)")
    if sync_note:
        await message.channel.send(sync_note)
    if integrity_note:
        await message.channel.send(integrity_note)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # **길드가 정해져 있으면 그 길드만.** 다만 **DM 은 여기서 안 거른다.**
    #
    # 실측 2026-09-09: 관리 채널(1542081266315427912)이 서버 채널이 아니라 **DM**
    # 이었다(`type=1, guild=None`). DM 은 `message.guild` 가 None 이라 이 검사에
    # 절대 안 맞고, 그래서 길드를 켜는 순간 **관리 채널이 통째로 죽었다.**
    # 길드 필터는 '남의 서버 글을 안 받겠다' 는 뜻이지 'DM 을 안 받겠다' 가 아니다.
    #
    # DM 을 통과시켜도 경계는 안 무너진다 -- 아래에서 채널 id 로 한 번 더 거르고,
    # 관리 채널은 사용자 화이트리스트까지 있다.
    if GUILD_ID and message.guild is not None and message.guild.id != GUILD_ID:
        return
    admin = message.channel.id == ADMIN_CHANNEL_ID
    public = message.channel.id in main_public.PUBLIC_CHANNEL_IDS
    if not (admin or public):
        return

    # **고정 명령이 먼저다 -- 그런데 아는 접두사(`!소설` · `!실험`)로 시작하는 것만.**
    # 배선은 dispatch.py 한 곳에 있다 -- 새 기관의 명령은 거기 목록에 넣는다.
    #
    # 배포판이란 남이 같은 말을 쳤을 때 같은 일이 나는 것이다. 에이전트는 그것을 보장하지
    # 않는다 -- 매번 다르게 알아듣고, 때로는 저장소를 고친다(실측 2026-09-10 `4cd4473`:
    # "라노벨 상황극" 요청이 `scripts/drift.sh` 를 20줄짜리 촌극으로 덮었다).
    #
    # **셸을 뺏는 것이 아니다.** `dispatch.run` 은 모르는 말에 `None` 을 돌려주고,
    # 그러면 아래로 떨어져 예전 그대로 에이전트(run_shell 전권)가 받는다. VM 을 셸로
    # 만져야 하는 일은 하나도 안 줄어든다 -- 한 갈래가 그 앞에 생겼을 뿐이다.
    #
    # 쓰는 명령(시작 · 이어 · 멈춤 · 보내기)은 **관리 채널의 화이트리스트 안에서만** 듣는다.
    # 공개 채널은 누구나 치므로 읽는 것만 -- `멈춤` 하나로 밤새 도는 런이 죽는다.
    may_write = admin and (not ADMIN_ALLOWED_USER_IDS
                           or message.author.id in ADMIN_ALLOWED_USER_IDS)
    reply = await asyncio.to_thread(dispatch.run, message.content, None, may_write)
    if reply is not None:
        await message.reply(reply[:2000])
        # `!열쇠 이름=값` 은 값이 채널에 남는다 -- 지울 권한이 있으면 지운다. 못 지우면
        # 답이 이미 "이 메시지는 지워라" 고 말했다.
        if message.content.startswith(keys.PREFIX) and "=" in message.content:
            try:
                await message.delete()
            except Exception as e:                                  # noqa: BLE001
                print(f"[keys] 메시지 못 지움: {type(e).__name__}: {e}")
        return

    if admin:
        await _handle_admin_message(message)
    else:
        await _handle_public_message(message)


if __name__ == "__main__":
    client.run(BOT_TOKEN)
