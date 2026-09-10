"""**사건 연구 -- "그 뉴스가 뜨면 며칠 뒤에 얼마였나".** 이 저장소가 메인이라고 부른 자리.

    python3 coin/event.py --재기 --자산 BTC
    python3 coin/event.py --재기 --자산 BTC --유형 규제금지 --지평 1,3,7,14,30
    python3 coin/event.py --보기                     원장에 무엇이 들었나

## 여기서 나가는 것은 수 하나가 아니다

    관측중앙   그 사건들 뒤 지평일 수익률의 중앙값
    널중앙     **아무 날이나 같은 자로 잰 것** (null.py)
    초과       관측 - 널.  <- **보고하는 수는 이것이다**
    p          널이 관측만큼 나온 비율
    n / 유효n  표본 · 겹치지 않게 센 표본
    연도별     해마다 따로. 부호가 갈리면 뭉친 값은 뜻이 없다
    불안정     D0 를 '최초' 대신 '주류' 로 잡으면 부호가 뒤집히는가
    미검증     왜 못 쟀는지. **미검증은 통과가 아니다**

중앙값을 머리에 쓰는 까닭: 암호화폐 수익률은 꼬리가 두껍다. +180% 하루 하나가 평균을
통째로 끌고 간다. 평균도 같이 적되 **머리에 세우지 않는다.**

## 왜 LSTM 이 아닌가 -- 사용자가 먼저 그렇게 말했고, 그 판단이 맞다

값으로 값을 맞히는 모형은 여기서 세 가지를 다 못 준다.

    되짚기   왜 그 수가 나왔는지 못 말한다. 관문이 대조할 것이 없다
    표본     사건 유형별 n 이 수십인데 시퀀스 모형은 수천 표본을 먹는다
    기저율   맞춘 것처럼 보이는 것의 대부분이 **추세**다. 널이 없으면 안 갈린다

사건 연구는 셋 다 준다. 잰 값마다 날짜 목록이 붙어 있어 **손으로 다시 셀 수 있고**
(`gate.py` C002 가 실제로 그렇게 한다), 표본을 세어 밝히고, 널이 추세를 걷어낸다.

## 조용히 틀리는 길 네 개, 그리고 각각을 어디서 막나

    미리보기       D0 를 사건보다 앞에 잡는 것        price.진입일 (유예 2시간)
    영어만 봄      D0 가 몇 시간 늦는 것              news.뭉치기 (최초 보도)
    기저율 빠짐    추세를 신호로 읽는 것              null.널 (이동 순열)
    여러 번 재기   325번 재고 걸린 것만 말하는 것      null.보정 (BH) + 시험수 기록
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import null as NU                                           # noqa: E402
from coin import price as PR                                          # noqa: E402
from coin import tag as TG                                            # noqa: E402
from coin.price import _때                                            # noqa: E402

지평기본 = (1, 3, 7, 14, 30)
최소표본기본 = 8


def 사건날들(계열, 사건들: list, 유형: str, 자산: str, 기준: str = "최초",
             유예: float = PR.유예기본, 세기몫: float = 0.0) -> list:
    """사건 -> D0 목록. **같은 날은 한 번만 센다** -- 안 그러면 하루가 열 번 들어간다.

    ## 세기몫 -- 흔한 뉴스와 진짜 사건을 가른다

    실측: 규제금지 뉴스가 3000일 중 600일에 흩어져 있으면 뭉쳐도 사건이 533개다.
    그러면 "규제금지 뒤 D+7" 은 사실상 "규제 뉴스가 있던 아무 날 뒤 D+7" 이 되고,
    사건 연구가 '그 유형 뉴스 있는 날 vs 없는 날' 로 뭉개진다 -- n 이 595까지 부풀고
    초과가 죄다 0 근처가 된다.

    사용자가 처음에 말한 "특정한 뉴스" 는 흔한 규제 뉴스가 아니라 **큰 사건**이다.
    그것을 글수·나라수로 가른다 -- 문턱을 안 박고 **그 유형 자기 분포의 상위 몫**만
    (regime·scenario 와 같은 자). 세기몫 0 이면 다 쓴다(옛 동작).
    """
    묶 = [e for e in 사건들
          if e.get("유형") == 유형 and e.get("자산") == 자산]
    if 세기몫 > 0 and len(묶) >= 20:
        def 세기(e):
            return (e.get("글수", 1), e.get("나라수", 1))
        묶.sort(key=세기, reverse=True)
        묶 = 묶[:max(8, int(len(묶) * 세기몫))]
    본 = {}
    for e in 묶:
        d = 계열.진입일(e.get(기준) or e.get("최초") or "", 유예)
        if d and d not in 본:
            본[d] = e
    return sorted(본)


def 재기(계열, 사건들: list, 유형: str, 자산: str, 지평: int,
         기준: str = "최초", 판수: int = 2000, 씨: int = 20260909,
         최소표본: int = 최소표본기본, 유예: float = PR.유예기본,
         널꼴: str = "이동", 세기몫: float = 0.0) -> dict:
    D0들 = 사건날들(계열, 사건들, 유형, 자산, 기준, 유예, 세기몫)
    쓴날 = [d for d in D0들 if 계열.수익(d, 지평) is not None]   # 못 세는 것은 **버린다**
    r = [계열.수익(d, 지평) for d in 쓴날]
    관측 = NU.중앙(r)
    널 = NU.널(계열, 쓴날, 지평, 판수, 씨, 널꼴)
    널중 = NU.중앙(널["판"])
    p = NU.p값(관측, 널["판"])
    유효 = NU.유효표본(쓴날, 지평, 계열.차례)

    해 = {}
    for d, v in zip(쓴날, r):
        해.setdefault(d[:4], []).append(v)
    연도별 = {y: {"n": len(vs), "중앙": NU.중앙(vs)} for y, vs in sorted(해.items())}
    부호들 = {(1 if v["중앙"] > 0 else -1) for v in 연도별.values() if v["n"] >= 3}
    나라 = {}
    for e in 사건들:
        if e.get("유형") == 유형 and e.get("자산") == 자산:
            for c in (e.get("나라들") or []):
                나라[c] = 나라.get(c, 0) + 1

    잰것 = {
        "유형": 유형, "자산": 자산, "지평": 지평, "기준": 기준,
        "n": len(쓴날), "유효n": 유효, "버린것": len(D0들) - len(쓴날),
        "관측중앙": 관측, "관측평균": (sum(r) / len(r) if r else float("nan")),
        "승률": NU.승률(r),
        "널중앙": 널중, "널구간": NU.구간(널["판"]), "널꼴": 널["꼴"], "널판수": 널["판수"],
        "초과": (관측 - 널중) if (관측 == 관측 and 널중 == 널중) else float("nan"),
        "p상향": p["상향"], "p양측": p["양측"],
        "연도별": 연도별, "부호일관": (len(부호들) <= 1),
        "나라": 나라, "나라수": len(나라),
        "날들": 쓴날,                       # **다시 셀 수 있게** 남긴다 (C002 가 쓴다)
        "수익들": r,                         # 그 날들의 실제 수익률. scenario.py 가 쓴다
        "씨": 씨, "유예": 유예, "최소표본": 최소표본,
    }
    잰것["미검증"], 잰것["왜"] = _미검증(잰것)
    return 잰것


def _미검증(r: dict) -> tuple:
    if r["n"] < r["최소표본"]:
        return True, f"표본이 {r['n']}개다 (최소 {r['최소표본']})"
    if r["유효n"] < r["최소표본"]:
        return True, f"겹치지 않는 표본이 {r['유효n']}개다 (n={r['n']} 은 창이 겹친 것)"
    if not r["널판수"]:
        return True, "널을 못 세웠다"
    if r["관측중앙"] != r["관측중앙"]:
        return True, "수익률을 하나도 못 셌다"
    return False, ""


def 흔들기(계열, 사건들, 유형, 자산, 지평, 세기몫: float = 0.0, **kw) -> dict:
    """**같은 것을 두 기준으로 잰다.** 부호가 갈리면 그 잰 값은 못 믿는다.

    영어 기사 시각으로 잡으나 원문 시각으로 잡으나 같은 답이 나와야 그 답이 사건에서
    온 것이다. 갈리면 우리가 잰 것은 사건이 아니라 **보도 시차**다.
    """
    a = 재기(계열, 사건들, 유형, 자산, 지평, 기준="최초", 세기몫=세기몫, **kw)
    b = 재기(계열, 사건들, 유형, 자산, 지평, 기준="주류", 세기몫=세기몫, **kw)
    부호 = lambda v: 0 if (v != v or v == 0) else (1 if v > 0 else -1)      # noqa: E731
    a["주류초과"] = b["초과"]
    a["불안정"] = (부호(a["초과"]) != 부호(b["초과"]))
    if a["불안정"] and not a["미검증"]:
        a["미검증"], a["왜"] = True, (
            f"D0 를 최초보도 대신 주류보도로 잡으면 부호가 뒤집힌다 "
            f"({a['초과']*100:+.2f}%p -> {b['초과']*100:+.2f}%p) -- "
            "이것은 사건이 아니라 보도 시차를 잰 것이다")
    return a


def 전부(계열들: dict, 사건들: list, 지평들=지평기본, 유형들=None, 자산들=None,
         판수: int = 2000, 씨: int = 20260909, 최소표본: int = 최소표본기본,
         q: float = 0.10, 흔들: bool = True, 세기몫: float = 0.10) -> list:
    """**모든 (유형 x 자산 x 지평) 을 재고 다중비교를 보정한다.**

    걸린 것만 골라 재는 것이 아니라 **전부 재고 몇 번 쟀는지를 적는다.** 그 수가
    없으면 어떤 p 도 뜻이 없다.
    """
    유형들 = 유형들 or TG.유형들
    out = []
    for 자산, 계열 in 계열들.items():
        if not len(계열):
            continue
        for 유형 in 유형들:
            for h in 지평들:
                f = 흔들기 if 흔들 else 재기
                out.append(f(계열, 사건들, 유형, 자산, h,
                             판수=판수, 씨=씨, 최소표본=최소표본, 세기몫=세기몫))
    NU.보정([r for r in out if not r["미검증"]], q=q)
    for r in out:                                    # 미검증에도 시험수는 적는다
        r.setdefault("시험수", sum(1 for x in out if not x["미검증"]))
        r.setdefault("살아남음", False)
        r.setdefault("문턱", 0.0)
    return out


def 줄(r: dict) -> str:
    if r["미검증"]:
        return (f"  {r['유형']:<12} {r['자산']:<4} D+{r['지평']:<3} "
                f"n={r['n']:<4} **미검증** -- {r['왜']}")
    별 = "*" if r.get("살아남음") else " "
    return (f"  {r['유형']:<12} {r['자산']:<4} D+{r['지평']:<3} "
            f"n={r['n']:<3}(유효{r['유효n']:<3}) "
            f"관측 {r['관측중앙']*100:+6.2f}%  널 {r['널중앙']*100:+6.2f}%  "
            f"**초과 {r['초과']*100:+6.2f}%p**  p={r['p양측']:.3f}{별} "
            f"승률 {r['승률']*100:4.0f}%  나라 {r['나라수']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--재기", action="store_true")
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--유형", default="")
    ap.add_argument("--지평", default="1,3,7,14,30")
    ap.add_argument("--판수", type=int, default=2000)
    ap.add_argument("--최소표본", type=int, default=최소표본기본)
    ap.add_argument("--사건", default="")
    ap.add_argument("--저장", default="")
    ap.add_argument("--보기", action="store_true")
    a = ap.parse_args(argv)

    from coin import ledger as LG
    if a.보기:
        원장 = LG.불러오기()
        if not 원장.get("잰것"):
            print("원장이 비었다 -- python3 coin/event.py --재기", file=sys.stderr)
            return 3
        for r in LG.쓸만한것(원장):
            print(줄(r))
        print(f"\n잰것 {len(원장['잰것'])}개 · 쓸만한 것 {len(LG.쓸만한것(원장))}개")
        return 0

    if not a.재기:
        ap.print_help()
        return 0

    사건p = Path(a.사건) if a.사건 else Path(__file__).resolve().parent / "corpus/events.json"
    if not 사건p.exists():
        print(f"사건 원장이 없다: {사건p}\n  python3 coin/news.py --과거 --부터 2017-01-01"
              "\n  python3 coin/news.py --뭉치기", file=sys.stderr)
        return 3
    사건들 = json.loads(사건p.read_text(encoding="utf-8")).get("사건", [])
    자산들 = [x.strip() for x in a.자산.split(",") if x.strip()]
    계열들 = {}
    for x in 자산들:
        원 = PR.불러오기(x)
        if not 원:
            print(f"가격 원장이 없다: {x} -- python3 coin/price.py --받기 {x}", file=sys.stderr)
            return 3
        계열들[x] = PR.계열(원)
    지평들 = tuple(int(v) for v in a.지평.split(",") if v.strip())
    유형들 = tuple(v.strip() for v in a.유형.split(",") if v.strip()) or None

    잰것 = 전부(계열들, 사건들, 지평들, 유형들, 판수=a.판수, 최소표본=a.최소표본)
    for r in 잰것:
        print(줄(r))
    p = LG.저장({"잰것": 잰것, "사건수": len(사건들)}, a.저장 or None)
    산것 = [r for r in 잰것 if not r["미검증"]]
    print(f"\n{len(잰것)}번 쟀다 · 쓸만한 것 {len(산것)}개 · "
          f"BH 를 넘은 것 {sum(1 for r in 산것 if r['살아남음'])}개 -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
