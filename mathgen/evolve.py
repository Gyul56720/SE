"""문제 생성기 자가개선 루프 -- Evol-Instruct 연산자로 난이도를 올리고, 심판이 채택을 정한다.

논문에서 가져온 것:

  Evol-Instruct / WizardMath (Microsoft) -- **In-Depth Evolving 5연산자.** 난이도를 올리는
      방향을 무작위 변이가 아니라 이름 붙은 연산자로 준다. 제약 추가 / 심화 / 구체화 /
      추론단계 증가 / 입력 복잡화. 한 라운드에 하나만 적용한다 -- 여러 개를 한꺼번에 걸면
      무엇이 효과였는지 알 수 없고, 실패했을 때 되돌릴 지점도 사라진다.

  VeriEvol -- **난이도와 정답 신뢰성을 분리한다.** 연산자는 난이도만 올리고, 정답은 별도
      검증이 보증한다. 여기서는 그 분리가 구조로 강제된다: 생성기가 답 F 를 먼저 정하고
      f = F' 를 문제로 내므로 정당성은 구성상 참이고, LLM 은 오직 "더 어렵게"만 하면 된다.
      LLM 이 정답을 판단할 일이 아예 없다.

  MathScale (Microsoft Research) -- 씨앗에서 개념을 뽑아 조합한다. 여기서는 씨앗 생성기의
      족(族) 목록이 그 역할을 한다.

  Google DeepMind, ICLR'24 (LLMs Cannot Self-Correct Reasoning Yet) -- 내재적 자기교정은
      개선이 없거나 성능을 떨어뜨린다. 그래서 채점에 LLM 을 한 방울도 안 쓴다. 심판은
      전부 sympy 다. 실패 사유만 LLM 에게 되돌려준다(외부 신호).

래칫: 새 생성기는 **정당성 100% · sympy 미해결 100% · 압축비는 챔피언보다 작을 것**.
세 조건을 동시에 넘어야 채택한다. 한 축만 좋아지는 교환을 허용하면 루프가 곧 "계산만 긴
문제"로 굴러떨어진다 -- 압축 코덱에서 3진 양자화가 그 지점이었다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "orchestrator"))

import judge  # noqa: E402

SEEDS = HERE / "seeds"
CHAMPION = HERE / "champion.py"
LEDGER = HERE / "ledger.json"
CANDIDATES = HERE / "candidates"

# Evol-Instruct 의 In-Depth Evolving. 이름과 취지는 논문 그대로, 대상만 자연어 지시가
# 아니라 **생성기 프로그램**이다.
OPERATORS = {
    "add_constraints": (
        "제약 추가 -- 답 F 에 조건을 하나 더 얹어라. 정의역 제한, 매개변수 부호 조건, "
        "특정 항이 상쇄되도록 만드는 계수 관계 같은 것. 문제가 좁아지되 답은 여전히 하나여야 한다."),
    "deepening": (
        "심화 -- 답 F 의 구조를 한 겹 더 깊게 만들어라. 합성의 중첩을 늘리거나, "
        "지금 쓰는 함수족을 더 다루기 어려운 것으로 바꿔라."),
    "concretizing": (
        "구체화 -- 일반적인 형태를 특정한 형태로 바꿔라. 임의 계수를 특정 수론적 성질을 "
        "갖는 값으로 고정해서, 그 성질을 알아야만 지름길이 보이게 만들어라."),
    "increase_steps": (
        "추론단계 증가 -- 답 F 를 두 개 이상의 조각이 결합된 형태로 만들어, 되찾으려면 "
        "분해 단계가 하나 더 필요하게 하라."),
    "complicate_input": (
        "입력 복잡화 -- 피적분함수의 겉모습을 바꿔라. 같은 F 라도 f 를 정리하지 않고 두거나 "
        "다른 형태로 묶어서, 구조가 한눈에 안 보이게 하라."),
}

PROMPT = '''문제 생성기 프로그램을 **더 어렵게** 고쳐라.

[지금 챔피언]
```python
{source}
```

[지금 성적] 정당성 {sound:.0%} · sympy 미해결 {unsolved:.0%} · 압축비 {ratio:.3f}

[이번에 적용할 연산자] {op_name}
{op_desc}

[계약] generate(seed: int) -> dict 하나만 정의한다. 반환은 다음 네 키:
    statement  사람이 읽는 문제문. **답을 절대 적지 마라 -- 적으면 즉시 실격이다**
    spec       {{"task": "integrate", "expr": "<피적분함수>", "var": "x"}}
    answer     정답 (sympy 가 파싱할 수 있는 문자열)
    solution   중간식 리스트. 각 원소는 sympy 가 파싱할 수 있어야 한다
같은 seed 에는 항상 같은 문제를 내라(random.Random(seed) 를 써라). sympy 와 표준
라이브러리만 쓴다.

[반드시 지킬 구성 방식] **답 F 를 먼저 정하고 f = diff(F, x) 를 문제로 내라.**
그러면 정답은 구성상 확실하다. 너는 정답이 맞는지 고민할 필요가 **전혀 없다** --
그건 심판이 미분해서 확인한다. 너는 오직 "sympy 가 f 에서 F 를 되찾지 못하게" 만드는
데만 집중하라.

[심판이 재는 것 -- 네가 아니라 sympy 가 잰다]
  ① 정당성    diff(답, x) 가 피적분함수와 같은가          (구성상 자동 통과)
  ② 비자명성  sympy.integrate 가 시간 안에 못 푸는가       ← 여기를 올려라
  ③ 압축성    풀이 연산수 / 펼친 문제의 연산수             ← 여기를 **낮춰라**
세 축을 **동시에** 넘어야 채택된다. ②만 올리려고 계수를 크게 키우면 ③이 나빠져 기각된다.
지저분해서 어려운 것이 아니라 **구조가 있어서 어려운 것**을 만들어라.

[실측으로 알려진 것] sympy 가 되찾지 못하는 족은 좁다. 12개 형태를 훑어 2개만 걸렸다:
  · (x^2+c)/sqrt(x^4+a*x+b) 꼴의 도함수   -> 시간 초과
  · exp(a*x*exp(b*x)) 꼴의 도함수          -> Integral 로 되돌아온다
다항x지수, 로그 합성, 중첩 근호, 역삼각 합성, 삼각 거듭 합성 등은 sympy 가 전부 되찾는다.
이 목록 밖에서 새 족을 찾으면 그것이 이번 라운드의 성과다.

{failure}

파이썬 코드만 ```python 블록 하나로 답하라.
'''


def _load_ledger() -> dict:
    if LEDGER.is_file():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"champion": None, "history": []}


def _save_ledger(led: dict) -> None:
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_champion() -> Path:
    """챔피언이 없으면 씨앗으로 시작한다."""
    if not CHAMPION.is_file():
        shutil.copy2(SEEDS / "backward_hard.py", CHAMPION)
        led = _load_ledger()
        led["champion"] = {"from": "backward_hard.py", "adopted_at": time.time()}
        _save_ledger(led)
    return CHAMPION


def _parse_code(text: str) -> str:
    if "```" not in text:
        return text.strip()
    block = text.split("```", 2)[1]
    if block.startswith("python"):
        block = block[len("python"):]
    return block.strip()


def one_round(operator: str = None, seeds=range(4), pool=None) -> dict:
    """한 라운드: 연산자 하나 적용 -> 심판 채점 -> 세 축 모두 이기면 챔피언 교체."""
    import llm_pool

    champ = ensure_champion()
    base = judge.evaluate(champ, seeds=seeds)
    if not base["passed"]:
        return {"status": "champion_broken", "reason": base["reason"]}

    led = _load_ledger()
    ops = list(OPERATORS)
    operator = operator or ops[len(led["history"]) % len(ops)]

    last = next((h for h in reversed(led["history"]) if not h["adopted"]), None)
    failure = (f"[직전 시도가 기각된 이유]\n{last['reason']}\n"
               "같은 방식으로 다시 시도하지 마라." if last else "")

    m = base["mean"]
    prompt = PROMPT.format(source=champ.read_text(encoding="utf-8"),
                           sound=m["sound"], unsolved=1 - m["machine_solved"],
                           ratio=m["compress_ratio"], op_name=operator,
                           op_desc=OPERATORS[operator], failure=failure)

    pool = pool or llm_pool.build_pool()
    if not pool:
        return {"status": "no_pool",
                "reason": "LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라"}
    text, label = llm_pool.call(pool, prompt, pool_id="mathgen")

    CANDIDATES.mkdir(exist_ok=True)
    cand = CANDIDATES / f"cand-{time.strftime('%Y%m%d-%H%M%S')}.py"
    cand.write_text(_parse_code(text), encoding="utf-8")

    # 여기서부터가 채택 판정. LLM 은 관여하지 않는다.
    try:
        res = judge.evaluate(cand, baseline=champ, seeds=seeds)
        reason, passed = res["reason"], res["passed"]
        ratio = res["mean"]["compress_ratio"]
    except judge.GeneratorFailure as e:
        reason, passed, ratio = f"실격: {e}", False, None

    entry = {"ts": time.time(), "operator": operator, "model": label,
             "candidate": str(cand), "adopted": passed, "reason": reason,
             "compress_ratio": ratio, "champion_ratio": m["compress_ratio"]}
    led["history"].append(entry)

    if not passed:
        _save_ledger(led)
        return {"status": "rejected", "operator": operator, "reason": reason,
                "candidate": str(cand)}

    n = len([h for h in led["history"] if h["adopted"]])
    keep = HERE / f"champion_v{n}.py"
    shutil.copy2(cand, keep)
    shutil.copy2(cand, CHAMPION)
    led["champion"] = {"from": keep.name, "adopted_at": time.time(),
                       "operator": operator, "compress_ratio": ratio}
    _save_ledger(led)
    return {"status": "adopted", "operator": operator, "champion": keep.name,
            "compress_ratio": ratio, "previous_ratio": m["compress_ratio"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="어려운 문제 생성기 자가개선 루프")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--operator", default=None, choices=list(OPERATORS))
    ap.add_argument("--instances", type=int, default=4)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    seeds = range(a.instances)

    if a.status:
        champ = ensure_champion()
        res = judge.evaluate(champ, seeds=seeds)
        m = res["mean"]
        print(f"챔피언 {champ.name}")
        print(f"  정당성 {m['sound']:.0%} · sympy 미해결 {1 - m['machine_solved']:.0%} "
              f"· 압축비 {m['compress_ratio']:.3f}")
        led = _load_ledger()
        print(f"  채택 {len([h for h in led['history'] if h['adopted']])}회 / "
              f"시도 {len(led['history'])}회")
        return 0

    for i in range(1, a.rounds + 1):
        r = one_round(a.operator, seeds)
        print(f"[라운드 {i}] {r['status']} ({r.get('operator', '-')}) "
              f"-- {r.get('reason') or r.get('champion', '')}")
        if r["status"] == "adopted":
            print(f"  압축비 {r['previous_ratio']:.3f} -> {r['compress_ratio']:.3f}")
        if r["status"] in ("no_pool", "champion_broken"):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
