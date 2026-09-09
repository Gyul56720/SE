"""**루프 · 트리거 · 뭉치기 · 모으기** -- 망도 LLM 도 안 쓴다 (가짜 호출자를 넣는다).

    python3 tests/test_coin_loop.py

여기서 붙드는 것 셋:
  1. **hard 가 남은 답은 안 나간다.** 제일 나은 것이라도 안 나간다
  2. **되먹임에 관문 이름이 안 샌다.** 알려 주면 관문이 사양서가 된다
  3. **여러 나라를 모으면 D0 가 앞당겨진다.** 다국적 수집의 값이 이것이다
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _coin_fixture as FX                                            # noqa: E402
from coin import event as EV                                          # noqa: E402
from coin import loop as LP                                           # noqa: E402
from coin import news as NW                                           # noqa: E402
from coin import scenario as SC                                       # noqa: E402
from coin import situation as ST                                      # noqa: E402
from coin import source as SRC                                        # noqa: E402
from coin import tag as TG                                            # noqa: E402
from coin import watch as WT                                          # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


# ---------------------------------------------------------------- 덮임 격자
# **빈틈은 개수로 안 보이고 격자로 보인다.** 매체를 스무 곳 붙여 놓고 규제 원문이
# 하나도 없으면 그것이 빈틈인데, 목록만 보면 "아흔 곳이나 된다" 로 보인다.
빈 = SRC.빈틈()
ok(not 빈, f"(나라 x 층) 격자에 빈 칸이 없다" + (f" -- 빈 칸: {빈}" if 빈 else ""))
for 나라 in SRC.나라들:
    있 = [x for x in SRC.목록 if x.나라 == 나라]
    ok(len(있) >= 6, f"{나라} 출처 {len(있)}곳")
g = SRC.격자()
for 나라 in SRC.나라들:
    ok(bool(g.get((나라, "규제"))), f"{나라} 에 **규제 원문**이 있다 (기사만 보지 않는다)")
ok(all(x.층 in SRC.층들 for x in SRC.목록), "모든 출처의 층이 표에 있는 것이다")
ok(not SRC.확인된것(),
   "**확인된 출처가 아직 0곳이다** -- 이 컨테이너는 프록시가 막는다. 그것이 사실이다")

# 나라를 늘렸으면 그 말의 낱말도 늘어야 한다 -- 안 그러면 조용히 0건이 된다
말들 = {x.말 for x in SRC.목록} - {"mul"}
사전말 = {m for 유형 in TG.사전.values() for m in 유형}
없는말 = 말들 - 사전말
ok(not 없는말, f"출처의 말이 전부 사전에 있다" + (f" -- 없는 말: {없는말}" if 없는말 else ""))
for 글, 참 in [("EZB erhöht den Leitzins", "금리거시"),
               ("La BCE annonce une interdiction", "규제금지"),
               ("SEC ruling on XRP", "소송제재"),
               ("最高人民法院 가상화폐 판결", "소송제재")]:
    ok(참 in TG.유형만(글), f"{글!r} -> {참}")

# ---------------------------------------------------------------- 문서와 코드
# **적어 놓고 안 만든 명령이 이 저장소의 병이다.** `source.py` 의 머리글에
# `--탐침 --기록` 이라고 적어 놓고 그 옵션을 안 만들었었다 -- 사용자가 그대로 치면
# usage 만 나온다. 그래서 문서에 적힌 news.py 옵션이 실제로 있는지 여기서 본다.
import argparse as _ap
import io as _io
import contextlib as _ctx
from coin import news as _NW

_적힌것 = set(re.findall(r"coin/news\.py((?:\s+--[가-힣A-Za-z_]+)+)", SRC.__doc__ or ""))
_적힌옵션 = {o for 묶 in _적힌것 for o in 묶.split() if o.startswith("--")}
_있는옵션 = set()
_p = _io.StringIO()
with _ctx.redirect_stdout(_p):
    try:
        _NW.main(["--help"])
    except SystemExit:
        pass
_도움 = _p.getvalue()
for o in _적힌옵션:
    ok(o in _도움, f"source.py 가 적어 둔 `news.py {o}` 가 실제로 있다")
ok(bool(_적힌옵션), f"문서에서 옵션을 {len(_적힌옵션)}개 읽었다 (0개면 이 검사가 헛것이다)")

# 탐침 기록 -> 확인된것 -> 격자
import tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    _p2 = Path(_d) / "probe.json"
    SRC.탐침기록([{"이름": "sec-press", "산것": 12, "왜": ""},
                 {"이름": "pboc", "산것": 0, "왜": "403"}], _p2)
    본 = SRC.탐침본것(_p2)
    ok(본.get("sec-press", {}).get("산것") == 12, "탐침 기록을 적고 다시 읽는다")
    ok(본.get("pboc", {}).get("산것") == 0, "못 받은 것도 왜와 함께 남는다")
ok(len(SRC.빈틈(확인된것만=True)) > 0,
   "**아직 아무 출처도 확인 안 됐으므로 '확인된 것만' 빈틈은 비어 있지 않다** -- "
   "선언된 덮임과 실제 덮임은 다른 물음이다")

# ---------------------------------------------------------------- dig 에 기대는 자리
# **밑줄 이름에 기대고 있다.** `search._집` 이 없어지면 출처 발굴이 런타임에 죽는데,
# 그것을 검사가 아니라 사용자가 보게 된다. 그래서 여기서 붙든다 -- 이름이 바뀌면
# 검사가 빨개진다.
try:
    from dig import search as DIGS
except Exception:                                                     # noqa: BLE001
    DIGS = None
ok(DIGS is not None, "dig/search 를 임포트할 수 있다 (출처 발굴이 이것으로 돈다)")
if DIGS is not None:
    ok(callable(getattr(DIGS, "_집", None)),
       "**search._집 이 아직 있다** -- 없어지면 coin 이 거친 벌충으로 물러선다")
    ok(callable(getattr(DIGS, "찾기", None)), "search.찾기 가 있다")
    ok(DIGS._집("html.duckduckgo.com") == DIGS._집("duckduckgo.com"),
       "앞자리가 달라도 한집으로 본다")
    ok(DIGS._집("www.naver.co.kr") == "naver.co.kr",
       "**co.kr 이 co.kr 로 안 뭉개진다** -- 뭉개지면 한국 쪽이 통째로 한집이 된다")
집내기 = WT.집자()
ok(집내기("https://www.sec.gov/news/pressreleases.rss") == "sec.gov", "주소에서 집을 낸다")
ok(WT._집벌충("html.duckduckgo.com") == "duckduckgo.com", "벌충도 앞자리는 접는다")
ok(집내기("") == "", "빈 주소는 빈 집")

# ---------------------------------------------------------------- 트리거
for 글, 참 in [("비트코인 시장 분석해줘", True), ("암호화폐 어때", True),
               ("SOL -12.4% 왜 이래?", True), ("PEPE 어때", True),
               ("오늘 점심 뭐 먹지", False), ("리그오브레전드 전적", False)]:
    걸림, _ = ST.걸리나(글)
    ok(걸림 == 참, f"트리거 {'걸림' if 참 else '안 걸림'}: {글!r}")

ok(ST.종목("PEPE 어때", 대조=False) == ["PEPE"],
   "**표에 없는 종목도 푼다** -- 종목표를 코드에 안 박았다")
ok("ETF" not in ST.종목("ETF 승인됐대", 대조=False), "ETF · SEC 같은 말머리는 종목이 아니다")
ok(ST.등락률("SOL -12.4% 왜 이래?") == [-12.4], "등락률을 뽑는다")

# ---------------------------------------------------------------- 뭉치기 (다국적)
글들 = [
    {"제목": "中国央行禁止加密货币交易", "시각": "2021-05-21T09:00:00+00:00",
     "본때": "2021-05-21T09:05:00+00:00", "출처": "pboc", "나라": "CN", "말": "zh",
     "무게": 1.5, "url": "a", "유형": ["규제금지"], "자산": ["BTC"]},
    {"제목": "8btc 禁止", "시각": "2021-05-21T09:30:00+00:00",
     "본때": "2021-05-21T09:35:00+00:00", "출처": "8btc", "나라": "CN", "말": "zh",
     "무게": 1.2, "url": "b", "유형": ["규제금지"], "자산": ["BTC"]},
    {"제목": "China bans crypto trading", "시각": "2021-05-21T16:00:00+00:00",
     "본때": "2021-05-21T16:05:00+00:00", "출처": "coindesk", "나라": "US", "말": "en",
     "무게": 0.6, "url": "c", "유형": ["규제금지"], "자산": ["BTC"]},
]
사건 = NW.뭉치기(글들)
ok(len(사건) == 1 and 사건[0]["글수"] == 3, "세 나라 기사가 한 사건으로 뭉친다")
ok(사건[0]["최초"][11:16] == "09:00", "D0 는 **제일 이른 보도**(중국어)")
영어만 = NW.뭉치기([g for g in 글들 if g["나라"] == "US"])
ok(영어만[0]["최초"][11:16] == "16:00",
   "**영어만 모았으면 7시간 늦다** -- 그 일곱 시간이 대개 그 사건의 움직임 전부다")
ok(사건[0]["나라수"] == 2 and 사건[0]["주국"] == "CN", "나라 수와 주류 나라를 센다")

미래 = dict(글들[0], 시각="2099-01-01T00:00:00+00:00", 앞선시각=True)
ok(len(NW.뭉치기([미래])) == 0,
   "**시각이 미래인 줄은 D0 를 못 정한다** -- 피드 시간대 버그가 미리보기를 만든다")

덮 = NW.덮임(글들)
ok(덮["나라"] == {"CN": 2, "US": 1}, "덮임이 나라별로 센다 -- 무엇이 빠졌는지 보이는 자리")

# ---------------------------------------------------------------- 루프
날 = FX.사건날()
c = FX.계열(심을날=날, 효과=0.09)
잰것 = EV.전부({"BTC": c}, FX.사건(날), 지평들=(7,), 유형들=("규제금지",), 판수=500)
원장 = {"잰것": 잰것, "사건수": len(날)}
r = 잰것[0]
뭉치 = [SC.뽑기(c, r)]
바른 = (f"규제금지 D+7: 관측 중앙값 {r['관측중앙']*100:+.2f}% 인데 아무 날이나 골랐을 때의 "
        f"기저율이 {r['널중앙']*100:+.2f}% 라 초과는 {r['초과']*100:+.2f}%p 로 상승 쪽이다. "
        f"표본 n={r['n']} (겹치지 않는 것 {r['유효n']}), 승률 {r['승률']*100:.0f}%. "
        f"이번 실행에서 {r['시험수']}번 쟀고 BH 보정.")

부른것 = []


def 가짜(고침: int):
    def _(p):
        부른것.append(p)
        if len(부른것) <= 고침:
            return f"규제금지 D+7 은 -99.00% 가고 반드시 오릅니다. n={r['n']}."
        return 바른
    return _


부른것.clear()
끝 = LP.돌리기("비트코인 어때", 원장, 가짜(1), None, {"BTC": c}, 뭉치, 바퀴수=4)
ok(끝.통과 and 끝.돈바퀴 == 2, f"한 번 고치면 2바퀴에서 멈춘다 (돈 바퀴 {끝.돈바퀴})")
ok(끝.답 == 바른, "제일 좋은 답을 낸다")

부른것.clear()
끝2 = LP.돌리기("비트코인 어때", 원장, 가짜(99), None, {"BTC": c}, 뭉치, 바퀴수=3)
ok(not 끝2.통과 and 끝2.답 == "",
   "**끝내 안 고쳐지면 안 내보낸다** -- 제일 나은 것이라도 안 내보낸다")
ok(끝2.돈바퀴 == 3 and any(v.급 == "hard" for v in 끝2.위반들),
   "대신 어디가 어긋났는지를 준다")

부른것.clear()
끝3 = LP.돌리기("비트코인 어때", 원장, lambda p: 바른, None, {"BTC": c}, 뭉치, 바퀴수=4)
ok(끝3.통과 and 끝3.돈바퀴 == 1, "처음부터 맞으면 한 바퀴에서 멈춘다 (호출을 안 낭비한다)")


def 터짐(p):
    raise RuntimeError("키가 없다")


끝4 = LP.돌리기("비트코인 어때", 원장, 터짐, None, {"BTC": c}, 뭉치)
ok(not 끝4.통과 and "못 불렀다" in 끝4.왜, "모델을 못 부르면 사실대로 말한다")

# ---------------------------------------------------------------- 프롬프트가 새는가
프 = 부른것[0] if 부른것 else ""
부른것.clear()
LP.돌리기("비트코인 어때", 원장, 가짜(1), None, {"BTC": c}, 뭉치, 바퀴수=2)
ok(not re.search(r"C0\d\d", 부른것[0]),
   "**프롬프트에 관문 이름이 없다** -- 있으면 관문이 사양서가 된다")
ok(not re.search(r"C0\d\d", 부른것[1]), "두 바퀴째 되먹임에도 없다")
ok("(라)" in 부른것[0] and "시나리오" in 부른것[0], "시나리오 표가 프롬프트에 실린다")
ok("확률을 네가 정하지 마라" in 부른것[0], "확률을 모델이 못 매기게 못을 박는다")
ok("고래" in 부른것[0] and "지갑이 아니다" in 부른것[0],
   "거래량을 고래라고 부르지 말라는 것이 프롬프트에 있다")

# ---------------------------------------------------------------- 모으기 한 바퀴
# **출처를 빈 목록으로 준다 -- 검사는 망을 타면 안 된다.** 곁문이 붙은 뒤로 한 바퀴가
# 94곳 x (헤더벌 + 곁문) 이라, 망이 막힌 데서 돌리면 그 시간을 전부 기다린다.
r1 = WT.한바퀴(출처=[])
ok(isinstance(r1, dict) and "받은것" in r1 and r1["받은것"] == 0,
   "모으기 한 바퀴가 출처 0곳에서도 안 죽는다 (검사는 망을 안 탄다)")
ok(WT.줄(r1).startswith("["), "바퀴마다 로그 한 줄 -- **로그가 안 늘면 죽은 것이다**")

print()
print(f"실패 {len(fails)}개" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
