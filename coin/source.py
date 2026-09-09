"""**출처는 코드가 아니라 선언이다.** 그리고 이 표의 요점은 개수가 아니라 **나라**다.

`brief/source.py` 와 같은 자리다. 다른 것은 칸이 둘 늘었다는 것 -- `나라` 와 `말`.

## 왜 나라가 칸인가 -- 영어만 모으면 사건 연구가 **거꾸로** 잰다

암호화폐 시장은 24시간이고 사건은 아시아에서 먼저 난다. 실제로 값을 제일 크게
움직인 사건들이 그랬다:

    2017-09  중국 ICO 금지          공고는 중국어. 영어 기사는 그 뒤
    2021-05  중국 채굴 금지          国务院 금융안정위 발표. 영어는 몇 시간 뒤
    2018-01  코인체크 유출           일본어 회견이 먼저
    2014-02  마운트곡스              일본
    2023-06  SEC 소송                이건 영어가 원문이다

여기서 갈린다. **영어 기사 시각으로 D0 를 잡으면 그 움직임은 이미 끝나 있다.**
그러면 잰 값은 "사건 뒤의 수익률" 이 아니라 "이미 빠진 뒤의 되돌림" 이다. 신호가
약하게 나오는 정도가 아니라 **부호가 뒤집힌 가짜 신호**가 나온다. 원문을 안 모으면
이 오류는 원장 어디에도 안 남는다 -- 잰 값만 남고 왜 틀렸는지는 안 남는다.

그래서 이 파이프라인은 같은 사건의 여러 나라 기사를 **뭉쳐서 제일 이른 시각**을
D0 로 쓴다(`news.py` 의 `뭉치기`). 그러려면 애초에 여러 나라를 받아야 한다.

## 이 표의 `확인` 칸이 비어 있는 것에 대하여

**여기(에이전트 컨테이너)에서는 이 주소들이 한 개도 안 열린다.** 프록시가 CONNECT
단계에서 403 을 준다(실측 2026-09-09: api.binance.com · api.coingecko.com ·
cryptopanic.com · www.coindesk.com 넷 다). 그래서 `확인` 은 **전부 비어 있다** --
확인된 적이 없다는 뜻이고, 그것이 사실이다.

VM 에서 한 번 돌려서 채워라:

    python3 coin/news.py --탐침            # 어느 출처가 실제로 답하나
    python3 coin/news.py --탐침 --기록     # 답한 것을 이 표에 적어 준다

**확인 안 된 출처를 확인된 것처럼 세지 않는다.** `쓸수있나()` 가 그 자리다.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Source:
    이름: str
    나라: str                      # US · CN · JP · KR · XX(다국적)
    말: str                        # en · zh · ja · ko · mul
    url: str
    층: str = "매체"               # 규제 · 거시 · 사법 · 거래소 · 발행사 · 매체 · 집계
    꼴: str = "rss"                # rss · json · gdelt
    설명: str = ""
    열쇠: str = ""                 # 필요한 환경변수. 비면 필요 없다
    과거: bool = False             # **과거를 캘 수 있나** -- RSS 는 못 판다
    경로: str = ""                 # json 일 때 글 목록이 있는 자리
    확인: str = ""                 # 언제 실제로 도는 것을 봤나. 비면 **본 적 없다**
    무게: float = 1.0              # 같은 사건이 겹칠 때 어느 시각을 믿나 (원문 우선)
    # **주소는 썩는다 -- 그래서 찾을 거리를 같이 둔다.**
    #
    # 실측 2026-09-09: 손으로 적은 104개 중 열여덟이 404 였고, 고쳐서 다시 재니 또 몇이
    # 죽었다. 주소를 손으로 적는 한 이 되돌이는 안 끝난다 -- 그 쪽이 개편하면 또 죽고,
    # 죽은 줄 알려면 사람이 탐침을 봐야 한다.
    #
    # 그런데 **아무 주소나 받을 수도 없다.** 검색이 물어온 것을 그대로 쓰면 아무 데서
    # 온 글이 사건 원장에 들어가고, 그러면 D0 를 정하는 시각을 아무도 검사 안 한 곳이
    # 정하게 된다. 그래서 가른다:
    #
    #     집(도메인)  **선언한다.** sec.gov 가 아니면 SEC 출처가 아니다.
    #                 도메인은 경로와 달리 잘 안 바뀌므로 손으로 적을 값어치가 있다
    #     경로        **찾는다.** dig/search 로 찾고 두드려서 글이 나오는 것만 쓴다
    #                 (`coin/locate.py`). 자주 바뀌므로 손으로 적을 값어치가 없다
    #
    # 둘 다 안 적으면 지금 `url` 에서 뽑아 쓴다 -- 백 곳에 손으로 또 적지 않는다.
    찾는말: str = ""               # 무엇으로 찾나. 비면 이름·층·설명에서 짓는다
    집: str = ""                   # 어느 도메인이어야 하나. 비면 url 에서 뽑는다

    def 쓸수있나(self) -> tuple:
        if self.열쇠 and not os.environ.get(self.열쇠):
            return False, f"{self.열쇠} 가 없다"
        return True, ""


# ---------------------------------------------------------------- 과거를 캐는 자리
# **여기가 이 파이프라인의 목숨이다.** RSS 는 최근 것만 준다(대개 24~72시간). 사건
# 연구는 몇 년치 뉴스가 있어야 성립하는데, 그것을 공짜로 여러 나라 말로 주는 곳은
# 사실상 GDELT 하나다 -- 2017년부터, 100개 넘는 말, 나라·말로 거를 수 있다.
#
# 한 번 물으면 250건까지만 준다. 그래서 `news.py` 가 시간을 잘라 가며 여러 번 묻는다.
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

# ============================================================ 층
# **빈틈은 개수로 안 보이고 격자로 보인다.** 매체를 스무 곳 붙여 놓고 규제 원문이
# 하나도 없으면 그것이 빈틈인데, 목록만 보면 "서른 곳이나 된다" 로 보인다. 그래서
# 출처마다 `층` 을 달고 `빈틈()` 이 (나라 x 층) 격자의 빈 칸을 짚는다.
#
#   규제    감독기관 원문. 사건의 **원문**이고 시각이 정확하다
#   거시    중앙은행 · 통계. 암호화폐가 제일 크게 반응하는 예정된 사건
#   사법    기소 · 소송 · 판결 · 압수. 규제와 다른 층인 까닭은 **시점이 다르기 때문**이다 --
#           규제는 규칙이 바뀌는 순간이고 사법은 이미 있는 규칙이 사람에게 닿는 순간이다.
#           둘을 한 칸에 넣으면 "기소 뒤 D+7" 과 "규칙 변경 뒤 D+7" 이 섞여 둘 다 흐려진다
#   거래소  상장 · 폐지 · 유의 · 출금중단. **알트를 제일 크게 움직인다**
#   발행사  스테이블코인 발행/소각 · 기관 보유
#   매체    기사. 위의 것들을 **재보도**하므로 시각이 늦다
#   집계    여러 곳을 모아 주는 곳
#
# 매체를 무게 0.6 으로 두는 까닭이 이것이다 -- 같은 사건에서 원문과 기사가 겹치면
# `news.뭉치기` 는 **제일 이른 시각**을 쓰는데, 그것이 대개 원문이다.
층들 = ("규제", "거시", "사법", "거래소", "발행사", "매체", "집계")
나라들 = ("US", "EU", "KR", "CN", "JP")

목록 = [
    # ======================================================= 과거를 캐는 자리
    # 사건 연구의 밑감. RSS 는 과거를 못 판다 -- 몇 년치를 여러 나라 말로 공짜로 주는
    # 곳은 사실상 GDELT 하나다.
    Source("gdelt-en", "US", "en", GDELT, "집계", "gdelt", 과거=True, 무게=0.6,
           설명="GDELT 영어. 2017~"),
    Source("gdelt-zh", "CN", "zh", GDELT, "집계", "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 중국어(sourcelang:chi)"),
    Source("gdelt-ja", "JP", "ja", GDELT, "집계", "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 일본어(sourcelang:jpn)"),
    Source("gdelt-ko", "KR", "ko", GDELT, "집계", "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 한국어(sourcelang:kor)"),
    Source("gdelt-de", "EU", "de", GDELT, "집계", "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 독일어(sourcelang:ger)"),
    Source("gdelt-fr", "EU", "fr", GDELT, "집계", "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 프랑스어(sourcelang:fre)"),

    # ======================================================= 미국 -- 제일 두껍게
    # **여기가 제일 중요하다.** 2020년 이후 비트코인을 제일 크게 움직인 사건은
    # 거의 다 미국 규제·거시였다(ETF 승인 · SEC 소송 · CPI · FOMC · 은행 접근).
    # 그리고 미국은 **원문이 공개돼 있고 시각이 정확하다** -- 기사를 기다릴 이유가 없다.

    # ---- 규제 (원문) ----
    Source("sec-press", "US", "en", "https://www.sec.gov/news/pressreleases.rss",
           "규제", "rss", 무게=1.5, 설명="SEC 보도자료"),
    Source("sec-lit", "US", "en", "https://www.sec.gov/rss/litigation/litreleases.xml",
           "규제", "rss", 무게=1.5, 설명="SEC 소송 릴리스 -- 제재의 원문"),
    Source("sec-admin", "US", "en",
           "https://www.sec.gov/rss/litigation/admin.xml", "규제", "rss", 무게=1.4,
           설명="SEC 행정처분"),
    # **EDGAR 가 이 목록에서 제일 값진 한 줄일 수 있다.** ETF 는 19b-4 와 S-1 이
    # 올라오는 순간이 사건이고, 기사는 그 뒤다. 기관 매입(8-K)도 여기서 먼저 보인다.
    Source("edgar-19b4", "US", "en",
           "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=19b-4"
           "&company=&dateb=&owner=include&count=100&action=getcurrent&output=atom",
           "규제", "rss", 무게=1.6,
           설명="EDGAR 19b-4 -- **ETF 규칙변경 신청. 기사보다 먼저다**"),
    Source("edgar-s1", "US", "en",
           "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1"
           "&dateb=&owner=include&count=40&output=atom", "규제", "rss", 무게=1.4,
           설명="EDGAR S-1"),
    Source("edgar-8k", "US", "en",
           "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K"
           "&dateb=&owner=include&count=40&output=atom", "규제", "rss", 무게=1.2,
           설명="EDGAR 8-K -- 기관 매입 공시가 여기로 온다"),
    Source("sec-suspend", "US", "en",
           "https://www.sec.gov/litigation/suspensions.htm", "규제", "html", 무게=1.4,
           설명="거래정지"),
    Source("cftc", "US", "en", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml",
           "규제", "rss", 무게=1.5),
    Source("cftc-enf", "US", "en", "https://www.cftc.gov/RSS/RSSENF/rssenf.xml",
           "규제", "rss", 무게=1.5, 설명="CFTC 제재"),
    Source("ofac", "US", "en",
           "https://ofac.treasury.gov/recent-actions",
           "규제", "html", 무게=1.6,
           설명="**OFAC 제재 -- 특정 코인·주소를 즉시 움직인다**(토네이도캐시)"),
    Source("fincen", "US", "en", "https://www.fincen.gov/news",
           "규제", "rss", 무게=1.3),
    Source("occ", "US", "en", "https://www.occ.gov/rss/occ_bulletins.xml",
           "규제", "rss", 무게=1.2, 설명="은행이 코인을 만질 수 있나"),
    Source("fdic", "US", "en", "https://www.fdic.gov/news/press-releases",
           "규제", "rss", 무게=1.2, 설명="은행 접근 -- 실버게이트·시그니처가 이 층이었다"),
    Source("whitehouse", "US", "en",
           "https://www.whitehouse.gov/presidential-actions/feed/", "규제", "rss",
           무게=1.4, 설명="디지털자산 행정명령"),

    # ---- 사법 ----
    Source("doj", "US", "en", "https://www.justice.gov/news/rss?type=press_release",
           "사법", "rss", 무게=1.5, 설명="기소 -- CZ · SBF 가 이 층이었다"),
    Source("doj-usao", "US", "en",
           "https://www.justice.gov/usao-sdny/news", "사법", "html",
           무게=1.4, 설명="**뉴욕 남부지검 -- 암호화폐 형사사건이 거의 다 여기서 난다**"),
    # CourtListener 는 연방법원 문서를 무료 API 로 준다. 리플·SEC 같은 사건은
    # **판결문이 올라오는 순간**이 사건이고 기사는 몇 시간 뒤다.
    Source("courtlistener", "US", "en",
           "https://www.courtlistener.com/api/rest/v4/search/"
           "?q=cryptocurrency+OR+bitcoin&type=r&order_by=dateFiled+desc",
           "사법", "json", 경로="results", 무게=1.5,
           설명="연방법원 문서. 열쇠 없이도 제한적으로 된다"),

    # ---- 거시 ----
    Source("fed-monetary", "US", "en",
           "https://www.federalreserve.gov/feeds/press_monetary.xml", "거시", "rss",
           무게=1.6, 설명="FOMC -- 예정된 사건 중 제일 크게 움직인다"),
    Source("fed-speeches", "US", "en",
           "https://www.federalreserve.gov/feeds/speeches.xml", "거시", "rss", 무게=1.3),
    Source("fed-all", "US", "en",
           "https://www.federalreserve.gov/feeds/press_all.xml", "거시", "rss", 무게=1.2),
    Source("bls", "US", "en", "https://www.bls.gov/feed/bls_latest.rss", "거시", "rss",
           무게=1.6, 설명="**CPI · 고용 -- 발표 순간이 사건이다**"),
    Source("treasury", "US", "en",
           "https://home.treasury.gov/system/files/126/press_releases.xml",
           "거시", "rss", 무게=1.3),

    # ---- 거래소 · 발행사 ----
    Source("coinbase-blog", "US", "en", "https://www.coinbase.com/blog/rss.xml",
           "거래소", "rss", 무게=1.3, 설명="상장 발표"),
    Source("coinbase-status", "US", "en", "https://status.coinbase.com/history.rss",
           "거래소", "rss", 무게=1.1, 설명="장애 · 출금중단"),
    Source("binance-ann", "XX", "en",
           "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
           "?type=1&pageNo=1&pageSize=50", "거래소", "json",
           경로="data", 무게=1.5,
           설명="**바이낸스 공지 -- 상장/폐지가 알트를 20~50% 움직인다**"),
    Source("okx-ann", "XX", "en",
           "https://www.okx.com/help/section/announcements-latest-announcements",
           "거래소", "html", 무게=1.2),
    Source("farside-etf", "US", "en", "https://farside.co.uk/btc/", "발행사", "html",
           무게=1.4, 설명="**현물 ETF 일별 유입/유출** -- 표를 dig 가 뽑는다"),
    Source("tether", "XX", "en", "https://tether.to/en/news/feed/", "발행사", "rss",
           무게=1.2, 설명="USDT 발행/소각"),
    Source("circle", "US", "en", "https://www.circle.com/blog", "발행사", "html",
           무게=1.2, 설명="USDC"),

    # ---- 매체 ----
    Source("coindesk", "US", "en", "https://www.coindesk.com/arc/outboundfeeds/rss/",
           "매체", "rss", 무게=0.6),
    Source("theblock", "US", "en", "https://www.theblock.co/rss.xml", "매체", "rss",
           무게=0.6),
    Source("decrypt", "US", "en", "https://decrypt.co/feed", "매체", "rss", 무게=0.6),
    Source("blockworks", "US", "en", "https://blockworks.co/feed", "매체", "rss",
           무게=0.6),
    Source("cointelegraph", "XX", "en", "https://cointelegraph.com/rss", "매체", "rss",
           무게=0.6),
    Source("bitcoinmag", "US", "en", "https://bitcoinmagazine.com/feed", "매체", "rss",
           무게=0.5),
    Source("cnbc-fin", "US", "en",
           "https://search.cnbc.com/rs/search/combinedcms/view.xml"
           "?partnerId=wrss25&id=10000664", "매체", "rss", 무게=0.6),
    Source("reuters-biz", "US", "en", "https://www.reuters.com/markets/cryptocurrency/", "매체", "html", 무게=0.6),

    # ======================================================= 유럽 (EU + 영국)
    # **미국 다음으로 규칙이 실제로 바뀌는 자리다.** MiCA 가 전면 시행되면서 상장·
    # 스테이블코인·수탁의 문턱이 여기서 정해지고, 유럽 발행사가 그 문턱에 맞춰 코인을
    # 빼거나 넣는다(USDT 상장폐지가 그랬다). ECB 는 FOMC 다음으로 크게 움직인다.
    #
    # 유럽 기관은 대부분 **영어로도 낸다** -- 그래서 말이 en 이다. 다만 매체는 독일어·
    # 프랑스어라 `tag.py` 에 de·fr 낱말을 같이 넣었다. 안 넣으면 그 나라 글이
    # 들어와도 꼬리표가 하나도 안 걸려 **조용히 0건이 된다.**
    Source("esma", "EU", "en", "https://www.esma.europa.eu/rss.xml", "규제", "rss",
           무게=1.5, 설명="**ESMA -- MiCA 의 집행 창구**"),
    Source("eba", "EU", "en", "https://www.eba.europa.eu/rss.xml", "규제", "rss",
           무게=1.3, 설명="EBA -- 스테이블코인(ART/EMT) 규칙"),
    Source("eu-commission", "EU", "en",
           "https://ec.europa.eu/commission/presscorner/api/rss?language=en",
           "규제", "rss", 무게=1.2),
    Source("fca", "EU", "en", "https://www.fca.org.uk/news/rss.xml", "규제", "rss",
           무게=1.5, 설명="**영국 FCA -- 등록·광고 규제. 영국은 EU 밖이지만 같은 층**"),
    Source("bafin", "EU", "de", "https://www.bafin.de/DE/Aufsicht/FinTech/Kryptoverwahrgeschaeft/"
           "kryptoverwahrgeschaeft_node.html", "규제", "html", 무게=1.2,
           설명="독일 BaFin"),
    Source("amf-fr", "EU", "fr", "https://www.amf-france.org/fr/actualites-publications/actualites", "규제", "html",
           무게=1.2, 설명="프랑스 AMF -- PSAN 등록"),
    Source("ecb", "EU", "en", "https://www.ecb.europa.eu/rss/press.html", "거시", "rss",
           무게=1.5, 설명="**ECB -- FOMC 다음으로 크게 움직인다**"),
    Source("boe", "EU", "en", "https://www.bankofengland.co.uk/rss/news", "거시", "rss",
           무게=1.3, 설명="영란은행"),
    Source("eurostat", "EU", "en",
           "https://ec.europa.eu/eurostat/web/main/news/euro-indicators", "거시",
           "html", 무게=1.1, 설명="HICP 물가"),
    Source("curia", "EU", "en",
           "https://curia.europa.eu/jcms/jcms/Jo2_7052/en/", "사법", "html", 무게=1.1,
           설명="EU 사법재판소"),
    Source("europol", "EU", "en", "https://www.europol.europa.eu/media-press/newsroom",
           "사법", "html", 무게=1.3, 설명="**유로폴 -- 압수·다크마켓 폐쇄가 여기서 난다**"),
    Source("bitstamp", "EU", "en", "https://www.bitstamp.net/newsroom/", "거래소", "html",
           무게=1.1),
    Source("kraken-status", "EU", "en", "https://status.kraken.com/history.rss",
           "거래소", "rss", 무게=1.1),
    Source("btc-echo", "EU", "de", "https://www.btc-echo.de/feed/", "매체", "rss",
           무게=1.0, 설명="독일어 매체"),
    Source("journalducoin", "EU", "fr", "https://journalducoin.com/feed/", "매체", "rss",
           무게=1.0, 설명="프랑스어 매체"),
    Source("beincrypto", "EU", "en", "https://beincrypto.com/feed/", "매체", "rss",
           무게=0.7),

    # ======================================================= 한국
    Source("fsc", "KR", "ko", "https://www.fsc.go.kr/rss/no010101.xml", "규제", "rss",
           무게=1.5, 설명="금융위원회 보도자료"),
    Source("fss", "KR", "ko", "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218",
           "규제", "html", 무게=1.4, 설명="금융감독원"),
    Source("bok", "KR", "ko", "https://www.bok.or.kr/portal/bbs/B0000338/list.do?menuNo=200761",
           "거시", "html", 무게=1.3, 설명="한국은행 -- 기준금리"),
    Source("moef", "KR", "ko", "https://www.moef.go.kr/com/bbs/rss.do?bbsId=MOSFBBS_000000000028",
           "규제", "rss", 무게=1.2, 설명="기획재정부 -- 과세"),
    # **업비트 공지는 원화 시장에서 제일 센 한 줄이다.** 상장은 급등, 유의종목 지정은
    # 급락. 기사는 늘 그 뒤다.
    Source("upbit-notice", "KR", "ko",
           "https://api-manager.upbit.com/api/v1/announcements"
           "?os=web&page=1&per_page=30&category=all", "거래소", "json",
           경로="data", 무게=1.6,
           설명="**업비트 공지 -- 상장·유의종목. 원화 시장을 제일 크게 움직인다**"),
    Source("bithumb-notice", "KR", "ko",
           "https://feed.bithumb.com/notice", "거래소", "html", 무게=1.4),
    Source("daxa", "KR", "ko", "https://www.daxa.or.kr/",
           "거래소", "html", 무게=1.3, 설명="DAXA 공동 유의종목 지정"),
    Source("spo-kr", "KR", "ko",
           "https://www.spo.go.kr/site/spo/ex/board/List.do?cbIdx=1204", "사법", "html",
           무게=1.3, 설명="대검찰청 -- 가상자산 수사·압수"),
    Source("scourt-kr", "KR", "ko",
           "https://www.scourt.go.kr/portal/news/NewsListAction.work?gubun=42",
           "사법", "html", 무게=1.1, 설명="대법원 보도자료"),
    Source("coindeskkr", "KR", "ko", "https://www.coindeskkorea.com/rss/allArticle.xml",
           "매체", "rss", 무게=1.0),
    Source("blockmedia", "KR", "ko", "https://www.blockmedia.co.kr/feed", "매체", "rss",
           무게=1.0),
    Source("tokenpost", "KR", "ko", "https://www.tokenpost.kr/rss", "매체", "rss",
           무게=1.0),
    Source("decenter", "KR", "ko", "https://decenter.sedaily.com/", "매체",
           "html", 무게=1.0),

    # ======================================================= 중국 (+홍콩)
    Source("pboc", "CN", "zh", "http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", "규제", "html",
           무게=1.5, 설명="중국인민은행 -- 2021 채굴 금지가 이 계열"),
    Source("csrc", "CN", "zh", "http://www.csrc.gov.cn/csrc/xwfb/index.shtml",
           "규제", "html", 무게=1.3, 설명="증감회"),
    Source("ndrc", "CN", "zh", "https://www.ndrc.gov.cn/xwdt/xwfb/", "규제", "html",
           무게=1.3, 설명="발개위 -- 채굴 정책이 여기서 나온다"),
    Source("cac", "CN", "zh", "http://www.cac.gov.cn/xxfb/A0901index_1.htm", "규제", "html",
           무게=1.2, 설명="망신판"),
    # **홍콩이 지금 중국의 실제 정책 창구다.** 대륙이 막은 뒤 라이선스·현물 ETF가
    # 여기서 나왔는데, 중국 항목만 보면 통째로 놓친다.
    Source("hk-sfc", "CN", "en", "https://www.sfc.hk/en/News-and-announcements/Policy-statements-and-announcements",
           "규제", "html", 무게=1.5,
           설명="**홍콩 SFC -- 대륙이 막은 뒤 정책은 여기서 나온다**"),
    Source("hkma", "CN", "en", "https://www.hkma.gov.hk/eng/news-and-media/press-releases/",
           "규제", "html", 무게=1.3),
    # 격자가 짚어 준 빈칸: 중국 거시
    Source("stats-cn", "CN", "zh", "https://www.stats.gov.cn/sj/zxfb/", "거시", "html",
           무게=1.2, 설명="국가통계국 -- CPI · GDP"),
    Source("mof-cn", "CN", "zh", "http://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/",
           "거시", "html", 무게=1.1, 설명="재정부"),
    Source("court-cn", "CN", "zh", "https://www.court.gov.cn/zixun.html", "사법",
           "html", 무게=1.2, 설명="최고인민법원 -- 가상화폐 판결"),
    Source("spp-cn", "CN", "zh", "https://www.spp.gov.cn/xwfbh/", "사법", "html",
           무게=1.1, 설명="최고인민검찰원"),
    Source("jinse", "CN", "zh", "https://www.jinse.cn/lives", "매체", "html",
           무게=1.1, 설명="金色财经"),
    Source("8btc", "CN", "zh", "https://www.8btc.com/", "매체", "html", 무게=1.1),
    Source("panews", "CN", "zh", "https://www.panewslab.com/zh/rss", "매체", "rss",
           무게=1.1),
    Source("odaily", "CN", "zh", "https://www.odaily.news/newsflash", "매체", "html", 무게=1.1),
    Source("blockbeats", "CN", "zh", "https://www.theblockbeats.info/newsflash",
           "매체", "html", 무게=1.2, 설명="律动 -- 속보가 빠르다"),
    Source("chaincatcher", "CN", "zh", "https://www.chaincatcher.com/news", "매체",
           "html", 무게=1.1),
    Source("techflow", "CN", "zh", "https://www.techflowpost.com/newsletter/index.html",
           "매체", "html", 무게=1.1, 설명="深潮"),
    Source("cls", "CN", "zh", "https://www.cls.cn/telegraph", "매체", "html", 무게=1.2,
           설명="财联社 전보 -- 규제 소식이 제일 빨리 뜨는 쪽"),
    Source("wublock", "CN", "zh", "https://wublock123.com/feed", "매체", "rss", 무게=1.1,
           설명="吴说 -- 대륙 소식통"),

    # ======================================================= 일본
    Source("fsa", "JP", "ja", "https://www.fsa.go.jp/news/index.html", "규제", "html",
           무게=1.5, 설명="금융청 -- 코인체크 뒤 행정처분이 여기"),
    Source("kanto-zaimu", "JP", "ja",
           "https://lfb.mof.go.jp/kantou/kinyuu/index.html", "규제", "html", 무게=1.2,
           설명="관동재무국 -- 실제 행정처분이 나오는 자리"),
    Source("boj", "JP", "ja", "https://www.boj.or.jp/rss/whatsnew.xml", "거시", "rss",
           무게=1.4, 설명="일본은행 -- 엔 캐리가 풀릴 때 코인이 같이 빠진다"),
    Source("jvcea", "JP", "ja", "https://jvcea.or.jp/news/", "규제", "html", 무게=1.2,
           설명="일본암호자산거래업협회"),
    Source("bitflyer-ann", "JP", "ja", "https://bitflyer.com/ja-jp/news", "거래소",
           "html", 무게=1.2),
    Source("bitbank-ann", "JP", "ja", "https://bitbank.cc/news", "거래소", "html",
           무게=1.1),
    Source("npa-jp", "JP", "ja", "https://www.npa.go.jp/news/index.html", "사법",
           "html", 무게=1.2, 설명="경찰청 -- 거래소 유출 수사"),
    Source("courts-jp", "JP", "ja", "https://www.courts.go.jp/news/index.html", "사법",
           "html", 무게=1.0),
    Source("coinpost", "JP", "ja", "https://coinpost.jp/?feed=rss2", "매체", "rss",
           무게=1.1),
    Source("neweconomy", "JP", "ja", "https://www.neweconomy.jp/feed", "매체", "rss",
           무게=1.1, 설명="あたらしい経済"),
    Source("coindeskjp", "JP", "ja", "https://www.coindeskjapan.com/feed/", "매체",
           "rss", 무게=1.0),
    Source("bittimes", "JP", "ja", "https://bittimes.net/feed", "매체", "rss", 무게=1.0),

    # ======================================================= 집계 (열쇠가 있으면)
    Source("cryptopanic", "XX", "mul",
           "https://cryptopanic.com/api/v1/posts/?auth_token={key}&public=true",
           "집계", "json", 경로="results", 열쇠="CRYPTOPANIC_TOKEN", 무게=0.5,
           설명="집계기 -- 원문이 아니라 재보도라 무게가 낮다"),
]

표 = {s.이름: s for s in 목록}


def get(이름: str):
    return 표.get(이름)


def 나라별() -> dict:
    out = {}
    for s in 목록:
        out.setdefault(s.나라, []).append(s.이름)
    return out


# **어느 나라만 볼 것인가.** 환경변수로도 준다 -- 셸에서 한 번 걸어 두면 아래 모든
# 명령이 따라간다. 비면 전부.
#
#     COIN_COUNTRY=US python3 coin/run.py --채우기
#     python3 coin/news.py --탐침 --나라 US
#
# `XX` 는 나라에 안 매인 것이다(바이낸스 · 테더 · 코인텔레그래프 · GDELT 아님).
# `--나라 US` 는 **US 만** 이고, 그것들까지 보려면 `--나라 US,XX` 다.
def 집뽑기(url: str) -> str:
    return (url or "").split("//", 1)[-1].split("/", 1)[0].split("?", 1)[0].lower()


def 집이름(s) -> str:
    """이 출처가 어느 집이어야 하나. **여기를 못 넘으면 그 주소는 이 출처가 아니다.**"""
    return (s.집 or 집뽑기(s.url)).lower()


def 찾을말(s) -> str:
    """무엇으로 찾을 것인가. 안 적었으면 이미 적힌 것에서 짓는다 -- 또 손으로 안 적는다."""
    if s.찾는말:
        return s.찾는말
    집 = 집이름(s).replace("www.", "")
    꼬리 = {"규제": "press releases", "거시": "press releases", "사법": "news",
            "거래소": "announcements", "발행사": "news",
            "매체": "news"}.get(s.층, "news")
    말 = (s.설명 or "").split("--")[0].replace("*", "").strip()
    return " ".join(x for x in (집, 말, 꼬리) if x)


def 기본나라() -> tuple:
    v = os.environ.get("COIN_COUNTRY", "").strip()
    return tuple(x.strip().upper() for x in v.split(",") if x.strip()) if v else ()


def 고르기(나라=None) -> tuple:
    """문자열('US,XX')이든 튜플이든 받아 튜플로. 안 주면 환경변수, 그것도 없으면 전부."""
    if 나라 is None:
        return 기본나라()
    if isinstance(나라, str):
        return tuple(x.strip().upper() for x in 나라.split(",") if x.strip())
    return tuple(str(x).upper() for x in 나라)


def 쓸수있는것(과거만: bool = False, 나라=None) -> list:
    골 = 고르기(나라)
    out = []
    for s in 목록:
        if 과거만 and not s.과거:
            continue
        if 골 and s.나라 not in 골:
            continue
        ok, _ = s.쓸수있나()
        if ok:
            out.append(s)
    return out


def 격자(확인된것만: bool = False) -> dict:
    """(나라, 층) -> 출처 이름들. **빈틈을 보는 자리.**"""
    확 = {s.이름 for s in 확인된것()} if 확인된것만 else None
    out = {}
    for s in 목록:
        if 확 is not None and s.이름 not in 확:
            continue
        나라 = s.나라 if s.나라 in 나라들 else "XX"
        out.setdefault((나라, s.층), []).append(s.이름)
    return out


def 빈틈(확인된것만: bool = False) -> list:
    """**어느 칸이 비었나.** 목록이 길어도 빈 칸이 있으면 그 층은 안 보는 것이다.

    `집계` 와 `발행사` 는 나라에 안 매이므로 빼고 본다 -- 미국에 발행사가 있으면
    USDT/USDC 는 어느 나라에서 물어도 보인다.
    """
    g = 격자(확인된것만)
    핵심 = ("규제", "거시", "사법", "거래소", "매체")
    return [(나라, 층) for 나라 in 나라들 for 층 in 핵심
            if not g.get((나라, 층)) and not g.get(("XX", 층))]


# 탐침이 적어 두는 자리. **`확인` 칸은 코드가 아니라 여기서 온다** -- 어느 문이
# 열리는지는 기계마다 다르고(프록시 · 나라 · 시각), 코드에 박으면 남의 기계의
# 어제 결과를 내 기계의 오늘 사실로 말하게 된다.
탐침길 = Path(__file__).resolve().parent / "corpus/probe.json"


def 탐침기록(재것: list, 경로=None) -> Path:
    """`news.py --탐침 --기록` 이 부른다. 답한 것만 적는다."""
    탐침길 = Path(경로) if 경로 else globals()["탐침길"]
    본 = {}
    if 탐침길.exists():
        본 = json.loads(탐침길.read_text(encoding="utf-8")).get("본것", {})
    때 = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for x in 재것:
        본[x["이름"]] = {"산것": x["산것"], "왜": x.get("왜", ""), "때": 때}
    탐침길.parent.mkdir(parents=True, exist_ok=True)
    탐침길.write_text(json.dumps({"본것": 본}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return 탐침길


def 탐침본것(경로=None) -> dict:
    p = Path(경로) if 경로 else 탐침길
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("본것", {})


def 확인된것() -> list:
    """**실제로 도는 것을 본 출처만.** 비어 있으면 아직 아무도 안 봤다는 뜻이다.

    표의 `확인` 칸이든 탐침 기록이든, **글이 실제로 온 것**만 센다.
    """
    본 = 탐침본것()
    return [s for s in 목록
            if s.확인 or (본.get(s.이름, {}).get("산것", 0) > 0)]
