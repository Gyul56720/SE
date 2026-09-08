"""옮겨 적기 -- **옮겨 적는 자도 지어낸다**가 이 검사의 본체다.

안 보이는 글자를 모델이 그럴듯하게 메우면, 법률문에서는 조문 번호가 바뀌고 '취소' 가
'무효' 가 된다. 그래서 프롬프트가 시키는 것은 하나뿐이고(보이는 대로만, 안 보이면
`[읽을 수 없음]`), 그것이 프롬프트에 실제로 실려 있는지를 닫힌 목록으로 고정한다.

**네트워크를 안 탄다.** 그림 만들기와 쪽 고르기만 여기서 돌린다.
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from law import ocr as OC                                             # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("[지어내지 마라] **옮겨 적는 자가 메우면 조문 번호가 바뀐다**")
for 말 in ("지어내지 마십시오", "[읽을 수 없음]", "짐작해서 메우지",
          "조문 번호와 법령명", "그대로 옮겨 적으십시오"):
    ok(말 in OC.PROMPT, f"프롬프트가 {말!r} 를 시킨다")
ok("끊긴 채로 두십시오" in OC.PROMPT,
   "끊긴 문장을 이어 붙이지 말라고 시킨다 -- 이어 붙이는 순간 그건 지어낸 것이다")

print()
print("[쪽 고르기] 시험 삼아 몇 쪽만 돌릴 수 있어야 한다")
ok(OC.pages_of("", 5) == [1, 2, 3, 4, 5], "안 주면 전부")
ok(OC.pages_of("1-3", 36) == [1, 2, 3], "`1-3`")
ok(OC.pages_of("2,5-6", 36) == [2, 5, 6], "`2,5-6`")
ok(OC.pages_of("40", 36) == [], "쪽수를 넘으면 버린다 -- 없는 쪽을 부르지 않는다")

print()
print("[그림] poppler 없이 순수 파이썬으로 PNG 를 만든다")


class _Im(dict):
    def __init__(self, w, h, ch):
        super().__init__({"/Width": w, "/Height": h})
        self._data = zlib.compress(bytes(range(256)) * ((w * h * ch) // 256 + 1))
        self._data = zlib.compress(b"\x80" * (w * h * ch))


class _Page(dict):
    def __init__(self, im):
        super().__init__({"/Resources": {"/XObject": {"/Im0": im}}})


import tempfile                                                       # noqa: E402
_out = Path(tempfile.mkdtemp()) / "p.png"
OC.page_png(_Page(_Im(40, 100, 3)), _out, scale=2)
raw = _out.read_bytes()
ok(raw[:8] == b"\x89PNG\r\n\x1a\n", "PNG 머리표를 쓴다")
W, H = struct.unpack(">II", raw[16:24])
# 세로는 TOP~BOT 만 남기고 scale 로 줄인다 -- 껍데기를 그림에서부터 잘라 낸다.
ok(W == 20 and H == len(range(int(100 * OC.TOP), int(100 * OC.BOT), 2)),
   f"껍데기를 잘라 내고 절반으로 줄인다 (얻은 값 {W}x{H})")

print()
print("[한 벌] 그림을 보내려고 클라이언트를 따로 만들지 않았다")
_src = (ROOT / "orchestrator" / "gemini_http.py").read_text(encoding="utf-8")
ok("def invoke(self, prompt, images=None)" in _src,
   "gemini_http.Client 가 그림을 받는다 -- 두 벌이면 키 규율도 두 벌이 된다")
# **주석에 적힌 `?key=` 는 그 규율을 설명하는 글이지 코드가 아니다.** 낱말이 있나
# 없나로 재면 자기 자신을 설명한 주석에 걸린다 -- 코드 줄만 본다.
_코드 = "\n".join(l for l in _src.splitlines() if not l.lstrip().startswith("#"))
ok('headers={"x-goog-api-key": self.key}' in _코드,
   "키는 여전히 헤더로 간다")
ok("key=" not in _코드.split("url = API.format")[1].split("r = requests.post")[0],
   "URL 을 만드는 자리에 키가 없다 -- 실으면 예외 문자열로 새어 나간다")
ok("import requests" not in (ROOT / "law" / "ocr.py").read_text(encoding="utf-8"),
   "law/ocr.py 는 직접 HTTP 를 치지 않는다")

print()
print("[한 벌] **novel 이 쓰는 후보 풀을 그대로 쓴다**")
# 처음엔 여기에 키·모델을 도는 반복문을 따로 짰다. **그게 두 벌이었다.** llm_pool 은
# (키·모델)별 잔량 추적, RPM 쿨다운, 500/503 을 거듭 내는 후보 격리, 실측 지연 기반
# 순위, 바퀴 사이 대기를 이미 갖고 있다 -- 소설 파이프라인이 회차마다 100번씩 두드리며
# 다듬은 층이다. 내 반복문은 그것을 전부 버리고 `for 모델: for 키:` 로 되돌린 것이었다.
_src = (ROOT / "law" / "ocr.py").read_text(encoding="utf-8")
ok("llm_pool.call(" in _src, "부르는 것은 llm_pool.call 이다")
for 흔적 in ("for model in models", "GEMINI_API_KEY_FALLBACK", "time.sleep"):
    ok(흔적 not in _src,
       f"제 반복문의 흔적 {흔적!r} 이 없다 -- 있으면 두 벌로 갈라진다")
ok("gemma" in _src, "gemma 는 뺀다 -- 그림을 못 본다")

# **그림은 줄 때만 넘긴다.** 안 그러면 `invoke(prompt)` 만 아는 가짜 LLM 이 터진다.
_pool = (ROOT / "orchestrator" / "llm_pool.py").read_text(encoding="utf-8")
ok("l.invoke(prompt, images=images) if images" in _pool,
   "풀이 그림을 줄 때만 넘긴다 -- 기존 부르는 쪽과 가짜 LLM 이 그대로 돈다")


class _가짜:
    def invoke(self, prompt):            # 그림을 모르는 옛 꼴
        class R:
            content = "됐다"
        return R()


sys.path.insert(0, str(ROOT / "orchestrator"))
import llm_pool                                                       # noqa: E402
ok(llm_pool.call([("가짜:모델", _가짜())], "물음", verbose=False)[0] == "됐다",
   "그림 없이 부르면 옛 꼴 LLM 도 그대로 돈다")

print()
print("[무엇에 막혔나] **가려서 보고해야 다음에 무엇을 할지 안다**")
for _글, _뜻 in [("503 UNAVAILABLE. The model is overloaded", "과부하"),
               ("504 DEADLINE_EXCEEDED", "과부하"),
               ("429 RESOURCE_EXHAUSTED", "쿼터에 막혔다"),
               ("404 NOT_FOUND models/없는모델", "그런 모델이 없다")]:
    ok(OC._why(Exception(_글)) == _뜻, f"{_글[:26]!r} -> {_뜻}")

print()
print("[무엇에 막혔나] **가려서 보고해야 다음에 무엇을 할지 안다**")
# 실측: 쿼터(429)만 넘기고 과부하(503)는 그 자리에서 터뜨렸다. 서른여섯 쪽짜리 일이
# 한 번의 과부하로 통째로 죽었다. 둘은 다음에 할 일이 다르다 --
# 쿼터는 **내일**, 과부하는 **조금 뒤**.
for _글, _뜻 in [("503 UNAVAILABLE. The model is overloaded", "과부하"),
               ("504 DEADLINE_EXCEEDED", "과부하"),
               ("500 INTERNAL", "과부하"),
               ("429 RESOURCE_EXHAUSTED", "쿼터에 막혔다"),
               ("404 NOT_FOUND models/없는모델", "그런 모델이 없다")]:
    ok(OC._why(Exception(_글)) == _뜻, f"{_글[:26]!r} -> {_뜻}")

print()
print("[이어하기] **쿼터에 막혀 멈춰도 다음 날 이어서 한다**")
_o = Path(tempfile.mkdtemp()) / "본.txt"
_o.write_text(OC.PAGE_MARK.format(n=1) + "\n문 1.\n"
              + OC.PAGE_MARK.format(n=2) + "\n문 2.\n", encoding="utf-8")
ok(OC.done_pages(_o) == {1, 2}, f"이미 옮긴 쪽을 되짚는다 (얻은 값 {OC.done_pages(_o)})")
ok(OC.done_pages(Path("/없는/파일")) == set(), "없으면 빈 것으로 본다")

print()
print("[견줌] **어느 쪽도 기준이 아니다 -- 갈리는 자리를 찾는 것이 쓸모다**")
# 실측: 사람이 옮긴 것과 Gemini 가 옮긴 것을 대 보니 확인한 두 자리에서 전부 사람이
# 틀렸고, 그중 하나는 `청구할 수 있다/없다` -- 한 글자가 답을 뒤집는 자리였다.
_a = Path(tempfile.mkdtemp()) / "a.txt"
_b = Path(tempfile.mkdtemp()) / "b.txt"
_a.write_text("# 머리말은 안 본다\n문 2.\n④ 방해배제를 청구할 수 있다.\n", encoding="utf-8")
_b.write_text("문 2.\n④ 방해배제를 청구할 수 없다.\n", encoding="utf-8")
import io                                                             # noqa: E402
import contextlib                                                     # noqa: E402
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    OC.compare(_a, _b)
_찍힘 = _buf.getvalue()
ok("있다" in _찍힘 and "없다" in _찍힘, "갈린 줄을 양쪽 다 찍는다")
ok("문 2." not in _찍힘, "같은 줄은 안 찍는다 -- 볼 자리만 남긴다")
ok("머리말" not in _찍힘, "주석은 안 견준다")

print()
if fails:
    print(f"옮겨 적기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("옮겨 적기: 지어내지 마라 · 쪽 고르기 · 그림 · 한 벌 -- 통과")
