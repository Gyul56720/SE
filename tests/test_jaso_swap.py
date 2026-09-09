"""**치환 검사가 눈으로도 납득되는가.**

    python3 tests/test_jaso_swap.py

판정은 `tests/test_jaso_gate.py` 가 본다(P001). 여기서 보는 것은 **사람에게 보여 주는
쪽**이다 -- `갈아끼우기` 는 판정에 안 쓰이지만, 수만 보여 주면 아무도 안 고친다.
"정말 그대로 말이 되네" 를 눈으로 봐야 고친다.

그리고 하나 더 붙든다: **회사·직무 이름은 앵커가 아니다.** 그것이 바로 갈아 끼우는
자리이므로, 앵커로 세면 회사 이름만 넣은 일반론이 통과한다.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                      # noqa: E402
from jaso import swap as SW                                        # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


L = LG.읽기(str(ROOT / "jaso" / "보기.json"))

print("── 갈아 끼운다 ────────────────────────────────────────")
글 = "누리하나의 데이터 분석 직무에 지원합니다. 누리하나에서 성장하고 싶습니다."
새 = SW.갈아끼우기(글, "누리하나", "데이터 분석")
ok("누리하나" not in 새 and "□□기업" in 새, "회사 이름이 갈렸다")
ok("데이터 분석" not in 새, "직무 이름이 갈렸다")
ok(SW.갈아끼우기(글, "", "") == 글, "줄 것이 없으면 그대로 둔다")
ok(SW.갈아끼우기(글, "가", "") == 글, "한 글자 이름은 안 바꾼다 -- 아무 데나 걸린다")

print("\n── 회사 이름은 앵커가 아니다 (핵심) ────────────────────")
회사만 = "누리하나의 인재상에 깊이 공감하여 지원했습니다."
ok(not SW.앵커들(회사만, L),
   "**회사 이름만 든 문단에는 앵커가 0 이다** -- 앵커로 세면 이름만 바꾼 일반론이 "
   "통과한다")
원장것 = "무봉테크에서 클릭률을 2.1%에서 2.6%로 올렸습니다."
ok(SW.앵커들(원장것, L), "(대조군) 원장에서 온 것이 든 문단에는 앵커가 있다")

print("\n── 문단으로 세고 답변으로 판정한다 ─────────────────────")
답변 = 원장것 + "\n\n" + 회사만 + "\n\n그래서 저는 배웠습니다."
잰것 = SW.재기(답변, L)
ok(잰것["문단수"] == 3, f"문단 {잰것['문단수']}개")
ok(잰것["빈문단"] == 2, f"앵커 없는 문단 {잰것['빈문단']}개")
ok(잰것["앵커수"] > 0, "답변 전체로는 앵커가 있다 -- **hard 가 아니다**")
ok(SW.재기(회사만, L)["앵커수"] == 0, "일반론만 있으면 답변 전체 앵커가 0 이다")

print("\n── 원장이 비면 판정이 아니라 못 잰 것이다 ──────────────")
ok(SW.재기(원장것, LG.원장())["앵커수"] == 0,
   "빈 원장에서는 성한 문단도 앵커 0 으로 나온다 -- 그래서 P001 이 원장 없이 "
   "판정하지 않는다(gate 쪽 회귀 못)")

print("\n── CLI ────────────────────────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "글.md"
    p.write_text(회사만, encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = SW.main([str(p), "--표", str(ROOT / "jaso" / "보기.json")])
    out = buf.getvalue()
    ok(code == 1, f"앵커가 하나도 없으면 끝값 1 (받은 것: {code})")
    ok("앵커가 하나도 없다" in out, "왜 걸렸는지 화면에 적는다")

    p.write_text(원장것, encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = SW.main([str(p), "--표", str(ROOT / "jaso" / "보기.json"), "--보기",
                        "--회사", "누리하나"])
    ok(code == 0, "(대조군) 앵커가 있으면 끝값 0")

    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = SW.main([str(p), "--표", "없는파일.json"])
    ok(code == 3 and "판정이 아니라 못 잰 것" in err.getvalue(),
       "**원장이 없으면 3 을 내고 그렇다고 말한다** -- 조용히 '통과' 를 내지 않는다")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
