"""
공개 채널(길드, 화이트리스트 없음) 에이전트 -- Gemini + LangGraph.

화이트리스트가 없어 이 채널을 볼 수 있는 누구나 메시지를 보낼 수 있다. run_shell(임의 셸
실행)을 admin과 동일하게 부여한다 -- 화이트리스트 없는 채널에 셸 실행 경로를 열어두는 위험을
사용자가 명시적으로 인지하고 감수하겠다고 요청했다. write_public_answer로 Public_agent/
폴더 밖으로 못 나가는 결과물 저장 도구도 함께 제공한다(public_agent_files.py가 경로를
코드로 강제, git commit까지만 하고 push는 안 함). bot_tools.py의 공유 도구/복구 로직을
그대로 쓴다.

discord_bot_server.py가 이 모듈에서 PUBLIC_CHANNEL_IDS와 run_public_agent()를 가져다 쓴다.
공개 채널은 여럿일 수 있다(DISCORD_PUBLIC_CHANNEL_ID · ..._2 · ...).
"""

from __future__ import annotations

import os

from langgraph.checkpoint.memory import MemorySaver

import agent_context
import channels

from bot_tools import (
    search_memory, save_memory, write_public_answer, run_shell,
    build_agent_pool, run_with_fallback_pool, _current_author,
    register_thread, unregister_thread,
)

# 공개 채널은 **여럿일 수 있다.** DISCORD_PUBLIC_CHANNEL_ID · ..._2 · ..._3 ...
# (쉼표로 여러 개도 된다). 파싱은 `channels.py` 한 자리에서 한다 -- 이 모듈은
# langgraph 를 임포트하므로 그것이 안 깔린 데서는 읽어 볼 수조차 없고, 그러면
# 채널 설정을 잘못 읽는 결손이 검사에 안 걸린다.
PUBLIC_CHANNEL_IDS, PUBLIC_CHANNEL_이상 = channels.공개채널()
if not PUBLIC_CHANNEL_IDS:
    # 예전과 같은 자리에서 같은 오류를 낸다 -- 첫째 변수가 없으면 못 뜬다.
    raise KeyError("DISCORD_PUBLIC_CHANNEL_ID")
# 예전 이름. 밖에서 이것을 쓰던 자리가 안 깨지게 남긴다(첫째 채널).
PUBLIC_CHANNEL_ID = PUBLIC_CHANNEL_IDS[0]
# DISCORD_PUBLIC_GEMINI_MODEL 은 예전 이름이다. 이름이 바뀐 뒤에도 .env 에는 옛 이름이
# 남아 있어서(실측 2026-08-30) 거기 적은 값이 조용히 무시되고 있었다 -- 마침 기본값과 같은
# 값이라 겉으로 드러나지 않았을 뿐, 바꿔 적었다면 아무 일도 일어나지 않았을 것이다.
# 설정이 조용히 무시되는 상황을 없애려고 옛 이름도 받아준다.
PUBLIC_MODEL_NAME = (os.getenv("DISCORD_PUBLIC_MODEL")
                     or os.getenv("DISCORD_PUBLIC_GEMINI_MODEL")
                     or "gemini-3.5-flash-lite")
# GEMINI_MODEL_POOL을 명시하면 그 모델들만 쓴다(수동 제한용). 비워두면 build_agent_pool이
# 키마다 실제 쓸 수 있는 모델 전체를 API로 조회해서 자동으로 순환한다 -- 429는
# (프로젝트, 모델) 단위라 특정 모델이 소진돼도 같은 키의 다른 모델은 살아있을 수 있어서다.
_extra_models = [m.strip() for m in os.getenv("GEMINI_MODEL_POOL", "").split(",") if m.strip()]
PUBLIC_MODEL_CANDIDATES = [PUBLIC_MODEL_NAME] + [m for m in _extra_models if m != PUBLIC_MODEL_NAME] \
    if _extra_models else None

PUBLIC_TOOLS = [search_memory, save_memory, write_public_answer, run_shell]
# admin과 동일한 "적극적으로 조사해서 근거 기반으로 답하라"는 태도로 통일했다 -- 예전엔
# "간결하게/불필요한 수식어 금지" 규칙 때문에, 상태·속도·에러를 묻는 질문에도 조사 없이
# "OK" 한마디로 끝내버리는 경우가 있었다(admin은 run_shell로 journalctl을 직접 뒤져서 표까지
# 만들어 답하는데, public은 같은 질문에 아무것도 확인 안 하고 짧게만 답한 게 실측 확인됨,
# 2026-08-28). 이제는 "짧게"가 아니라 "정보 밀도 높게" -- 답을 늘리려고 말을 채우지는 말되,
# 확인 가능한 근거(로그, 파일 내용 등)가 있으면 반드시 확인하고 그 내용을 압축해서 담아라.
PUBLIC_SYSTEM_PROMPT = (
    "너는 **더 많은 정보를 찾아 주는 에이전트**다. run_shell 로 아무 셸 명령이나 돌릴 수 있다.\n"
    "1. 무엇을 묻든 -- 맛집이든 부품 값이든 논문이든 전적이든 처음 보는 것이든 -- 되는 "
    "방법(api·http·크롤링·파싱)을 다 써서 긁어모아 **구체적으로** 낸다:\n"
    "      python3 dig/run.py --찾기 '<물음>' --파 6 --따라 10 --찾 가격,메뉴  # 주소를 몰라도\n"
    "      python3 dig/run.py --url '<주소>' --따라 12 --찾 가격,메뉴          # 주소를 알면\n"
    "   --찾기 는 검색·위키·논문·지도·github 등 20여 문을 한꺼번에 두드려 주소를 캐고, "
    "--파 가 그 위쪽을 이어서 판다. **한 줄로 끝까지 간다.**\n"
    "   JSON-LD·og·meta·묻힌 json(__NEXT_DATA__)·표·목록·img alt·링크·본문을 다 뽑고, "
    "가격·전화·평점·영업시간·주소·좌표는 정규식으로도 캔다. **거절이 없다.**\n"
    "2. **이름 셋과 별점은 답이 아니다.** 메뉴마다의 값·리뷰 본문·평점과 리뷰 수·"
    "영업시간·휴무·전화·주소·주차·웨이팅까지 있는 대로 다 낸다. 어떤 물음이든 같다.\n"
    "3. **한 주소로 끝내지 마라.** 곁문과 안쪽 링크를 판다 -- 다른 문이 다른 것을 준다. "
    "한 번에 안 나오면 --찾 말을 바꿔 가며 여러 번 불러라. 로그인·유료벽은 안 뚫는다.\n"
    "4. **해 보기 전에 '수단이 없다'고 하지 마라.** 못 하는 것과 안 해 본 것은 다르다. "
    "여러 번 시도하고, 그래도 안 되면 실패한 명령과 오류를 그대로 대라.\n"
    "5. **지어내지 마라.** 못 받았으면 그 자리를 비우고 못 받았다고 하라. 찾은 것마다 "
    "**어디서 왔는지 주소를 붙여라.**\n"
    "6. **출력을 네 말로 요약하지 마라. 그대로 붙여라.** 요약하면 값·리뷰·시간이 통째로 "
    "빠지고, 그것이 사용자가 '정보가 없다'고 하는 그 답이다. Discord 한 메시지는 "
    "2000자이니 네가 줄이지 말고 **여러 메시지로 나눠라.** 인사말·감탄·이모지는 빼고 "
    "그 자리에 근거를 채워라.\n"
    "6-1. 문제 풀이·오답노트를 물으면 `study/`다. 문제는 **지어내지 말고** 사용자가 준 "
    "것이나 dig 로 긁은 것을 넣는다:\n"
    "      python3 study/run.py --넣기 문제.json / --낼것 / --답 <id> '<답>' --메모 '<풀이>'\n"
    "      python3 study/run.py --오답노트 / --취약점 / --교안\n"
    "   취약점은 **세어서** 나온다(이항 꼬리+Holm). 표본이 짧으면 '못잼'이고, 그때 "
    "'약하다'고 네가 대신 말하지 마라 -- 몇 문제 더 풀면 갈리는지는 화면이 적어 준다.\n"
    "6-2. 사유는 **과목이 아니라 어긋난 자리**로 적어라. '확률을 모름'(X) -> "
    "'조건부확률에서 분모를 P(A)가 아니라 전체로 잡는다'(O). 취약점은 태그가 아니라 "
    "이걸로 센다. `--사유 <id> '<무엇이>'` 또는 `--사유프롬프트`로 받은 것을 채워 "
    "`--사유붙이기`. 태그도 같은 자리(`--태그프롬프트`/`--태그붙이기`). **같은 것은 "
    "같은 말로 적어라** -- 닮으면 코드가 묶지만 자를 짜게 뒀으므로(잘못 묶으면 없는 "
    "약점이 교안에 실린다) 다르게 부르면 되풀이가 안 보인다.\n"
    "7. 수를 **재야** 하는 물음(이 움직임이 이례인가·기준선을 이기나)이면 그때만 "
    "brief/report.py · lol/predict.py 를 쓴다.\n"
    "7-1. **암호화폐·코인·비트코인·종목 등락률**을 물으면 `coin/` 이다. 네가 시황을 "
    "쓰지 마라 -- 한 명령이 뉴스(여러 나라)·과거 사건 연구·시나리오 확률까지 낸다:\n"
    "      python3 coin/run.py --물음 '<사용자가 물은 그대로>'\n"
    "   끝값 0 이면 그 출력을 **그대로** 붙여라. 1 이면 답이 원장과 어긋나 안 나온 "
    "것이니 화면에 적힌 어긋난 자리를 그대로 전하고, 3 이면 원장이 비었다는 뜻이니 "
    "`python3 coin/run.py --채우기` 를 먼저 돌려라.\n"
    "   **확률과 수익률을 네가 말하지 마라.** 그 수는 원장에서만 나오고, 관문("
    "`coin/gate.py`, LLM 아님)이 원장에 없는 수를 기각한다. 사거나 팔라고도 하지 "
    "마라 -- 이것은 측정 보고이지 투자 권유가 아니다.\n"
    "8. 기억이 필요하면 search_memory, 사용자가 새로 알려 준 것은 save_memory(잡담은 "
    "말고). 파일로 남길 것은 write_public_answer(Public_agent/ 아래만).\n"
    "9. 이 저장소 코드를 고쳤으면 push 전에 `python3 gatekeeper.py` 를 돌려라.\n"
    "10. 비밀값(.env·API 키·토큰)은 읽어내려 하지 마라 -- 공개 채널 셸에는 없다.\n"
)
# 모든 후보가 같은 MemorySaver를 공유해야 후보 전환이 일어나도 같은 thread_id의 대화
# 맥락이 끊기지 않는다.
_public_checkpointer = MemorySaver()
PUBLIC_AGENT_POOL = build_agent_pool(
    keys=[os.environ["GEMINI_API_KEY"], os.getenv("GEMINI_API_KEY_FALLBACK")],
    models=PUBLIC_MODEL_CANDIDATES,
    tools=PUBLIC_TOOLS,
    prompt=PUBLIC_SYSTEM_PROMPT,
    checkpointer=_public_checkpointer,
    fallback_models=[PUBLIC_MODEL_NAME],
)

_public_thread_map: dict[str, str] = {}


def run_public_agent(prompt: str, thread_id: str, author_id: str = "") -> str:
    """`thread_id` 는 **대화 상태**의 열쇠, `author_id` 는 **기억**의 열쇠다.

    한때 둘이 같았다(둘 다 사람 id). 공개 채널이 여럿이 되면서 갈라야 했다 --
    대화 상태는 방마다 따로여야 하고(다른 방의 문맥이 섞이면 안 된다), 기억은
    사람마다 하나여야 한다(방을 옮겼다고 그 사람을 잊으면 안 된다).
    안 가르고 thread_id 에 채널을 넣으면 **그 사람 기억이 방 수만큼 쪼개진다.**
    """
    print(f"[public-agent] thread={thread_id} prompt={prompt[:120]!r}")
    _current_author.set(author_id or thread_id)
    # 공개 채널 표시. bot_tools.run_shell이 이 값을 보고 자식 프로세스 환경에서 비밀
    # 변수를 지운다(화이트리스트가 없는 채널이므로 누구나 트리거할 수 있다).
    agent_context.current_channel.set("public")
    # stop 명령이 이 스레드가 띄운 run_shell 서브프로세스를 죽이고 fallback 루프를
    # 멈출 수 있도록, 지금 실행 중인 OS 스레드를 discord thread_id에 등록해둔다.
    register_thread(thread_id)
    try:
        reply = run_with_fallback_pool(PUBLIC_AGENT_POOL, _public_thread_map, thread_id, prompt, "[public-agent]")
        print(f"[public-agent] thread={thread_id} reply={reply[:200]!r}")
        return reply
    except Exception as e:
        print(f"[public-agent] thread={thread_id} error={e}")
        return f"(에이전트 오류, 사용 가능한 API 키/모델 조합 모두 실패) {e}"
    finally:
        unregister_thread(thread_id)
