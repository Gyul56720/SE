"""날 한글이 든 주소를 dig 가 받는지 붙든다.

실측 2026-09-12: 봇이 `dig/run.py --url 'https://search.naver.com/...?query=한글'` 로 캐다
`UnicodeEncodeError: 'ascii' codec can't encode characters` 로 죽었고, 보고에는 **"시스템
내부의 인코딩 제한으로 한글 검색어 처리가 거부된다"** 고 적혔다. 제한이 아니라 빠진 한 줄이었다 --
`dig/search.py` 의 질의는 quote 를 지나는데 `--url` 과 따라가는 안쪽 링크는 안 지났다.
**잘못된 진단은 고칠 자리를 가린다** -- 그래서 이 검사가 그 자리를 붙든다.

붙드는 것 여섯: (1) 질의의 한글이 인코딩된다, (2) 경로의 한글도, (3) 이미 인코딩된 것은 두 번
인코딩되지 않는다, (4) 한글 집은 IDNA 로, (5) 멀쩡한 아스키 주소는 **한 글자도 안 바뀐다**,
(6) 받기()가 그 주소로 urllib 까지 간다 -- UnicodeEncodeError 로 죽지 않는다(망은 안 쓴다).

실행: python3 tests/test_dig_주소정규화.py
"""
from __future__ import annotations

import shutil
import sys
import urllib.parse
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from dig import fetch as FT  # noqa: E402
from dig import search as S  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== 날 한글이 든 주소를 아스키로 ==")
for 원, 기대, 말 in [
    ("https://search.naver.com/search.naver?query=한글시험",
     "https://search.naver.com/search.naver?query=%ED%95%9C%EA%B8%80%EC%8B%9C%ED%97%98", "질의의 한글"),
    ("https://ko.wikipedia.org/wiki/한글", "https://ko.wikipedia.org/wiki/%ED%95%9C%EA%B8%80", "경로의 한글"),
    ("https://example.com/a b", "https://example.com/a%20b", "공백"),
]:
    난 = FT.주소정규화(원)
    ok(난 == 기대 and 난.isascii(), f"{말}: {난}")

ok(FT.주소정규화("https://x.org/?q=%ED%95%9C%EA%B8%80&p=1") == "https://x.org/?q=%ED%95%9C%EA%B8%80&p=1",
   "**이미 인코딩된 것은 두 번 인코딩하지 않는다** (%ED -> %25ED 가 되면 검색이 깨진다)")
ok(FT.주소정규화("https://한글.kr/길").startswith("https://xn--"), "한글 집은 IDNA 로")

print("\n== 멀쩡한 아스키 주소는 한 글자도 안 바뀐다 ==")
그대로 = [t[1].replace("{q}", "abc") for t in S.틀들()] + [
    "https://api.github.com/search/repositories?q=a+b&per_page=20",
    "https://x.org/p;v=1,2/~u!a$b&c'd(e)*f=g?x=y#z",
]
안바뀐것 = [u for u in 그대로 if FT.주소정규화(u) != u]
ok(안바뀐것 == [], f"검색 틀 {len(S.틀들())}개와 까다로운 주소가 그대로다 (바뀐 것: {안바뀐것})")

print("\n== 정규화는 urlopen 직전 한 자리에서만 (망은 안 쓴다) ==")
# 왜 한 자리인가: 실측 2026-09-12, 받기() 에서 미리 바꿨더니 한글 집이 punycode 가 되어
# 집 이름으로 갈래를 정하던 곳(tests/test_jaso_crawl 의 가짜 문)이 깨졌다. precheck 가 잡았다.
import urllib.request  # noqa: E402

간것 = []


class _가짜응답:
    status = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def read(self):
        return b"ok"

    def geturl(self):
        return 간것[-1]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_원열기 = urllib.request.urlopen
try:
    urllib.request.urlopen = lambda req, timeout=None: (간것.append(req.full_url), _가짜응답())[1]
    한 = "https://한글집.com/길?q=한글"
    r = FT.받기(한, 틈=1)
    ok(간것 and 간것[0].isascii() and "xn--" in 간것[0] and "%ED%95%9C" in 간것[0],
       f"**urlopen 에는 아스키가 간다** ({간것[0]})")
    ok(r.url == 한, f"**응답의 url 은 부른 쪽이 준 그대로** -- 집 이름으로 갈래를 정하는 곳이 안 깨진다 ({r.url})")
finally:
    urllib.request.urlopen = _원열기

try:
    urllib.request.Request(FT.주소정규화("https://search.naver.com/search.naver?query=한글"),
                           headers={"User-Agent": "t"})
    ok(True, "urllib.request.Request 가 이 주소를 받는다 -- 원래 오류가 났던 자리")
except UnicodeEncodeError as e:
    ok(False, f"아직 ascii 오류가 난다: {e}")


print("\n== 망점검: 되는지/안 되는지를 코드가 말한다 (가짜 응답, 망 안 씀) ==")
from dig import search as SC  # noqa: E402


def _응답들(만들기):
    def 가짜여럿(urls, 동시=8, 틈=0, 벌수=0):
        return [만들기(u) for u in urls]
    return 가짜여럿


_원여럿 = FT.여럿
try:
    FT.여럿 = _응답들(lambda u: FT.응답(url=u, 코드=200, 몸통="<html>ok</html>", 꼴="text/html"))
    r = SC.망점검(틈=1, 적기=False)
    ok(r["됐나"] and r["열린문"] == r["전체"] and "바깥이 된다" in r["진단"], f"다 열리면 된다고 한다 ({r['진단']})")

    FT.여럿 = _응답들(lambda u: FT.응답(url=u, 코드=0, 왜="프록시가 끊었다 -- 이 환경의 나가는 길이 막혔다"))
    r = SC.망점검(틈=1, 적기=False)
    ok(not r["됐나"] and "나가는 길이 막혀" in r["진단"], f"**프록시면 코드 문제가 아니라고 말한다** ({r['진단']})")

    FT.여럿 = _응답들(lambda u: FT.응답(url=u, 코드=0, 왜="20.0초 안에 답이 없다"))
    r = SC.망점검(틈=1, 적기=False)
    ok(not r["됐나"] and "시간 초과" in r["진단"], f"전부 시간 초과면 그렇다고 ({r['진단']})")

    # 서버가 HTTP 로 답했으면 **망은 된 것**이다 -- 그 문이 막았을 뿐. 이 둘을 가르는 것이 요점이다.
    FT.여럿 = _응답들(lambda u: FT.응답(url=u, 코드=403, 몸통="", 왜="HTTP 403 -- 막았다"))
    r = SC.망점검(틈=1, 적기=False)
    ok(not r["됐나"] and r["닿았나"] and "망은 된다" in r["진단"] and "망 탓으로 적지 마라" in r["진단"],
       f"**문이 막은 것과 망이 안 되는 것을 가른다** ({r['진단'][:60]})")
    FT.여럿 = _응답들(lambda u: FT.응답(url=u, 코드=0, 왜="안 닿는다 -- 모르는 까닭"))
    r = SC.망점검(틈=1, 적기=False)
    ok(not r["됐나"] and not r["닿았나"] and "지어내지 마라" in r["진단"], "까닭을 모르면 지어내지 말라고 적는다")
    보 = SC.망보고(r)
    ok("dig 망점검" in 보 and 보.count("\n") >= r["전체"], f"문마다 한 줄 ({보.count(chr(10))}줄)")
finally:
    FT.여럿 = _원여럿

print("\n== 문 목록 꼴 검사 · 문마다 쓸 만한 결과 수 ==")
# 실측 2026-09-12(VM): `!개선 수집망 url에 인스타그램, x, meta 추가해줘` 가 문 셋을
# `https://www.google.com/search?q=site:...` 로 넣었다. **꼴은 멀쩡해서 시뮬이 초록이었다.**
# 그 문이 답을 주는지는 두드려야 안다 -- 그래서 결과 수를 센다(HTTP 200 이어도 0 이면 닫힌 문이다).
ok(SC.틀검사() == [], f"지금 문 목록은 성립한다 ({SC.틀검사()})")
_탈 = SC.틀검사([("a", "https://x/?q={q}"), ("a", "https://y/?q={q}"),
               ("b", "ftp://z/{q}"), ("c", "https://w/?q=1")])
ok(len(_탈) == 3 and any("겹친다" in x for x in _탈) and any("http(s)" in x for x in _탈)
   and any("{q}` 가 없다" in x for x in _탈), f"이름 겹침·꼴 아님·물음자리 없음을 잡는다 ({len(_탈)}개)")

_원여럿2 = FT.여럿
try:
    def _한문만준다(urls, 동시=8, 틈=0, 벌수=0):
        return [FT.응답(url=u, 코드=200, 꼴="text/html",
                      몸통=('<a href="https://example.org/a">첫</a><a href="https://example.net/b">둘</a>'
                          if "mojeek" in u else "<html>결과 없음</html>")) for u in urls]
    FT.여럿 = _한문만준다
    r = SC.망점검(틈=1, 고른것=["mojeek", "brave"], 적기=False)
    센 = {d["이름"]: d["결과"] for d in r["문들"]}
    ok(센 == {"mojeek": 2, "brave": 0},
       f"**200 이어도 결과가 0 이면 그 문은 닫힌 것** -- 문마다 따로 센다 ({센})")
    ok("결과   2" in SC.망보고(r), "보고에 문마다 결과 수가 적힌다")
    ok(len(r["문들"]) == 2, f"`고른것` 으로 새 문만 두드린다 ({len(r['문들'])}개)")
    ok("그런 이름의 문이 없다" in SC.망점검(틈=1, 고른것=["없는문"], 적기=False)["진단"], "없는 이름은 그렇다고 말한다")
finally:
    FT.여럿 = _원여럿2

print("\n== 문 원장: 잰 것이 지식이 된다 -- 결과 0 이었던 집을 문으로 넣으면 코드가 잡는다 ==")
# 사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." "구글은 봇을 막는다" 는 세상 지식을 구조로
# 못 준다고 했던 것이 틀렸다 -- 재서 쌓으면 된다. 구글 문 셋이 다시 들어오면 여기서 막힌다.
_원장집 = Path(tempfile.mkdtemp(prefix="문원장-"))
_원여럿3 = FT.여럿
try:
    def _한집만거절(urls, 동시=8, 틈=0, 벌수=0):
        out = []
        for u in urls:
            if "deny.example" in u:                # 403 -- 200 을 한 번도 안 준다
                out.append(FT.응답(url=u, 코드=403, 몸통="", 왜="HTTP 403 -- 막았다"))
            else:
                out.append(FT.응답(url=u, 코드=200, 꼴="text/html",
                                 몸통='<a href="https://example.org/a">첫</a><a href="https://example.net/b">둘</a>'))
        return out
    FT.여럿 = _한집만거절
    막문 = [("거절-g", "https://deny.example/search?q={q}"), ("mojeek", "https://www.mojeek.com/search?q={q}")]
    ok(SC.틀검사(막문, repo=_원장집) == [], "잰 적이 없으면 꼴 검사만 -- 아직 모른다")
    _원틀 = SC.틀
    SC.틀 = tuple(막문)
    try:
        for _ in range(2):                         # 두 번 재야 집으로 인정한다(한 번 403 은 사고일 수 있다)
            r = SC.망점검(틈=1, repo=_원장집)
    finally:
        SC.틀 = _원틀
    ok((_원장집 / "dig" / "door_ledger.jsonl").is_file() and len(SC.문원장읽기(_원장집)) == 4, "망점검이 문마다 원장에 적는다")
    지 = SC.문지식(_원장집)
    ok(지.get("deny.example", {}).get("이백") == 0 and 지.get("mojeek.com", {}).get("있음") == 2,
       f"집마다 200 받은 수와 결과 있음을 센다 ({지})")
    ok(list(SC.막힌집들(_원장집)) == ["deny.example"], f"200 을 한 번도 못 받은 집만 막힌 집이다 ({list(SC.막힌집들(_원장집))})")
    탈 = SC.틀검사(막문, repo=_원장집)
    ok(len(탈) == 1 and 탈[0].startswith("거절-g") and "한 번도 200 을 못 받았다" in 탈[0],
       f"**거절하는 집을 문으로 넣으면 코드가 잡는다** -- 세상 지식이 누적된 측정이 됐다 ({탈[0][:60]})")
    ok(SC.틀검사([("x-g", "https://deny2.example/search?q={q}")], repo=_원장집) == [], "다른 집은 아직 안 쟀으니 안 잡는다 -- 지어내지 않는다")
    # **제 문을 거절하면 안 된다.** 실측 2026-09-12(VM): 첫 판은 '결과 0' 을 막힌 집으로 쳐서 저장소의 제 문
    # 일곱 개(bing · wiki-ko · wiki-en · wikidata · openlibrary · startpage · mojeek)를 전부 찍었고 이 검사가
    # 빨개졌다. 까닭은 계수기였다 -- 답이 제 집 안에 있는 문은 '바깥으로 나가는 주소' 가 0 이다.
    _원장집2 = Path(tempfile.mkdtemp(prefix="문원장2-"))
    try:
        (_원장집2 / "dig").mkdir()
        import json as _js, time as _tm
        때 = _tm.strftime("%Y-%m-%dT%H:%M:%SZ", _tm.gmtime())
        with open(_원장집2 / "dig" / "door_ledger.jsonl", "w", encoding="utf-8") as f:
            for 이름, 꼴 in SC.틀:                  # 모든 제 문이 200 인데 결과 0 이었다고 적어 둔다
                집 = SC._집(urllib.parse.urlsplit(꼴.replace("{q}", "q")).netloc)
                for _ in range(3):
                    f.write(_js.dumps({"때": 때, "이름": 이름, "집": 집, "코드": 200, "결과": 0, "왜": "", "말": "t"},
                                      ensure_ascii=False) + "\n")
        ok(SC.막힌집들(_원장집2) == {}, "200 을 받았으면 결과가 0 이어도 막힌 집이 아니다")
        ok(SC.틀검사(repo=_원장집2) == [], "**저장소의 제 문을 거절하지 않는다** -- 잘못된 검사는 없느니만 못하다")
    finally:
        shutil.rmtree(_원장집2, ignore_errors=True)
finally:
    FT.여럿 = _원여럿3
    shutil.rmtree(_원장집, ignore_errors=True)

_cmd2 = (뿌리 / "dig" / "discord_cmd.py").read_text(encoding="utf-8")
ok('말.startswith("망 ")' in _cmd2, "`!수집 망 <문이름>` 으로 봇도 새 문만 두드린다")

# dig 에는 구글 문이 없다 -- 보고가 "구글이 차단했다" 고 말할 근거가 애초에 없다
ok(not any("google" in 꼴 for _이름, 꼴 in SC.틀들()), "**dig 에 구글 문은 없다** -- 구글 차단은 지어낸 원인이었다")
_cmd = (뿌리 / "dig" / "discord_cmd.py").read_text(encoding="utf-8")
ok("망점검" in _cmd and "{PREFIX} 망" in _cmd, "`!수집 망` 으로 봇도 그 자리에서 잰다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("dig 주소정규화: 한글 질의·경로·집 · 두 번 인코딩 안 함 · 멀쩡한 주소 보존 · 망점검 -- 통과")
