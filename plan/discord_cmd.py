"""`!계획` -- 저장소를 고치는 일을 diff 로 먼저 보이고, 사람이 승인해야 실제 트리에 닿는다.

    !계획 켜기 <요청>   그림자 워크트리를 꺼낸다. 이후 edit_file · run_shell 은 거기서 돈다 (관리 채널)
    !계획 보기          그림자의 diff = 계획 (공개 채널도 읽기는 된다)
    !계획 시험          격리 판에서 미리 돌려 본다 (관리 채널) -- 승인의 전제
    !계획 시험 전부     레포 전체(171개)를 돌려 **회귀**까지 본다 (느리다)
    !계획 승인          실제 트리에 git apply --index (관리 채널) -- 리허설이 초록일 때만
    !계획 버림          그림자를 버린다 (관리 채널)
    !계획 상태
"""
from __future__ import annotations

from plan import store as _판

PREFIX = "!계획"

HELP = f"""**계획 (plan)** -- 고치기 전에 diff 로 계획을 보이고, **사람이 승인해야** 실제 트리에 닿는다
`{PREFIX} 켜기 <요청>` 그림자에서 고치기 시작 (관리 채널) · `{PREFIX} 보기` diff = 계획
`{PREFIX} 시험` **격리 판에서 미리 돌려 본다**(문법·게이트·검사) · `{PREFIX} 시험 전부` 레포 전체 회귀까지
`{PREFIX} 승인` 실제 트리에 적용 (관리 채널, 리허설 초록일 때만) · `{PREFIX} 버림` · `{PREFIX} 상태`"""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    if not text.startswith(PREFIX):
        return None
    tail = text[len(PREFIX):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if not 말:
        return HELP
    words = 말.split(maxsplit=1)
    머리 = words[0]
    if 머리 == "상태":
        return _판.상태()
    if 머리 == "보기":
        return _판.보기()[:1900]
    if not allow_write:
        return "여기서는 읽기만 된다(보기·상태). 켜기·승인·버림은 관리 채널에서 -- 승인 주체가 사람인 것을 그 화이트리스트가 지킨다."
    if 머리 == "켜기":
        if len(words) < 2 or not words[1].strip():
            return f"`{PREFIX} 켜기 <요청>` -- 무엇을 고치려는지 한 줄을 적어라."
        return _판.켜기(words[1], 누가="관리채널")
    if 머리 == "시험":
        전부 = len(words) > 1 and words[1].strip() in ("전부", "전체", "레포")
        return _판.시험하기(전부=전부)[:1900]
    if 머리 == "승인":
        return _판.승인(누가="관리채널")
    if 머리 == "버림":
        return _판.버림()
    return f"모르는 하위 명령 `{머리}`.\n\n{HELP}"
