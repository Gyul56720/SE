# -*- coding: utf-8 -*-
"""교안 골격 -- 표지 · 목차 · 그림 · 표 · 소스부록 · 렌더.

수는 전부 `/home/user/edu/zoo.json` 에서 온다. 손으로 적은 수는 쓰지 않는다.
"""
import html, json, os, re, subprocess, time

E = html.escape
D = "/home/user/edu"
ZOO = {"ip": "/home/user/ipzoo", "model": "/home/user/modelzoo",
       "hls": "/home/user/hls_study"}

_zoo = None
_byrepo = None


def 동물원():
    global _zoo, _byrepo
    if _zoo is None:
        _zoo = json.load(open(f"{D}/zoo.json", encoding="utf-8"))
        _byrepo = json.load(open(f"{D}/zoo_by_repo.json", encoding="utf-8"))
    return _zoo, _byrepo


def 파일찾기(존: str, 부분경로: str):
    """경로에 `부분경로` 가 든 파일 기록을 낸다. 없으면 예외 -- 조용히 넘어가지 않는다."""
    z, _ = 동물원()
    난것 = [f for f in z[존] if 부분경로 in f["경로"]]
    if not 난것:
        raise KeyError(f"{존} 에 '{부분경로}' 가 없다 -- 경로를 확인하라")
    return 난것


def 줄수(존: str, 부분경로: str) -> int:
    return sum(f["줄"] for f in 파일찾기(존, 부분경로))


def 읽기(존: str, 상대경로: str) -> str:
    return open(os.path.join(ZOO[존], 상대경로), encoding="utf-8",
                errors="replace").read()


def 토막(존: str, 상대경로: str, 시작: int, 끝: int, 설명: str = "") -> str:
    """실제 파일의 [시작,끝] 줄을 **줄번호와 함께** 그대로 낸다.

    교안이 인용하는 코드는 전부 이 함수를 지난다. 손으로 옮겨 적지 않는다 --
    옮겨 적으면 원본이 바뀌었을 때 조용히 틀려진다.
    """
    줄들 = 읽기(존, 상대경로).splitlines()
    조각 = 줄들[시작 - 1:끝]
    몸 = "\n".join(f"{시작+i:5d}  {l}" for i, l in enumerate(조각))
    머리 = f'<span class="cap">{E(상대경로)}:{시작}-{끝}'
    if 설명:
        머리 += f"  &mdash; {E(설명)}"
    머리 += "</span>\n"
    return f'<pre class="code">{머리}{E(몸)}</pre>'


_figno = [0]
_tabno = [0]
_FIG = None


def 그림(키, 설명):
    global _FIG
    if _FIG is None:
        _FIG = {}
        for f in ("figs_a.json", "figs_b.json", "figs_c.json"):
            p = f"/home/user/survey/{f}"
            if os.path.exists(p):
                _FIG.update(json.load(open(p)))
    _figno[0] += 1
    본 = _FIG.get(str(키), "")
    return (f'<figure id="fig{_figno[0]}">{본}'
            f'<figcaption><b>그림 {_figno[0]}.</b> {설명}</figcaption></figure>')


def svg그림(svg, 설명):
    _figno[0] += 1
    return (f'<figure id="fig{_figno[0]}">{svg}'
            f'<figcaption><b>그림 {_figno[0]}.</b> {설명}</figcaption></figure>')


def 표(설명, 머리, 행들):
    _tabno[0] += 1
    h = "".join(f"<th>{c}</th>" for c in 머리)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in 행들)
    return (f'<table><caption>표 {_tabno[0]}. {설명}</caption>'
            f'<thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>')


def 소스부록(항목들, 이름표="A", 표제="부록 A  수록 소스 전문", 안내=""):
    """(존, 상대경로) 목록을 전문 그대로 싣는다. 줄번호는 파일의 실제 줄번호다."""
    조각 = [f'<h1 class="srcapp" id="{이름표}">{E(표제)}</h1>']
    if 안내:
        조각.append(f"<p>{안내}</p>")
    조각.append('<div class="srcwrap">')
    총 = 0
    for i, (존, rel) in enumerate(항목들, 1):
        t = 읽기(존, rel)
        줄들 = t.splitlines()
        총 += len(줄들)
        조각.append(f'<h3 class="srcfile">{이름표}.{i}&nbsp; {E(rel)} '
                    f'<span class="srcmeta">({len(줄들):,}줄, {len(t):,}B)</span></h3>')
        몸 = "\n".join(f'<span class="ln">{n:5d}</span> {E(s)}'
                       for n, s in enumerate(줄들, 1))
        조각.append(f'<pre class="src">{몸}</pre>')
    조각.append("</div>")
    return "\n".join(조각), 총


def 목차(본문):
    항 = re.findall(r'<h([12])[^>]*id="([^"]+)"[^>]*>(.*?)</h[12]>', 본문, re.S)
    줄 = []
    for 급, ident, 글 in 항:
        글 = re.sub(r"<[^>]+>", "", 글).replace("&nbsp;", " ").strip()
        글 = re.sub(r"\s+", " ", 글)
        줄.append(f'<div class="toc{급}"><a href="#{ident}">{글}</a></div>')
    return ('<div class="tocwrap"><h2 style="break-before:auto">차례</h2>'
            + "\n".join(줄) + "</div>")


def 표지(번호, 제목, 부제, 본문설명):
    return f"""<div class="cover">
  <div class="docno">{E(번호)} &nbsp;&bull;&nbsp; {time.strftime('%Y-%m-%d')}</div>
  <h1 class="ctitle">{E(제목)}</h1>
  <div class="csub">{E(부제)}</div>
  <div class="cline"></div>
  <div class="cmeta">{본문설명}</div>
</div>"""


def 렌더(html본문, 낼파일, css="/home/user/SE/edu/edu_style.css"):
    from weasyprint import HTML, CSS
    임시 = f"{D}/{os.path.basename(낼파일)}.html"
    open(임시, "w", encoding="utf-8").write(html본문)
    t0 = time.time()
    HTML(filename=임시).write_pdf(낼파일, stylesheets=[CSS(filename=css)])
    걸림 = time.time() - t0
    쪽 = subprocess.run(["pdfinfo", 낼파일], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", 쪽)
    print(f"{os.path.basename(낼파일)}: {m.group(1) if m else '?'}쪽, "
          f"{os.path.getsize(낼파일):,}B, 렌더 {걸림:.0f}s")
    return int(m.group(1)) if m else 0
