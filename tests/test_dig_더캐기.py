"""**한 번 부르면 얼마나 가져오는가.**

    python3 tests/test_dig_더캐기.py

`tests/test_dig.py` 는 '있는 것이 빠지지 않는가' 를 본다. 여기는 그 앞뒤 -- **어디까지
가서 캐 오는가**, 그리고 **캐 온 것이 사용자에게 닿기까지 살아 있는가** 를 본다.

실측 2026-09-09, 사용자: "훨씬 더 많은 정보들을 제공해 줬으면", "한 호출당 뽑을 수
있는 최대 정보를 다 담도록". 찾아보니 새는 데가 네 군데였고, **셋은 dig 안이 아니라
그 앞뒤**였다.

    1  extract.합치기 가 json 쪽의 `칸` 을 안 걷었다 -- api 로 받은 것이 통째로 사라짐
    2  bot_tools.run_shell 이 stdout 의 **뒤 4000 자만** 남겼다 -- dig 가 앞에 놓은
       캔값· 메뉴· 값· 영업시간이 먼저 잘림
    3  run.안쪽링크 가 문서 차례대로 집었다 -- `--따라` 예산을 머리말에 다 씀
    4  주소를 모르면 시작할 길이 아예 없었다 -- 모델이 검색 주소를 지어내다 403

**네 군데 다 조용했다.** 오류가 안 났고, 도구는 매번 '성공' 으로 돌아왔다. 그래서
이 검사가 있다 -- 조용히 새는 것은 검사가 붙들지 않으면 아무도 못 본다.

망은 안 탄다. 진짜 쪽 꼴을 먹여서 뽑는 길만 본다.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import extract as EX                                  # noqa: E402
from dig import fetch as FT                                    # noqa: E402
from dig import run as RN                                      # noqa: E402
from dig import search as SC                                   # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("── api 로 받은 것이 합치기에서 사라지지 않는가 ─────────────")
# 열린 API 는 대개 이렇게 답한다. 여기 든 것이 정확히 사용자가 물어본 것이다.
api답 = ('{"query":{"search":[{"title":"안암동","snippet":"성북구의 법정동",'
         '"wordcount":812},{"title":"고려대학교","snippet":"안암동 소재",'
         '"wordcount":9310}]},"batchcomplete":true}')
쪽 = EX.뽑기(api답, "application/json", "https://ko.wikipedia.org/w/api.php")
ok(쪽.get("갈래") == "json" and 쪽.get("칸"), "json 으로 알아보고 칸을 편다")

묶 = EX.합치기([쪽])
싣린것 = " ".join(str(v) for j in 묶["묻힌json"] for v in (j.get("칸") or {}).values())
ok("안암동" in 싣린것 and "고려대학교" in 싣린것,
   "**합치기가 json 의 칸을 싣는다** -- 안 싣던 때는 api 응답이 캔값 말고 통째로 사라졌다")
ok("성북구의 법정동" in 싣린것, "값까지 남는다 -- 제목만 남기면 그것이 '이름 셋' 답이다")
ok(any("api.php" in str(j.get("어디")) for j in 묶["묻힌json"]),
   "어디서 온 것인지 남긴다")

# 내놓기까지 실제로 통과시켜 본다 -- 합치기가 실어도 찍는 자리가 없으면 그만이다.
import contextlib, io                                          # noqa: E402
버퍼 = io.StringIO()


class _가짜응답:
    url = 최종url = "https://ko.wikipedia.org/w/api.php"
    코드, 몸통, 꼴, 왜, 쓴헤더 = 200, api답, "application/json", "", 0

    def __str__(self):
        return "[200] " + self.url


with contextlib.redirect_stdout(버퍼):
    RN.내놓기([_가짜응답()], [쪽], [])
찍힌것 = 버퍼.getvalue()
ok("안암동" in 찍힌것 and "성북구의 법정동" in 찍힌것,
   "**화면까지 나온다** -- 합치기만 고치고 찍는 자리를 안 보면 반쪽이다")

print()
print("── 안쪽으로 팔 때 머리말을 안 판다 ────────────────────────")
# 진짜 쪽의 꼴이다. 앞의 링크는 죄다 머리말이고 메뉴는 뒤에 있다.
가게쪽 = """<html><body>
<nav><a href="/">홈</a><a href="/login">로그인</a><a href="/about">회사소개</a>
<a href="/terms">이용약관</a><a href="/help">고객센터</a><a href="/notice">공지사항</a></nav>
<main>
 <a href="/store/34812/menu?tab=all">동우설렁탕 메뉴 전체보기</a>
 <a href="/store/34812/review">방문자 리뷰 1,287개</a>
 <a href="/store/34812">가게 정보</a>
</main>
<footer><a href="/privacy">개인정보처리방침</a><a href="/policy">운영정책</a></footer>
</body></html>"""
뽑 = EX.뽑기(가게쪽, "text/html", "https://ex.kr/store/34812")
고른것 = RN.안쪽링크(뽑, "https://ex.kr/store/34812", 2, ["메뉴", "리뷰", "가격"])
ok(len(고른것) == 2, f"둘을 고른다 ({len(고른것)})")
ok(any("menu" in u for u in 고른것), "**메뉴 쪽을 고른다** -- 문서에서는 일곱째였다")
ok(any("review" in u for u in 고른것), "리뷰 쪽을 고른다")

# **거르지 않는다 -- 차례만 바꾼다.** 머리말도 뒤에 그대로 남아야 한다. 거르면 그
# 말이 안 든 자리가 없어지는데 답은 자주 거기 있다(dig 규율: 거절이 없다).
줄세운것 = RN.안쪽링크(뽑, "https://ex.kr/store/34812", 99, ["메뉴", "리뷰", "가격"])
머리말자리 = [i for i, u in enumerate(줄세운것)
             if u.endswith(("/login", "/terms", "/help", "/about", "/notice"))]
본문자리 = [i for i, u in enumerate(줄세운것) if "/store/34812/" in u]
ok(본문자리 and 머리말자리 and max(본문자리) < min(머리말자리),
   "**본문 쪽이 머리말보다 앞에 선다** -- 차례대로 집던 때는 예산이 여기서 다 없어졌다")
ok(len(줄세운것) >= 8, f"머리말을 버리지는 않는다 ({len(줄세운것)}개 다 남는다)")

차례대로 = [L["href"] for L in 뽑["링크"]][:3]
ok(차례대로 == ["/", "/login", "/about"],
   "(그때 무엇을 팠는지) 문서 차례로는 홈· 로그인· 회사소개였다")

# 물음의 말이 없어도 꼴만으로 어느 정도 간다 -- 말은 더 얹는 것이지 있어야 하는 게 아니다.
말없이 = RN.안쪽링크(뽑, "https://ex.kr/store/34812", 3, [])
ok(sum(1 for u in 말없이 if "/store/34812" in u) >= 2,
   "**말을 안 줘도 깊은 쪽을 고른다** -- 낱개를 가리키는 꼴(숫자 마디· 깊이)로만")

print()
print("── 머리 없는 표에서 첫 줄을 안 먹는가 ──────────────────────")
# 메뉴판이 거의 이 꼴이다 -- <th> 가 없다. 첫 줄을 머리로 먹으면 그 메뉴가 없어진다.
메뉴표 = ("<table><tr><td>육개장</td><td>9,000원</td></tr>"
         "<tr><td>돼지갈비</td><td>15,000원</td></tr></table>")
줄들 = EX.뽑기(메뉴표, "text/html")["표"][0]
ok(len(줄들) == 2, f"두 줄이 두 줄로 남는다 ({len(줄들)}줄)")
납작 = str(줄들)
ok("육개장" in 납작 and "9,000원" in 납작 and "돼지갈비" in 납작 and "15,000원" in 납작,
   "**첫 메뉴와 그 값이 살아 있다** -- 머리로 먹던 때는 열쇠 자리로 가서 두 줄이 뭉개졌다")
ok(all("칸1" in r for r in 줄들), "머리가 없으면 자리번호로 붙인다")

머리표 = ("<table><tr><th>메뉴</th><th>값</th></tr>"
         "<tr><td>육개장</td><td>9,000원</td></tr></table>")
줄들2 = EX.뽑기(머리표, "text/html")["표"][0]
ok(줄들2 == [{"메뉴": "육개장", "값": "9,000원"}],
   "**문서가 <th> 로 적었으면 그대로 머리로 쓴다** -- 되레 망가뜨리면 안 된다")

줄머리 = ("<table><tr><th>전화</th><td>02-434-1234</td></tr>"
         "<tr><th>영업</th><td>10:00-22:00</td></tr></table>")
줄들3 = EX.뽑기(줄머리, "text/html")["표"][0]
ok(len(줄들3) == 2 and "02-434-1234" in str(줄들3) and "10:00-22:00" in str(줄들3),
   "**줄머리 표(<th>이름</th><td>값</td>)도 안 먹는다** -- 한 칸이라도 td 면 머리가 아니다")

print()
print("── 주소를 모를 때 캐 오는가 ───────────────────────────────")
검색쪽 = """<html><body>
<a href="/settings">설정</a><a href="https://duckduckgo.com/about">회사</a>
<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fblog.kr%2F2026%2F09%2Fjunghwa-matjip&rut=x">
 중화역 맛집 12곳 총정리 - 메뉴와 가격</a>
<a href="https://map.example.kr/place/998877">중화역 맛집 지도</a>
<a href="/y.js?ad_provider=1">광고</a>
</body></html>"""


class _검색응답:
    url = 최종url = "https://html.duckduckgo.com/html/"
    코드, 몸통, 꼴, 왜 = 200, 검색쪽, "text/html", ""
    됐나 = True


검뽑 = EX.뽑기(검색쪽, "text/html", "https://html.duckduckgo.com/html/")
거둔 = SC.거두기([_검색응답()], [검뽑], "중화역 맛집")
주소들 = [d["주소"] for d in 거둔]
ok(any("blog.kr/2026/09/junghwa-matjip" in u for u in 주소들),
   "**껍데기를 벗긴다** -- `?uddg=` 로 감싼 것을 안 풀면 거둔 것이 전부 검색 쪽 주소다")
ok(not any("duckduckgo.com" in u for u in 주소들),
   "**검색 쪽 자기 집은 결과가 아니다** -- 설정· 회사· 광고를 안 싣는다")
ok(any("map.example.kr/place/998877" in u for u in 주소들), "맨 주소도 거둔다")
ok(거둔 and "blog.kr" in 거둔[0]["주소"],
   "**물음의 말이 든 것을 위로 올린다** -- 아래 것부터 파면 예산만 쓴다")
ok(all(d.get("어디서") for d in 거둔), "어느 문에서 나왔는지 남긴다")

# JSON 으로 답하는 문이 더 많다. 거기 주소는 태그가 아니라 값 안에 있다.
제이슨 = ('{"message":{"items":[{"title":["Tensor rank bounds"],'
          '"URL":"https://doi.org/10.1000/abcd","score":9.1}]}}')
제뽑 = EX.뽑기(제이슨, "application/json", "https://api.crossref.org/works")


class _제응답:
    url = 최종url = "https://api.crossref.org/works"
    코드, 몸통, 꼴, 왜 = 200, 제이슨, "application/json", ""
    됐나 = True


거둔2 = SC.거두기([_제응답()], [제뽑], "tensor rank")
ok(any("doi.org/10.1000/abcd" in d["주소"] for d in 거둔2),
   "**json 안에 박힌 주소도 거둔다** -- `<a>` 만 보면 열린 API 는 한 줄도 안 나온다")

이름들 = [이름 for 이름, _ in SC.틀들()]
ok(len(이름들) >= 20, f"문이 여럿이다 ({len(이름들)}개) -- 어느 것이 열릴지 미리 모른다")
ok(len(set(이름들)) == len(이름들), "이름이 안 겹친다 -- 겹치면 --문 으로 못 고른다")
ok(all("{q}" in 꼴 for _n, 꼴 in SC.틀들()), "틀마다 물음 자리가 있다")
ok(len(SC.주소들("가 나", ["ddg-html"])) == 1, "--문 으로 하나만 고를 수 있다")
ok("%EA%B0%80" in SC.주소들("가", ["ddg-html"])[0][1], "한글을 감싼다")

print()
print("── 층이 여럿이면 그만큼 파고드는가 ─────────────────────────")
# 실측 2026-09-09, 사용자: "왜 dig 가 더 깊게 안 들어가지?" -- 합격수기 쪽을
# 걸었는데 **제목만** 나왔다. 못 들어간 것이 아니라 **안 들어가게 짜여 있었다**:
# 안쪽으로 파는 자리가 `if 따라 > 0:` 한 번이라 `--따라` 를 아무리 키워도
# 깊이는 늘 1 이었다. 실제 쪽은 대개 세 층이다.
집 = {
    "https://ex.kr/hall": '<html><body><h1>명예의 전당</h1>'
                          '<a href="/login">로그인</a>'
                          '<a href="/univ/hanyang">한양대 편입 합격수기</a>'
                          '<a href="/univ/sogang">서강대 편입 합격수기</a></body></html>',
    "https://ex.kr/univ/hanyang": '<html><body>'
                                  '<a href="/story/11">학점 2.8로 9관왕, 그 비결</a>'
                                  '<a href="/story/12">학교병행 10관왕 달성</a></body></html>',
    "https://ex.kr/univ/sogang": '<html><body>'
                                 '<a href="/story/21">꼴찌의 반란</a></body></html>',
    "https://ex.kr/story/11": '<html><body><p>본문이다. 나는 2학년 때 학점이 '
                              '2.8이었다. 그해 겨울부터 하루 열두 시간을 …</p></body></html>',
    "https://ex.kr/story/12": '<html><body><p>본문이다. 학교를 다니면서 …</p></body></html>',
    "https://ex.kr/story/21": '<html><body><p>본문이다. 꼴찌였다 …</p></body></html>',
}


def _가짜받기(url, 헤더, 틈=20.0):
    r = FT.응답(url=url, 최종url=url)
    if url in 집:
        r.몸통, r.꼴, r.코드 = 집[url], "text/html", 200
    else:
        r.코드, r.왜 = 404, "HTTP 404"
    return r


진짜 = FT.한번
FT.한번 = _가짜받기
try:
    응답들, 뽑 = RN.캐기(["https://ex.kr/hall"], 앞문만=True, 따라=4,
                       찾을말=["합격수기", "수기"], 깊이=1)
    받은 = {r.url for r in 응답들 if r.몸통}
    ok(any("/univ/" in u for u in 받은), "깊이 1 이면 한 층은 간다 (목록 -> 대학별)")
    ok(not any("/story/" in u for u in 받은),
       "**깊이 1 로는 수기 본문에 못 닿는다** -- 이것이 '제목만 나온다' 의 정체다")

    응답들, 뽑 = RN.캐기(["https://ex.kr/hall"], 앞문만=True, 따라=4,
                       찾을말=["합격수기", "수기"], 깊이=2)
    받은 = {r.url for r in 응답들 if r.몸통}
    ok(sum(1 for u in 받은 if "/story/" in u) >= 2,
       f"**깊이 2 면 수기 본문까지 간다** ({sorted(u[-9:] for u in 받은 if '/story/' in u)})")
    글 = " ".join(x.get("글") or "" for x in 뽑)
    ok("학점이 2.8" in 글 and "꼴찌였다" in 글,
       "**본문이 실제로 들어온다** -- 제목이 아니라 글이")

    앞것 = [r.url for r in 응답들]
    ok(len(앞것) == len(set(앞것)),
       f"**같은 쪽을 두 번 안 받는다** ({len(앞것)}개) -- 홉마다 다시 훑으면 제자리를 돈다")

    응답들, _ = RN.캐기(["https://ex.kr/hall"], 앞문만=True, 따라=40,
                      깊이=5, 쪽상한=3)
    ok(len(응답들) <= 6,
       f"**쪽상한이 고삐가 된다** ({len(응답들)}쪽) -- 없으면 한 줄이 한 집을 통째로 긁는다")

    응답들, _ = RN.캐기(["https://ex.kr/hall"], 앞문만=True, 따라=0, 깊이=3)
    ok(len(응답들) == 1,
       "**--따라 가 0 이면 깊이를 줘도 안 판다** -- 예전 쓰임이 안 깨진다")
finally:
    FT.한번 = 진짜

print()
print("── 캔 것이 사용자에게 닿기까지 살아 있는가 ─────────────────")
# `bot_tools` 는 langchain 없이는 임포트가 안 되므로 이 함수만 떼어 실제로 돌린다.
나무 = ast.parse((ROOT / "bot_tools.py").read_text(encoding="utf-8"))
ns: dict = {}
for n in 나무.body:
    if isinstance(n, ast.FunctionDef) and n.name == "자르기":
        exec(compile(ast.Module(body=[n], type_ignores=[]), "<떼어냄>", "exec"), ns)
자르기 = ns.get("자르기")
ok(자르기 is not None, "**`자르기` 가 bot_tools 에 있다**")

원본 = (ROOT / "bot_tools.py").read_text(encoding="utf-8")
ok('(stdout or "")[-4000:]' not in 원본,
   "**꼬리 4000 자만 남기던 자리가 없어졌다** -- dig 가 앞에 놓은 것이 먼저 잘렸다")

if 자르기:
    글 = "머리" + ("가" * 50000) + "꼬리"
    난것 = 자르기(글, 24000, 6000)
    ok(난것.startswith("머리"), "**앞을 남긴다** -- dig 는 캔값· 메뉴· 값을 맨 앞에 찍는다")
    ok(난것.endswith("꼬리"), "**뒤도 남긴다** -- 로그는 반대로 까닭이 꼬리에 있다")
    ok("잘림" in 난것 and "없는 것이 아니라" in 난것,
       "**얼마나 버렸는지 적는다** -- 말없이 사라지면 모델이 '없는 것' 으로 읽는다")
    ok(len(자르기("짧다", 24000, 6000)) == 2 and 자르기("", 10, 10) == "",
       "짧으면 그대로 둔다 · 빈 것으로 안 죽는다")
    ok(len(자르기(글, 24000, 6000)) < len(글), "길면 줄기는 한다 -- 무한정은 아니다")

    # dig 한 판이 통째로 들어가는가. 예전 예산(4000)으로는 앞의 캔값에서 이미 끊겼다.
    긴출력 = 찍힌것 + "가" * 20000
    ok("안암동" in 자르기(긴출력, 24000, 6000),
       "**dig 출력의 앞머리가 살아남는다** -- 예전 예산으로는 여기가 제일 먼저 없어졌다")
    ok("안암동" not in 자르기(긴출력, 0, 4000),
       "(그때 무엇을 잃었는지) 뒤 4000 자만 남기면 캔 값이 통째로 없다")

print()
if fails:
    print(f"더 캐기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("api 응답이 안 사라짐 · 머리말 대신 본문 쪽을 팜 · 주소를 몰라도 캠 · "
      "캔 것이 화면까지 살아남음 -- 통과")
