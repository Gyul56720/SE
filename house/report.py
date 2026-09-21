# -*- coding: utf-8 -*-
"""house/report -- 보고서를 PDF 로 내고, 사내 메일 양식에 맞춰 보낸다.

**규칙 하나.** 이 모듈이 내는 보고서에는 그림이 반드시 들어간다. 그림이 하나도 없는
보고서는 `내기()` 가 거절한다 -- 사용자(2026-09-21): "에이전트들은 이론서가 아니다.
보고서는 이해하기 쉬어야 하며, 이는 반드시 시각화가 되어 있어야한다."

**규칙 둘.** 수는 '잰 것' 과 '가정한 것' 을 갈라 적는다. 보고서의 모든 표에는 그 수가
어느 도구에서 나왔는지를 적는 칸이 있다. 도구가 없어서 대안을 쓴 것은 대안 이름을
그대로 적는다(예: "OpenSTA 없음 -> house/syn/sta_pvt.py").
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
sys.path.insert(0, str(저장소))

from house import people as 사람들  # noqa: E402
from house import viz  # noqa: E402

내는곳 = 뿌리 / "out"
원장 = 저장소 / "logs" / "house_ledger.jsonl"

CSS = """
@page { size: A4; margin: 15mm 14mm 16mm 14mm;
        @bottom-center { content: counter(page) " / " counter(pages);
                         font-family: 'NanumGothic', sans-serif; font-size: 8pt; color: #8a8f98; } }
* { box-sizing: border-box; }
body { font-family: 'NanumGothic','Noto Sans CJK KR',sans-serif; font-size: 9.6pt;
       color: #1b1b1f; line-height: 1.5; }
h1 { font-size: 17pt; margin: 0 0 2mm 0; letter-spacing: -0.3px; }
h2 { font-size: 12.5pt; margin: 7mm 0 2mm 0; padding-bottom: 1.2mm;
     border-bottom: 1.6px solid #1b1b1f; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; color: #1b1b1f; page-break-after: avoid; }
p  { margin: 0 0 2mm 0; }
code, .mono { font-family: 'NanumGothicCoding','DejaVu Sans Mono',monospace; font-size: 8.6pt; }
pre { background: #f5f7fa; border: 1px solid #e3e7ec; border-radius: 3px;
      padding: 2.4mm 3mm; font-family: 'NanumGothicCoding','DejaVu Sans Mono',monospace;
      font-size: 8.0pt; line-height: 1.38; white-space: pre-wrap; overflow-wrap: anywhere;
      page-break-inside: avoid; }
.head { border: 1.8px solid #1b1b1f; border-radius: 4px; padding: 3.5mm 4mm; margin-bottom: 4mm; }
.head .who { font-size: 9pt; color: #454b54; margin-top: 1.5mm; }
.head .who b { color: #1b1b1f; }
.kv { display: flex; flex-wrap: wrap; gap: 0 6mm; font-size: 8.6pt; color: #454b54; margin-top: 2mm; }
.sum { background: #fdf6e3; border-left: 3.5px solid #e08a2e; padding: 2.6mm 3.4mm;
       margin: 0 0 4mm 0; page-break-inside: avoid; }
.sum ul { margin: 1mm 0 0 4mm; padding: 0; }
.sum li { margin: 0.8mm 0; }
.note { background: #eef4fb; border-left: 3.5px solid #1f6feb; padding: 2.4mm 3.2mm;
        margin: 2.5mm 0; font-size: 9.1pt; page-break-inside: avoid; }
.warn { background: #f9ecec; border-left: 3.5px solid #c0392b; padding: 2.4mm 3.2mm;
        margin: 2.5mm 0; font-size: 9.1pt; page-break-inside: avoid; }
.fig { margin: 3mm 0 4mm 0; page-break-inside: avoid; text-align: center; }
.fig svg { display: block; margin: 0 auto; }
.cap { font-size: 8.4pt; color: #5b616b; margin-top: 1.4mm; text-align: left; }
.cap b { color: #1b1b1f; }
table.d { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 2mm 0 3mm 0;
          page-break-inside: avoid; }
table.d th { background: #1b1b1f; color: #fff; text-align: left; padding: 1.5mm 2mm;
             font-weight: bold; }
table.d td { border-bottom: 1px solid #e3e7ec; padding: 1.4mm 2mm; vertical-align: top; }
table.d tr:nth-child(even) td { background: #fafbfc; }
table.d td.hi { font-weight: bold; }
.tool { font-size: 8.3pt; color: #5b616b; margin: 1.5mm 0 3mm 0; }
.tool b { color: #1b1b1f; }
.sig { margin-top: 6mm; padding-top: 2.5mm; border-top: 1px solid #c9ced6;
       font-size: 8.4pt; color: #5b616b; }
.limit { background: #f5f7fa; border: 1px dashed #8a8f98; padding: 2.6mm 3.2mm;
         font-size: 8.7pt; margin-top: 3mm; page-break-inside: avoid; }
"""


def _e(s) -> str:
    return html.escape(str(s), quote=False)


_굵 = re.compile(r"\*\*(.+?)\*\*", re.S)


def _꾸밈(s: str) -> str:
    """`**이것**` 을 굵게 바꾼다.

    실측 2026-09-21: 보고서 1쪽에 `**있는**` 이 별표째로 찍혔다. 사람이 글을 쓸 때
    손이 마크다운으로 가는 것은 막을 수 없으니, 내는 쪽에서 받아 준다.
    """
    return _굵.sub(r"<b>\1</b>", str(s))


class 보고서:
    """그림과 표를 쌓아 PDF 하나로 낸다."""

    def __init__(self, 담당, 제목, 과제, 부제=""):
        self.담당 = 담당 if hasattr(담당, "이름") else 사람들.키로[담당]
        self.제목 = 제목
        self.과제 = 과제
        self.부제 = 부제
        self.조각 = []
        self.요약줄 = []
        self.그림수 = 0
        self.표수 = 0
        self.잰것 = []          # (이름, 값, 단위, 도구)
        self.시작 = time.time()
        self.업무초 = None      # 실제로 도구를 돌린 시간 (보고서 조립 시간이 아니다)

    # ---- 쌓기 ----
    def 요약(self, 줄: str):
        self.요약줄.append(_꾸밈(줄))
        return self

    def 절(self, 이름: str):
        self.조각.append(f"<h2>{_e(이름)}</h2>")
        return self

    def 소절(self, 이름: str):
        self.조각.append(f"<h3>{_e(이름)}</h3>")
        return self

    def 글(self, s: str):
        self.조각.append(f"<p>{_꾸밈(s)}</p>")
        return self

    def 짚기(self, s: str):
        self.조각.append(f'<div class="note">{_꾸밈(s)}</div>')
        return self

    def 경고(self, s: str):
        self.조각.append(f'<div class="warn">{_꾸밈(s)}</div>')
        return self

    def 한계(self, s: str):
        self.조각.append(f'<div class="limit"><b>이 보고서가 하지 않은 것</b><br>{_꾸밈(s)}</div>')
        return self

    def 코드(self, s: str, 이름=""):
        머리 = f'<div class="tool"><b>{_e(이름)}</b></div>' if 이름 else ""
        self.조각.append(머리 + f"<pre>{_e(s)}</pre>")
        return self

    def 그림(self, svg: str, 설명: str = "", 도구: str = ""):
        self.그림수 += 1
        cap = f'<div class="cap"><b>그림 {self.그림수}.</b> {_꾸밈(설명)}' + \
              (f' <span style="color:#8a8f98">[{_e(도구)}]</span>' if 도구 else "") + "</div>"
        self.조각.append(f'<div class="fig">{svg}{cap}</div>')
        return self

    def 표(self, 머리, 줄들, 설명="", 도구="", 강조열=None):
        self.표수 += 1
        t = viz.표(머리, 줄들, 강조열)
        cap = ""
        if 설명 or 도구:
            cap = (f'<div class="cap"><b>표 {self.표수}.</b> {_꾸밈(설명)}' +
                   (f' <span style="color:#8a8f98">[{_e(도구)}]</span>' if 도구 else "") + "</div>")
        self.조각.append(cap + t)
        return self

    def 잰다(self, 이름, 값, 단위="", 도구=""):
        self.잰것.append((이름, 값, 단위, 도구))
        return self

    # ---- 내기 ----
    def html(self) -> str:
        if self.그림수 == 0:
            raise RuntimeError(
                "그림이 없는 보고서는 내지 않는다 -- 이 회사의 규칙이다. "
                "최소 한 장은 시각화해라 (house/report.py)")
        p = self.담당
        오늘 = time.strftime("%Y-%m-%d")
        요약 = "".join(f"<li>{s}</li>" for s in self.요약줄) or "<li>-</li>"
        잰표 = ""
        if self.잰것:
            줄들 = [[n, str(v), u, t or "-"] for n, v, u, t in self.잰것]
            잰표 = ('<h2>부록 A. 이 보고서가 낸 수와 그 출처</h2>'
                   '<p class="tool">모든 수는 아래 도구가 <b>실제로 돌아서</b> 나온 값이다. '
                   '가정한 값은 도구 칸에 <b>가정</b> 이라고 적는다.</p>'
                   + viz.표(["양", "값", "단위", "무엇으로 쟀나"], 줄들))
        걸린 = self.업무초 if self.업무초 is not None else (time.time() - self.시작)
        return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{_e(self.제목)}</title><style>{CSS}</style></head><body>
<div class="head">
  <h1>{_e(self.제목)}</h1>
  {f'<div style="font-size:9.5pt;color:#454b54">{_e(self.부제)}</div>' if self.부제 else ''}
  <div class="who">작성 <b>{_e(p.이름)}</b> · {_e(p.직급)} · {_e(p.팀)} &nbsp;|&nbsp;
       {_e(사람들.회사)} ({_e(사람들.회사약칭)})</div>
  <div class="kv">
    <span>과제: <b>{_e(self.과제)}</b></span>
    <span>작성일: {오늘}</span>
    <span>문서: {_e(self.담당.키.upper())}-RPT</span>
    <span>도구 실행 시간: {걸린:.1f} s</span>
  </div>
</div>
<div class="sum"><b>1. 주요 진행 상황 (요약)</b><ul>{요약}</ul></div>
{"".join(self.조각)}
{잰표}
<div class="sig">{_e(p.이름)} / {_e(p.서명)} · {_e(p.메일)}<br>
이 문서는 {_e(사람들.회사)} 의 자동 설계 흐름이 생성했습니다. 모든 그림은 실제 실행 결과에서 그려집니다.</div>
</body></html>"""

    def 내기(self, 파일이름=None) -> Path:
        """**HTML 을 먼저 쓰고** PDF 를 만든다.  순서가 중요하다 --
        PDF 단계가 죽어도 내용은 남아야 한다."""
        내는곳.mkdir(parents=True, exist_ok=True)
        이름 = 파일이름 or f"{time.strftime('%Y%m%d')}_{self.담당.이름.replace(' ', '')}_{self.담당.키.upper()}.pdf"
        길 = 내는곳 / 이름
        h = self.html()
        htm = 내는곳 / (길.stem + ".html")
        htm.write_text(h, encoding="utf-8")            # 무슨 일이 있어도 이건 남는다
        try:
            from weasyprint import HTML                # 무거워서 여기서 들인다
        except ImportError as e:
            raise RuntimeError(
                f"weasyprint 가 없어 PDF 를 못 만들었다 ({e}). "
                f"HTML 은 남겼다: {htm}\n"
                "**사람에게 설치를 시키지 마라** -- requirements.txt 에 "
                "`weasyprint>=60` 을 넣고 main 에 머지하면 배포가 깐다 "
                "(CLAUDE.md '사람에게 설치를 시키지 마라 -- 배포가 이미 깐다')."
            ) from e
        HTML(string=h, base_url=str(뿌리)).write_pdf(str(길))
        return 길


def PDF된다() -> dict:
    """**다섯이 줄줄이 같은 까닭으로 죽기 전에 한 번 묻는다.**

    실측 2026-09-21: VM 에서 Priya · Sofia · Kenji 가 각자 보고서를 다 만들고
    마지막 한 줄에서 똑같이 `ModuleNotFoundError: weasyprint` 로 죽었다.
    세 번 같은 말을 듣는 것보다 시작할 때 한 번 아는 것이 낫다.
    """
    try:
        import weasyprint
        return {"된다": True, "판": getattr(weasyprint, "__version__", "?")}
    except ImportError as e:
        return {"된다": False, "까닭": str(e)[:120],
                "고치는법": "requirements.txt 에 `weasyprint>=60` -> main 머지 -> 배포가 깐다"}


# -------------------------------------------------------------- 메일

def 메일본문(담당, 제목, 요약줄, 특이사항, 수신자="대표", 첨부이름="") -> str:
    """사용자가 준 사내 메일 양식 그대로."""
    p = 담당 if hasattr(담당, "이름") else 사람들.키로[담당]
    항목 = "\n".join(f"  * {s}" for s in 요약줄) or "  * -"
    특 = "\n".join(f"  * {s}" for s in (특이사항 or ["없음"]))
    첨부줄 = f"\n첨부: {첨부이름}\n" if 첨부이름 else "\n"
    return f"""안녕하세요 {수신자}님,

{p.팀} {p.직급} {p.이름}입니다.
{제목}에 대한 업무 보고드립니다.
상세 내용은 첨부 파일 참고 부탁드립니다.
{첨부줄}
1. 주요 진행 상황 (요약)

{항목}

2. 특이사항 및 요청/문의 사항

{특}

관련하여 검토 후 피드백 부탁드립니다.
감사합니다.

{p.이름} 올림

---------------------------------------------
  소속: {사람들.회사} / {p.팀} / {p.직급}
  담당: {p.직무.splitlines()[0][:70]}
  이메일: {p.메일}
---------------------------------------------
"""


def 메일제목(담당, 과제) -> str:
    p = 담당 if hasattr(담당, "이름") else 사람들.키로[담당]
    주 = time.strftime("%Y년 %m월 %d일")
    return f"[보고] {주} {과제}_{p.팀} {p.이름}"


def 보내기(담당, 제목, 본문, 첨부: "list[Path] | None" = None, to=None, repo=None) -> dict:
    """mailer 를 쓰되 첨부를 얹는다.  mailer 가 없는 값을 물으면 그 말을 그대로 돌려준다."""
    sys.path.insert(0, str(저장소))
    import mailer
    첨부 = [Path(a) for a in (첨부 or [])]
    받는이 = to or mailer.내정보(repo)["주소"]
    if not 받는이:
        # **"me" 로 보내지 않는다.** 주소를 모르면 보내는 시늉을 하는 대신
        # 무엇이 없는지 말한다 -- 사용자가 `!열쇠 USER_EMAIL=...` 한 줄로 준다.
        return {"보냈나": False, "필요한것": ["USER_EMAIL"],
                "말": "받는 주소를 모른다 -- `!열쇠 USER_EMAIL=<주소>` 로 한 번 주면 된다"}
    return mailer.보내기_첨부(받는이, 제목, 본문, 첨부, repo=repo)


def 원장적기(줄: dict) -> None:
    import json
    원장.parent.mkdir(parents=True, exist_ok=True)
    줄 = dict(줄)
    줄.setdefault("때", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(원장, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 쪽수(길: Path) -> int:
    """PDF 쪽 수.  보고서가 실제로 만들어졌는지 확인하는 싼 방법.

    weasyprint 는 오브젝트를 압축해서 넣으므로 `/Type /Page` 를 날것으로 못 센다
    (실측: 14장짜리 보고서가 1쪽으로 나왔다). pypdf 가 있으면 그것으로 세고,
    없으면 0 을 돌려주고 '못 셌다' 로 다룬다 -- 틀린 수를 내지 않는다.
    """
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(길)).pages)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        import pikepdf
        with pikepdf.open(str(길)) as f:
            return len(f.pages)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        b = Path(길).read_bytes()
        n = len(re.findall(rb"/Type\s*/Page[^s]", b))
        return n if n > 0 else 0
    except Exception:                                        # noqa: BLE001
        return 0
