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
import json
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

ROOT = Path(__file__).resolve().parent.parent

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


def oc_from_env() -> str:
    """인증키. **`.env` 도 여기서 읽는다.**

    실측(같은 병을 두 번 앓았다): `law/ocr.py` 가 이름 목록만 `llm_pool` 과 맞춰 놓고
    `.env` 를 안 읽어서, 키가 `.env` 에 멀쩡히 있는데 "키가 없다" 고 답했다.
    이 파일도 같았다 -- docstring 은 ".env 의 LAW_API_OC 에 넣어라" 라고 안내하면서
    정작 `os.environ` 만 봤다. systemd 는 EnvironmentFile 로 받지만 SSH 셸은 안 받는다.

    읽는 자리를 새로 만들지 않고 `llm_pool._load_dotenv_once()` 를 부른다.
    **두 벌은 언젠가 갈라진다** -- 그 한 벌이 이미 있다.
    """
    if os.environ.get("LAW_API_OC"):
        return os.environ["LAW_API_OC"]
    try:
        sys.path.insert(0, str(ROOT / "orchestrator"))
        import llm_pool
        llm_pool._load_dotenv_once()
    except Exception:                            # noqa: BLE001  키 못 읽는 것이 죽을 일은 아니다
        pass
    return os.environ.get("LAW_API_OC", "")


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


NAME_TAGS = ("법령명한글", "법령명_한글", "법령명")
ROW_TAGS = ("law", "Law", "법령")


def _rows_of(root) -> list:
    """검색 결과에서 '한 법령' 에 해당하는 원소들.

    **이름으로 먼저 찾고, 못 찾으면 꼴로 찾는다.** target 마다 원소 이름이 다를 수
    있는데, 이름 목록이 틀리면 `parse_search` 가 0행을 주고 `history` 는 그것을
    "판이 없다" 로 읽는다. 그러면 **"이 법은 판이 하나뿐" 이라는 거짓 결론이 조용히
    남는다** -- 자를 먼저 의심하라. 그래서 이름이 안 맞으면 법령명을 **직속 자식으로**
    가진 원소를 행으로 본다. 직속으로 한정하는 이유: `iter()` 로 훑으면 뿌리
    <LawSearch> 자신도 법령명을 후손으로 가지므로 행이 하나 더 생긴다.
    """
    named = [el for el in root.iter() if el.tag.split("}")[-1] in ROW_TAGS]
    if named:
        return named
    out = []
    for el in root.iter():
        kids = {c.tag.split("}")[-1] for c in el}
        if any(n in kids for n in NAME_TAGS):
            out.append(el)
    return out


def parse_search(xml: str) -> list:
    """검색 결과 -> [{이름, 일련번호, 시행일자, 구분}]."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RuntimeError(f"검색 응답이 XML 이 아니다: {e}") from None
    out = []
    for law in _rows_of(root):
        name = _first(law, *NAME_TAGS)
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


# 시행일별 판을 어느 이름으로 부르는지 **실측하지 않았다.** 그래서 후보를 차례로
# 두드려 보고 **여러 판이 실제로 오는 것**을 쓴다. 기억으로 하나를 적어 두면, 그것이
# 틀렸을 때 "판이 하나뿐" 이라는 거짓 결론이 조용히 남는다 -- 이 저장소가 오늘만
# 두 번 앓은 병이다(ocr.py 의 키 이름, fetch.py 의 .env).
HISTORY_TARGETS = ("eflaw", "law")


def history(name: str, oc: str, fetcher=None, display: str = "100") -> tuple:
    """이 법령의 **시행일별 판 목록**. (행, 어느 target 이 줬나).

    판이 하나뿐이면 그 API 가 현행만 준다는 뜻이다 -- 그때는 행위시법을 못 한다고
    **말해야 한다.** 조용히 최신으로 돌아가면 옛 사건을 새 법으로 재게 된다.
    """
    get = fetcher or _get
    best, where = [], ""
    for tgt in HISTORY_TARGETS:
        try:
            rows = parse_search(get(_url(SEARCH, oc, target=tgt, query=name,
                                         display=display), oc))
        except Exception:                       # noqa: BLE001  다음 후보를 두드린다
            continue
        같 = [r for r in rows if r["이름"].replace(" ", "") == name.replace(" ", "")]
        판 = {_daykey(r.get("시행일자", "")) for r in 같} - {""}
        if len(판) > len({_daykey(r.get("시행일자", "")) for r in best} - {""}):
            best, where = 같, tgt
        if len(판) > 1:
            break
    return best, where


def pick_at(rows: list, name: str, when: str):
    """**그날 시행 중이던 판.** 시행일자가 `when` **이하인 것 중 가장 늦은 것**.

    행위시법이 이 함수의 존재 이유다. 법은 개정되고 재판은 행위 당시의 법으로 한다
    (형법 제1조 제1항 "행위 시의 법률에 의한다"; 민사는 법률불소급 + 부칙 경과규정).
    지금 원장은 `pick()` 이 늘 최신을 골라 **현행법만** 담는다. 2018년 확약을 2026년
    민법으로 재는 셈이다.

    판례 대조에서는 더 크게 어긋난다. 2015년 판결은 2015년 법을 적용한 것이라,
    현행 조문과 대 보면 **옛 판결이 전부 틀린 것처럼** 나온다. 판례 원장을 채우기
    전에 이것을 고쳐야 하는 이유다 -- 안 그러면 채우자마자 헛돈다.

    **못 고르면 None 이다.** 그날보다 늦은 판밖에 없으면 그때 시행 중이던 법을 우리가
    안 가진 것이고, 아무거나 골라 대조하면 틀린 법으로 멀쩡한 글을 기각한다.
    """
    key = _daykey(when)
    same = [r for r in rows if r["이름"].replace(" ", "") == name.replace(" ", "")]
    쓸것 = [r for r in same if r.get("시행일자") and _daykey(r["시행일자"]) <= key]
    if not 쓸것:
        return None
    return sorted(쓸것, key=lambda r: _daykey(r["시행일자"]))[-1]


def _daykey(s: str) -> str:
    """`2019-02-15` · `20190215` · `2019. 2. 15.` 를 한 꼴(`20190215`)로.

    **월·일이 한 자리인 꼴을 따로 다룬다.** 숫자만 뽑아 붙이면 `2019.2.15` 가
    `2019215`(7자)가 되어 못 읽는 것으로 떨어진다 -- 판결문과 법령 공고가 늘 쓰는
    꼴이 그것이다. 못 읽으면 빈 문자열이고, 빈 것은 비교에서 빠진다.
    """
    g = re.findall(r"\d+", s or "")
    if len(g) >= 3 and len(g[0]) == 4:
        return f"{g[0]}{int(g[1]):02d}{int(g[2]):02d}"
    d = "".join(g)
    return d[:8] if len(d) >= 8 else ""


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


def prec_total(xml: str) -> int:
    """검색이 말한 **총 건수.** 전부 긁기 전에 규모부터 알아야 한다 -- 분당 한도가
    있는 곳에서 며칠짜리 일인지 몇 분짜리 일인지는 이 수로 갈린다."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return 0
    for el in root.iter():
        if el.tag.split("}")[-1] in ("totalCnt", "총건수") and (el.text or "").strip().isdigit():
            return int(el.text.strip())
    return 0


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


PROGRESS_FILE = "_훑던자리.json"


def _훑기키(query: str, params: dict | None) -> str:
    """어느 훑기인지 가리키는 이름. 검색어가 같아도 **거르개가 다르면 다른 훑기다.**"""
    꼬리 = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return f"{query}|{꼬리}" if 꼬리 else query


def 훑던자리(root: Path) -> dict:
    """어디까지 훑었는가. 없으면 빈 것."""
    p = Path(root) / PROGRESS_FILE
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}                    # 못 읽으면 처음부터. **거짓 진행을 만들지 않는다**


def _자리적기(root: Path, 키: str, 쪽: int, 총: int, 받음: int) -> None:
    자리 = 훑던자리(root)
    자리[키] = {"마지막쪽": 쪽, "총건수": 총, "받음": 받음,
                "때": time.strftime("%Y-%m-%d %H:%M:%S")}
    (Path(root) / PROGRESS_FILE).write_text(
        json.dumps(자리, ensure_ascii=False, indent=2), encoding="utf-8")


def sweep_prec(query: str, oc: str, root: Path, fetcher=None, display: str = "100",
               start: int = 1, pages: int = 0, dry: bool = False,
               params: dict | None = None, 이어: bool = False):
    """**목록을 쪽 단위로 훑는다.** 한 쪽 받고 그 쪽을 다 받은 뒤 다음 쪽으로.

    쪽마다 곧바로 저장하는 것이 요점이다. 분당 한도에 걸려 중간에 끊겨도 받은 것은
    원장에 남고, 다시 부르면 `pull_prec` 의 이어하기가 이미 있는 건을 건너뛴다.

    ## 며칠짜리 훑기를 견디게 한다

    민법 판례는 분당 20회로 며칠이 걸린다. 그 사이에 한 번도 안 끊길 리 없다.
    그래서 **쪽마다 `_훑던자리.json` 에 적는다.** `이어=True` 면 거기서 이어간다.

    이것이 없을 때 **조용한 버그가 있었다**: `--쪽 50` 으로 다시 시작하면 `받음` 이
    0부터 세어져서 `받음 >= 총` 이 영영 참이 안 되고, 그러면 `_받은범위.json` 이
    안 써진다. 훑기는 멀쩡히 끝나는데 **원장은 영원히 '아직 덜 받았다'** 로 남고
    L004 가 기각으로 안 올라간다. 받아 놓고도 못 쓰는 꼴이다.

    ## 거르개는 넘겨받기만 한다

    `params` 는 API 에 **그대로 실어 보낸다.** 어느 인자가 '민법 판례' 를 골라 주는지
    여기서 정하지 않는다 -- 기억으로 인자 이름을 적어 두면 그것이 틀렸을 때
    "그런 판례가 없다" 는 거짓 결론이 조용히 남는다(`--이력` 에서 겪은 그 병).
    후보를 실어 보내고 **총건수를 보고** 사람이 고른다.
    """
    get = fetcher or _get
    키 = _훑기키(query, params)
    앞선 = 훑던자리(root).get(키, {}) if 이어 else {}
    page = (앞선.get("마지막쪽", 0) + 1) if 앞선 else start
    받음, 총 = 앞선.get("받음", 0), 앞선.get("총건수", 0)
    처음쪽 = page
    색인 = CP.load_cases(root) if not dry else {}    # 한 번만 만든다
    while True:
        xml = get(_url(SEARCH, oc, target="prec", query=query,
                       display=display, page=str(page), **(params or {})), oc)
        총 = 총 or prec_total(xml)
        rows = parse_prec_search(xml)
        if not rows:
            break
        yield {"쪽": page, "총건수": 총, "목록": len(rows),
               "받음": pull_prec("", oc, root, fetcher=get, dry=dry, rows=rows,
                                있는것=색인)}
        받음 += len(rows)
        if not dry:
            _자리적기(root, 키, page, 총, 받음)
        page += 1
        if (pages and page - 처음쪽 >= pages) or (총 and 받음 >= 총):
            break
    if not dry and 총 and 받음 >= 총:
        # **여러 번 훑을 수 있다.** 민법을 한 검색어로 다 못 긁으므로 훑은 것을
        # 쌓아 둔다. `전부` 는 지금까지 끝낸 훑기가 하나라도 있다는 뜻이다.
        p = Path(root) / CP.SCOPE_FILE
        옛 = {}
        if p.is_file():
            try:
                옛 = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                옛 = {}
        훑은것 = [x for x in 옛.get("훑은것", []) if x.get("키") != 키]
        훑은것.append({"키": 키, "검색어": query, "거르개": params or {},
                       "총건수": 총, "받은날": time.strftime("%Y-%m-%d")})
        p.write_text(json.dumps({"전부": True, "검색어": query, "총건수": 총,
                                 "받은날": time.strftime("%Y-%m-%d"),
                                 "훑은것": 훑은것},
                                ensure_ascii=False, indent=2), encoding="utf-8")


def pull_prec(query: str, oc: str, root: Path, fetcher=None, sid: str = "",
              dry: bool = False, display: str = "20", rows=None,
              있는것=None) -> list:
    """판례를 받아 저장한다. 검색어는 사건번호여도 되고 사건명이어도 된다.

    **사건번호가 안 실린 것은 저장하지 않는다.** 첫 줄이 원장의 색인이라, 사건번호가
    없으면 그 파일은 원장에 안 잡히고 있으나 마나가 된다. 조문 쪽에서 `제N조` 가
    하나도 없으면 저장을 막는 것과 같은 이유다 -- 원장에 쓰레기가 들어가면 심판이
    그것을 정답으로 삼는다.
    """
    get = fetcher or _get
    if rows is not None:
        pass                                   # 훑기가 이미 받아 온 한 쪽이다
    elif sid:
        rows = [{"일련번호": sid, "사건번호": "", "사건명": "", "법원명": "", "선고일자": ""}]
    else:
        rows = parse_prec_search(get(_url(SEARCH, oc, target="prec", query=query,
                                          display=display), oc))
    # **이어한다.** 목록에 사건번호가 이미 실려 오므로, 원장에 있는 것은 본문 호출을
    # 아예 안 한다. 분당 한도가 있는 곳에서 이것이 제일 크게 아끼는 자리다 --
    # 제한에 걸려 중간에 끊겨도 다시 부르면 안 받은 것부터 이어간다.
    # **색인을 쪽마다 다시 만들지 않는다.** `load_cases` 는 원장의 파일을 전부 열어
    # 첫 줄을 읽는다. 훑기가 쪽마다 이것을 부르면 열기 횟수가 제곱으로 는다 --
    # 실측 예정치(민법 본문검색 16,624건 · 100건씩 167쪽): 약 140만 번. 무료 VM 의
    # 느린 디스크에서는 이것이 API 기다리는 시간보다 커질 수 있다.
    # 훑기가 색인을 한 번 만들어 넘겨주면 그 자리가 사라진다(아래에서 갱신한다).
    if 있는것 is None:
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
            # 넘겨받은 색인을 그 자리에서 갱신한다. 다음 쪽이 이것을 그대로 쓴다.
            있는것[CP.normalize_case(meta["사건번호"])] = {
                "법원": meta["법원명"], "선고일자": meta["선고일자"],
                "사건명": meta["사건명"], "파일": str(path)}
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
         dry: bool = False, when: str = "") -> dict:
    """한 법령을 받아 저장한다. (검색 -> 고르기 -> 본문 -> 검사 -> 저장)

    `when` 을 주면 **그날 시행 중이던 판**을 받는다(행위시법). 그 판이 없으면 최신으로
    돌아가지 않고 **말하고 멈춘다** -- 조용히 새 법으로 옛일을 재는 것이 제일 나쁘다.
    """
    get = fetcher or _get
    chosen = None
    if not mst:
        if when:
            rows, where = history(name, oc, fetcher=get)
            판수 = len({_daykey(r.get("시행일자", "")) for r in rows} - {""})
            chosen = pick_at(rows, name, when)
            if not chosen:
                가진 = sorted({r.get("시행일자", "") for r in rows if r.get("시행일자")})
                raise RuntimeError(
                    f"{name}: {when} 에 시행 중이던 판을 못 찾았다 "
                    f"(가진 판 {판수}개: {', '.join(가진[:6]) or '없음'}"
                    + (f", target={where}" if where else "") + ")"
                    + ("\n  판이 하나뿐이면 이 API 가 현행만 주는 것이다 -- "
                       "그러면 행위시법을 못 한다." if 판수 <= 1 else ""))
        else:
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


def as_of_dir(root: Path, when: str) -> Path:
    """시점 원장의 자리. `law/corpus/@2019-02-15/`.

    현행 원장(`law/corpus/`)을 덮지 않는다. 그리고 모든 도구가 이미 `--corpus` 를
    받으므로, 이 디렉터리를 그대로 넘기면 **손댈 곳 없이** 그 시점 법으로 돌아간다.

        python3 law/gate.py 법이론서 --corpus law/corpus/@2019-02-15
    """
    return Path(root) / f"@{_daykey(when)[:4]}-{_daykey(when)[4:6]}-{_daykey(when)[6:8]}"


def main(argv=None):
    ap = argparse.ArgumentParser(description="조문 원장을 법제처 API 로 채운다")
    ap.add_argument("names", nargs="+", help="법령명 (예: 형법 민법). --판례 면 검색어/사건번호")
    ap.add_argument("--판례", dest="prec", action="store_true",
                    help="법령이 아니라 판례를 받는다 (law/precedents/ 에 저장)")
    ap.add_argument("--건수", dest="display", default="20",
                    help="--판례 일 때 한 검색어에서 받을 건수 (기본 20)")
    ap.add_argument("--전부", dest="sweep", action="store_true",
                    help="목록을 쪽 단위로 끝까지 훑는다 (이어할 수 있다)")
    ap.add_argument("--쪽", dest="page", type=int, default=1, help="--전부 시작 쪽")
    ap.add_argument("--이어", dest="resume", action="store_true",
                    help="`_훑던자리.json` 에 적힌 다음 쪽부터. 며칠짜리 훑기용")
    ap.add_argument("--거르개", dest="filters", action="append", default=[],
                    metavar="key=value",
                    help="검색에 그대로 실어 보낼 인자(여러 번 줄 수 있다). "
                         "어느 인자가 민법 판례를 골라 주는지 **재고 나서 고른다**")
    ap.add_argument("--쪽수", dest="pages", type=int, default=0,
                    help="--전부 에서 이번에 돌 쪽 수 (0 이면 끝까지)")
    ap.add_argument("--oc", default="", help="인증키. 없으면 .env 의 LAW_API_OC")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--cases", default=str(CP.CASES_DIR), help="판례 원장 자리")
    ap.add_argument("--mst", default="", help="일련번호를 직접 지정(법령 하나일 때)")
    ap.add_argument("--시행일", dest="when", default="",
                    help="그날 시행 중이던 판을 받는다 (행위시법). 예: 2019-02-15")
    ap.add_argument("--날것", dest="raw", action="store_true",
                    help="--이력 과 함께. 후보 target 이 준 XML 의 원소 이름을 그대로 "
                         "찍는다 -- 판이 하나뿐인 것인지 자가 못 읽은 것인지 가른다")
    ap.add_argument("--이력", dest="hist", action="store_true",
                    help="이 법령에 어떤 시행일 판들이 있는지만 본다 (저장 안 함)")
    ap.add_argument("--list", action="store_true", help="검색 결과만 본다")
    ap.add_argument("--dry", action="store_true", help="받되 파일은 안 쓴다")
    a = ap.parse_args(argv)
    a.oc = a.oc or oc_from_env()
    거르개 = {}
    for kv in a.filters:
        if "=" not in kv:
            print(f"--거르개 는 key=value 꼴이다 (받은 것 {kv!r})", file=sys.stderr)
            return 2
        k, _, v = kv.partition("=")
        거르개[k.strip()] = v.strip()

    if not a.oc:
        print("인증키가 없다. open.law.go.kr 에서 OPEN API 를 신청하고 발급받은 "
              "API인증키(OC)를 .env 의 LAW_API_OC 에 넣어라.", file=sys.stderr)
        return 2
    print(f"인증키 {mask(a.oc)} · 원장 {a.corpus}")

    root = Path(a.corpus)
    bad = 0

    if a.hist and a.raw:
        # **재고 나서 말한다.** "판이 하나뿐" 은 API 가 그런 것일 수도, 우리 자가
        # 원소 이름을 못 알아본 것일 수도 있다. 둘은 화면이 똑같으니 날것을 본다.
        for name in a.names:
            for tgt in HISTORY_TARGETS:
                try:
                    xml = _get(_url(SEARCH, a.oc, target=tgt, query=name,
                                    display="100"), a.oc)
                except Exception as e:                       # noqa: BLE001
                    print(f"\n[{name}] target={tgt} 조회 실패: {e}")
                    continue
                try:
                    root_el = ET.fromstring(xml)
                except ET.ParseError as e:
                    print(f"\n[{name}] target={tgt} XML 아님: {e} · 앞 200자\n"
                          f"  {xml[:200]!r}")
                    continue
                names = {}
                for el in root_el.iter():
                    names[el.tag.split("}")[-1]] = names.get(el.tag.split("}")[-1], 0) + 1
                rows = parse_search(xml)
                판 = sorted({r.get("시행일자", "") for r in rows if r.get("시행일자")})
                print(f"\n[{name}] target={tgt} · 길이 {len(xml):,} · 우리가 읽은 행 "
                      f"{len(rows)} · 시행일 {len(판)}종")
                print("  원소:", ", ".join(f"{k}×{v}" for k, v in
                                          sorted(names.items(), key=lambda x: -x[1])[:15]))
                if 판:
                    print("  시행일:", " ".join(판[:12]))
        return 0

    if a.hist:
        for name in a.names:
            rows, where = history(name, a.oc)
            판 = sorted({r.get("시행일자", "") for r in rows if r.get("시행일자")})
            print(f"\n[{name}] 시행일 판 {len(판)}개"
                  + (f" (target={where})" if where else ""))
            for r in rows[:30]:
                print(f"  시행 {r.get('시행일자', '?')} · 일련번호 "
                      f"{r.get('일련번호') or r.get('ID')}")
            if len(판) <= 1:
                print("  **판이 하나뿐이다** -- 이 API 가 현행만 준다는 뜻이고,"
                      " 그러면 행위시법을 못 한다.")
        return 0

    if a.when:
        root = as_of_dir(root, a.when)
        print(f"시점 원장 {root}  (현행 원장은 안 건드린다)")

    if a.prec:
        croot = Path(a.cases)
        print(f"판례 원장 {croot}")
        for q in a.names:
            try:
                if a.list:
                    xml = _get(_url(SEARCH, a.oc, target="prec", query=q,
                                    display=a.display, **거르개), a.oc)
                    rows, 총 = parse_prec_search(xml), prec_total(xml)
                    분 = (총 * 2 / RPM) if 총 else 0
                    print(f"\n[{q}] 총 {총 or '?'}건 · 이 쪽 {len(rows)}건"
                          + (f" · 거르개 {거르개}" if 거르개 else ""))
                    if 총:
                        일 = 분 / 60 / 24
                        print(f"  전부 받으면 호출 약 {총 * 2}회 · 분당 {RPM} 이면 "
                              f"**{분 / 60:.1f}시간**"
                              + (f" (= {일:.1f}일)" if 일 >= 1 else "")
                              + "  (--이어 로 끊어 돌 수 있다)")
                    for r in rows[:20]:
                        print(f"  {r['사건번호']} · {r['법원명']} · {r['선고일자']}"
                              f" · {r['사건명'][:40]}")
                    continue
                if a.sweep:
                    앞 = 훑던자리(croot).get(_훑기키(q, 거르개))
                    if a.resume and 앞:
                        print(f"  이어한다 -- {앞['마지막쪽']}쪽까지 받았다"
                              f" ({앞['받음']}/{앞['총건수']}건, {앞['때']})")
                    for 쪽 in sweep_prec(q, a.oc, croot, display=a.display,
                                        start=a.page, pages=a.pages, dry=a.dry,
                                        params=거르개, 이어=a.resume):
                        새 = sum(1 for r in 쪽["받음"] if not r.get("이미") and not r.get("실패"))
                        print(f"  {q} 쪽 {쪽['쪽']} · 목록 {쪽['목록']}건 · 새로 {새}건"
                              f"  (총 {쪽['총건수'] or '?'})", flush=True)
                    사건 = CP.load_cases(croot)
                    print(f"[{q}] 훑기 끝 · 원장 {len(사건)}건"
                          + (" · **전부 받았다고 적었다** (L004 가 기각으로 올라간다)"
                             if CP.load_case_scope(croot).get("전부") else
                             " · 아직 덜 받았다 (L004 는 미검증으로 남는다)"))
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
                     dry=a.dry, when=a.when)
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
