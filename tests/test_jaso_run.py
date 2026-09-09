"""**배관이 한 명령으로 돌고, 사람 차례에서 멈추는가.**

    python3 tests/test_jaso_run.py

## 이 검사가 붙드는 제일 중요한 못

**`run.py` 는 경험 항목을 만들지 않는다.** 항목이 원장에 들어가는 길은 `intake` 가
사람의 답에서 넣는 것 하나뿐이다.

실측으로 한 번 그럴 뻔했다 -- "`내원장.json` 이 없으면 방금 수집한 정보를 토대로
구조를 잡고 진행하겠습니다." 수집한 것은 **남의 공고문**이다. 그것으로 원장을 만들면
그 사람의 이력을 지어내는 것이고, J001~J004 와 P001 이 전부 미검증이 되며, 나오는
글은 정확히 이 파이프라인이 막으려던 그 글이다 -- 관문이 있다는 착각만 얹은 채로.

## 끝값이 다음에 무엇을 할지다

    0  자소서까지 냈다     2  **사람 차례**     1  hard 남음     3  못 갔다
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                     # noqa: E402
from jaso import run as RN                                        # noqa: E402
from jaso import write as WR                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


역량 = ("직무에 필요한 역량은 무엇이며 이를 갖추기 위해 어떤 노력을 했는지 "
       "구체적 경험과 그 결과를 기술하시오 (700자)")


def 돌리기(터, *argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = RN.main(["--터", str(터), "--회사", "누리하나",
                        "--직무", "데이터 분석", *argv])
    return code, buf.getvalue() + err.getvalue()


진짜풀 = WR._풀에게
성한벌 = ("무봉테크 데이터플랫폼팀 인턴으로 사내 추천 시스템 개편에 참여하며 로그 "
        "파이프라인을 다시 썼습니다. 2주간 A/B 로 24000명씩 재니 클릭률이 2.1%에서 "
        "2.6%로 올랐습니다.\n\n같이 일한 사람들 중 저는 지표 쪽을 맡았습니다.")

with tempfile.TemporaryDirectory() as d:
    터 = Path(d) / "일"

    print("── 1바퀴 -- 물음이 나가고 **멈춘다** ────────────────────")
    code, out = 돌리기(터, "--문항", 역량)
    ok(code == RN.사람차례, f"끝값 {code} == 2 (사람 차례)")
    ok("사람 차례입니다" in out, "무엇을 해야 하는지 화면에 적는다")
    ok((터 / "답.txt").is_file(), "답을 적을 칸을 만들어 둔다")
    ok((터 / "물음.json").is_file() and (터 / "문항.json").is_file(),
       "물음과 문항이 폴더에 남는다 -- 다음 바퀴가 이어받는다")
    ok(f"--터 {터}" in out,
       "**다시 부르는 법을 그대로 찍는다** -- `--이름` 을 찍으면 다른 폴더가 새로 "
       "파이고 답을 적어 둔 데를 잃는다 (회귀 못)")

    print("\n── **원장을 지어내지 않는다** (제일 중요한 못) ──────────")
    ok(not (터 / "원장.json").is_file() or not LG.읽기(str(터 / "원장.json")).항목들,
       "물음만 냈을 때 원장에 항목이 하나도 없다 -- 공고문으로 이력을 만들지 않는다")
    code2, _ = 돌리기(터, "--문항", 역량)
    ok(code2 == RN.사람차례 and not LG.읽기(str(터 / "원장.json")).항목들
       if (터 / "원장.json").is_file() else code2 == RN.사람차례,
       "**몇 번을 다시 불러도 항목이 안 생긴다** -- 사람이 답해야 생긴다")

    print("\n── 2바퀴 -- 답을 넣으면 그 물음이 사라진다 ──────────────")
    물음 = json.loads((터 / "물음.json").read_text(encoding="utf-8"))["물음"]
    답표 = {"새항목": "사내 추천 시스템 개편, 무봉테크 데이터플랫폼팀 인턴, "
                   "2025-03 ~ 2025-08, 참여",
          "생각": "지표를 의심하는 습관입니다",
          "잰것": "클릭률 2.1% -> 2.6% (2주 A/B, 대조군 24,000 실험군 24,000명)",
          "쓴것": "Python, BigQuery", "증빙": "커밋 로그", "역할": "참여",
          "언제": "2025-03 ~ 2025-08", "어떻게": "2주 A/B, 24,000명"}
    바퀴 = 0
    while 바퀴 < 6:
        물음 = json.loads((터 / "물음.json").read_text(encoding="utf-8"))["물음"]
        if not 물음:
            break
        바퀴 += 1
        글 = "\n".join(f"{i}) {답표[q['칸'].split(':')[0]]}"
                     for i, q in enumerate(물음, 1))
        code, out = 돌리기(터, "--답글", 글)
        ok("답을 넣었다" in out, f"{바퀴}바퀴: 답이 들어갔다")
        ok(list(터.glob(f"답_{바퀴:02d}.txt")),
           f"{바퀴}바퀴: 답 원문을 남긴다 -- 작성 근거 기록의 재료다")
    ok(바퀴 <= 4, f"**{바퀴}바퀴 만에 물을 것이 없어졌다** -- 고리가 닫힌다")
    L = LG.읽기(str(터 / "원장.json"))
    ok(L.항목들 and not LG.hard(LG.검사(L)), "원장이 차고 hard 가 없다")

    print("\n── 껍데기 답은 항목을 안 만든다 (회귀 못) ──────────────")
    with tempfile.TemporaryDirectory() as d2:
        터2 = Path(d2) / "일"
        돌리기(터2, "--문항", 역량)
        _, out = 돌리기(터2, "--답글", "1) Python, BigQuery, Airflow")
        ok("기간도 역할도 못 읽었다" in out,
           "**'Python, BigQuery' 로 항목을 안 만든다** -- 실측: 번호가 밀린 답이 "
           "들어와 이름이 `Python` 인 껍데기가 생겼고, 그 뒤로 매 바퀴 네 개씩 "
           "물었다. 사람은 있지도 않은 경험을 설명하게 된다")
        ok(not LG.읽기(str(터2 / "원장.json")).항목들
           if (터2 / "원장.json").is_file() else True, "원장이 안 더럽혀졌다")
        ok(list(터2.glob("답_*.txt")), "**답은 그대로 남는다** -- 버리지 않는다")

    print("\n── 3바퀴 -- 재료가 차면 끝까지 자동이다 ─────────────────")
    WR._풀에게 = lambda _: 성한벌
    try:
        code, out = 돌리기(터)
    finally:
        WR._풀에게 = 진짜풀
    ok(code in (0, 1), f"끝값 {code} (0 냈다 · 1 hard 남음)")
    ok((터 / "자소서.md").is_file(), "자소서를 냈다")
    ok((터 / "근거.md").is_file(), "**작성 근거 기록도 같이 낸다**")
    ok("관문:" in out, "관문 결과를 같이 적는다")
    근거 = (터 / "근거.md").read_text(encoding="utf-8")
    ok("인터뷰 원문" in 근거, "답한 원문이 근거에 남는다")
    ok("2주간 A/B" in 근거 or "2주 A/B" in 근거, "재는 법이 근거에 남는다")
    ok("기록.md" in [p.name for p in 터.iterdir()], "무슨 일이 있었는지 기록이 남는다")

    print("\n── **빈 자소서는 안 쓴다** (회귀 못) ────────────────────")
    (터 / "자소서.md").unlink()

    def 죽는다(_):
        raise RuntimeError("LLM 후보 풀이 비었다")

    WR._풀에게 = 죽는다
    try:
        code, out = 돌리기(터)
    finally:
        WR._풀에게 = 진짜풀
    ok(code == 3, f"끝값 {code} == 3 (못 갔다)")
    ok(not (터 / "자소서.md").is_file(),
       "**0자짜리 파일을 안 만든다** -- 실측: 키가 없는 데서 모든 벌이 죽었는데 "
       "`min` 이 빈 글을 골라 `[씀] 자소서.md` 가 찍혔다. 사람은 파일이 생긴 것을 "
       "먼저 보고, 빨간불은 글이 나쁜 탓이라고 읽는다")
    ok("한 벌도 글을 못 받았다" in out and "GEMINI_API_KEY" in out,
       "왜 못 갔는지 갈래로 말한다")

print("\n── 아무 글에서 문항을 캔다 (갈래를 안 가린다) ──────────")
요강 = """2027학년도 편입학 모집요강

가. 모집단위 및 인원
나. 전형요소별 배점
다. 제출서류: 학업계획서 1부

[학업계획서 문항]
1. 본교 해당 학과에 지원하게 된 동기와 학업 계획을 기술하시오. (1,000자 이내)
2. 편입 후 학업을 수행하기 위해 준비한 것과 그 과정에서 배운 점을 서술하시오. (800자)

문의: 입학처"""
with tempfile.TemporaryDirectory() as d3:
    터3 = Path(d3) / "편입"
    code, out = 돌리기(터3, "--글", 요강)
    ok(code == RN.사람차례, f"요강을 그대로 줘도 돈다 (끝값 {code})")
    ok("문항 2개" in out,
       "**요강에서 문항 둘만 캤다** -- 모집단위·전형요소·제출서류·문의는 안 담긴다. "
       "글의 갈래를 목록으로 두면 목록에 없는 서식이 오는 날 통째로 못 읽는다")
    qs = RN.문항읽기(터3)
    ok(qs and qs[0].상한 == 1000 and qs[1].상한 == 800,
       f"글자 수까지 딸려 온다 ({[q.상한 for q in qs]})")
    ok(any("학업 계획" in q.원문 for q in qs), "문항 원문이 그대로 남는다")

print("\n── 준 것의 **꼴을 보고** 어디로 보낼지 정한다 ─────────")
ok(RN.받은것꼴("") == {}, "빈 것은 아무 데도 안 보낸다")
ok(RN.받은것꼴("한양대 편입") == {"질의": "한양대 편입"},
   "짧은 이름 한 줄은 **찾을 말**이다")
ok(RN.받은것꼴("여기요 https://a.kr/x 랑 https://b.kr/y 요")
   == {"urls": ["https://a.kr/x", "https://b.kr/y"]},
   "주소가 섞여 있으면 **주소**다 (여럿이면 여럿 다)")
ok("글" in RN.받은것꼴("1. 지원 동기\n2. 성장 과정"), "줄이 여럿이면 **붙여넣은 글**이다")
ok("글" in RN.받은것꼴("가" * 130), "길면 붙여넣은 글이다")
ok("갈래를 물어보지 않는다" in " ".join((RN.받은것꼴.__doc__ or "").split()),
   "**갈래를 되묻지 않는 까닭이 적혀 있다** -- 되물으면 한 왕복이 늘고 거기서 사람이 떠난다")

print("\n── 문항이 없는 것은 **끝값 3 이 아니라 사람 차례다** (회귀 못) ──")
with tempfile.TemporaryDirectory() as d4:
    터4 = Path(d4) / "빈손"
    code, out = 돌리기(터4)
    ok(code == RN.사람차례,
       f"끝값 {code} == 2 -- **3 이면 부르는 쪽이 '이 건은 끝났다' 로 읽고 대화를 "
       "닫는다.** 재료가 모자란 것은 실패가 아니라 사람에게 물을 것이 남은 것이다")
    ok("어디에 내는 것입니까" in out, "**사람의 말로 되묻는다**")
    ok("--문항" not in out and "--질의" not in out,
       "**옵션 이름을 모르는 사람에게 옵션 이름으로 답하지 않는다** -- 실측: 여기서 "
       "`문항을 못 구했다 -- `--문항 \"<원문>\"` 을 직접 주거나…` 가 공개 채널에 "
       "그대로 나갔다. 배포판에서 열에 아홉이 지나는 자리다")
    ok((터4 / "답.txt").is_file(), "적을 칸을 만들어 둔다 -- 이것도 사람 차례다")

    print("\n   ...그리고 **같은 물음을 두 번 하지 않는다**")
    import jaso.fetch as JF
    진짜받기 = JF.받기
    JF.받기 = lambda 질의, urls, 회사, 몇: {"창구별": {}, "쪽별": {}, "문항": []}
    try:
        code2, out2 = 돌리기(터4, "--답글", "한양대 편입")
    finally:
        JF.받기 = 진짜받기
    ok(code2 == RN.사람차례, f"끝값 {code2} == 2")
    ok("찾아봤지만" in out2 and "질의" in out2,
       "**짚어 본 것을 말한다** -- 찾아본 티를 안 내면 사람은 자기 말이 씹혔다고 읽는다")
    ok("어디에 내는 것입니까" not in out2,
       "**첫 물음을 되풀이하지 않는다** -- 같은 물음이 두 번 오면 '이 봇은 내 말을 "
       "안 듣는다' 가 되고, 두 번째 왕복에서 사람이 떠난다")
    ok("그대로 붙여넣어" in out2,
       "**되는 길 하나만 짚는다** -- 두 번째에는 셋을 늘어놓지 않는다")
    ok("붙여넣어" in (터4 / "답.txt").read_text(encoding="utf-8"),
       "적을 칸의 머리말도 같이 바뀐다")

print("\n── 준 것이 **주소면 주소로** 간다 ──────────────────────")
with tempfile.TemporaryDirectory() as d5:
    터5 = Path(d5) / "주소"
    받은것 = {}
    import jaso.fetch as JF
    진짜받기 = JF.받기

    def 잡기(질의, urls, 회사, 몇):
        받은것["질의"], 받은것["urls"] = 질의, list(urls)
        return {"창구별": {}, "쪽별": {}, "문항": []}

    JF.받기 = 잡기
    try:
        code, out = 돌리기(터5, "--답글", "https://admission.example.ac.kr/transfer")
    finally:
        JF.받기 = 진짜받기
    ok(받은것.get("urls") == ["https://admission.example.ac.kr/transfer"],
       f"주소가 `--url` 자리로 갔다 ({받은것.get('urls')})")
    ok(not 받은것.get("질의"), "찾을 말로 안 보냈다 -- 주소는 바로 열면 된다")
    ok("주소 1개" in out, "짚어 본 것에 주소가 적힌다")

print("\n── 준 것이 **요강이면 문항까지 간다** (배포판 한 왕복) ──")
with tempfile.TemporaryDirectory() as d6:
    터6 = Path(d6) / "한왕복"
    code, out = 돌리기(터6)                       # "자소서 써 줘" 만 한 것
    ok(code == RN.사람차례 and "어디에 내는 것입니까" in out, "① 되묻는다")
    code, out = 돌리기(터6, "--답글", 요강)        # 요강을 붙여 넣은 것
    ok(code == RN.사람차례 and "문항 2개" in out,
       f"② **되물은 답에서 문항을 캔다** (끝값 {code})")
    ok("사람 차례입니다" in out and "[Q1]" in out,
       "③ 곧바로 인터뷰 물음이 나간다 -- 왕복 한 번에 여기까지다")
    ok(RN.문항읽기(터6), "문항이 폴더에 남는다")

print("\n── 문항이 이미 있으면 답글은 **답이다** (회귀 못) ────────")
with tempfile.TemporaryDirectory() as d7:
    터7 = Path(d7) / "답"
    돌리기(터7, "--문항", 역량)
    _, out = 돌리기(터7, "--답글",
                  "1) 사내 추천 시스템 개편, 무봉테크 인턴, 2025-03 ~ 2025-08, 참여")
    ok("답을 넣었다" in out,
       "**문항이 있는 판에서 온 답글은 찾을 말이 아니다** -- 여기서 꼴을 보고 "
       "`--질의` 로 보내면 사람이 적은 경험이 검색어가 되어 통째로 사라진다")

print("\n── 공개 채널 -- 사람마다 원장을 가른다 ──────────────────")
가 = RN._사람터("사람가", "일")
나 = RN._사람터("사람나", "일")
ok(가 != 나, "**호출자가 다르면 폴더가 다르다** -- 안 가르면 남의 이력을 보게 된다")
ok(RN._사람터("사람가", "일") == 가, "같은 사람은 같은 폴더 (이어서 갈 수 있다)")
ok("사람가" not in str(가),
   "**id 가 폴더 이름에 안 드러난다** -- 드러나면 누가 이 봇을 썼는지가 목록으로 남는다")
buf2, err2 = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(buf2), contextlib.redirect_stderr(err2):
    code = RN.main(["--터", str(ROOT / "Public_agent" / "x"), "--문항", 역량])
ok(code == 3 and "커밋되는 곳" in err2.getvalue(),
   "**`Public_agent/` 안에는 못 쓴다** -- 거기는 커밋되는 곳이고, 경험 원장과 "
   "인터뷰 답이 담기면 그 사람의 이력이 저장소에 영영 남는다")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
