"""**출처는 코드가 아니라 선언이다.** 새 출처를 붙이는 것은 표 한 줄을 더하는 일이다.

`mathdrift/ops.py` 가 연산자를 고정 목록으로 두고, `law/issue.py` 가 갈래별 단계를
표로 두는 것과 같은 자리다. 여기 붙는 것이 늘어나도 **논리 층은 안 바뀐다.**

## 왜 선언인가

"오늘 주식 시장 보고해줘" 를 위해 주식 코드를 짜고, 다음에 환율을 물으면 환율 코드를
짜면, 물음마다 코드가 하나씩 는다. 그러면 어느 보고서가 검사를 받았고 어느 것이 안
받았는지 아무도 모르게 된다 -- 이 저장소가 `law/` 에서 피한 그것이다(관문은 하나,
문서는 여럿).

그래서 **가져오기·검사·셈·관문은 한 벌**이고, 출처는 아래 표에만 는다.

    Source.칸      무엇이 반드시 있어야 하는가          -> ledger 가 강제한다
    Source.수칸    무엇이 수인가                        -> derive 가 셈한다
    Source.셈      이 출처에서 무엇을 낼 것인가          -> gate 가 다시 셈해서 대조한다
    Source.신선    며칠 지나면 낡은 것인가              -> gate B003

## 열쇠가 필요한 출처는 열쇠를 요구한다

없으면 **미검증으로 끝난다.** 다른 출처의 값을 끌어다 메우지 않는다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Source:
    이름: str
    설명: str
    url: str                       # {..} 자리는 fetch 가 채운다
    꼴: str = "csv"                # csv · json
    칸: tuple = ()                 # 반드시 있어야 하는 칸
    수칸: tuple = ()               # 수로 읽을 칸
    key: str = ""                  # 줄을 가리키는 이름 (줄 id 가 된다)
    경로: str = ""                 # json 일 때 줄 목록이 있는 자리 (점으로 구분)
    별칭: dict = field(default_factory=dict)
    셈: tuple = ()                 # 이 출처에서 낼 파생값 (derive.RULES 의 이름)
    신선: int = 3                  # 며칠까지 신선한가
    열쇠: str = ""                 # 필요한 환경변수 이름. 빈 값이면 필요 없다
    단위: dict = field(default_factory=dict)

    def 쓸수있나(self) -> tuple:
        """(쓸 수 있나, 왜). 열쇠가 필요한데 없으면 여기서 걸린다."""
        if self.열쇠 and not os.environ.get(self.열쇠):
            return False, f"{self.열쇠} 가 없다 -- 이 출처는 열쇠가 있어야 한다"
        return True, ""


# ── 출처 표 ──────────────────────────────────────────────────────────
# **여기에 줄을 더하는 것이 '새 기능' 이다.** 아래 어느 줄도 답을 담고 있지 않다 --
# 어디서 무엇을 어떤 꼴로 받아 오는지만 적혀 있다.
SOURCES = {}


def 등록(s: Source) -> Source:
    SOURCES[s.이름] = s
    return s


등록(Source(
    이름="주식",
    설명="지수·종목 종가 (Stooq. 열쇠 없음)",
    # 여러 심볼을 쉼표로 한 번에. f= 는 받을 칸을 정하는 Stooq 의 문법이다.
    url="https://stooq.com/q/l/?s={심볼}&f=sd2t2ohlcv&h&e=csv",
    꼴="csv",
    칸=("Symbol", "Date", "Open", "High", "Low", "Close", "Volume"),
    수칸=("Open", "High", "Low", "Close", "Volume"),
    key="Symbol",
    별칭={
        "코스피": "^kospi", "kospi": "^kospi",
        "코스닥": "^kosdaq", "kosdaq": "^kosdaq",
        "s&p": "^spx", "sp500": "^spx", "스앤피": "^spx",
        "나스닥": "^ndq", "nasdaq": "^ndq",
        "다우": "^dji", "dow": "^dji",
        "닛케이": "^nkx", "삼성전자": "005930.kr", "sk하이닉스": "000660.kr",
    },
    셈=("일간등락", "폭", "종가위치"),
    신선=3,
    단위={"Close": "", "Volume": "주", "일간등락": "%", "폭": "%", "종가위치": ""},
))

등록(Source(
    이름="환율",
    설명="통화쌍 종가 (Stooq. 열쇠 없음)",
    url="https://stooq.com/q/l/?s={심볼}&f=sd2t2ohlcv&h&e=csv",
    꼴="csv",
    칸=("Symbol", "Date", "Open", "High", "Low", "Close"),
    수칸=("Open", "High", "Low", "Close"),
    key="Symbol",
    별칭={"달러": "usdkrw", "usdkrw": "usdkrw", "엔": "jpykrw",
          "유로": "eurkrw", "위안": "cnykrw"},
    셈=("일간등락", "폭", "종가위치"),
    신선=3,
    단위={"Close": "원", "일간등락": "%", "폭": "%"},
))


등록(Source(
    이름="시계열",
    설명="지수·종목의 **일별 내력** (Stooq. 열쇠 없음) -- 추론은 이것이 있어야 한다",
    url="https://stooq.com/q/d/l/?s={심볼}&i=d",
    꼴="csv",
    칸=("Date", "Open", "High", "Low", "Close"),
    수칸=("Open", "High", "Low", "Close"),
    key="Date",
    별칭=SOURCES["주식"].별칭,          # 같은 이름으로 부른다 -- 두 벌을 두면 갈라진다
    셈=(),                              # 줄이 날짜라 '일간등락' 은 여기서 안 쓴다
    신선=5,
    단위={},
))


def get(name: str) -> Source | None:
    """이름으로 출처를. **없으면 None 이다** -- 비슷한 것을 골라 주지 않는다."""
    return SOURCES.get(name)


def 즉석(url: str, 꼴: str = "", 칸=(), 수칸=(), key: str = "", 경로: str = "",
         셈=(), 신선: int = 3, 이름: str = "즉석") -> Source:
    """**등록하지 않고 그 자리에서 만드는 출처.**

    위의 표는 내가 미리 아는 도메인만 담는다 -- 티켓값을 물으면 표에 없다. 그런데
    표에 없다고 못 하면 결국 내가 예상한 것만 되는 것이고, 그게 하드코딩이다.

    ## 그래도 규율은 안 풀린다

    여기서 밖(사람이든 모델이든)이 정하는 것은 **어디를 볼 것인가**뿐이다.
    수는 여전히 아무도 못 만든다:

        url 을 지어내면      -> fetch 가 실패한다 -> 미검증, 수 0개
        스키마를 지어내면    -> 도착한 것과 안 맞아 inspect 가 거절한다
        칸을 안 적으면       -> 도착한 것에서 읽는다 (짐작이 아니라 관측이다)
        값을 지어내면        -> **B004 가 원장에서 다시 세서 잡는다**

    `law/METHOD.md` 의 분업 그대로다 -- LLM 은 조문에서 요건을 뽑고(대조 가능한 일),
    쟁점은 코드가 도출한다. 여기서는 **출처 제안이 그 '요건 뽑기' 자리**다.

    꼴을 안 주면 url 에서 짐작하되, 짐작이 틀려도 `parse` 가 빈 목록을 돌려주고
    그러면 거절된다 -- 짐작이 조용히 통과하는 길은 없다.
    """
    if not 꼴:
        꼴 = "csv" if any(t in url.lower() for t in (".csv", "e=csv", "format=csv")) else "json"
    return Source(이름=이름, 설명=f"즉석 출처 ({url[:60]})", url=url, 꼴=꼴,
                  칸=tuple(칸), 수칸=tuple(수칸), key=key, 경로=경로,
                  셈=tuple(셈), 신선=신선)


def 심볼(s: Source, 것들: list) -> list:
    """사람이 부른 이름 -> 출처의 심볼. **모르는 것은 그대로 넘긴다.**

    임의로 고쳐 넣지 않는다 -- 고쳐 넣으면 딴 종목의 값을 그 이름으로 보고하게 된다.
    모르는 채로 넘기면 출처가 빈 값을 돌려주고, 그것은 ledger 검사가 잡는다.
    """
    out = []
    for x in 것들:
        k = x.strip().lower().replace(" ", "")
        out.append(s.별칭.get(k, x.strip()))
    return out
