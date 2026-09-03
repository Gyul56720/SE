"""XOR 회로 심판의 회귀 검사 -- **막는다고 적어둔 것을 실제로 막는가.**

막는다고 문서에 적는 것과 실제로 막는 것은 다르다. 직선거리에서 심판과 그 심판의 테스트가
같은 맹점을 공유해 초록불이 떴던 것이 그 증거다. 그래서 부정행위를 하나씩 심어서 잡히는지
본다. LLM·네트워크 없이 돈다.

실행: python3 tests/test_slp_verifier.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "orchestrator" / "problems" / "slp_xor"))

import verify  # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


# y0 = x0^x1, y1 = x1^x2, y2 = x0^x1^x2   (n=3)
M = [[1, 1, 0],
     [0, 1, 1],
     [1, 1, 1]]
# 배선 0,1,2 = x0,x1,x2 / 3 = x0^x1 / 4 = x1^x2 / 5 = (x0^x1)^x2
GOOD = {"ops": [[0, 1], [1, 2], [3, 2]], "outputs": [3, 4, 5]}

print("[기본] 맞는 회로는 통과하고 게이트를 센다")
res = verify.score(GOOD, M)
ok(res["ok"], "맞는 회로가 통과한다")
ok(res["gates"] == 3, f"게이트 수를 3으로 센다 (얻은 값 {res['gates']})")

print("[오답] 배선 하나를 바꾸면 반드시 걸린다")
broken = {"ops": [[0, 1], [1, 2], [3, 2]], "outputs": [3, 4, 4]}
bad_ok, why = verify.check_circuit(broken, M)
ok(not bad_ok, "틀린 출력이 기각된다")
ok("1/3" in why or "행" in why, f"어느 행이 틀렸는지 말해준다: {why[:50]}")

print("[부분 일치] 일부만 맞는 것은 통과가 아니다")
partial = {"ops": [[0, 1]], "outputs": [3, 3, 3]}
ok(not verify.check_circuit(partial, M)[0], "3행 중 1행만 맞아도 기각된다")

print("[거짓 보고] 후보가 보고한 게이트 수는 읽지 않는다")
liar = dict(GOOD, gates=1, cost=1, reported_gates=1)
ok(verify.gate_count(liar) == 3, "보고된 1 을 무시하고 ops 를 직접 세어 3")

print("[실격] 아직 없는 배선을 참조하는 회로")
future = {"ops": [[0, 9]], "outputs": [3, 3, 3]}
f_ok, f_why = verify.check_circuit(future, M)
ok(not f_ok and "실격" in f_why, f"앞선 배선만 참조 규칙을 강제한다: {f_why[:60]}")

print("[실격] 자기 자신을 참조하는 회로 (t3 = t3 ^ t0)")
selfref = {"ops": [[3, 0]], "outputs": [3, 3, 3]}
ok(not verify.check_circuit(selfref, M)[0], "자기 참조가 막힌다")

print("[실격] outputs 개수가 행 수와 다르다")
short = {"ops": [[0, 1]], "outputs": [3]}
s_ok, s_why = verify.check_circuit(short, M)
ok(not s_ok and "실격" in s_why, "출력 개수 불일치가 실격이다")

print("[퇴화] 게이트 0개로 통과하려는 시도")
empty = {"ops": [], "outputs": [0, 1, 2]}
ok(not verify.check_circuit(empty, M)[0], "입력을 그대로 내는 것은 M 을 계산하지 않는다")

print("[정당] 게이트 0개가 정말 맞는 경우는 통과해야 한다 (M = 항등)")
I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
i_ok, _ = verify.check_circuit({"ops": [], "outputs": [0, 1, 2]}, I3)
ok(i_ok, "항등행렬은 게이트 0개로 옳다 -- 심판이 과잉 기각하지 않는다")

print("[규모] 무작위 행렬에서 순진한 구성이 통과한다")
import random
rng = random.Random(7)
n, m = 12, 12
R = [[rng.randint(0, 1) for _ in range(n)] for _ in range(m)]
ops, outs = [], []
for row in R:                       # 각 행을 왼쪽부터 접어서 만든다
    idx = [i for i, v in enumerate(row) if v]
    if not idx:
        continue
    cur = idx[0]
    for i in idx[1:]:
        ops.append([cur, i])
        cur = n + len(ops) - 1
    outs.append(cur)
R = [r for r in R if any(r)]
r_ok, r_why = verify.check_circuit({"ops": ops, "outputs": outs}, R)
ok(r_ok, f"12x12 무작위 행렬에서 통과 ({r_why})")

print()
if fails:
    print(f"XOR 회로 심판: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("XOR 회로 심판: 오답·부분일치·거짓보고·미래배선·자기참조·개수불일치·퇴화를 "
      "전부 잡고, 정당한 0게이트는 통과시킨다 -- 통과")
