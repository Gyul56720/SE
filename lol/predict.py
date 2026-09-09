"""**두 팀의 승률.** 원장이 못 받치면 **숫자를 안 낸다.**

    python3 lol/predict.py T1 HLE
    python3 lol/predict.py T1 "Hanwha Life Esports" --세트 5
    python3 lol/predict.py --팀                        # 원장에 있는 이름 목록

    끝값 0  숫자를 냈다        3  미검증 -- 못 냈다

## 이 파일이 하는 일의 절반은 **거절**이다

공개 채널 에이전트가 T1-HLE 승률을 물었을 때 한 일이 이것이었다(실측 2026-09-09):
도구를 한 번도 안 써 보고 "수집 제약으로 불가" 라고 답했다. 그런데 **정반대 실패가
더 흔하고 더 나쁘다** -- 아무 데이터 없이 "55% 대 45%" 라고 답하는 것. 화면에서
지어낸 55% 와 계산한 55% 는 똑같이 생겼다.

그래서 여기서는 숫자를 내는 조건을 코드가 쥔다:

    원장에 두 팀이 다 있는가          없으면 미검증 (이름 후보를 대신 보여 준다)
    각 팀이 몸풀기 경기를 치렀는가    아니면 미검증 (1500 에서 안 움직인 레이팅이다)
    원장이 낡지 않았는가              낡았으면 **며칠 낡았는지 적고** 낸다
    이 모델이 기준선을 이기는가       못 이기면 그렇게 **같이 적는다**

마지막 줄이 `law/exam.py` 의 "두 수를 나란히 적는다" 다. 승률만 적고 그 승률의
성적을 안 적으면, 읽는 사람은 검사받지 않은 숫자를 검사받은 것으로 읽는다.

## 이것은 도박 도구가 아니다

Elo 는 **원장에 적힌 승패만** 본다. 로스터 교체 · 부상 · 패치 · 밴픽 · 대회 중요도를
하나도 모른다. 화면이 그 목록을 매번 같이 찍는 이유다 -- 모델이 무엇을 안 보는지
모르면 숫자를 과신하게 된다.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lol import corpus as CP                                       # noqa: E402
from lol import elo as EL                                          # noqa: E402
from lol import score as SC                                        # noqa: E402

MIN_GAMES = 5        # 이보다 적게 치른 팀은 레이팅이 아직 1500 근처다
STALE_DAYS = 21      # 이보다 낡은 원장은 낡았다고 적는다

# 모델이 **안 보는 것**. 화면에 매번 같이 찍는다.
BLIND = ("로스터 교체 · 대리 출전", "선수 부상 · 컨디션", "패치 변화",
         "밴픽 상성", "대회 중요도(진출 확정 여부)", "다전제 안에서의 밴픽 적응")


def _days_old(last: str) -> int | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(last[:19] if len(last) >= 19 else last[:10], fmt)
            return (datetime.now(timezone.utc).replace(tzinfo=None) - d).days
        except ValueError:
            continue
    return None


def matchup(c, a: str, b: str, k: float = EL.K) -> dict:
    """(A 가 블루일 때 · A 가 레드일 때 · 진영 모름) 세 승률.

    **진영을 모르면 세 개를 다 준다.** 하나로 뭉개면 그 하나가 어느 가정의 값인지
    화면에서 사라진다 -- 진영 이점은 잰 값이고, 잰 값은 어디에 쓰였는지 보여야 한다.
    """
    r, _, bias = EL.walk(c.games, k=k)
    played = c.teams()
    ra, rb = r.get(a, EL.BASE), r.get(b, EL.BASE)
    return {
        "a": a, "b": b, "ra": ra, "rb": rb,
        "na": played.get(a, 0), "nb": played.get(b, 0), "진영이점": bias,
        "a_블루": EL.expect(ra + bias, rb),
        "a_레드": EL.expect(ra, rb + bias),
        "진영모름": EL.expect(ra, rb),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="두 팀의 승률 (LLM 호출 0회)")
    ap.add_argument("a", nargs="?", help="팀 A")
    ap.add_argument("b", nargs="?", help="팀 B")
    ap.add_argument("--경로", dest="path", default=str(CP.CORPUS_DIR))
    ap.add_argument("--세트", dest="bo", type=int, default=1, help="다전제 (1·3·5)")
    ap.add_argument("--K", dest="k", type=float, default=EL.K)
    ap.add_argument("--팀", dest="list_teams", action="store_true",
                    help="원장에 있는 팀 이름을 그대로 보여 준다")
    a = ap.parse_args(argv)

    c = CP.load(a.path)
    if not c.games:
        print("**미검증** -- 원장이 비어 있어 승률을 낼 수 없다.")
        print(f"  경로: {a.path}")
        print("  python3 lol/fetch.py --대회 'LCK/2026 Season' 로 먼저 받아라.")
        print("  원장 없이 숫자를 지어내지 않는다 -- 그것이 이 파일이 있는 이유다.")
        return 3

    if a.list_teams or not (a.a and a.b):
        print(f"원장: 경기 {len(c)}개 · {c.first_date[:10]} ~ {c.last_date[:10]}")
        for t, n in sorted(c.teams().items(), key=lambda kv: -kv[1]):
            print(f"  {n:>4}경기  {t}")
        return 0 if a.list_teams else 3

    # ── 이름 -- 못 찾거나 여럿이면 **고르지 않는다** ──────────────────
    bad = False
    names = []
    for want in (a.a, a.b):
        got, cands = c.resolve(want)
        if got is None:
            bad = True
            print(f"**미검증** -- 원장에서 {want!r} 를 하나로 못 좁혔다.")
            if cands:
                print(f"  후보: {', '.join(cands[:8])}")
                print("  이름을 그대로 적어서 다시 불러라. 임의로 고르지 않는다 -- "
                      "다른 팀의 승률을 내놓는 것이기 때문이다.")
            else:
                print("  후보가 없다. `--팀` 으로 원장에 있는 이름을 보라.")
        names.append(got)
    if bad:
        return 3
    A, B = names

    m = matchup(c, A, B, k=a.k)
    if m["na"] < MIN_GAMES or m["nb"] < MIN_GAMES:
        print(f"**미검증** -- 원장의 경기 수가 모자란다 "
              f"({A} {m['na']}경기 · {B} {m['nb']}경기, 최소 {MIN_GAMES}).")
        print("  레이팅이 아직 시작값(1500)에서 거의 안 움직였다. 그 상태의 승률은 "
              "원장이 아니라 시작값이 낸 숫자다.")
        return 3

    s = SC.backtest(c.games, k=a.k)
    old = _days_old(c.last_date)

    print(f"{A}  {m['ra']:.0f}  ({m['na']}경기)")
    print(f"{B}  {m['rb']:.0f}  ({m['nb']}경기)")
    print(f"원장: 경기 {len(c)}개 · 마지막 {c.last_date[:10]}"
          + (f" (**{old}일 낡았다**)" if old is not None and old > STALE_DAYS else ""))
    print()
    print(f"  {A} 가 블루     {m['a_블루']:.1%}")
    print(f"  {A} 가 레드     {m['a_레드']:.1%}")
    print(f"  진영 모름       {m['진영모름']:.1%}   (잰 진영 이점 {m['진영이점']:+.1f} Elo)")
    if a.bo > 1:
        p = m["진영모름"]
        print(f"  Bo{a.bo} 시리즈    {EL.series(p, a.bo):.1%}   "
              f"(세트가 서로 독립이라고 보고 센 값이다 -- 실제로는 아니다)")
    print()

    # **승률과 그 승률의 성적을 나란히 적는다.** 하나만 적으면 검사받지 않은 숫자를
    # 검사받은 것으로 읽는다 -- law/exam.py 가 정답률과 위반 수를 같이 적는 그 자리다.
    if s.get("n"):
        base = min(s["기준_반반"], s["기준_기저율"])
        verdict = ("기준선을 이긴다" if s["브라이어"] < base else
                   "**기준선을 못 이긴다 -- 위 숫자를 믿지 마라**")
        print(f"  이 모델의 성적: 브라이어 {s['브라이어']:.4f} · 기준선 {base:.4f} "
              f"· 정확도 {s['정확도']:.3f} ({s['n']}경기 백테스트) -- {verdict}")
    else:
        print("  이 모델의 성적: **아직 못 쟀다** (채점할 경기가 모자란다). "
              "성적을 모르는 승률이다.")
    print(f"  모델이 안 보는 것: {' · '.join(BLIND)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
