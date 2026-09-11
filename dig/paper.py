"""dig/paper -- 논문(arXiv)을 **읽을 수 있는 글자**로 내린다. 비언어(수식·표·그림·알고리즘) 처리. 도메인 무관.

원칙(사용자와 합의, 2026-09-11): 픽셀은 코드가 검증 못 한다. 그래서 비언어는 **읽을 수 있는
텍스트로 내려서** 잡고, 못 내리는 것은 지어내지 말고 **포인터**로 남긴다.

  · 수식   LaTeX **문자열 그대로** (MathML alttext · TeX 소스 · $$…$$). 렌더링·해석 안 함.
  · 표     HTML 표는 구조로(extract.표로). PDF 표는 못 살린다 -- 그렇다고 적는다.
  · 그림   캡션 + 출처 = `[그림 N: 캡션]`. 픽셀은 안 읽는다.
  · 알고리즘 `algorithm` 환경(TeX)의 의사코드 텍스트 -- codify 가 코드로 바꿀 재료.

어느 문으로 가나 (앞이 안 되면 다음): arXiv HTML(arxiv.org/html) → ar5iv → abs(제목·초록)
→ PDF 텍스트 층(pypdf 있을 때만, 없으면 '못읽음') → TeX 소스(e-print: equation/align/algorithm).
**PDF 만 있으면 수식은 흩어져 사라진다** -- 그래서 HTML/TeX 가 먼저다. 이 도메인은 안 가린다:
물리든 경제든 ML 이든 "논문을 읽을 글자로" 는 같다.

요지(정제): 제목·초록·수식 N개(원문)·알고리즘·그림 캡션·본문 발췌를 한 글로 -- harvest 가
저장·색인하는 '에이전트가 읽기 쉬운 꼴'. 무엇을 못 읽었는지도 같이 적는다.

쓰기:
    python3 dig/paper.py --url https://arxiv.org/abs/2401.00001 [--json]
끝값: 0 뭐라도 읽었다 · 3 한 문도 못 열었다
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import extract as X  # noqa: E402
from dig import fetch as FT  # noqa: E402

_아이디 = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
바이트받기 = None     # 검사 주입: (url) -> bytes|None. 이진(PDF·tar.gz)은 fetch 가 글자로 깨므로 따로
한번 = None          # 검사 주입: fetch.한번 대신
바이트상한 = 8_000_000


def arxiv_id(url: str) -> str:
    if "arxiv" not in (url or "").lower():
        return ""
    m = _아이디.search(url)
    return m.group(1) if m else ""


def 곁문들(url: str) -> "list[tuple[str, str]]":
    """(문 이름, 주소) 순서대로. HTML/TeX 가 먼저 -- PDF 는 수식이 사라진다."""
    id_ = arxiv_id(url)
    if not id_:
        return [("html", url)]
    return [("html", f"https://arxiv.org/html/{id_}"),
            ("ar5iv", f"https://ar5iv.labs.arxiv.org/html/{id_}"),
            ("abs", f"https://arxiv.org/abs/{id_}"),
            ("pdf", f"https://arxiv.org/pdf/{id_}"),
            ("tex", f"https://arxiv.org/e-print/{id_}")]


def _받기(url: str):
    h = {"User-Agent": "SE-dig-paper (research)", "Accept": "text/html,application/xhtml+xml,*/*"}
    return (한번 or FT.한번)(url, h, 25.0)


def _바이트기본(url: str) -> "bytes | None":
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SE-dig-paper"})
        with urllib.request.urlopen(req, timeout=40) as r:          # noqa: S310
            return r.read(바이트상한)
    except Exception:                                              # noqa: BLE001
        return None


def pdf텍스트(raw: bytes) -> "tuple[str, str]":
    """(글, 못읽은까닭). pypdf 가 있을 때만 -- 없으면 '못읽음' 이지 빈 글이 아니다."""
    if not raw or raw[:5] != b"%PDF-":
        return "", "PDF 가 아니다"
    try:
        import pypdf
    except ImportError:
        return "", "PDF 텍스트 층: pypdf 없음 (pip install pypdf)"
    try:
        r = pypdf.PdfReader(io.BytesIO(raw))
        글 = "\n".join((pg.extract_text() or "") for pg in r.pages[:40])
        return 글, "" if 글.strip() else "PDF 텍스트 층이 비었다(스캔본?)"
    except Exception as e:                                         # noqa: BLE001
        return "", f"PDF 못 읽음: {type(e).__name__}"


_tex알고 = re.compile(r"\\begin\{(algorithm|algorithmic)\}(.+?)\\end\{\1\}", re.S)
_tex캡션 = re.compile(r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}")


def tex뽑기(raw: bytes) -> dict:
    """e-print(tar.gz 또는 단일 .tex.gz)에서 수식·알고리즘·캡션을 **원문 그대로**."""
    out = {"수식": [], "알고리즘": [], "캡션": [], "못읽음": ""}
    texs: "list[str]" = []
    try:
        try:
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as t:
                for m in t.getmembers():
                    if m.isfile() and m.name.lower().endswith(".tex") and m.size < 3_000_000:
                        f = t.extractfile(m)
                        if f:
                            texs.append(f.read().decode("utf-8", "replace"))
        except tarfile.ReadError:
            texs.append(gzip.decompress(raw).decode("utf-8", "replace"))
    except Exception as e:                                         # noqa: BLE001
        out["못읽음"] = f"TeX 소스 못 풂: {type(e).__name__}"
        return out
    for tex in texs:
        tex = re.sub(r"(?<!\\)%.*", "", tex)                       # 주석 제거
        out["수식"] += X.수식뽑기(tex)
        out["알고리즘"] += [" ".join(m.group(2).split())[:4000] for m in _tex알고.finditer(tex)]
        out["캡션"] += [" ".join(m.group(1).split()) for m in _tex캡션.finditer(tex)]
    for k in ("수식", "알고리즘", "캡션"):
        out[k] = list(dict.fromkeys(x for x in out[k] if x))[:200]
    if not texs:
        out["못읽음"] = "TeX 소스에 .tex 가 없다"
    return out


def 논문받기(url: str, 문들: "tuple[str, ...]" = ("html", "ar5iv", "abs", "pdf", "tex")) -> dict:
    """한 논문을 읽을 수 있는 글자로. 어느 문이 됐고 무엇을 못 읽었는지 다 적는다."""
    논 = {"id": arxiv_id(url), "url": url, "제목": "", "초록": "", "본문": "", "수식": [], "그림": [],
         "알고리즘": [], "표": [], "된문": [], "못읽음": [],
         "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def 더수식(xs):
        for s in xs:
            if s and s not in 논["수식"]:
                논["수식"].append(s)

    for 문, u in 곁문들(url):
        if 문 not in 문들:
            continue
        if 문 in ("html", "ar5iv", "abs"):
            r = _받기(u)
            if not r.됐나 or ("not found" in r.몸통[:4000].lower() and 문 != "abs"):
                논["못읽음"].append(f"{문}: {r.왜[:60] or 'HTTP ' + str(r.코드)}")
                continue
            e = X.뽑기(r.몸통, r.꼴, u)
            논["된문"].append(문)
            if not 논["제목"]:
                논["제목"] = (e.get("제목") or "").replace("\n", " ").strip()[:300]
            if not 논["초록"]:
                논["초록"] = (e.get("머리표", {}).get("citation_abstract")
                           or e.get("머리표", {}).get("og:description")
                           or e.get("머리표", {}).get("description") or "").strip()[:2000]
            더수식(e.get("수식", []))
            for g in e.get("그림", []):
                if g.get("캡션") and g not in 논["그림"]:
                    논["그림"].append(g)
            논["표"] = 논["표"] or e.get("표", [])
            if 문 in ("html", "ar5iv") and not 논["본문"]:
                논["본문"] = (e.get("글") or "")[:20000]
            if 문 in ("html", "ar5iv") and 논["수식"]:
                break                                              # 깨끗한 HTML 에서 수식까지 얻었으면 충분
        elif 문 == "pdf":
            if 논["본문"]:
                continue                                           # HTML 에서 이미 본문을 얻었다
            raw = (바이트받기 or _바이트기본)(u)
            글, 왜 = pdf텍스트(raw or b"")
            if 글.strip():
                논["된문"].append("pdf")
                논["본문"] = 글[:20000]
                더수식(X.수식뽑기(글))
            elif 왜:
                논["못읽음"].append(f"pdf: {왜}")
        elif 문 == "tex":
            if 논["수식"] and 논["알고리즘"]:
                continue
            raw = (바이트받기 or _바이트기본)(u)
            if not raw:
                continue
            t = tex뽑기(raw)
            if t["못읽음"]:
                논["못읽음"].append(f"tex: {t['못읽음']}")
            if t["수식"] or t["알고리즘"]:
                논["된문"].append("tex")
            더수식(t["수식"])
            for a in t["알고리즘"]:
                if a not in 논["알고리즘"]:
                    논["알고리즘"].append(a)
            for c in t["캡션"]:
                g = {"꼴": "tex캡션", "src": "", "캡션": c}
                if c and g not in 논["그림"]:
                    논["그림"].append(g)
    return 논


def 요지(논: dict, 글상한: int = 4000) -> str:
    """에이전트·harvest 가 읽는 정제된 한 글. 못 읽은 것도 정직히 적는다."""
    줄 = [f"# {논['제목'] or '(제목 못 읽음)'}  <{논['url']}>"]
    if 논["초록"]:
        줄 += ["", "## 초록", 논["초록"][:1500]]
    if 논["수식"]:
        줄 += ["", f"## 수식 {len(논['수식'])}개 (원문 LaTeX)"] + [f"- `{s[:200]}`" for s in 논["수식"][:20]]
    if 논["알고리즘"]:
        줄 += ["", f"## 알고리즘 {len(논['알고리즘'])}개"] + [f"- {a[:400]}" for a in 논["알고리즘"][:5]]
    if 논["그림"]:
        줄 += ["", f"## 그림·캡션 {len(논['그림'])}개 (픽셀 아님, 포인터)"] \
            + [f"- [{g.get('캡션', '')[:160]}] {g.get('src', '')}" for g in 논["그림"][:10]]
    if 논["본문"]:
        줄 += ["", "## 본문 발췌", 논["본문"][:1500]]
    if 논["못읽음"]:
        줄 += ["", "## 못 읽은 것 (안전이 아니라 안 읽은 것)"] + [f"- {x}" for x in 논["못읽음"]]
    return "\n".join(줄)[:글상한 * 4]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="논문을 읽을 수 있는 글자로 내린다 (비언어 포함)")
    ap.add_argument("--url", required=True)
    ap.add_argument("--문", default="html,ar5iv,abs,pdf,tex", help="쉼표로 고른 문만")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    논 = 논문받기(args.url, tuple(x.strip() for x in args.문.split(",") if x.strip()))
    if args.json:
        print(json.dumps(논, ensure_ascii=False, indent=1))
    else:
        print(요지(논))
    return 0 if 논["된문"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
