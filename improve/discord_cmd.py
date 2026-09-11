"""`!자가개선` -- 스스로 틈을 찾아 제2의 뇌를 근거로 패치를 제안하고, 격리 판에서 시뮬레이션해
red->green · 리허설 초록을 코드가 확인한 뒤 **사람의 동의**를 기다린다. 봇은 승인을 대신 못 친다.

    !자가개선              탐색 -> 제안 -> 시뮬 -> 동의 대기  (관리 채널, 배경 -- 모델·sandbox 를 쓴다)
    !개선 <말>             사람이 말한 개선 (레포 전체 시뮬로 회귀를 본다)
    !자가개선 점검         인수 검사(점검)·배선까지 훑어 틈을 찾는다 (느리다, 배경)
    !자가개선 틈           틈만 센다 (모델·sandbox 안 씀)
    !자가개선 승인         동의 -> 실제 트리에 붙인다 (관리 채널, 사람만)
    !자가개선 버림 · 상태
"""
from __future__ import annotations

from pathlib import Path

from eval.discord_cmd import _배경으로
from improve import run as I

PREFIX = "!자가개선"
별칭 = ("!자가개선", "!개선")      # 사용자가 실제로 친 것: "!개선 하고 말하면 되냐?" -- 둘 다 받는다
REPO = Path(__file__).resolve().parent.parent
로그 = REPO / "logs" / "improve.log"

HELP = f"""**자가개선 (improve)** -- 틈을 스스로 찾아(CI 빨강 · 못 푼 수리 · 검사 없는 핵심 모듈 · 점검 실패), 제2의 뇌를
근거로 패치를 제안하고, **격리 판에서** red->green 과 리허설을 코드가 확인한 뒤 **사람의 동의**를 기다린다.
`{PREFIX}` 탐색->제안->시뮬 (배경 -- **틈이 없으면 제2의 뇌로 적용거리를 찾는다**) · `{PREFIX} 점검` 인수 검사·배선까지 (느림) · `{PREFIX} 틈` 틈만
`{PREFIX} <말>` **사람이 말한 개선** -- 제2의 뇌를 근거로 패치를 지어 **레포 전체 시뮬(회귀)** 뒤 동의를 구한다
`{PREFIX} 승인` 동의해 붙인다 (사람만) · `{PREFIX} 버림` · `{PREFIX} 상태` (`!개선` 으로도 친다)
봇이 켜져 있으면 IMPROVE_SEC(기본 6h)마다 스스로 한 번씩 돌아 동의를 구한다."""


def run(text: str, runner=None, allow_write: bool = True) -> "str | None":
    text = (text or "").strip()
    쓴것 = next((x for x in 별칭 if text.startswith(x)), None)
    if 쓴것 is None:
        return None
    tail = text[len(쓴것):]
    if tail and not tail[0].isspace():
        return None
    말 = tail.strip()
    if 말 == "상태":
        return I.상태()
    if 말 == "틈":
        틈들 = I.틈모으기()
        if not 틈들:
            return "틈 없음 -- CI 초록 · 미해결 수리 없음 · 핵심 모듈 검사 다 있음 (`!자가개선 점검` 은 더 깊이 본다)"
        return "\n".join(f"  [{g['종류']}] {g['무엇']}  <- {g['판정명령'][:60]}" for g in 틈들[:15]) + f"\n  틈 {len(틈들)}개"
    if 말 == "도움":
        return HELP
    if not allow_write:
        return "자가개선은 관리 채널에서만 -- 모델·sandbox 를 돌리고, 승인은 사람의 것이다."
    if 말 == "승인":
        return I.승인(누가="관리채널")
    if 말 == "버림":
        return I.버림()
    # **그 밖의 말은 전부 '사람이 말한 개선' 이다.** 사용자: "사용자가 말하는 개선(!개선)을 모두 하게
    # 만들라고." 틈(red->green)이 아니라 부탁이므로 판정은 **레포 전체에 회귀가 없는 것**이다.
    if 말 and 말 != "점검":
        return (runner or _배경으로)(["python3", "improve/run.py", "--부탁", 말], 로그, "improve/run.py")
    argv = ["python3", "improve/run.py"] + (["--점검", "--배선"] if 말 == "점검" else [])
    return (runner or _배경으로)(argv, 로그, "improve/run.py")
