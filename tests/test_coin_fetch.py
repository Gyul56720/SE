"""**받아 온 것을 실제로 읽는가** -- 피드 꼴 · 날짜 표기 · json 모양.

    python3 tests/test_coin_fetch.py

## 왜 이 파일이 뒤늦게 생겼나

VM 탐침(2026-09-09)에서 104곳 중 46곳만 답했는데, **못한 것의 절반이 막힌 것도 빈
것도 아니었다** -- "답은 왔는데 글이 0개" 였다. 받기는 됐고 **읽기가 안 됐다.**

    연준 · SEC 소송 · OCC ...   RSS 1.0(RDF)라 `item` 이 네임스페이스 안에 있었다
    피드 스무 곳 남짓            날짜가 "... 12:00:00 GMT" 인데 `%z` 는 이름을 안 받는다
    바이낸스                     `data` 아래가 목록이 아니라 dict 라 `.get` 에서 터졌다

셋 다 **내 검사를 통과했다.** `_rss` 를 진짜 피드 꼴로 한 번도 안 돌려 봤기 때문이다 --
뭉치기·사건연구·관문은 다 검사했는데 **그 앞의 한 걸음**이 비어 있었다. 그 사이
사용자는 "출처가 절반밖에 안 산다" 를 봤고, 절반은 출처 탓이 아니라 이 세 줄 탓이었다.

`검사하지 않은 초록불이 검사한 빨간불보다 나쁘다` 가 정확히 이 자리다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import news as NW                                           # noqa: E402
from coin import source as SRC                                        # noqa: E402
from coin.price import _때                                            # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


쪽 = SRC.get("sec-press")

# ---------------------------------------------------------------- 날짜 표기
for 글, 참, 왜 in [
    ("Tue, 09 Sep 2026 12:00:00 GMT", "2026-09-09T12:00:00", "**RFC-822 + 이름 시간대(GMT)**"),
    ("Tue, 09 Sep 2026 12:00:00 EST", "2026-09-09T17:00:00", "이름 시간대(EST) -> UTC"),
    ("Tue, 09 Sep 2026 12:00:00 +0000", "2026-09-09T12:00:00", "숫자 오프셋"),
    ("Mon, 08 Sep 2026 23:00:00 -0400", "2026-09-09T03:00:00", "음수 오프셋"),
    ("2026-09-09T18:00:00Z", "2026-09-09T18:00:00", "ISO"),
    ("2026-09-09 18:00:00", "2026-09-09T18:00:00", "공백 ISO"),
    ("20260909T120000Z", "2026-09-09T12:00:00", "GDELT seendate 꼴"),
]:
    t = _때(글)
    ok(t is not None and t.strftime("%Y-%m-%dT%H:%M:%S") == 참, f"{왜}: {글!r}")
ok(_때("") is None and _때("아무 말") is None, "못 읽는 것은 None -- 지어내지 않는다")

# ---------------------------------------------------------------- 피드 꼴
RSS2 = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>SEC</title>
 <item><title>SEC charges crypto exchange</title><link>https://y/1</link>
 <pubDate>Tue, 09 Sep 2026 12:00:00 GMT</pubDate></item>
 <item><title>Second item</title><link>https://y/2</link>
 <pubDate>Tue, 09 Sep 2026 09:00:00 GMT</pubDate></item></channel></rss>"""
RDF = b"""<?xml version="1.0"?><rdf:RDF
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
 <channel rdf:about="https://fed"><title>Federal Reserve</title></channel>
 <item rdf:about="https://x/1"><title>FOMC statement</title><link>https://x/1</link>
 <dc:date>2026-09-09T18:00:00Z</dc:date></item></rdf:RDF>"""
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
 <entry><title>19b-4 filing for spot ETF</title><link href="https://z/1"/>
 <updated>2026-09-09T10:00:00Z</updated></entry></feed>"""

r2 = NW._rss(RSS2, 쪽)
ok(len(r2) == 2, f"RSS 2.0 을 읽는다 ({len(r2)}건)")
ok(r2 and r2[0]["시각"].startswith("2026-09-09T12:00"), "RSS 2.0 의 GMT 날짜를 읽는다")
ok(r2 and r2[0]["url"] == "https://y/1", "고리를 담는다")

rd = NW._rss(RDF, SRC.get("fed-monetary"))
ok(len(rd) == 1, f"**RSS 1.0(RDF)을 읽는다** -- 연준 계열이 이 꼴 ({len(rd)}건)")
ok(rd and rd[0]["제목"] == "FOMC statement", "RDF 의 제목을 읽는다")
ok(rd and rd[0]["시각"].startswith("2026-09-09T18:00"), "RDF 의 dc:date 를 읽는다")

at = NW._rss(ATOM, SRC.get("edgar-19b4"))
ok(len(at) == 1, f"Atom 을 읽는다 -- EDGAR 가 이 꼴 ({len(at)}건)")
ok(at and at[0]["url"] == "https://z/1", "Atom 의 link href 를 읽는다")

ok(NW._rss(b"<html><body>not a feed</body></html>", 쪽) == [], "피드가 아니면 빈손")
ok(NW._rss("깨진 것 <<<".encode("utf-8"), 쪽) == [], "깨진 것에 안 죽는다")

# ---------------------------------------------------------------- json 모양
ok(len(NW._줄찾기({"data": [{"title": "a"}]}, "data")) == 1, "목록을 바로 준 꼴")
ok(len(NW._줄찾기({"data": {"catalogs": [{"title": "BTC 상장"}]}}, "data")) == 1,
   "**dict 속의 목록을 찾는다** -- 바이낸스가 이 꼴이라 터졌었다")
ok(len(NW._줄찾기({"data": ["쓰레기", {"title": "진짜"}]}, "data")) == 1,
   "문자열이 섞여도 안 죽는다 ('str' object has no attribute 'get')")
ok(NW._줄찾기({"data": "글자"}, "data") == [], "목록이 없으면 빈손")
ok(NW._줄찾기([], "") == [] and NW._줄찾기(None, "") == [], "빈 것에 안 죽는다")

# ---------------------------------------------------------------- 시각출처
ok(all(g.get("시각출처") == "feed" for g in r2), "피드에서 온 것은 시각출처가 feed")
HTML = b"""<html><head><meta property="og:title" content="China bans crypto trading">
<meta property="article:published_time" content="2026-09-09T01:00:00+09:00">
<script type="application/ld+json">{"@type":"NewsArticle",
 "headline":"SEC approves spot bitcoin ETF","datePublished":"2026-09-09T02:00:00Z"}
</script></head><body></body></html>"""
h = NW._html(HTML, 쪽, "https://x/")
ok(len(h) >= 1, f"HTML 에서도 글을 뽑는다 ({len(h)}건)")
ok(any(g["시각출처"] == "jsonld" for g in h), "JSON-LD 에서 온 것은 jsonld 로 표시")
ok(all(g["시각출처"] != "feed" for g in h), "**HTML 에서 온 것은 feed 가 아니다**")

# ---------------------------------------------------------------- GDELT 말 후보
ok(len(NW.GDELT_말) == 6 and all(len(v) >= 2 for v in NW.GDELT_말.values()),
   "GDELT 말 표기는 **후보가 여럿**이다 (하나만 박으면 그 표기가 틀렸을 때 0건)")
ok("" in NW.GDELT_말["gdelt-en"], "영어는 말을 안 거는 후보도 둔다")
ok(all(k in NW.GDELT_질의 for k in NW.GDELT_말), "말마다 그 말로 묻는다")

# ---------------------------------------------------------------- 나라 거르개
import os as _os
ok(len(SRC.쓸수있는것(나라="US")) < len(SRC.쓸수있는것()), "--나라 US 가 줄인다")
ok(all(x.나라 == "US" for x in SRC.쓸수있는것(나라="US")), "**US 만 나온다**")
ok({x.나라 for x in SRC.쓸수있는것(나라="US,XX")} <= {"US", "XX"}, "US,XX 는 둘만")
ok(SRC.고르기("us") == ("US",), "소문자도 받는다")
ok(SRC.고르기(None) == SRC.기본나라(), "안 주면 환경변수를 본다")
_옛 = _os.environ.get("COIN_COUNTRY")
_os.environ["COIN_COUNTRY"] = "US"
try:
    ok(SRC.기본나라() == ("US",), "**COIN_COUNTRY 를 읽는다** -- 셸에서 한 번 걸면 다 따라간다")
    ok(all(x.나라 == "US" for x in SRC.쓸수있는것()), "환경변수만으로도 US 만 본다")
finally:
    if _옛 is None:
        _os.environ.pop("COIN_COUNTRY", None)
    else:
        _os.environ["COIN_COUNTRY"] = _옛
ok(len(SRC.쓸수있는것(나라="US")) >= 30, "US 출처가 서른 곳 넘는다")
for 층 in ("규제", "거시", "사법", "거래소", "매체"):
    ok(any(x.층 == 층 for x in SRC.쓸수있는것(나라="US")), f"US 에 {층} 층이 있다")

# ---------------------------------------------------------------- 주소 찾기
# **집은 선언이고 경로는 발견이다.** 손으로 적은 주소는 썩지만(104곳 중 18곳이 404였다)
# 아무 주소나 받으면 아무 데서 온 글이 원장에 들어간다. 그래서 집으로 거른다.
from coin import locate as LC                                         # noqa: E402
import tempfile as _tf2                                               # noqa: E402

_s = SRC.get("sec-press")
ok(SRC.집이름(_s).endswith("sec.gov"), f"집을 url 에서 뽑는다: {SRC.집이름(_s)}")
ok("sec.gov" in SRC.찾을말(_s), "찾을말을 이미 적힌 것에서 짓는다 -- 또 손으로 안 적는다")
ok("*" not in SRC.찾을말(SRC.get("upbit-notice")), "찾을말에 마크업이 안 샌다")
ok(all(SRC.찾을말(x) for x in SRC.목록), "모든 출처에 찾을말이 나온다")
ok(all(SRC.집이름(x) for x in SRC.목록), "모든 출처에 집이 나온다")

_밖 = SRC.집뽑기("https://evil.example.com/sec-press-releases")
ok(_밖 != SRC.집이름(_s), "**다른 집이면 같은 집이 아니다** -- 이것이 첫째 자물쇠다")
ok(SRC.집뽑기("https://www.sec.gov/news/x?a=1") == "www.sec.gov", "집을 경로·물음표 앞까지만")

_옛길 = LC.길
try:
    with _tf2.TemporaryDirectory() as _d:
        LC.길 = Path(_d) / "주소.json"
        ok(LC.지금주소(_s) == _s.url, "찾아 둔 것이 없으면 선언된 주소")
        LC.적기("sec-press", "https://www.sec.gov/찾은것", "찾아서 바꿨다", 12)
        ok(LC.지금주소(_s) == "https://www.sec.gov/찾은것",
           "**찾아 둔 주소가 있으면 그것을 쓴다**")
        ok(LC.찾아둔것()["sec-press"]["건수"] == 12, "몇 건을 냈는지도 남는다 -- 되짚는 자리")
finally:
    LC.길 = _옛길

# ---------------------------------------------------------------- SEC 연락처
# **가짜 연락처를 주는 것은 안 주는 것보다 나쁘다** -- SEC 정책 위반이고, 막히면서
# 이유도 안 남는다. 그리고 저장소가 공개라 진짜를 박으면 스팸 봇이 긁는다.
import os as _os2                                                     # noqa: E402
_옛2 = _os2.environ.get("SEC_CONTACT")
try:
    _os2.environ.pop("SEC_CONTACT", None)
    ok(NW._집머리표() == {}, "**연락처가 없으면 그 머리를 아예 안 보낸다** (가짜 금지)")
    _os2.environ["SEC_CONTACT"] = "aaa@bbb.com"
    _표 = NW._집머리표()
    ok("www.sec.gov" in _표 and "aaa@bbb.com" in _표["www.sec.gov"]["User-Agent"],
       "연락처가 있으면 User-Agent 에 담는다")
    ok("sec.gov" in _표 and "efts.sec.gov" in _표, "EDGAR 쪽도 같은 머리")
finally:
    if _옛2 is None:
        _os2.environ.pop("SEC_CONTACT", None)
    else:
        _os2.environ["SEC_CONTACT"] = _옛2
# **함수 몸통**만 본다 -- 왜 안 박는지 적은 주석에 그 말이 나오는 것은 괜찮다.
# 검사가 이것을 처음에 통째로 grep 해서 자기 설명에 걸렸다.
_소스 = (ROOT / "coin" / "news.py").read_text(encoding="utf-8")
_몸통 = _소스.split("def _집머리표()")[1].split("\ndef ")[0]
ok("example.com" not in _몸통, "**보내는 자리에 가짜 연락처가 없다**")
ok('os.environ.get("SEC_CONTACT"' in _몸통, "부를 때 환경변수를 읽는다")
ok("@" not in _몸통.replace("SEC_CONTACT", ""), "몸통에 박힌 메일이 없다")

# ---------------------------------------------------------------- 직접 부르기
# **`python3 coin/price.py` 로 부르면 sys.path[0] 이 coin/ 이지 현재 폴더가 아니다.**
# 그래서 `from coin import ...` 이 ModuleNotFoundError 로 죽는다. 실측 2026-09-09:
# VM 에서 가격 받기가 여기서 멈췄고, 화면에는 "못 받았다: ModuleNotFoundError" 만
# 남아서 망 문제인지 코드 문제인지 안 갈렸다.
#
# 모듈 안에서 임포트하는 자리(`받기` 안의 `from coin import clock`)는 부르기 전에는
# 안 터지므로, **다른 폴더에서 실제로 돌려 봐야** 잡힌다.
import subprocess as _sp                                              # noqa: E402
import tempfile as _tf3                                              # noqa: E402

_돌릴것 = sorted(p.name for p in (ROOT / "coin").glob("*.py")
                if "__main__" in p.read_text(encoding="utf-8"))
ok(len(_돌릴것) >= 10, f"직접 부를 수 있는 모듈 {len(_돌릴것)}개를 본다")
with _tf3.TemporaryDirectory() as _d3:
    _못 = []
    for _n in _돌릴것:
        _r = _sp.run([sys.executable, str(ROOT / "coin" / _n), "--도움없는인자"],
                     capture_output=True, text=True, cwd=_d3, timeout=60)
        _글 = (_r.stdout + _r.stderr)
        if "No module named 'coin'" in _글:
            _못.append(_n)
    ok(not _못, f"**어느 폴더에서 불러도 임포트가 산다**" + (f" -- 죽는 것: {_못}" if _못 else ""))

# ---------------------------------------------------------------- 진행 · 부분저장
# 실측 2026-09-09 (VM): `--과거` 를 30분 넘게 돌렸는데 로그가 비어 있었다. `--과거` 는
# 다 받은 뒤에야 저장/출력하므로, 도는 동안 죽었는지 살았는지 볼 수 없었다.
# CLAUDE.md 가 "프로세스가 살아 있는 것과 일을 하는 것은 다르다 -- 로그에 줄이 쌓이는지
# 봐라" 라고 한 그 자리인데 안 지켰다.
import contextlib as _ctx2, io as _io2                               # noqa: E402
_s = SRC.get("gdelt-en")
_옛히 = NW._http
try:
    NW._http = lambda url, timeout=25.0: (
        b'{"articles":[{"title":"bitcoin","seendate":"20200101T120000Z","url":"x"}]}')
    _buf = _io2.StringIO()
    with _ctx2.redirect_stderr(_buf):
        _got = NW._gdelt(_s, "2017-01-01", "2019-01-01")
    _조각줄 = [l for l in _buf.getvalue().splitlines() if "조각" in l]
    ok(len(_조각줄) >= 2, f"**GDELT 가 조각마다 진행을 찍는다** ({len(_조각줄)}줄) -- "
       "로그가 안 늘면 죽은 것이라고 볼 수 있다")
    ok(any("여기까지" in l for l in _조각줄), "몇 건 받았는지도 찍는다")
finally:
    NW._http = _옛히

# 부분 저장이 실제로 불리는가
_불린 = []
class _가짜출처:
    이름, 나라, 층, 꼴, 열쇠, 경로 = "가짜", "US", "매체", "gdelt", "", ""
    url = NW.GDELT
    def 쓸수있나(self): return True, ""
_옛히2 = NW._http
try:
    NW._http = lambda url, timeout=25.0: b'{"articles":[]}'
    NW.받기([_가짜출처()], 부터="2020-01-01", 까지="2020-02-01",
            부분저장=lambda 누적: _불린.append(len(누적)))
    ok(len(_불린) >= 1, "**부분저장이 출처마다 불린다** -- 중간에 끊겨도 안 날아간다")
finally:
    NW._http = _옛히2

print()
print(f"실패 {len(fails)}개" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
