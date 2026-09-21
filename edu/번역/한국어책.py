# -*- coding: utf-8 -*-
"""옮긴 장들을 한 권으로 묶어 PDF 로 낸다 -- **번역이 끝난 뒤 여기서 돈다.**

    python3 edu/번역/한국어책.py                  # edu/IP_Theory_KR.pdf

## 왜 VM 이 아니라 여기인가

번역은 Gemini 키가 있는 **VM 에서** 돈다.  PDF 는 weasyprint 가 필요한데 그것은
VM 에 없다(`requirements.txt` 에 없고, 판고 같은 시스템 라이브러리까지 딸려온다).
한 번 쓰는 렌더 때문에 봇 VM 에 무거운 의존성을 얹지 않는다.

    VM:   원문 -> 한국어 HTML (키가 거기 있다)
    여기: 한국어 HTML -> PDF  (weasyprint 와 한글 폰트가 여기 있다)

## 빠진 장을 숨기지 않는다

옮기다 만 상태에서도 묶을 수 있어야 한다(쿼터가 끊기면 그렇게 된다).  그때
**표지에 '몇 장 중 몇 장' 을 적는다** -- 반쪽을 통권처럼 내놓지 않는다.
"""
import json
import os
import re
import sys
import time

여기 = os.path.dirname(os.path.abspath(__file__))
뿌리 = os.path.dirname(os.path.dirname(여기))
sys.path.insert(0, os.path.join(뿌리, "edu"))
한국어 = os.path.join(여기, "한국어")
낼곳 = os.path.join(뿌리, "edu", "IP_Theory_KR.pdf")
css = os.path.join(뿌리, "edu", "eduK_style.css")


def 차례만들기(본문):
    it = re.findall(r'<h([12])[^>]*id="([^"]+)"[^>]*>(.*?)</h[12]>', 본문, re.S)
    줄 = []
    for lvl, ident, t in it:
        t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ").strip()
        t = re.sub(r"\s+", " ", t)
        줄.append(f'<div class="toc{lvl}"><a href="#{ident}">{t}</a></div>')
    return '<div class="tocwrap"><h2>차례</h2>' + "\n".join(줄) + "</div>"


def 묶기(이론만=False):
    """`이론만` 이면 대학원 이론서(T 계열)만 센다.

    왜 나누나: `IP_Theory.pdf` 가 T 계열만 묶은 책이므로, 그 한국어판도 같은
    범위여야 표지의 '옮긴 장 N / 전체' 가 **뜻이 맞는다.**  전체 192장을
    분모로 쓰면 이론서를 다 옮기고도 영영 '아직 다 옮기지 않았다' 가 된다.
    """
    import re as _re
    import 원문내기
    차례 = json.load(open(원문내기.차례경로, encoding="utf-8"))["장"] \
        if os.path.exists(원문내기.차례경로) else []
    if 이론만:
        차례 = [c for c in 차례 if _re.fullmatch(r"T\d+_\w+", c["모듈"])]
        차례.sort(key=lambda c: int(_re.match(r"T(\d+)", c["모듈"]).group(1)))
    전체 = len(차례)
    본문, 있는것 = [], 0
    본순서 = []
    for c in 차례:
        키 = c["모듈"].split("_")[0]
        if 키 not in 본순서:
            본순서.append(키)
    for 키 in 본순서:
        p = os.path.join(한국어, f"{키}.html")
        if os.path.exists(p):
            본문.append(open(p, encoding="utf-8").read())
            있는것 += 1
    return "\n".join(본문), 있는것, len(본순서)


def 내기(out=낼곳, 이론만=False):
    본문, 있는것, 전체 = 묶기(이론만)
    if not 본문.strip():
        print(f"옮긴 것이 없다 -- 먼저 `bash scripts/번역돌리기.sh` (VM 에서)."
              f"\n  본 곳: {한국어}", file=sys.stderr)
        return 2
    표지 = (f'<div class="cover"><div class="docno">SE · {time.strftime("%Y-%m-%d")}</div>'
          f'<h1 class="ctitle">IP 설계 이론</h1>'
          f'<div class="csub">'
          + ('혼성신호·디지털 IC 설계 — 대학원 이론서 · 한국어판'
             if 이론만 else '반도체 IP 개발을 위한 이론서 — 한국어판')
          + '</div>'
          f'<div class="cline"></div>'
          f'<div class="cmeta">옮긴 장 {있는것} / {전체}'
          + ("" if 있는것 == 전체 else " · <b>아직 다 옮기지 않았다</b>")
          + "</div></div>")
    문서 = ("<!doctype html><html><head><meta charset='utf-8'>"
          "<title>IP 설계 이론</title></head><body>"
          + 표지 + 차례만들기(본문) + 본문 + "</body></html>")
    from weasyprint import HTML, CSS
    tmp = os.path.join(뿌리, "logs", "한국어책.html")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "w", encoding="utf-8").write(문서)
    t0 = time.time()
    HTML(filename=tmp).write_pdf(out, stylesheets=[CSS(filename=css)])
    print(f"{os.path.basename(out)}: {os.path.getsize(out):,} B · "
          f"장 {있는것}/{전체} · {time.time()-t0:.0f}초")
    return 0


if __name__ == "__main__":
    이론 = "--이론" in sys.argv or "--theory" in sys.argv
    낼 = os.path.join(뿌리, "edu",
                     "IP_Theory_KR.pdf" if 이론 else "IP_KR.pdf")
    sys.exit(내기(낼, 이론만=이론))
