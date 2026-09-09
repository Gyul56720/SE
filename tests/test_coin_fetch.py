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

print()
print(f"실패 {len(fails)}개" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
