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

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
