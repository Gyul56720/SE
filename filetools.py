"""정확 편집 -- 옛 문자열이 **정확히 한 번**일 때만 바꾼다. 전체 덮어쓰기의 반대말이다.

왜 있나: 에이전트의 편집 수단이 sed 와 heredoc 덮어쓰기뿐이었다. 그래서 "라노벨 상황극"
한마디가 scripts/drift.sh 287줄을 20줄 촌극으로 덮었고(4cd4473), 게스트 제한 요청 하나가
discord_bot_server.py 를 통째로 다시 써서 봇이 기동 불가가 됐다(1a82685, 자기 재작성 붕괴).
G005 가 대량 삭제 커밋을 막지만 그것은 커밋 때고, 여기서는 **편집 자체가 그렇게 될 수 없게**
한다: 바꿀 자리를 옛 문자열로 짚고, 그것이 파일에 딱 하나 있어야만 바꾼다.

  0번  -> 거절. 파일을 먼저 read_file 로 보고 실제 글자를 그대로 대라 (들여쓰기 포함)
  2번+ -> 거절. 앞뒤를 더 붙여 하나로 좁혀라
  빈 old -> 거절. 그것은 전체 쓰기다

경로는 toolgate.경로풀기 를 지난다 -- 저장소 밖 · 게이트 · 판정 원장 · .env · .git 은 못 만진다.
표준 라이브러리만 쓴다(봇 없이 검사되고 게이트가 볼 수 있게).
"""
from __future__ import annotations

from pathlib import Path

import toolgate

읽기상한 = 400        # 한 번에 읽는 줄 수
줄상한 = 4000         # 한 줄이 이보다 길면 자른다


def 읽기(path: str, 시작: int = 1, 줄수: int = 읽기상한, repo=None) -> str:
    """줄 번호를 붙여 돌려준다 -- edit_file 의 old 를 정확히 짚으려면 실제 글자를 봐야 한다."""
    p = toolgate.경로풀기(path, 쓰기=False, repo=repo)
    if not p.is_file():
        return f"파일이 없다: {path}"
    줄들 = p.read_text(encoding="utf-8", errors="replace").splitlines()
    시작 = max(1, int(시작))
    줄수 = max(1, min(int(줄수), 읽기상한))
    토막 = 줄들[시작 - 1:시작 - 1 + 줄수]
    if not 토막:
        return f"{path}: {len(줄들)}줄뿐이다 (시작 {시작})"
    폭 = len(str(시작 + len(토막)))
    본 = "\n".join(f"{i:>{폭}}\t{ln[:줄상한]}" for i, ln in enumerate(토막, 시작))
    남 = len(줄들) - (시작 - 1 + len(토막))
    return 본 + (f"\n… (뒤에 {남}줄 더 -- 시작={시작 + len(토막)} 로 이어 읽어라)" if 남 > 0 else "")


def 편집(path: str, old: str, new: str, repo=None) -> str:
    """정확히 한 번 치환. 성공하면 무엇이 얼마나 바뀌었는지, 아니면 왜 거절했는지를 말한다."""
    if not old:
        raise ValueError("old 가 비었다 -- 빈 문자열 치환은 전체 쓰기다. 바꿀 자리를 짚어라")
    if old == new:
        raise ValueError("old 와 new 가 같다 -- 바꿀 것이 없다")
    p = toolgate.경로풀기(path, 쓰기=True, repo=repo)
    if not p.is_file():
        raise ValueError(f"파일이 없다: {path} -- 새 파일은 run_shell 로 만들되 작게")
    text = p.read_text(encoding="utf-8", errors="replace")
    n = text.count(old)
    if n == 0:
        힌트 = ""
        한줄 = old.strip().splitlines()[0] if old.strip() else ""
        if 한줄 and 한줄 in text:
            힌트 = " (첫 줄은 있다 -- 들여쓰기나 줄바꿈이 다르다. read_file 로 실제 글자를 봐라)"
        raise ValueError(f"old 가 파일에 없다{힌트}")
    if n > 1:
        raise ValueError(f"old 가 {n}번 나온다 -- 앞뒤를 더 붙여 하나로 좁혀라")
    새글 = text.replace(old, new, 1)
    p.write_text(새글, encoding="utf-8")
    뺀줄 = len(old.splitlines())          # "x\n" 은 1줄이다 -- count("\n")+1 은 2로 센다
    넣은줄 = len(new.splitlines())
    return f"{p.relative_to(Path(repo or toolgate.REPO).resolve())}: {뺀줄}줄 -> {넣은줄}줄 바꿈"
