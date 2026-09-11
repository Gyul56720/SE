"""**뽑는다 -- 있는 것을 다.** 고르지 않는다.

`brief/ledger.py` 는 '줄' 하나만 찾았다. 수를 재는 것이 목적이었으니 옳았다. 여기
목적은 **무엇이 있는가**이므로 반대다 -- 한 쪽에서 나올 수 있는 갈래를 전부 판다.

    묻힌표(JSON-LD)   schema.org. **메뉴· 값· 평점· 영업시간이 여기 있다.**
    머리표(og·meta)   제목· 그림· 설명· 좌표
    묻힌json          __NEXT_DATA__ · __INITIAL_STATE__ · <script type=json>
    표(table)         그대로 줄로
    목록(ul·ol·dl)    메뉴판이 대개 이 꼴이다
    링크              안쪽으로 더 팔 자리
    글                태그 걷어낸 본문
    캔값              가격· 전화· 평점· 시간· 주소· 좌표· 이메일 -- 정규식으로

## 왜 정규식까지 쓰나

구조가 없는 쪽이 많다. "1인 12,000원" 이 그냥 글 안에 있으면 JSON-LD 도 표도 없다.
**구조가 없다고 값이 없는 것이 아니다.** 구조에서 못 얻으면 글에서 캔다. 캔 것은
`캔값` 에 따로 담아 둔다 -- 어디서 왔는지 갈라 두면 읽는 쪽이 믿을 만큼만 믿는다.

## 안 하는 것

**고르지 않는다.** 무엇이 중요한지는 여기서 안 정한다. 다 담아서 올려 보내고, 줄일지
말지는 부르는 쪽이 정한다 -- 여기서 줄이면 **줄인 것을 아무도 못 되찾는다.**
"""
from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser

# ── 캘 값들. **도메인이 아니라 꼴이다** -- 맛집이든 부품이든 같은 정규식이 문다 ────
값꼴 = {
    "가격": re.compile(
        r"(?:₩|\$|€|¥|￦)\s?\d[\d,]*(?:\.\d+)?|"
        r"\d[\d,]*(?:\.\d+)?\s*(?:원|won|KRW|USD|달러|엔|위안)", re.I),
    "전화": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?0?\d{2,4}[-.\s]\d{3,4}[-.\s]\d{4}"),
    "평점": re.compile(r"(?:★|☆|평점|별점|rating|score)\s*:?\s*\d(?:\.\d+)?|"
                      r"\d(?:\.\d+)?\s*/\s*(?:5|10)(?:점|\b)", re.I),
    "시간": re.compile(r"\d{1,2}\s*:\s*\d{2}\s*(?:~|-|–|—|부터|to)\s*\d{1,2}\s*:\s*\d{2}|"
                      r"(?:매일|평일|주말|월|화|수|목|금|토|일)\s*\d{1,2}:\d{2}"),
    # `고려대로24길 15` 처럼 **길 이름 뒤에 번지가 또 온다.** 처음에 앞쪽만 물어서
    # "고려대로24" 에서 잘렸다(검사가 잡았다) -- 잘린 주소는 못 찾아가는 주소다.
    "주소": re.compile(r"[가-힣A-Za-z0-9]+(?:특별시|광역시|도|시|군|구)\s"
                      r"[^\n,<>]{2,40}?(?:로|길|동|가|읍|면)\s?\d[\d\-]*"
                      r"(?:\s?길\s?\d[\d\-]*)?(?:\s?\d+동)?(?:\s?\d+호)?"),
    "좌표": re.compile(r"[-+]?\d{1,3}\.\d{4,}\s*,\s*[-+]?\d{1,3}\.\d{4,}"),
    "이메일": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
    "날짜": re.compile(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{4}년\s?\d{1,2}월\s?\d{1,2}일"),
    "퍼센트": re.compile(r"[-+]?\d+(?:\.\d+)?\s?%"),
}

# 쪽이 자기 상태를 <script> 안에 통째로 박아 두는 이름들. **여기 진짜가 있을 때가
# 많다** -- 눈에 보이는 HTML 은 껍데기고 목록· 값· 자막 주소는 이 덩어리 안에 있다.
# 이름을 아는 만큼만 캘 수 있어서, 새 꼴을 만나면 여기 한 줄을 더한다.
_묻힌json이름 = ("__NEXT_DATA__", "__NUXT__", "__INITIAL_STATE__", "__APOLLO_STATE__",
                "__PRELOADED_STATE__", "INITIAL_DATA", "window.__data",
                # 영상 쪽. 재생목록의 항목들과 자막 트랙 주소가 여기 들어 있다 --
                # 본문 HTML 에는 한 줄도 없다(스크립트가 그려 넣는다).
                "ytInitialData", "ytInitialPlayerResponse",
                "__remixContext", "__STATE__", "__DATA__", "self.__next_f")


class _판(HTMLParser):
    """HTML 을 한 번만 훑으며 **여러 갈래를 동시에** 담는다.

    bs4 를 안 쓴다 -- 이 저장소는 표준 라이브러리로만 돈다. 대신 필요한 것만 본다.
    닫는 태그가 어긋나도 안 죽는다(`convert_charrefs` 가 글자를 풀어 준다).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.jsonld, self.묻힌json, self.머리표 = [], [], {}
        self.표, self.목록, self.링크, self.글, self.제목 = [], [], [], [], []
        # 비언어: 수식(LaTeX 문자열) · 그림(캡션·출처 포인터). 픽셀은 안 담는다 -- 검증 못 한다.
        self.수식, self.그림 = [], []
        self._anno, self._figcap = False, None
        # 표마다 '첫 줄이 진짜 머리였나'. **첫 줄을 무조건 머리로 먹으면 안 된다** --
        # <th> 없는 표(메뉴 · 값 목록이 흔히 그렇다)에서는 그 줄이 첫 메뉴다.
        self.표머리: list = []
        self._이표머리 = False
        self._칸th = False
        self._줄모두th = True
        self._script, self._스타일 = "", 0
        self._표: list = []
        self._줄: list = []
        self._칸 = None
        self._목록: list = []
        self._항목 = None
        self._a = None
        self._h = None

    # ── 태그 ──────────────────────────────────────────────────────
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self._script = a.get("type", "") or "js"
            self._현재script = ""
        elif tag in ("style", "noscript"):
            self._스타일 += 1
        elif tag in ("meta",):
            키 = a.get("property") or a.get("name") or a.get("itemprop")
            값 = a.get("content")
            if 키 and 값:
                self.머리표.setdefault(키, 값)
        elif tag == "link":
            # **<link rel> 을 안 읽고 있었다.** 거기 다음에 두드릴 문이 적혀 있다 --
            # 피드(rss· atom: 글 본문이 통째로 온다) · canonical(진짜 주소) ·
            # oembed 끝점 · alternate(다른 언어· 모바일 쪽). 쪽이 **스스로 알려 주는**
            # 곁문인데 meta 만 보느라 통째로 버렸다.
            rel = " ".join(a.get("rel", "").split()).lower()
            href = a.get("href")
            if rel and href and rel not in ("stylesheet", "preload", "prefetch",
                                            "dns-prefetch", "preconnect",
                                            "icon", "shortcut icon", "apple-touch-icon",
                                            "manifest", "modulepreload"):
                self.머리표.setdefault(f"link:{rel}", href)
        elif tag == "table":
            self._표 = []
            self._이표머리 = False
        elif tag == "tr":
            self._줄 = []
            self._줄모두th = True
        elif tag in ("td", "th"):
            self._칸 = ""
            self._칸th = (tag == "th")
        elif tag in ("ul", "ol", "dl"):
            self._목록 = []
        elif tag in ("li", "dt", "dd"):
            self._항목 = ""
        elif tag == "a":
            self._a = a.get("href", "")
            self._a글 = ""
        elif tag in ("h1", "h2", "h3", "h4"):
            self._h = ""
        elif tag == "img":
            # alt 에 정보가 있는 일이 흔하다(메뉴 사진의 이름·가격)
            if a.get("alt"):
                self.글.append(a["alt"])
            src = a.get("src") or a.get("data-src") or ""
            if src or a.get("alt"):
                self.그림.append({"꼴": "img", "src": src[:300], "캡션": (a.get("alt") or "")[:300]})
        elif tag == "math":
            # arXiv HTML 의 MathML 은 alttext 에 원본 LaTeX 를 담는다 -- 그것만 집는다(속 글자는 부스러기)
            alt = a.get("alttext") or a.get("data-latex")
            if alt:
                self.수식.append(alt.strip())
        elif tag == "annotation":
            self._anno = "tex" in (a.get("encoding", "") or "").lower()
        elif tag == "figcaption":
            self._figcap = ""

    def handle_endtag(self, tag):
        if tag == "script":
            글 = getattr(self, "_현재script", "")
            self._담기(self._script, 글)
            self._script, self._현재script = "", ""
        elif tag in ("style", "noscript"):
            self._스타일 = max(0, self._스타일 - 1)
        elif tag in ("td", "th"):
            if self._칸 is not None:
                self._줄.append(self._칸.strip())
                # 한 칸이라도 td 면 머리줄이 아니다. 줄머리(<th>이름</th><td>값</td>)를
                # 머리로 오해하면 그 표의 값이 통째로 열쇠 자리로 간다.
                self._줄모두th = self._줄모두th and self._칸th
            self._칸 = None
        elif tag == "tr":
            if self._줄:
                if not self._표:
                    self._이표머리 = self._줄모두th
                self._표.append(self._줄)
            self._줄 = []
        elif tag == "table":
            if self._표:
                self.표.append(self._표)
                self.표머리.append(self._이표머리)
            self._표 = []
        elif tag in ("li", "dt", "dd"):
            if self._항목 and self._항목.strip():
                self._목록.append(self._항목.strip())
            self._항목 = None
        elif tag in ("ul", "ol", "dl"):
            if self._목록:
                self.목록.append(list(self._목록))
            self._목록 = []
        elif tag == "a":
            if self._a:
                self.링크.append({"href": self._a,
                                 "글": (getattr(self, "_a글", "") or "").strip()[:120]})
            self._a = None
        elif tag in ("h1", "h2", "h3", "h4"):
            if self._h and self._h.strip():
                self.제목.append(self._h.strip())
            self._h = None
        elif tag == "annotation":
            self._anno = False
        elif tag == "figcaption":
            if self._figcap and self._figcap.strip():
                self.그림.append({"꼴": "figure", "src": "", "캡션": self._figcap.strip()[:400]})
            self._figcap = None

    def handle_data(self, d):
        if self._script:
            self._현재script = getattr(self, "_현재script", "") + d
            return
        if self._스타일:
            return
        글 = d.strip()
        if not 글:
            return
        if self._칸 is not None:
            self._칸 += " " + 글
        if self._항목 is not None:
            self._항목 += " " + 글
        if self._a is not None:
            self._a글 = getattr(self, "_a글", "") + " " + 글
        if self._h is not None:
            self._h += " " + 글
        if self._anno:
            self.수식.append(글)
        if self._figcap is not None:
            self._figcap += " " + 글
        self.글.append(글)

    # ── script 안 ─────────────────────────────────────────────────
    def _담기(self, 종류: str, 글: str):
        글 = (글 or "").strip()
        if not 글:
            return
        if "ld+json" in 종류:
            d = _느슨하게json(글)
            if d is not None:
                self.jsonld.append(d)
            return
        if "json" in 종류:
            d = _느슨하게json(글)
            if d is not None:
                self.묻힌json.append({"어디": 종류, "값": d})
            return
        # 그냥 <script> 안에 박힌 상태 덩어리. **여기 진짜가 있을 때가 많다.**
        for 이름 in _묻힌json이름:
            if 이름 in 글:
                d = _중괄호덩어리(글, 글.find(이름))
                if d is not None:
                    self.묻힌json.append({"어디": 이름, "값": d})
                break


def _느슨하게json(글: str):
    """JSON 으로 읽되 **깨진 것도 살려 본다.**

    실제 쪽에는 끝에 세미콜론이 붙거나 여러 덩어리가 이어 붙어 있다. 한 번 실패했다고
    버리면 거기 있던 메뉴·가격이 통째로 없어진다.
    """
    글 = 글.strip().rstrip(";").strip()
    try:
        return json.loads(글)
    except json.JSONDecodeError:
        pass
    # 이어 붙은 덩어리: 첫 것만이라도
    d = _중괄호덩어리(글, 0)
    if d is not None:
        return d
    return None


def _중괄호덩어리(글: str, 시작: int):
    """`시작` 뒤 첫 `{`(또는 `[`)에서 짝 맞는 데까지 잘라 읽는다. 문자열 안은 안 센다."""
    i = 글.find("{", 시작)
    j = 글.find("[", 시작)
    if i < 0 and j < 0:
        return None
    i = j if i < 0 or (0 <= j < i) else i
    엶, 닫 = 글[i], ("}" if 글[i] == "{" else "]")
    깊이, 따옴, 이스 = 0, "", False
    for k in range(i, min(len(글), i + 4_000_000)):
        c = 글[k]
        if 이스:
            이스 = False
            continue
        if c == "\\":
            이스 = True
            continue
        if 따옴:
            if c == 따옴:
                따옴 = ""
            continue
        if c in "\"'":
            따옴 = c
            continue
        if c == 엶:
            깊이 += 1
        elif c == 닫:
            깊이 -= 1
            if 깊이 == 0:
                try:
                    return json.loads(글[i:k + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _평평(값, 앞="", 나온것=None, 깊이=0):
    """중첩 JSON 을 `a.b.c = 값` 으로 편다. **묻힌 것을 눈에 보이게 한다.**

    JSON-LD 의 메뉴는 `hasMenu.hasMenuSection[0].hasMenuItem[3].offers.price` 같은
    데 있다. 안 펴면 사람이 못 찾고, 못 찾으면 없는 것과 같다.
    """
    if 나온것 is None:
        나온것 = {}
    if 깊이 > 12 or len(나온것) > 4000:
        return 나온것
    if isinstance(값, dict):
        for k, v in 값.items():
            _평평(v, f"{앞}.{k}" if 앞 else str(k), 나온것, 깊이 + 1)
    elif isinstance(값, list):
        for i, v in enumerate(값):
            _평평(v, f"{앞}[{i}]", 나온것, 깊이 + 1)
    elif 값 is not None and str(값).strip():
        나온것[앞] = 값
    return 나온것


def 캔값(글: str) -> dict:
    """글에서 값을 캔다. **구조가 없다고 값이 없는 것이 아니다.**

    겹치는 것은 없애되 **순서는 나온 대로** 둔다 -- 쪽 위에서 위에 있던 것이 대개
    더 중요하고, 정렬해 버리면 그 단서가 없어진다.
    """
    out = {}
    for 이름, pat in 값꼴.items():
        본, 목록 = set(), []
        for m in pat.finditer(글):
            v = m.group(0).strip()
            if v not in 본:
                본.add(v)
                목록.append(v)
            if len(목록) >= 200:
                break
        if 목록:
            out[이름] = 목록
    return out


def 표로(표: list, 머리있음: bool = True) -> list:
    """`[[칸,칸],[값,값]]` -> dict 목록. 머리가 있으면 첫 줄을 열쇠로, **없으면 자리번호로.**

    `머리있음` 은 **문서가 그렇게 적었나**를 그대로 옮긴 것이다(`_판` 이 첫 줄이
    전부 `<th>` 였는지 본다). 예전엔 이것을 안 보고 첫 줄을 늘 머리로 먹었는데,
    `<th>` 없는 표에서는 그 줄이 **첫 값**이다 -- 메뉴판이 거의 그 꼴이라

        <tr><td>육개장</td><td>9,000원</td></tr>
        <tr><td>돼지갈비</td><td>15,000원</td></tr>

    가 `{'육개장': '돼지갈비', '9,000원': '15,000원'}` 한 줄이 됐다. 첫 메뉴와 그 값이
    열쇠 자리로 가면서 **두 줄이 한 줄로 뭉개졌다**(실측 2026-09-09).
    """
    if not 표:
        return []
    머리 = 표[0]
    몸 = 표[1:]
    if not 머리있음 or not 몸 or len({len(r) for r in 표}) > 2:
        머리 = [f"칸{i+1}" for i in range(max(len(r) for r in 표))]
        몸 = 표
    return [{(머리[i] if i < len(머리) and 머리[i] else f"칸{i+1}"): v
             for i, v in enumerate(r)} for r in 몸 if any(x.strip() for x in r)]


def 뽑기(몸통: str, 꼴: str = "", url: str = "") -> dict:
    """**한 쪽에서 나올 수 있는 것을 다 뽑는다.** 고르지 않는다.

    `꼴` 은 힌트일 뿐이다. 안 맞으면 몸통을 보고 정한다 -- 서버가 Content-Type 을
    틀리게 주는 일이 흔하고, 그것을 믿었다가 통째로 못 읽는 것이 아깝다.
    """
    몸통 = 몸통 or ""
    t = 몸통.lstrip()[:400].lower()
    html꼴 = ("html" in (꼴 or "").lower() or t.startswith("<!doctype html")
              or t.startswith("<html") or "<body" in 몸통[:2000].lower()
              or "<div" in 몸통[:2000].lower())
    out: dict = {"url": url, "받은꼴": 꼴, "길이": len(몸통)}

    if html꼴:
        p = _판()
        try:
            p.feed(몸통)
            p.close()
        except Exception:                                      # noqa: BLE001
            pass                                               # 깨진 HTML 도 여기까지 담긴다
        글 = " ".join(p.글)
        out.update({
            "갈래": "html",
            "제목": (p.머리표.get("og:title") or p.머리표.get("title")
                    or (p.제목[0] if p.제목 else "")),
            "머리표": p.머리표,
            "묻힌표": [_평평(x) for x in p.jsonld],
            "묻힌표원본": p.jsonld,
            "묻힌json": [{"어디": x["어디"], "칸": _평평(x["값"])} for x in p.묻힌json],
            "표": [표로(t2, p.표머리[i] if i < len(p.표머리) else True)
                  for i, t2 in enumerate(p.표)],
            "목록": p.목록,
            "제목들": p.제목,
            "링크": p.링크,
            "수식": list(dict.fromkeys(x for x in p.수식 if x.strip()))[:200],
            "그림": p.그림[:100],
            "글": 글,
            # **머리표까지 넣고 캔다.** 좌표(`geo.position`)· 전화· 가격이 meta 에만
            # 있는 쪽이 흔하다 -- 눈에 보이는 글만 캐면 그것을 통째로 놓친다.
            "캔값": 캔값(" ".join([글]
                               + [str(v) for v in p.머리표.values()]
                               + [str(v) for x in p.jsonld
                                  for v in _평평(x).values()])),
        })
        return out

    # JSON / XML / CSV / 그 밖 -- 전부 편다
    d = _느슨하게json(몸통)
    if d is not None:
        out.update({"갈래": "json", "칸": _평평(d), "원본": d, "캔값": 캔값(몸통)})
        return out
    if 몸통.lstrip().startswith("<"):
        p = _판()
        try:
            p.feed(몸통)
            p.close()
        except Exception:                                      # noqa: BLE001
            pass
        out.update({"갈래": "xml", "글": " ".join(p.글),
                    "표": [표로(t2, p.표머리[i] if i < len(p.표머리) else True)
                          for i, t2 in enumerate(p.표)],
                    "목록": p.목록, "캔값": 캔값(몸통)})
        return out
    out.update({"갈래": "글", "글": 몸통, "캔값": 캔값(몸통)})
    return out


_수식환경 = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|eqnarray\*?|multline\*?)\}(.+?)\\end\{\1\}", re.S)
_수식구분 = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)", re.S)


def 수식뽑기(text: str) -> "list[str]":
    """날 텍스트(TeX 소스·마크다운)에서 수식을 **원문 LaTeX 그대로** 뽑는다. 렌더링·해석 안 함.
    equation/align 등 환경 + $$…$$ · \\[…\\] · \\(…\\). 검증 가능한 문자열이라 그대로 보관한다."""
    out = []
    for m in _수식환경.finditer(text or ""):
        out.append(" ".join(m.group(2).split()))
    for m in _수식구분.finditer(text or ""):
        조각 = next((g for g in m.groups() if g), "")
        조각 = " ".join(조각.split())
        if 조각:
            out.append(조각)
    return list(dict.fromkeys(x for x in out if x))[:200]


def 합치기(뽑은것들: list) -> dict:
    """여러 쪽에서 뽑은 것을 **한 자리에 모은다. 겹치는 것만 지운다.**

    다른 문은 다른 것을 준다(모바일에 가격, 데스크톱에 리뷰). 그래서 합치는 것이
    이 도구의 요점이다 -- 다만 **어느 쪽에서 왔는지는 값마다 남긴다.**
    """
    묶음: dict = {"쪽수": len(뽑은것들), "출처": [], "제목": "", "머리표": {},
                 "묻힌표": [], "묻힌json": [], "표": [], "목록": [], "제목들": [],
                 "링크": [], "캔값": {}, "글길이": 0}
    본캔값: dict = {}
    본링크 = set()
    for x in 뽑은것들:
        묶음["출처"].append({"url": x.get("url", ""), "갈래": x.get("갈래", ""),
                           "길이": x.get("길이", 0)})
        if not 묶음["제목"] and x.get("제목"):
            묶음["제목"] = x["제목"]
        for k, v in (x.get("머리표") or {}).items():
            묶음["머리표"].setdefault(k, v)
        for 키 in ("묻힌표", "묻힌json", "표", "목록", "제목들"):
            묶음[키] += x.get(키) or []
        # **JSON 으로 답한 쪽을 여기서 잃고 있었다.** `뽑기` 는 json 쪽을 {"갈래":
        # "json", "칸": {...}} 로 내는데 위 목록에 `칸` 이 없어서, api 로 받은 것이
        # 캔값 말고는 통째로 버려졌다(실측 2026-09-09). 하필 api 탐색이 이 도구의
        # 요점인데 그 길만 비어 있었다. 묻힌json 과 같은 자리에 실어 같이 낸다.
        if x.get("갈래") == "json" and x.get("칸"):
            묶음["묻힌json"].append({"어디": x.get("url") or "json", "칸": x["칸"]})
        for L in x.get("링크") or []:
            h = L.get("href", "")
            if h and h not in 본링크:
                본링크.add(h)
                묶음["링크"].append(L)
        묶음["글길이"] += len(x.get("글") or "")
        for 이름, 목록 in (x.get("캔값") or {}).items():
            자리 = 본캔값.setdefault(이름, [])
            for v in 목록:
                if v not in 자리:
                    자리.append(v)
    묶음["캔값"] = 본캔값
    return 묶음
