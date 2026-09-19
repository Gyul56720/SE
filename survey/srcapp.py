# -*- coding: utf-8 -*-
"""부록: 말뭉치와 벤더 헤더의 전문(verbatim) 수록.

한 줄도 요약하지 않는다.  디스크의 바이트를 그대로 옮긴다 -- 어떤 모델도
이 부록의 내용을 생성하지 않는다.  줄 번호는 파일의 실제 줄 번호다.
"""
import html, json, os, sys

ROOT = "/home/user/hls_study"
OUT  = "/home/user/survey"

# 말뭉치(분석 대상)와 벤더 헤더(그 코드가 의존하는 것)를 가른다.
def 훑기(밑, 벤더):
    난것 = []
    for 뿌리, 디렉, 파일들 in os.walk(밑):
        if "/.git" in 뿌리 or "/synth" in 뿌리:
            continue
        안벤더 = "/vendor" in 뿌리 or 뿌리.rstrip("/").endswith("vendor")
        if 안벤더 != 벤더:
            continue
        for f in sorted(파일들):
            if f.endswith((".h", ".hpp", ".cpp", ".c", ".hh")):
                난것.append(os.path.join(뿌리, f))
    return sorted(난것)

말뭉치 = 훑기(ROOT, False)
헤더   = 훑기(ROOT, True)


def 토막(경로들, 표제, 이름표, 안내):
    """파일 하나를 <pre> 하나로.  줄 번호를 붙이고 HTML 을 이스케이프한다."""
    머리 = (f'<h1 id="{이름표}">{html.escape(표제)}</h1>'
            f'<p>{안내}</p>')
    조각 = []
    총줄 = 0
    for i, p in enumerate(경로들, 1):
        원문 = open(p, encoding="utf-8", errors="replace").read()
        줄들 = 원문.splitlines()
        총줄 += len(줄들)
        상대 = os.path.relpath(p, ROOT)
        조각.append(
            f'<h3 class="srcfile">{이름표}.{i}&nbsp; {html.escape(상대)} '
            f'<span class="srcmeta">({len(줄들):,} lines, '
            f'{os.path.getsize(p):,} B)</span></h3>')
        몸 = "\n".join(
            f'<span class="ln">{n:5d}</span> {html.escape(s)}'
            for n, s in enumerate(줄들, 1))
        조각.append(f'<pre class="src">{몸}</pre>')
    return 머리 + '<div class="srcwrap">' + "\n".join(조각) + "</div>", 총줄, len(경로들)


if __name__ == "__main__":
    한계 = int(sys.argv[1]) if len(sys.argv) > 1 else 0   # 0 = 전부
    말 = 말뭉치[:한계] if 한계 else 말뭉치
    헤 = 헤더[:한계]   if 한계 else 헤더

    d, dl, dn = 토막(
        말, "Appendix D  Complete Corpus Source Listings", "D",
        "Every line of every corpus file, reproduced verbatim from disk. Line numbers "
        "are the real line numbers in the file, so a reference of the form "
        "<code>aes.hpp:317</code> given anywhere in this document can be followed "
        "directly to the line below. Nothing has been elided, reformatted or "
        "summarised; licence headers are reproduced with the code they govern.")
    e, el, en = 토막(
        헤, "Appendix E  Complete Vendor Header Source Listings", "E",
        "The header tree the corpus depends on, reproduced on the same terms. These "
        "files were obtained from the public repositories listed in Table 3 and are "
        "included because no statement in Chapters 3 to 6 about what the corpus "
        "elaborates into can be checked without them.")

    open(f"{OUT}/appendix_src.html", "w", encoding="utf-8").write(d + "\n" + e)
    json.dump({"말뭉치파일": dn, "말뭉치줄": dl, "헤더파일": en, "헤더줄": el,
               "총파일": dn + en, "총줄": dl + el},
              open(f"{OUT}/src_stats.json", "w"), ensure_ascii=False, indent=1)
    print(f"말뭉치 {dn}개 {dl:,}줄 / 헤더 {en}개 {el:,}줄 / 합계 {dn+en}개 {dl+el:,}줄")
    print(f"HTML {os.path.getsize(OUT+'/appendix_src.html'):,} B")
