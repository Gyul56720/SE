"""**뉴스를 사건 유형으로 가른다. LLM 을 안 쓴다.**

    python3 coin/tag.py --낱말                 사전을 본다 (호출 0회)
    python3 coin/tag.py --글 "中国央行禁止加密货币交易"
    python3 coin/tag.py --재현 30 --원장 coin/corpus/news.json   사람이 30개를 검수한다

## 왜 여기에 모델을 안 쓰나

두 가지다.

1. **되짚을 수 있어야 한다.** 이 꼬리표가 D0 를 정하고 D0 가 잰 값을 정한다. 모델이
   붙인 꼬리표는 다시 물으면 달라지고, 그러면 어제의 잰 값과 오늘의 잰 값이 왜 다른지
   아무도 못 밝힌다. 여기서 나가는 꼬리표는 **어느 낱말이 어디서 걸렸는지**를 들고
   다닌다(`Tag.걸린것`). `brief/derive.py` 의 `Fact.근거` 와 같은 자리다.
2. **틀리는 방향이 안전하다.** 사전은 놓치고(재현율 낮음) 헛짚는다(정밀도 낮음).
   그런데 사건 연구에서 **꼬리표 잡음은 신호를 널 쪽으로 끌어내린다** -- 상관없는
   날이 섞이면 잰 값이 기저율에 가까워진다. 즉 잡음은 **덜 주장하게** 만든다.
   그것이 안전한 방향이다. 위험한 것은 잡음이 아니라 **미리보기**(D0 를 사건보다
   뒤로 잡는 것)이고, 그것은 사전이 아니라 `news.py` 의 뭉치기가 막는다.

## 말마다 자르는 법이 다르다

영어는 낱말 경계를 봐야 한다 -- `ban` 을 그냥 넣으면 `urban` · `Albania` 가 걸린다
(이것 때문에 한 번 헛짚었다). 중국어·일본어는 띄어쓰기가 없으므로 **부분 문자열이
맞는 법**이다. 그래서 말에 따라 다른 자를 쓴다(`_재기`).

## 사전에 없는 유형은 없는 것이다

새 유형을 붙이는 것은 이 표에 줄을 더하는 일이지 코드를 짜는 일이 아니다
(`brief/source.py` 와 같은 규약). 그리고 **표에 없는 유형을 답이 지어내면
`gate.py` C007 이 잡는다.**
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 유형 -> 말 -> 낱말들.
# 무게(events 가 쓰는 것)가 아니라 **가름**만 여기서 한다.
사전 = {
    "규제금지": {
        "en": ["ban", "bans", "banned", "crackdown", "prohibit", "prohibits", "outlaw",
               "illegal", "restrict", "restricts", "clampdown"],
        "zh": ["禁止", "取缔", "打击", "整治", "叫停", "严禁", "清退", "违法"],
        "ja": ["禁止", "規制強化", "取り締ま", "違法"],
        "ko": ["금지", "규제 강화", "단속", "불법", "제한"],
    },
    "규제승인": {
        "en": ["approve", "approves", "approved", "approval", "greenlight", "green light",
               "authorize", "authorized", "license", "licensed", "registration granted"],
        "zh": ["批准", "核准", "获批", "许可", "牌照"],
        "ja": ["承認", "認可", "登録完了", "免許"],
        "ko": ["승인", "인가", "허가", "라이선스"],
    },
    "소송제재": {
        "en": ["sues", "sued", "lawsuit", "charges", "charged", "indict", "indicted",
               "enforcement action", "subpoena", "settlement", "fined", "penalty"],
        "zh": ["起诉", "诉讼", "指控", "罚款", "处罚", "立案"],
        "ja": ["提訴", "訴訟", "起訴", "行政処分", "業務改善命令", "課徴金"],
        "ko": ["소송", "기소", "제재", "과징금", "행정처분", "고발"],
    },
    "해킹유출": {
        "en": ["hack", "hacked", "hacker", "exploit", "exploited", "breach", "stolen",
               "drained", "attack on", "vulnerability"],
        "zh": ["黑客", "被盗", "攻击", "漏洞", "被黑"],
        "ja": ["ハッキング", "流出", "不正アクセス", "脆弱性", "盗まれ"],
        "ko": ["해킹", "유출", "탈취", "취약점", "도난"],
    },
    "파산지급중단": {
        "en": ["bankruptcy", "insolvent", "insolvency", "halts withdrawals",
               "suspends withdrawals", "chapter 11", "liquidation", "collapse"],
        "zh": ["破产", "暂停提币", "暂停提现", "清算", "爆雷"],
        "ja": ["破綻", "破産", "出金停止", "民事再生"],
        "ko": ["파산", "출금 중단", "회생", "지급 중단"],
    },
    "상장": {
        "en": ["lists", "listing", "will list", "adds support for", "debuts on"],
        "zh": ["上线", "上币", "开放交易", "首发"],
        "ja": ["上場", "取扱開始", "取り扱い開始"],
        "ko": ["상장", "거래 지원", "원화 마켓"],
    },
    "ETF": {
        "en": ["etf", "exchange-traded fund", "spot etf", "s-1", "19b-4"],
        "zh": ["ETF", "现货ETF"],
        "ja": ["ETF", "現物ETF"],
        "ko": ["ETF", "현물 ETF"],
    },
    "기관채택": {
        "en": ["buys bitcoin", "adds bitcoin", "treasury", "allocates to bitcoin",
               "institutional adoption", "custody launch", "legal tender"],
        "zh": ["增持", "配置比特币", "机构采用", "法定货币"],
        "ja": ["購入を発表", "準備資産", "機関投資家", "法定通貨"],
        "ko": ["매입", "편입", "기관 채택", "법정화폐"],
    },
    "금리거시": {
        "en": ["fomc", "federal reserve", "rate hike", "rate cut", "cpi", "inflation data",
               "jobs report", "powell", "quantitative tightening"],
        "zh": ["加息", "降息", "美联储", "通胀数据", "议息"],
        "ja": ["利上げ", "利下げ", "FRB", "日銀", "消費者物価"],
        "ko": ["금리 인상", "금리 인하", "연준", "물가", "FOMC"],
    },
    "반감기업그레이드": {
        "en": ["halving", "hard fork", "upgrade goes live", "mainnet launch", "merge"],
        "zh": ["减半", "硬分叉", "主网上线", "升级"],
        "ja": ["半減期", "ハードフォーク", "メインネット"],
        "ko": ["반감기", "하드포크", "메인넷", "업그레이드"],
    },
    "고래이동": {
        "en": ["whale", "whales", "large transfer", "moved to exchange", "dormant wallet"],
        "zh": ["巨鲸", "大额转账", "转入交易所"],
        "ja": ["クジラ", "大口送金"],
        "ko": ["고래", "대량 이체", "거래소 입금"],
    },
    "스테이블코인": {
        "en": ["depeg", "depegged", "stablecoin", "loses peg", "redemption halt"],
        "zh": ["脱锚", "稳定币", "脱钩"],
        "ja": ["ペッグ", "ステーブルコイン", "デペッグ"],
        "ko": ["디페그", "스테이블코인", "페그"],
    },
    "채굴": {
        "en": ["mining ban", "hashrate", "miners", "mining farm", "difficulty adjustment"],
        "zh": ["挖矿", "矿场", "算力", "矿工"],
        "ja": ["マイニング", "ハッシュレート", "採掘"],
        "ko": ["채굴", "해시레이트", "채굴장"],
    },
}

# 자산 이름 -- **코드가 아니라 데이터다.** 거래소 심볼(BTC · ETH ...)은 price.심볼목록()
# 이 거래소에서 받아 오고, 여기 있는 것은 그것을 **사람 말로 부르는 이름**뿐이다
# (비트코인 · 比特币 · ビットコイン). 새 이름은 이 파일에 줄을 더하면 되고 코드는 안 바뀐다.
별명길 = Path(__file__).resolve().parent / "corpus/aliases.json"


def 자산별명() -> dict:
    if 별명길.exists():
        return json.loads(별명길.read_text(encoding="utf-8"))
    return {}


자산사전 = 자산별명()

유형들 = tuple(사전.keys())
자산들 = tuple(자산사전.keys())

# 낱말 경계를 봐야 하는 말. 나머지(zh·ja)는 부분 문자열이 맞다.
_경계 = {"en"}


@dataclass
class Tag:
    유형: str
    걸린것: tuple = ()       # ((말, 낱말), ...) -- **되짚는 자리**

    def __hash__(self):
        return hash(self.유형)


def _재기(말: str, 낱말: str, 글: str) -> bool:
    """말에 따라 다른 자. 영어만 낱말 경계를 본다."""
    if 말 in _경계:
        return re.search(r"(?<![a-z0-9])" + re.escape(낱말) + r"(?![a-z0-9])", 글) is not None
    return 낱말 in 글


def 재기(글: str, 말: str = "") -> list:
    """글 하나에서 유형들을 뽑는다. `말` 을 주면 그 말 사전만, 안 주면 전부 본다.

    **여러 유형이 나올 수 있다.** 하나로 좁히지 않는다 -- "중국이 거래소를 금지하고
    소송을 걸었다" 는 실제로 둘이다. 사건 연구는 유형별로 따로 세므로 겹쳐도 된다.
    """
    낮 = (글 or "").lower()
    out = []
    for 유형, 말별 in 사전.items():
        걸림 = []
        for m, 낱말들 in 말별.items():
            if 말 and m != 말 and m != "en":
                pass                       # 말을 줘도 en 은 늘 본다 (고유명사가 섞인다)
            for w in 낱말들:
                if _재기(m, w.lower(), 낮):
                    걸림.append((m, w))
        if 걸림:
            out.append(Tag(유형, tuple(걸림)))
    return out


def 자산재기(글: str) -> tuple:
    낮 = (글 or "").lower()
    out = []
    for 이름, 낱말들 in 자산사전.items():
        for w in 낱말들:
            if _재기("en" if w.isascii() else "zh", w.lower(), 낮):
                out.append(이름)
                break
    return tuple(out)


def 유형만(글: str) -> tuple:
    return tuple(t.유형 for t in 재기(글))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--낱말", action="store_true")
    ap.add_argument("--글", default="")
    ap.add_argument("--재현", type=int, default=0, help="원장에서 몇 개를 뽑아 사람이 검수")
    ap.add_argument("--원장", default="coin/corpus/news.json")
    ap.add_argument("--씨", type=int, default=1)
    a = ap.parse_args(argv)

    if a.낱말:
        for 유형, 말별 in 사전.items():
            수 = sum(len(v) for v in 말별.values())
            print(f"  {유형:<14} {수:>3}낱말  " + " · ".join(f"{m}{len(v)}" for m, v in 말별.items()))
        print(f"\n유형 {len(사전)}개 · 자산 {len(자산사전)}개. **표에 없는 유형은 없는 것이다**")
        return 0

    if a.글:
        ts = 재기(a.글)
        if not ts:
            print("걸린 유형 없음")
        for t in ts:
            print(f"  {t.유형:<14} <- " + ", ".join(f"{m}:{w}" for m, w in t.걸린것))
        자 = 자산재기(a.글)
        print(f"  자산: {', '.join(자) or '없음'}")
        return 0

    if a.재현:
        p = Path(a.원장)
        if not p.exists():
            print(f"원장이 없다: {p} -- 먼저 news.py 로 채워라", file=sys.stderr)
            return 3
        글들 = json.loads(p.read_text(encoding="utf-8")).get("글", [])
        random.Random(a.씨).shuffle(글들)
        for g in 글들[:a.재현]:
            ts = 재기(g.get("제목", ""))
            print(f"\n[{g.get('나라','?')}/{g.get('말','?')}] {g.get('제목','')[:90]}")
            print("   -> " + (", ".join(t.유형 for t in ts) or "없음"))
        print(f"\n**사람이 본다.** 위 {min(a.재현, len(글들))}개 중 몇 개가 맞나 -- "
              "그 수가 이 사전의 정밀도이고, 그것 말고 이 사전을 잴 길은 없다")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
