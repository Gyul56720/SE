"""옮겨 적기 -- **옮겨 적는 자도 지어낸다**가 이 검사의 본체다.

안 보이는 글자를 모델이 그럴듯하게 메우면, 법률문에서는 조문 번호가 바뀌고 '취소' 가
'무효' 가 된다. 그래서 프롬프트가 시키는 것은 하나뿐이고(보이는 대로만, 안 보이면
`[읽을 수 없음]`), 그것이 프롬프트에 실제로 실려 있는지를 닫힌 목록으로 고정한다.

**네트워크를 안 탄다.** 그림 만들기와 쪽 고르기만 여기서 돌린다.
"""
from __future__ import annotations

import contextlib
import io
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
print("[한 벌] **부르는 경로를 재는 것이지, 낱말이 있나 보는 것이 아니다**")
# 처음엔 `"for model in models" not in 소스` 처럼 낱말로 쟀다. 그건 **오늘 낸 그 사본이
# 그 이름 그대로 되살아날 때만** 걸린다 -- `for m in ms:` 로 쓰면 그냥 통과한다. 게다가
# 낱말로 재면 주석에 걸린다(바로 위 블록에서 `?key=` 로 실제로 겪었다).
#
# 그래서 **불러 보고 잰다.** 가짜 풀을 넣고 _ask 를 돌려서
#   (1) llm_pool.call 로 가는가          -- 제 반복문이면 안 간다
#   (2) 터졌을 때 **다시 안 부르는가**   -- 부르면 그게 두 번째 재시도 층이다
#   (3) 풀을 한 번만 세우는가            -- 매번 세우면 모델 조회로 쿼터를 태운다
# 이름을 바꿔도, 주석을 어떻게 달아도 이 셋은 그대로 잡힌다.
sys.path.insert(0, str(ROOT / "orchestrator"))
import llm_pool                                                       # noqa: E402

_png = Path(tempfile.mkdtemp()) / "쪽.png"
_png.write_bytes(b"\x89PNG\r\n\x1a\nfake-bytes")


class _엿봄:
    """부른 것을 적어 두는 가짜. **행동을 재려면 진짜 자리에 끼워야 한다.**"""

    def __init__(self, 터뜨릴=None):
        self.부름, self.세움, self.터뜨릴 = [], 0, 터뜨릴

    def build_pool(self, *a, **k):
        self.세움 += 1
        return [("키:gemini-flash", object()), ("키:gemma-3", object())]

    def call(self, pool, prompt, **k):
        self.부름.append((pool, prompt, k))
        if self.터뜨릴:
            raise self.터뜨릴
        return ("옮긴 글", "키:gemini-flash")


def _끼우고(엿, fn):
    """가짜를 진짜 자리에 끼우고 돌린 뒤 되돌린다."""
    _b, _c, _p = llm_pool.build_pool, llm_pool.call, OC._POOL
    llm_pool.build_pool, llm_pool.call, OC._POOL = 엿.build_pool, 엿.call, None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return fn()
    finally:
        llm_pool.build_pool, llm_pool.call, OC._POOL = _b, _c, _p


_엿 = _엿봄()
_답 = _끼우고(_엿, lambda: OC._ask([_png], prefer="flash"))
ok(_답 == "옮긴 글", f"풀이 돌려준 글이 그대로 나온다 (얻은 값 {_답!r})")
ok(len(_엿.부름) == 1, f"llm_pool.call 로 간다 -- 딱 한 번 (얻은 값 {len(_엿.부름)})")
_pool, _prompt, _k = _엿.부름[0]
ok(_k.get("images") == [("image/png", _png.read_bytes())],
   "그림이 실려 간다 -- 풀이 그림을 받는 그 길로 간다")
ok(_k.get("pool_id") == "ocr", f"제 이름표를 달고 간다 (얻은 값 {_k.get('pool_id')!r})")
ok("지어내지 마십시오" in _prompt, "옮겨 적기 프롬프트가 그대로 간다")
# **gemma 는 그림을 못 본다.** 후보에 남겨 두면 실패만 물고 온다.
ok([l for l, _ in _pool] == ["키:gemini-flash"],
   f"gemma 는 후보에서 빠진다 (얻은 값 {[l for l, _ in _pool]})")

# **터졌을 때 다시 부르면 그게 두 번째 재시도 층이다.** 재시도는 풀이 이미 한다 --
# 여기서 또 하면 같은 쿼터를 두 배로 태우고, 풀의 쿨다운 셈도 어긋난다.
_엿2 = _엿봄(터뜨릴=RuntimeError("429 RESOURCE_EXHAUSTED"))
try:
    _끼우고(_엿2, lambda: OC._ask([_png]))
    ok(False, "터지면 멈춘다")
except SystemExit as e:
    ok(len(_엿2.부름) == 1,
       f"터져도 **다시 안 부른다** -- 재시도 층은 풀에 한 벌만 (얻은 값 {len(_엿2.부름)})")
    ok("쿼터에 막혔다" in str(e) and "내일" in str(e),
       f"무엇에 막혔는지와 다음에 할 일을 말하고 멈춘다 ({str(e)[:30]}...)")

# **풀은 한 번만 세운다.** 매번 세우면 키마다 모델 목록을 조회해서 쿼터를 태운다.
_엿3 = _엿봄()


def _두번():
    OC._ask([_png])
    return OC._ask([_png])


_끼우고(_엿3, _두번)
ok(_엿3.세움 == 1 and len(_엿3.부름) == 2,
   f"두 번 물어도 풀은 한 번만 세운다 (세움 {_엿3.세움} · 부름 {len(_엿3.부름)})")

# 그림 없이 부르는 옛 길도 그대로여야 한다 -- 풀은 글에도 쓰인다.
class _가짜:
    def invoke(self, prompt):            # 그림을 모르는 옛 꼴
        class R:
            content = "됐다"
        return R()


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
# 실측: 사람이 옮긴 것과 Gemini 가 옮긴 것을 대 보니 **양쪽 다 틀린 데가 있었다.**
# 문 2 ④ `청구할 수 있다/없다` 는 사람이 틀렸고(한 글자가 답을 뒤집는다),
# 문 8 ㄱ `각/각각` 과 문 1 ㄹ `거치지 않고/않아` 는 OCR 이 틀렸다.
#
# 그리고 **자가 잘못돼 있었다.** 줄 단위로 대면 줄 접는 자리와 ○/O 표기까지 갈린 줄로
# 세어진다 -- 실측 717 줄. 그 안에서 진짜 갈린 자리는 보이지 않는다. 과잉 기각하는
# 심판은 맞는 답도 버린다. 그래서 아래 세 검사가 자를 붙든다.
_a = Path(tempfile.mkdtemp()) / "a.txt"
_b = Path(tempfile.mkdtemp()) / "b.txt"
import io                                                             # noqa: E402
import contextlib                                                     # noqa: E402


def _견줌(A, B):
    _a.write_text(A, encoding="utf-8")
    _b.write_text(B, encoding="utf-8")
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        OC.compare(_a, _b)
    return _buf.getvalue()


_찍힘 = _견줌("# 머리말은 안 본다\n문 2.\n혼동에 관한 설명 중 옳은 것은?\n④ 방해배제를 청구할 수 있다.\n",
             "문 2.\n혼동에 관한 설명 중 옳은 것은?\n④ 방해배제를 청구할 수 없다.\n")
ok("있다" in _찍힘 and "없다" in _찍힘, "갈린 칸을 양쪽 다 찍는다")
ok("혼동에 관한" not in _찍힘, "같은 칸은 안 찍는다 -- 볼 자리만 남긴다")
ok("머리말" not in _찍힘, "주석은 안 견준다")

# RED: 줄을 다르게 접었을 뿐인 것을 갈렸다고 부르면, 진짜 갈린 자리가 묻힌다.
_찍힘 = _견줌("문 5.\n등기에 관한 설명 중\n옳지 않은 것은?\n① ㄱ(○), ㄴ(×)\n",
             "문 5.\n등기에 관한 설명 중 옳지 않은 것은?\n① ㄱ(O), ㄴ(X)\n")
ok("갈림 0" in _찍힘,
   f"줄 접는 자리와 ○/O·×/X 는 갈린 게 아니다 (얻은 값: {_찍힘.strip().splitlines()[-2:]})")

# 한쪽에만 있는 문항은 '갈림' 이 아니라 '한쪽이 안 읽음' 이다 -- 섞으면 수가 거짓이 된다.
_찍힘 = _견줌("문 5.\n등기에 관한 설명\n", "문 5.\n등기에 관한 설명\n문 6.\n소멸시효에 관한 설명\n")
ok("갈림 0" in _찍힘 and "[6]" in _찍힘,
   f"한쪽에만 있는 문항은 따로 센다 (얻은 값: {_찍힘.strip().splitlines()[-2:]})")

print()
if fails:
    print(f"옮겨 적기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("옮겨 적기: 지어내지 마라 · 쪽 고르기 · 그림 · 한 벌 -- 통과")
