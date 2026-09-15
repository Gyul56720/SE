"""`circuitdraw` -- 회로도가 **실제로 그려지나.**

사용자(2026-09-15): "회로 설계에 사용되는 그림들(cmos nmos capacitor inductor ...
current mirror 등)이나, 원리를 설명해주는 그런 기능도 필요해."

## 무엇을 붙드나

여기서는 **진짜로 PNG 를 만든다.** 글자만 보면 안 되는 자리다 -- 이 저장소가 오늘
그것으로 두 번 거짓 초록을 냈다. 그리고 그리는 것보다 **안 그려진 것을 안 그려졌다고
말하는 것**이 더 중요하다: 못 그렸는데 그렸다고 하면 사용자는 빈 자리를 본다.

  1. 본보기 넷이 다 **그려진다** (그리고 PNG 가 빈 파일이 아니다)
  2. 틀린 코드는 **왜 틀렸는지** 말한다 -- 조용히 빈 그림을 내지 않는다
  3. 들여쓴 코드를 그대로 받는다 (dedent 를 strip 보다 먼저 -- 실측으로 넷 다 터졌다)
  4. 모르는 본보기 이름은 아는 이름을 알려준다
  5. 배선 -- 두 채널이 도구를 싣고, 봇이 그림을 답에 붙여 보낸다
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


try:
    import schemdraw                                              # noqa: F401
except ImportError as e:
    print(f"  건너뜀  schemdraw 가 없다: {e}")
    print("(requirements.txt 에 있다 -- 배포가 깐다. 여기서는 배선만 본다)")
    schemdraw = None

import circuitdraw as C                                           # noqa: E402

판 = Path(tempfile.mkdtemp(prefix="회로-검사-"))
try:
    if schemdraw is not None:
        print("== 본보기가 다 그려진다 ==")
        for 이름 in C.본보기:
            쪽 = 판 / f"{이름}.png"
            r = C.본보기그리기(이름, str(쪽))
            ok(r["됐나"], f"`{이름}` 이 그려진다 -- {r['왜'][:90]}")
            if r["됐나"]:
                # **빈 파일이 아니어야 한다.** 파일만 있고 비어 있으면 사용자는 깨진
                # 그림을 본다 -- 그것은 못 그린 것과 같다.
                ok(쪽.is_file() and 쪽.stat().st_size > 1000,
                   f"`{이름}` PNG 가 성하다 ({쪽.stat().st_size if 쪽.is_file() else 0}바이트)")

        print("\n== 들여쓴 코드를 그대로 받는다 ==")
        # 본보기들이 소스 안에서 들여쓰여 있다. dedent 를 strip 뒤에 하면 첫 줄만
        # 벗겨져 공통 앞머리가 빈 문자열이 되고, 붙여 넣은 코드가 통째로
        # IndentationError 로 터진다(실측 2026-09-15: 본보기 넷이 다 그랬다).
        r = C.그리기("""
            d += elm.Resistor().right().label('$R_1$')
            d += elm.Capacitor().down().label('$C_1$')
        """, str(판 / "들여쓴것.png"))
        ok(r["됐나"], f"들여쓴 코드가 돈다 -- {r['왜'][:110]}")

        print("\n== 틀린 코드는 까닭을 말한다 ==")
        # **모르는 소자 이름은 AttributeError 를 안 낸다.** schemdraw 는 그냥 아무것도
        # 안 그리고 끝나고, matplotlib 이 `Axis limits cannot be NaN or Inf` 를 낸다 --
        # 사람이 읽고 고칠 수 있는 말이 아니다(실측 2026-09-15). 옮겨 적는지 본다.
        r = C.그리기("d += elm.없는소자().right()", str(판 / "틀린것.png"))
        ok(not r["됐나"], "틀린 코드는 실패로 낸다")
        ok("아무것도 안 그려졌다" in r["왜"] and "example" in r["왜"],
           f"**빈 그림은 빈 그림이라고, 무엇을 할지까지 말한다** -- {r['왜'][:90]!r}")
        ok("Axis limits" not in r["왜"],
           "matplotlib 의 속사정을 사용자에게 넘기지 않는다")

        r = C.그리기("d += elm.Resistor().없는메서드()", str(판 / "틀린것2.png"))
        ok(not r["됐나"] and ("AttributeError" in r["왜"] or "없는메서드" in r["왜"]),
           f"진짜 파이썬 오류는 그대로 낸다 -- {r['왜'][:90]!r}")
        ok(not (판 / "틀린것.png").exists() or (판 / "틀린것.png").stat().st_size == 0,
           "터진 판의 그림을 성한 것처럼 남기지 않는다")

        r = C.그리기("")
        ok(not r["됐나"] and "빈" in r["왜"], f"빈 코드는 거절 -- {r['왜'][:60]}")

    print("\n== 모르는 본보기 이름 ==")
    r = C.본보기그리기("없는회로")
    ok(not r["됐나"] and "current_mirror" in r["왜"],
       f"**아는 이름을 알려준다** -- {r['왜'][:90]}")

    print("\n== 배선: 두 채널이 싣는다 ==")
    서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
    공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
    ok("draw_circuit" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에 있다")
    ok("draw_circuit" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0],
       "**PUBLIC_TOOLS 에 있다** -- 도구가 없으면 못 쓴다")
    ok("schemdraw" in (뿌리 / "requirements.txt").read_text(encoding="utf-8"),
       "**requirements.txt 에 있다** -- 없으면 VM 에서 임포트부터 터진다")

    print("\n== 배선: 그린 그림이 답에 붙어 나간다 ==")
    보내기 = 서버.split("async def _답보내기")[1].split("\nasync def ")[0]
    ok("마지막그림" in 보내기,
       "**봇이 그린 그림을 답에 붙인다** -- 경로만 돌려주면 사용자는 그것을 못 연다")
    ok("thread_id" in 보내기, "실행별로 갈라 붙인다 -- 남의 그림이 섞이면 안 된다")
    도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
    ok("마지막그림[thread_id]" in 도구,
       "한 실행이 끝날 때 옮겨진다 (`마지막셸` 과 같은 자리·같은 때)")
    _그림 = 도구.split("def draw_circuit")[1].split("\n@tool")[0]
    ok("absanchors" in _그림,
       "**도구 설명이 `absanchors` 를 짚는다** -- `anchors` 로 이으면 선이 엉뚱한 "
       "높이에 그어진다(실측으로 두 번 틀렸다)")
    ok("볼 수 없" in _그림 and "imageread" in _그림,
       "**그린 그림을 되읽어 확인시킨다** -- 에이전트는 제 그림을 못 본다")
    for 이름, 글 in (("public", 공개), ("admin", 서버)):
        ok("draw_circuit" in 글 and "본보기" in 글,
           f"{이름} 프롬프트가 그리라고 시킨다")

    print("\n== 본보기가 `absanchors` 를 쓴다 ==")
    # **도구 설명이 그렇게 말한다고 본보기가 그렇게 쓰는 것은 아니다.** 실측으로 두 번
    # 틀린 자리이고(게이트 버스가 소스 높이로 지나갔다), 베껴 쓰는 사람은 본보기를
    # 베낀다. 그러니 본보기 안을 본다.
    import re as _re
    맨앵커 = {n: _re.findall(r"\.anchors\[", 글) for n, 글 in C.본보기.items()}
    걸린것 = [n for n, v in 맨앵커.items() if v]
    ok(not 걸린것,
       f"**본보기가 `anchors[` 를 안 쓴다** (놓인 뒤의 자리는 `absanchors` 다): {걸린것}")
    쓰는것 = [n for n, 글 in C.본보기.items() if "absanchors" in 글]
    ok(len(쓰는것) >= 6,
       f"소자를 잇는 본보기들이 실제로 `absanchors` 를 쓴다: {len(쓰는것)}개")

    print("\n== 정식 이름은 **영어**다 -- 한글은 별칭으로만 ==")
    # 사용자(2026-09-15): "스키매틱은 대학 교재 혹은 현업에서 사용되는 형식을 따르도록
    # 모든 용어 명칭 개념들을 영어로 작성해주도록." 그래서 본보기의 **키가 영어**이고,
    # 한국어로 물어도 찾히게 한글을 별칭에 둔다.
    import re as _re
    한글이름 = [n for n in C.본보기 if _re.search(r"[가-힣]", n)]
    ok(not 한글이름,
       f"**본보기 이름에 한글이 없다** -- 교재·데이터시트 표기를 따른다: {한글이름}")
    ok(all(_re.fullmatch(r"[a-z][a-z0-9_]*", n) for n in C.본보기),
       f"이름이 소문자·밑줄 꼴이다: {[n for n in C.본보기 if not _re.fullmatch(r'[a-z][a-z0-9_]*', n)]}")
    # 한글·약칭 별칭이 **정식 영어 이름**을 가리킨다
    for 별, 정식 in (("전류미러", "current_mirror"), ("CMOS낸드", "cmos_nand2"),
                   ("카르노맵", "karnaugh_map"), ("차동쌍", "diff_pair"),
                   ("cs_amp", "common_source_amp"), ("kmap", "karnaugh_map"),
                   ("tg", "transmission_gate"), ("sf", "source_follower")):
        난것 = C.별칭.get(별, C.별칭.get(별.lower()))
        ok(난것 == 정식, f"`{별}` -> `{정식}` (난 것 {난것!r})")
        ok(정식 in C.본보기, f"  그리고 `{정식}` 이 실제로 있다")
    끊긴 = {a: t for a, t in C.별칭.items() if t not in C.본보기}
    ok(not 끊긴, f"**별칭이 다 실재하는 본보기를 가리킨다**: 끊긴 것 {끊긴}")
    if schemdraw is not None:
        r = C.본보기그리기("current_mirror", str(판 / "영어이름.png"))
        ok(r["됐나"], f"정식 영어 이름으로 그려진다 -- {r['왜'][:70]}")
        r2 = C.본보기그리기("전류미러", str(판 / "한글별칭.png"))
        ok(r2["됐나"], f"한글 별칭으로도 그려진다 -- {r2['왜'][:70]}")

    print("\n== 한글 라벨은 두부가 되기 전에 막는다 ==")
    # **실측 2026-09-15: 한글 라벨이 □□□ 로 그려졌는데 '그렸다' 로 끝났다.**
    # 조용한 실패다 -- 사용자만 깨진 그림을 본다.
    import latex_formatter as _LF                                 # noqa: E402
    if not _LF.한글글꼴():
        r = C.그리기("d += elm.Resistor().label('저항')")
        ok(not r["됐나"] and "두부" in r["왜"],
           f"글꼴이 없으면 그리기 전에 막고 까닭을 말한다 -- {r['왜'][:60]}")
        ok("영어로" in r["왜"], "무엇을 하라고까지 말한다")
    else:
        ok(True, f"이 기계에는 한글 글꼴이 있다({_LF.한글글꼴()}) -- 그대로 그린다")
    # **주석에 든 한글에는 안 걸려야 한다.** 주석은 그림에 안 나간다 -- 처음에 코드
    # 전체를 보다가 본보기 여덟이 통째로 거절됐다.
    if schemdraw is not None:
        r = C.그리기("# 저항 하나를 놓는다\nd += elm.Resistor().label('$R$')",
                   str(판 / "주석한글.png"))
        ok(r["됐나"], f"**한글 주석은 통과한다** -- {r['왜'][:70]}")
finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("회로 그리기: 본보기가 그려진다 · 틀린 코드는 까닭을 말한다 · 두 채널에 배선됐다 -- 통과")
