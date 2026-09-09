"""**합격 자소서에서 문법만 캐는가. 본문이 안 남는가.**

    python3 tests/test_jaso_mine.py

망은 안 탄다 -- `dig.fetch.한번` 을 갈아 끼운다.

## 제일 중요한 못 -- M001

**담긴 것에 본문이 없어야 한다.** 이 하나가 무너지면 나머지가 다 무너진다.

  · 남의 글이 저장소에 사본으로 남는다
  · 그 글이 언젠가 생성 재료로 새어 들어가고, 그러면 표절이 된다
  · 표절 검사(한국 채용 실무의 주력)가 바로 잡는다

문법은 **문장이 아니라 구조**다. 문단이 몇 개인가 · 첫 문장이 장면인가 · 100자에 수가
몇 개인가 -- 전부 세면 나오고, 세고 나면 본문이 필요 없다. 그래서 재고 **버린다.**

## 그리고 이 수가 무엇이 아닌지

합격 자소서에서 **관찰된** 형식 분포다. 불합격 쪽 표본이 통째로 없으므로 '합격과
상관있는 형식' 이 아니다. 화면이 늘 그렇게 적는지 검사가 본다.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import fetch as DF                                       # noqa: E402
from jaso import ledger as LG                                     # noqa: E402
from jaso import mine as MN                                       # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


장면글 = """2025년 3월, 로그 파이프라인이 여섯 시간씩 밀리는 화면을 처음 봤습니다.
배치가 끝나야 지표가 갱신되는 구조였고, 그래서 아무도 어제 무슨 일이 있었는지
당일에 알지 못했습니다.

저는 수집 경로를 스트리밍으로 바꾸는 일을 맡았습니다. 반영 지연을 35분에서 4분으로
줄였습니다. 지연이 줄자 추천 결과가 달라 보였는데, 그것이 개선인지 착시인지 알 수
없어 A/B 대시보드를 따로 만들었습니다.

2주간 24000명씩 두고 재니 클릭률이 2.1%에서 2.6%로 올랐습니다. 무엇을 재는지 먼저
정하고 잰 값입니다.

그때부터 저는 지표를 의심하는 쪽으로 일합니다."""

일반론글 = """저는 성실하고 열정적인 사람입니다. 또한 귀사의 인재상에 부합한다고
생각합니다. 이를 통해 성장하고 싶습니다.

또한 저는 협업 능력을 갖추고 있습니다. 또한 원활하게 소통하였습니다. 이를 통해
좋은 결과를 얻을 수 있었습니다. 또한 최선을 다하였습니다."""


print("── 형식을 잰다 -- 본문 없이 ────────────────────────────")
x = MN.재기(장면글, "https://example.com/a")
ok(x.첫문장 == "장면", f"첫 문장을 장면으로 읽는다 ({x.첫문장})")
ok(MN.재기(일반론글, "u").첫문장 == "일반론",
   f"(대조군) '저는 ~입니다' 는 일반론 ({MN.재기(일반론글, 'u').첫문장})")
ok(x.문단수 == 4 and x.문장수 >= 8, f"문단 {x.문단수} · 문장 {x.문장수}")
ok(x.수밀도 > MN.재기(일반론글, "u").수밀도, "수 밀도가 갈린다")
ok(x.결과있나 and not MN.재기(일반론글, "u").결과있나, "결과(수) 유무가 갈린다")
ok(MN.재기(일반론글, "u").이음말밀도 > x.이음말밀도, "이음말 밀도가 갈린다")
ok(MN.재기(일반론글, "u").상투구수 > 0, "상투구를 센다")
ok(x.본문해시 and len(x.본문해시) == 16, "같은 글을 두 번 안 세려고 해시만 든다")


print("\n── **M001 -- 담긴 것에 본문이 없다** (제일 중요) ─────────")
d = asdict(x)
긴칸 = {k: v for k, v in d.items()
       if k != "출처" and isinstance(v, str) and len(v) > 24}
ok(not 긴칸, f"24자 넘는 글 칸이 없다 ({list(긴칸)})")
샌것 = [k for k, v in d.items()
       if k != "출처" and isinstance(v, str) and len(v) >= 12 and v in 장면글]
ok(not 샌것, f"**원문 조각이 든 칸이 없다** ({샌것})")
ok(not LG.hard(MN.검사(x, 장면글)), "성한 것은 검사를 지난다")
샌것2 = MN.잰형식(출처="u", 첫문장=장면글[:60])
ok(any(v.규칙 == "M001" for v in MN.검사(샌것2, 장면글)),
   "**본문이 섞이면 M001 이 잡는다**")
ok(any(v.규칙 == "M002" for v in MN.검사(MN.잰형식(출처=""))), "출처 없으면 M002")
with tempfile.TemporaryDirectory() as t:
    ok(MN.담기([샌것2], t) is None, "**본문이 섞인 것은 안 담긴다**")
    p = MN.담기([x, MN.재기(일반론글, "https://example.com/a")], t)
    ok(p and p.exists(), "성한 것은 담긴다")
    담긴글 = p.read_text(encoding="utf-8")
    ok("로그 파이프라인" not in 담긴글 and "지표를 의심" not in 담긴글,
       "**담긴 파일에 원문이 한 조각도 없다** -- 사본이 아니라 통계다")
    ok(json.loads(담긴글) and all("출처" in r for r in json.loads(담긴글)),
       "출처는 남는다")
    다시 = MN.읽기(t)
    ok(len(다시) == 2, f"되읽으면 {len(다시)}편")
    ok(len(MN.읽기(t + "/없다")) == 0, "없는 데는 빈 것 (안 죽는다)")


print("\n── 같은 글을 두 번 안 센다 ────────────────────────────")
with tempfile.TemporaryDirectory() as t:
    MN.담기([MN.재기(장면글, "https://a.com/1")], t)
    MN.담기([MN.재기(장면글, "https://b.com/2")], t)     # 같은 글, 다른 주소
    ok(len(MN.읽기(t)) == 1,
       f"해시가 같으면 한 편으로 센다 ({len(MN.읽기(t))}편) -- 미러가 표본을 부풀린다")


print("\n── 분포와 문법 후보 ───────────────────────────────────")
것들 = [MN.재기(장면글, f"https://x.com/{i}") for i in range(5)]
for i, 것 in enumerate(것들):
    것.본문해시 = f"h{i}"                       # 서로 다른 글인 척
d = MN.분포(것들)
ok(d["표본"] == 5, "표본을 센다")
ok(d["첫문장"].get("장면") == 5, f"첫 문장 갈래를 센다 ({d['첫문장']})")
ok("중앙" in d["문단수"] and "아래" in d["문단수"],
   "**중앙값과 사분위를 낸다** -- 평균은 한 편이 길면 통째로 끌려간다")
초안 = MN.문법후보(d)
ok("문법(" in 초안 and "캔것" in 초안, "forms.py 에 넣을 꼴로 낸다")
ok("장면으로 엽니다" in 초안, "관찰된 첫 문장 갈래가 초안에 반영된다")
ok("가설" in 초안, "**가설이라고 초안 안에 적혀 있다**")
ok("합격률" not in 초안, "초안이 합격률을 말하지 않는다")
ok(MN.문법후보({}) == "(잰 것이 없다)", "빈 분포에도 안 죽는다")


print("\n── 받기 -- 재고 **버린다** ────────────────────────────")
진짜한번 = DF.한번
쪽 = f"<html><body><article>{장면글}</article></body></html>"
DF.한번 = lambda url, 헤더, 틈=20.0: (
    DF.응답(url=url, 최종url=url, 코드=200, 몸통=쪽, 꼴="text/html")
    if "good" in url else DF.응답(url=url, 코드=404, 왜="HTTP 404"))
try:
    보고 = MN.받기(urls=["https://good.example.com/x",
                       "https://bad.example.com/y"], 몇=2)
    ok(len(보고["잰것"]) == 1, f"받은 쪽만 잰다 ({len(보고['잰것'])}편)")
    ok(보고["잰것"][0].첫문장 == "장면", "쪽에서 뽑은 글도 갈래가 나온다")
    ok("못 받았다" in str(보고["쪽별"]), "못 받은 쪽은 까닭을 남긴다")
    ok(not any("로그 파이프라인" in str(v) for v in 보고.values()),
       "**보고 어디에도 본문이 없다**")
finally:
    DF.한번 = 진짜한번


print("\n── 화면이 무엇이 아닌지 적는가 ─────────────────────────")
with tempfile.TemporaryDirectory() as t:
    MN.담기(것들, t)
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = MN.main(["--분포", "--곳", t])
    out = buf.getvalue()
    ok(code == 0, f"돈다 (끝값 {code})")
    ok("합격률이 높다' 가 아니다" in out or "합격률이 높다" in out,
       "**'이 형식이면 합격률이 높다' 가 아니라고 적는다**")
    ok("합격자만 올린다" in out, "왜인지(선택 편향)까지 적는다")
    ok("본문은 담기지 않았다" in out, "본문이 안 담겼다고 적는다")
    ok("bench.py 가 관문으로 낸다" in out, "순위는 어디서 나는지 적는다")
    ok("표본이 5편뿐이다" in out, "**표본이 작으면 작다고 적는다**")
ok("선택 편향" in MN.__doc__ and "문장이 아니라 구조" in MN.__doc__,
   "파일에도 적혀 있다 -- 화면만 보고 지나칠 수 있다")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
