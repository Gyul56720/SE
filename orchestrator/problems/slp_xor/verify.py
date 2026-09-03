"""XOR 회로의 외부 심판. 후보 코드를 임포트하지 않고, 보고된 숫자를 믿지 않는다.

원리. SLP 는 배선 목록이다. 입력 x_0..x_{n-1} 을 단위벡터로 두고 XOR 을 그대로 굴리면
각 배선이 계산하는 선형형식이 F_2^n 의 벡터로 나온다. 그것을 목표 행렬의 행과 대조한다.
O(게이트 수) 이고 허용오차가 없다 -- 맞거나 틀리거나다.

**게이트 수는 심판이 직접 센다.** 후보가 보고한 수는 읽지 않는다. mathgen 심판이 답을
미분해 독립 재검증하는 것과 같은 수다.
"""
from __future__ import annotations


class MalformedProgram(ValueError):
    """회로가 계약을 어겼다. 틀린 답과 구분한다 -- 이쪽은 실격이지 오답이 아니다."""


def rows_to_masks(matrix) -> list:
    """행렬의 각 행을 입력에 대한 비트마스크로. matrix[j][i] 가 x_i 의 계수."""
    masks = []
    for j, row in enumerate(matrix):
        m = 0
        for i, v in enumerate(row):
            if v not in (0, 1):
                raise MalformedProgram(f"행렬 원소가 F_2 가 아니다: [{j}][{i}]={v}")
            if v:
                m |= 1 << i
        masks.append(m)
    return masks


def evaluate(program, n: int) -> list:
    """배선마다 그것이 계산하는 선형형식을 비트마스크로 돌려준다.

    형식 검사도 여기서 한다. 앞선 배선만 참조해야 한다 -- 그러지 않으면 회로가 아니라
    방정식계이고, '한 번의 XOR' 이라는 비용 모형이 무너진다."""
    wires = [1 << i for i in range(n)]
    ops = program.get("ops", [])
    if not isinstance(ops, (list, tuple)):
        raise MalformedProgram("ops 가 목록이 아니다")
    for k, op in enumerate(ops):
        if len(op) != 2:
            raise MalformedProgram(f"ops[{k}] 가 (a,b) 쌍이 아니다: {op!r}")
        a, b = op
        limit = len(wires)
        if not (isinstance(a, int) and isinstance(b, int)):
            raise MalformedProgram(f"ops[{k}] 의 배선 번호가 정수가 아니다: {op!r}")
        if not (0 <= a < limit and 0 <= b < limit):
            raise MalformedProgram(
                f"ops[{k}]={op} 가 아직 없는 배선을 참조한다 (현재 배선 {limit}개)")
        wires.append(wires[a] ^ wires[b])
    return wires


def gate_count(program) -> int:
    """**심판이 직접 센다.** 후보가 보고한 값은 쓰지 않는다."""
    return len(program.get("ops", []))


def check_circuit(program, matrix) -> tuple:
    """(통과 여부, 사유). 사유는 실패 지점을 짚어준다 -- 수리 루프가 읽을 신호다."""
    if not matrix or not matrix[0]:
        return False, "빈 행렬"
    n = len(matrix[0])
    if any(len(r) != n for r in matrix):
        return False, "행 길이가 들쭉날쭉하다"

    try:
        targets = rows_to_masks(matrix)
        wires = evaluate(program, n)
    except MalformedProgram as e:
        return False, f"실격: {e}"

    outs = program.get("outputs")
    if not isinstance(outs, (list, tuple)) or len(outs) != len(matrix):
        return False, (f"실격: outputs 가 행 수와 다르다 "
                       f"({len(outs) if isinstance(outs, (list, tuple)) else outs!r} "
                       f"vs {len(matrix)})")

    bad = []
    for j, w in enumerate(outs):
        if not isinstance(w, int) or not (0 <= w < len(wires)):
            return False, f"실격: outputs[{j}]={w!r} 가 배선 범위 밖이다"
        if wires[w] != targets[j]:
            bad.append(j)
    if bad:
        return False, (f"{len(bad)}/{len(matrix)} 행이 틀렸다 (예: 행 {bad[:5]}). "
                       f"부분 일치는 통과가 아니다")
    return True, f"모든 행이 일치 · 게이트 {gate_count(program)}개"


def score(program, matrix) -> dict:
    ok, why = check_circuit(program, matrix)
    return {"ok": ok, "reason": why, "gates": gate_count(program) if ok else None}
