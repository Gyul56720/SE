"""조문을 **받아서** 원장에 넣는 경로가 실제로 도는가.

이 컨테이너에서는 law.go.kr 이 조직 egress 정책에 막혀 있어(연결 자체가 안 된다) 실제
호출을 여기서 돌려볼 수 없다. 그래서 네트워크만 가짜로 갈아끼우고 **나머지 전부**를
검사한다 -- 검색 결과 고르기 · 본문 파싱 · 저장 · 저장한 것을 원장으로 다시 읽기 ·
받은 것이 조문이 아닐 때 거부하기 · 인증키를 로그에 안 흘리기.

가짜로 바꾸는 것은 `fetcher` 하나뿐이다. 그래서 여기서 통과하면 진짜 API 를 붙였을 때
남는 위험은 **응답 스키마가 내가 가정한 것과 다른가** 하나로 좁혀진다.

    python3 tests/test_law_fetch.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["LAW_API_TRIES"] = "1"          # 되풀이를 기다리지 않는다

from law import corpus as CP                                          # noqa: E402
from law import fetch as F                                            # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<LawSearch>
 <law><법령명한글>형법</법령명한글><법령일련번호>001766</법령일련번호>
      <시행일자>20200101</시행일자><법령구분명>법률</법령구분명></law>
 <law><법령명한글>형법</법령명한글><법령일련번호>009999</법령일련번호>
      <시행일자>20260101</시행일자><법령구분명>법률</법령구분명></law>
 <law><법령명한글>군형법</법령명한글><법령일련번호>002000</법령일련번호>
      <시행일자>20250101</시행일자><법령구분명>법률</법령구분명></law>
 <law><법령명한글>형법 시행령</법령명한글><법령일련번호>003000</법령일련번호>
      <시행일자>20250101</시행일자><법령구분명>대통령령</법령구분명></law>
</LawSearch>"""

BODY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<법령>
 <기본정보><법령명_한글>형법</법령명_한글><시행일자>20260101</시행일자>
           <공포일자>20250701</공포일자></기본정보>
 <조문>
  <조문단위><조문여부>전문</조문여부><조문내용>제1편 총칙</조문내용></조문단위>
  <조문단위><조문여부>조문</조문여부><조문번호>355</조문번호>
   <조문내용>제355조(횡령, 배임) ①타인의 재물을 보관하는 자가 그 재물을 횡령한 때에는
   가상의 형에 처한다.</조문내용>
   <항><항내용>②전항의 방법으로 제삼자로 하여금 취득하게 한 때에도 같다.</항내용></항>
  </조문단위>
  <조문단위><조문여부>조문</조문여부><조문번호>356</조문번호>
   <조문내용>제356조(업무상의 횡령과 배임) 업무상의 임무에 위배하여 전조의 죄를 범한
   자는 가중하여 처벌한다.</조문내용>
  </조문단위>
 </조문>
</법령>"""

ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Law><resultCode>401</resultCode><resultMsg>인증키가 유효하지 않습니다</resultMsg></Law>"""

OC = "testkey123"


def faker(search=SEARCH_XML, body=BODY_XML):
    calls = []

    def get(url, oc=""):
        calls.append(url)
        return search if "lawSearch" in url else body
    get.calls = calls
    return get


print("[검색] 이름이 정확히 같은 것만 고른다")
rows = F.parse_search(SEARCH_XML)
ok(len(rows) == 4, f"네 건을 읽는다 (얻은 값 {len(rows)})")
got = F.pick(rows, "형법")
ok(got and got["이름"] == "형법",
   f"'형법' 을 고른다 -- 군형법·형법 시행령이 아니다 (얻은 값 {got and got['이름']})")
ok(got["일련번호"] == "009999",
   f"이름이 같은 것이 여럿이면 시행일자가 늦은 것 (얻은 값 {got['일련번호']})")
ok(F.pick(rows, "상법") is None, "이름이 같은 것이 없으면 고르지 않는다")

print()
print("[본문] 조문내용·항내용을 순서대로 잇고, 편·장 제목은 뺀다")
meta, text = F.parse_law(BODY_XML)
ok(meta["이름"] == "형법" and meta["시행일자"] == "20260101",
   f"법령명과 시행일자를 읽는다 (얻은 값 {meta})")
ok("제1편 총칙" not in text, "조문여부가 '조문' 이 아닌 것은 안 싣는다")
ok(text.count("제355조") == 1 and "②전항의" in text,
   "조문 본문과 항이 함께 실린다")
ok(len(F._HEAD.findall(text)) == 2, f"조문 머리 2개 (얻은 값 {len(F._HEAD.findall(text))})")

print()
print("[물러서기] 스키마를 못 알아보면 모든 칸을 잇는다")
_, t = F.parse_law("<x><a>제9조(가상) 내용이다.</a><b>덧붙임</b></x>")
ok("제9조" in t and "덧붙임" in t, f"조문단위가 없어도 글을 건진다 (얻은 값 {t!r})")

print()
print("[한 바퀴] 받아서 저장하고, 저장한 것을 원장으로 다시 읽는다")
tmp = Path(tempfile.mkdtemp())
r = F.pull("형법", OC, tmp, fetcher=faker())
ok(r["조문머리"] == 2 and r["담긴조문"] == 2,
   f"받은 조문 머리 수와 원장에 잡힌 조문 수가 같다 (얻은 값 {r['조문머리']}/{r['담긴조문']})")
saved = Path(r["저장"])
ok(saved.name == "형법.txt", f"법령명으로 저장한다 (얻은 값 {saved.name})")
head = saved.read_text(encoding="utf-8").splitlines()[0]
ok(head.startswith("#") and "20260101" in head,
   f"첫 줄에 시행일자를 적는다 -- 언제 것인지 모르는 원장은 못 쓴다 ({head[:60]})")
ok("받은 날" in head, "받은 날짜도 적는다")

c = CP.load(tmp)
ok(c.has("형법", "355") and c.has("형법", "356"), "원장이 두 조문을 다 담았다")
ok("보관하는 자" in c.text("형법", "355"), "조문 본문이 온전하다")

print()
print("[검색을 건너뛰기] 일련번호를 직접 주면 본문만 받는다")
f2 = faker()
F.pull("형법", OC, tmp, fetcher=f2, mst="009999")
ok(all("lawSearch" not in u for u in f2.calls),
   f"검색을 부르지 않는다 (부른 것 {len(f2.calls)}개)")

print()
print("[거부] 조문이 아닌 것은 원장에 넣지 않는다")
tmp2 = Path(tempfile.mkdtemp())
try:
    F.pull("형법", OC, tmp2, fetcher=faker(body=ERROR_XML))
    ok(False, "인증키 오류 응답을 저장해 버렸다")
except RuntimeError as e:
    ok("조문 머리" in str(e), f"조문 머리가 없으면 거부한다 ({e})")
ok(not list(tmp2.glob("*.txt")), "거부했으면 파일도 안 남는다")

try:
    F.pull("상법", OC, tmp2, fetcher=faker())
    ok(False, "이름이 다른 것을 받아 버렸다")
except RuntimeError as e:
    ok("이름이 정확히 같은" in str(e), f"고를 것이 없으면 거부한다 ({e})")

print()
print("[인증키] 로그에도 오류에도 그대로 나가지 않는다")
ok(F.mask(OC) == "te********", f"앞 두 글자만 남긴다 (얻은 값 {F.mask(OC)})")
url = F._url(F.SEARCH, OC, target="law", query="형법")
ok(f"OC={OC}" in url, "URL 에는 들어간다 -- 안 그러면 호출이 안 된다")


def boom(*a, **k):
    raise OSError("연결 거부")


import urllib.request                                                  # noqa: E402
urllib.request.urlopen = boom
try:
    F._get(url, OC)
    ok(False, "실패했는데 예외가 안 났다")
except RuntimeError as e:
    ok(OC not in str(e), f"오류 메시지에 인증키가 없다 ({e})")
    ok(F.mask(OC) in str(e), "가린 형태로만 나온다")
    ok("query=" not in str(e), "URL 질의문도 통째로 싣지 않는다")

print()
print("[판례] **원장을 채울 수 있으면 L004 는 금지가 아니라 대조가 된다**")
_목록 = """<?xml version="1.0" encoding="UTF-8"?><PrecSearch>
  <prec><판례일련번호>123456</판례일련번호><사건번호>2018다287522</사건번호>
    <사건명>건물인도</사건명><법원명>대법원</법원명><선고일자>20200521</선고일자>
    <사건종류명>민사</사건종류명></prec>
  <prec><판례일련번호>999999</판례일련번호><사건번호>2020다1111</사건번호>
    <사건명>손해배상</사건명><법원명>대법원</법원명><선고일자>20210101</선고일자></prec>
</PrecSearch>"""
_행 = F.parse_prec_search(_목록)
ok([r["사건번호"] for r in _행] == ["2018다287522", "2020다1111"],
   f"판례 목록에서 사건번호를 읽는다 (얻은 값 {[r['사건번호'] for r in _행]})")
ok(_행[0]["법원명"] == "대법원" and _행[0]["선고일자"] == "20200521",
   "법원명·선고일자도 읽는다 -- 사건번호만으로는 특정이 안 된다")

_본문 = """<?xml version="1.0" encoding="UTF-8"?><PrecService>
  <판례일련번호>123456</판례일련번호><사건번호>2018다287522</사건번호>
  <사건명>건물인도</사건명><법원명>대법원</법원명><선고일자>20200521</선고일자>
  <판시사항>공유물의 소수지분권자가 ...</판시사항>
  <판결요지>인도를 청구할 수 없다 ...</판결요지>
</PrecService>"""
_메타, _글 = F.parse_prec(_본문)
ok(_메타["사건번호"] == "2018다287522", "본문에서도 사건번호를 읽는다")
ok("판시사항" in _글 and "판결요지" in _글, f"판시사항·판결요지를 담는다 (얻은 값 {_글[:30]!r})")

_보관 = Path(tempfile.mkdtemp())


def _가짜(url, oc=""):
    return _본문 if "lawService" in url else _목록


_받음 = F.pull_prec("공유물", OC, _보관, fetcher=_가짜)
ok(len(_받음) == 2, f"검색 결과를 모두 받는다 (얻은 값 {len(_받음)})")
_원장 = CP.load_cases(_보관)
ok("2018다287522" in _원장,
   f"저장한 것을 판례 원장으로 다시 읽는다 -- 받는 것과 잡히는 것은 다른 일이다 (얻은 값 {list(_원장)})")
ok(_원장["2018다287522"]["법원"] == "대법원" and _원장["2018다287522"]["선고일자"] == "20200521",
   f"첫 줄에서 법원·선고일자가 되읽힌다 (얻은 값 {_원장.get('2018다287522')})")

_빈보관 = Path(tempfile.mkdtemp())
_없음 = """<?xml version="1.0"?><PrecService><판례일련번호>7</판례일련번호>
  <판시사항>사건번호가 없다</판시사항></PrecService>"""
_결과 = F.pull_prec("", OC, _빈보관, sid="7", fetcher=lambda url, oc="": _없음)
ok(not list(_빈보관.glob("*.txt")),
   "사건번호가 없으면 저장하지 않는다 -- 원장에 쓰레기가 들어가면 심판이 그것을 정답으로 삼는다")
ok(_결과 and _결과[0].get("실패"),
   f"조용히 건너뛰지 않고 왜 안 담았는지 적는다 (얻은 값 {_결과})")

print()
if fails:
    print(f"받기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("받기: 조문 고르기·파싱·저장·되읽기 · 판례 목록·본문·거부 · 인증키 가리기 -- 통과")
