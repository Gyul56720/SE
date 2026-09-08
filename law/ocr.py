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
import time
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


_POOL = None


def _pool():
    """**`novel/` 이 쓰는 그 후보 풀을 그대로 쓴다.**

    처음엔 여기에 키·모델을 도는 반복문을 따로 짰다. **그게 두 벌이었다.**
    `orchestrator/llm_pool.py` 는 (키·모델)별 잔량 추적, RPM 쿨다운, 500/503 을 거듭
    내는 후보 격리, 실측 지연 기반 순위, 바퀴 사이 대기를 이미 갖고 있다 -- 소설
    파이프라인이 회차마다 100번씩 두드리며 다듬은 층이다. 내 반복문은 그것을 전부
    버리고 `for 모델: for 키:` 로 되돌린 것이었다.

    **gemma 는 뺀다.** 그림을 못 보므로 부르면 실패만 물고 온다. 이건 이 쓰임에만
    맞는 거르개라 여기서 한다 -- 풀은 글에도 쓰이고 거기서는 gemma 가 제 몫을 한다.
    """
    global _POOL
    if _POOL is None:
        sys.path.insert(0, str(ROOT / "orchestrator"))
        import llm_pool
        pool = [c for c in llm_pool.build_pool() if "gemma" not in c[0].lower()]
        if not pool:
            raise SystemExit(
                "그림을 볼 수 있는 후보가 없다 -- GEMINI_API_KEY 를 확인하라.")
        _POOL = pool
        print(f"후보 {len(pool)}개: "
              + ", ".join(l for l, _ in pool[:4])
              + (" ..." if len(pool) > 4 else ""))
    return _POOL


def _ask(pngs: list, prefer: str = "flash") -> str:
    """쪽 그림 여럿을 한 번에 보낸다. **호출 수가 곧 쿼터다.**

    재시도·키 돌려쓰기·쿨다운은 전부 풀이 한다. 여기서는 무엇에 막혀 끝났는지만
    가려서 말한다 -- 다음에 무엇을 할지가 거기서 갈린다.
    """
    sys.path.insert(0, str(ROOT / "orchestrator"))
    import llm_pool
    images = [("image/png", p.read_bytes()) for p in pngs]
    try:
        text, label = llm_pool.call(_pool(), PROMPT, pool_id="ocr",
                                    images=images, prefer=prefer)
    except Exception as e:                                        # noqa: BLE001
        raise SystemExit(
            f"{_why(e)} -- 멈춘다.\n  마지막: {str(e)[:200]}\n"
            f"  쿼터면 내일 같은 명령을 다시 치면 남은 쪽부터 이어간다.\n"
            f"  과부하(503)면 조금 뒤에 다시 치면 된다.")
    return text


def _why(e) -> str:
    """무엇에 막혔나. **가려서 보고해야 다음에 무엇을 할지 안다.**"""
    t = str(e)
    if "RESOURCE_EXHAUSTED" in t or "429" in t:
        return "쿼터에 막혔다"
    if "UNAVAILABLE" in t or "503" in t or "overloaded" in t.lower():
        return "과부하"
    if "500" in t or "INTERNAL" in t or "DEADLINE" in t or "504" in t:
        return "과부하"
    if "NOT_FOUND" in t or "404" in t:
        return "그런 모델이 없다"
    return "막혔다"


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


_같은뜻 = str.maketrans({"O": "○", "o": "○", "X": "×", "x": "×", "ｘ": "×"})


def _홈(s: str) -> str:
    """줄바꿈·띄어쓰기와 ○/O·×/X 만 고른다. **글자가 다른 것만 남긴다.**"""
    return re.sub(r"\s+", "", s).translate(_같은뜻)


def _문항별(p: Path) -> dict:
    from law import exam as EX
    d = {}
    for q in EX.parse(p.read_text(encoding="utf-8")):
        if q.번호 in d:                     # 쪽 경계에서 두 조각으로 갈린 문항
            o = d[q.번호]
            o.물음 = (o.물음 + " " + q.물음).strip()
            o.보기 += q.보기
            o.선택지 += q.선택지
        else:
            d[q.번호] = q
    return d


def compare(a: Path, b: Path) -> int:
    """두 읽기가 **갈리는 자리만** 찍는다. 줄 단위가 아니라 **문항의 칸 단위**로.

    처음엔 사람이 옮긴 것을 '기준' 이라 불렀는데 그 틀이 틀렸다. 실측: 확인한 자리에서
    양쪽 다 틀린 데가 있었다. 문 2 ④ `청구할 수 있다/없다` 는 사람이 틀렸고(한 글자가
    답을 뒤집는다), 문 8 ㄱ `각/각각` 은 OCR 이 틀렸다. **어느 쪽도 기준이 아니다.**

    처음 판은 줄 단위 diff 였는데 **자가 잘못돼 있었다.** 두 읽기는 줄을 다르게 접고
    ○ 를 O 로 적기도 한다 -- 그건 갈린 게 아닌데 전부 갈린 줄로 세어졌다. 실측:
    717 줄이 나왔고 그 안에서 진짜 갈린 자리는 보이지 않았다. **과잉 기각하는 심판은
    맞는 답도 버린다.** 그래서 문항 번호로 짝을 짓고, 물음·보기·선택지 칸끼리
    맞대고, 띄어쓰기와 ○/O 를 고른 뒤에 남는 것만 갈렸다고 부른다.

    한쪽에만 있는 문항은 갈린 게 아니라 **한쪽이 안 읽은 것**이라 따로 센다. 한 칸이
    다른 칸의 앞머리이기만 하면 **잘린 것**이라 또 따로 센다. 남는 것이 사람이
    원본을 확대해 봐야 할 자리다.
    """
    A, B = _문항별(a), _문항별(b)
    둘, A만, B만 = sorted(set(A) & set(B)), sorted(set(A) - set(B)), sorted(set(B) - set(A))
    같음 = 잘림 = 0
    갈림 = []
    for n in 둘:
        x, y = A[n], B[n]
        yb = dict(y.보기)
        칸 = [("물음", x.물음, y.물음)]
        칸 += [(f"보기 {k}", s, yb.get(k, "")) for k, s in x.보기]
        칸 += [(f"선택지 {i + 1}", s, y.선택지[i] if i < len(y.선택지) else "")
               for i, s in enumerate(x.선택지)]
        for 이름, s, u in 칸:
            S, U = _홈(s), _홈(u)
            if S == U:
                같음 += 1
            elif S and U and (S.startswith(U) or U.startswith(S)):
                잘림 += 1
            else:
                갈림.append((n, 이름, s, u))

    for n, 이름, s, u in 갈림:
        print(f"\n문 {n} {이름}\n  {a.name}: {s[:180]}\n  {b.name}: {u[:180]}")
    print(f"\n두 읽기에 다 있는 문항 {len(둘)}개 · 칸 같음 {같음} · 한쪽이 잘림 {잘림}"
          f" · **갈림 {len(갈림)}**")
    if A만:
        print(f"{a.name} 에만 있는 문항 {len(A만)}개: {A만[:20]}")
    if B만:
        print(f"{b.name} 에만 있는 문항 {len(B만)}개: {B만[:20]}")
    print("**갈린 자리만 원본을 확대해 보면 된다.**" if 갈림 else "**갈린 자리가 없다.**")
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
    # **모델을 손으로 고르지 않는다.** 풀이 (키·모델)별 잔량과 실측 지연으로 고른다 --
    # 하나를 못 박으면 그것이 막힐 때 갈 곳이 없다. 앞으로 당길 것만 말한다.
    ap.add_argument("--선호", dest="prefer", default="flash",
                    help="이 이름이 든 후보를 먼저 두드린다 (거르지는 않는다)")
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
            text = _ask(pngs, a.prefer).strip()
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
