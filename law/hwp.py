"""HWP 에서 글을 뽑는다 -- **OCR 이 아니다. 지어낼 자리가 없다.**

LEET 기출이 두 꼴로 온다: 스캔 PDF(글자층 0자)와 HWP. 앞엣것은 OCR 이 필요하고
OCR 은 **지어낸다** -- 이 저장소가 변호사시험지에서 그것을 겪었다(사람이 읽은 것도
두 자리에서 틀렸다: `기망하며` -> `기망해`, `청구할 수 있다` -> **`없다`**).
뒤엣것은 문서 안에 글자가 그대로 들어 있다. **뽑는 것과 읽는 것은 다르다.**

그래서 HWP 가 있으면 HWP 를 쓴다. 같은 해 시험지가 둘 다 있으면 HWP 를 정본으로
삼고 PDF 는 견줌용으로 둔다.

## 꼴

HWP 5.x 는 OLE 복합 파일이다.

    FileHeader          32바이트 signature + 속성. **압축 여부가 여기 있다**
    BodyText/Section0   본문. 압축이면 raw deflate (zlib 머리 없음, wbits=-15)
    DocInfo             글꼴·스타일. 본문 글자는 없다

Section 안은 레코드가 줄줄이 이어진다. 머리 4바이트에 셋이 눌려 있다:

    tag  = h & 0x3FF          (10비트)
    level= (h >> 10) & 0x3FF  (10비트)
    size = (h >> 20) & 0xFFF  (12비트) -- 0xFFF 면 **다음 4바이트가 진짜 크기**

글자는 tag 67(HWPTAG_PARA_TEXT)에 UTF-16LE 로 들어 있다. 32 미만은 제어문자인데,
그중 몇은 **뒤에 12바이트가 더 붙는다**(확장 제어). 그걸 안 건너뛰면 표·그림의
속성 바이트가 글자로 새어 나온다.

## 배포용 문서는 **잠겨 있다고 말한다**

LEET 기출 HWP 는 '배포용 문서' 다. 본문이 `ViewText/Section0` 에 잠겨 있고
`BodyText/Section0` 에는 **껍데기만** 남아 있다. 그런데 껍데기도 글이라서, 아무
생각 없이 BodyText 를 읽으면 이런 것이 나온다(실측):

    "상위 버전의 배포용 문서입니다. 문서를 읽으려면 최신 버전의 한글 또는 ..."
    "추리논증 / 20 / 짝수형"

**131자가 나왔고 오류는 없었다.** 이것이 가장 나쁜 꼴이다 -- 못 뽑았는데 뽑은
것처럼 보이고, 그 131자를 시험지라 여기면 그 위에서 세는 모든 수가 거짓이 된다.
그래서 `ViewText` 가 있으면 **잠겼다고 말하고 멈춘다.**

잠금을 푸는 코드는 여기 두지 않는다. 같은 시험지가 PDF 로도 있고, 그쪽은 OCR 로
읽으면 된다.

## 그래도 공짜로 주는 것 하나 -- `PrvText`

미리보기 글이 잠기지 않은 채 들어 있다. 1,000자 남짓이고 **출제기관이 쓴 글자
그대로**다. 짧지만 값이 크다: OCR 이 지어내는지 재는 **기준자**가 된다. 이 저장소는
사람이 옮긴 것도 두 자리에서 틀리는 것을 겪었다 -- 기준 없이 대조하면 어느 쪽이
틀렸는지 영영 모른다.

## 못 뽑으면 못 뽑았다고 한다

빈 문자열을 돌려주고 조용히 넘어가지 않는다. 서명이 다르거나 Section 이 없으면
그렇게 말한다 -- **미검증은 통과가 아니다.**
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

TAG_PARA_TEXT = 67

# 뒤에 12바이트가 더 붙는 제어문자. 안 건너뛰면 표·그림 속성이 글자로 샌다.
_확장제어 = frozenset({1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23})
# 홀로 서는 제어문자 중 **줄바꿈으로 볼 것**.
_줄바꿈 = frozenset({10, 13, 24, 25, 26, 27, 28, 29, 30, 31})


class 못뽑음(RuntimeError):
    """뽑기에 실패했다. **빈 글을 돌려주지 않는다.**"""


def _열기(path):
    try:
        import olefile
    except ImportError:                                   # pragma: no cover
        raise 못뽑음("olefile 이 없다. `pip install olefile`") from None
    if not olefile.isOleFile(str(path)):
        raise 못뽑음(f"OLE 복합 파일이 아니다: {path}")
    return olefile.OleFileIO(str(path))


def 압축인가(ole) -> bool:
    """FileHeader 의 속성 첫 비트. **여기를 안 보고 풀면 아무것도 안 나온다.**"""
    head = ole.openstream("FileHeader").read()
    if not head.startswith(b"HWP Document File"):
        raise 못뽑음("HWP 서명이 없다 -- HWP 5.x 가 아니다")
    prop = int.from_bytes(head[36:40], "little")
    return bool(prop & 1)


def 레코드들(buf: bytes):
    """(tag, level, 몸통) 을 차례로. 크기가 어긋나면 거기서 멈춘다."""
    i, n = 0, len(buf)
    while i + 4 <= n:
        h = int.from_bytes(buf[i:i + 4], "little")
        i += 4
        tag, level, size = h & 0x3FF, (h >> 10) & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF:
            if i + 4 > n:
                return
            size = int.from_bytes(buf[i:i + 4], "little")
            i += 4
        if i + size > n:
            return                      # 잘렸다. **지어내서 잇지 않는다**
        yield tag, level, buf[i:i + size]
        i += size


def 글자(몸통: bytes) -> str:
    """PARA_TEXT 한 덩이 -> 글. UTF-16LE 이고 32 미만은 제어문자다."""
    out, i, n = [], 0, len(몸통) - 1
    while i < n:
        c = int.from_bytes(몸통[i:i + 2], "little")
        i += 2
        if c >= 32:
            out.append(chr(c))
        elif c in _확장제어:
            i += 12                     # 확장 제어는 뒤에 12바이트가 더 있다
        elif c in _줄바꿈:
            out.append("\n")
    return "".join(out)


def 배포용인가(ole) -> bool:
    """본문이 `ViewText` 에 잠긴 배포용 문서인가."""
    return any("/".join(x).startswith("ViewText/Section") for x in ole.listdir())


def 머리글(path) -> str:
    """`PrvText` -- 미리보기 글. **출제기관이 쓴 글자 그대로**이고 1,000자 남짓이다.

    배포용이라 본문을 못 읽어도 이것은 읽힌다. OCR 이 지어내는지 재는 기준자다.
    """
    ole = _열기(path)
    try:
        이름들 = {"/".join(x) for x in ole.listdir()}
        if "PrvText" not in 이름들:
            raise 못뽑음("PrvText 가 없다")
        return ole.openstream("PrvText").read().decode("utf-16le", "replace")
    finally:
        ole.close()


def 뽑기(path) -> str:
    """HWP 파일 -> 본문. 못 뽑으면 `못뽑음` 을 던진다."""
    ole = _열기(path)
    try:
        압축 = 압축인가(ole)
        if 배포용인가(ole):
            # **131자짜리 껍데기를 시험지라 하지 않는다.** 실측: BodyText 에
            # "상위 버전의 배포용 문서입니다 ... 추리논증 / 20 / 짝수형" 만 있었다.
            raise 못뽑음("배포용 문서다 -- 본문이 ViewText 에 잠겨 있다. "
                        "BodyText 에는 껍데기(131자)만 있어서 읽으면 시험지가 아닌 것을 "
                        "시험지라 여기게 된다. `머리글()` 로 PrvText 를 쓰거나 PDF 를 OCR 하라")
        이름들 = sorted("/".join(x) for x in ole.listdir())
        구역 = [s for s in 이름들 if s.startswith("BodyText/Section")]
        if not 구역:
            raise 못뽑음(f"BodyText/Section 이 없다 (가진 것: {이름들[:8]})")
        조각 = []
        for s in sorted(구역, key=lambda s: int(re.sub(r"\D", "", s.split("Section")[-1]) or 0)):
            raw = ole.openstream(s).read()
            buf = zlib.decompress(raw, -15) if 압축 else raw
            for tag, _lvl, 몸 in 레코드들(buf):
                if tag == TAG_PARA_TEXT:
                    조각.append(글자(몸))
        글 = "\n".join(조각)
        if not 글.strip():
            raise 못뽑음("레코드는 읽었는데 글이 한 자도 안 나왔다")
        return 글
    finally:
        ole.close()


def 다듬기(글: str) -> str:
    """쓸데없는 빈 줄을 줄이고 줄 끝 공백을 없앤다. **글자는 안 고친다.**"""
    줄 = [l.rstrip() for l in 글.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out, 빈 = [], 0
    for l in 줄:
        if l.strip():
            빈 = 0
            out.append(l)
        else:
            빈 += 1
            if 빈 <= 1:
                out.append("")
    return "\n".join(out).strip() + "\n"


def main(argv=None) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="HWP 에서 글을 뽑는다")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="", help="쓸 자리. 없으면 화면에")
    ap.add_argument("--머리", action="store_true",
                    help="PrvText(미리보기)만 뽑는다. 배포용 문서도 이건 읽힌다")
    a = ap.parse_args(argv)
    for f in a.files:
        try:
            글 = 다듬기(머리글(f) if a.머리 else 뽑기(f))
        except 못뽑음 as e:
            print(f"[{Path(f).name}] 못 뽑았다: {e}", file=sys.stderr)
            continue
        한글 = sum(1 for c in 글 if "가" <= c <= "힣")
        print(f"[{Path(f).name}] {len(글):,}자 · 한글 {한글:,}자 · 줄 {글.count(chr(10)):,}",
              file=sys.stderr)
        if a.out:
            p = Path(a.out) / (Path(f).stem + ".txt")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(글, encoding="utf-8")
            print(f"  -> {p}", file=sys.stderr)
        else:
            print(글[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
