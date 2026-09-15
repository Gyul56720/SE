"""`read_image` -- 사진을 **실제로 보는** 길이 이어져 있나.

## 왜 있나 (실측 2026-09-15)

사용자가 문제 사진을 올렸더니 봇이 이렇게 답했다.

    아니요, 아직 문제 이미지나 텍스트가 보이지 않습니다!

재 보니 두 군데가 끊겨 있었다.

  공개 채널  `_handle_public_message` 가 `if not content: return` 으로 시작해서
             **첨부만 있는 메시지를 저장조차 안 하고 버렸다.**
  관리 채널  첨부는 저장하는데 프롬프트에 "run_shell로 cat/열어볼 것" 이라 적어 줬다.
             **PNG 를 cat 하면 깨진 바이트다.**

그런데 그림을 보내는 길은 이미 있었다 -- `orchestrator/gemini_http.py::invoke(images=)`
와 `llm_pool.call(..., images=)`. `law/ocr.py` 가 그 길로 시험지를 읽고 있었다.
**봇만 그 길을 안 쓰고 있었다.**

## 무엇을 붙드나

여기서 진짜 LLM 을 부르지 않는다(쿼터를 쓰고, 답이 매번 다르다). 대신 **가짜 풀**을
꽂아 두고 **무엇이 실제로 그 풀에 건네지는지**를 본다 -- mime 이 맞나, 바이트가 그대로
가나, gemma 가 빠지나, 물음이 프롬프트에 실리나. 배선이 이 검사의 대상이다.
"""
from __future__ import annotations

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


# ---- 가짜 풀. 건네진 것을 그대로 붙들어 둔다 ------------------------------------
class _가짜풀:
    def __init__(self):
        self.받은것 = None
        self.터뜨릴것 = None

    def build_pool(self):
        return [("gemini-3.5-flash", object()), ("gemma-3-27b", object()),
                ("gemini-3.1-pro", object())]

    def call(self, pool, prompt, pool_id="", images=None, **kw):
        self.받은것 = {"pool": pool, "prompt": prompt, "pool_id": pool_id, "images": images}
        if self.터뜨릴것:
            raise self.터뜨릴것
        return "1번 문제: 2x + 3 = 7 일 때 x 는?", "gemini-3.5-flash"


가짜 = _가짜풀()
sys.modules["llm_pool"] = 가짜                      # imageread.읽기 가 import 할 때 이것을 집는다

import imageread                                    # noqa: E402

판 = Path(tempfile.mkdtemp(prefix="readimg-"))
try:
    print("== 못 읽는 것은 못 읽는다고 한다 ==")
    글 = imageread.읽기(str(판 / "없는파일.png"))
    ok("[그림 없음]" in 글, f"없는 경로 -- {글[:50]}")
    ok(가짜.받은것 is None, "**없는 파일로 LLM 을 부르지 않는다** -- 쿼터를 안 버린다")

    글파일 = 판 / "메모.txt"
    글파일.write_text("이건 글이다\n", encoding="utf-8")
    글 = imageread.읽기(str(글파일))
    ok("[그림 아님]" in 글 and "read_file" in 글, f"글 파일은 돌려보낸다 -- {글[:60]}")

    print("\n== 그림이면 풀에 제대로 건넨다 ==")
    그림 = 판 / "문제.png"
    바이트 = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    그림.write_bytes(바이트)
    글 = imageread.읽기(str(그림))
    받 = 가짜.받은것
    ok(받 is not None, "풀을 실제로 불렀다")
    ok(받["images"] == [("image/png", 바이트)],
       "**mime 과 바이트가 그대로 간다** -- 여기가 틀리면 그림이 안 보인다")
    ok(all("gemma" not in l for l, _ in 받["pool"]),
       f"**gemma 를 뺐다** -- 그림을 못 본다 ({[l for l, _ in 받['pool']]})")
    ok("그대로" in 받["prompt"] and "지어내지 마라" in 받["prompt"],
       "옮겨 적으라고 시킨다 -- 지어내지 말라고 못박는다")
    ok("[안 보임]" in 받["prompt"],
       "**안 보이는 곳은 비우라고 시킨다** -- 메우면 없는 문제를 푼다")
    ok("2x + 3 = 7" in 글 and "문제.png" in 글, f"읽은 글과 파일 이름이 돌아온다 -- {글[:60]}")

    print("\n== 물음을 주면 프롬프트에 실린다 ==")
    imageread.읽기(str(그림), question="답이 몇이야?")
    ok("답이 몇이야?" in 가짜.받은것["prompt"], "물음이 실린다")

    print("\n== jpg·pdf 도 받는다 ==")
    for 이름, mime in (("사진.jpg", "image/jpeg"), ("시험지.pdf", "application/pdf"),
                     ("캡처.WEBP", "image/webp")):
        (판 / 이름).write_bytes(b"x")
        imageread.읽기(str(판 / 이름))
        ok(가짜.받은것["images"][0][0] == mime, f"{이름} -> {mime}")

    print("\n== 실패는 감추지 않는다 ==")
    가짜.터뜨릴것 = RuntimeError("RESOURCE_EXHAUSTED: 쿼터")
    글 = imageread.읽기(str(그림))
    가짜.터뜨릴것 = None
    ok("[그림 못 읽음]" in 글 and "RESOURCE_EXHAUSTED" in 글,
       f"**왜 못 읽었는지 그대로 낸다** -- {글[:60]}")

    print("\n== 배선: 두 채널이 이 도구를 싣는다 ==")
    서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
    공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
    ok("read_image" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0],
       "ADMIN_TOOLS 에 있다")
    ok("read_image" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0],
       "**PUBLIC_TOOLS 에 있다** -- 도구가 없으면 못 쓴다. 여기가 비어 있었다")

    print("\n== 배선: 공개 채널이 첨부를 버리지 않는다 ==")
    # 예전에는 `content = ...strip()` 바로 다음이 `if not content: return` 이었다.
    뒤 = 서버.split("async def _handle_public_message")[1][:900]
    ok("_save_attachments" in 뒤,
       "**첨부를 저장한다** -- 예전에는 사진만 있는 메시지가 통째로 버려졌다")
    ok("if not content and not attachment_paths:" in 뒤,
       "사진만 있어도 안 버린다")

    print("\n== 배선: 그림에 cat 을 시키지 않는다 ==")
    안내 = 서버.split("def _첨부안내")[1].split("\n\n\n")[0]
    ok("read_image" in 안내 and "cat 하지 마라" in 안내,
       "그림이면 read_image 를 시킨다")
    ok("run_shell로 cat" not in 서버,
       "**옛 안내문이 남아 있지 않다** -- 남아 있으면 그 말이 다시 그림을 cat 하게 한다")
    ok("보이지 않는다고 답하지 마라" in 서버 and "보이지 않는다고 답하지 마라" not in 공개
       or "안 보인다고 답하지 마라" in 공개,
       "두 채널 다 '안 보인다'로 끝내지 말라고 적혀 있다")

    print("\n== 배선: 네 덩이를 시킨다 (풀이·약한 개념·오답노트·예상 질문) ==")
    for 이름, 글뭉치 in (("public", 공개), ("admin", 서버)):
        빠진 = [x for x in ("풀이", "약한 개념", "오답노트", "예상 질문")
              if x not in 글뭉치]
        ok(not 빠진, f"{이름} 프롬프트가 넷을 다 시킨다 (빠진 것 {빠진})")
        ok("LaTeX" in 글뭉치 and "$$" in 글뭉치,
           f"{이름} 프롬프트가 **수식을 LaTeX 로** 쓰라고 시킨다")
    ok("처음 보는 사람" in 공개 and "처음 보는 "

       in 서버,
       "**예상 질문은 '처음 보는 사람' 기준이라고 못박는다** -- 아는 사람 기준이면 "
       "막히는 자리를 못 짚는다")
    ok("파일로 쓰거나 커밋하지 마라" in 공개,
       "**오답노트를 파일로 쓰지 말라고 남겨 뒀다** -- 2026-09-13 에 그것이 사고였다")

    print("\n== 말: 문제 풀이는 한국어, 회로 설계는 영어 ==")
    # 사용자(2026-09-15): "문제 푸는 챗봇은 한국어로 나와야해."
    # 앞서 회로 쪽에 "영어로" 를 넣었는데 그것이 문제 풀이까지 덮으면 안 된다.
    ok("문제 풀이" in 공개 and "한국어" in 공개,
       "**문제 풀이는 한국어라고 적혀 있다**")
    _말규칙 = 공개.split("무슨 말로 답하나")[1].split("## 문제가 오면")[0]
    ok("한국어" in _말규칙 and "영어" in _말규칙,
       "둘을 갈라 적는다 -- 한쪽만 적으면 다른 쪽이 새어 나간다")
    ok(공개.index("무슨 말로 답하나") < 공개.index("네 덩이"),
       "**말 규칙이 문제 절보다 먼저 온다** -- 뒤에 두면 이미 답을 쓰고 난 뒤다")
    _회로절 = 공개.split("Circuit / IC design")[1][:400]
    ok("this section only" in _회로절.lower(),
       f"회로 절의 영어 규칙이 **그 절에만** 걸린다 -- {_회로절[:90]!r}")
finally:
    import shutil
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("read_image: 그림만 보낸다 · gemma 를 뺀다 · 실패를 감추지 않는다 · 두 채널에 배선됐다 -- 통과")
