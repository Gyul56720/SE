"""**발산** -- 공간을 최대한 많이 낳는다. 이 단계에서 죽이는 것은 없다.

    python3 mathdrift/spread.py --check              # 지금 무엇을 쓸 수 있나 (호출 0회)
    python3 mathdrift/spread.py --n 300              # 300개
    python3 mathdrift/spread.py --n 5 --dry          # 호출 없이 프롬프트만 본다
    python3 mathdrift/spread.py --show               # 원장을 본다
    python3 mathdrift/spread.py --lineage S17        # 씨앗까지의 사슬

## 왜 안 죽이나

공간은 틀릴 수 없다 -- 쓸모없을 뿐이다. 틀린 정리는 원장을 오염시키지만 빈 공간은
탐색해봐야 아무것도 안 나올 뿐이다. 그래서 발산에는 게이트를 안 건다. 4축 심판은
**다음 커밋의 별도 배치**이고, 여기서 흉내내면 발산이 죽는다.

## 대신 스키마는 강제한다

만 개를 자유 산문으로 뽑아 두면 검증할 때 만 번을 다시 파싱해야 한다 -- 생성 비용만큼이
다시 든다. `novel/flow.py` 와 같은 배치다: **모델은 자유롭게 쓰고, 받는 것은 칸이다.**

## 쿼터 -- 묶어서 부른다

무료 티어에서 병목은 일일 한도가 아니라 **분당 한도(RPM)** 다. 구글 문서 기준으로 한도는
**프로젝트** 단위이고 RPM 은 모델별로 따로 걸린다(flash 10/분 남짓). 공간 하나에 호출
하나면 300개에 30분 이상이고, 그 시간의 대부분은 쿨다운을 기다리는 것이다.

그래서 **한 번에 여러 개를 받는다.** 부모 하나를 보여 주고 연산자 K 개를 함께 걸어
K 개를 받는다. 호출이 1/K 로 준다. 공짜로 얻는 것이 하나 더 있다 -- 모델이 K 개를 **한
자리에서 보므로** 서로 다르게 쓴다. 따로 부르면 비슷한 것이 K 벌 나온다.

풀은 `orchestrator/llm_pool.py` 를 그대로 쓴다. 429 를 맞으면 그 후보를 소진 표시하고
다음으로 넘어가고, 성공한 후보는 pin 되고, RPM 은 60초 쿨다운으로 따로 처리된다 --
이 저장소가 이미 갖고 있는 것을 새로 짜지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import measure as ME                                   # noqa: E402
from mathdrift import ops as OPS                                      # noqa: E402
from mathdrift import space as SP                                     # noqa: E402

# **한 번에 받는 공간 수.** 크게 잡을수록 호출이 줄지만, 하나가 깨지면 그 묶음이 통째로
# 흔들리고 출력이 길어져 뒤엣것이 성의 없어진다. 5 는 출력 1,500토큰 남짓이라
# llm_pool 의 기본 상한(8,192)에 한참 못 미친다.
BATCH = 5


def prompt(parent: dict, picks: list[tuple[str, str, int]]) -> str:
    """**공간을 발명하라고 묻지 않는다.** 부모와 연산자를 주고 무엇이 되는지만 묻는다.
    인과성이 물음의 문법에 들어 있으므로 나중에 검사할 것이 없다."""
    cells = "\n".join(f"    {f}: {parent.get(f) or '(비어 있음)'}" for f in SP.FIELDS)
    lines = []
    for op, what, dist in picks:
        far = "  ← 먼 이주다. 한 걸음으로는 안 되는 갈아타기여도 좋다" if dist >= 2 else ""
        lines.append(f"  · {op} : {what}{far}")
    ops_block = "\n".join(lines)
    return f"""너는 행렬곱 복잡도 문제의 **형식화**를 넓히는 중이다. 답을 찾는 것이 아니라
**답을 찾을 수 있는 공간**을 적는 것이 일이다.

지금 있는 공간(부모):
{cells}

이 부모에 연산자를 하나씩 건다. {len(picks)}개다.

{ops_block}

연산자마다 공간 하나씩, **JSON 배열 하나로만** 답해라. 원소는 {len(picks)}개다.

  연산자  : 위 목록에 적힌 이름 그대로 (어느 것인지 짝을 맞추려는 칸이다)
  이름    : 이 공간을 한 마디로
  점      : 이 공간의 한 점은 무엇인가
  표기    : 점을 어떻게 적나
  되사상  : 이 공간의 점이 원래의 행렬곱 스킴으로 어떻게 돌아가나
  크기    : 유한/이산/연속 중 무엇이고 대략 얼마나 큰가
  왜      : 왜 이것이 그럴듯한가 (사람이 읽는 칸)

규칙 넷.

  · **엄밀할 필요 없다.** 정리도 증명도 아니다. 그럴듯하면 된다
  · **모르는 칸은 비워라.** 지어내지 마라 -- 빈 칸은 벌점이 아니다
  · **부모를 지우지 마라.** 부모의 무엇을 그대로 물려받는지가 `점` 이나 `표기` 에
    남아 있어야 한다. 아무 관계 없는 공간은 이 일이 아니다
  · **{len(picks)}개를 서로 다르게 써라.** 같은 부모에서 나오지만 연산자가 다르므로
    가는 곳도 달라야 한다

JSON 배열:"""


_OBJ = re.compile(r"\{[^{}]*\}", re.S)


def objects(raw) -> list[dict]:
    """**하나가 깨져도 나머지는 건진다.** 배열로 못 읽으면 중괄호 덩어리를 낱낱이 읽는다 --
    묶어 부르는 것의 값이 한 글자 때문에 다섯을 잃는 데서 사라지면 안 된다."""
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if not isinstance(raw, str):
        return []
    t = raw.strip()
    if "```" in t:
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            t = t[4:] if t.lstrip().startswith("json") else t
    i, j = t.find("["), t.rfind("]")
    if 0 <= i < j:
        try:
            d = json.loads(t[i:j + 1])
            if isinstance(d, list):
                return [x for x in d if isinstance(x, dict)]
        except ValueError:
            pass
    out = []
    for m in _OBJ.finditer(t):
        try:
            d = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def _pick_ops(led: dict, seed: str, n: int, k: int) -> list[tuple[str, str, int]]:
    """연산자 k 개. 겹치지 않게 뽑고, 덜 써 본 것으로 채운다."""
    got, i = [], 0
    while len(got) < k and i < k * 8:
        op, what, dist = OPS.draw(seed, n * k + i)
        if op not in {g[0] for g in got}:
            got.append((op, what, dist))
        i += 1
    for op in OPS.rarest(led["ops_used"]):
        if len(got) >= k:
            break
        if op not in {g[0] for g in got}:
            what, dist = OPS.BY_NAME[op]
            got.append((op, what, dist))
    return got[:k]


def step(led: dict, llm, seed: str, n: int, k: int = BATCH, log=print) -> list[dict]:
    """호출 한 번 = 공간 여러 개. **부모는 원장에서 고른다** -- 계보가 끊길 수가 없다."""
    if not led["spaces"]:
        log("[발산] 원장이 비어 있다 -- 씨앗 공간이 있어야 시작한다")
        return []
    picks = _pick_ops(led, seed, n, k)
    parent = led["spaces"][n % len(led["spaces"])]

    try:
        raw = llm(prompt(parent, picks))
    except Exception as e:                                    # noqa: BLE001
        log(f"[발산] 호출 실패({type(e).__name__}: {str(e)[:70]}) -- 건너뛴다")
        return []

    recs = objects(raw)
    if not recs:
        log("[발산] JSON 을 못 읽었다 -- 이 묶음을 건너뛴다")
        return []

    # **연산자 이름으로 짝짓는다.** 순서만 믿으면 모델이 하나를 빼먹었을 때 이후가 전부
    # 어긋난 부모-연산자로 원장에 박힌다. 이름이 안 맞는 것만 순서로 채운다.
    by_name = {op: (what, dist) for op, what, dist in picks}
    left = [p[0] for p in picks]
    out = []
    for rec in recs:
        want = (rec.get("연산자") or "").strip()
        if want not in by_name or want not in left:
            want = left[0] if left else None
        if want is None:
            break
        left.remove(want)
        _, dist = by_name[want]
        made = SP.add(led, rec, parent=parent["id"], op=want, dist=dist)
        made["잰것"] = ME.measure(made, parent)
        out.append(made)
        log(f"[발산] {made['id']} <- {parent['id']} / {want} : "
            f"{made.get('이름','')[:28]} -- {ME.note(made['잰것'])}")
    if len(out) < len(picks):
        log(f"[발산] {len(picks)}개 중 {len(out)}개만 왔다")
    return out


# 옛 이름. 한 번에 하나만 받던 시절의 서명 -- 배선 검사가 이것으로 짜여 있다.
def one(led: dict, llm, seed: str, n: int, log=print) -> dict | None:
    got = step(led, llm, seed, n, k=1, log=log)
    return got[0] if got else None


# ── 풀 ────────────────────────────────────────────────────────────────
def _pool():
    """`orchestrator/llm_pool.py` 를 그대로 쓴다. **여기서 임포트한다** -- dry 는
    무거운 것도 키도 안 끌고 온다."""
    from orchestrator import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("후보가 하나도 없다 (GEMINI_API_KEY 확인)")
    return llm_pool, pool


def _live():
    llm_pool, pool = _pool()

    def call(p: str) -> str:
        text, label = llm_pool.call(pool, p, pool_id="mathdrift", verbose=False)
        return text

    return call


def check() -> int:
    """**호출을 0회 하고** 지금 무엇을 쓸 수 있는지 본다. 300개를 걸기 전에 이것부터."""
    try:
        llm_pool, pool = _pool()
    except Exception as e:                                    # noqa: BLE001
        print(f"풀을 못 세웠다: {e}")
        return 1
    import quota_tracker as q

    keys, live = {}, 0
    for label, _ in pool:
        kid = label.split(":", 1)[0]
        keys.setdefault(kid, []).append(label)
    print(f"후보 {len(pool)}개 / 키 {len(keys)}개")
    print("  (한도는 **프로젝트** 단위다. 같은 프로젝트에서 키만 늘리면 한도는 그대로다)")
    for kid, labels in keys.items():
        alive = [lb for lb in labels
                 if not q.is_dead(lb) and q.remaining(lb) > 0 and not q.is_rpm_cooling(lb)]
        live += len(alive)
        rem = sum(max(0, q.remaining(lb)) for lb in alive)
        print(f"  {kid:<14} 후보 {len(labels):>2}개 · 지금 쓸 수 있는 것 {len(alive):>2}개 "
              f"· 남은 것으로 추정 {rem:,}회")
    if not live:
        print("\n지금 쓸 수 있는 후보가 없다 -- 돌려도 429 만 쌓인다.")
        return 3
    print(f"\n묶음 {BATCH}개씩이면 공간 300개에 호출 {-(-300 // BATCH)}회.")
    print("RPM 이 병목이므로 남은 일일 잔량보다 이 호출 수가 중요하다.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="이번에 낳을 공간 수(대략)")
    ap.add_argument("--batch", type=int, default=BATCH, help="호출 하나가 낳는 공간 수")
    ap.add_argument("--dry", action="store_true", help="호출 없이 프롬프트만 본다")
    ap.add_argument("--check", action="store_true", help="쓸 수 있는 후보를 본다(호출 0회)")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--lineage", default="")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    if a.check:
        return check()

    led = SP.load(a.path or None)

    if a.show:
        print(f"공간 {len(led['spaces'])}개")
        print(SP.brief(led))
        s = ME.spread(led)
        print(f"\n확산 {s['확산']}/{s['잰공간']} (몫 {s['몫']:.2f})")
        bad = sum(1 for x in led["spaces"] if x.get("등급") == "검증불가")
        print(f"검증불가 {bad}개 (되사상이 빈 것 -- 기각은 아니다)")
        print("연산자 씀: " + ", ".join(f"{k} {v}" for k, v in
                                     sorted(led["ops_used"].items(), key=lambda x: -x[1])))
        return 0

    if a.lineage:
        for sid in SP.lineage(led, a.lineage):
            r = SP.get(led, sid) or {}
            g = r.get("계보") or {}
            print(f"  {sid:<5} {g.get('연산자','씨앗'):<10} {r.get('이름','')}")
        return 0

    rounds = max(1, -(-a.n // max(1, a.batch)))

    if a.dry:
        for i in range(min(rounds, 3)):
            picks = _pick_ops(led, "dry", i, a.batch)
            print("=" * 70)
            print(prompt(led["spaces"][i % len(led["spaces"])], picks))
        return 0

    try:
        llm = _live()
    except Exception as e:                                    # noqa: BLE001
        print(f"못 돌린다: {e}")
        return 1

    t0, made = time.time(), 0
    for i in range(rounds):
        made += len(step(led, llm, seed=str(len(led["spaces"])), n=i, k=a.batch))
        SP.save(led, a.path or None)
        print(f"[발산] {i + 1}/{rounds}회 · 공간 {made}개 · {time.time() - t0:.0f}초")
    print(f"\n호출 {rounds}회로 {made}개를 원장에 올렸다. 공간 {len(led['spaces'])}개.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
