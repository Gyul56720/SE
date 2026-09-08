"""**시험지를 글로 옮긴다.** 그림을 Gemini 에게 보여 주고 받아 적게 한다.

    python3 law/ocr.py 시험지.pdf --쪽 1-3           # 몇 쪽만 시험 삼아
    python3 law/ocr.py 시험지.pdf --out law/exam/2026_민사법_선택형.txt
    python3 law/ocr.py 시험지.pdf --그림만 /tmp/쪽    # 부르지 않고 PNG 만 뽑는다

## 왜 tesseract 가 아닌가

한국어 법률문은 한자(甲乙丙丁)와 낫표(「민법」)와 원문자(①ㄱ)가 섞인다. 스캔이 아니라
**휴대폰으로 찍은 화면**이면 더 나쁘다. 실측: 기존 OCR 결과가 쓸 수 없는 수준이었다.
비전 모델은 이 꼴을 훨씬 잘 읽고, 이 저장소는 이미 Gemini 키와 클라이언트를 들고 있다.

## 옮겨 적는 자도 지어낸다

이게 이 파일의 유일한 위험이다. 안 보이는 글자를 모델이 **그럴듯하게 메운다.** 법률문에서
그것은 조문 번호가 바뀌고 '취소' 가 '무효' 가 된다는 뜻이다. 그래서 프롬프트가 시키는
것은 하나뿐이다 -- **보이는 대로만 적고, 안 보이면 `[읽을 수 없음]` 이라고 적어라.**

메웠는지는 `law/exam.py --보기` 가 되짚는다: 선택지를 못 읽은 문항이 몇 개인지, 번호가
빠짐없이 이어지는지. **옮겨 적기가 조용히 반쯤 성공하면 그 뒤의 점수가 전부 거짓이다.**

## PDF 는 그림뿐이다

이 시험지 PDF 는 쪽마다 그림 하나이고 글자층이 없다(그래서 OCR 이 필요하다).
poppler 없이 순수 파이썬으로 PNG 를 만든다 -- 서버에 깔 것을 늘리지 않는다.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent

# 휴대폰 화면 위아래의 껍데기(시각·주소창·아래 단추)를 그림에서부터 잘라 낸다.
TOP, BOT = 0.13, 0.92


def page_png(page, out: Path, scale: int = 2) -> Path:
    """PDF 쪽의 그림 하나를 PNG 로. 세로로 잘라 껍데기를 뺀다."""
    xo = page["/Resources"]["/XObject"]
    im = xo[list(xo.keys())[0]]
    w, h = int(im["/Width"]), int(im["/Height"])
    raw = zlib.decompress(im._data)
    ch = len(raw) // (w * h)
    rows = []
    for y in range(int(h * TOP), int(h * BOT), scale):
        line = raw[y * w * ch:(y + 1) * w * ch]
        rows.append(b"\x00" + b"".join(line[x*ch:(x+1)*ch] for x in range(0, w, scale)))

    def ck(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t+d) & 0xffffffff)

    W, H = len(range(0, w, scale)), len(rows)
    out.write_bytes(b"\x89PNG\r\n\x1a\n"
                    + ck(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, {1: 0, 3: 2}[ch], 0, 0, 0))
                    + ck(b"IDAT", zlib.compress(b"".join(rows), 6)) + ck(b"IEND", b""))
    return out


PROMPT = """이 그림은 대한민국 변호사시험 선택형 문제지의 한 쪽입니다.
**보이는 글자를 그대로 옮겨 적으십시오.**

  · 없는 글자를 지어내지 마십시오. 문장이 중간에 끊겨 있으면 끊긴 채로 두십시오.
  · 흐릿해서 못 읽는 자리는 `[읽을 수 없음]` 이라고 적으십시오. 짐작해서 메우지
    마십시오. 조문 번호와 법령명은 특히 그렇습니다 -- 한 글자가 다른 법이 됩니다.
  · 한자(甲乙丙丁戊), 낫표(「민법」), 동그라미 숫자(①②③④⑤), ㄱㄴㄷㄹ 을 그대로
    씁니다.
  · 문항은 `문 12.` 꼴로, 보기는 `ㄱ.` 꼴로, 선택지는 `① ` 꼴로 줄을 시작합니다.
  · 화면 위아래의 시각·통신사·주소창·쪽번호·단추는 옮기지 마십시오.

옮긴 글만 출력하고 다른 말은 붙이지 마십시오."""


def _ask(png: Path, model: str) -> str:
    sys.path.insert(0, str(ROOT / "orchestrator"))
    import gemini_http
    import os
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY 가 없다.")
    c = gemini_http.Client(model, key, timeout=180.0, max_output_tokens=8192)
    return c.invoke(PROMPT, images=[("image/png", png.read_bytes())]).content


def pages_of(spec: str, n: int) -> list:
    """`3` · `1-4` · `1-4,9` 를 쪽 번호 목록으로. 없으면 전부."""
    if not spec:
        return list(range(1, n + 1))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return [p for p in out if 1 <= p <= n]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="시험지 PDF 를 글로 옮긴다 (Gemini 비전)")
    ap.add_argument("pdf")
    ap.add_argument("--out", default="")
    ap.add_argument("--쪽", dest="pages", default="")
    ap.add_argument("--그림만", dest="only", default="")
    ap.add_argument("--model", default="gemini-flash-latest")
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args(argv)

    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf 가 없다:  pip install pypdf")
    r = PdfReader(a.pdf)
    want = pages_of(a.pages, len(r.pages))
    print(f"쪽 {len(r.pages)}개 중 {len(want)}개를 옮긴다")

    tmp = Path(a.only) if a.only else Path("/tmp/law_ocr")
    tmp.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
    fh = out.open("w", encoding="utf-8") if out else None
    try:
        for i in want:
            png = page_png(r.pages[i - 1], tmp / f"p{i:02d}.png", a.scale)
            if a.only:
                print(f"  {png}")
                continue
            text = _ask(png, a.model).strip()
            # **못 읽은 자리를 세어 보여 준다.** 조용히 메워진 것보다 낫다.
            흐림 = text.count("[읽을 수 없음]")
            print(f"  {i:>2}쪽  {len(text):>5}자"
                  + (f"  **못 읽은 자리 {흐림}군데**" if 흐림 else ""))
            (fh.write(text + "\n\n") if fh else print(text))
    finally:
        if fh:
            fh.close()
    if out:
        print(f"\n{out}\n다음:  python3 law/exam.py {out} --보기")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
