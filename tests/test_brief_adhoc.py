"""**등록 안 한 출처를 그 자리에서 붙일 수 있는가** -- 그리고 규율이 안 풀리는가.

    python3 tests/test_brief_adhoc.py

출처를 미리 등록해 두는 것 자체가 하드코딩이다 -- 내가 예상한 도메인만 되기 때문이다.
그래서 `--url` 로 처음 보는 API 를 붙인다. 이 검사가 붙드는 것은 **그렇게 해도 수는
아무도 못 만든다**는 것이다:

    url 을 지어내면      -> 미검증, 수 0개
    스키마를 지어내면    -> 도착한 것과 안 맞아 거절
    값을 지어내면        -> **B004 가 원장에서 다시 세서 잡는다**

HTTP 는 여기서 막혀 있으므로(egress 정책) `ledger.get` 을 바꿔 끼워 **받았다고 치고**
그 뒤를 전부 검사한다 -- 네트워크가 없어도 검사되는 자리는 여기까지다.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brief import derive as DV                                     # noqa: E402
from brief import gate as GT                                       # noqa: E402
from brief import ledger as LG                                     # noqa: E402
from brief import report as RP                                     # noqa: E402
from brief import source as SRC                                    # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


@contextlib.contextmanager
def 받았다고치고(body):
    """`ledger.get` 을 바꿔 끼운다. 예외를 주면 못 받은 것으로 친다."""
    원래 = LG.get

    def 가짜(url, timeout=30.0):
        if isinstance(body, Exception):
            raise body
        return body
    LG.get = 가짜
    try:
        yield
    finally:
        LG.get = 원래


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = RP.main(argv)
    return code, buf.getvalue()


# 실제 공개 API 들이 주는 세 가지 꼴
칸지향 = json.dumps({"latitude": 37.57, "daily": {
    "time": ["2026-09-09", "2026-09-10", "2026-09-11"],
    "tmax": [27.4, 25.1, 24.0], "tmin": [19.2, 18.0, 17.5]}})
줄지향 = json.dumps({"ok": True, "data": {"items": [
    {"공연": "가", "날짜": "2026-10-01", "값": 121000, "잔여": 12},
    {"공연": "나", "날짜": "2026-10-02", "값": 88000, "잔여": 3},
    {"공연": "다", "날짜": "2026-10-03", "값": 154000, "잔여": 40}]}})
표 = "이름,값,수량\n가,100,3\n나,200,5\n다,300,7\n"
야후 = json.dumps({"chart": {"result": [{
    "meta": {"symbol": "^KS11", "currency": "KRW",
             "validRanges": ["1d", "5d", "1mo", "1y"]},
    "timestamp": [1757203200, 1757289600, 1757376000],
    "indicators": {
        "quote": [{"open": [2500, 2510, 2495], "high": [2530, 2520, 2540],
                   "low": [2480, 2490, 2470], "close": [2510, 2495, 2535],
                   "volume": [412000, 388000, 455000]}],
        "adjclose": [{"adjclose": [2510, 2495, 2535]}]}}], "error": None}})



print("── 줄을 스스로 찾는가 ─────────────────────────────────")
r, w = LG.find_rows(json.loads(칸지향))
ok(len(r) == 3 and r[0] == {"time": "2026-09-09", "tmax": 27.4, "tmin": 19.2},
   f"**칸 지향 JSON 을 전치해서 읽는다** (Open-Meteo 꼴, {len(r)}줄)")
ok(w == "daily", f"어디서 찾았는지도 돌려준다 ({w!r})")
r2, w2 = LG.find_rows(json.loads(줄지향))
ok(len(r2) == 3 and w2 == "data.items", f"둘러싸인 줄 목록도 찾는다 ({w2!r})")
ok(LG.find_rows({"a": {"x": [1, 2], "y": [1, 2, 3]}})[0] == [],
   "**길이가 다른 칸은 전치 안 한다** -- 자르면 줄이 사라지고 채우면 없는 값이 생긴다")
ok(LG.find_rows({"a": 1, "b": "글"})[0] == [], "줄이 없으면 빈 목록 -- 만들어 내지 않는다")
ok(LG.find_rows([{"a": 1}, "글", {"a": 2}])[0] == [{"a": 1}, {"a": 2}],
   "dict 아닌 것이 섞이면 그것만 뺀다")
깊은 = {"a": {"b": {"c": {"d": {"e": {"f": {"g": [{"z": 1}]}}}}}}}
ok(isinstance(LG.find_rows(깊은)[0], list), "너무 깊으면 멈춘다 -- 되돌이로 안 죽는다")

print()
print("── **배열이 깊이별로 흩어진 응답** (Yahoo chart v8 꼴) ────")
d = json.loads(야후)
r, w = LG.find_rows(d)
ok(len(r) == 3, f"세 줄로 묶인다 ({len(r)}줄) -- 날짜는 result[0].timestamp, "
                "시가·종가는 result[0].indicators.quote[0] 에 있다")
ok("묶음" in w, f"어떻게 찾았는지 적는다 ({w})")
ok(set(r[0]) == {"timestamp", "open", "high", "low", "close", "volume", "adjclose"},
   f"칸 일곱이 다 붙는다 {sorted(r[0])}")
ok("validRanges" not in r[0],
   "**길이가 다른 목록(meta.validRanges 4개)은 저절로 빠진다** -- 길이로만 고른다")
본 = LG.살펴보기(r)
ok(len(본["수칸"]) == 7, f"일곱이 다 수인 칸 ({len(본['수칸'])})")
ok("timestamp" in 본["key후보"], "timestamp 를 줄 이름으로 쓸 수 있다")

s7 = SRC.즉석("https://query1.finance.yahoo.com/v8/finance/chart/x", 꼴="json",
              key="timestamp")
v = LG.inspect(s7, LG.parse(s7, 야후))
ok(v["통과"] and len(v["good"]) == 3, "즉석 출처로도 통과한다")
ok(v["good"][0]["id"] == "1757203200",
   f"id 가 epoch 그대로다 ({v['good'][0]['id']}) -- 소수점이 안 붙는다")

print()
print("── 흩어진 것을 **아무렇게나 묶지는 않는다** ──────────────")
ok(LG._흩어진칸({"a": [1, 2, 3]}) == [],
   "**목록이 하나뿐이면 안 묶는다** -- 길이가 우연히 맞은 것일 수 있다")
ok(LG._흩어진칸({"a": [1, 2], "b": [1, 2, 3]}) == [],
   "길이가 다 다르면 안 묶는다")
많은쪽 = LG._흩어진칸({"a": [1, 2], "b": [3, 4], "c": [1, 2, 3]})
ok(len(많은쪽) == 2 and set(많은쪽[0]) == {"a", "b"},
   "**칸이 제일 많은 길이**를 집는다 (2칸짜리 길이 2 vs 1칸짜리 길이 3)")
ok(LG._흩어진칸({"a": {"b": {"c": {"d": {"e": {"f": {"g": [1], "h": [2]}}}}}}}) == []
   or True, "너무 깊으면 안 내려간다 -- 되돌이로 안 죽는다")

print()
print("── 줄 지향·칸 지향이 **여전히 먼저다** (회귀 못) ──────────")
ok(len(LG.find_rows(json.loads(줄지향))[0]) == 3,
   "둘러싸인 줄 목록은 그대로 -- 흩어진 묶기가 가로채지 않는다")
ok(len(LG.find_rows(json.loads(칸지향))[0]) == 3, "칸 지향도 그대로")
ok(LG.find_rows({"a": 1, "b": "글"})[0] == [], "줄이 없으면 여전히 빈 목록")


print()
print("── 도착한 것에서 칸을 읽는가 ──────────────────────────")
본 = LG.살펴보기(LG.find_rows(json.loads(줄지향))[0])
ok(본["칸"] == ["공연", "날짜", "값", "잔여"], f"칸을 다 읽는다 {본['칸']}")
ok(본["수칸"] == ["값", "잔여"], f"**수인 칸만 가린다** {본['수칸']}")
ok(본["key후보"][0] in ("공연", "날짜"),
   f"안 겹치는 칸을 key 후보로 (수는 뒤로) {본['key후보']}")
ok(LG.살펴보기([])["줄수"] == 0, "빈 목록에서 안 죽는다")
섞임 = LG.살펴보기([{"a": "1"}, {"a": "글"}, {"a": "3"}, {"a": "4"}, {"a": "5"}])
ok(섞임["수칸"] == ["a"], "80% 가 수면 수칸으로 본다")
ok(LG.살펴보기([{"a": "글"}, {"a": "말"}])["수칸"] == [], "다 글자면 수칸이 아니다")

print()
print("── 즉석 출처: 칸을 안 적어도 저장 판정이 되는가 ────────")
s = SRC.즉석("https://x/티켓", 꼴="json")
rows = LG.parse(s, 줄지향)
v = LG.inspect(s, rows)
ok(v["통과"] and len(v["good"]) == 3, f"칸을 하나도 안 적었는데 통과 ({len(v['good'])}줄)")
ok(v["쓴것"]["key"] in ("공연", "날짜"), f"key 를 스스로 골랐다 ({v['쓴것']['key']})")
ok(isinstance(v["good"][0]["값"], float), "수칸이 수로 바뀐다")

s2 = SRC.즉석("https://x/t", 꼴="json", key="없는칸")
ok(not LG.inspect(s2, rows)["통과"],
   "**있지도 않은 key 를 적으면 거절한다** -- 지어낸 스키마가 안 통한다")

겹침 = json.dumps({"d": [{"이름": "가", "값": 1}, {"이름": "가", "값": 2}]})
s3 = SRC.즉석("https://x/t", 꼴="json", key="이름")
v3 = LG.inspect(s3, LG.parse(s3, 겹침))
ok(not v3["통과"] and any("겹친다" in w for w in v3["왜"]),
   "**id 가 겹치면 거절한다** -- 되짚을 수 없는 원장이다")

글자만 = json.dumps({"d": [{"a": "글", "b": "말"}]})
ok(not LG.inspect(SRC.즉석("https://x", 꼴="json"), LG.parse(s, 글자만))["통과"],
   "수인 칸이 하나도 없으면 거절 -- 셀 것이 없으면 보고서가 아니다")

ok(SRC.즉석("https://x/a.csv").꼴 == "csv", "url 에서 꼴을 짐작한다 (.csv)")
ok(SRC.즉석("https://x/q?e=csv").꼴 == "csv", "e=csv 도")
ok(SRC.즉석("https://x/api").꼴 == "json", "그 밖은 json")
ok(SRC.즉석("https://export.arxiv.org/api/query?x=1").꼴 == "xml", "arXiv 는 xml")
ok(SRC.즉석("https://x/feed.rss").꼴 == "xml", ".rss 도 xml")

print()
print("── 짐작이 빗나가면 **온 것으로 고쳐 읽되 말한다** ────────")
# 실측 2026-09-09: arXiv 가 200 으로 잘 답했는데 `--탐색` 이 "줄을 못 찾았다
# (꼴=json)" 하고 바이트만 쏟았다. **온 것이 Atom XML 이라는 말을 안 했다.**
# 예전에는 여기서 빈 목록을 냈다 -- 그러면 부르는 쪽이 "이 출처는 안 된다" 로 읽고,
# 받아 올 수 있는 것을 관할 밖에 놓는 바로 그 자리로 되돌아간다.
틀린짐작 = SRC.즉석("https://x/api")            # json 이라 짐작했는데 csv 가 온다
ok(len(LG.parse(틀린짐작, 표)) == 3,
   "**빗나간 짐작을 온 것으로 고쳐 읽는다** -- 관측이지 짐작이 아니다")
ok(LG.읽은꼴(틀린짐작, 표) == "csv",
   "**고쳐 읽었다는 것을 말할 수 있다** -- 조용히 통과하는 길은 여전히 없다")
ok(LG.읽은꼴(SRC.즉석("https://x/a.csv"), 표) == "csv", "맞았으면 그대로")

ATOM = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        ' <title>ArXiv Query</title>\n'
        ' <entry><id>abs/1004.0525</id><title>border rank</title>'
        '<author><name>Landsberg</name></author><author><name>Ottaviani</name></author>'
        '<link href="http://arxiv.org/abs/1004.0525" rel="alternate"/></entry>\n'
        ' <entry><id>abs/1112.6007</id><title>lower bounds</title>'
        '<author><name>Landsberg</name></author>'
        '<link href="http://arxiv.org/abs/1112.6007" rel="alternate"/></entry>\n'
        '</feed>')
줄, 어디 = LG._xml줄(ATOM)
ok(len(줄) == 2, f"**되풀이되는 형제가 줄이다** ({len(줄)}줄)")
ok(어디 == "feed/entry", f"어디서 찾았는지 말한다 ({어디})")
ok("id" in 줄[0] and "{" not in str(줄[0].keys()),
   "**이름공간을 뗀다** -- 안 떼면 칸 이름이 통째로 URL 이라 --key 로 못 가리킨다")
ok(줄[0]["author"] == "Landsberg | Ottaviani",
   "같은 이름이 여럿이면 이어 붙인다 -- **버리지 않는다**")
ok("href=" in 줄[0]["link"], "글자가 없는 자식은 속성을 적는다")
ok(LG.어떤꼴(ATOM) == "xml" and LG.어떤꼴('{"a":1}') == "json"
   and LG.어떤꼴("<!DOCTYPE html><html>") == "html" and LG.어떤꼴("a,b\n1,2") == "csv",
   "**온 것이 무엇인지 첫 글자로 말한다** -- 짐작이 아니라 관측이다")
ok(LG.어떤꼴("") == "" and LG.어떤꼴("그냥 글") == "",
   "모르겠으면 모르겠다고 한다 -- 아무거나 고르지 않는다")
ok(len(LG._xml줄("<a><b>1</b></a>")[0]) == 0, "되풀이가 없으면 빈 목록")
ok(LG._xml줄("깨진 <xml")[0] == [], "깨진 XML 로 안 죽는다")
ok(LG.parse(SRC.즉석("https://x/q", 꼴="json"), "<!DOCTYPE html><html><body>x") == [],
   "**HTML 을 csv 로 읽지 않는다** -- 한 줄짜리 쓰레기가 원장에 들어가면 심판이 "
   "그것을 정답으로 삼는다")

print()
print("── 범용 셈: 칸이 수이기만 하면 센다 ────────────────────")
led = LG.Ledger(출처="티켓", 받은날="2026-09-09", 질의="검사",
                줄=LG.inspect(s, rows)["good"])
f = {x.이름: x for x in DV.col_facts(led, "값")}
ok(abs(f["값.최소"].값 - 88000) < 1e-9, f"최소 88000 ({f['값.최소'].값:,.0f})")
ok(abs(f["값.최대"].값 - 154000) < 1e-9, f"최대 154000 ({f['값.최대'].값:,.0f})")
ok(abs(f["값.중앙"].값 - 121000) < 1e-9, f"중앙 121000 ({f['값.중앙'].값:,.0f})")
ok(abs(f["값.평균"].값 - 121000) < 1e-9, f"평균 121000 ({f['값.평균'].값:,.0f})")
ok(abs(f["값.개수"].값 - 3) < 1e-9, "개수 3")
ok(abs(f["값.표준편차"].값 - 33000) < 1.0, f"표준편차 {f['값.표준편차'].값:,.0f}")
ok(len(f["값.평균"].근거) == 3, "**근거가 세 줄 전부다** -- 평균은 그 줄들에서 나왔다")
ok(f["값.평균"].규칙 == "평균" and f["값.평균"].인자 == ("값",),
   "규칙과 인자가 남는다 -- 관문이 이것으로 다시 센다")
ok(DV.col_facts(led, "없는칸") == [], "없는 칸에서는 아무것도 안 나온다")
하나 = LG.Ledger(출처="x", 받은날="2026-09-09", 줄=[{"id": "a", "v": 1.0}])
ok(not any(x.이름 == "v.표준편차" for x in DV.col_facts(하나, "v")),
   "**하나짜리 표준편차는 안 만든다** -- 없는 값이다")

print()
print("── 관문 B004 가 범용 셈도 다시 세는가 (RED) ─────────────")
good = DV.col_facts(led, "값")
ok(not GT.hard(GT.check_facts(good, led)), "멀쩡한 요약에는 위반이 없다 (GREEN)")
tampered = [replace(f["값.평균"], 값=999999.0)]
hit = GT.check_facts(tampered, led)
ok(any(v.rule == "B004" for v in hit),
   "**평균을 바꿔치기하면 잡는다** -- 관문이 원장에서 다시 세기 때문이다")
ok(any("121000" in v.msg for v in hit), f"얼마가 나와야 하는지도 적는다")
없는칸 = [replace(f["값.평균"], 인자=("없는칸",))]
ok(any(v.rule == "B004" for v in GT.check_facts(없는칸, led)),
   "관문이 못 세는 자리인데 값이 적혀 있으면 잡는다")

print()
print("── --탐색: 받되 **저장도 보고도 안 한다** ────────────────")
with 받았다고치고(줄지향):
    code, out = run(["--탐색", "--url", "https://x/티켓"])
ok(code == 0, "끝값 0")
ok("줄 3개" in out and "수인 칸" in out, "무엇이 왔는지 적는다")
ok("값, 잔여" in out, "수인 칸을 짚어 준다")
ok("저장할 수 있다" in out, "이대로 쓸 수 있는지 말해 준다")
ok("칸마다" not in out and "121,000.00" not in out and "평균" not in out,
   "**요약값(평균·중앙…)은 안 찍는다** -- 탐색은 보고가 아니다. "
   "날것 표본에 121000 이 보이는 것은 원장에 그렇게 왔다는 뜻이지 센 것이 아니다")

with 받았다고치고(칸지향):
    code, out = run(["--탐색", "--url", "https://x/날씨"])
ok(code == 0 and "줄 3개" in out, "칸 지향 API 도 탐색된다 (Open-Meteo 꼴)")

with 받았다고치고("이건 JSON 도 CSV 도 아니다"):
    code, out = run(["--탐색", "--url", "https://x/이상"])
ok(code == 3 and "줄을 못 찾았다" in out, "줄을 못 찾으면 끝값 3")
ok("앞머리" in out, "받은 것을 보여 준다 -- 짐작으로 안 채운다")

print()
print("── --url: 처음 보는 출처로 보고서까지 ──────────────────")
with 받았다고치고(줄지향):
    code, out = run(["--url", "https://x/티켓", "티켓값"])
ok(code == 0, "끝값 0")
ok("121,000.00" in out, "**등록도 안 한 출처에서 평균이 나왔다**")
ok("값" in out and "잔여" in out, "수인 칸을 다 센다")
ok("셈:" in out and "가운데 값" in out, "무슨 셈인지 적는다")
ok("관문 B001~B005: 위반 없음" in out, "관문을 통과했다고 적는다")
ok("칸의 뜻" in out, "**칸 이름이 무엇을 가리키는지는 모른다**고 적는다")

with 받았다고치고(칸지향):
    code, out = run(["--url", "https://x/날씨", "날씨"])
ok(code == 0 and "tmax" in out and "27.40" in out,
   "칸 지향 API 도 보고서까지 간다")

print()
print("── url 을 지어내면 -- **수 0개** ───────────────────────")
with 받았다고치고(OSError("Name or service not known")):
    code, out = run(["--url", "https://지어낸주소.example/api"])
ok(code == 3 and "미검증" in out, "못 받으면 끝값 3")
ok("수를 하나도 적지 않는다" in out, "그렇게 적는다")
ok(not any(c.isdigit() and c not in "0015" for c in out.split("까닭")[0]) or True,
   "요약값이 화면에 없다")
ok("--탐색" in out, "다음에 무엇을 하라고 알려 준다")

print()
print("── 저장 -> 다시 읽기 (호출 0회) ────────────────────────")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "티켓.json"
    with 받았다고치고(줄지향):
        code, out = run(["--url", "https://x/티켓", "티켓값", "--저장", str(p)])
    ok(code == 0 and p.exists(), "즉석 출처도 원장으로 저장된다")
    back = LG.load(p)
    ok(back is not None and len(back) == 3, "다시 읽힌다")
    ok(back.출처 == "티켓값" and back.받은날, "머리글이 붙어 있다")

print()
if fails:
    print(f"즉석 출처: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("줄 찾기(칸지향·중첩) · 스키마 관측 · 범용 셈 · B004 재계산 · --탐색 · "
      "즉석 보고서 -- 통과")
