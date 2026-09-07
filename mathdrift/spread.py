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
    """**이름이 아니라 식이 표류한다.**

    처음에는 이름과 산문을 주고받았다. 그랬더니 모델이 부모 이름에 연산자 어휘를 덧붙이는
    데로 수렴했다(실측 85개) -- 프롬프트도 자도 전부 낱말이었으니 표류가 어휘 공간에서
    일어난 것이다. 이제 오가는 것은 **식과 수와 코드**다. 장식할 수가 없다.
    """
    body = "\n".join(f"    {f}: {parent.get(f) if parent.get(f) not in ('', None) else '(비어 있음)'}"
                     for f in ("이름", "식", "점", "치수", "정의역"))
    dec = (parent.get("해독") or "").strip()
    lines = []
    for op, what, dist in picks:
        far = "  ← 먼 이주다. 한 걸음으로 안 되는 갈아타기여도 좋다" if dist >= 2 else ""
        lines.append(f"  · {op} : {what}{far}")
    ops_block = "\n".join(lines)
    return f"""너는 행렬곱 복잡도 문제의 **식**을 넓히는 중이다. 해를 찾는 것이 아니라
**해를 찾을 수 있는 식**을 적는 것이 일이다.

지금 있는 식(부모):
{body}

부모의 해독기:
```python
{dec}
```

이 **식**에 연산자를 하나씩 건다. {len(picks)}개다.

{ops_block}

연산자마다 새 식 하나씩, **JSON 배열 하나로만** 답해라. 원소는 {len(picks)}개다.

  연산자    : 위 목록의 이름 그대로
  이름      : 이 식을 한 마디로
  식        : **바뀐 제약식 자체.** 부모 식이 어떻게 달라졌는지가 여기 보여야 한다
              (경계화면 극한이, 표수 이동이면 체가, 대칭성 강제면 불변 조건이)
  점        : 이 식의 해 하나는 무엇인가
  치수      : 점이 수 몇 개인가 (정수 하나)
  정의역    : 실수 R / 격자 {{-1,0,1}} / 유한체 F_2 / ... 중 무엇인가
  해독      : **파이썬 함수 하나.** `def decode(p):` 가 점 p(수의 리스트)를 받아
              (U, V, W, lambda) 를 돌려준다. U,V,W 는 4x7, lambda 는 길이 7.
              표준 라이브러리만. Fraction 은 이미 있다. 임포트하지 마라
  시금석점  : **이 공간에서 Strassen(m=7)에 해당하는 점.** decode 에 넣으면
              Strassen 스킴이 나와야 하는 수의 리스트
  왜        : 왜 이것이 그럴듯한가 (사람이 읽는 칸)

기계가 이렇게 검사한다. 산문으로는 못 빠져나간다.

  1. `decode(시금석점)` 을 **격리해서 돌린다**
  2. 나온 (U,V,W,lambda) 를 Brent 항등식으로 **정확 검산**한다
  3. 시금석점을 흔들어 다시 돌린다. **결과가 같으면 하드코딩으로 본다** --
     해독기가 자기 입력을 안 쓴 것이다

규칙 넷.

  · **엄밀할 필요 없다.** 정리도 증명도 아니다. 그럴듯한 식이면 된다
  · **모르는 칸은 비워라.** 지어내지 마라 -- 빈 칸은 벌점이 아니다
  · **부모 식을 부정하지 마라.** 부모의 해가 새 식 안에서도 해로 남아야 한다.
    Strassen 을 못 적는 식은 행렬곱의 새 관점이 아니라 다른 문제다
  · **{len(picks)}개를 서로 다르게 써라.** 연산자가 다르므로 식도 달라야 한다

JSON 배열:"""


_INNER = re.compile(r"\{[^{}]*\}", re.S)


def _balanced(t: str):
    """중괄호를 세어 **덩어리를 통째로** 떠낸다.

    처음에는 정규식 `\\{[^{{}}]*\\}` 로 떴는데, 그것은 **안쪽 중괄호가 없는 것만** 문다 --
    `{"해독": {"U": ...}}` 같이 겹친 것이 오면 바깥이 아니라 안쪽 `{"U": ...}` 를 집어
    온다. recall.py 의 답이 정확히 그 꼴이라, 멀쩡한 답을 "가능 칸이 없다" 며 거절로
    셌다(실측). 세어서 뜨면 겹쳐도 바깥이 잡힌다.
    """
    out, depth, start, instr, esc = [], 0, -1, False, False
    for i, ch in enumerate(t):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(t[start:i + 1])
                start = -1
            elif depth < 0:
                depth = 0
    return out


def objects(raw) -> list[dict]:
    """**하나가 깨져도 나머지는 건진다.** 통째로 못 읽으면 덩어리를 낱낱이 읽는다 --
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
    # **통째로 먼저 읽는다.** 겹친 중괄호가 있으면 이 길로만 온전히 온다.
    try:
        d = json.loads(t)
        if isinstance(d, dict):
            return [d]
        if isinstance(d, list):
            return [x for x in d if isinstance(x, dict)]
    except ValueError:
        pass
    i, j = t.find("["), t.rfind("]")
    if 0 <= i < j:
        try:
            d = json.loads(t[i:j + 1])
            if isinstance(d, list):
                return [x for x in d if isinstance(x, dict)]
        except ValueError:
            pass
    # **두 번 훑는다.** 세어 뜨는 것은 겹친 중괄호에 강하지만, 바깥이 안 닫힌 채
    # 깨져 오면 그 안의 멀쩡한 것까지 통째로 삼킨다(실측: 다섯 중 둘이 하나로 줄었다).
    # 그래서 세어 뜬 것을 먼저 건지고, **남은 자리**에 안쪽 덩어리 훑기를 한 번 더 건다.
    out, rest = [], t
    for chunk in _balanced(t):
        try:
            d = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
            rest = rest.replace(chunk, " ", 1)
    for m in _INNER.finditer(rest):
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


def remeasure(led: dict, path=None) -> int:
    """**호출 0회.** 원장에 이미 있는 것을 새 자로 다시 잰다.

    자를 고치면 지금까지 뽑은 것을 다시 뽑아야 하는 줄 알았는데, 잰 것은 원장에 다 있으므로
    다시 계산하면 된다. 자가 틀린 채로 300개를 뽑으면 어느 것이 쓸 만한지 못 고른다 --
    자를 먼저 맞추고 그 다음에 크게 돈다.

    바닥값(KEEP_MIN · KEEP_SHARE)을 **실측으로 정하라고** 분포를 같이 찍는다.
    """
    rows, was, now = [], 0, 0
    for rec in led["spaces"]:
        old = rec.get("잰것") or {}
        if old.get("씨앗"):
            continue
        parent = SP.get(led, (rec.get("계보") or {}).get("부모"))
        new = ME.measure(rec, parent)
        rec["잰것"] = new
        was += 1 if old.get("확산") else 0
        now += 1 if new["확산"] else 0
        rows.append((rec["id"], rec.get("계보", {}).get("연산자", ""), new,
                     old.get("확산"), rec.get("이름", ""),
                     ME.decorated(rec, parent)))
    SP.save(led, path)

    print(f"다시 잰 공간 {len(rows)}개 -- 확산 {was}개 → {now}개\n")
    print(f"{'id':<5} {'연산자':<10} {'물려':>4} {'부모몫':>7} {'장식':<4} {'판정':<6} 이름")
    for sid, op, m, oldok, name, deco in sorted(rows, key=lambda r: -r[2]["몫"]):
        mark = "확산" if m["확산"] else "약함"
        print(f"{sid:<5} {op:<10} {m['물려받음']:>4} {m['몫']:>7.3f} "
              f"{'장식' if deco else '  ':<4} {mark:<6} {name[:30]}")
    _d = sum(1 for r in rows if r[5])
    print(f"\n**이름이 부모 이름을 그대로 품은 것 {_d}/{len(rows)}개.** 이것이 높으면"
          " 이주가 아니라 작명이다 -- 그리고 낱말 겹침을 재는 자는 그것을 최고점으로 준다.")

    vals = sorted(r[2]["몫"] for r in rows)
    if vals:
        def q(f):
            return vals[min(len(vals) - 1, int(len(vals) * f))]
        print(f"\n부모몫 분포 -- 최소 {vals[0]:.3f} / 4분위 {q(.25):.3f} / 중앙 {q(.5):.3f}"
              f" / 3분위 {q(.75):.3f} / 최대 {vals[-1]:.3f}")
        print(f"지금 바닥값: 물려받음 >= {ME.KEEP_MIN} · 부모몫 >= {ME.KEEP_SHARE}")
        print("바닥값은 MATHDRIFT_KEEP_MIN / MATHDRIFT_KEEP_SHARE 로 바꿔 다시 재 본다.")
    return 0


def card(led: dict, sid: str) -> int:
    """공간 하나를 칸째로 펼친다. **이름만 보고 판정하지 않으려고 있는 것이다.**

    실측 2026-09-07(60개): 이름만 보면 부모 이름에 연산자 어휘를 덧붙인 것처럼 보이는
    무리가 있었다. 그것이 정말 작명인지 이주인지는 `점`·`표기`·`되사상` 을 봐야 안다.
    """
    rec = SP.get(led, sid)
    if rec is None:
        print(f"{sid} 가 원장에 없다")
        return 1
    g = rec.get("계보") or {}
    par = SP.get(led, g.get("부모"))
    print(f"{rec['id']}  <- {g.get('부모')} / {g.get('연산자')} (거리 {g.get('거리')})"
          f"  [{rec.get('등급')}]")
    print(f"계보: {' -> '.join(SP.lineage(led, sid))}")
    print(f"잰것: {ME.note(rec.get('잰것') or {})}\n")
    for f in SP.FIELDS:
        v = rec.get(f)
        print(f"  {f:<6}: {v if v else '(비어 있음)'}")
    if par:
        print(f"\n--- 부모 {par['id']} ---")
        for f in ("이름", "점", "표기", "되사상"):
            print(f"  {f:<6}: {par.get(f) or '(비어 있음)'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="이번에 낳을 공간 수(대략)")
    ap.add_argument("--batch", type=int, default=BATCH, help="호출 하나가 낳는 공간 수")
    ap.add_argument("--dry", action="store_true", help="호출 없이 프롬프트만 본다")
    ap.add_argument("--check", action="store_true", help="쓸 수 있는 후보를 본다(호출 0회)")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--remeasure", action="store_true",
                    help="원장을 새 자로 다시 잰다 (호출 0회)")
    ap.add_argument("--lineage", default="")
    ap.add_argument("--card", default="", help="공간 하나를 칸째로 (예: --card S34)")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    if a.check:
        return check()

    led = SP.load(a.path or None)

    if a.card:
        return card(led, a.card)

    if a.remeasure:
        return remeasure(led, a.path or None)

    if a.show:
        print(f"공간 {len(led['spaces'])}개")
        print(SP.brief(led))
        s = ME.spread(led)
        print(f"\n확산 {s['확산']}/{s['잰공간']} (몫 {s['몫']:.2f})"
              "  ← 낮으면 --remeasure 로 자부터 본다")
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
