"""research(목표 -> 추상 질의 -> 수집 -> 코드화 -> 결론 메모)를 가짜로 **끝까지 돌려** 붙든다.

사용자 규정(실측 2026-09-11): 구체 키워드는 논문이 0건이다 -- 목표를 **일반 방법론 질의
여럿**으로 풀어 넓게 모으고, 막히면 그 막힘을 다시 추상화해 더 넓게 모으기를 되풀이한다
(3~5 바퀴). 모은 것은 코드화로 검증하고, 과정->결과를 압축해 메모로 남긴다. 도메인 무관.

붙드는 것: (1) 분해가 구체 목표를 여러 일반 질의로 푼다(모델 없으면 기계 일반화),
(2) 한 바퀴가 막히면(색인 0) 그 막힘으로 다시 분해해 **다른** 질의로 재시도, 모이면 멈춘다,
(3) 질의가 안 바뀌면 멈춘다(무한 loop 금지), (4) 바퀴 99 줘도 최대 5, (5) 메모에 질의·
바퀴별 수집·코드화·결론(과정->결과)이 압축돼 남는다 + 원장 시작/바퀴/끝, (6) 배선.

LLM·망 없이 돈다(가짜 분해기·종합기·한바퀴·논문코드화 주입). 실행: python3 tests/test_research.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from research import run as Rs  # noqa: E402
from dig import harvest as H    # noqa: E402
from codify import run as C     # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 수확(색인, 막힘=None, 돌았나=True):
    return {"돌았나": 돌았나, "색인": 색인, "저장": 색인, "받음": 색인, "거절": [],
            "막힘": 막힘 or {}, "적은것": [], "걸린초": 0.1}


print("== 분해: 구체 목표를 여러 일반 질의로 (모델 없으면 기계 일반화) ==")
구체 = "naver booking automation playwright headless browser workaround"
질의 = Rs._기계일반화(구체)
ok(len(질의) > 1, f"한 줄이 아니라 여러 질의 ({len(질의)}개)")
ok(any(q != 구체 for q in 질의), "구체 목표 그대로만 쓰지 않는다 -- 더 짧고 일반적인 질의도 낸다")
ok(any("survey" in q or "methodology" in q for q in 질의), "방법론으로 넓히는 질의가 있다")

# 모델이 있으면 그 답을 줄로 쪼갠다(주입)
Rs.분해기 = lambda 목표, 막힌것: "1. reinforcement learning\n2. scheduling optimization\n- queueing theory"
질의2 = Rs.분해("x")
ok(질의2 == ["reinforcement learning", "scheduling optimization", "queueing theory"],
   f"모델 답의 번호·불릿을 떼고 질의로 ({질의2})")
Rs.분해기 = None

임시 = Path(tempfile.mkdtemp(prefix="test-research-"))
try:
    print("\n== 막히면 다시 추상화해 재시도, 모이면 멈춘다 ==")
    바퀴세기 = {"n": 0}

    def 한바퀴_막혔다가(말들, repo=None, 몇=3, 상한=8, 출처=()):   # 1바퀴 막힘, 2바퀴 모임
        바퀴세기["n"] += 1
        return 수확(0, 막힘={"arxiv": "403"}) if 바퀴세기["n"] == 1 else 수확(2)
    H.한바퀴 = 한바퀴_막혔다가
    Rs._이번논문 = lambda repo, 질의들: (["https://arxiv.org/abs/2501.1"] if 바퀴세기["n"] >= 2 else [])
    C.논문코드화 = lambda url, repo=None: {"논문": "2501.1", "제목": "Method P", "스펙수": 2,
                                       "성공": 1, "결과들": [{"파일": "codify/out/p.py", "성공": True}], "못읽음": []}
    Rs.분해기 = lambda 목표, 막힌것: ("broad method X\nbroad method Y" if 막힌것 else "specific topic one\nspecific topic two")
    Rs.종합기 = lambda 목표, 모은요약: "과정: 두 바퀴에 방법 X 모음. 결과: 방법 X 로 푼다."

    r = Rs.연구("auto reserve a salon slot next week", repo=임시, 바퀴=3)
    ok(r["충분"] and r["바퀴수"] == 2, f"**1바퀴 막힘 -> 재분해 -> 2바퀴 모임 -> 멈춤** ({r['바퀴수']}바퀴, 충분 {r['충분']})")
    ok(r["바퀴들"][0]["질의들"] != r["바퀴들"][1]["질의들"], "막힘 뒤 질의가 **바뀐다**(더 넓은 방법론으로)")
    ok(r["바퀴들"][1]["코드성공"] == 1 and r["바퀴들"][1]["파일들"] == ["codify/out/p.py"], "모인 바퀴에서 코드화 검증")
    메모 = (임시 / r["메모"])
    ok(메모.is_file(), f"메모가 쓰인다 ({r['메모']})")
    본 = 메모.read_text(encoding="utf-8")
    ok("## 결론 (과정 -> 결과)" in 본 and "방법 X 로 푼다" in 본, "메모에 과정->결과 결론")
    ok("broad method X" in 본 and "Method P" in 본 and "codify/out/p.py" in 본, "메모에 질의·논문·코드 파일(압축된 과정)")
    원장 = [__import__("json").loads(x) for x in (임시 / Rs.원장상대).read_text(encoding="utf-8").splitlines()]
    꼴들 = [r.get("꼴") for r in 원장]
    ok("연구시작" in 꼴들 and 꼴들.count("연구바퀴") == 2 and "연구끝" in 꼴들, f"원장 시작/바퀴×2/끝 ({꼴들})")

    print("\n== 질의가 안 바뀌면 멈춘다 (무한 loop 금지) ==")
    H.한바퀴 = lambda *a, **k: 수확(0, 막힘={"arxiv": "403"})
    Rs._이번논문 = lambda repo, 질의들: []
    Rs.분해기 = lambda 목표, 막힌것: "same one\nsame two"      # 늘 같은 질의
    r = Rs.연구("goal", repo=임시, 바퀴=5)
    ok(r["바퀴수"] == 1 and "질의가 바뀌지 않아" in r["남은것"], f"**같은 질의면 2바퀴째 멈춘다** ({r['바퀴수']}, {r['남은것'][:30]!r})")

    print("\n== 바퀴 99 줘도 최대 5, 매번 다른 질의 ==")
    세 = {"n": 0}

    def 매번다른(목표, 막힌것):
        세["n"] += 1
        return f"method variant {세['n']}\nmethod other {세['n']}"
    Rs.분해기 = 매번다른
    r = Rs.연구("goal2", repo=임시, 바퀴=99)
    ok(r["바퀴수"] == 5 and not r["충분"], f"**바퀴 99 줘도 최대 5** ({r['바퀴수']})")
    ok("보고" and "5바퀴" in Rs.보고(r), "보고가 바퀴 수를 말한다")
finally:
    Rs.분해기 = Rs.종합기 = None
    H.한바퀴 = None
    import importlib
    importlib.reload(Rs)          # _이번논문 등 원래대로
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import subprocess  # noqa: E402
import dispatch    # noqa: E402
ok("연구" in (dispatch.run("!연구", allow_write=True) or ""), "!연구 도움말")
ok("관리 채널" in (dispatch.run("!연구 어떤 목표", allow_write=False) or ""), "공개 채널 거절")
불림 = []
dispatch.run("!연구 어떤 목표", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0][:3] == ["python3", "research/run.py", "--목표"], f"배경으로 연구 ({불림})")
ok(dispatch.run("!연구기 x") is None, "붙여 쓴 `!연구기` 는 명령이 아니다")
_보 = dispatch.run("!연구 보기", allow_write=True) or ""
ok("메모가 없다" in _보 or _보.startswith("📄"), f"**`!연구 보기` 가 마지막 메모 전문을 준다** ({_보[:40]!r})")
ok(len(_보) <= 2000, "디스코드 한 통에 들어간다(길면 잘리고 전문 경로를 준다)")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def research" in _도구 and _서버.count(" research,") >= 2, "research 도구·ADMIN_TOOLS·임포트")
ok("research 도구" in _서버, "프롬프트가 research 를 이름을 대고 시킨다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"research/**.py"' in _wf, "research 가 배포 경로에")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("research: 분해·재시도·멈춤·바퀴상한·메모·원장·배선 -- 통과")
