"""**①재현** -- 이 식이 Strassen 을 품는가. **호출 0회. 판정은 Brent 항등식이 한다.**

    python3 mathdrift/recall.py            # 아직 안 본 것 전부
    python3 mathdrift/recall.py --only S6,S34
    python3 mathdrift/recall.py --show

## 왜 호출이 0회인가

공간이 생성될 때 **해독기와 시금석점을 같이 들고 나온다**(`spread.py` 의 프롬프트가
그것을 받는다). 그래서 판정은 다시 묻는 일이 아니라 **순수 계산**이다 -- 원장에 있는
것을 돌려 보면 끝난다. 85개를 재판정하는 데 쿼터가 한 방울도 안 든다.

## 왜 산문을 버렸나

실측 2026-09-07(85개). 되사상을 산문으로 받았더니 "요네다 매몰을 통해 구체적인 텐서
공간으로 재해석" 같은 것이 통과했다 -- 차 있지만 공허하다. `space.grade` 는 빈 칸만
보므로 이것을 못 거른다. 코드는 **돌려 보면 끝난다.**

## 무엇을 보나

  0. `시금석점` 이 없으면 `부호화`(encode)로 **만든다** -- Strassen 을 그 인코딩으로 옮긴다
  1. `decode(시금석점)` 을 격리해서 돌린다 (`encode.run` -> `_child.py`)
  2. 나온 (U,V,W,lambda) 를 `ExactArithVerifier` 로 정확 검산한다
  3. 시금석점을 흔들어 다시 돌린다. **결과가 같으면 하드코딩이다** --
     해독기가 자기 입력을 안 쓴 것이다

판정: `재현` · `틀림` · `못돎` · `못읽음` · `없음`(해독기나 시금석점이 비었다).
`하드코딩` 은 판정과 별개로 붙는 표다 -- 재현이어도 붙을 수 있고, 그때는 **재현이 아니라
외운 답을 적은 것**이다.

## 통과가 여전히 약한 증거인 이유

흔들기는 "해독기가 입력을 쓰는가" 만 본다. 입력을 쓰면서도 식과 무관한 인코딩일 수
있다(예: 점을 그냥 재배열해 놓고 식은 딴소리). 그래서 이 축은 증명이 아니라 **필요조건
거르개**다 -- 강한 신호는 여전히 `틀림` · `못돎` · `하드코딩` 쪽이다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import encode as EN                                    # noqa: E402
from mathdrift import space as SP                                     # noqa: E402


def one(rec: dict, log=print) -> dict:
    out = EN.check(rec.get("해독") or "", rec.get("시금석점") or None,
                   enc=rec.get("부호화") or "")
    # 만들어 쓴 점은 원장에 적어 둔다 -- 나중에 카드로 볼 수 있어야 한다.
    if out.pop("점만듦", False) and out.get("점"):
        rec.setdefault("시금석점", out["점"])
    out.pop("점", None)
    out["시금석"] = f"strassen b={EN.B} m={EN.M}"
    rec["재현"] = out
    mark = out["판정"] + ("+하드코딩" if out.get("하드코딩") else "")
    log(f"[재현] {rec['id']:<5} {mark:<12} {str(rec.get('식') or '')[:44]}"
        + (f"  -- {out.get('왜','')[:60]}" if out.get("왜") else ""))
    return out


def report(led: dict) -> int:
    seen = [s for s in led["spaces"] if s.get("재현")]
    if not seen:
        print("아직 아무것도 안 봤다. python3 mathdrift/recall.py")
        return 0
    tally, hard = {}, 0
    for s in seen:
        v = s["재현"]["판정"]
        tally[v] = tally.get(v, 0) + 1
        hard += 1 if s["재현"].get("하드코딩") else 0
    print(f"본 공간 {len(seen)}개 -- "
          + " · ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda x: -x[1]))
          + f"  (그중 하드코딩 {hard}개)")
    print()
    for s in sorted(seen, key=lambda r: (r["재현"]["판정"], not r["재현"].get("하드코딩"))):
        r = s["재현"]
        mark = r["판정"] + ("+하드코딩" if r.get("하드코딩") else "")
        print(f"  {s['id']:<5} {mark:<12} {str(s.get('식') or '')[:56]}")
    print("\n**강한 신호는 틀림 · 못돎 · 하드코딩이다** -- 그 식은 Strassen 을 품지 못한다.")
    print("재현은 다음 축으로 갈 자격일 뿐이지 그 식이 쓸모 있다는 뜻이 아니다.")
    print("**없음은 실패가 아니다** -- 코드 칸이 없어서 아직 안 본 것이다. 발산은 그것을 안 벌한다.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="쉼표로 짚어서 (예: S6,S34)")
    ap.add_argument("--n", type=int, default=0, help="앞에서부터 이만큼만")
    ap.add_argument("--again", action="store_true", help="이미 본 것도 다시")
    ap.add_argument("--all", action="store_true",
                    help="코드 칸이 없는 것까지 -- 기본은 검증가능한 것만 본다")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    led = SP.load(a.path or None)
    if a.show:
        return report(led)

    want = [x.strip() for x in a.only.split(",") if x.strip()]
    # **기본은 검증가능한 것만 본다.** 코드 칸이 없는 것은 결함이 아니라 아직 안 본
    # 것이고, 그것들을 "없음" 으로 줄줄이 찍으면 발산이 실패한 것처럼 읽힌다.
    todo = [s for s in led["spaces"]
            if (s["id"] in want if want else True)
            and (a.again or not s.get("재현"))
            and (a.all or want or s.get("등급") == "검증가능")]
    if a.n:
        todo = todo[:a.n]
    if not todo:
        n_all = len(led["spaces"])
        n_ok = sum(1 for s in led["spaces"] if s.get("등급") == "검증가능")
        print(f"볼 것이 없다. 공간 {n_all}개 중 검증가능 {n_ok}개 "
              f"(코드 칸이 있는 것). --all 로 나머지도 볼 수 있고, --again 으로 다시 본다.")
        return 0

    for rec in todo:
        one(rec)
        SP.save(led, a.path or None)
    print()
    return report(led)


if __name__ == "__main__":
    raise SystemExit(main())
