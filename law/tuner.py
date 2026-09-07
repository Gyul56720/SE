"""**지시문을 고치고, 관문 점수로 채택하거나 되돌린다.** novel/tuner.py 를 법으로 옮긴 것.

옮기면서 하나가 좋아졌다. 소설에서 축은 문장 길이·대사 몫 같은 **취향**이었고, 그래서
목표값을 표본 소설에서 끌어와야 했다(novel/targets.py 가 "우리 요구가 표본과 5배
어긋났다" 고 적어둔 그 문제). 법의 축은 **관문 규칙**이고 목표값은 전부 0이다. 표본이
필요 없고, 어느 쪽으로 벗어났는지(low/high)도 없다 -- 위반은 한 방향이다.

한 바퀴.

    1. 산출물을 잰다               law/gate.py + law/issuegate.py -- LLM 호출 0회
    2. 제일 많이 걸린 규칙 하나     여럿을 같이 고치면 어느 쪽이 움직였는지 모른다
    3. 그 규칙의 지시문만 다시 쓴다  claude -p 한 번. **산출물 본문은 안 준다**
    4. 다시 생성해서 점수를 견준다   내려갔으면 채택, 아니면 되돌린다
    5. 장부에 적는다                law/tune.jsonl

novel/tuner.py 가 피 흘려 배운 것 셋을 그대로 가져왔다:

- **쉬는 축**(cooling) -- 한 축을 내리 두 번 되돌리면 여섯 바퀴 건너뛴다. 안 그러면 제일
  먼 축이 그대로라 다음 바퀴도 같은 축이 뽑힌다(실측: 여섯 시간에 한 축만 두드렸다).
- **시도마다 결론은 한 번**(_pending) -- 마지막 '고침' 을 매 바퀴 다시 집으면, 한 바퀴 전에
  채택한 것을 다음 바퀴가 조용히 되돌린다.
- **되받은 것을 그대로 싣지 않는다**(_clean) -- 머리말·코드펜스·따옴표가 통째로 프롬프트에
  들어간 적이 있다.

여기서 하나를 더 넣었다. **재생성 없이는 심판하지 않는다.** 지시문을 고쳐도 산출물이
그대로면 점수가 같을 수밖에 없고, 같은 점수는 '되돌림' 이니 무엇을 써도 되돌아간다.
그래서 keep 은 잰 파일들의 지문을 견주고, 안 바뀌었으면 판정을 거부한다.

    python3 law/tuner.py plan                    # 무엇을 고칠지만 본다 (호출 0)
    python3 law/tuner.py try                     # 지시문을 고쳐 넣는다 (호출 1)
    python3 law/tuner.py try --dry               # claude 에게 줄 것만 찍는다
    (생성기를 다시 돌린다)
    python3 law/tuner.py keep                    # 다시 잰 점수로 채택/되돌림
    python3 law/tuner.py log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import gate as GT                                            # noqa: E402
from law import issue as IS                                           # noqa: E402
from law import issuegate as JG                                       # noqa: E402

HERE = Path(__file__).resolve().parent
DIRECTIVES = Path(os.environ.get("LAW_DIRECTIVES", HERE / "directives.json"))
LOG = Path(os.environ.get("LAW_TUNE_LOG", HERE / "tune.jsonl"))
BEST = Path(os.environ.get("LAW_TUNE_BEST", HERE / "tune.best.json"))
CLAUDE = os.environ.get("LAW_CLAUDE", os.environ.get("DRIFT_CLAUDE", "claude"))
MAX_LEN = int(os.environ.get("LAW_DIRECTIVE_MAX", "220"))

GIVEUP = int(os.environ.get("LAW_TUNE_GIVEUP", "2"))   # 몇 번 되돌리면 쉬나
COOL = int(os.environ.get("LAW_TUNE_COOL", "6"))       # 몇 번의 시도 동안 쉬나

# soft 를 hard 와 같이 세면 보고용 규칙이 기각용 규칙을 덮는다. 5분의 1로 센다.
SOFT_WEIGHT = 0.2

DEFAULT_TARGETS = ("법이론서", "law/cases")


# ---------------------------------------------------------------- 재기

def _files(targets) -> tuple:
    docs, cases = [], []
    for t in targets:
        p = Path(t)
        if p.is_file():
            (cases if p.suffix == ".json" else docs).append(p)
        elif p.is_dir():
            docs += [f for f in sorted(p.rglob("*.md"))
                     if not f.name.lower().startswith("readme")]
            cases += [f for f in sorted(p.rglob("*.json"))
                      if not f.name.startswith("_")]
    return docs, cases


def fingerprint(targets=DEFAULT_TARGETS) -> str:
    """잰 파일들의 지문. **재생성이 실제로 있었는지**를 이걸로 안다."""
    h = hashlib.sha256()
    docs, cases = _files(targets)
    for f in docs + cases:
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def measure(targets=DEFAULT_TARGETS, corpus=None) -> dict:
    """관문을 전부 돌려 규칙별 점수를 낸다. **LLM 호출 0회.**

    gap = (hard + 0.2*soft) / 잰 것의 수. 대상 수로 나누는 이유: 문서를 더 만들면 위반도
    같이 늘어난다. 나누지 않으면 '많이 만들수록 나빠진' 것으로 보여서 채택 판정이 뒤집힌다.
    """
    corpus = corpus if corpus is not None else CP.load()
    docs, cases = _files(targets)
    axes = {}
    checked = unverified = 0

    def add(v):
        a = axes.setdefault(v.rule, {"hard": 0, "soft": 0})
        a[v.severity] += 1

    for f in docs:
        vs, c, u = GT.check(GT.parse(f), corpus)
        checked += c
        unverified += u
        for v in vs:
            add(v)
    for f in cases:
        try:
            case = IS.load(f)
        except Exception as e:                       # 사건 파일이 깨진 것도 결과다
            axes.setdefault("J000", {"hard": 0, "soft": 0})["hard"] += 1
            print(f"  (읽지 못한 사건 파일 {f}: {e})", file=sys.stderr)
            continue
        vs, c, u = JG.check(case, corpus=corpus)
        checked += c
        unverified += u
        for v in vs:
            add(v)

    n = max(1, len(docs) + len(cases))
    for a in axes.values():
        a["gap"] = (a["hard"] + SOFT_WEIGHT * a["soft"]) / n
    return {"axes": axes, "total": sum(a["gap"] for a in axes.values()),
            "checked": checked, "unverified": unverified,
            "docs": len(docs), "cases": len(cases), "n": n}


def table(s: dict) -> str:
    if not s["axes"]:
        return f"위반 없음 (문서 {s['docs']} · 사건 {s['cases']})"
    rows = sorted(s["axes"].items(), key=lambda kv: -kv[1]["gap"])
    out = [f"{'규칙':<6}{'hard':>6}{'soft':>6}{'거리':>9}"]
    for k, a in rows:
        out.append(f"{k:<6}{a['hard']:>6}{a['soft']:>6}{a['gap']:>9.3f}")
    out.append(f"총점 {s['total']:.3f}  ·  문서 {s['docs']} · 사건 {s['cases']}")
    out.append(f"인용 대조: 검증 {s['checked']}건 · 미검증 {s['unverified']}건")
    return "\n".join(out)


# ---------------------------------------------------------------- 장부

def note(row: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rows() -> list:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def cooling() -> set:
    """지금 건너뛸 규칙. 최근 시도에서 내리 되돌린 것들이다.

    **새것부터 훑는다.** 채택이 나오면 그 축은 거기서 끊는다 -- 그보다 오래된 되돌림은
    이미 극복된 것이라 세면 안 된다(novel/tuner.py 가 배운 것 그대로).
    """
    fail, cleared, seen = {}, set(), 0
    for r in reversed(rows()):
        if r["무엇"] not in ("채택", "되돌림"):
            continue
        seen += 1
        if seen > COOL:
            break
        k = r.get("축")
        if not k or k in cleared:
            continue
        if r["무엇"] == "채택":
            cleared.add(k)
            fail.pop(k, None)
        else:
            fail[k] = fail.get(k, 0) + 1
    return {k for k, n in fail.items() if n >= GIVEUP}


# ---------------------------------------------------------------- 지시문

def read_directives() -> dict:
    return json.loads(DIRECTIVES.read_text(encoding="utf-8"))


def write_directives(d: dict) -> None:
    DIRECTIVES.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                          encoding="utf-8")


def block(s: dict | None = None, limit: int = 8) -> str:
    """생성기 프롬프트에 실을 지시문 덩어리.

    **걸린 규칙의 지시문만 싣는다.** 열여덟 줄을 다 실으면 실제로 걸리는 것이 묻힌다.
    측정값을 안 주면(s=None) 전부 싣는다 -- 첫 바퀴에는 잴 것이 없다.
    """
    d = read_directives()["rules"]
    keys = list(d)
    if s and s.get("axes"):
        keys = [k for k, _ in sorted(s["axes"].items(), key=lambda kv: -kv[1]["gap"])
                if k in d][:limit]
    return "\n".join(f"- {d[k]['지시']}" for k in keys)


def worst(s: dict, skip=None) -> tuple:
    """제일 많이 걸린 규칙과 그 거리. 없으면 (None, ...).

    **쉬는 축은 건너뛴다.** 전부 쉬는 중이면 그때는 제일 먼 것을 그냥 쓴다 -- 아무것도
    안 하는 것보다 낫다.
    """
    if not s["axes"]:
        return None, 0.0
    skip = cooling() if skip is None else skip
    live = {k: v for k, v in s["axes"].items() if k not in skip}
    k, a = max((live or s["axes"]).items(), key=lambda kv: kv[1]["gap"])
    return (k if a["gap"] > 0 else None), a["gap"]


def ask_prompt(rule: str, s: dict, now: str, aim: str) -> str:
    """**claude 에게 줄 것.** 수와 지금 지시문뿐이다 -- 산출물 본문은 한 글자도 안 준다.

    novel 에서 다섯 번 겪은 것이 근거다: 원문 조각이 프롬프트로 새면 산출물이 그것으로
    도배된다. 법에서는 더 나쁘다 -- 위반 사례의 문장을 실어 주면 그 표현이 다음 산출물에
    그대로 다시 나온다.
    """
    a = s["axes"][rule]
    return f"""법 학습자료 생성기의 지시문 한 줄을 고쳐 쓴다. 아래는 측정값이다.

규칙: {rule}
이 규칙이 지키려는 것: {aim}
잰 결과: 기각 위반 {a['hard']}건 · 보고 위반 {a['soft']}건 (대상 {s['n']}개, 거리 {a['gap']:.3f})
목표: 0건

지금 쓰고 있는 지시문:
{now}

이 지시문을 받고도 위반이 저만큼 나왔다. **지시문이 틀렸다고 보고 다시 써라.**

규칙:
- 한국어 한 문장에서 세 문장 사이. {MAX_LEN}자를 넘기지 마라.
- **예를 들지 마라.** 예를 박으면 산출물이 그 예로 도배된다.
- 조문 번호나 법령 이름을 박지 마라. 어느 법에나 통해야 한다.
- 무엇을 하지 말라고만 하지 말고 **무엇을 하라고** 말해라.
- 앞의 지시문과 다른 각도로 말해라. 같은 말을 다시 하면 같은 값이 나온다.

고친 지시문만 출력한다. 따옴표도 머리말도 쓰지 마라."""


def _call(prompt: str) -> str:
    out = subprocess.run([CLAUDE, "-p", prompt], capture_output=True, text=True,
                         timeout=180)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:200] or "claude -p 실패")
    return out.stdout.strip()


def _clean(text: str) -> str:
    """되받은 것을 그대로 싣지 않는다 -- 머리말·코드펜스·따옴표·여러 줄을 걷어낸다."""
    t = (text or "").strip()
    if "```" in t:
        parts = t.split("```")
        t = max(parts[1::2] or parts, key=len).strip()
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    lines = [l for l in lines if not (len(l) < 30 and l.endswith(":"))]
    t = " ".join(lines)
    if len(t) > 1 and t[0] in "\"'“‘" and t[-1] in "\"'”’":
        t = t[1:-1].strip()
    return t


# ---------------------------------------------------------------- 한 바퀴

def _pending():
    """아직 심판 안 한 고침 하나. 이미 결론이 붙은 것은 다시 안 본다."""
    tries, done = [], set()
    for i, r in enumerate(rows()):
        if r["무엇"] == "고침":
            tries.append((i, r))
        elif r.get("대상") is not None:
            done.add(r["대상"])
    for i, r in reversed(tries):
        if i not in done:
            return dict(r, _row=i)
    return None


def plan(targets) -> int:
    s = measure(targets)
    print(table(s))
    skip = cooling()
    if skip:
        print(f"쉬는 규칙: {', '.join(sorted(skip))}")
    rule, gap = worst(s, skip)
    if not rule:
        print("\n고칠 것이 없다 -- 관문에 걸리는 것이 없다.")
        return 0
    print(f"\n다음에 고칠 규칙: **{rule}** · 거리 {gap:.3f} · 총점 {s['total']:.3f}")
    return 0


def attempt(targets, dry: bool = False) -> int:
    s = measure(targets)
    rule, gap = worst(s)
    if not rule:
        print("고칠 것이 없다.")
        return 0
    d = read_directives()
    spec = d["rules"].get(rule)
    if spec is None:
        print(f"{rule} 에 대한 지시문이 directives.json 에 없다. 먼저 넣어라.",
              file=sys.stderr)
        return 1
    p = ask_prompt(rule, s, spec.get("지시", "(아직 없다)"), spec.get("aim", ""))
    if dry:
        print(p)
        return 0
    new = _clean(_call(p))
    if not new or len(new) > MAX_LEN * 2:
        print(f"되받은 것이 쓸 수 없다({len(new)}자). 그대로 둔다.", file=sys.stderr)
        return 1
    was = spec.get("지시", "")
    d["rules"][rule]["지시"] = new
    write_directives(d)
    note({"때": time.strftime("%m-%d %H:%M"), "무엇": "고침", "축": rule,
          "전": was, "후": new, "점수(전)": s["total"], "거리(전)": gap,
          "지문(전)": fingerprint(targets)})
    print(f"[{rule}] 고쳐 넣었다. 총점 {s['total']:.3f} · 거리 {gap:.3f} 에서 출발한다.\n"
          f"\n{new}\n\n**이제 생성기를 다시 돌리고** `law/tuner.py keep` 로 견줘라.")
    return 0


def keep(targets) -> int:
    """다시 생성한 뒤 부른다. 나아졌으면 채택, 아니면 되돌린다."""
    last = _pending()
    if not last:
        print("심판할 고침이 없다(이미 다 결론 났다).")
        return 0
    now_fp = fingerprint(targets)
    if last.get("지문(전)") == now_fp:
        print("**재생성이 없었다.** 지시문을 고쳐도 산출물이 그대로면 점수가 같을 수밖에 "
              "없고, 같은 점수는 되돌림이라 무엇을 써도 되돌아간다. 생성기를 돌린 뒤에 "
              "다시 불러라.", file=sys.stderr)
        return 1
    s = measure(targets)
    was, gap_was = last["점수(전)"], last.get("거리(전)")
    gap_now = (s["axes"].get(last["축"]) or {}).get("gap", 0.0)
    total = s["total"]
    # **판정은 그 규칙의 거리로 한다.** 총점만 보면 규칙 하나를 고친 효과가 나머지
    # 열일곱 규칙의 흔들림에 묻힌다. 총점은 지킴목으로만 쓴다 -- 하나를 잡자고 전체가
    # 나빠지면 안 받는다.
    better = (gap_now < gap_was - 1e-9) and (total <= was + 1e-9) \
        if gap_was is not None else total < was - 1e-9
    d = read_directives()
    if not better:
        d["rules"][last["축"]]["지시"] = last["전"]
        write_directives(d)
    note({"때": time.strftime("%m-%d %H:%M"), "무엇": "채택" if better else "되돌림",
          "축": last["축"], "대상": last["_row"], "점수(전)": was, "점수(후)": total,
          "거리(전)": gap_was, "거리(후)": gap_now, "지문(후)": now_fp})
    if better:
        BEST.write_text(json.dumps({"총점": total, "rules": d["rules"]},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"채택. {last['축']} 거리 {gap_was:.3f} -> {gap_now:.3f} "
              f"· 총점 {was:.3f} -> {total:.3f}")
    else:
        print(f"되돌렸다. {last['축']} 거리 {gap_was:.3f} -> {gap_now:.3f} "
              f"· 총점 {was:.3f} -> {total:.3f} (나아지지 않았다)")
    return 0


def show_log() -> int:
    for r in rows():
        if r["무엇"] == "고침":
            print(f"{r['때']}  고침  {r['축']}  (총점 {r['점수(전)']:.3f} · "
                  f"거리 {r.get('거리(전)', 0):.3f})")
            print(f"    전: {r['전'][:70]}")
            print(f"    후: {r['후'][:70]}")
        else:
            print(f"{r['때']}  {r['무엇']}  {r['축']}  "
                  f"{r['점수(전)']:.3f} -> {r['점수(후)']:.3f}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="법 지시문을 고치고 관문 점수로 채택한다")
    ap.add_argument("cmd", choices=["plan", "try", "keep", "log", "block"])
    ap.add_argument("targets", nargs="*", default=list(DEFAULT_TARGETS))
    ap.add_argument("--dry", action="store_true", help="claude 에게 줄 것만 찍는다")
    a = ap.parse_args(argv)
    targets = a.targets or list(DEFAULT_TARGETS)
    if a.cmd == "log":
        return show_log()
    if a.cmd == "block":
        print(block(measure(targets)))
        return 0
    if a.cmd == "plan":
        return plan(targets)
    if a.cmd == "try":
        return attempt(targets, a.dry)
    return keep(targets)


if __name__ == "__main__":
    raise SystemExit(main())
