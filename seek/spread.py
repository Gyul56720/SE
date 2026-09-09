r"""**문제를 낳는다.** 프롬프트가 요구하는 것은 식이 아니라 **판정기**다.

mathdrift 의 프롬프트는 "그럴듯한 식이면 된다" 였고, 51개 중 41개가 뜻이 안 정해진
기호를 갖고 돌아왔다. 규칙 위반이 아니라 **규칙을 지킨 것**이다 -- 그럴듯한 식은
Phi 를 안 정해도 그럴듯하고, 정하는 것보다 싸다.

여기서는 그 말이 성립하지 않는다. **판정기는 그럴듯할 수가 없다. 돌거나 안 돌거나다.**
그리고 안 도는 것은 `problem.add()` 가 안 받는다 -- 프롬프트가 부탁하는 것이 아니라
원장이 못 받는 것이다.

    python3 seek/spread.py --n 10 --dry     # 호출 없이 프롬프트만 본다
    python3 seek/spread.py --n 20 --점검     # 호출 없이 쓸 수 있는 후보와 잔량을 본다
    python3 seek/spread.py --n 20           # 낳는다
    python3 seek/spread.py --show

호출은 전부 `orchestrator/llm_pool.py` 로 나간다 -- 아래 '## 풀' 참고. 여기서 제
반복문을 짜지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import judge as J                                   # noqa: E402
from seek import ops as OPS                                   # noqa: E402
from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402

BATCH = int(os.environ.get("BATCH", "3"))


def prompt(parent: dict, picks: list) -> str:
    """부모 문제 하나에 연산자 K 개를 걸어 자식 문제 K 개를 받는다.

    **판정기를 달라고 한다.** 그것이 이 프롬프트의 전부다."""
    lines = "\n".join(f"  · {op} : {what}" for op, what, _ in picks)
    return f"""너는 **문제를 낳는 중**이다. 답을 찾는 것이 아니라, 답을 **기계가 검산할 수
있는 새 문제**를 적는 것이 일이다.

지금 있는 문제(부모):

  물음: {parent.get('물음')}

  표본:
{_ind(parent.get('표본'))}

  판정:
{_ind(parent.get('판정'))}

이 문제에 연산자를 하나씩 건다. {len(picks)}개다.

{lines}

## 무엇을 돌려주나

연산자마다 문제 하나씩. 네 칸이다.

  물음 : 사람이 읽는 한 줄. 여기만 한국어다
  표본 : `def sample(rng):` 무작위 후보 **하나**를 돌려준다. rng 는 random.Random 이다
  판정 : `def judge(x):` 그 후보가 답이면 True, 아니면 False. **반드시 참/거짓이다**
  옮김 : `def embed(x):` **부모의 후보**를 이 문제의 후보로 바꾼다

## 규칙 -- 여기가 전부다

  · **판정기가 돌지 않으면 원장이 안 받는다.** 부탁이 아니라 문법이다.
    `pass` 도 안 되고, None 을 돌려줘도 안 되고, 터져도 안 된다
  · **판정은 유한 시간에 끝나야 한다.** 후보 하나에 1초 안쪽. 전수 계산이 제일 좋다
  · **판정이 후보의 꼴을 먼저 봐라.** 꼴이 아니면 `raise ValueError`.
    이것을 안 하면 나중에 이 문제가 부모가 됐을 때 자식이 넓어졌는지를 잴 수가 없다
  · **표준 라이브러리만.** 임포트는 판정기 안에서 해라. numpy 는 없다
  · **`옮김`은 부모의 답이 여기서도 답인지 보는 자리다.** 부모의 후보를 그대로 쓸 수
    있으면 그대로 돌려주면 된다
  · 판정기 안에 "그럴듯한" 것은 없다. **돌거나 안 돌거나다**

## 꼴

JSON 배열 하나로만 답한다. 원소는 {len(picks)}개다.

[{{"연산자": "...", "물음": "...", "표본": "def sample(rng):\\n    ...",
  "판정": "def judge(x):\\n    ...", "옮김": "def embed(x):\\n    ..."}}]
"""


def _ind(code) -> str:
    return "\n".join("    " + l for l in str(code or "").split("\n"))


def objects(raw: str) -> list:
    """JSON 배열을 건진다. 깨지면 중괄호 덩어리를 낱낱이 건진다.

    mathdrift 가 겪은 것과 같은 자리다 -- 하나가 깨졌다고 묶음 전체를 잃지 않는다.
    다만 여기는 LaTeX 이 아니라 파이썬이라 역슬래시 사고는 덜하다."""
    t = raw.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.M).strip()
    try:
        got = json.loads(t)
        if isinstance(got, list):
            return [g for g in got if isinstance(g, dict)]
        if isinstance(got, dict):
            return [got]
    except Exception:                                         # noqa: BLE001
        pass
    out, depth, start = [], 0, None
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    g = json.loads(t[start:i + 1])
                    if isinstance(g, dict):
                        out.append(g)
                except Exception:                             # noqa: BLE001
                    pass
                start = None
    return out


def _pick(led: dict, seed: str, n: int, k: int) -> list:
    got, i = [], 0
    while len(got) < k and i < k * 8:
        op, what, dist = OPS.draw(seed, n * k + i)
        if op not in {g[0] for g in got}:
            got.append((op, what, dist))
        i += 1
    used = {}
    for p in led.get("problems", []):
        o = (p.get("계보") or {}).get("연산자")
        used[o] = used.get(o, 0) + 1
    for op in OPS.rarest(used):
        if len(got) >= k:
            break
        if op not in {g[0] for g in got}:
            w, d = OPS.BY_NAME[op]
            got.append((op, w, d))
    return got[:k]


def step(led: dict, llm, seed: str, n: int, k: int = BATCH, log=print) -> list:
    """호출 한 번 = 문제 여럿. **안 도는 판정기는 원장이 안 받는다.**"""
    ps = led.get("problems") or []
    if not ps:
        log("[낳기] 원장이 비어 있다")
        return []
    parent = ps[n % len(ps)]
    picks = _pick(led, seed, n, k)
    try:
        raw = llm(prompt(parent, picks))
    except Exception as e:                                    # noqa: BLE001
        log(f"[낳기] 호출 실패({type(e).__name__}: {str(e)[:70]})")
        return []
    recs = objects(raw)
    if not recs:
        log("[낳기] JSON 을 못 읽었다")
        return []

    by = {op: (w, d) for op, w, d in picks}
    left = [p[0] for p in picks]
    out = []
    for rec in recs:
        want = (rec.get("연산자") or "").strip()
        if want not in by or want not in left:
            want = left[0] if left else None
        if want is None:
            break
        left.remove(want)
        try:
            made = PR.add(led, rec, parent=parent["id"], op=want)
        except PR.NotAProblem as e:
            # **이것이 이 설계의 요점이다.** 안 받는 것을 세어 보여 준다.
            log(f"[낳기] {want:<10} 안 받았다 -- {e}")
            continue
        except ValueError as e:
            log(f"[낳기] {want:<10} 안 받았다 -- {e}")
            continue
        out.append(made)
        log(f"[낳기] {made['id']} <- {parent['id']} / {want} : {str(made.get('물음'))[:52]}")
    return out


# ── 풀 ────────────────────────────────────────────────────────────────
# **`orchestrator/llm_pool.py` 를 그대로 쓴다.** 여기서 제 반복문을 짜면 안 된다 --
# 그 파일이 아는 것을 하나도 모르는 채로 돈다:
#
#   · 429 를 **분당 한도**와 **오늘 치 소진**으로 가른다. 앞의 것은 60초면 풀리는데
#     뒤의 것으로 읽으면 멀쩡한 키를 자정까지 봉인한다 (tests/test_llm_pool_rpm.py).
#   · 500/503 은 쿼터가 아니라 일시장애다 -- 두 번 거듭 나야 잠깐 쉬게 한다.
#   · 같은 **키**를 MIN_GAP 안에 다시 두드리지 않는다. 모델만 바꿔 봐야 한도는 키에
#     붙어 있다.
#   · 재본 응답 시간과 성공률로 다음 후보를 고른다. 이름 등급은 안 재본 것의 기본값.
#   · 한 바퀴가 전부 RPM 이면 "이 키로는 못 한다" 가 아니라 "지금은 못 한다" 이므로
#     쿨다운만큼 자고 다시 돈다 (RPM_ROUNDS).
#
# 그래서 여기가 하는 일은 **부르는 것뿐**이다. pool_id 만 "seek" 로 준다.
def _pool():
    """**여기서 임포트한다** -- `--dry` 와 `--show` 는 키도 무거운 것도 안 끌고 온다."""
    from orchestrator import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("후보가 하나도 없다 (GEMINI_API_KEY 확인)")
    return llm_pool, pool


def _live(verbose: bool = True):
    """`verbose` 가 참이면 어느 후보가 왜 막혔는지 llm_pool 이 stderr 에 적는다.

    **기본을 참으로 둔다.** 거짓으로 두면 30분을 돌고도 "호출 실패" 한 줄만 남아,
    분당 한도로 쉬는 중인지 오늘 치가 다 된 것인지 500 을 맞는 중인지 구분할 수가
    없다. 그 구분은 llm_pool 이 이미 갈라서 찍고 있다 -- 끄지 않으면 그냥 보인다.
    """
    llm_pool, pool = _pool()

    def call(p: str) -> str:
        text, label = llm_pool.call(pool, p, pool_id="seek", verbose=verbose)
        call.label = label
        return text

    call.label = ""
    return call


def check(n: int = 0, batch: int = BATCH) -> int:
    """**호출 0회.** 지금 무엇을 쓸 수 있는지 본다. 크게 걸기 전에 이것부터.

    `llm_pool` 이 후보를 고를 때 보는 것과 **같은 자(quota_tracker)** 로 센다 --
    여기서 "쓸 수 있는 것 0개" 면 돌려도 429 만 쌓인다.
    """
    try:
        llm_pool, pool = _pool()
    except Exception as e:                                    # noqa: BLE001
        print(f"풀을 못 세웠다: {e}")
        return 1
    import quota_tracker as q

    keys, live = {}, 0
    for label, _ in pool:
        keys.setdefault(label.split(":", 1)[0], []).append(label)
    print(f"후보 {len(pool)}개 / 키 {len(keys)}개")
    print("  (한도는 **프로젝트** 단위다. 같은 프로젝트에서 키만 늘리면 한도는 그대로다)")
    for kid, labels in keys.items():
        alive = [lb for lb in labels
                 if not q.is_dead(lb) and q.remaining(lb) > 0 and not q.is_rpm_cooling(lb)]
        live += len(alive)
        rem = sum(max(0, q.remaining(lb)) for lb in alive)
        cool = sum(1 for lb in labels if q.is_rpm_cooling(lb))
        tail = f" · 분당 한도로 쉬는 중 {cool}개(60초면 풀린다)" if cool else ""
        print(f"  {kid:<14} 후보 {len(labels):>2}개 · 지금 쓸 수 있는 것 {len(alive):>2}개 "
              f"· 남은 것으로 추정 {rem:,}회{tail}")
    if not live:
        print("\n지금 쓸 수 있는 후보가 없다 -- 돌려도 429 만 쌓인다.")
        return 3
    if n:
        rounds = max(1, -(-n // max(1, batch)))
        print(f"\n묶음 {batch}개씩이면 문제 {n}개에 호출 {rounds}회.")
        print("RPM 이 병목이므로 남은 일일 잔량보다 이 호출 수가 중요하다.")
    return 0


def show(led: dict) -> int:
    ps = led.get("problems", [])
    print(f"문제 {len(ps)}개\n")
    print(PR.brief(led))
    solved = sum(1 for p in ps if p.get("답") is not None)
    print(f"\n푼 것 {solved}/{len(ps)}개")
    used = {}
    for p in ps:
        o = (p.get("계보") or {}).get("연산자", "씨앗")
        used[o] = used.get(o, 0) + 1
    print("연산자 씀: " + ", ".join(f"{k} {v}" for k, v in
                                  sorted(used.items(), key=lambda x: -x[1])))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=9)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--점검", dest="check", action="store_true",
                    help="호출 0회. 지금 쓸 수 있는 후보와 잔량을 본다")
    ap.add_argument("--조용히", dest="quiet", action="store_true",
                    help="어느 후보가 왜 막혔는지 안 찍는다 (기본은 찍는다)")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    led = PR.load(a.path or None)

    if a.show:
        return show(led)
    if a.check:
        return check(a.n, a.batch)
    rounds = max(1, -(-a.n // max(1, a.batch)))
    if a.dry:
        for i in range(min(rounds, 2)):
            ps = led["problems"]
            print("=" * 70)
            print(prompt(ps[i % len(ps)], _pick(led, "dry", i, a.batch)))
        return 0
    if check(a.n, a.batch) == 3:
        # **먼저 세어 보고 안 돈다.** llm_pool 이 후보를 고를 때 보는 것과 같은 자로
        # 세어서 하나도 없으면, 20바퀴를 돌아 봐야 429 만 20번 쌓이고 끝난다.
        return 3
    try:
        llm = _live(verbose=not a.quiet)
    except Exception as e:                                    # noqa: BLE001
        print(f"못 돌린다: {e}")
        return 1

    # **풀이 통째로 죽었는지 본다.** step 은 호출이 터져도 [] 만 돌려주므로(배선 검사가
    # 그 계약을 붙들고 있다), 여기서 따로 센다. 안 그러면 키가 다 소진된 뒤에도 남은
    # 바퀴를 전부 돌며 같은 실패를 되풀이한다 -- 로그만 길어지고 얻는 것은 없다.
    fails = [0]
    _raw = llm

    def llm(p):                                               # noqa: F811
        try:
            got = _raw(p)
        except Exception:
            fails[0] += 1
            raise
        fails[0] = 0
        return got

    t0, made = time.time(), 0
    done = 0
    for i in range(rounds):
        done = i + 1
        made += len(step(led, llm, seed=str(len(led["problems"])), n=i, k=a.batch))
        PR.save(led, a.path or None)
        print(f"[낳기] {done}/{rounds}회 · 받은 문제 {made}개 · {time.time() - t0:.0f}초")
        if fails[0] >= 2:
            print(f"[낳기] 호출이 연달아 {fails[0]}번 다 막혔다 -- 여기서 멈춘다."
                  " `--점검` 으로 잔량을 보고 다시 걸어라")
            break
    print(f"\n호출 {done}회로 {made}개가 원장에 올랐다. 문제 {len(led['problems'])}개.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
