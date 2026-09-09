"""**긁어모으는 자리가 거르지 않는가.**

    python3 tests/test_dig.py

`brief/` 검사와 정반대의 것을 붙든다. 거기서는 '못 믿을 것이 원장에 안 들어가는가'
를 보았고, 여기서는 **'있는 것이 빠지지 않는가'** 를 본다. 목적이 다르면 검사도
반대여야 한다 -- 여기서 거절을 검사하면 찾아 준 것이 없어진다.

망은 안 탄다(이 컨테이너는 나가는 길이 막혀 있다). `dig.fetch.한번` 을 갈아 끼워
받는 길을 검사하고, 뽑는 길은 진짜 쪽 꼴로 검사한다.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import extract as EX                                  # noqa: E402
from dig import fetch as FT                                    # noqa: E402
from dig import run as RN                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


쪽 = '''<!DOCTYPE html><html><head>
<meta charset="utf-8"><title>동우설렁탕 - 안암</title>
<meta property="og:title" content="동우설렁탕">
<meta name="geo.position" content="37.5859,127.0294">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Restaurant","name":"동우설렁탕",
 "telephone":"02-923-3355",
 "address":{"streetAddress":"서울특별시 성북구 고려대로24길 15"},
 "aggregateRating":{"ratingValue":"4.4","reviewCount":"1287"},
 "openingHours":["Mo-Fr 06:00-21:00"],
 "hasMenu":{"hasMenuSection":[{"name":"탕류","hasMenuItem":[
   {"name":"설렁탕","offers":{"price":"11000","priceCurrency":"KRW"}},
   {"name":"도가니탕","offers":{"price":"17000","priceCurrency":"KRW"}}]}]},
 "review":[{"author":{"name":"김**"},"reviewRating":{"ratingValue":"5"},
            "reviewBody":"국물이 진하고 깍두기가 맛있다. 웨이팅 10분."}]}
</script>
<script>window.__NEXT_DATA__ = {"props":{"store":{"주차":"2시간 무료","웨이팅":"평균 12분"}}};</script>
</head><body>
<h1>동우설렁탕</h1>
<table><tr><th>메뉴</th><th>가격</th></tr>
<tr><td>설렁탕</td><td>11,000원</td></tr><tr><td>수육 (소)</td><td>28,000원</td></tr></table>
<ul><li>영업시간 06:00 ~ 21:00</li><li>주차 가능</li></ul>
<p>평점 4.4 / 5 · 리뷰 1,287개 · 안암역 2번 출구 도보 3분</p>
<a href="/review?p=2">리뷰 더보기</a><a href="https://other.example/x">남의 집</a>
<img alt="설렁탕 11,000원 사진">
</body></html>'''

x = EX.뽑기(쪽, "text/html", "https://ex.kr/store/1")

print("── 한 쪽에서 **갈래를 다 뽑는가** ──────────────────────")
ok(x["갈래"] == "html", "html 로 읽는다")
ok(x["제목"] == "동우설렁탕", f"제목({x['제목']})")
평 = x["묻힌표"][0]
ok(평.get("hasMenu.hasMenuSection[0].hasMenuItem[0].name") == "설렁탕",
   "**묻힌 메뉴 이름을 편다** -- 안 펴면 사람이 못 찾고, 못 찾으면 없는 것과 같다")
ok(평.get("hasMenu.hasMenuSection[0].hasMenuItem[1].offers.price") == "17000",
   "메뉴마다 **값**이 붙어 나온다 -- '★4.3' 만 주던 자리")
ok(평.get("aggregateRating.reviewCount") == "1287", "리뷰 수")
ok(평.get("review[0].reviewBody", "").startswith("국물이"), "**리뷰 본문**까지 온다")
ok(평.get("openingHours[0]") == "Mo-Fr 06:00-21:00", "영업시간")

print()
print("── 묻힌 json (window.__NEXT_DATA__) ────────────────────")
칸 = {k: v for j in x["묻힌json"] for k, v in j["칸"].items()}
ok(칸.get("props.store.웨이팅") == "평균 12분",
   "**<script> 안에 박힌 상태 덩어리를 판다** -- 진짜가 여기 있을 때가 많다")
ok(any(j["어디"] == "__NEXT_DATA__" for j in x["묻힌json"]), "어디서 왔는지 적는다")

print()
print("── 표 · 목록 · 링크 · alt ──────────────────────────────")
ok(x["표"][0][0] == {"메뉴": "설렁탕", "가격": "11,000원"}, "표를 머리로 읽는다")
ok(len(x["표"][0]) == 2, "줄을 다 담는다")
ok("주차 가능" in x["목록"][0], "목록도 담는다")
ok(any(L["href"] == "/review?p=2" for L in x["링크"]), "링크를 담는다")
ok("설렁탕 11,000원 사진" in x["글"],
   "**img alt 도 글이다** -- 메뉴 사진 이름·값이 거기 있는 쪽이 있다")

print()
print("── 캔 값: **구조가 없다고 값이 없는 것이 아니다** ────────")
캔 = x["캔값"]
ok("11,000원" in 캔["가격"] and "28,000원" in 캔["가격"], f"가격({캔['가격'][:4]})")
ok("02-923-3355" in 캔["전화"], "전화")
ok(any("4.4" in v for v in 캔["평점"]), f"평점({캔['평점'][:3]})")
ok("서울특별시 성북구 고려대로24길 15" in 캔["주소"],
   f"**주소가 안 잘린다** -- 잘린 주소는 못 찾아가는 주소다 ({캔.get('주소')})")
ok("37.5859,127.0294" in 캔.get("좌표", []),
   "**meta 에만 있는 좌표도 캔다** -- 눈에 보이는 글만 캐면 통째로 놓친다")

print()
print("── 안 죽는다 · 깨진 것도 담는다 ─────────────────────────")
ok(EX.뽑기("", "")["갈래"] == "글", "빈 몸통으로 안 죽는다")
깨진 = EX.뽑기("<html><body><p>값 5,000원 <div><table><tr><td>가", "text/html")
ok("5,000원" in 깨진["캔값"]["가격"],
   "**닫는 태그가 어긋나도 뽑은 것은 남는다** -- 다 버리면 거기 있던 값이 없어진다")
ok(EX._느슨하게json('{"a":1};') == {"a": 1}, "끝에 세미콜론이 붙어도 읽는다")
ok(EX._느슨하게json('{"a":1}{"b":2}') == {"a": 1}, "이어 붙은 덩어리도 첫 것은 살린다")
ok(EX._느슨하게json("전혀 아님") is None, "아닌 것은 None -- 억지로 안 만든다")
ok(EX._중괄호덩어리('x = {"a":"}"} ;', 0) == {"a": "}"},
   "**문자열 안의 중괄호를 안 센다** -- 세면 덩어리가 엉뚱한 데서 끊긴다")

j = EX.뽑기('{"items":[{"n":"김밥","p":3500}]}', "application/json")
ok(j["갈래"] == "json" and j["칸"]["items[0].p"] == 3500, "json 도 펴서 준다")
ok(EX.뽑기("<feed><entry><id>a</id></entry></feed>", "")["갈래"] == "xml", "xml 갈래")

print()
print("── 합치기: **다른 문이 다른 것을 준다** ──────────────────")
쪽2 = ('<html><head><meta property="og:site_name" content="다이닝"></head><body>'
       '<p>웨이팅 평균 15분 · 포장 가능 · 1인 15,000원</p>'
       '<a href="/menu">메뉴</a></body></html>')
묶 = EX.합치기([x, EX.뽑기(쪽2, "text/html", "https://m.ex.kr/store/1")])
ok(묶["쪽수"] == 2 and len(묶["출처"]) == 2, "쪽마다 어디서 왔는지 남긴다")
ok("15,000원" in 묶["캔값"]["가격"] and "11,000원" in 묶["캔값"]["가격"],
   "**두 문의 값이 다 남는다** -- 하나만 보면 하나를 잃는다")
ok(묶["머리표"].get("og:site_name") == "다이닝", "머리표도 합친다")
ok(len([L for L in 묶["링크"] if L["href"] == "/menu"]) == 1, "겹치는 링크는 하나로")

print()
print("── 곁문: 주인이 열어 둔 다른 문만 ───────────────────────")
문 = FT.곁문("https://www.ex.kr/store/1?a=2")
ok(any(u.startswith("https://m.ex.kr/") for u in 문), "모바일 쪽")
ok(any("/amp" in u for u in 문), "AMP")
ok(any("format=json" in u for u in 문), "그 쪽 JSON 끝점 꼴")
ok(any("web.archive.org" in u for u in 문), "공개 아카이브 -- 그 쪽이 죽었을 때")
ok(len(set(문)) == len(문), "겹치는 문은 안 낸다")
ok(FT.곁문("주소가 아님") == [], "주소가 아니면 빈 목록 -- 안 죽는다")

print()
print("── 받기: **한 번 해 보고 안 된다고 말하지 않는다** ───────")
부른것 = []


def 가짜(url, 헤더, 틈=20.0):
    부른것.append((url, 헤더.get("User-Agent", "")[:16]))
    if len(부른것) < 3:                       # 앞의 두 헤더벌은 막힌다
        return FT.응답(url=url, 코드=403, 왜="HTTP 403 -- 막았다")
    return FT.응답(url=url, 코드=200, 몸통=쪽, 꼴="text/html", 최종url=url)


진짜한번 = FT.한번
FT.한번 = 가짜
try:
    r = FT.받기("https://ex.kr/store/1")
    ok(r.됐나 and r.쓴헤더 == 2,
       f"**헤더벌을 돌려쓴다** -- 하나가 403 이어도 다음 것으로 (쓴헤더={r.쓴헤더})")
    ok(len({h for _, h in 부른것}) == 3, "실제로 다른 UA 로 불렀다")

    부른것.clear()
    FT.한번 = lambda url, 헤더, 틈=20.0: FT.응답(url=url, 코드=403, 왜="HTTP 403 -- 막았다")
    r2 = FT.받기("https://ex.kr/x")
    ok(not r2.됐나 and "403" in r2.왜,
       "**다 막히면 까닭을 들고 온다** -- 빈손과 '403이라 못 받았다' 는 다른 말이다")

    # 캐기: 앞문이 되어도 곁문을 본다
    FT.한번 = 가짜
    부른것.clear()
    나온것 = FT.캐기("https://ex.kr/store/1")
    ok(len(나온것) > 1, f"**앞문이 되어도 곁문을 본다** ({len(나온것)}쪽)")
finally:
    FT.한번 = 진짜한번

print()
print("── 안쪽 링크: 같은 집 안으로만 ──────────────────────────")
안 = RN.안쪽링크(x, "https://ex.kr/store/1", 10)
ok(any("ex.kr/review" in u for u in 안), "같은 집 링크는 따라간다")
ok(not any("other.example" in u for u in 안), "**남의 집은 안 간다** -- 가면 끝이 없다")
ok(not any(u.endswith((".jpg", ".css", ".js")) for u in 안), "그림·css 는 안 판다")

print()
print("── CLI ──────────────────────────────────────────────────")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = RN.main(argv)
    return code, buf.getvalue()


code, out = run([])
ok(code == 3 and "주소를 줘라" in out, "주소가 없으면 끝값 3 · 무엇을 하라고 알려 준다")

FT.한번 = 가짜
부른것.clear()
try:
    code, out = run(["--url", "https://ex.kr/store/1", "--앞문만", "--찾", "웨이팅"])
    ok(code == 0, "받았으면 끝값 0")
    ok("설렁탕" in out and "11000" in out, "**메뉴와 값이 화면에 나온다**")
    ok("국물이 진하고" in out, "리뷰 본문도 나온다")
    ok("웨이팅" in out and "평균 12분" in out, "--찾 이 그 말 자리를 짚어 준다")
    ok("## 캔 값" in out and "## 묻힌표 1" in out and "## 표 1" in out,
       "갈래마다 절을 나눠 낸다")

    FT.한번 = lambda url, 헤더, 틈=20.0: FT.응답(
        url=url, 코드=0, 왜="프록시가 끊었다 -- 이 환경의 나가는 길이 막혔다")
    code, out = run(["--url", "https://ex.kr/x", "--앞문만"])
    ok(code == 3 and "한 쪽도 못 받았다" in out, "한 쪽도 못 받으면 끝값 3")
    ok("다음에 무엇을 할지" in out and "프록시가 끊었다" in out,
       "**까닭마다 다음에 무엇을 할지 적는다** -- 빈손으로 끝내지 않는다")
finally:
    FT.한번 = 진짜한번

print()
if fails:
    print(f"dig: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("갈래 전부 뽑기(묻힌표·묻힌json·표·목록·alt) · 캔값(가격·전화·평점·주소·좌표) · "
      "깨진 것도 남김 · 곁문 · 헤더 돌려쓰기 · 같은 집 안으로만 · CLI -- 통과")
