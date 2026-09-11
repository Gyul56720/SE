"""dig 비언어 -- 수식(LaTeX)·표·그림(포인터)·PDF·TeX·arXiv 문 순서를 **실제로** 붙든다. 도메인 무관.

이 저장소 규율: 픽셀은 못 검증하니 캡션·출처 포인터만, 수식은 LaTeX 문자열 그대로(검증 가능),
못 읽은 것은 '못읽음'(≠안전). PDF 만 있으면 수식이 흩어지므로 HTML/TeX 가 먼저다.

(1) extract.수식뽑기 가 TeX 환경·$$…$$ 의 LaTeX 를 원문으로, (2) extract.뽑기 가 MathML
alttext·annotation 을 수식으로, figcaption·img 를 그림 포인터로(픽셀·base64 안 담음), (3)
fetch 가 arXiv 를 HTML·ar5iv 로 돌리고, (4) paper.논문받기 가 문 순서(HTML→ar5iv→abs→PDF→TeX)
대로 내리고 무엇을 못 읽었는지 적으며, 깨끗한 HTML 에서 수식을 얻으면 PDF 를 안 연다, (5)
TeX 소스에서 수식·알고리즘·캡션을, (6) 요지가 못 읽은 것을 정직히 적는다.

network·LLM·pypdf 없이 돈다(가짜 fetch·바이트 주입). 실행: python3 tests/test_dig_비언어.py
"""
from __future__ import annotations

import gzip
import io
import sys
import tarfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from dig import extract as X  # noqa: E402
from dig import fetch as F  # noqa: E402
from dig import paper as PP  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== extract.수식뽑기: TeX 환경·구분자의 LaTeX 를 원문으로 ==")
s = r"intro \begin{equation} E = mc^2 \end{equation} mid $$\frac{a}{b}$$ and \(x+y\) end \begin{align} a &= b \end{align}"
수 = X.수식뽑기(s)
ok("E = mc^2" in 수 and "\\frac{a}{b}" in 수 and "x+y" in 수 and "a &= b" in 수, f"환경·$$·\\( 다 ({수})")
ok("%" not in " ".join(수), "주석 섞인 것은 부르는 쪽(tex뽑기)이 지운다")
ok(X.수식뽑기("") == [] and X.수식뽑기("no math here") == [], "수식 없으면 빈 목록")

print("\n== extract.뽑기: MathML·annotation·figcaption·img ==")
html = ('<h1>T</h1><p>prose.</p>'
        '<math alttext="\\alpha P"><annotation encoding="application/x-tex">E=mc^2</annotation></math>'
        '<math alttext="\\alpha P"></math>'
        '<figure><img src="/f1.png" alt="overview"><figcaption>Figure 1: pipeline.</figcaption></figure>'
        '<table><tr><th>m</th><th>a</th></tr><tr><td>ours</td><td>0.9</td></tr></table>')
d = X.뽑기(html, "text/html", "https://arxiv.org/html/2401.00001")
ok("\\alpha P" in d["수식"] and "E=mc^2" in d["수식"], f"alttext·annotation 수식 ({d['수식']})")
ok(d["수식"].count("\\alpha P") == 1, "중복 수식은 한 번")
ok(any(g["캡션"].startswith("Figure 1") for g in d["그림"]) and any(g["src"] == "/f1.png" for g in d["그림"]),
   f"figcaption·img 포인터 ({d['그림']})")
ok(all("base64" not in str(g).lower() for g in d["그림"]), "픽셀·base64 안 담음")
ok(d["표"] == [[{"m": "ours", "a": "0.9"}]], f"표는 구조로 ({d['표']})")

print("\n== fetch: arXiv 를 HTML·ar5iv 로 ==")
곁 = F.곁문("https://arxiv.org/pdf/2401.00001v2")
ok(any("arxiv.org/html/2401.00001" in u for u in 곁) and any("ar5iv" in u for u in 곁), "arxiv 곁문")
ok(not any("ar5iv" in u for u in F.곁문("https://example.com/x")), "arxiv 아니면 안 붙인다")

print("\n== paper.논문받기: 문 순서 · 깨끗한 HTML 이면 PDF 안 엶 ==")
열린문 = []


def 가짜한번(u, h, t=25.0):
    열린문.append(u)
    if "arxiv.org/html/" in u:
        몸 = ('<html><head><meta name="citation_abstract" content="We study X."></head><body>'
             '<h1>Paper Title</h1><p>body text here.</p>'
             '<math alttext="\\nabla f = 0"></math>'
             '<figure><figcaption>Figure 2: the method.</figcaption></figure></body></html>')
        return F.응답(url=u, 최종url=u, 코드=200, 몸통=몸, 꼴="text/html", 헤더={})
    return F.응답(url=u, 코드=404, 왜="HTTP 404")


PP.한번 = 가짜한번
PP.바이트받기 = lambda u: (_ for _ in ()).throw(AssertionError("HTML 에서 수식을 얻었으면 PDF/TeX 안 열어야"))
try:
    논 = PP.논문받기("https://arxiv.org/abs/2401.00001")
    ok(논["제목"] == "Paper Title" and "We study X." in 논["초록"], f"제목·초록 ({논['제목']!r})")
    ok("\\nabla f = 0" in 논["수식"], "HTML MathML 수식을 얻는다")
    ok(any("Figure 2" in g["캡션"] for g in 논["그림"]), "그림 캡션 포인터")
    ok("html" in 논["된문"] and "pdf" not in 논["된문"], f"**HTML 에서 수식 얻으면 PDF 안 엶** ({논['된문']})")
    ok(any("arxiv.org/html/2401.00001" in u for u in 열린문) and 열린문[0].endswith("html/2401.00001"),
       "HTML 문을 먼저 열었다")
finally:
    PP.한번 = None
    PP.바이트받기 = None

print("\n== paper: HTML 죽으면 TeX 소스에서 수식·알고리즘 ==")
tex = (r"\begin{equation} \mathcal{L} = \sum_i \ell_i \end{equation}"
       r"\begin{algorithm} 1: for each x do 2: update \theta \end{algorithm}"
       r"\caption{Our pipeline overview}")
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    b = tex.encode("utf-8")
    ti = tarfile.TarInfo("main.tex"); ti.size = len(b)
    t.addfile(ti, io.BytesIO(b))
targz = buf.getvalue()
PP.한번 = lambda u, h, t=25.0: F.응답(url=u, 코드=404, 왜="HTTP 404 없음")       # HTML·abs 다 죽음
PP.바이트받기 = lambda u: targz if "e-print" in u else None                    # PDF 없음, TeX 만
try:
    논 = PP.논문받기("https://arxiv.org/abs/2401.99999")
    ok("\\mathcal{L} = \\sum_i \\ell_i" in 논["수식"], f"**TeX equation 수식** ({논['수식']})")
    ok(any("update" in a for a in 논["알고리즘"]), f"**TeX algorithm 의사코드** ({논['알고리즘']})")
    ok(any("pipeline overview" in g["캡션"] for g in 논["그림"]), "TeX caption 을 그림 포인터로")
    ok("tex" in 논["된문"] and any("html" in x for x in 논["못읽음"]), "TeX 로 열었고 HTML 은 못읽음에 적힌다")
    보 = PP.요지(논)
    ok("## 수식" in 보 and "## 알고리즘" in 보 and "## 못 읽은 것" in 보, "요지에 수식·알고리즘·못읽음")
finally:
    PP.한번 = None
    PP.바이트받기 = None

print("\n== paper: PDF pypdf 없을 때 '못읽음'(≠안전) ==")
ok(PP.pdf텍스트(b"not pdf")[1] == "PDF 가 아니다", "PDF 아니면 까닭")
글, 왜 = PP.pdf텍스트(b"%PDF-1.4\n...")
ok(글 == "" and 왜, f"PDF 지만 pypdf 없거나 깨지면 빈 글이 아니라 까닭 ({왜[:40]})")
PP.한번 = lambda u, h, t=25.0: F.응답(url=u, 코드=404, 왜="404")
PP.바이트받기 = lambda u: (b"%PDF-1.4\nbroken" if "/pdf/" in u else None)
try:
    논 = PP.논문받기("https://arxiv.org/abs/2401.88888", 문들=("pdf",))
    ok(not 논["된문"] and any("pdf" in x for x in 논["못읽음"]), f"PDF 만 있고 못 읽으면 못읽음에 ({논['못읽음']})")
finally:
    PP.한번 = None
    PP.바이트받기 = None

print("\n== 배선 ==")
import subprocess  # noqa: E402
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"dig/**.py"' in _wf, "dig/paper.py 가 배포 경로에 걸린다")
p = subprocess.run(["python3", "dig/paper.py", "--url", "https://arxiv.org/abs/1706.03762", "--문", "abs"],
                   cwd=str(뿌리), capture_output=True, text=True, timeout=60)
ok(p.returncode in (0, 3), f"CLI 가 돈다 (끝값 {p.returncode})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("dig 비언어: 수식뽑기 · MathML/figcaption · arXiv 곁문 · 문 순서 · TeX · PDF 정직 -- 통과")
