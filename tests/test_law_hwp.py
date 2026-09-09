"""HWP 뽑기가 **못 뽑았을 때 못 뽑았다고 하는가.**

이 파일에서 가장 위험한 것은 오류가 아니라 **껍데기다.** LEET 기출 HWP 는 배포용
문서라 본문이 `ViewText` 에 잠겨 있고 `BodyText` 에는 안내문만 남아 있다. 그런데
그것도 글이라서, 아무 생각 없이 읽으면 131자가 나오고 오류는 안 난다(실측):

    "상위 버전의 배포용 문서입니다. ... " / "추리논증" / "20" / "짝수형"

**뽑았다고 여기면 그 131자 위에서 세는 모든 수가 거짓이 된다.** 그래서 검사가
보는 것은 "뽑히는가" 만이 아니라 "안 뽑혔을 때 그렇다고 말하는가" 다.

    python3 tests/test_law_hwp.py
"""
from __future__ import annotations

import io
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import hwp as H                                              # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def 레코드(tag: int, level: int, 몸: bytes) -> bytes:
    """검사용 HWP 레코드 한 덩이. 크기가 4095 를 넘으면 꼬리에 진짜 크기를 단다."""
    n = len(몸)
    if n >= 0xFFF:
        return struct.pack("<I", (tag & 0x3FF) | (level << 10) | (0xFFF << 20)) \
            + struct.pack("<I", n) + 몸
    return struct.pack("<I", (tag & 0x3FF) | (level << 10) | (n << 20)) + 몸


def 글덩이(글: str) -> bytes:
    return 레코드(H.TAG_PARA_TEXT, 0, 글.encode("utf-16le"))


print("[레코드] 머리 4바이트에 셋이 눌려 있다")
_버퍼 = 글덩이("첫 줄") + 글덩이("둘째 줄")
_본 = [(t, bytes(b)) for t, _l, b in H.레코드들(_버퍼)]
ok(len(_본) == 2 and all(t == H.TAG_PARA_TEXT for t, _ in _본),
   f"레코드 둘을 갈라 읽는다 (얻은 값 {[(t, len(b)) for t, b in _본]})")
ok("".join(H.글자(b) for _, b in _본) == "첫 줄둘째 줄",
   f"UTF-16LE 로 읽는다 (얻은 값 {''.join(H.글자(b) for _, b in _본)!r})")

# **4095자를 넘으면 크기가 꼬리로 간다.** 이걸 안 보면 긴 지문이 통째로 잘린다.
_긴 = "가" * 3000
ok(H.글자(next(iter(H.레코드들(글덩이(_긴))))[2]) == _긴,
   "4095바이트를 넘는 덩이도 끝까지 읽는다")

print()
print("[제어문자] **안 건너뛰면 표·그림 속성이 글자로 샌다**")
# 확장 제어문자는 뒤에 12바이트가 더 붙는다. 그 12바이트는 글자가 아니다.
_몸 = "앞".encode("utf-16le") + struct.pack("<H", 2) + b"\xff" * 12 + "뒤".encode("utf-16le")
ok(H.글자(_몸) == "앞뒤", f"확장 제어 뒤 12바이트를 건너뛴다 (얻은 값 {H.글자(_몸)!r})")
_줄 = "앞".encode("utf-16le") + struct.pack("<H", 13) + "뒤".encode("utf-16le")
ok(H.글자(_줄) == "앞\n뒤", f"줄바꿈 제어는 줄바꿈으로 (얻은 값 {H.글자(_줄)!r})")

print()
print("[잘림] **지어내서 잇지 않는다**")
_잘린 = 글덩이("멀쩡") + struct.pack("<I", (H.TAG_PARA_TEXT) | (0x100 << 20)) + b"\x00\x00"
_읽 = list(H.레코드들(_잘린))
ok(len(_읽) == 1, f"크기가 안 맞으면 거기서 멈춘다 (얻은 값 {len(_읽)}덩이)")

print()
print("[배포용] **131자짜리 껍데기를 시험지라 하지 않는다**")
# **`is_dir()` 는 "못 읽음" 을 안 삼킨다.** pathlib 이 삼키는 errno 는 (2, 20, 9, 40)
# 뿐이고 EACCES(13)는 그대로 터진다. 여기(에이전트 컨테이너)에서는 경로가 아예 없어서
# False 가 나와 초록이었는데, CI 러너에서는 `/root` 가 **있는데 못 읽어서** 터졌다.
# 실측 2026-09-09: 게이트 워크플로가 이것 하나로 계속 빨간불이었다(82개 중 1개 실패).
# G019: 기계 경로 -- 일부러 만진다. 여기 올린 진짜 시험지가 있으면 그것으로 재고,
# 없거나 못 읽으면 건너뛴다고 **말한다**. 아래 try 가 그 자리다.
_올린곳 = Path("/root/.claude/uploads")
try:
    _기출 = sorted(_올린곳.rglob("*.hwp")) if _올린곳.is_dir() else []
except OSError as e:
    _기출 = []
    print(f"  건너뜀 {_올린곳} 를 못 본다 ({type(e).__name__}) -- 여기는 그 기계가 아니다")
if _기출:
    _한 = _기출[0]
    try:
        H.뽑기(_한)
        ok(False, "배포용인데 조용히 뽑았다")
    except H.못뽑음 as e:
        ok("배포용" in str(e) and "ViewText" in str(e),
           f"잠겼다고 말하고 멈춘다 (얻은 값 {str(e)[:44]}…)")
    _머 = H.머리글(_한)
    ok(len(_머) > 500 and "학년도" in _머,
       f"그래도 PrvText 는 읽힌다 -- OCR 을 잴 기준자다 ({len(_머):,}자)")
else:
    print("  건너뜀 올린 HWP 가 없다")

# 저장소에 담아 둔 머리글이 **글자 그대로**인가. 손대면 기준자가 못 된다.
_담김 = sorted((Path(__file__).resolve().parent.parent / "law" / "leet").rglob("*_머리.txt"))
ok(len(_담김) >= 3, f"머리글을 담아 뒀다 ({len(_담김)}개)")
for p in _담김:
    글 = p.read_text(encoding="utf-8")
    ok("학년도 법학적성시험" in 글 and ("추리논증" in 글 or "언어이해" in 글),
       f"{p.name} 이 제 과목·해를 스스로 말한다")
    ok(("40문항" in 글) == ("추리논증" in p.name),
       f"{p.name}: 추리논증 40문항 · 언어이해 30문항 (실측)")

print()
print("[못 읽는 것] 오류를 삼키지 않는다")
_빈 = Path("/tmp/claude-0/안HWP.bin")
_빈.parent.mkdir(parents=True, exist_ok=True)
_빈.write_bytes(b"not an ole file at all")
# **건너뛰지 않고 세운다.** `olefile` 은 requirements.txt 에도 CI 에도 없는 선택
# 의존이라, 없는 기계에서는 "OLE 가 아니다" 대신 "olefile 이 없다" 가 왔다 -- 즉 이
# 줄은 **설정을 제대로 한 사람만 보는 실패**였다(실측 2026-09-08, 이 컨테이너).
#
# 건너뛰는 것으로 때우지 않는다. 조용한 건너뜀은 가짜 green 이고, 소리 내어 건너뛰어도
# 그 기계에서는 아무것도 안 재는 것은 같다. 대신 `isOleFile` 만 있는 대역을 끼워
# **판별 갈래를 어느 기계에서나 실제로 태운다.** 대역이 하는 일은 "OLE 가 아니다" 라고
# 답하는 것 하나뿐이고, 판정은 여전히 law/hwp.py 가 한다.
import importlib.util as _iu
_없다 = "olefile" not in sys.modules and _iu.find_spec("olefile") is None
if _없다:
    import types
    _대역 = types.ModuleType("olefile")
    _대역.isOleFile = lambda _p: False          # 이 파일은 OLE 가 아니다 -- 사실이다
    sys.modules["olefile"] = _대역
try:
    H.뽑기(_빈)
    ok(False, "OLE 도 아닌 것을 읽었다")
except H.못뽑음 as e:
    ok("OLE" in str(e), f"OLE 가 아니면 그렇다고 한다 (얻은 값 {str(e)[:40]}…)"
       + ("  ← olefile 대역으로 태웠다" if _없다 else ""))
finally:
    if _없다:
        sys.modules.pop("olefile", None)

print()
print("[다듬기] **글자는 안 고친다**")
ok(H.다듬기("가\r\n\r\n\r\n나  \n") == "가\n\n나\n",
   f"빈 줄을 줄이고 줄 끝 공백만 없앤다 (얻은 값 {H.다듬기('가' + chr(13) + chr(10) * 3 + '나  ' + chr(10))!r})")
ok("착오" in H.다듬기("  착오로 말미암은  "), "가운데 글자는 그대로 둔다")

print()
if fails:
    print(f"HWP: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("HWP: 레코드 · 제어문자 · 잘림 · 배포용 거절 · 머리글 · 다듬기 -- 통과")
