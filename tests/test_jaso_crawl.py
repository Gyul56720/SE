"""**오래 도는 수집기가 제 자리에 담고, 두 번 안 받고, 멈추는가.**

    python3 tests/test_jaso_crawl.py

망은 안 탄다 -- `dig.fetch.한번` 을 갈아 끼운다.

## 붙드는 것 넷

1. **K001 -- 무시 규칙에 안 잡히면 한 자도 안 쓴다.** 여기는 남의 글이 실제로 앉는
   유일한 자리이고, 한 번 커밋되면 `git rm` 을 해도 히스토리에 남는다.
2. **질의를 코드에 안 박는다.** 있는 것에서 뽑고, 받은 것에서 넓힌다.
3. **두 번 안 받는다.** 주소로도 본문 해시로도 -- 미러가 표본을 부풀린다.
4. **멈춘다.** 시간이 되거나 `.그만` 이 생기면. 안 멈추는 수집기는 남의 쪽을 두드리는
   기계가 된다.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import fetch as DF                                       # noqa: E402
from jaso import crawl as CR                                      # noqa: E402
from jaso import keep as KP                                       # noqa: E402
from jaso import ledger as LG                                     # noqa: E402
from jaso import mine as MN                                       # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


본문 = ("2025년 3월, 로그 파이프라인이 여섯 시간씩 밀리는 화면을 처음 봤습니다. "
       "배치가 끝나야 지표가 갱신되는 구조였습니다.\n\n"
       "저는 수집 경로를 스트리밍으로 바꾸는 일을 맡았고 반영 지연을 35분에서 4분으로 "
       "줄였습니다. 2주간 24000명씩 재니 클릭률이 2.1%에서 2.6%로 올랐습니다.\n\n"
       "그때부터 지표를 의심하는 쪽으로 일한다는 것을 배웠습니다. " * 2)
검색쪽 = """<html><body>
<a href="https://ex.com/a">무봉테크 합격 자기소개서 후기</a>
<a href="https://ex.com/b">데이터 분석 직무 합격 자소서</a>
</body></html>"""


def 터(d, **덮기):
    a = argparse.Namespace(
        분=1, 씨앗=["합격 자기소개서 예시"], 회사="", 직무="", 학과="",
        몇=5, 틈=0.0, 최소=100, 씨앗주소=[], 따라=20, 걸름=0.0, 집참기=3,
        곳=str(Path(d) / "보기"),
        잰곳=str(Path(d) / "잰형식"), 문항곳=str(Path(d) / "문항"),
        그만="", 모델=False, 살펴만=False)
    for k, v in 덮기.items():
        setattr(a, k, v)
    return a


print("── 질의를 코드에 안 박는다 ────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    ok(CR.씨앗뽑기(터(d, 씨앗=[])) == [],
       "**아무것도 없으면 물을 것이 없다** -- 목록을 박으면 그 밖은 영영 안 찾아진다")
    씨 = CR.씨앗뽑기(터(d, 씨앗=[], 회사="무봉테크", 직무="데이터 분석"))
    ok(any("무봉테크" in x for x in 씨) and any("데이터 분석" in x for x in 씨),
       f"준 것에서 뽑는다 ({씨})")
넓힌것 = CR.넓히기(["무봉테크 합격 자소서 후기", "무봉테크 자소서 항목 정리",
                 "합격 자소서 후기 모음"], "합격 자소서")
ok(넓힌것, f"**받은 쪽 제목에서 다음 질의가 는다** ({넓힌것})")
ok(all("합격 자소서" in x for x in 넓힌것), "씨앗을 물고 넓힌다")
ok(not any(w in " ".join(넓힌것) for w in ("네이버", "블로그", "바로")),
   "아무 데나 걸리는 말은 안 붙인다")
ok(CR.모델질의(["합격 자소서"], 묻기=lambda _: "1. 우수 자소서\n2) 자소서 사례\n")
   == ["우수 자소서", "자소서 사례"], "모델이 낸 질의에서 번호를 뗀다")


print("\n── **K001 -- 무시 규칙이 없으면 한 자도 안 쓴다** ────────")
with tempfile.TemporaryDirectory() as d:      # 저장소 밖 -> 무시 규칙에 안 잡힌다
    p, vs = KP.담기(본문, "https://ex.com/a", Path(d) / "보기")
    ok(p is None and any(v.규칙 == "K001" for v in vs),
       "저장소 밖(무시 규칙 밖)에는 안 쓴다")
    ok(not (Path(d) / "보기").exists() or not list((Path(d) / "보기").glob("*.txt")),
       "**파일이 하나도 안 생긴다** -- '거절했다' 고 말만 하고 쓰면 뜻이 없다")
ok(KP.무시되나(KP.보기DIR / "x.txt"),
   "**딸려 있는 `jaso/corpus/보기/` 는 무시 규칙에 잡힌다** (회귀 못)")
ok(not KP.무시되나(ROOT / "README.md"), "(대조군) 아무 데나 무시된다고 하지 않는다")
ok(LG.hard(KP.검사(ROOT / "Public_agent", "u")), "K003 -- 공개 폴더는 막는다")
ok(LG.hard(KP.검사(KP.보기DIR, "")), "K002 -- 출처 없으면 막는다")


print("\n── 돌린다 -- 담고, 재고, 두 번 안 받는다 ────────────────")
진짜 = DF.한번
받은수 = {"n": 0}


def 가짜(url, 헤더, 틈=20.0):
    if any(w in url for w in ("duckduckgo", "bing", "mojeek")):
        return DF.응답(url=url, 최종url=url, 코드=200, 몸통=검색쪽, 꼴="text/html")
    if "ex.com" in url:
        받은수["n"] += 1
        꼬리 = "" if url.endswith("/a") else " 다른 편입니다. " * 8
        return DF.응답(url=url, 최종url=url, 코드=200,
                     몸통=f"<html><body><article>{본문}{꼬리}</article></body></html>",
                     꼴="text/html")
    return DF.응답(url=url, 코드=404, 왜="HTTP 404")


DF.한번 = 가짜
try:
    with tempfile.TemporaryDirectory() as d:
        곳 = KP.보기DIR / "_검사"           # 무시 규칙 안쪽에 임시로
        잰곳 = MN.잰것DIR / "_검사"
        a = 터(d, 곳=str(곳), 잰곳=str(잰곳))
        try:
            보고 = CR.돌리기(a)
            ok(보고["담음"] >= 2, f"본문 {보고['담음']}편을 담았다")
            ok(보고["잼"] >= 2, f"잰 것 {보고['잼']}편도 같이 담았다")
            ok(len(KP.읽기(곳)) == 보고["담음"], "담은 만큼 되읽힌다")
            ok(all(출처 for _, 출처, _ in KP.읽기(곳)), "출처가 붙는다")
            담긴글 = (list(Path(곳).glob("*.txt"))[0]).read_text(encoding="utf-8")
            ok("# 출처:" in 담긴글 and "저장소에 안 올라간다" in 담긴글,
               "파일 머리에 출처와 경고가 붙는다")
            잰편 = MN.읽기(잰곳)
            ok(잰편 and all(not LG.hard(MN.검사(x)) for x in 잰편),
               "**잰 것은 M001 을 지난다** -- 본문이 안 섞였다")

            앞 = 받은수["n"]
            보고2 = CR.돌리기(터(d, 곳=str(곳), 잰곳=str(잰곳)))
            ok(보고2["담음"] == 0, "**두 번째 바퀴는 한 편도 안 담는다** -- 주소를 안다")
            ok(받은수["n"] == 앞, f"아예 다시 안 받는다 ({받은수['n'] - 앞}번 더 받음)")

            (Path(곳) / ".그만").touch()
            보고3 = CR.돌리기(터(d, 곳=str(곳), 잰곳=str(잰곳), 씨앗=["다른 것"]))
            ok("멈췄다" in 보고3["왜"], f"**`.그만` 이 있으면 멈춘다** ({보고3['왜']})")
        finally:
            for x in (곳, 잰곳):
                for f in Path(x).glob("*"):
                    f.unlink()
                Path(x).rmdir() if Path(x).exists() else None
finally:
    DF.한번 = 진짜


print("\n── **탐침을 좁힌다** -- 받자마자 걸러 안 담는다 ────────")
논문 = ("초록 본 연구는 편입학 전형의 효과를 분석하였다. Keywords: 편입, 전형. "
       "참고문헌 목록은 다음과 같다. DOI:10.1234/abcd Vol. 12 No. 3 pp. 45-67 "
       "한국교육학회 등재 논문이다. 저자명 홍길동. 본 연구는 게재되었다. " * 4)
좋은글 = ("2025년 3월, 파이프라인이 밀리는 화면을 처음 봤습니다. 저는 스트리밍으로 "
        "바꾸는 일을 맡았고 지연을 35분에서 4분으로 줄였습니다. 그때 저는 지표를 "
        "의심하는 습관을 얻었습니다. 지원 동기도 거기서 나왔고, 직무에 필요한 역량을 "
        "그 경험에서 배웠습니다. 입사 후에도 그렇게 일하겠습니다. " * 3)


def 가짜3(url, 헤더, 틈=20.0):
    if any(w in url for w in ("duckduckgo", "bing", "mojeek")):
        return DF.응답(url=url, 최종url=url, 코드=200, 꼴="text/html", 몸통=(
            "<html><body><a href='https://논문집.com/1'>논문 하나</a>"
            "<a href='https://논문집.com/2'>논문 둘</a>"
            "<a href='https://논문집.com/3'>논문 셋</a>"
            "<a href='https://논문집.com/4'>논문 넷</a>"
            "<a href='https://수기집.com/1'>합격 수기</a></body></html>"))
    글 = 좋은글 if "수기집" in url else 논문
    return DF.응답(url=url, 최종url=url, 코드=200, 꼴="text/html",
                 몸통=f"<html><head><title>편입 자소서</title></head>"
                      f"<body><article>{글}</article></body></html>")


DF.한번 = 가짜3
try:
    with tempfile.TemporaryDirectory() as d:
        곳, 잰곳 = KP.보기DIR / "_좁힘", MN.잰것DIR / "_좁힘"
        try:
            보고 = CR.돌리기(터(d, 곳=str(곳), 잰곳=str(잰곳), 몇=5, 걸름=0.0))
            ok(보고["담음"] == 1,
               f"**점수 낮은 것은 안 담는다** (담음 {보고['담음']}편 · "
               f"거름 {보고['걸름']}편) -- 담고 나서 거르면 그 사이에 mine 이 "
               "오염된 값을 집계한다")
            ok(보고["걸름"] >= 3, f"논문은 걸렸다 ({보고['걸름']}편)")
            ok(보고["집건너뜀"] >= 1,
               f"**같은 집에서 낮은 것이 이어지면 그 집을 그만 판다** "
               f"({보고['집건너뜀']}번 건너뜀) -- 차단 목록을 안 박고 전적으로 민다")
            남 = KP.읽기(곳)
            ok(len(남) == 1 and "수기집" in 남[0][1], f"남은 것은 수기뿐 ({남[0][1]})")
        finally:
            for x2 in (곳, 잰곳):
                if Path(x2).exists():
                    for f in Path(x2).glob("*"):
                        f.unlink()
                    Path(x2).rmdir()

    with tempfile.TemporaryDirectory() as d:
        곳, 잰곳 = KP.보기DIR / "_안좁힘", MN.잰것DIR / "_안좁힘"
        try:
            보고 = CR.돌리기(터(d, 곳=str(곳), 잰곳=str(잰곳), 몇=5,
                            걸름=-9999.0, 집참기=99))
            ok(보고["담음"] >= 2,
               f"(대조군) 걸름을 내리면 다 담는다 ({보고['담음']}편) -- "
               "**거르는 것은 옵션이지 몰래 하는 일이 아니다**")
        finally:
            for x2 in (곳, 잰곳):
                if Path(x2).exists():
                    for f in Path(x2).glob("*"):
                        f.unlink()
                    Path(x2).rmdir()
finally:
    DF.한번 = 진짜
ok("차단 목록을 코드에 박지 않는다" in (CR.__doc__ or ""),
   "**목록을 안 박는다**고 적혀 있다 -- 목록은 늘 모자라고, 모자란 목록은 그 밖을 "
   "영영 못 거른다")

print("\n── 씨앗 주소 -- 그 집 안쪽으로 판다 ────────────────────")
목록쪽 = ("<html><body>"
        "<a href='/post/1'>합격 수기 1</a><a href='/post/2'>합격 수기 2</a>"
        "<a href='https://남의집.com/x'>남의 집</a>"
        "<a href='/img/a.png'>그림</a></body></html>")
받은주소 = []


def 가짜2(url, 헤더, 틈=20.0):
    받은주소.append(url)
    if any(w in url for w in ("duckduckgo", "bing", "mojeek")):
        return DF.응답(url=url, 코드=403, 왜="HTTP 403 -- 막았다")   # 창구가 다 막힘
    if url.rstrip("/").endswith("목록.com"):
        return DF.응답(url=url, 최종url=url, 코드=200, 몸통=목록쪽, 꼴="text/html")
    if "목록.com/post/" in url:
        n = url.rsplit("/", 1)[-1]
        return DF.응답(url=url, 최종url=url, 코드=200,
                     몸통=f"<html><body><article>{본문} 제{n}편.</article></body></html>",
                     꼴="text/html")
    return DF.응답(url=url, 코드=404, 왜="HTTP 404")


DF.한번 = 가짜2
try:
    with tempfile.TemporaryDirectory() as d:
        곳 = KP.보기DIR / "_검사3"
        잰곳 = MN.잰것DIR / "_검사3"
        try:
            보고 = CR.돌리기(터(d, 곳=str(곳), 잰곳=str(잰곳), 씨앗=[],
                            씨앗주소=["https://목록.com"], 따라=20))
            ok(보고["담음"] >= 2,
               f"**목록 쪽에서 안쪽 글을 파고들어 {보고['담음']}편을 담았다** -- "
               "검색 창구가 전부 403 인데도 돌았다")
            ok(any("/post/1" in u for u in 받은주소), "안쪽 링크를 실제로 받았다")
            ok(not any("남의집.com" in u for u in 받은주소),
               "**남의 집까지 안 판다** -- dig 의 규율 그대로")
            ok(not any(u.endswith(".png") for u in 받은주소), "그림은 안 받는다")
        finally:
            for x2 in (곳, 잰곳):
                if Path(x2).exists():
                    for f in Path(x2).glob("*"):
                        f.unlink()
                    Path(x2).rmdir()
finally:
    DF.한번 = 진짜

print("\n── 검색 결과 쪽을 씨앗주소로 넣지 말라고 적었는가 ───────")
글2 = CR.__doc__ or ""
ok("같은 host 안으로만" in 글2 and "결과로는 영영 못 간다" in 글2,
   "**`dig --따라` 는 같은 host 안으로만 판다**고 적혀 있다 -- 검색 결과 쪽에 걸면 "
   "창구 자기 살림만 돈다")
ok("dig/find.py" in 글2, "검색은 find 로 하라고 적혀 있다")

print("\n── 시간이 되면 멈춘다 ─────────────────────────────────")
DF.한번 = lambda url, 헤더, 틈=20.0: DF.응답(url=url, 왜="프록시가 끊었다")
try:
    with tempfile.TemporaryDirectory() as d:
        보고 = CR.돌리기(터(d, 곳=str(KP.보기DIR / "_검사2"), 분=0))
        ok(보고["담음"] == 0 and 보고["왜"],
           f"**안 멈추는 수집기는 남의 쪽을 두드리는 기계가 된다** ({보고['왜']})")
finally:
    DF.한번 = 진짜
    for x in (KP.보기DIR / "_검사2",):
        if x.exists():
            for f in x.glob("*"):
                f.unlink()
            x.rmdir()


print("\n── 백그라운드 규칙이 파일에 적혀 있는가 ─────────────────")
글 = CR.__doc__ or ""
for 말 in ("setsid", "nohup", "disown", "pgrep -af"):
    ok(말 in 글, f"{말!r} 가 적혀 있다")
ok("ps -p $!" in 글 and "거짓 음성" in 글,
   "**`ps -p $!` 는 거짓 음성을 낸다**고 적혀 있다 (CLAUDE.md 실측)")
ok("pkill -f" in 글 and "자기 셸까지 죽는다" in 글, "`pkill -f` 경고도 있다")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
