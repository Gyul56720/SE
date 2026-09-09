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
from dataclasses import dataclass, field


@dataclass
class Source:
    이름: str
    나라: str                      # US · CN · JP · KR · XX(다국적)
    말: str                        # en · zh · ja · ko · mul
    url: str
    꼴: str = "rss"                # rss · json · gdelt
    설명: str = ""
    열쇠: str = ""                 # 필요한 환경변수. 비면 필요 없다
    과거: bool = False             # **과거를 캘 수 있나** -- RSS 는 못 판다
    경로: str = ""                 # json 일 때 글 목록이 있는 자리
    확인: str = ""                 # 언제 실제로 도는 것을 봤나. 비면 **본 적 없다**
    무게: float = 1.0              # 같은 사건이 겹칠 때 어느 시각을 믿나 (원문 우선)

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

목록 = [
    # ---- 과거를 캐는 것 (사건 연구의 밑감) ----
    Source("gdelt-en", "US", "en", GDELT, "gdelt", 과거=True, 무게=0.6,
           설명="GDELT 영어. 2017~ . 열쇠 없음"),
    Source("gdelt-zh", "CN", "zh", GDELT, "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 중국어(sourcelang:chi). **중국 규제 원문이 여기로 들어온다**"),
    Source("gdelt-ja", "JP", "ja", GDELT, "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 일본어(sourcelang:jpn). 거래소·금융청"),
    Source("gdelt-ko", "KR", "ko", GDELT, "gdelt", 과거=True, 무게=1.0,
           설명="GDELT 한국어(sourcelang:kor)"),

    # ---- 미국 · 영어 ----
    Source("coindesk", "US", "en", "https://www.coindesk.com/arc/outboundfeeds/rss/",
           "rss", 무게=0.6),
    Source("cointelegraph", "XX", "en", "https://cointelegraph.com/rss", "rss", 무게=0.6),
    Source("decrypt", "US", "en", "https://decrypt.co/feed", "rss", 무게=0.6),
    Source("theblock", "US", "en", "https://www.theblock.co/rss.xml", "rss", 무게=0.6),
    # **원문이다.** 규제 사건은 기사보다 이쪽이 먼저고 시각이 정확하다.
    Source("sec", "US", "en", "https://www.sec.gov/news/pressreleases.rss", "rss",
           무게=1.4, 설명="SEC 보도자료 -- 규제 사건의 **원문**"),
    Source("cftc", "US", "en", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml", "rss", 무게=1.4),
    Source("federalreserve", "US", "en",
           "https://www.federalreserve.gov/feeds/press_monetary.xml", "rss", 무게=1.4,
           설명="금리 -- 암호화폐가 제일 크게 반응하는 거시 사건"),

    # ---- 중국 · 중국어 ----
    # 대륙 매체는 밖에서 막히거나 느린 것이 많다. 그래서 **여럿 걸어 두고 탐침이
    # 고르게** 한다. 하나가 죽어도 GDELT-zh 가 남는다.
    Source("jinse", "CN", "zh", "https://api.jinse.cn/noah/v2/rss", "rss", 무게=1.2,
           설명="金色财经"),
    Source("8btc", "CN", "zh", "https://www.8btc.com/feed", "rss", 무게=1.2, 설명="巴比特"),
    Source("panews", "CN", "zh", "https://www.panewslab.com/zh/rss", "rss", 무게=1.2),
    Source("odaily", "CN", "zh", "https://www.odaily.news/feed", "rss", 무게=1.2),
    Source("pboc", "CN", "zh", "http://www.pbc.gov.cn/rss/rss_zcyj.xml", "rss", 무게=1.5,
           설명="중국인민은행 -- **규제 원문**. 2021 채굴 금지가 이 계열이었다"),
    Source("wublock", "CN", "zh", "https://wublock123.com/feed", "rss", 무게=1.1),

    # ---- 일본 · 일본어 ----
    Source("coinpost", "JP", "ja", "https://coinpost.jp/?feed=rss2", "rss", 무게=1.2),
    Source("neweconomy", "JP", "ja", "https://www.neweconomy.jp/feed", "rss", 무게=1.2,
           설명="あたらしい経済"),
    Source("fsa", "JP", "ja", "https://www.fsa.go.jp/fsaNewsList.xml", "rss", 무게=1.5,
           설명="금융청 -- **규제 원문**. 코인체크 뒤의 행정처분이 여기"),

    # ---- 한국 · 한국어 ----
    Source("blockmedia", "KR", "ko", "https://www.blockmedia.co.kr/feed", "rss", 무게=1.1),
    Source("decenter", "KR", "ko", "https://decenter.sedaily.com/RSS/S1N1.xml", "rss",
           무게=1.1),

    # ---- 집계 (열쇠가 있으면) ----
    Source("cryptopanic", "XX", "mul",
           "https://cryptopanic.com/api/v1/posts/?auth_token={key}&public=true",
           "json", 경로="results", 열쇠="CRYPTOPANIC_TOKEN", 무게=0.5,
           설명="집계기. 원문이 아니라 **재보도**라 무게가 낮다"),
]

표 = {s.이름: s for s in 목록}


def get(이름: str):
    return 표.get(이름)


def 나라별() -> dict:
    out = {}
    for s in 목록:
        out.setdefault(s.나라, []).append(s.이름)
    return out


def 쓸수있는것(과거만: bool = False) -> list:
    out = []
    for s in 목록:
        if 과거만 and not s.과거:
            continue
        ok, _ = s.쓸수있나()
        if ok:
            out.append(s)
    return out


def 확인된것() -> list:
    """**실제로 도는 것을 본 출처만.** 비어 있으면 아직 아무도 안 봤다는 뜻이다."""
    return [s for s in 목록 if s.확인]
