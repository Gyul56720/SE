"""**발산** -- 공간을 최대한 많이 낳는다. 이 단계에서 죽이는 것은 없다.

    python3 mathdrift/spread.py --n 300              # Gemini 로 300개
    python3 mathdrift/spread.py --n 5 --dry          # 호출 없이 프롬프트만 본다
    python3 mathdrift/spread.py --show               # 원장을 본다
    python3 mathdrift/spread.py --lineage S17        # 씨앗까지의 사슬

## 왜 안 죽이나

공간은 틀릴 수 없다 -- 쓸모없을 뿐이다. 틀린 정리는 원장을 오염시키지만 빈 공간은
탐색해봐야 아무것도 안 나올 뿐이다. 그래서 발산에는 게이트를 안 건다. 4축 심판(재현 ·
비자명성 · 압축 · 실행 가능)은 **다음 커밋의 별도 배치**이고, 여기서 흉내내면 발산이 죽는다.

## 대신 스키마는 강제한다

만 개를 자유 산문으로 뽑아 두면 검증할 때 만 번을 다시 파싱해야 한다 -- 생성 비용만큼이
다시 든다. 그래서 `novel/flow.py` 와 같은 배치를 쓴다: **모델은 자유롭게 쓰고, 받는 것은
칸이다.** 칸이 비는 것은 허용하되, 칸 밖으로 나가는 것은 안 받는다.

## 모델 배치

`CLAUDE.md` 규칙 그대로. 발산은 호출 수가 전부이므로 **Gemini** 다. 여기(에이전트 세션)에서
직접 공간을 지어내 원장에 넣지 않는다 -- 파이프라인이 만든 것이 아니면 발산율도 계보도
거짓이 된다. 소설 쪽에서 산문을 직접 짓지 않는 것과 같은 이유다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import measure as ME                                   # noqa: E402
from mathdrift import ops as OPS                                      # noqa: E402
from mathdrift import space as SP                                     # noqa: E402


def prompt(parent: dict, op: str, what: str, dist: int) -> str:
    """**공간을 발명하라고 묻지 않는다.** 부모와 연산자를 주고 무엇이 되는지만 묻는다.
    인과성이 물음의 문법에 들어 있으므로 나중에 검사할 것이 없다."""
    cells = "\n".join(f"    {f}: {parent.get(f) or '(비어 있음)'}" for f in SP.FIELDS)
    far = ("\n이번 것은 **먼 이주**다. 한 걸음으로는 안 되는 갈아타기여도 좋다. "
           "다만 부모의 무엇을 그대로 물려받는지는 반드시 적어라.\n" if dist >= 2 else "")
    return f"""너는 행렬곱 복잡도 문제의 **형식화**를 넓히는 중이다. 답을 찾는 것이 아니라
**답을 찾을 수 있는 공간**을 하나 적는 것이 일이다.

지금 있는 공간:
{cells}

여기에 연산자 하나를 건다.

    연산자: {op}
    하는 일: {what}
{far}
이 연산자를 걸면 무엇이 되는지 아래 칸으로만 답해라. **JSON 하나만 내라.**

  이름    : 이 공간을 한 마디로
  점      : 이 공간의 한 점은 무엇인가
  표기    : 점을 어떻게 적나
  되사상  : 이 공간의 점이 원래의 행렬곱 스킴으로 어떻게 돌아가나
  크기    : 유한/이산/연속 중 무엇이고 대략 얼마나 큰가
  왜      : 왜 이것이 그럴듯한가 (사람이 읽는 칸)

규칙 셋.

  · **엄밀할 필요 없다.** 정리도 증명도 아니다. 그럴듯하면 된다
  · **모르는 칸은 비워라.** 지어내지 마라 -- 빈 칸은 벌점이 아니다
  · **부모를 지우지 마라.** 부모의 무엇을 그대로 물려받는지가 `점` 이나 `표기` 에
    남아 있어야 한다. 아무 관계 없는 공간은 이 일이 아니다

JSON:"""


def one(led: dict, llm, seed: str, n: int, log=print) -> dict | None:
    """한 걸음. **부모는 원장에서 고른다** -- 그래서 계보가 끊길 수가 없다."""
    if not led["spaces"]:
        log("[발산] 원장이 비어 있다 -- 씨앗 공간이 있어야 시작한다")
        return None
    # 덜 써 본 연산자 쪽으로 약하게 기울이되, 뽑기는 씨앗에 묶는다(재현된다).
    op, what, dist = OPS.draw(seed, n)
    rare = OPS.rarest(led["ops_used"])
    if led["ops_used"].get(op, 0) > (led["ops_used"].get(rare[0], 0) + 3):
        op = rare[0]
        what, dist = OPS.BY_NAME[op]
    parent = led["spaces"][n % len(led["spaces"])]

    p = prompt(parent, op, what, dist)
    try:
        raw = llm(p)
    except Exception as e:                                    # noqa: BLE001
        log(f"[발산] 호출 실패({type(e).__name__}) -- 건너뛴다")
        return None
    rec = _json(raw)
    if rec is None:
        log("[발산] JSON 이 아니라서 건너뛴다")
        return None

    out = SP.add(led, rec, parent=parent["id"], op=op, dist=dist)
    out["잰것"] = ME.measure(out, parent)
    log(f"[발산] {out['id']} <- {parent['id']} / {op} : "
        f"{out.get('이름','')[:30]} -- {ME.note(out['잰것'])}")
    return out


def _json(raw: str):
    """모델이 코드펜스나 앞말을 붙여 오는 것을 벗긴다. 못 벗기면 None."""
    if not isinstance(raw, str):
        return raw if isinstance(raw, dict) else None
    t = raw.strip()
    if "```" in t:
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        return None
    try:
        d = json.loads(t[i:j + 1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def _live():
    """Gemini 를 붙인다. **여기서 임포트한다** -- dry 는 무거운 것을 안 끌고 온다."""
    from novel import drive as D
    call = D._extractor(D.default_llm)
    if call is None:
        raise RuntimeError("Gemini 가 안 붙었다 (GEMINI_API_KEY 확인)")
    return call


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="이번에 낳을 공간 수")
    ap.add_argument("--dry", action="store_true", help="호출 없이 프롬프트만 본다")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--lineage", default="")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    led = SP.load(a.path or None)

    if a.show:
        print(f"공간 {len(led['spaces'])}개")
        print(SP.brief(led))
        s = ME.spread(led)
        print(f"\n확산 {s['확산']}/{s['잰공간']} (몫 {s['몫']:.2f})")
        print("연산자 씀: " + ", ".join(f"{k} {v}" for k, v in
                                     sorted(led["ops_used"].items(), key=lambda x: -x[1])))
        return 0

    if a.lineage:
        chain = SP.lineage(led, a.lineage)
        for sid in chain:
            r = SP.get(led, sid) or {}
            g = r.get("계보") or {}
            print(f"  {sid:<5} {g.get('연산자','씨앗'):<10} {r.get('이름','')}")
        return 0

    if a.dry:
        for i in range(a.n):
            op, what, dist = OPS.draw("dry", i)
            parent = led["spaces"][i % len(led["spaces"])]
            print("=" * 70)
            print(prompt(parent, op, what, dist))
        return 0

    try:
        llm = _live()
    except Exception as e:                                    # noqa: BLE001
        print(f"못 돌린다: {e}")
        return 1

    made = 0
    for i in range(a.n):
        if one(led, llm, seed=str(len(led["spaces"])), n=i) is not None:
            made += 1
        SP.save(led, a.path or None)
    print(f"\n{made}/{a.n} 개를 원장에 올렸다. 공간 {len(led['spaces'])}개.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
