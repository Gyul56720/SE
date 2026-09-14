"""G020(판정 원장·게이트 삭제 금지)를 임시 저장소에서 **실제로 돌려** 붙든다.

self_challenge 가 승격할 때 RED/GREEN 을 한 번 증명했지만, 그 증명은 그 자리의
한 번이다 -- 이 검사가 그 성질을 계속 붙든다(tests/test_pr_merged.py 가 pr_merged.sh
를 붙드는 것과 같은 자리: 잘못 답하는 장치는 없느니만 못하다).

붙드는 것: (1) 판정 원장의 줄 삭제를 잡는다, (2) 게이트 파일 통삭제를 잡는다,
(3) 줄을 더하는 것은 안 잡는다(원장의 일이다), (4) 파생 색인(graph/ledger.jsonl)의
재구축은 안 잡는다, (5) 게이트 파일의 수정(삭제 아님)은 안 잡는다.

실행: python3 tests/test_gate_g020.py
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import gatekeeper  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


게이트파일 = sorted((뿌리 / "gates").glob("G020_*.py"))
ok(len(게이트파일) == 1, f"G020 이 gates/ 에 승격돼 있다 ({[p.name for p in 게이트파일]})")
spec = importlib.util.spec_from_file_location("_g020", 게이트파일[0])
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def 저장소() -> Path:
    d = Path(tempfile.mkdtemp(prefix="test-g020-")) / "repo"
    (d / "eval").mkdir(parents=True)
    (d / "graph").mkdir()
    (d / "gates").mkdir()
    subprocess.run(["git", "-C", str(d), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    (d / "eval" / "ledger.jsonl").write_text('{"판정":"초록"}\n{"판정":"빨강"}\n', encoding="utf-8")
    (d / "graph" / "ledger.jsonl").write_text('{"색인":1}\n{"색인":2}\n', encoding="utf-8")
    (d / "gates" / "G998_더미.py").write_text("RULE_ID='G998'\n", encoding="utf-8")
    # 목록에 이름이 **없는** 새 계보. `--묶음 vne` 가 만드는 꼴이다.
    (d / "falsegreen").mkdir()
    (d / "falsegreen" / "요약-cut+vne.jsonl").write_text(
        '{"잰변형":10}\n{"잰변형":20}\n', encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "기준"], check=True)
    return d


repo = 저장소()
try:
    print("== 성한 트리는 통과 ==")
    ok(not G.check(gatekeeper.GateContext(repo)), "변경 없음 -> 위반 없음")

    print("\n== 판정 원장의 줄 삭제를 잡는다 ==")
    (repo / "eval" / "ledger.jsonl").write_text('{"판정":"초록"}\n', encoding="utf-8")
    v = G.check(gatekeeper.GateContext(repo))
    ok(len(v) == 1 and "append-only" in v[0], f"**빨강 줄을 지우면 걸린다** ({v})")

    print("\n== 이름이 목록에 없는 새 계보도 자리로 지킨다 ==")
    (repo / "eval" / "ledger.jsonl").write_text(
        '{"판정":"초록"}\n{"판정":"빨강"}\n', encoding="utf-8")          # 앞 위반을 되돌린다
    ok(not G.check(gatekeeper.GateContext(repo)), "되돌리면 성한 트리다")
    ok("falsegreen/요약-cut+vne.jsonl" not in G.보호원장,
       "이 이름은 목록에 **없다** -- 자리로만 걸려야 뜻이 있다")
    (repo / "falsegreen" / "요약-cut+vne.jsonl").write_text('{"잰변형":10}\n', encoding="utf-8")
    v = G.check(gatekeeper.GateContext(repo))
    ok(len(v) == 1 and "append-only" in v[0],
       f"**falsegreen/ 아래 새 계보의 줄을 지워도 걸린다** ({v})")
    (repo / "falsegreen" / "요약-cut+vne.jsonl").unlink()
    v = G.check(gatekeeper.GateContext(repo))
    ok(any("사라졌다" in x for x in v), f"파일째 지워도 걸린다 ({v})")
    (repo / "falsegreen" / "요약-cut+vne.jsonl").write_text(
        '{"잰변형":10}\n{"잰변형":20}\n', encoding="utf-8")
    ok(not G.check(gatekeeper.GateContext(repo)), "되돌리면 다시 성하다")

    print("\n== 줄을 더하는 것은 안 잡는다 ==")
    (repo / "eval" / "ledger.jsonl").write_text(
        '{"판정":"초록"}\n{"판정":"빨강"}\n{"판정":"초록"}\n', encoding="utf-8")
    ok(not G.check(gatekeeper.GateContext(repo)), "덧쓰기는 원장의 일이다 -- 안 걸린다")

    print("\n== 파생 색인의 재구축은 안 잡는다 ==")
    (repo / "graph" / "ledger.jsonl").write_text('{"색인":"다시"}\n', encoding="utf-8")
    ok(not G.check(gatekeeper.GateContext(repo)),
       "graph/ledger.jsonl 은 파생이라 다시 지어도 된다")

    print("\n== 게이트 통삭제는 잡고, 수정은 안 잡는다 ==")
    (repo / "gates" / "G998_더미.py").write_text("RULE_ID='G998'\nTITLE='고침'\n", encoding="utf-8")
    ok(not G.check(gatekeeper.GateContext(repo)), "게이트 수정(사람 리뷰 영역)은 안 걸린다")
    (repo / "gates" / "G998_더미.py").unlink()
    v = G.check(gatekeeper.GateContext(repo))
    ok(any("우회" in x for x in v), f"**게이트를 지우면 걸린다** ({v})")

    print("\n== 원장 파일째 삭제도 잡는다 ==")
    (repo / "eval" / "ledger.jsonl").unlink()
    v = G.check(gatekeeper.GateContext(repo))
    ok(any("사라졌다" in x for x in v), f"파일째 지워도 걸린다 ({v})")
finally:
    shutil.rmtree(repo.parent, ignore_errors=True)

print("\n== 보호 목록이 **도구를 따라가는가** (표류 방지) ==")
# **실측 2026-09-13.** 보호원장에 2026-09-11 의 채점표 넷만 있고, 그 뒤에 생긴 오늘의
# 채점표(falsegreen/*.jsonl)는 없었다. 그래서 "채점표를 고쳐 실패를 없애는 길" 이 오늘의
# 채점표에 대해서는 열려 있었다. 목록이 도구를 안 따라가는 것이 표류의 꼴이므로, 여기서
# 도구의 경로 상수와 목록을 맞춰 붙든다 -- 새 원장을 만들고 여기 안 넣으면 이 검사가 빨갛다.
import importlib  # noqa: E402
for 모듈, 상수 in (("mutate", "요약경로"), ("perf", "성능경로"),
                ("policy", "정책경로"), ("farcheck", "기록경로"),
                ("vne.measure", "원장경로")):
    경로 = getattr(importlib.import_module(모듈), 상수)
    ok(경로 in G.보호원장,
       f"**{모듈}.{상수} ({경로}) 를 G020 이 지킨다** -- 판정의 역사가 지워지면 그 위의 모든 "
       f"판정이 뜻을 잃는다")
ok(len(set(G.보호원장)) == len(G.보호원장), f"보호 목록에 중복이 없다 ({len(G.보호원장)}개)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("G020: 원장 삭제 잡음 · 덧쓰기 허용 · 파생 재구축 허용 · 게이트 삭제 잡음 · 보호 목록이 도구를 따라감 -- 통과")
