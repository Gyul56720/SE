"""고정 명령의 배선 -- 한 곳에서 잇는다.

배포판이란 남이 같은 말을 쳤을 때 같은 일이 나는 것이고, 그것을 보장하는 것은
에이전트가 아니라 고정 명령이다(`novel/discord_cmd.py` 의 사고 기록). 명령 모듈이
둘이 되면서(!소설 · !실험) 봇이 모듈마다 한 줄씩 부르는 대신 여기 한 줄만 부른다 --
새 기관의 명령은 이 목록에 한 줄 넣으면 배선이 끝난다.

규약: 각 모듈은 PREFIX 와 run(text, runner=None, allow_write=True) 를 가지고,
**모르는 말에는 None 을 돌려준다.** 그러면 다음 모듈로, 다 모르면 에이전트로 간다 --
이 파일이 기존 동작을 뺏지 않는다.
"""
from __future__ import annotations

from audit import discord_cmd as 감사
from codify import discord_cmd as 코드화
from delegate import discord_cmd as 위임
from dig import discord_cmd as 수집
from eval import discord_cmd as 평가
from evolve import discord_cmd as 진화
from graph import discord_cmd as 기억
from intent import discord_cmd as 목표
from novel import discord_cmd as 소설
from repair import discord_cmd as 고치기
from research import discord_cmd as 연구
from plan import discord_cmd as 계획
from improve import discord_cmd as 자가개선
from investigate import discord_cmd as 조사
from secaudit import discord_cmd as 점검
from router import discord_cmd as 경로
from sandbox import discord_cmd as 실험
from falsegreen import discord_cmd as 거짓초록
import keys as 열쇠
import relay as 중계

명령들 = (소설, 실험, 감사, 기억, 평가, 경로, 목표, 진화, 중계, 위임, 수집, 열쇠, 고치기, 점검, 코드화, 연구, 계획, 자가개선, 조사, 거짓초록)


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    """첫 번째로 알아듣는 명령 모듈의 답. 아무도 모르면 None(에이전트로)."""
    for 모듈 in 명령들:
        reply = 모듈.run(text, runner, allow_write)
        if reply is not None:
            return reply
    return None


# 사람이 치는 것과 봇이 치는 것의 경계. 실측 2026-09-11: 봇이 자연어 부탁에 고정 명령 **목록을
# 보여 주고** 끝냈다 -- 목록이 아니라 알맞은 명령을 제가 쳐야 한다. 단 승인 주체는 사람이다:
# `!목표 승인` `!계획 승인` 과 비밀값을 받는 `!열쇠` 는 봇이 대신 치지 못한다.
사람만 = ("승인", "머지")          # `!조사 머지 <번호>` -- 문제가 있는 PR 을 그래도 붙이는 확정은 사람이 친다


def 도구로쳐도되나(text: str) -> "tuple[bool, str]":
    t = (text or "").strip()
    if not t.startswith("!"):
        return False, "고정 명령은 `!` 로 시작한다"
    머리 = t.split(maxsplit=2)
    if 머리[0] == "!열쇠":
        return False, "!열쇠 는 사람이 친다 -- 비밀값을 봇이 대신 넣지 않는다"
    if 머리[0] == "!머지":
        return False, "!머지 는 사람이 친다 -- 문제가 있는 PR 을 그래도 붙이는 확정은 사람이다"
    if len(머리) > 1 and 머리[1] in 사람만:
        return False, f"`{머리[0]} {머리[1]}` 은 사람만 친다 -- 승인 주체는 사람이다(관리 채널 화이트리스트)"
    return True, ""


# ---------------------------------------------------------------- 자연어 -> 고정 명령 (코드가 고른다)
#
# 실측 2026-09-11: 사용자가 자연어로 부탁했는데 봇이 **고정 명령 목록을 보여 주고** 끝냈다.
# 사용자: "사용자의 자연어를 적절하게 해석해서 도구를 호출해야 한다."
#
# 그래서 고르는 일을 모델의 재량에 두지 않고 **표로 못박는다.** 모델은 부탁을 그대로 넘기고,
# 어느 명령인지는 이 표가 정한다. 못 고르면 None 과 **까닭**을 준다 -- 아무 명령이나 치지 않는다.
# (승인·열쇠는 여기서도 안 고른다. 사람이 치는 것이다 -- 도구로쳐도되나 가 한 번 더 막는다.)
import re as _re
import re

_아이디꼴 = _re.compile(r"\b(\d{4}\.\d{4,5})\b")


def _아이디(말: str) -> str:
    m = _아이디꼴.search(말 or "")
    return m.group(1) if m else ""


# (이름, 실마리 정규식, 만들기) -- 위에서부터 먼저 걸리는 것이 이긴다(구체적인 것이 위).
자연어표 = [
    ("승인", r"승인|approve|열쇠|토큰\s*(?:넣|등록|설정)|비밀번호",
     lambda 말: (None, "승인·열쇠는 **사람이 친다** -- `!목표 승인 <id>` · `!계획 승인` · `!열쇠 이름=값` 을 사람에게 청하라")),
    ("자가개선", r"자가\s*개선|스스로\s*(?:개선|고쳐|나아)|self.?improve|개선\s*(?:제안|해\s*봐|해\s*줘|할\s*(?:것|점))|어디를?\s*개선",
     lambda 말: ("!자가개선 점검" if re.search(r"점검|깊이|전부|샅샅", 말) else "!자가개선", "")),
    ("코드화", r"코드화|코드로\s*(?:바꿔|만들|옮)|수식.*(?:구현|코드)|알고리즘.*코드|논문.*구현|\d{4}\.\d{4,5}[^\n]{0,10}(?:구현|코드)",
     lambda 말: ((f"!코드화 논문 {_아이디(말)}", "") if _아이디(말)
                else (None, "arXiv id 가 없다 -- `!코드화 논문 <id>` 꼴이어야 한다. id 를 모르면 `!연구 <주제>` 로 먼저 찾아라"))),
    ("계획시험", r"(?:돌려|시험|시뮬|리허설)[^\n]{0,10}(?:보|해|하)|바꾸기\s*전에|미리\s*(?:돌려|시험)|계획[^\n]{0,4}(?:시험|리허설)",
     lambda 말: ("!계획 시험", "")),
    ("계획", r"(?:저장소|코드|파일|\.py)[^\n]{0,12}(?:고쳐|수정|바꿔|추가|붙여|만들)|리팩터|기능[^\n]{0,8}(?:추가|붙여|만들)",
     lambda 말: (f"!계획 켜기 {말.strip()[:180]}", "")),
    # 긴 호흡. "끝까지" · "시간이 걸려도" · "파헤쳐" 는 한 턴짜리 고치기가 아니라 조사다.
    # '조사해' 는 안 건다 -- "시세 방법론 조사해줘" 같은 연구 부탁까지 삼킨다(실측 test_dispatch_tool).
    ("조사", r"끝까지\s*(?:고쳐|풀어|해결|파)|시간이?\s*(?:걸려도|들어도)|파헤쳐|원인[^\n]{0,6}(?:찾아|캐|밝혀)|될\s*때까지",
     lambda 말: (f"!조사 {말.strip()[:180]}", "")),
    ("고치기", r"고치기|오류|에러|실패하는|안\s*돌아|깨졌|repair|터졌|죽었",
     lambda 말: (None, "재현 명령과 증상이 필요하다 -- `!고치기 <재현 명령> :: <증상>` 또는 repair 도구를 직접 불러라")),
    ("점검", r"보안|취약|해킹|포트|방화벽|점검해",
     lambda 말: ("!점검", "")),
    ("평가", r"평가|눈금|과제|참고.*이득|자를\s*대|벤치",
     lambda 말: ("!평가 과제", "")),
    ("감사", r"감사|바뀐\s*(?:것|파일).*검사|변경.*검사",
     lambda 말: ("!감사", "")),
    ("실험", r"검사(?:해|를|만)?\s*(?:돌려|해줘|해봐)?|테스트|게이트.*(?:돌려|확인)",
     lambda 말: ("!실험 게이트", "")),
    ("기억밤", r"간추|밤\s*돌려|장기\s*기억|요지문",
     lambda 말: ("!기억 밤", "")),
    ("기억", r"기억|전에\s*뭐|무엇을\s*배웠|깃발",
     lambda 말: (f"!기억 {말.strip()[:100]}", "")),
    ("경로", r"비용|쿼터|어떤\s*모델|모델\s*(?:표|현황)|라우팅|경로",
     lambda 말: ("!경로 요약", "")),
    ("수집틈", r"틈|약점|스스로.*(?:메워|채워)|자가.*수집",
     lambda 말: ("!수집 틈으로", "")),
    ("연구", r"연구|조사|알아봐|찾아봐|방법론|논문|최신|모아|수집|자료|정리해",
     lambda 말: (f"!연구 {말.strip()[:180]}", "")),
    ("목표", r"목표|할\s*일|무엇을\s*할",
     lambda 말: ("!목표 목록", "")),
    ("진화", r"진화|자기\s*개조|게이트\s*(?:몇|현황)",
     lambda 말: ("!진화", "")),
    ("소설", r"소설|이어\s*써|집필|원고",
     lambda 말: ("!소설 상태", "")),
]


def 고르기(말: str) -> "tuple[str | None, str]":
    """자연어 부탁 -> (고정 명령, "") 또는 (None, 까닭). 판정은 모델이 아니라 이 표가 한다."""
    t = (말 or "").strip()
    if not t:
        return None, "빈 말이다"
    if t.startswith("!"):
        return t, ""
    for _이름, 패턴, 만들기 in 자연어표:
        if _re.search(패턴, t):
            return 만들기(t)
    return None, ("어느 고정 명령인지 못 골랐다 -- 부탁을 더 또렷이 하거나, 도구(research · codify_paper · "
                  "repair · security_audit)를 직접 불러라")
