"""probes -- 탐침 묶음을 나란히 돌려 표로 돌려주는지 **실제로 돌려** 붙든다.

사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 8개 중 5번. 약한 모델의 천장은 한 호출당
추론 깊이다 -- 깊이는 못 올리지만 폭은 올릴 수 있다. 한 바퀴에 명령 하나씩 돌리던 것이 표 하나가 된다.

붙드는 것 다섯: (1) 나란히 돈다(벽시계로 잰다), (2) 명령마다 끝값·걸린초·꼬리, (3) 빈 줄·중복·상한, (4) 시간
초과는 124 로 잡히고 나머지는 산다, (5) 배선 -- run_probes 도구가 있고 ADMIN_TOOLS 에 들고 조사 프롬프트가 부른다.

실행: python3 tests/test_probes.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import probes as P  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== 나란히 돈다 ==")
시작 = time.monotonic()
r = P.묶음(["sleep 1; echo a", "sleep 1; echo b", "sleep 1; echo c", "sleep 1; echo d"], cwd=뿌리, 초=10, 동시=4)
걸림 = time.monotonic() - 시작
ok(len(r) == 4 and [x["끝값"] for x in r] == [0, 0, 0, 0] and [x["꼬리"] for x in r] == ["a", "b", "c", "d"],
   f"넷 다 돌고 차례가 유지된다 ({[x['꼬리'] for x in r]})")
ok(걸림 < 3.0, f"**넷이 나란히** -- 4초짜리를 {걸림:.1f}초에 (하나씩이면 4초 넘는다)")

print("\n== 명령마다 끝값·걸린초·꼬리 · 빈 줄·중복·상한 ==")
r = P.묶음(["exit 3", "", "echo x", "echo x", "  "], cwd=뿌리, 초=10)
ok([(x["명령"], x["끝값"]) for x in r] == [("exit 3", 3), ("echo x", 0)], f"빈 줄과 중복은 뺀다 ({[(x['명령'], x['끝값']) for x in r]})")
ok(all("걸린초" in x for x in r), "걸린초가 있다")
r = P.묶음([f"echo {i}" for i in range(20)], cwd=뿌리, 초=10)
ok(len(r) == P.최대명령, f"상한 {P.최대명령}개 -- 넘치면 앞 것만")

print("\n== 시간 초과는 124, 나머지는 산다 ==")
r = P.묶음(["sleep 5", "echo 산다"], cwd=뿌리, 초=1)
ok(r[0]["끝값"] == 124 and "안 끝났다" in r[0]["꼬리"] and r[1]["끝값"] == 0, f"({[(x['끝값']) for x in r]})")
본 = P.표(r)
ok(본.startswith("탐침 2개 · 빨강 1개") and 본.index("exit=124") < 본.index("exit=0"), "표는 빨강이 위로")
ok(P.표([]) == "(돌린 명령이 없다)", "빈 표")

print("\n== 배선 ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
_조사 = (뿌리 / "investigate" / "run.py").read_text(encoding="utf-8")
ok("def run_probes(commands: str" in _도구 and "probes.묶음(" in _도구 and "toolgate.검사(c)" in _도구,
   "run_probes 도구가 있고 probes.묶음 을 부르며 명령마다 toolgate 를 지난다")
ok(" run_probes," in _서버 and "ADMIN_TOOLS = [run_shell, run_experiment, run_probes," in _서버, "ADMIN_TOOLS 에 든다")
ok("run_probes 로 한꺼번에" in _조사, "조사 프롬프트가 탐침을 묶으라고 말한다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"probes.py"' in _wf, "배포 경로에 probes.py")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("probes: 나란히 · 표 · 상한 · 시간초과 · 배선 -- 통과")
