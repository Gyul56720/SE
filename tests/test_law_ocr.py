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
if fails:
    print(f"옮겨 적기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("옮겨 적기: 지어내지 마라 · 쪽 고르기 · 그림 · 한 벌 -- 통과")
