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
print("[분당 한도] **제한당하면 원장이 못 차고, 원장이 안 차면 심판이 아무것도 못 본다**")
# 판례는 검색 1회 + 본문 N회를 몰아 부른다(`--건수 20` 이면 21회). 0.5초 간격은
# 순간 간격만 묶을 뿐이라 분당 120회가 나간다. 그래서 세 가지를 못 박는다.

# 1) 제한에 걸리면 **되풀이하지 않는다** -- 되풀이는 더 세게 두드리는 것이다.
_불린횟수 = [0]


def _제한(*a, **k):
    _불린횟수[0] += 1
    raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)


urllib.request.urlopen = _제한
try:
    F._get(url, OC)
    ok(False, "제한인데 예외가 안 났다")
except F.Throttled as e:
    ok(_불린횟수[0] == 1,
       f"429 는 한 번만 부르고 멈춘다 (얻은 값 {_불린횟수[0]}회)")
    ok(OC not in str(e), "제한 메시지에도 인증키가 없다")
except Exception as e:                                                # noqa: BLE001
    ok(False, f"Throttled 가 아니라 {type(e).__name__} 이 났다: {e}")

# 2) 본문이 제한이라고 말해도 (HTTP 200 이어도) 멈춘다.
class _응답:
    def __init__(self, s): self._s = s
    def read(self): return self._s.encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


urllib.request.urlopen = lambda *a, **k: _응답(
    "짧은 시간 내 과도한 호출이 발생하여 이용이 제한되었습니다")
try:
    F._get(url, OC)
    ok(False, "본문이 제한이라 말했는데 그냥 돌려줬다")
except F.Throttled:
    ok(True, "응답 본문이 제한이라 말하면 200 이어도 멈춘다")

# 3) **이어한다** -- 목록에 사건번호가 실려 오므로 원장에 있는 것은 본문을 안 부른다.
_보관2 = Path(tempfile.mkdtemp())
(_보관2 / "2018다287522.txt").write_text(
    "# 2018다287522 · 대법원 · 20200521 · 건물인도\n# 받은 것\n\n[판시사항]\n...\n",
    encoding="utf-8")
_부름 = []


def _센다(u, oc=""):
    _부름.append("본문" if "lawService" in u else "검색")
    return _본문 if "lawService" in u else _목록


_받음2 = F.pull_prec("공유물", OC, _보관2, fetcher=_센다)
ok(_부름.count("본문") == 1,
   f"원장에 있는 것은 본문을 안 부른다 (얻은 값 본문 {_부름.count('본문')}회 · 목록 2건)")
ok(any(r.get("이미") for r in _받음2), "이미 있던 것이라고 적는다")

# 4) 목록과 본문이 다른 사건을 가리키면 담지 않는다 -- 조용한 오답이 된다.
_엉뚱 = _본문.replace("<판례일련번호>123456</판례일련번호>", "<판례일련번호>999999</판례일련번호>")
_보관3 = Path(tempfile.mkdtemp())
_받음3 = F.pull_prec("공유물", OC, _보관3,
                    fetcher=lambda u, oc="": (_엉뚱 if "lawService" in u else _목록))
ok(any("본문은" in (r.get("실패") or "") for r in _받음3),
   f"목록·본문의 사건번호가 어긋나면 원장에 안 넣고 말한다 "
   f"(얻은 값 {[r.get('실패') for r in _받음3]})")
ok(not (_보관3 / "2020다1111.txt").exists(),
   "어긋난 건은 파일로 남지 않는다")

print()
print("[전부 훑기] **범위를 적어야 L004 가 기각으로 올라간다**")


def _쪽(n, 총=5):
    시작 = (n - 1) * 2 + 1
    if 시작 > 총:
        return f"<r><totalCnt>{총}</totalCnt></r>"
    항 = "".join(
        f"<prec><판례일련번호>{i}</판례일련번호><사건번호>2020다{i}</사건번호>"
        f"<법원명>대법원</법원명><선고일자>2020010{i}</선고일자>"
        f"<사건명>사건{i}</사건명></prec>"
        for i in range(시작, min(시작 + 2, 총 + 1)))
    return f"<r><totalCnt>{총}</totalCnt>{항}</r>"


def _훑기가짜(u, oc=""):
    if "lawService" in u:
        i = u.split("ID=")[1].split("&")[0]
        return (f"<r><판례일련번호>{i}</판례일련번호><사건번호>2020다{i}</사건번호>"
                f"<법원명>대법원</법원명><선고일자>2020010{i}</선고일자>"
                f"<사건명>사건{i}</사건명><판시사항>...</판시사항></r>")
    return _쪽(int(u.split("page=")[1].split("&")[0]))


ok(F.prec_total("<r><totalCnt>91234</totalCnt></r>") == 91234,
   "총 건수를 읽는다 -- 며칠짜리인지 몇 분짜리인지가 이 수로 갈린다")

_훑 = Path(tempfile.mkdtemp())
_쪽들 = list(F.sweep_prec("전체", OC, _훑, fetcher=_훑기가짜, display="2"))
ok(len(_쪽들) == 3 and len(CP.load_cases(_훑)) == 5,
   f"쪽을 넘겨 가며 끝까지 훑는다 (얻은 값 쪽 {len(_쪽들)} · 원장 {len(CP.load_cases(_훑))}건)")
ok(CP.load_case_scope(_훑).get("전부") is True,
   f"끝까지 갔으면 범위를 적는다 (얻은 값 {CP.load_case_scope(_훑)})")

# **중간에 끊긴 훑기는 '전부' 라고 적지 않는다.** 적으면 L004 가 아직 안 받은
# 판례를 지어냈다고 기각한다 -- 과잉 기각하는 심판은 맞는 답도 버린다.
_반 = Path(tempfile.mkdtemp())
list(F.sweep_prec("전체", OC, _반, fetcher=_훑기가짜, display="2", pages=1))
ok(not CP.load_case_scope(_반).get("전부"),
   f"덜 훑었으면 범위를 안 적는다 (얻은 값 {CP.load_case_scope(_반)})")

# 이어한다: 다시 부르면 이미 받은 쪽은 본문을 안 부른다.
_본문호출 = [0]


def _센다2(u, oc=""):
    if "lawService" in u:
        _본문호출[0] += 1
    return _훑기가짜(u, oc)


list(F.sweep_prec("전체", OC, _반, fetcher=_센다2, display="2"))
ok(_본문호출[0] == 3,
   f"이미 받은 2건은 본문을 다시 안 부른다 (얻은 값 {_본문호출[0]}회 · 남은 3건)")
ok(CP.load_case_scope(_반).get("전부") is True, "이어서 끝까지 가면 그때 범위를 적는다")

print()
print("[인증키] **`.env` 에 넣으라 해 놓고 `.env` 를 안 읽으면 안내가 거짓말이 된다**")
# 실측(같은 병을 두 번): law/ocr.py 가 이름 목록만 llm_pool 과 맞추고 .env 를 안 읽어
# "키가 없다" 고 답했다. 이 파일도 같았다 -- docstring 은 .env 를 가리키는데 코드는
# os.environ 만 봤다. systemd 는 EnvironmentFile 로 받지만 SSH 셸은 안 받는다.
import os                                                             # noqa: E402

_옛OC = os.environ.pop("LAW_API_OC", None)
_ROOT = Path(__file__).resolve().parent.parent
_env = _ROOT / ".env"
_있던env = _env.read_text(encoding="utf-8") if _env.is_file() else None
try:
    _env.write_text("LAW_API_OC=검사용키123\n", encoding="utf-8")
    ok(F.oc_from_env() == "검사용키123",
       f"`.env` 의 LAW_API_OC 를 읽는다 (얻은 값 {F.mask(F.oc_from_env())})")
    os.environ["LAW_API_OC"] = "환경변수가우선"
    ok(F.oc_from_env() == "환경변수가우선",
       "이미 환경에 있으면 그것이 우선이다 -- systemd 로 들어온 값을 .env 가 덮지 않는다")
finally:
    os.environ.pop("LAW_API_OC", None)
    if _있던env is None:
        _env.unlink(missing_ok=True)
    else:
        _env.write_text(_있던env, encoding="utf-8")
    if _옛OC is not None:
        os.environ["LAW_API_OC"] = _옛OC

print()
print("[며칠짜리 훑기] **끊기는 것이 정상이다. 이어지는가가 문제다**")
# 민법 판례는 분당 20회로 며칠이 걸린다. 그 사이에 한 번도 안 끊길 리 없다.
_보관2 = Path(tempfile.mkdtemp())


def _가짜목록(쪽: int, 총: int, 크기: int = 2) -> str:
    시작 = (쪽 - 1) * 크기
    if 시작 >= 총:
        칸 = ""
    else:
        칸 = "".join(
            f"<prec><판례일련번호>{i}</판례일련번호>"
            f"<사건번호>2020다{1000 + i}</사건번호><법원명>대법원</법원명>"
            f"<선고일자>2020.01.01</선고일자><사건명>사건{i}</사건명></prec>"
            for i in range(시작, min(시작 + 크기, 총)))
    return f'<?xml version="1.0"?><PrecSearch><totalCnt>{총}</totalCnt>{칸}</PrecSearch>'


def _가짜본문(ident: str) -> str:
    i = int(ident)
    return ('<?xml version="1.0"?><PrecService>'
            f'<사건번호>2020다{1000 + i}</사건번호><법원명>대법원</법원명>'
            f'<선고일자>2020.01.01</선고일자><사건명>사건{i}</사건명>'
            '<판시사항>판시사항이다.</판시사항>'
            '<판결요지>판결요지다. 이것으로 본문이 있다고 본다.</판결요지>'
            '</PrecService>')


_부른것 = []


def _훑기가짜(url: str, oc: str = "") -> str:
    _부른것.append(url)
    if "lawService" in url:
        return _가짜본문(re.search(r"ID=(\d+)", url).group(1))
    쪽 = int(re.search(r"page=(\d+)", url).group(1)) if "page=" in url else 1
    return _가짜목록(쪽, 5)


import re                                                             # noqa: E402
# 두 쪽만 돌고 멈춘다 -- 한도에 걸려 끊긴 셈이다.
_난것 = list(F.sweep_prec("민법", OC, _보관2, fetcher=_훑기가짜, display="2", pages=2))
_자리 = F.훑던자리(_보관2)
ok(len(_난것) == 2 and _자리.get("민법", {}).get("마지막쪽") == 2,
   f"쪽마다 어디까지 갔는지 적는다 (얻은 값 {_자리})")
ok(not CP.load_case_scope(_보관2).get("전부"),
   "덜 받았으면 '전부' 라고 안 적는다")

# **여기가 조용한 버그였다.** 이어할 때 받음을 0부터 세면 `받음 >= 총` 이 영영
# 참이 안 되고, 훑기가 멀쩡히 끝나도 `_받은범위.json` 이 안 써진다. 그러면
# 원장은 영원히 '아직 덜 받았다' 로 남고 L004 가 기각으로 안 올라간다 --
# 다 받아 놓고도 못 쓰는 꼴이다.
_이어난것 = list(F.sweep_prec("민법", OC, _보관2, fetcher=_훑기가짜, display="2",
                              이어=True))
ok(_이어난것 and _이어난것[0]["쪽"] == 3,
   f"이어하면 다음 쪽부터 (얻은 값 {[x['쪽'] for x in _이어난것]})")
ok(CP.load_case_scope(_보관2).get("전부"),
   "이어서 끝까지 갔으면 **'전부' 라고 적는다** -- 이래야 L004 가 기각으로 올라간다")
ok(len(CP.load_cases(_보관2)) == 5,
   f"다섯 건이 원장에 있다 (얻은 값 {len(CP.load_cases(_보관2))})")
_범위 = CP.load_case_scope(_보관2)
ok(_범위.get("훑은것") and _범위["훑은것"][0]["키"] == "민법",
   f"무엇을 훑었는지 쌓아 둔다 -- 민법은 한 검색어로 다 못 긁는다 (얻은 값 {_범위.get('훑은것')})")

# 거르개는 **그대로 실어 보내기만 한다.** 어느 인자가 맞는지 여기서 정하지 않는다.
_부른것.clear()
list(F.sweep_prec("민법", OC, Path(tempfile.mkdtemp()), fetcher=_훑기가짜,
                  display="2", pages=1, params={"search": "2", "org": "400201"}))
ok(any("search=2" in u and "org=400201" in u for u in _부른것),
   f"거르개를 그대로 실어 보낸다 (얻은 값 {[u.split('?')[1][:70] for u in _부른것[:1]]})")
ok(F._훑기키("민법", {"search": "2"}) != F._훑기키("민법", None),
   "검색어가 같아도 거르개가 다르면 다른 훑기다")

# **색인을 쪽마다 다시 만들면 열기 횟수가 제곱으로 는다.** 민법 본문검색 16,624건을
# 100건씩 167쪽으로 훑으면 약 140만 번이다. 훑기가 색인을 한 번 만들어 넘겨주는지
# 본다 -- 파일 여는 것을 세어서.
_센다 = {"n": 0}
_진짜읽기 = Path.read_text


def _세는읽기(self, *a, **k):
    if self.suffix == ".txt":
        _센다["n"] += 1
    return _진짜읽기(self, *a, **k)


_보관3 = Path(tempfile.mkdtemp())
Path.read_text = _세는읽기
try:
    list(F.sweep_prec("민법", OC, _보관3, fetcher=_훑기가짜, display="1"))
finally:
    Path.read_text = _진짜읽기
# 5건을 1건씩 5쪽. 쪽마다 색인을 다시 만들면 0+1+2+3+4 = 10번 읽는다.
# 한 번만 만들면 0번이다(빈 원장에서 시작하므로).
ok(_센다["n"] <= 2,
   f"색인을 쪽마다 다시 안 만든다 (파일 읽기 {_센다['n']}회 · 쪽마다 만들면 10회)")
ok(len(CP.load_cases(_보관3)) == 5,
   f"그래도 다섯 건이 다 저장됐다 (얻은 값 {len(CP.load_cases(_보관3))})")
# 색인을 안 넘기면 지금까지대로 스스로 만든다 -- 낱건 받기가 안 깨진다.
_난것2 = F.pull_prec("", OC, _보관3, fetcher=_훑기가짜,
                     rows=[{"일련번호": "0", "사건번호": "2020다1000",
                            "법원명": "대법원", "선고일자": "2020.01.01", "사건명": "사건0"}])
ok(_난것2 and _난것2[0].get("이미"),
   f"색인 없이 부르면 스스로 만들어 이미 있는 것을 알아본다 (얻은 값 {_난것2})")

print()
print("[저장소에 안 넣는다] **범위 기록을 커밋하면 심판이 뒤집힌다**")
# `_받은범위.json` 에 `전부: true` 가 있으면 `covers_cases()` 가 참이 되고 L004 가
# "원장에 없는 판례 = 지어낸 것" 으로 **기각**을 올린다. 그런데 판례 본문은 커밋을
# 안 하니 새로 받은 사람의 원장은 비어 있다. 그러면 **맞는 인용까지 전부 기각된다.**
# 과잉 기각하는 심판은 맞는 답도 버린다.
import subprocess                                                     # noqa: E402
_뿌리 = Path(__file__).resolve().parent.parent
for _막을것 in ("law/precedents/2020다1.txt",
                "law/precedents/_받은범위.json",
                "law/precedents/_훑던자리.json",
                "law/corpus/민법.txt"):
    _답 = subprocess.run(["git", "check-ignore", "-q", _막을것],
                         cwd=str(_뿌리), capture_output=True)
    ok(_답.returncode == 0, f"{_막을것} 은 저장소에 안 들어간다")
# README 는 들어간다 -- 무엇을 어디서 받는지 적어 둔 자리다.
_답 = subprocess.run(["git", "check-ignore", "-q", "law/precedents/README.md"],
                     cwd=str(_뿌리), capture_output=True)
ok(_답.returncode != 0, "README 는 그대로 추적한다")

print()
print("[행위시법] **그날 시행 중이던 판** -- 지금 법으로 옛일을 재지 않는다")
# 형법 제1조 제1항 "행위 시의 법률에 의한다"; 민사는 법률불소급 + 부칙 경과규정.
# 판례 대조에서 더 크게 어긋난다 -- 2015년 판결은 2015년 법을 적용한 것이라
# 현행 조문과 대 보면 옛 판결이 전부 틀린 것처럼 나온다.
_판 = [{"이름": "상법", "시행일자": "20120415", "일련번호": "A"},
       {"이름": "상법", "시행일자": "20200101", "일련번호": "B"},
       {"이름": "상법", "시행일자": "20260301", "일련번호": "C"},
       {"이름": "군상법", "시행일자": "20190101", "일련번호": "X"}]
ok(F.pick_at(_판, "상법", "2019-02-15")["일련번호"] == "A",
   "2019년 사건에는 2012년 판 (2020년 판은 아직 시행 전이다)")
ok(F.pick_at(_판, "상법", "2026-07-01")["일련번호"] == "C", "2026년 사건에는 2026년 판")
ok(F.pick_at(_판, "상법", "2012-04-15")["일련번호"] == "A", "시행일 당일은 그 판이 시행 중이다")
ok(F.pick_at(_판, "상법", "2010-01-01") is None,
   "그날보다 늦은 판밖에 없으면 **None** -- 최신으로 돌아가지 않는다")
ok(F.pick(_판, "상법")["일련번호"] == "C", "시행일을 안 주면 지금까지대로 최신")
ok(F.pick_at(_판, "상법", "20190215")["일련번호"] == "A"
   and F.pick_at(_판, "상법", "2019.2.15")["일련번호"] == "A",
   "날짜 꼴이 달라도 같게 읽는다")

# 판이 하나뿐이면 **행위시법을 못 한다고 말해야 한다** -- 조용히 최신을 쓰면 안 된다.
_한판 = """<?xml version="1.0"?><LawSearch>
 <law><법령명한글>상법</법령명한글><법령일련번호>C</법령일련번호>
  <시행일자>20260301</시행일자></law></LawSearch>"""
_보관 = Path(tempfile.mkdtemp())
try:
    F.pull("상법", OC, _보관, fetcher=lambda u, oc="": _한판, when="2019-02-15")
    ok(False, "그때 판이 없는데 조용히 받았다")
except RuntimeError as e:
    ok("시행 중이던 판을 못 찾았다" in str(e) and "판이 하나뿐" in str(e),
       f"판이 하나뿐이면 그렇게 말하고 멈춘다 (얻은 값 {str(e)[:60]}...)")
ok(not list(_보관.glob("*.txt")), "못 찾았으면 아무것도 저장하지 않는다")

# **자를 먼저 의심하라.** "판이 하나뿐" 은 두 가지가 겹쳐 보인다 -- API 가 정말
# 현행만 준 것과, 우리 자가 원소 이름을 못 알아본 것. 화면은 똑같고 결론은 정반대다.
# 실측: parse_search 가 <law>·<Law>·<법령> 세 이름만 알아봤다. target=eflaw 가
# 다른 이름으로 주면 0행이 되고, history 는 그것을 "판이 없다" 로 읽는다.
_다른이름 = """<?xml version="1.0"?><LawSearch>
 <eflaw><법령명한글>상법</법령명한글><법령일련번호>A</법령일련번호>
  <시행일자>20120415</시행일자></eflaw>
 <eflaw><법령명한글>상법</법령명한글><법령일련번호>B</법령일련번호>
  <시행일자>20200101</시행일자></eflaw></LawSearch>"""
_읽음 = F.parse_search(_다른이름)
ok(len(_읽음) == 2 and {r["일련번호"] for r in _읽음} == {"A", "B"},
   f"원소 이름이 <law> 가 아니어도 법령명을 가진 원소를 행으로 읽는다 (얻은 값 {len(_읽음)}행)")
ok({r["시행일자"] for r in _읽음} == {"20120415", "20200101"},
   f"그래서 판 2개가 판 2개로 보인다 -- 0행을 '판이 하나뿐' 이라 읽지 않는다 (얻은 값 {_읽음})")
_이력행, _어디 = F.history("상법", OC, fetcher=lambda u, oc="": _다른이름)
ok(len(_이력행) == 2, f"history 도 그 판들을 본다 (얻은 값 {len(_이력행)}행 · target={_어디})")

# 뿌리 <LawSearch> 자신을 행으로 세지 않는다 -- iter() 로 훑으면 후손에 법령명이
# 있으므로 뿌리도 걸린다. 그러면 있지도 않은 판이 하나 늘어난다.
ok(len(F.parse_search("""<?xml version="1.0"?><LawSearch><target>eflaw</target>
 <eflaw><법령명한글>상법</법령명한글><시행일자>20120415</시행일자></eflaw>
 </LawSearch>""")) == 1, "뿌리는 행이 아니다 -- 법령명을 직속 자식으로 가진 것만 행이다")

# 아는 이름이 있으면 그것만 쓴다. 꼴로 찾기는 **못 찾았을 때만** 나선다.
ok(len(F.parse_search(_한판)) == 1, "<law> 를 아는 자리에서는 지금까지대로 읽는다")

# 시점 원장은 현행 원장을 안 덮는다. 모든 도구가 --corpus 를 받으므로 이것만으로 쓰인다.
ok(str(F.as_of_dir(Path("law/corpus"), "2019-02-15")).endswith("@2019-02-15"),
   f"시점 원장은 따로 담는다 (얻은 값 {F.as_of_dir(Path('law/corpus'), '2019-02-15')})")

print()
if fails:
    print(f"받기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("받기: 조문 고르기·파싱·저장·되읽기 · 판례 목록·본문·거부 · 인증키 가리기 -- 통과")
