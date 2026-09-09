"""**어느 문법이 나은가를 재는 자가 제대로 재는가.**

    python3 tests/test_jaso_bench.py

LLM 은 안 부른다 -- 문법마다 다른 글을 돌려주는 가짜를 넣고, **좋은 글을 내는 문법이
1위로 올라오는지** 본다. 재는 자를 먼저 재는 자리다(`law/mutate.py` 가 관문을 재고,
여기서는 순위 매기는 자를 잰다).

## 제일 중요한 못

**이 파일이 내는 수가 합격률이 아니라고 화면에 적혀 있어야 한다.** 적지 않으면 읽는
사람은 그것을 합격률로 읽고, 그 순간 이 파이프라인이 제일 싫어하는 것 -- 판정 안 받은
답에 판정받은 옷을 입히는 것 -- 이 된다.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import bench as BN                                      # noqa: E402
from jaso import forms as FM                                      # noqa: E402
from jaso import item as IT                                       # noqa: E402
from jaso import ledger as LG                                     # noqa: E402
from jaso import write as WR                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


L = LG.읽기(str(ROOT / "jaso" / "보기.json"))
q = IT.쪼개기("직무에 필요한 역량은 무엇이며 어떤 노력을 했는지 구체적 경험과 "
            "그 결과를 기술하시오 (700자)", "1")

좋음 = ("무봉테크 데이터플랫폼팀 인턴으로 사내 추천 시스템 개편에 참여하며 로그 "
       "파이프라인을 다시 썼습니다. 2주간 A/B 로 24000명씩 재니 클릭률이 2.1%에서 "
       "2.6%로 올랐습니다.\n\n지연은 35분에서 4분으로 줄었습니다. Airflow 로 "
       "스케줄을 걸고 BigQuery 에서 집계했습니다. 같이 일한 4명 중 저는 지표 쪽을 "
       "맡았습니다.")
그저그럼 = ("무봉테크에서 추천 시스템 개편에 참여했습니다. 클릭률이 2.1%에서 2.6%로 "
          "올랐습니다.\n\n또한 저는 열정적으로 임했습니다.")
나쁨 = ("귀사의 인재상에 부합하는 인재입니다. 매출을 30% 향상시켰고 프로젝트를 "
       "주도했습니다.\n\n어릴 적부터 최선을 다해 왔습니다.")


print("── 문법 후보 ──────────────────────────────────────────")
ok(len(FM.문법들) >= 4, f"후보가 {len(FM.문법들)}개")
ok(all(f.어떻게 for f in FM.문법들.values()), "문법마다 시키는 것이 있다")
ok(FM.고르기("없는문법").이름 == "기본",
   "**모르는 이름은 기본이다** -- 예외로 죽으면 런이 통째로 없어진다")
프기본 = WR.프롬프트(q, *WR.고르기(q, L), "누리", "직무", "기본")
프장면 = WR.프롬프트(q, *WR.고르기(q, L), "누리", "직무", "장면")
ok(프기본 != 프장면, "문법이 프롬프트를 실제로 바꾼다")
ok("장면으로 엽니다" in 프장면 and "장면으로 엽니다" not in 프기본, "그 문법의 말이 실린다")
ok("2주간 A/B" in 프장면 and "무봉테크" in 프장면,
   "**문법을 바꿔도 재료는 그대로다** -- 재료가 빠지면 모델이 기억으로 채운다")
금지 = ("J002", "P001", "D001", "관문", "위반", "hard", "soft", "앵커", "합격")
for f in FM.문법들:
    프 = WR.프롬프트(q, *WR.고르기(q, L), "", "", f)
    샌것 = [w for w in 금지 if w in 프]
    ok(not 샌것, f"[{f}] 프롬프트에 관문·합격 이야기가 안 샌다 ({샌것})")


print("\n── 재는 자를 잰다 -- 좋은 글이 1위로 오는가 ─────────────")
글표 = {"기본": 좋음, "두괄": 그저그럼, "장면": 나쁨}


def 가짜(프):
    for 이름, 글 in 글표.items():
        if FM.고르기(이름).어떻게[0][:18] in 프:
            return 글
    return 나쁨


성적들 = BN.재기(q, L, list(글표), 벌=2, 되풀이=1, 묻기=가짜)
ok(len(성적들) == 3, f"문법 {len(성적들)}개를 쟀다")
표 = BN.순위(성적들)
ok(표[0].이름 == "기본",
   f"**좋은 글을 낸 문법이 1위다** (1위: {표[0].이름} · 순위 "
   f"{[s.이름 for s in 표]})")
ok(표[-1].이름 == "장면", f"나쁜 글을 낸 문법이 꼴찌다 ({표[-1].이름})")
ok(표[0].성한비율 == 1.0 and 표[-1].성한비율 == 0.0,
   f"성한비율이 갈린다 ({표[0].성한비율:.0%} vs {표[-1].성한비율:.0%})")
ok(표[0].앵커 > 표[-1].앵커, "앵커도 갈린다")
ok(all(s.벌 == 2 for s in 성적들), "벌 수만큼 돌았다")


print("\n── 대조군 -- 문항만 던진 것 ────────────────────────────")
맨프 = BN.맨프롬프트(q, "누리하나", "데이터 분석")
ok("무봉테크" not in 맨프 and "2.1" not in 맨프,
   "**대조군에는 원장이 안 들어간다** -- 일반 LLM 에 문항만 던진 것과 같아야 한다")
ok(q.원문[:20] in 맨프, "문항은 들어간다")
ok(len(맨프) < len(프기본) / 2, "훨씬 짧다 -- 재료를 안 주니까")
성적2 = BN.재기(q, L, ["기본"], 벌=1, 맨=True, 묻기=lambda p: 나쁨 if "본문만 출력하세요" in p else 좋음)
이름들 = [s.이름 for s in 성적2]
ok("맨(대조군)" in 이름들, f"대조군이 같이 돈다 ({이름들})")
표2 = BN.순위(성적2)
ok(표2[0].이름 == "기본",
   "**대조군이 없으면 우리 수가 좋은지 알 수 없다** -- `seek/` 의 P3 와 같은 자리")


print("\n── 죽은 벌을 성적으로 안 센다 ──────────────────────────")
def 가끔죽는(_):
    raise RuntimeError("풀이 비었다")


성적3 = BN.재기(q, L, ["기본"], 벌=2, 묻기=가끔죽는)
ok(성적3[0].벌 == 0 and 성적3[0].죽은것 == 2, "죽은 것은 따로 센다")
ok(성적3[0].성한비율 == 0.0 and BN.순위(성적3) == [],
   "**한 벌도 못 받은 문법은 순위에 안 올린다** -- 0벌로 1위가 되면 거짓말이다")


print("\n── **합격률이 아니라고 화면에 적는가** (제일 중요) ───────")
buf, err = io.StringIO(), io.StringIO()
원래 = WR._풀에게
WR._풀에게 = lambda _: 좋음
try:
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = BN.main(["--표", str(ROOT / "jaso" / "보기.json"),
                        "--문항", q.원문, "--문법", "기본", "--문법", "짧게",
                        "--벌", "2"])
finally:
    WR._풀에게 = 원래
out = buf.getvalue()
ok(code == 0, f"돈다 (끝값 {code})")
ok("합격률이 아니다" in out, "**합격률이 아니라고 적는다**")
for 말 in ("선택 편향" in out or "합격자만 올리" in out,
          "학점" in out or "면접" in out):
    ok(말, "왜 못 재는지까지 적는다 (편향 · 교란)")
ok("성한비율" in out, "무엇을 쟀는지 이름이 나온다")
ok("표본이 작다" in out or "같은 점수" in out or "제일 나은 것" in out,
   "**표본이 작으면 그렇다고 적는다** -- 두 벌짜리 순위를 결론처럼 내지 않는다")
ok("합격률" in FM.__doc__ and "선택 편향" in BN.__doc__,
   "파일에도 적혀 있다 -- 화면만 보고 지나칠 수 있다")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
