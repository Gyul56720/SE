"""**프롬프트를 고치고, 점수로 채택하거나 되돌린다.**

이게 학습 루프의 마지막 조각이다. 지금까지는 사람이 눈으로 보고 고쳤고, 그래서 이
세션에서만 네 번 되돌렸다(예문 도배 · 번역투 · 늘어짐 · 토속 어휘). 되돌릴 수 있어야
최적화지, 아니면 표류다.

한 바퀴.

    1. 원고를 잰다                     score.py -- 호출 0회
    2. 제일 먼 축 하나를 고른다        여럿을 같이 고치면 어느 쪽이 움직였는지 모른다
    3. 그 축의 지시문만 다시 쓴다      claude -p 한 번. **원문은 안 준다** -- 수와 지금 지시문뿐
    4. 다시 돌려서 점수를 견준다       내려갔으면 채택, 올라갔으면 되돌린다
    5. 시도를 장부에 적는다            tune.jsonl -- 축 · 이전 · 이후 · 점수 전후

**원문은 여기 안 들어온다.** 표본도 원고도 아니고, 수와 지시문만 오간다 -- 원문 조각이
프롬프트로 새면 원고가 그것으로 도배된다는 것을 다섯 번 겪었다.

실행:
    python3 novel/tuner.py plan  novel/drift.json      # 무엇을 고칠지만 본다(호출 0)
    python3 novel/tuner.py try   novel/drift.json      # 지시문을 고쳐 써 넣는다(호출 1)
    python3 novel/tuner.py keep  novel/drift.json      # 다시 잰 점수로 채택/기각
    python3 novel/tuner.py log                         # 지금까지의 시도
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import dyn, score as SC, targets as TG                     # noqa: E402

HERE = Path(__file__).resolve().parent
LOG = Path(os.environ.get("DRIFT_TUNE_LOG", HERE / "tune.jsonl"))
# 챔피언 -- 지금까지 제일 좋았던 지시문 한 벌과 그 점수.
BEST = Path(os.environ.get("DRIFT_TUNE_BEST", HERE / "tune.best.json"))
CLAUDE = os.environ.get("DRIFT_CLAUDE", "claude")
# 지시문 한 줄의 길이 상한. 길어지면 그것도 묻힌다.
MAX_LEN = int(os.environ.get("DRIFT_DIRECTIVE_MAX", "220"))


def worst(path) -> tuple:
    """제일 먼 축과 그 거리. 없으면 (None, 0)."""
    s = SC.score(path)
    if not s:
        return None, 0.0, {}
    k, a = max(s["axes"].items(), key=lambda kv: kv[1]["gap"])
    return (k if a["gap"] > dyn.SLACK else None), s["total"], s


def side_of(axis: str, s: dict) -> str:
    a = s["axes"][axis]
    return "low" if a["got"] < a["lo"] else "high"


def ask_prompt(axis: str, side: str, s: dict, now: str) -> str:
    """**Claude 에게 줄 것.** 수와 지금 지시문뿐이다 -- 원문은 한 글자도 안 준다."""
    a = s["axes"][axis]
    return f"""소설 생성기의 지시문 한 줄을 고쳐 쓴다. 아래는 측정값이다.

축: {axis}
지금 우리 원고: {a['got']:.3f}
표본 소설의 폭: {a['lo']:.3f} ~ {a['hi']:.3f}
어느 쪽으로 벗어났나: {'모자란다' if side == 'low' else '넘친다'} (거리 {a['gap']:.2f})

지금 쓰고 있는 지시문:
{now}

이 지시문을 받고도 값이 저렇게 나왔다. **지시문이 틀렸다고 보고 다시 써라.**

규칙:
- 한국어 한 문장에서 세 문장 사이. {MAX_LEN}자를 넘기지 마라.
- **예를 들지 마라.** 예를 박으면 원고가 그 예로 도배된다.
- **수를 박지 마라.** 필요하면 자리표만 써라: {{got}} {{lo}} {{hi}} {{mid}}
- 무엇을 하지 말라고만 하지 말고 **무엇을 하라고** 말해라.
- 앞의 지시문과 다른 각도로 말해라. 같은 말을 다시 하면 같은 값이 나온다.

고친 지시문만 출력한다. 따옴표도 머리말도 쓰지 마라."""


def _call(prompt: str) -> str:
    out = subprocess.run([CLAUDE, "-p", prompt], capture_output=True, text=True,
                         timeout=180)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:200] or "claude -p 실패")
    return out.stdout.strip()


def read_directives() -> dict:
    return json.loads(dyn.PATH.read_text(encoding="utf-8"))


def write_directives(d: dict) -> None:
    dyn.PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    dyn._CACHE = None


def note(row: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rows() -> list:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]


def plan(path) -> int:
    axis, total, s = worst(path)
    print(f"표본: {TG.source()}")
    print(SC.table(s) if s else "잴 것이 없다")
    if not axis:
        print("\n고칠 것이 없다 -- 전부 표본 폭 안이다.")
        return 0
    print(f"\n다음에 고칠 축: **{axis}** ({side_of(axis, s)}) · 총점 {total:.3f}")
    return 0


def attempt(path, dry: bool = False) -> int:
    axis, total, s = worst(path)
    if not axis:
        print("고칠 것이 없다.")
        return 0
    side = side_of(axis, s)
    d = read_directives()
    now = (d["axes"].get(axis) or {}).get(side, "")
    p = ask_prompt(axis, side, s, now or "(아직 없다)")
    if dry:
        print(p)
        return 0
    new = _call(p)
    if not new or len(new) > MAX_LEN * 2:
        print(f"되받은 것이 쓸 수 없다({len(new)}자). 그대로 둔다.", file=sys.stderr)
        return 1
    d["axes"].setdefault(axis, {})[side] = new
    write_directives(d)
    note({"때": time.strftime("%m-%d %H:%M"), "무엇": "고침", "축": axis, "쪽": side,
          "전": now, "후": new, "점수(전)": total})
    print(f"[{axis}·{side}] 고쳐 넣었다. 총점 {total:.3f} 에서 출발한다.\n\n{new}\n\n"
          f"이제 다시 돌리고 `tuner.py keep` 로 견줘라.")
    return 0


def keep(path) -> int:
    """다시 돌린 뒤 부른다. 나아졌으면 채택, 나빠졌으면 되돌린다."""
    hist = [r for r in rows() if r["무엇"] == "고침"]
    if not hist:
        print("고친 기록이 없다.", file=sys.stderr)
        return 1
    last = hist[-1]
    _, total, _s = worst(path)
    was = last["점수(전)"]
    if total <= was:
        note({"때": time.strftime("%m-%d %H:%M"), "무엇": "채택", "축": last["축"],
              "점수(전)": was, "점수(후)": total})
        print(f"채택. 총점 {was:.3f} -> {total:.3f}")
        BEST.write_text(json.dumps({"총점": total, "axes": read_directives()["axes"]},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        return 0
    d = read_directives()
    d["axes"][last["축"]][last["쪽"]] = last["전"]
    write_directives(d)
    note({"때": time.strftime("%m-%d %H:%M"), "무엇": "되돌림", "축": last["축"],
          "점수(전)": was, "점수(후)": total})
    print(f"되돌렸다. 총점 {was:.3f} -> {total:.3f} 로 나빠졌다.")
    return 0


def show_log() -> int:
    for r in rows():
        if r["무엇"] == "고침":
            print(f"{r['때']}  고침  {r['축']}·{r['쪽']}  (총점 {r['점수(전)']:.3f})")
            print(f"    전: {r['전'][:70]}")
            print(f"    후: {r['후'][:70]}")
        else:
            print(f"{r['때']}  {r['무엇']}  {r['축']}  "
                  f"{r['점수(전)']:.3f} -> {r['점수(후)']:.3f}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="프롬프트를 고치고 점수로 채택한다")
    ap.add_argument("cmd", choices=["plan", "try", "keep", "log"])
    ap.add_argument("path", nargs="?", default="novel/drift.json")
    ap.add_argument("--dry", action="store_true", help="claude 에게 줄 것만 찍는다")
    a = ap.parse_args(argv)
    if a.cmd == "log":
        return show_log()
    if a.cmd == "plan":
        return plan(a.path)
    if a.cmd == "try":
        return attempt(a.path, a.dry)
    return keep(a.path)


if __name__ == "__main__":
    raise SystemExit(main())
