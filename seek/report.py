r"""**원장을 안 옮기고 결과만 옮긴다.** 호출 0회. 파일 하나를 남긴다.

원장(`seek/ledger.json`)은 무시 목록에 있다 -- VM 이 계속 쓰는 파일이라 추적하면
배포의 `git pull` 이 매번 충돌한다(`compression/ledger.json` 과 같은 부류다).
그렇다고 화면 출력을 사람이 옮겨 적으면 **옮기는 사이에 잃는다.**

    실측 2026-09-09, 세 번 연달아: 표를 요약해 보내니 `무작위` 열이 사라졌다.
    그 열이 없으면 도약률 100% 가 연산자의 공인지 꼴 바꾸기의 그림자인지 알 수가
    없는데, 그 구분을 하려고 대조군을 만든 것이었다. 한 번은 더 물어보면 되지만
    세 번은 절차의 결손이다.

그래서 **파생물을 남긴다.** `seek/report.md` 는 감사 · 대조군 · 셈을 한 파일에
담고, 원장과 달리 이 명령을 칠 때만 쓰인다 -- 계속 쓰이지 않으므로 충돌하지 않는다.

    python3 seek/report.py            # 화면에 찍는다
    python3 seek/report.py --쓰기      # seek/report.md 에 남긴다. 그것을 커밋한다
"""
from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import audit as AU                                  # noqa: E402
from seek import control as CT                                # noqa: E402
from seek import problem as PR                                # noqa: E402
from seek import reach as RE                                  # noqa: E402
from seek import tally as TA                                  # noqa: E402

여기 = Path(__file__).resolve().parent
나갈곳 = 여기 / "report.md"


def 잡아서(fn, *a, **kw) -> str:
    out = io.StringIO()
    with redirect_stdout(out):
        try:
            fn(*a, **kw)
        except Exception as e:                                # noqa: BLE001
            print(f"(못 돌렸다: {type(e).__name__}: {e})")
    return out.getvalue().rstrip()


def 도약목록(led: dict) -> str:
    """**도약이라고 판정된 것의 물음을 그대로 적는다.**

    숫자만 남기면 22개가 무엇인지 아무도 못 본다. 이 파이프라인이 무엇을 낳았는지는
    결국 이 문장들이다.
    """
    줄 = []
    for kid in led.get("problems") or []:
        par_id = (kid.get("계보") or {}).get("부모")
        if not par_id or par_id == "-":
            continue
        par = PR.get(led, par_id)
        if par is None:
            continue
        r = RE.pair(par, kid)
        if r.get("판정") != "도약":
            continue
        줄.append(f"### {par['id']} -> {kid['id']}  ({(kid.get('계보') or {}).get('연산자')})\n\n"
                  f"- 부모: {str(par.get('물음'))}\n"
                  f"- 자식: {str(kid.get('물음'))}\n")
    return "\n".join(줄) if 줄 else "(도약으로 판정된 걸음이 없다)"


def build(led: dict, seed: int = 1, n: int = 200) -> str:
    ps = led.get("problems") or []
    풀린 = sum(1 for p in ps if p.get("답") is not None)
    경고 = ""
    if 풀린 < len(ps):
        # **덜 푼 원장으로는 도약을 못 잰다.** 보존은 부모의 답을, 확장은 자식의
        # 답을 필요로 한다. 그것을 머리에 안 적으면 아래의 0%들을 "연산자가 아무
        # 일도 안 했다" 로 읽는다 -- 실제로는 아직 아무것도 안 쟀을 뿐이다.
        경고 = (f"\n> **아직 {len(ps) - 풀린}개가 안 풀렸다.** 도약은 부모와 자식의"
                " 답이 **둘 다** 있어야 잰다.\n> 아래 판정의 0%는 '연산자가 아무 일도"
                " 안 했다' 가 아니라 '잴 데가 없다' 일 수 있다.\n"
                "> `python3 seek/sweep.py` 를 먼저 돌려라.\n")
    부 = [f"# seek 결과\n",
          f"문제 {len(ps)}개 · 답이 있는 것 {풀린}개",
          경고,
          "**이 파일은 만들어진 것이다.** 고치지 마라 --"
          " `python3 seek/report.py --쓰기` 가 덮어쓴다.",
          "원장(`seek/ledger.json`)은 무시 목록에 있다. 이것이 그 파생물이다.\n",
          "## 감사 -- 판정기가 무엇을 거르나\n",
          "```\n" + 잡아서(AU.show, led, n) + "\n```\n",
          "## 대조군 -- 그 자가 계보를 재기는 하나\n",
          "```\n" + 잡아서(CT.show, led, seed) + "\n```\n",
          "## 셈 -- 어느 연산자가 냈나\n",
          "```\n" + 잡아서(TA.show, led, seed) + "\n```\n",
          "## 도약으로 판정된 걸음\n",
          도약목록(led) + "\n"]
    return "\n".join(부)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--쓰기", dest="write", action="store_true")
    ap.add_argument("--씨", dest="seed", type=int, default=1)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)
    글 = build(PR.load(a.path or None), a.seed, a.n)
    if a.write:
        나갈곳.write_text(글, encoding="utf-8")
        print(f"{나갈곳} 에 {len(글):,}자를 적었다. 이것을 커밋하면 된다:\n"
              f"  git add seek/report.md && git commit -m 'seek 결과' "
              f"&& git push -u origin main")
        return 0
    print(글)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
