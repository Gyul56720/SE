"""조문 원장을 **받아서** 채운다 -- 지어내지 않는다.

`law/corpus/README.md` 가 "LLM 이 기억으로 적어준 조문을 여기 넣지 마라" 고 적은 그 자리를
사람 손 대신 API 로 채우는 파일이다. 원장은 심판이 대조하는 정답 자리라, 여기가 틀리면
심판이 틀린 것을 기준으로 멀쩡한 문서를 기각하고 틀린 문서를 통과시킨다.

출처는 법제처 **국가법령정보 공동활용**(open.law.go.kr) OPEN API 다. 인증키(OC)는 무료이고
한 번만 발급받으면 된다: 로그인 -> 왼쪽 메뉴 'OPEN API 신청' -> 'API인증키관리' 에서
현재 API인증키(OC) 를 복사해 `.env` 의 `LAW_API_OC` 에 넣는다.

    python3 law/fetch.py 형법 민법            # 받아서 law/corpus/ 에 저장
    python3 law/fetch.py 형법 --list          # 검색 결과만 본다 (무엇을 받을지 고르기)
    python3 law/fetch.py 형법 --dry           # 받아서 요약만, 파일은 안 쓴다

## 두 걸음으로 받는 이유

법령명으로 곧바로 본문을 부르지 않고 **검색 -> 일련번호 -> 본문** 순으로 간다.
'형법' 을 검색하면 군형법 · 형법 시행령 같은 것이 같이 나오기 때문이다. 이름이 정확히
같은 것만 골라서 그 일련번호로 본문을 받는다. 자동으로 고른 것이 미덥지 않으면
`--list` 로 먼저 보고 `--mst` 로 직접 지정한다.

## 받은 것을 그대로 믿지 않는다

- 조문 머리(`제N조`)가 하나도 없으면 **저장하지 않는다.** 로그인 페이지나 오류 XML 을
  원장에 넣으면 심판이 그것을 정답으로 삼는다.
- 저장한 뒤 `law/corpus.py` 로 다시 읽어 **조문 몇 개가 실제로 잡히는지** 보고한다.
  받는 것과 파싱되는 것은 다른 일이다.
- 파일 첫 줄에 법령명 · 시행일자 · 받은 날짜를 적는다. 조문은 개정되므로 **언제 받은
  것인지 모르는 원장은 못 쓴다.** (`#` 로 시작하는 줄은 파서가 버린다.)

## 인증키는 절대 찍지 않는다

OC 는 자격증명이다. URL 에는 들어가지만 로그·오류 메시지에는 가려서만 나간다(G004 가
막는 그 사고가 정확히 "토큰을 찾아 출력했다" 였다).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402

SEARCH = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE = "https://www.law.go.kr/DRF/lawService.do"

TIMEOUT = int(os.environ.get("LAW_API_TIMEOUT", "30"))
TRIES = int(os.environ.get("LAW_API_TRIES", "4"))

# **호출 사이에 쉰다.** 신청 화면의 주의사항 1번이 이것이다 -- "짧은 시간 내 과도한
# 호출이 발생할 경우 비정상적인 접근으로 간주되어 이용이 제한될 수 있습니다."
# 법령 몇 개를 받을 때는 문제가 안 되지만 판례를 훑기 시작하면 곧바로 걸린다.
# 제한을 당하면 원장이 못 차고, 원장이 안 차면 관문이 아무것도 못 본다.
SLEEP = float(os.environ.get("LAW_API_SLEEP", "0.5"))
_last = [0.0]

# **분당 한도가 따로 있다.** 0.5초 간격은 순간 간격만 묶을 뿐이라 그대로 두면 분당
# 120회가 나간다. 판례는 검색 1회 + 본문 N회를 몰아 부르므로(`--건수 20` 이면 21회)
# 몇 주제만 돌려도 곧바로 걸린다. 그래서 **구르는 1분 창**으로 센다.
# 창이 안 찼으면 안 쉰다 -- 평소에는 SLEEP 만 걸리고, 찼을 때만 창이 빌 때까지 기다린다.
RPM = int(os.environ.get("LAW_API_RPM", "20"))
_window: list = []

# 제한에 걸렸을 때 되풀이하면 **더 세게 두드리는 것**이다. 네트워크 실패는 되풀이하고
# 제한은 즉시 멈춘다. 둘을 섞으면 1분이면 풀릴 것을 한참 동안 못 쓰게 만든다.
# (실측한 응답 꼴이 아니다 -- 429·403 과 본문의 제한 문구로 보수적으로 본다.)
_THROTTLE = re.compile(r"과도한\s*호출|비정상적인\s*접근|이용이\s*제한|요청\s*제한|too\s*many")


class Throttled(RuntimeError):
    """호출 제한에 걸렸다. 되풀이하지 않고 멈춘다."""


def _wait_turn() -> None:
    now = time.monotonic()
    _window[:] = [t for t in _window if now - t < 60]
    if len(_window) >= RPM:
        time.sleep(max(0.0, 60 - (now - _window[0])) + 0.1)
        now = time.monotonic()
        _window[:] = [t for t in _window if now - t < 60]
    gap = SLEEP - (now - _last[0])
    if gap > 0:
        time.sleep(gap)
    _last[0] = time.monotonic()
    _window.append(_last[0])

# 조문 본문이 들어 있는 칸. 스키마가 조금 달라져도 견디게 **끝소리로** 고른다.
TEXT_TAGS = ("조문내용", "항내용", "호내용", "목내용")
# 조문단위 안에서 이 값이 '조문' 이 아니면 편·장·절 제목이다.
KIND_TAG = "조문여부"

_HEAD = re.compile(r"^\s*제\s*\d+\s*조", re.M)
_WS = re.compile(r"[ \t]+")


def mask(oc: str) -> str:
    """인증키를 로그에 그대로 두지 않는다. 앞 두 글자만 남긴다."""
    return (oc[:2] + "*" * max(0, len(oc) - 2)) if oc else "(없음)"


def _url(base: str, oc: str, **params) -> str:
    q = {"OC": oc, "type": "XML"}
    q.update({k: v for k, v in params.items() if v not in (None, "")})
    return base + "?" + urllib.parse.urlencode(q, encoding="utf-8")


def _get(url: str, oc: str = "") -> str:
    """받아온다. 네트워크 실패만 되풀이한다(2·4·8·16초).

    실패 메시지에 URL 을 그대로 싣지 않는다 -- 거기에 인증키가 들어 있다.
    """
    last = None
    for i in range(TRIES):
        _wait_turn()
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                body = r.read().decode("utf-8", "replace")
            if _THROTTLE.search(body[:2000]):
                raise Throttled("호출 제한에 걸렸다 (응답 본문이 그렇게 말한다)")
            return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 403):
                raise Throttled(f"호출 제한에 걸렸다 (HTTP {e.code})") from None
            last = e
            if i < TRIES - 1:
                time.sleep(2 ** (i + 1))
        except (urllib.error.URLError, OSError) as e:
            last = e
            if i < TRIES - 1:
                time.sleep(2 ** (i + 1))
    where = url.split("?")[0]
    raise RuntimeError(f"{where} 에서 못 받았다 (OC {mask(oc)}): {last}")


def _text(el) -> str:
    return (el.text or "").strip()


def _first(node, *names):
    """끝소리가 맞는 첫 칸의 값. 스키마 이름이 조금 달라도 잡으려고 이렇게 한다."""
    for el in node.iter():
        tag = el.tag.split("}")[-1]
        if any(tag.endswith(n) or n in tag for n in names) and _text(el):
            return _text(el)
    return ""


def parse_search(xml: str) -> list:
    """검색 결과 -> [{이름, 일련번호, 시행일자, 구분}]."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"검색 응답이 XML 이 아니다: {e}") from None
    out = []
    for law in root.iter():
        tag = law.tag.split("}")[-1]
        if tag not in ("law", "Law", "법령"):
            continue
        name = _first(law, "법령명한글", "법령명_한글", "법령명")
        if not name:
            continue
        out.append({
            "이름": _WS.sub(" ", name).strip(),
            "일련번호": _first(law, "법령일련번호", "법령마스터번호", "MST"),
            "ID": _first(law, "법령ID", "법령id"),
            "시행일자": _first(law, "시행일자"),
            "구분": _first(law, "법령구분명"),
        })
    return out


def pick(rows: list, name: str):
    """**이름이 정확히 같은 것만 고른다.** '형법' 검색에 군형법·형법 시행령이 같이 온다.

    같은 이름이 여럿이면 시행일자가 늦은 것(=최신 시행)을 고른다.
    """
    same = [r for r in rows if r["이름"].replace(" ", "") == name.replace(" ", "")]
    if not same:
        return None
    return sorted(same, key=lambda r: r.get("시행일자") or "", reverse=True)[0]


def parse_law(xml: str) -> tuple:
    """법령 본문 XML -> (메타, 조문 원문 텍스트).

    조문내용 · 항내용 · 호내용을 문서 순서대로 잇는다. 스키마를 못 알아보면 **모든 칸의
    글을 순서대로 잇는 것으로 물러선다** -- 그래도 `제N조` 가 없으면 위에서 저장을 막는다.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"본문 응답이 XML 이 아니다: {e}") from None

    meta = {
        "이름": _first(root, "법령명한글", "법령명_한글", "법령명"),
        "시행일자": _first(root, "시행일자"),
        "공포일자": _first(root, "공포일자"),
    }

    lines, seen = [], set()

    def push(s: str):
        s = _WS.sub(" ", s).strip()
        if not s or s in seen:
            return
        seen.add(s)
        lines.append(s)

    units = [el for el in root.iter() if el.tag.split("}")[-1].endswith("조문단위")]
    if units:
        for u in units:
            kind = _first(u, KIND_TAG)
            if kind and kind != "조문":          # 편·장·절 제목은 조문이 아니다
                continue
            for el in u.iter():
                tag = el.tag.split("}")[-1]
                if any(tag.endswith(t) for t in TEXT_TAGS):
                    push(_text(el))
    else:
        for el in root.iter():                    # 스키마를 못 알아봤다 -- 다 이어 붙인다
            push(_text(el))
    return meta, "\n".join(lines)


# 판례 본문에서 글을 담고 있는 칸. 조문과 같은 이유로 **끝소리로** 고른다.
PREC_TAGS = ("판시사항", "판결요지", "참조조문", "참조판례", "판례내용")


def parse_prec_search(xml: str) -> list:
    """판례 목록 XML -> [{사건번호, 사건명, 법원명, 선고일자, 일련번호, 사건종류명}]."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"판례 검색 응답이 XML 이 아니다: {e}") from None
    out = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in ("prec", "Prec", "판례"):
            continue
        no = _first(node, "사건번호")
        if not no:
            continue
        out.append({
            "사건번호": _WS.sub(" ", no).strip(),
            "사건명": _first(node, "사건명"),
            "법원명": _first(node, "법원명"),
            "선고일자": _first(node, "선고일자"),
            "일련번호": _first(node, "판례일련번호"),
            "사건종류명": _first(node, "사건종류명"),
        })
    return out


def parse_prec(xml: str) -> tuple:
    """판례 본문 XML -> (메타, 원문 텍스트).

    조문과 달리 **본문이 없어도 메타만으로 쓸모가 있다.** L004 가 먼저 묻는 것은
    "이 사건번호가 실재하는가" 이고, 그건 사건번호·법원·선고일자로 답해진다.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"판례 본문 응답이 XML 이 아니다: {e}") from None
    meta = {
        "사건번호": _WS.sub(" ", _first(root, "사건번호")).strip(),
        "사건명": _first(root, "사건명"),
        "법원명": _first(root, "법원명"),
        "선고일자": _first(root, "선고일자"),
        "일련번호": _first(root, "판례일련번호"),
    }
    parts = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if any(tag.endswith(n) for n in PREC_TAGS) and _text(el):
            parts.append(f"[{tag}]\n{_text(el)}")
    return meta, "\n\n".join(parts)


def prec_header(meta: dict) -> str:
    """첫 줄이 곧 원장의 색인이다 -- `corpus.load_cases()` 가 이 줄만 읽는다."""
    got = time.strftime("%Y-%m-%d")
    return (f"# {meta.get('사건번호')} · {meta.get('법원명') or '법원 미상'}"
            f" · {meta.get('선고일자') or '선고일자 미상'}"
            f" · {meta.get('사건명') or '사건명 미상'}\n"
            f"# 법제처 국가법령정보 공동활용 OPEN API · 받은 날 {got}\n"
            f"# 이 파일은 받은 것이다. 손으로 고치지 마라 -- 고치려면 다시 받아라.\n")


def pull_prec(query: str, oc: str, root: Path, fetcher=None, sid: str = "",
              dry: bool = False, display: str = "20") -> list:
    """판례를 받아 저장한다. 검색어는 사건번호여도 되고 사건명이어도 된다.

    **사건번호가 안 실린 것은 저장하지 않는다.** 첫 줄이 원장의 색인이라, 사건번호가
    없으면 그 파일은 원장에 안 잡히고 있으나 마나가 된다. 조문 쪽에서 `제N조` 가
    하나도 없으면 저장을 막는 것과 같은 이유다 -- 원장에 쓰레기가 들어가면 심판이
    그것을 정답으로 삼는다.
    """
    get = fetcher or _get
    if sid:
        rows = [{"일련번호": sid, "사건번호": "", "사건명": "", "법원명": "", "선고일자": ""}]
    else:
        rows = parse_prec_search(get(_url(SEARCH, oc, target="prec", query=query,
                                          display=display), oc))
    # **이어한다.** 목록에 사건번호가 이미 실려 오므로, 원장에 있는 것은 본문 호출을
    # 아예 안 한다. 분당 한도가 있는 곳에서 이것이 제일 크게 아끼는 자리다 --
    # 제한에 걸려 중간에 끊겨도 다시 부르면 안 받은 것부터 이어간다.
    있는것 = CP.load_cases(root) if not sid else {}
    out = []
    for r in rows:
        ident = r.get("일련번호")
        if not ident:
            continue
        이미 = CP.normalize_case(r.get("사건번호", ""))
        if 이미 and 이미 in 있는것:
            out.append({"사건번호": r["사건번호"], "법원명": r.get("법원명", ""),
                        "선고일자": r.get("선고일자", ""), "글자": 0,
                        "저장": 있는것[이미]["파일"], "이미": True})
            continue
        meta, text = parse_prec(get(_url(SERVICE, oc, target="prec", ID=ident), oc))
        # **목록과 본문이 다른 사건을 가리키면 저장하지 않는다.** 둘 중 하나를 골라
        # 담으면 다른 사건의 판시사항이 그 사건번호로 원장에 앉는다 -- 심판이 대조하는
        # 자리라 그건 조용한 오답이 된다. 어긋난 것은 담지 말고 사람에게 말한다.
        본문no, 목록no = CP.normalize_case(meta.get("사건번호", "")), 이미
        if 본문no and 목록no and 본문no != 목록no:
            out.append({"사건번호": r.get("사건번호", ""), "법원명": r.get("법원명", ""),
                        "선고일자": r.get("선고일자", ""), "글자": len(text), "저장": None,
                        "실패": f"목록은 {r['사건번호']} 인데 본문은 {meta['사건번호']} 다"
                                f" -- 어느 쪽이 맞는지 모르므로 원장에 넣지 않는다"})
            continue
        meta = {k: (meta.get(k) or r.get(k) or "") for k in
                ("사건번호", "사건명", "법원명", "선고일자", "일련번호")}
        got = {"사건번호": meta["사건번호"], "법원명": meta["법원명"],
               "선고일자": meta["선고일자"], "글자": len(text), "저장": None}
        if not meta["사건번호"]:
            got["실패"] = "사건번호가 없다 -- 원장에 넣지 않는다"
            out.append(got)
            continue
        if not dry:
            root.mkdir(parents=True, exist_ok=True)
            path = root / f"{CP.normalize_case(meta['사건번호'])}.txt"
            path.write_text(prec_header(meta) + "\n" + text.rstrip() + "\n",
                            encoding="utf-8")
            got["저장"] = str(path)
        out.append(got)
    return out


def header(meta: dict, name: str) -> str:
    """파일 첫 줄. 파서가 버리는 자리이지만 **사람이 볼 때 제일 중요한 줄**이다."""
    got = time.strftime("%Y-%m-%d")
    eff = meta.get("시행일자") or "시행일자 미상"
    return (f"# {meta.get('이름') or name} (시행 {eff}) "
            f"· 법제처 국가법령정보 공동활용 OPEN API · 받은 날 {got}\n"
            f"# 이 파일은 받은 것이다. 손으로 고치지 마라 -- 고치려면 다시 받아라.\n")


def save(name: str, meta: dict, text: str, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{meta.get('이름') or name}.txt"
    path.write_text(header(meta, name) + "\n" + text.rstrip() + "\n", encoding="utf-8")
    return path


def pull(name: str, oc: str, root: Path, fetcher=None, mst: str = "",
         dry: bool = False) -> dict:
    """한 법령을 받아 저장한다. (검색 -> 고르기 -> 본문 -> 검사 -> 저장)"""
    get = fetcher or _get
    chosen = None
    if not mst:
        rows = parse_search(get(_url(SEARCH, oc, target="law", query=name,
                                     display="50"), oc))
        chosen = pick(rows, name)
        if not chosen:
            near = ", ".join(r["이름"] for r in rows[:5]) or "(결과 없음)"
            raise RuntimeError(f"{name!r} 과 이름이 정확히 같은 법령이 없다. 가까운 것: {near}")
        mst = chosen["일련번호"] or chosen["ID"]
        if not mst:
            raise RuntimeError(f"{name}: 검색 결과에 일련번호가 없다")

    key = "MST" if (chosen or {}).get("일련번호") or mst.isdigit() else "ID"
    meta, text = parse_law(get(_url(SERVICE, oc, target="law", **{key: mst}), oc))

    heads = len(_HEAD.findall(text))
    if heads == 0:
        raise RuntimeError(
            f"{name}: 받은 것에 조문 머리(제N조)가 하나도 없다 -- 원장에 넣지 않는다 "
            f"(길이 {len(text)}자)")

    out = {"이름": meta.get("이름") or name, "시행일자": meta.get("시행일자"),
           "조문머리": heads, "글자": len(text), "MST": mst, "저장": None, "담긴조문": 0}
    if dry:
        return out

    path = save(name, meta, text, root)
    # **받는 것과 파싱되는 것은 다른 일이다.** 저장한 뒤 원장으로 다시 읽어 확인한다.
    got = CP.load(root)
    out["저장"] = str(path)
    out["담긴조문"] = len(got.articles.get(CP.normalize_statute(out["이름"]), {}))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="조문 원장을 법제처 API 로 채운다")
    ap.add_argument("names", nargs="+", help="법령명 (예: 형법 민법). --판례 면 검색어/사건번호")
    ap.add_argument("--판례", dest="prec", action="store_true",
                    help="법령이 아니라 판례를 받는다 (law/precedents/ 에 저장)")
    ap.add_argument("--건수", dest="display", default="20",
                    help="--판례 일 때 한 검색어에서 받을 건수 (기본 20)")
    ap.add_argument("--oc", default=os.environ.get("LAW_API_OC", ""),
                    help="인증키. 없으면 환경변수 LAW_API_OC")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--cases", default=str(CP.CASES_DIR), help="판례 원장 자리")
    ap.add_argument("--mst", default="", help="일련번호를 직접 지정(법령 하나일 때)")
    ap.add_argument("--list", action="store_true", help="검색 결과만 본다")
    ap.add_argument("--dry", action="store_true", help="받되 파일은 안 쓴다")
    a = ap.parse_args(argv)

    if not a.oc:
        print("인증키가 없다. open.law.go.kr 에서 OPEN API 를 신청하고 발급받은 "
              "API인증키(OC)를 .env 의 LAW_API_OC 에 넣어라.", file=sys.stderr)
        return 2
    print(f"인증키 {mask(a.oc)} · 원장 {a.corpus}")

    root = Path(a.corpus)
    bad = 0

    if a.prec:
        croot = Path(a.cases)
        print(f"판례 원장 {croot}")
        for q in a.names:
            try:
                if a.list:
                    rows = parse_prec_search(_get(_url(SEARCH, a.oc, target="prec",
                                                       query=q, display=a.display), a.oc))
                    print(f"\n[{q}] 검색 {len(rows)}건")
                    for r in rows[:20]:
                        print(f"  {r['사건번호']} · {r['법원명']} · {r['선고일자']}"
                              f" · {r['사건명'][:40]}")
                    continue
                got = pull_prec(q, a.oc, croot, dry=a.dry, display=a.display)
                새로 = sum(1 for r in got if not r.get("이미") and not r.get("실패"))
                print(f"\n[{q}] {len(got)}건 (새로 받은 것 {새로})")
                for r in got:
                    if r.get("실패"):
                        print(f"  (건너뜀) {r['실패']}")
                        continue
                    if r.get("이미"):
                        print(f"  {r['사건번호']} · 원장에 이미 있다 -- 안 불렀다")
                        continue
                    print(f"  {r['사건번호']} · {r['법원명']} · {r['선고일자']}"
                          f" · {r['글자']}자  {r['저장'] or '(dry)'}")
            except Throttled as e:
                # **여기서 멈춘다.** 되풀이하면 더 세게 두드리는 것이다. 받은 것은
                # 이미 저장돼 있으므로, 잠시 뒤 같은 명령을 다시 부르면 이어간다.
                print(f"\n[{q}] {e}\n  받은 것은 원장에 남아 있다. "
                      f"잠시 뒤 같은 명령을 다시 부르면 안 받은 것부터 이어간다.\n"
                      f"  (분당 한도는 LAW_API_RPM 으로 낮출 수 있다 -- 지금 {RPM})",
                      file=sys.stderr)
                bad += 1
                break
            except Exception as e:                  # noqa: BLE001  사람에게 보여줄 것
                bad += 1
                print(f"\n[{q}] 실패: {e}", file=sys.stderr)
        if not a.list and not a.dry:
            사건 = CP.load_cases(croot)
            print(f"\n판례 원장으로 다시 읽으니 {len(사건)}건이 잡힌다")
            print("다음: python3 law/gate.py 법이론서   # L004 가 금지에서 대조로 바뀐다")
        return 1 if bad else 0

    for name in a.names:
        try:
            if a.list:
                rows = parse_search(_get(_url(SEARCH, a.oc, target="law", query=name,
                                              display="50"), a.oc))
                print(f"\n[{name}] 검색 {len(rows)}건")
                for r in rows[:20]:
                    star = " <-- 이름이 같다" if r["이름"].replace(" ", "") == \
                        name.replace(" ", "") else ""
                    print(f"  {r['이름']} · {r['구분']} · 시행 {r['시행일자']} "
                          f"· 일련번호 {r['일련번호'] or r['ID']}{star}")
                continue
            r = pull(name, a.oc, root, mst=a.mst if len(a.names) == 1 else "",
                     dry=a.dry)
            where = r["저장"] or "(저장 안 함 -- dry)"
            print(f"\n[{r['이름']}] 시행 {r['시행일자']} · 조문머리 {r['조문머리']}개 "
                  f"· {r['글자']}자\n  {where}")
            if r["저장"]:
                print(f"  원장으로 다시 읽으니 조문 {r['담긴조문']}개가 잡힌다")
                if r["담긴조문"] < r["조문머리"] * 0.9:
                    print("  (받은 조문 머리 수보다 적게 잡혔다 -- 파싱을 확인할 것)")
        except Exception as e:                      # noqa: BLE001  사람에게 보여줄 것
            bad += 1
            print(f"\n[{name}] 실패: {e}", file=sys.stderr)

    if not a.list and not a.dry:
        print("\n다음: python3 law/gate.py 법이론서   # 미검증이 얼마나 줄었는지 본다")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
