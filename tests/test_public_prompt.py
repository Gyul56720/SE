"""공개 채널 프롬프트가 **평범한 물음을 거절하지 않는가.**

실측 2026-09-13. "다른 기능들은 제공하지 말고" 라는 지시를 프롬프트에 이렇게 옮겼다:

    하는 일은 **둘뿐이다: dig 와 study.** 다른 것은 하지 마라 -- ...
    물어보면 '그건 안 한다' 고 한 줄로 답하고 끝내라.

배포 4분 뒤, 사용자가 `By the way 뜻이머야?` 를 보냈고 봇은 **답을 안 했다.** 대신
프롬프트 1번 줄을 그대로 읊었다 -- "1. 시황·예측·지표·보고서는 안 한다."

**기능을 안 주는 것과 물음을 거절하는 것은 다르다.** 빼야 했던 것은 다른 파이프라인
(coin·brief·lol)을 흉내 내는 일이지, 뜻을 묻는 말에 답하는 일이 아니었다. 프롬프트 한
줄이 그 둘을 뭉갰고, 그것을 잡아 줄 검사가 없었다. 이 파일이 그 자리다.
"""

from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL: list = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 프롬프트글() -> str:
    """`main_public.py` 는 langgraph·GEMINI_API_KEY 가 있어야 임포트된다. 검사 기계에는
    없을 수 있으므로 **글에서 읽는다** -- 임포트가 안 되는 데서도 이 규율은 재야 한다."""
    src = (뿌리 / "main_public.py").read_text(encoding="utf-8")
    i = src.index("PUBLIC_SYSTEM_PROMPT = (")
    return src[i:src.index("\n)\n", i)]


글 = 프롬프트글()

print("== 평범한 물음을 거절하지 않는다 ==")
ok("그냥 답한다" in 글 or "그냥 답하라" in 글,
   "**묻는 말에는 그냥 답하라고 적혀 있다** -- 도구가 없다고 답이 없어지면 안 된다")
ok("거절하지 마라" in 글,
   "**dig 쓸 일이 아니라고 거절하지 말라**고 못박혀 있다")
ok("by the way" in 글.lower(),
   "실제로 거절당한 그 물음이 보기로 적혀 있다 -- 다음 사람이 같은 자리를 안 밟게")
ok("둘뿐이다" not in 글,
   "**'하는 일은 둘뿐이다' 가 없다** -- 그 한 줄이 물음까지 둘 안으로 밀어 넣었다")
ok("한 줄로 답하고 끝내라" not in 글,
   "**'한 줄로 답하고 끝내라' 가 없다** -- 그것이 '대답 없이 끝'의 지시였다")

print("\n== 도구는 **dig 하나뿐이다** ==")
# 사용자 지시 2026-09-13: "study 없애고 dig만 사용해."
# 까닭이 있었다 -- `1+1 문제 풀어줘` 한 줄이 study 갈래로 빠져서, 답(1+1=2) 뒤에 공책
# 파일이 쓰이고 커밋 관문 보고까지 따라붙었다. 물어본 것은 **답**이었다.
ok("study/run.py" not in 글, "`study/run.py` 안내가 **없다**")
ok("--낼것" not in 글 and "--취약점" not in 글 and "--사유붙이기" not in 글,
   "study 옵션 안내가 하나도 안 남아 있다")
ok("dig/run.py" in 글, "`dig/run.py` 는 있다 -- 긁어와야 답할 수 있는 것에 쓴다")
ok("하나뿐이다" in 글 or "하나다" in 글, "**도구가 하나뿐**이라고 적혀 있다")

print("\n== 공부 이야기도 그냥 답한다 ==")
ok("공부" in 글 and "그냥 답" in 글,
   "**공부·문제 이야기도 그냥 답해 주라**고 적혀 있다 -- 공책으로 새지 않는다")
ok("1+1" in 글, "그 일이 보기로 박혀 있다 -- 다음 사람이 같은 자리를 안 밟게")

print("\n== 그래도 다른 파이프라인은 흉내 내지 않는다 ==")
ok("지어서 쓰지 마라" in 글 or "네가 지어" in 글,
   "시황·예측·지표·보고서를 **네가 지어 쓰지 말라**고는 그대로 남아 있다")
for 없어야 in ("coin/run.py", "brief/report.py", "lol/predict.py"):
    ok(없어야 not in 글, f"`{없어야}` 안내가 없다 -- 없는 기능을 흉내 내지 않는다")
ok("병렬" in 글, "앞문을 병렬로 뿌린다는 것을 프롬프트도 안다(--파 를 아끼지 않게)")

print("\n== 배선 ==")
배포 = (뿌리 / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8")
ok("main_public.py" in 배포, "배포가 main_public.py 를 서버에 올린다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("공개 프롬프트: 평범한 물음에 답함 · 공부도 그냥 답함 · study 없음 · dig 하나 -- 통과")
