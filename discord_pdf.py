"""discord_pdf -- 메모(.md)를 **핸드폰에서 열리는 PDF** 로.

사용자(2026-09-12): "md가 안보이니 discord에서는 pdf로 제공해라." 핸드폰 디스코드는 .md · .py 를
못 연다. 봇이 산출물을 보낼 때 .md 곁에 같은 내용의 .pdf 를 하나 더 붙인다.

두뇌(조사 c5cc1ef8)가 지은 것을 이어받았다: 검사가 진짜였고(PDF 를 만들어 `%PDF` 머리를 본다)
기능은 두 가지가 비어 있었다 -- **한글 글꼴**(기본 글꼴은 한글을 못 그린다)과 **봇 배선**(만들기만
있고 보내는 자리가 없었다). 둘 다 여기서 채운다.

  글꼴  시스템에서 한글을 그릴 수 있는 TTF 를 찾는다(나눔 · Noto · 은 · 백묵 · 문泉驛 차례).
        없으면 기본 글꼴로 만들되 **그렇다고 말한다** -- 조용히 네모(□)만 찍지 않는다.
  꼴    제목(#) · 글머리(- *) · 코드 블록(```) · 문단. 마크다운 전부가 아니라 메모에 쓰이는 것만.

    python3 discord_pdf.py public_agent_memory/어떤_메모.md        # 옆에 .pdf 를 만든다
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

# 한글을 그릴 수 있는 글꼴 후보. **파일 이름이 아니라 차례**가 뜻이다 -- 앞엣것이 있으면 그것을 쓴다.
글꼴후보 = (
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
    "/usr/share/fonts/truetype/unfonts-core/UnDotum.ttf",
    "/usr/share/fonts/truetype/baekmuk/dotum.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
)
_등록 = {}


def 글꼴찾기() -> "tuple[str, str]":
    """(reportlab 글꼴 이름, 경로). 못 찾으면 ("Helvetica", "") -- 한글이 안 그려진다는 뜻이다."""
    if "이름" in _등록:
        return _등록["이름"], _등록["경로"]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    후보 = list(글꼴후보)
    for 뿌리 in (Path("/usr/share/fonts"), Path.home() / ".fonts", REPO / "fonts"):
        if 뿌리.is_dir():
            for p in sorted(뿌리.rglob("*.tt[fc]")):
                if re.search(r"nanum|notosanskr|notosanscjk|undotum|unbatang|baekmuk|dotum|gulim|malgun|wqy", p.name, re.I):
                    후보.append(str(p))
    for 경로 in 후보:
        if not os.path.isfile(경로):
            continue
        이름 = "한글" + re.sub(r"[^A-Za-z0-9]", "", Path(경로).stem)[:20]
        try:
            pdfmetrics.registerFont(TTFont(이름, 경로, subfontIndex=0) if 경로.endswith(".ttc") else TTFont(이름, 경로))
        except Exception:                                   # noqa: BLE001 -- 다음 후보로
            continue
        _등록.update(이름=이름, 경로=경로)
        return 이름, 경로
    _등록.update(이름="Helvetica", 경로="")
    return "Helvetica", ""


def _줄나누기(글: str, 최대: int) -> "list[str]":
    """글자 수로 자른다 -- 한글은 폭이 고르니 이것으로 충분하다."""
    out = []
    for 문단 in 글.splitlines() or [""]:
        while len(문단) > 최대:
            잘 = 문단.rfind(" ", 0, 최대)
            잘 = 잘 if 잘 > 최대 // 2 else 최대
            out.append(문단[:잘]); 문단 = 문단[잘:].lstrip()
        out.append(문단)
    return out


def 만들기(md: str, 낼곳: "str | Path | None" = None, 제목: str = "") -> dict:
    """마크다운 글 -> PDF 파일. {"경로", "글꼴", "한글": bool, "쪽수"}."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    글꼴, 글꼴경로 = 글꼴찾기()
    한글 = bool(글꼴경로)
    if 낼곳 is None:
        import tempfile
        fd, 낼곳 = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
    낼곳 = Path(낼곳)
    c = canvas.Canvas(str(낼곳), pagesize=A4)
    if 제목:
        c.setTitle(제목)
    폭, 높이 = A4
    왼, 위, 줄간 = 48, 높이 - 56, 15
    y = 위
    쪽 = 1
    if not 한글:
        c.setFont("Helvetica", 9)
        c.drawString(왼, y, "[no CJK font on this machine -- Korean text will not render; install fonts-nanum]")
        y -= 줄간 * 1.5
    코드안 = False
    for 원줄 in md.splitlines():
        줄 = 원줄.rstrip("\n")
        if 줄.strip().startswith("```"):
            코드안 = not 코드안
            continue
        if 코드안:
            크기, 글꼴이름, 들여 = 8.5, ("Courier" if not 한글 else 글꼴), 12
            조각 = _줄나누기(줄, 95)
        elif 줄.startswith("#"):
            깊 = len(줄) - len(줄.lstrip("#"))
            크기, 글꼴이름, 들여 = max(11, 17 - 2 * (깊 - 1)), 글꼴, 0
            줄 = 줄.lstrip("#").strip()
            조각 = _줄나누기(줄, 60)
            y -= 4
        elif re.match(r"^\s*[-*•]\s+", 줄):
            크기, 글꼴이름, 들여 = 10, 글꼴, 14
            줄 = "• " + re.sub(r"^\s*[-*•]\s+", "", 줄)
            조각 = _줄나누기(줄, 80)
        else:
            크기, 글꼴이름, 들여 = 10, 글꼴, 0
            조각 = _줄나누기(줄, 84)
        for 토막 in 조각:
            if y < 56:
                c.showPage(); 쪽 += 1; y = 위
            c.setFont(글꼴이름, 크기)
            c.drawString(왼 + 들여, y, 토막)
            y -= 줄간 if 크기 <= 10 else 줄간 + 4
    c.save()
    return {"경로": str(낼곳), "글꼴": 글꼴, "한글": 한글, "쪽수": 쪽}


def md파일을pdf로(md경로: "str | Path", 낼곳디렉터리: "str | Path | None" = None) -> dict:
    """메모 파일 -> 같은 이름의 .pdf. 기본은 logs/pdf/ 아래(저장소를 안 더럽힌다)."""
    md경로 = Path(md경로)
    글 = md경로.read_text(encoding="utf-8", errors="replace")
    # 앞머리(--- … ---)는 뺀다 -- 메모의 살이 아니다
    글 = re.sub(r"\A---\n.*?\n---\n", "", 글, count=1, flags=re.S)
    디렉터리 = Path(낼곳디렉터리) if 낼곳디렉터리 else (REPO / "logs" / "pdf")
    디렉터리.mkdir(parents=True, exist_ok=True)
    return 만들기(글, 디렉터리 / (md경로.stem + ".pdf"), 제목=md경로.stem)


def format_markdown_as_pdf(markdown_text: str, output_path: "str | None" = None) -> str:
    """두뇌(조사 c5cc1ef8)가 지은 이름 -- 그 검사가 이 이름을 부른다. 같은 일이다."""
    return 만들기(markdown_text, output_path)["경로"]


def main() -> int:
    if len(sys.argv) < 2:
        print("쓰기: python3 discord_pdf.py <메모.md> [낼 디렉터리]")
        return 2
    r = md파일을pdf로(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"{r['경로']} · 글꼴 {r['글꼴']}{'' if r['한글'] else ' (한글 못 그림 -- fonts-nanum 을 깔아라)'} · {r['쪽수']}쪽")
    return 0 if r["한글"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
