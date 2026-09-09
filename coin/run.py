"""**한 명령.** 물음 하나를 받아 사람에게 돌려줄 것까지 간다.

    python3 coin/run.py --물음 "비트코인 시장 분석해줘"
    python3 coin/run.py --물음 "SOL -12.4% 왜 이래?" --바퀴 3
    python3 coin/run.py --물음 "..." --재기        사건 연구를 다시 돌리고 나서
    python3 coin/run.py --채우기                   원장을 채운다 (망 필요, 오래 걸림)

끝값이 **다음에 무엇을 할지**다.

    0  냈다
    1  바퀴를 다 돌았는데 어긋난 자리가 남았다 -- **안 내보냈다**
    2  트리거에 안 걸렸다 (암호화폐 물음이 아니다)
    3  못 돌렸다 (원장이 비었다 · 키가 없다 · 망이 막혔다)

## 왜 3 과 1 을 가르나

3 은 **아직 못 재 본 것**이고 1 은 **재 봤는데 답이 원장과 어긋난 것**이다.
다음에 할 일이 서로 다르다 -- 앞은 원장을 채우는 일이고 뒤는 답을 고치는 일이다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import event as EV                                          # noqa: E402
from coin import flow as FL                                           # noqa: E402
from coin import ledger as LG                                         # noqa: E402
from coin import loop as LP                                           # noqa: E402
from coin import price as PR                                          # noqa: E402
from coin import regime as RG                                         # noqa: E402
from coin import scenario as SC                                       # noqa: E402
from coin import screen as SN                                         # noqa: E402
from coin import situation as ST                                      # noqa: E402

사건길 = Path(__file__).resolve().parent / "corpus/events.json"


def 사건불러오기(경로=None) -> list:
    p = Path(경로) if 경로 else 사건길
    return json.loads(p.read_text(encoding="utf-8")).get("사건", []) if p.exists() else []


def 준비(물음: str, 원장: dict = None, 사건들: list = None, 지평들=(3, 7, 14)) -> dict:
    """원장 · 상황 · 시나리오까지. **모델을 안 부른다** -- 검사에서 이대로 쓴다."""
    원장 = 원장 if 원장 is not None else LG.불러오기()
    사건들 = 사건들 if 사건들 is not None else 사건불러오기()
    상황 = ST.읽기(물음, 사건들)
    자산 = 상황["자산"] or sorted({r["자산"] for r in LG.쓸만한것(원장)}) or ["BTC"]
    계열들 = {}
    for a in 자산:
        원 = PR.불러오기(a)
        if 원:
            계열들[a] = PR.계열(원)
    유형들 = 상황["지금유형"] or None
    뭉치 = []
    for a in 자산:
        c = 계열들.get(a)
        if not c:
            continue
        for r in LG.찾기(원장, "", a):
            if 유형들 and r["유형"] not in 유형들:
                continue
            if r["지평"] not in 지평들:
                continue
            m = SC.뽑기(c, r)
            if m.get("시나리오"):
                뭉치.append(m)
    뭉치.sort(key=lambda m: -max((s["확률"] for s in m["시나리오"]), default=0))
    장세 = {a: RG.장세(c, PR.불러오기(a)) for a, c in 계열들.items()}
    흐름 = FL.상태()
    훑음 = SN.훑기(원장, 계열들, 지평들[min(1, len(지평들) - 1)], 유형들, 흐름)
    return {"원장": 원장, "사건들": 사건들, "상황": 상황, "계열들": 계열들,
            "유형들": 유형들, "시나리오": 뭉치, "장세": 장세, "흐름": 흐름,
            "훑음": 훑음}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--물음", default="")
    ap.add_argument("--바퀴", type=int, default=4)
    ap.add_argument("--지평", default="3,7,14")
    ap.add_argument("--재기", action="store_true")
    ap.add_argument("--채우기", action="store_true")
    ap.add_argument("--상황만", action="store_true", help="모델을 안 부르고 무엇이 잡혔는지만")
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)

    if a.채우기:
        from coin import news as NW
        print("1) 뉴스 -- 여러 나라")
        NW.main(["--과거", "--부터", "2017-01-01"])
        print("2) 뭉치기")
        NW.main(["--뭉치기"])
        print("3) 가격")
        자산들 = sorted({e["자산"] for e in 사건불러오기()}) or ["BTC"]
        for x in 자산들:
            PR.main(["--받기", x])
        print("4) 돈 흐름 (포지션 · 온체인 · 심리)")
        for x in 자산들:
            FL.저장(FL.받기(x))
        흐름사건 = FL.사건화(자산=자산들[0])
        if 흐름사건:
            import json as _j
            p = 사건길
            옛 = _j.loads(p.read_text(encoding="utf-8")) if p.exists() else {"사건": []}
            본 = {(e["유형"], e["자산"], e["최초"]) for e in 옛["사건"]}
            옛["사건"] += [e for e in 흐름사건
                          if (e["유형"], e["자산"], e["최초"]) not in 본]
            옛["사건"].sort(key=lambda e: e["최초"])
            p.write_text(_j.dumps(옛, ensure_ascii=False), encoding="utf-8")
            print(f"   흐름 사건 {len(흐름사건)}개를 뉴스 사건과 **같은 원장에** 넣었다")
        print("5) 사건 연구")
        return EV.main(["--재기", "--자산", ",".join(
            sorted({e["자산"] for e in 사건불러오기()}) or ["BTC"])])

    if a.재기:
        자산 = ",".join(sorted({e["자산"] for e in 사건불러오기()}) or ["BTC"])
        rc = EV.main(["--재기", "--자산", 자산])
        if rc or not a.물음:
            return rc

    if not a.물음:
        ap.print_help()
        return 0

    걸림, 무엇 = ST.걸리나(a.물음)
    if not 걸림:
        print("암호화폐 물음이 아니다 -- 이 파이프라인이 맡지 않는다", file=sys.stderr)
        return 2

    지평들 = tuple(int(v) for v in a.지평.split(",") if v.strip())
    준 = 준비(a.물음, LG.불러오기(a.원장 or None), None, 지평들)
    상황 = 준["상황"]
    print(f"트리거: {', '.join(무엇)}")
    print(f"자산: {', '.join(상황['자산']) or '-'} · 등락률 {상황['등락률'] or '-'} "
          f"· 지금 걸린 유형 {', '.join(상황['지금유형']) or '-'}")
    s = LG.요약(준["원장"])
    print(f"원장: 잰것 {s['잰수']} · 쓸만한 것 {s['쓸만한것']} · BH 통과 {s['살아남음']} "
          f"· 미검증 {s['미검증']} · 시나리오 묶음 {len(준['시나리오'])}")

    if not LG.쓸만한것(준["원장"]):
        print("\n**쓸만한 잰것이 하나도 없다.** 원장부터 채워라:\n"
              "  python3 coin/run.py --채우기", file=sys.stderr)
        return 3

    for g in 준["장세"].values():
        print("\n" + RG.적기(g))
    본흐름 = {k: v for k, v in 준["흐름"].items() if v.get("백분위") == v.get("백분위")}
    if 본흐름:
        print("\n  돈 흐름 (자기 역사의 자리 · **포지션과 지갑을 갈라 적는다**)")
        for k, v in 본흐름.items():
            print(f"    {k:<12} {v['날']} {v['값']:>14.6g}  {v['백분위']*100:5.1f}% 자리")
    else:
        print("\n  돈 흐름: **못 받았다** -- python3 coin/flow.py --받기")
    print("\n" + SN.적기(준["훑음"], 전부=a.상황만))
    if a.상황만:
        for m in 준["시나리오"][:4]:
            print("\n" + SC.적기(m))
        return 0

    from coin import ask as AS
    try:
        부르기 = AS.부르는것()
    except Exception as e:                                            # noqa: BLE001
        print(f"\n못 돌린다: {e}", file=sys.stderr)
        return 3

    끝 = LP.돌리기(a.물음, 준["원장"], 부르기, 준["사건들"], 준["계열들"],
                  준["시나리오"], a.바퀴, 준["유형들"],
                  준["장세"], 준["흐름"], 준["훑음"])
    print("\n" + LP.적기(끝))
    if not 끝.통과:
        return 1
    print("\n" + "=" * 60 + "\n")
    print(끝.답)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
