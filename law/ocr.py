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
import re
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


PROMPT = """아래 그림들은 대한민국 변호사시험 선택형 문제지의 **이어지는 쪽**입니다
(한 장일 수도 있습니다). 준 차례대로 이어서 옮겨 적으십시오.
**보이는 글자를 그대로 옮겨 적으십시오.**

  · 없는 글자를 지어내지 마십시오. 문장이 중간에 끊겨 있으면 끊긴 채로 두십시오.
  · 흐릿해서 못 읽는 자리는 `[읽을 수 없음]` 이라고 적으십시오. 짐작해서 메우지
    마십시오. 조문 번호와 법령명은 특히 그렇습니다 -- 한 글자가 다른 법이 됩니다.
  · 한자(甲乙丙丁戊), 낫표(「민법」), 동그라미 숫자(①②③④⑤), ㄱㄴㄷㄹ 을 그대로
    씁니다.
  · 문항은 `문 12.` 꼴로, 보기는 `ㄱ.` 꼴로, 선택지는 `① ` 꼴로 줄을 시작합니다.
  · 화면 위아래의 시각·통신사·주소창·쪽번호·단추는 옮기지 마십시오.

옮긴 글만 출력하고 다른 말은 붙이지 마십시오."""


def keys() -> list:
    """`GEMINI_API_KEY` 와 그 예비들. **무료 티어는 키마다 따로 센다.**

    실측: 하루 20회에서 막혀 36쪽을 못 끝냈다. 키 하나만 보면 예비 키가 놀고 있어도
    거기서 멈춘다 -- `orchestrator/llm_pool.py` 가 이미 같은 목록을 쓴다.
    """
    import os
    names = ["GEMINI_API_KEY", "GEMINI_API_KEY_FALLBACK"]
    names += [f"GEMINI_API_KEY_FALLBACK{i}" for i in range(2, 9)]
    seen, out = set(), []
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append((n, v))
    return out


def _ask(pngs: list, models: list) -> str:
    """쪽 그림 여럿을 한 번에 보낸다. **호출 수가 곧 쿼터다.**

    쿼터에 막히면 다음 키로, 키가 다 떨어지면 다음 모델로 넘어간다. 마지막까지
    막히면 **거기서 멈춘다** -- 반쯤 옮긴 것을 성공으로 적으면 그 뒤가 전부 거짓이다.
    """
    sys.path.insert(0, str(ROOT / "orchestrator"))
    import gemini_http
    ks = keys()
    if not ks:
        raise SystemExit("GEMINI_API_KEY 가 없다.")
    images = [("image/png", p.read_bytes()) for p in pngs]
    last = None
    for model in models:
        for name, key in ks:
            c = gemini_http.Client(model, key, timeout=300.0, max_output_tokens=8192)
            try:
                return c.invoke(PROMPT, images=images).content
            except Exception as e:                                # noqa: BLE001
                last = f"{model} / {name}: {e}"
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    print(f"    ({name} 이 {model} 에서 쿼터에 막혔다 -- 다음 것으로)")
                    continue
                raise
    raise SystemExit(f"쓸 수 있는 키·모델이 없다. 마지막: {last}")


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


PAGE_MARK = "# --- 쪽 {n} ---"
_MARK = re.compile(r"^#\s*---\s*쪽\s*(\d+)\s*---\s*$", re.M)


def done_pages(out: Path) -> set:
    """이미 옮긴 쪽. **쿼터에 막혀 멈춰도 다음 날 이어서 한다.**"""
    if not out.exists():
        return set()
    return {int(m) for m in _MARK.findall(out.read_text(encoding="utf-8"))}


def compare(a: Path, b: Path) -> int:
    """두 읽기가 **갈리는 자리만** 찍는다.

    처음엔 사람이 옮긴 것을 '기준' 이라 불렀는데 그 틀이 틀렸다. 실측: 확인한 두
    자리에서 전부 사람 쪽이 틀렸고, 그중 하나는 `청구할 수 있다/없다` -- **한 글자가
    답을 뒤집는 자리**였다. 어느 쪽도 기준이 아니다.

    쓸모는 하나다: **갈린 자리를 찾아 사람이 원본을 확대해 보는 것.** 같은 자리는
    둘 다 그렇게 읽었다는 뜻이라 볼 필요가 적고, 갈린 자리는 반드시 봐야 한다.
    """
    import difflib

    def 줄(p):
        return [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.lstrip().startswith("#")]

    A, B = 줄(a), 줄(b)
    n = 0
    for line in difflib.unified_diff(A, B, a.name, b.name, lineterm="", n=0):
        if line.startswith(("---", "+++", "@@")):
            continue
        n += 1
        print(line[:200])
    print(f"\n갈린 줄 {n}개 -- **여기만 원본을 확대해 보면 된다.**"
          if n else "\n두 읽기가 같다.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="시험지 PDF 를 글로 옮긴다 (Gemini 비전)")
    ap.add_argument("pdf", nargs="?", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--쪽", dest="pages", default="")
    ap.add_argument("--그림만", dest="only", default="")
    ap.add_argument("--묶음", dest="batch", type=int, default=3,
                    help="한 번에 보낼 쪽 수. 호출 수가 곧 쿼터다 (기본 3)")
    ap.add_argument("--다시", dest="again", action="store_true",
                    help="이미 옮긴 쪽도 다시")
    ap.add_argument("--견줌", dest="cmp", nargs=2, default=None,
                    help="두 읽기를 견줘 갈리는 줄만 찍는다")
    ap.add_argument("--model", default="gemini-flash-latest,gemini-2.5-flash")
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args(argv)

    if a.cmp:
        return compare(Path(a.cmp[0]), Path(a.cmp[1]))
    if not a.pdf:
        ap.error("시험지 PDF 를 주거나 --견줌 을 주십시오")

    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf 가 없다:  pip install pypdf")
    r = PdfReader(a.pdf)
    want = pages_of(a.pages, len(r.pages))
    out = Path(a.out) if a.out else None
    이미 = set() if (a.again or not out) else done_pages(out)
    남은 = [p for p in want if p not in 이미]
    print(f"쪽 {len(r.pages)}개 중 {len(want)}개가 대상"
          + (f", 이미 옮긴 {len(이미)}개는 건너뛴다" if 이미 else ""))
    if not 남은:
        print("옮길 것이 없다. --다시 로 다시 옮긴다.")
        return 0
    models = [m.strip() for m in a.model.split(",") if m.strip()]
    묶음 = max(1, a.batch)
    print(f"부를 횟수: {-(-len(남은) // 묶음)}회 ({묶음}쪽씩)")

    tmp = Path(a.only) if a.only else Path("/tmp/law_ocr")
    tmp.mkdir(parents=True, exist_ok=True)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
    fh = out.open("a" if 이미 else "w", encoding="utf-8") if out else None
    try:
        for i in range(0, len(남은), 묶음):
            떼 = 남은[i:i + 묶음]
            pngs = [page_png(r.pages[n - 1], tmp / f"p{n:02d}.png", a.scale) for n in 떼]
            if a.only:
                print("  " + ", ".join(str(p) for p in pngs))
                continue
            text = _ask(pngs, models).strip()
            흐림 = text.count("[읽을 수 없음]")
            print(f"  {떼[0]}~{떼[-1]}쪽  {len(text):>5}자"
                  + (f"  **못 읽은 자리 {흐림}군데**" if 흐림 else ""))
            블록 = "\n".join(PAGE_MARK.format(n=n) for n in 떼) + "\n" + text + "\n\n"
            (fh.write(블록) or fh.flush()) if fh else print(text)
    finally:
        if fh:
            fh.close()
    if out:
        print(f"\n{out}\n다음:  python3 law/exam.py {out} --보기")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
