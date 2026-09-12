"""**받아 온다 -- 되는 방법을 다 써서.**

`brief/ledger.py get()` 은 한 번 부르고 안 되면 끝이었다. 여기는 다르다. 목표가
'판정할 수 있는 것만 받기' 가 아니라 **'받을 수 있는 것을 다 받기'** 이기 때문이다.

    한 주소  ->  헤더 여러 벌  ->  안 되면 곁문(m· amp· json· 아카이브)  ->  받은 것 전부

## 무엇이 다른가

    brief   받아서 **검사에 통과하는 것만** 원장에 넣는다. 수인 칸이 없으면 거절
    dig     받은 것을 **다 들고 온다.** 거절이 없다. 거르는 것은 뒤에서 할 일이다

`brief` 의 거절은 옳았다 -- 거기 목적이 '이 수를 믿어도 되는가' 였으므로. 여기 목적은
'무엇이 있는가' 다. 같은 거절을 여기서 하면 **찾아 준 것이 없어진다.**

## 되는 방법을 다 쓴다 -- 다만 문을 부수지는 않는다

곁문은 **주인이 열어 둔 다른 문**이다: 모바일 쪽 · AMP · 그 쪽이 쓰는 JSON 끝점 ·
공개 아카이브. 로그인·유료벽·접근 제어를 뚫는 것은 안 한다 -- 그것은 다른 일이고,
여기서 하면 이 도구를 못 쓰게 된다.

## 못 받았으면 **왜 못 받았는지** 남긴다

빈손으로 돌아오는 것과 '403 이라 못 받았다' 는 다른 말이다. 뒤쪽만이 다음에 무엇을
할지 알려 준다(다른 헤더· 곁문· 다른 출처). `brief/_왜못받았나` 가 배운 것과 같다.
"""
from __future__ import annotations

import gzip
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

기본틈 = 20.0
재시도 = 2

# **헤더를 여러 벌 돌려쓴다.** 같은 주소가 UA 하나에는 403 을 주고 다른 것에는 200 을
# 준다(실측: Yahoo v7 은 401, v8 은 UA 만 붙이면 200). 어느 것이 될지 미리 못 아니까
# 순서대로 해 본다 -- **한 번 해 보고 '안 된다' 고 말하지 않는다.**
헤더벌 = (
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
               "application/json;q=0.9,*/*;q=0.8",
     "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
     "Accept-Encoding": "gzip, deflate"},
    {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1",
     "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9",
     "Accept-Encoding": "gzip, deflate"},
    {"User-Agent": "SE-dig/1.0 (+https://github.com/gyul56720/se)",
     "Accept": "application/json, text/plain, */*"},
)


@dataclass
class 응답:
    url: str = ""
    최종url: str = ""
    코드: int = 0
    몸통: str = ""
    꼴: str = ""                 # Content-Type 에서 온 것
    헤더: dict = field(default_factory=dict)
    걸린초: float = 0.0
    쓴헤더: int = -1             # 몇 번째 헤더벌로 됐나
    왜: str = ""                 # 못 받았으면 까닭

    @property
    def 됐나(self) -> bool:
        return bool(self.몸통) and not self.왜

    def __str__(self) -> str:
        if not self.됐나:
            return f"[못받음] {self.url[:70]} -- {self.왜[:80]}"
        return (f"[{self.코드}] {self.url[:70]} · {len(self.몸통)}자 · "
                f"{self.꼴 or '?'} · {self.걸린초:.1f}s")


def _풀기(raw: bytes, enc: str) -> bytes:
    """gzip· deflate 를 푼다. **못 풀면 그대로 준다** -- 안 죽는 쪽으로."""
    try:
        if "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
    except (OSError, zlib.error):
        pass
    return raw


_META인코딩 = re.compile(
    rb"""<meta[^>]+charset=["']?\s*([A-Za-z0-9_\-]+)""", re.I)


def _글자로(raw: bytes, ctype: str) -> str:
    """바이트 -> 글자. **한글이 깨지면 정보가 없는 것과 같다.**

    순서: 헤더의 charset -> 문서 안 meta charset -> utf-8 -> cp949(euc-kr) -> latin-1.
    한국 사이트에 cp949 가 아직 많다. 마지막 latin-1 은 절대 안 터지므로 **빈손으로
    돌아가는 일이 없다** -- 깨져도 뽑을 것이 남는다.
    """
    후보 = []
    m = re.search(r"charset=\s*([A-Za-z0-9_\-]+)", ctype or "", re.I)
    if m:
        후보.append(m.group(1))
    m2 = _META인코딩.search(raw[:4096])
    if m2:
        후보.append(m2.group(1).decode("ascii", "ignore"))
    후보 += ["utf-8", "cp949", "euc-kr", "latin-1"]
    본 = []
    for enc in 후보:
        if not enc or enc.lower() in 본:
            continue
        본.append(enc.lower())
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _왜(e, url: str) -> str:
    """**갈래를 갈라 말한다.** 무엇을 다음에 할지가 갈래마다 다르다."""
    if isinstance(e, urllib.error.HTTPError):
        표 = {401: "인증이 필요하다 -- 열쇠 없이는 못 간다",
              403: "막았다 -- 헤더를 바꾸거나 곁문을 보라",
              404: "그런 주소가 없다 -- 주소가 틀렸거나 그 쪽이 옮겼다",
              429: "너무 자주 불렀다 -- 쉬었다 다시",
              500: "그 쪽 탈", 502: "그 쪽 탈", 503: "그 쪽이 잠깐 못 받는다"}
        return f"HTTP {e.code} -- {표.get(e.code, '그 쪽이 거절했다')}"
    if isinstance(e, urllib.error.URLError):
        r = str(getattr(e, "reason", e))
        if "Tunnel" in r or "proxy" in r.lower() or "CONNECT" in r:
            return f"프록시가 끊었다 -- 이 환경의 나가는 길이 막혔다 ({r[:60]})"
        return f"안 닿는다 -- {r[:80]}"
    if isinstance(e, socket.timeout):
        return f"{기본틈}초 안에 답이 없다"
    return f"{type(e).__name__}: {str(e)[:80]}"


def 주소정규화(url: str) -> str:
    """날 비아스키(한글 등)가 든 주소를 urllib 이 받을 꼴로. 이미 퍼센트 인코딩된 것은 건드리지 않는다.

    왜: `urllib.request` 는 주소가 아스키여야 한다. 한글이 그대로 들어 있으면
    `UnicodeEncodeError: 'ascii' codec can't encode characters` 로 죽는다. 실측 2026-09-12:
    봇이 `--url 'https://search.naver.com/...?query=한글'` 로 캐다 이 오류를 만났고, 보고에는
    **"시스템 내부의 인코딩 제한으로 한글 검색어가 거부된다"** 고 적혔다. 제한이 아니라 빠진
    한 줄이었다 -- dig/search.py 의 질의는 quote 를 지나는데 `--url` 과 따라가는 안쪽 링크는
    안 지났다. 잘못된 진단은 고칠 자리를 가린다.

    집(netloc)은 IDNA 로, 경로·질의·조각은 퍼센트 인코딩으로. `%` 가 이미 있는 자리는
    safe 에 넣어 두 번 인코딩되지 않게 한다."""
    u = (url or "").strip()
    if u.isascii() and " " not in u:
        return u                               # 멀쩡한 주소는 손대지 않는다(22개 검색 틀을 건드리지 않으려고)
    p = urllib.parse.urlsplit(u)
    try:
        host = p.hostname.encode("idna").decode("ascii") if p.hostname and not p.hostname.isascii() else (p.hostname or "")
    except (UnicodeError, AttributeError):
        host = p.hostname or ""
    netloc = host
    if p.port:
        netloc = f"{netloc}:{p.port}"
    if p.username:
        사용자 = urllib.parse.quote(p.username, safe="%")
        if p.password:
            사용자 += ":" + urllib.parse.quote(p.password, safe="%")
        netloc = f"{사용자}@{netloc}"
    return urllib.parse.urlunsplit((
        p.scheme,
        netloc,
        urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=~"),
        urllib.parse.quote(p.query, safe="/%:@!$&'()*+,;=~?"),
        urllib.parse.quote(p.fragment, safe="/%:@!$&'()*+,;=~?"),
    ))


def 한번(url: str, 헤더: dict, 틈: float = 기본틈) -> 응답:
    시작 = time.time()
    # **정규화는 urlopen 직전 한 자리에서만.** 돌려주는 응답의 url 은 부른 쪽이 준 그대로 둔다 --
    # 실측 2026-09-12: 받기() 에서 미리 바꿨더니 한글 집이 punycode 로 바뀌어, 집 이름으로 갈래를
    # 정하던 곳(tests/test_jaso_crawl 의 가짜 문)이 깨졌다. precheck 가 그것을 잡았다.
    req = urllib.request.Request(주소정규화(url), headers=헤더)
    try:
        with urllib.request.urlopen(req, timeout=틈) as r:     # noqa: S310
            raw = _풀기(r.read(), r.headers.get("Content-Encoding", "") or "")
            ctype = r.headers.get("Content-Type", "") or ""
            return 응답(url=url, 최종url=r.geturl(), 코드=r.status,
                       몸통=_글자로(raw, ctype), 꼴=ctype.split(";")[0].strip(),
                       헤더={k: v for k, v in r.headers.items()},
                       걸린초=time.time() - 시작)
    except Exception as e:                                     # noqa: BLE001
        # **HTTP 오류에도 몸통이 있다.** 404 쪽에 "이건 여기로 옮겼다" 가 적혀 있는
        # 일이 흔하다. 버리면 그 말을 못 읽는다.
        몸 = ""
        if isinstance(e, urllib.error.HTTPError):
            try:
                몸 = _글자로(_풀기(e.read(), e.headers.get("Content-Encoding", "") or ""),
                            e.headers.get("Content-Type", "") or "")
            except Exception:                                  # noqa: BLE001
                몸 = ""
        return 응답(url=url, 코드=getattr(e, "code", 0), 몸통=몸,
                   걸린초=time.time() - 시작, 왜=_왜(e, url))


def 받기(url: str, 틈: float = 기본틈, 벌수: int = 0) -> 응답:
    """**헤더벌을 돌려쓴다.** 하나가 막히면 다음 것으로 -- 한 번 해 보고 안 된다고
    말하지 않는다(`main_public` 4-1 이 금지한 그 일).

    `벌수` 를 주면 그 수만큼만 해 본다(0 이면 전부).
    """
    벌 = 헤더벌[:벌수] if 벌수 else 헤더벌
    마지막 = 응답(url=url, 왜="해 본 것이 없다")
    for i, h in enumerate(벌):
        r = 한번(url, dict(h), 틈)
        r.쓴헤더 = i
        if r.됐나:
            return r
        마지막 = r
        # 429·503 은 쉬면 되는 것이다. 나머지는 헤더를 바꿔 본다.
        if r.코드 in (429, 503):
            time.sleep(1.0 + i)
    return 마지막


def 영상쪽인가(url: str) -> str:
    """영상 쪽이면 그 id, 아니면 빈 글자. **꼴로만 본다.**"""
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return ""
    host, path = (p.netloc or "").lower(), p.path or ""
    if "youtu.be" in host:
        마디 = [s for s in path.split("/") if s]
        return 마디[0] if 마디 else ""
    if "youtube" not in host:
        return ""
    got = urllib.parse.parse_qs(p.query).get("v")
    if got and got[0]:
        return got[0]
    for 앞 in ("/embed/", "/shorts/", "/live/", "/v/"):
        if 앞 in path:
            return path.split(앞, 1)[1].split("/")[0]
    return ""


def 영상곁문(url: str, p=None) -> list:
    """**영상은 글이 본문 밖에 있다.** 자막과 재생목록을 따로 두드린다.

    영상 쪽을 그냥 받으면 제목과 설명뿐이다 -- 정작 사람이 말한 내용은 **자막
    트랙**에 있고, 재생목록의 항목들은 `ytInitialData` 안에 있다. 둘 다 앞문
    HTML 에는 한 줄도 안 나온다. 그래서 곁문이 필요하다.

    이것은 **어떤 물음에도 붙는다** -- 편입 수기든 강의든 리뷰든 회의록이든,
    영상이 답을 들고 있는 물음은 갈래를 안 가린다. 그래서 `jaso/` 옆이 아니라
    여기 있다.

    자막은 **공개된 것만** 받는다. 로그인·유료벽을 뚫지 않는다는 선은 그대로다.
    """
    vid = 영상쪽인가(url)
    나온것 = []
    if vid:
        # 어떤 자막이 있나(트랙 목록) -- 그 다음에 무엇을 받을지 이것이 알려 준다.
        나온것.append(f"https://www.youtube.com/api/timedtext?type=list&v={vid}")
        # 흔한 것 몇을 바로 두드린다. 어느 것이 있을지 미리 모르니 다 해 본다 --
        # 없는 것은 빈 답 하나로 끝나고, 있으면 그 자리에서 글이 통째로 온다.
        for lang in ("ko", "en"):
            나온것.append(
                f"https://www.youtube.com/api/timedtext?lang={lang}&v={vid}&fmt=json3")
            나온것.append(f"https://www.youtube.com/api/timedtext?lang={lang}&v={vid}")
        # 앞문이 shorts· youtu.be· embed 여도 제대로 된 쪽을 한 번 더 본다.
        나온것.append(f"https://www.youtube.com/watch?v={vid}")
    if p is not None and "list=" in (p.query or ""):
        # 재생목록. 항목이 ytInitialData 안에 있어 뽑개가 편다.
        목록 = urllib.parse.parse_qs(p.query).get("list")
        if 목록:
            나온것.append(f"https://www.youtube.com/playlist?list={목록[0]}")
    return [u for u in 나온것 if u != url]


def 곁문(url: str) -> list:
    """**같은 것을 주는 다른 문들.** 주인이 열어 둔 것만 -- 문을 부수지 않는다.

    앞문이 막혀도 이 중 하나가 열려 있는 일이 아주 흔하다. 모바일 쪽은 HTML 이 훨씬
    가볍고 JSON 을 그대로 물고 있을 때가 많으며, AMP 는 구조가 규칙적이라 뽑기 쉽다.
    아카이브는 그 쪽이 아예 죽었을 때 마지막으로 남는 길이다.
    """
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return []
    if not p.scheme or not p.netloc:
        return []
    나온것, 본것 = [], {url}

    def 더(u):
        if u and u not in 본것:
            본것.add(u)
            나온것.append(u)

    host, path = p.netloc, p.path or "/"
    q = p.query
    # arXiv: /abs·/pdf 를 HTML(수식 MathML·표·figcaption 이 텍스트로 온다)·ar5iv·TeX 로.
    # PDF 만 긁으면 수식이 글리프로 흩어져 못 살린다. (dig/paper.py 가 더 꼼꼼히 다룬다)
    m = re.search(r"arxiv\.org/(?:abs|pdf|html|e-print)/([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?", url, re.I)
    if m:
        aid = m.group(1)
        더(f"https://arxiv.org/html/{aid}")
        더(f"https://ar5iv.labs.arxiv.org/html/{aid}")
        더(f"https://arxiv.org/abs/{aid}")
    # 모바일 쪽
    if not host.startswith("m."):
        더(urllib.parse.urlunsplit((p.scheme, "m." + host.replace("www.", ""),
                                    path, q, "")))
    # AMP
    if not path.endswith("/amp"):
        더(urllib.parse.urlunsplit((p.scheme, host, path.rstrip("/") + "/amp", q, "")))
    # 그 쪽이 쓰는 JSON 끝점 꼴
    for 붙일 in ("format=json", "output=json", "_format=json"):
        더(urllib.parse.urlunsplit((p.scheme, host, path,
                                    (q + "&" if q else "") + 붙일, "")))
    if not path.endswith(".json"):
        더(urllib.parse.urlunsplit((p.scheme, host, path.rstrip("/") + ".json", q, "")))
    # oEmbed. **표준이다** -- 유튜브· 비메오· 사운드클라우드· 플리커· 틱톡이 다 문다.
    # 제목· 지은이· 길이· 미리보기를 JSON 으로 그냥 준다. 어떤 물음이든 붙으므로
    # 갈래를 안 가리고 두드린다(안 무는 쪽은 404 하나로 끝난다).
    감싼 = urllib.parse.quote(url, safe="")
    oe = "www.youtube.com" if "youtu.be" in host else host
    더(f"{p.scheme}://{oe}/oembed?url={감싼}&format=json")
    # 워드프레스가 쓰는 자리. 이 꼴을 쓰는 쪽이 웹의 큰 몫이다.
    더(f"{p.scheme}://{host}/wp-json/oembed/1.0/embed?url={감싼}")
    # **피드는 본문을 통째로 준다.** 목록 쪽을 열 번 파는 것보다 이 한 번이 낫다 --
    # 글 여러 편의 본문· 날짜· 지은이가 한 판에 온다. 쪽마다 자리가 달라 다 해 본다.
    밑 = path.rstrip("/")
    for 꼬리 in ("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/index.xml"):
        더(urllib.parse.urlunsplit((p.scheme, host, 밑 + 꼬리, "", "")))
    if 밑:
        더(urllib.parse.urlunsplit((p.scheme, host, "/feed", "", "")))
    나온것 += 영상곁문(url, p)
    # 공개 아카이브 -- 그 쪽이 죽었을 때
    더("https://web.archive.org/web/2/" + url)
    # http <-> https
    더(urllib.parse.urlunsplit((("http" if p.scheme == "https" else "https"),
                                host, path, q, "")))
    return 나온것


def 여럿(urls, 동시: int = 8, 틈: float = 기본틈, 벌수: int = 0) -> list:
    """**한꺼번에 받는다.** 하나씩 받으면 열 곳이 열 배 걸리고, 그러면 결국 한두 곳만
    보게 된다 -- 적게 모으는 쪽으로 저절로 기운다. 그래서 병렬이 규율이다.

    하나가 터져도 나머지는 온다. 순서는 준 대로 지킨다.
    """
    urls = [u for u in urls if u]
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(동시, len(urls)))) as ex:
        return list(ex.map(lambda u: 받기(u, 틈, 벌수), urls))


def 캐기(url: str, 곁문까지: bool = True, 틈: float = 기본틈) -> list:
    """한 주소를 **될 때까지** 판다. 앞문 -> 안 되면 곁문 전부 -> 받은 것 다 준다.

    앞문이 되어도 곁문을 볼 이유가 있다 -- **다른 문이 다른 것을 준다.** 모바일 쪽에
    가격이 있고 데스크톱 쪽에 리뷰가 있는 일이 흔하다. 그래서 기본이 '둘 다' 다.
    """
    첫 = 받기(url, 틈)
    나온것 = [첫]
    if not 곁문까지:
        return 나온것
    나온것 += [r for r in 여럿(곁문(url), 틈=틈, 벌수=1) if r.됐나 or r.코드]
    return 나온것
