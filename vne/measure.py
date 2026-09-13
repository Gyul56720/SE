"""VNE 측정 자 -- **무엇을 재고, 무엇을 못 재는지**를 한 줄에 같이 적는다.

## 재는 것

    온요청      씨앗이 정한다. 방법이 못 바꾼다 -- **분모를 고정한다**
    받음        배치가 선 요청
    거절        배치가 안 선 요청 (사유별로 나눈다: 노드자원부족 · 링크자원부족 · 경로없음)
    못잼        시한초과 · 오류 · 풀이기 없음. **거절이 아니다**
    수용률      받음 / 온요청
    매출        sum(cpu) + sum(대역)                     -- 요청이 달라는 자원
    비용        sum(cpu) + sum(대역 x 경로 홉수)          -- 실제로 문 자원
    매출비      매출 / 비용. 1 에 가까울수록 길게 안 돌아간다
    초          요청 하나를 배치하는 데 든 벽시계 시간
    LPgap       **여기서는 못 잰다** -- solver 가 없다. 그 자리를 0 으로 안 채운다

## 항등식

    온요청 = 받음 + 거절 + 못잼

이것이 성립해야 분모에서 빠진 수를 숨길 수 없다. 이 저장소가 거짓초록 사냥에서
`잰변형 = Killed + FG + 못잼` 으로 붙들어 둔 것과 같은 꼴이고, 같은 함정 때문이다 --
**수용률은 분모가 줄면 저절로 오른다.** 어려운 요청에서 터지는 방법이 그 요청을 표본에서
떨어뜨리면 수용률이 올라간다. 덜 잰 것이 개선으로 읽힌다.

## 견주는 법

**같은 씨앗·같은 흐름에서** 두 방법을 돌리고 **요청마다 짝지어** 뺀다. 기계 부하가 흐르는
것을 Δ 로 읽지 않게 `perf.py` 의 잣대를 그대로 쓴다 -- 짝차 · 잡음바닥(짝 차이의 MAD) ·
부호검정. 그 셋은 오늘 세 번 틀렸다가 실측으로 고친 것들이다.

    python3 -m vne.measure --재기 탐욕 --씨앗 0 --요청 200
    python3 -m vne.measure --견주기 탐욕 탐욕 --씨앗 0 --요청 200
    python3 -m vne.measure --보고
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vne import embed as EM                                        # noqa: E402
from vne import topo as T                                          # noqa: E402

원장경로 = "vne/측정.jsonl"
기본요청수 = 200
요청시한초 = 30.0                  # 요청 하나가 이걸 넘기면 **못잼**이다. 거절이 아니다


def _저장소() -> Path:
    return Path(__file__).resolve().parent.parent


def _기계() -> dict:
    return {"이름": platform.node(), "코어": os.cpu_count()}


def 한판(방법: str, 씨앗: int = 0, 요청수: int = 기본요청수, 바탕노드수: int = T.바탕노드수,
       꼴: str = "waxman", 시한초: float = 요청시한초, 말하기=None) -> dict:
    """요청 흐름 하나를 통째로 돌린 표본 벡터. **요청마다 한 칸씩 남긴다**(짝 비교의 단위)."""
    말 = 말하기 or (lambda s: None)
    배치기 = EM.방법들.get(방법)
    if 배치기 is None:
        return {"방법": 방법, "못잼": -1, "말": f"모르는 방법 '{방법}' ({', '.join(EM.방법들)})"}
    바탕 = T.바탕망(씨앗=씨앗, 노드수=바탕노드수, 꼴=꼴)
    흐름 = T.요청흐름(씨앗=씨앗, 개수=요청수)
    쓴cpu, 쓴대역 = {}, {}
    살아있는: list = []                                  # (나갈때, 요청, 배치)
    칸: list = []                                        # 요청마다 하나 -- 짝 비교의 단위
    셈 = {"받음": 0, "거절": 0, "못잼": 0}
    사유 = {}
    for 순번, (들어온때, 나갈때, 요청) in enumerate(흐름):
        # **수명이 끝난 것을 먼저 돌려준다.** 안 그러면 뒤로 갈수록 전부 거절이라
        # 수용률이 방법이 아니라 요청 수의 함수가 된다.
        남은것 = []
        for 끝, 옛요청, 옛배치 in 살아있는:
            if 끝 <= 들어온때:
                EM.자원깎기(바탕, 옛요청, 옛배치, 쓴cpu, 쓴대역, 부호=-1)
            else:
                남은것.append((끝, 옛요청, 옛배치))
        살아있는 = 남은것

        t0 = time.perf_counter()
        try:
            d = 배치기(바탕, 요청, 쓴cpu, 쓴대역)
            걸림 = time.perf_counter() - t0
            if 걸림 > 시한초:
                셈["못잼"] += 1
                칸.append({"순번": 순번, "결과": "못잼", "왜": "시한초과", "초": round(걸림, 6)})
                continue
        except Exception as e:                                     # noqa: BLE001
            걸림 = time.perf_counter() - t0
            셈["못잼"] += 1
            칸.append({"순번": 순번, "결과": "못잼", "왜": f"{type(e).__name__}: {e}"[:120],
                      "초": round(걸림, 6)})
            continue

        if d["됐나"]:
            EM.자원깎기(바탕, 요청, d, 쓴cpu, 쓴대역, 부호=1)
            살아있는.append((나갈때, 요청, d))
            셈["받음"] += 1
            칸.append({"순번": 순번, "결과": "받음", "매출": d["매출"], "비용": d["비용"],
                      # **가중비용**은 FF 목적함수와 같은 꼴이다 -- MIP 가 실제로 줄이는 것.
                      # `비용`(홉 수)은 그대로 둔다: 옛 원장이 그 수로 쌓여 있다.
                      "가중비용": d.get("가중비용", EM.가중비용(바탕, 요청, d)),
                      "초": round(걸림, 6)})
        else:
            셈["거절"] += 1
            사유[d["사유"]] = 사유.get(d["사유"], 0) + 1
            칸.append({"순번": 순번, "결과": "거절", "왜": d["사유"], "초": round(걸림, 6)})
        if 순번 % 50 == 49:
            말(f"[vne] {순번 + 1}/{요청수} 받음 {셈['받음']} 거절 {셈['거절']} 못잼 {셈['못잼']}")

    받은칸 = [c for c in 칸 if c["결과"] == "받음"]
    매출 = sum(c["매출"] for c in 받은칸)
    비용 = sum(c["비용"] for c in 받은칸)
    가중 = sum(c.get("가중비용") or 0.0 for c in 받은칸)
    온 = len(흐름)
    return {
        "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "방법": 방법, "씨앗": 씨앗, "꼴": 꼴, "바탕노드수": len(바탕.노드),
        "바탕링크수": len(바탕.링크), "시한초": 시한초, "기계": _기계(),
        # ---- 표본: **수용률보다 먼저 읽을 것들** ----
        "온요청": 온, "받음": 셈["받음"], "거절": 셈["거절"], "못잼": 셈["못잼"],
        "거절사유": 사유,
        # **온요청 = 받음 + 거절 + 못잼** 이 성립해야 분모에서 빠진 수를 숨길 수 없다
        "맞나": 온 == 셈["받음"] + 셈["거절"] + 셈["못잼"],
        "수용률": (round(셈["받음"] / 온, 4) if 온 else None),
        "매출": round(매출, 2), "비용": round(비용, 2),
        "매출비": (round(매출 / 비용, 4) if 비용 else None),
        # FF 목적함수와 같은 자. **받은 요청당**으로도 낸다 -- 합만 보면 많이 받은 쪽이
        # 늘 커 보인다(수용률과 뒤섞인다)
        "가중비용": round(가중, 2),
        "요청당가중비용": (round(가중 / len(받은칸), 4) if 받은칸 else None),
        "초합": round(sum(c["초"] for c in 칸), 4),
        "초중앙값": (round(statistics.median([c["초"] for c in 칸]), 6) if 칸 else None),
        # **못 재는 것을 0 으로 안 채운다**
        "LPgap": None, "LP말": _풀이기말(),
        "칸": 칸,
    }


def _풀이기말() -> str:
    for 이름 in ("scipy", "pulp", "mip", "gurobipy", "highspy"):
        try:
            __import__(이름)
            return f"{이름} 있음 -- LP/MIP 를 잴 수 있다(아직 안 붙였다)"
        except ImportError:
            continue
    return "풀이기가 없다(scipy·pulp·mip·gurobi·highs 전부) -- LP gap 은 **안 쟀다**"


# ------------------------------------------------------------------ 짝지어 견주기
def 짝(앞: dict, 뒤: dict) -> dict:
    """**같은 씨앗·같은 순번의 요청끼리만** 뺀다. 공통 순번이 아니면 안 견준다.

    까닭은 오늘 두 번 겪은 것이다 -- 표본이 다른 둘을 견주면 *덜 잰 쪽*이 이긴다.
    수용률은 분모가 줄면 오른다."""
    if not (앞 and 뒤) or 앞.get("씨앗") != 뒤.get("씨앗"):
        return {"견줄수있나": False, "까닭": ["씨앗이 다르다 -- 다른 인스턴스에서 잰 것이다"]}
    if 앞.get("꼴") != 뒤.get("꼴") or 앞.get("바탕노드수") != 뒤.get("바탕노드수"):
        return {"견줄수있나": False, "까닭": ["바탕망이 다르다"]}
    ㄱ = {c["순번"]: c for c in (앞.get("칸") or [])}
    ㄴ = {c["순번"]: c for c in (뒤.get("칸") or [])}
    공통 = sorted(set(ㄱ) & set(ㄴ))
    if not 공통:
        return {"견줄수있나": False, "까닭": ["같이 잰 요청이 하나도 없다"], "공통": 0}
    # 받음/거절은 요청마다 0/1 -- 짝지어 세면 '어느 요청에서 갈렸나' 까지 보인다
    앞받, 뒤받 = [ㄱ[i]["결과"] == "받음" for i in 공통], [ㄴ[i]["결과"] == "받음" for i in 공통]
    뒤만 = [i for i, a, b in zip(공통, 앞받, 뒤받) if b and not a]
    앞만 = [i for i, a, b in zip(공통, 앞받, 뒤받) if a and not b]
    앞초 = [ㄱ[i]["초"] for i in 공통]
    뒤초 = [ㄴ[i]["초"] for i in 공통]
    import perf                                            # 잣대를 다시 짓지 않는다
    이김, 짝수 = perf.짝이김(앞초, 뒤초)
    return {
        "견줄수있나": True, "공통": len(공통),
        "앞수용": sum(앞받), "뒤수용": sum(뒤받),
        "Δ수용": sum(뒤받) - sum(앞받),
        "뒤만받은요청": 뒤만[:10], "앞만받은요청": 앞만[:10],
        "Δ수용률": round((sum(뒤받) - sum(앞받)) / len(공통), 4),
        "Δ초": perf.짝Δ(앞초, 뒤초), "잡음바닥": perf.잡음바닥(앞초, 뒤초),
        "짝이김": (이김, 짝수), "부호p": perf.부호검정p(이김, 짝수),
        "시간이갈렸나": perf.짝으로갈렸나(앞초, 뒤초),
        "까닭": [],
    }


def 여러씨앗(앞방법: str, 뒤방법: str, 씨앗들, 요청수: int = 기본요청수,
        바탕노드수: int = T.바탕노드수, 꼴: str = "waxman", 말하기=None) -> dict:
    r"""**씨앗 하나는 측정이 아니다.** 씨앗마다 짝지어 재고 그 사이의 흩어짐까지 낸다.

    실측 2026-09-13. `탐욕cpu` vs `탐욕` 을 씨앗 하나로 쟀더니 이렇게 나왔다.

        요청 200 · 씨앗 0  ->  Δ수용률 +0.1100
        요청 500 · 씨앗 0  ->  Δ수용률 +0.0380

    효과가 요청 수에 따라 준 것처럼 보였다. 씨앗 넷으로 다시 재니 아니었다.

        요청 100  중앙값 +0.0850   (씨앗별 +0.050 ~ +0.120)
        요청 200  중앙값 +0.0925   (씨앗별 +0.065 ~ +0.195)
        요청 500  중앙값 +0.0900   (씨앗별 +0.038 ~ +0.166)

    **중앙값은 n 에 거의 안 움직이고 씨앗에 다섯 배로 움직인다.** 그 +0.0380 은 하필
    네 씨앗 가운데 최솟값이었다. 씨앗 하나로 낸 수는 방법의 성질이 아니라 **그 인스턴스의
    성질**이다. 논문에 "수용률이 3.8% 올랐다" 와 "19.5% 올랐다" 를 둘 다 참으로 쓸 수 있다.

    그래서 여기서는 세 가지를 같이 낸다 -- 중앙값 · 최소/최대 · **씨앗 사이 부호검정**."""
    말 = 말하기 or (lambda s: None)
    씨앗들 = list(씨앗들)
    각각, 나쁨 = [], []
    for s in 씨앗들:
        앞 = 한판(앞방법, 씨앗=s, 요청수=요청수, 바탕노드수=바탕노드수, 꼴=꼴)
        뒤 = 한판(뒤방법, 씨앗=s, 요청수=요청수, 바탕노드수=바탕노드수, 꼴=꼴)
        if 앞.get("못잼") == -1 or 뒤.get("못잼") == -1:
            return {"됐나": False, "말": 앞.get("말") or 뒤.get("말")}
        d = 짝(앞, 뒤)
        if not d["견줄수있나"]:
            나쁨.append((s, d["까닭"]))
            continue
        각각.append({"씨앗": s, "Δ수용률": d["Δ수용률"], "Δ수용": d["Δ수용"],
                   "앞수용률": round(앞["수용률"], 4), "뒤수용률": round(뒤["수용률"], 4),
                   "앞매출비": 앞["매출비"], "뒤매출비": 뒤["매출비"], "공통": d["공통"]})
        말(f"[vne] 씨앗 {s}: {앞['수용률']:.3f} -> {뒤['수용률']:.3f} (Δ {d['Δ수용률']:+.4f})")
    if not 각각:
        return {"됐나": False, "말": f"견줄 수 있는 씨앗이 하나도 없다 {나쁨[:2]}"}
    Δ들 = [x["Δ수용률"] for x in 각각]
    import perf
    이김 = sum(1 for d in Δ들 if d > 0)
    비김 = sum(1 for d in Δ들 if d == 0)
    return {
        "됐나": True, "앞": 앞방법, "뒤": 뒤방법, "요청수": 요청수, "씨앗수": len(각각),
        "못견준씨앗": [s for s, _ in 나쁨],
        "중앙값": round(statistics.median(Δ들), 4),
        "최소": round(min(Δ들), 4), "최대": round(max(Δ들), 4),
        # 흩어짐을 평균 대신 MAD 로 -- 씨앗 하나가 튀어도 끌려가지 않는다
        "흩어짐": (round(statistics.median([abs(d - statistics.median(Δ들)) for d in Δ들]), 4)
                if len(Δ들) >= 3 else None),
        "이긴씨앗": 이김, "비긴씨앗": 비김, "진씨앗": len(Δ들) - 이김 - 비김,
        "부호p": perf.부호검정p(이김, len(Δ들) - 비김),
        "몇씨앗이면": perf.몇짝이면(이김, len(Δ들) - 비김),
        "각각": 각각,
    }


def 여러씨앗보고(r: dict) -> str:
    if not r.get("됐나"):
        return "**못 견줬다**: " + str(r.get("말"))
    p = r["부호p"]
    p글 = f"{p:.2%}" if p is not None else "못 잼"
    갈렸나 = p is not None and p <= 0.01
    줄 = [f"{r['앞']} -> {r['뒤']} · 씨앗 {r['씨앗수']}개 · 요청 {r['요청수']}개",
         f"  Δ수용률  중앙값 {r['중앙값']:+.4f}  (최소 {r['최소']:+.4f} ~ 최대 {r['최대']:+.4f}"
         + (f" · 흩어짐 {r['흩어짐']:.4f}" if r["흩어짐"] is not None else "") + ")",
         f"  씨앗 부호검정  이긴 씨앗 {r['이긴씨앗']}/{r['씨앗수'] - r['비긴씨앗']} · p {p글}"]
    if 갈렸나:
        줄.append("  **씨앗을 넘어 이긴다** -- 한 인스턴스의 성질이 아니다")
    else:
        더 = r.get("몇씨앗이면")
        줄.append("  **아직 씨앗 잡음과 갈리지 않는다**"
                  + (f" -- 같은 승률이면 **씨앗 {더}개**에서 판정된다. "
                     "기준을 낮추지 말고 씨앗을 늘려라" if 더 else " -- 승률이 낮아 씨앗을 늘려도 안 된다"))
    폭 = r["최대"] - r["최소"]
    if 폭 > 0 and abs(r["중앙값"]) < 폭:
        줄.append(f"  **씨앗 사이 폭({폭:.4f})이 중앙값({r['중앙값']:+.4f})보다 크다** -- "
                  "씨앗 하나로 낸 수를 쓰지 마라")
    return "\n".join(줄)


# ------------------------------------------------------------------ 원장
def 적기(줄: dict, repo=None) -> dict:
    p = Path(repo or _저장소()) / 원장경로
    p.parent.mkdir(parents=True, exist_ok=True)
    줄 = dict(줄)
    줄["id"] = f"{줄.get('때', '')}#{len(기록들(repo)) + 1}"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄


def 기록들(repo=None) -> list:
    p = Path(repo or _저장소()) / 원장경로
    if not p.is_file():
        return []
    out = []
    for 줄 in p.read_text(encoding="utf-8").splitlines():
        if 줄.strip():
            try:
                out.append(json.loads(줄))
            except json.JSONDecodeError:
                continue
    return out


def 보고(repo=None) -> str:
    것 = 기록들(repo)
    if not 것:
        return f"{원장경로} 가 비어 있다 -- `python3 -m vne.measure --재기 탐욕` 으로 한 판 남겨라"
    줄 = [f"{'때':17} {'방법':6} {'씨앗':>4} {'온':>4} {'받음':>4} {'거절':>4} {'못잼':>4} "
         f"{'수용률':>6} {'매출비':>6} {'초합':>7} {'맞나':>4}"]
    for x in 것[-12:]:
        수 = x.get("수용률")
        비 = x.get("매출비")
        줄.append(f"{str(x.get('때'))[:16]:17} {str(x.get('방법')):6} {x.get('씨앗', 0):>4} "
                  f"{x.get('온요청', 0):>4} {x.get('받음', 0):>4} {x.get('거절', 0):>4} "
                  f"{x.get('못잼', 0):>4} {(f'{수:.3f}' if 수 is not None else '--'):>6} "
                  f"{(f'{비:.3f}' if 비 is not None else '--'):>6} "
                  f"{x.get('초합', 0):>7.2f} {'o' if x.get('맞나') else '**X**':>4}")
    나쁨 = [x for x in 것 if not x.get("맞나")]
    if 나쁨:
        줄.append(f"\n**항등식이 깨진 판이 {len(나쁨)}개다** -- 온요청 != 받음+거절+못잼. "
                  "그 판의 수용률은 믿지 마라(분모에서 빠진 것이 있다)")
    줄.append(f"\nLP gap: {_풀이기말()}")
    마지막 = 것[-1]
    if 마지막.get("거절사유"):
        줄.append("마지막 판의 거절 사유: " + " · ".join(f"{k} {v}" for k, v in
                                                sorted(마지막["거절사유"].items())))
    기계들 = {json.dumps(x.get("기계") or {}, ensure_ascii=False) for x in 것}
    if len(기계들) > 1:
        줄.append(f"\n**기계가 {len(기계들)}가지다** -- 초는 기계마다 다르다. 섞어 읽지 마라")
    return "\n".join(줄)


def 견줌보고(앞: dict, 뒤: dict) -> str:
    r = 짝(앞, 뒤)
    if not r["견줄수있나"]:
        return "**견줄 수 없다**: " + "; ".join(r["까닭"])
    p글 = f"{r['부호p']:.2%}" if r["부호p"] is not None else "못 잼"
    바닥 = r["잡음바닥"]
    return "\n".join([
        f"공통 요청 {r['공통']}개에서만 뺐다 (앞 {앞['방법']} vs 뒤 {뒤['방법']}, 씨앗 {앞['씨앗']})",
        f"  수용   {r['앞수용']} -> {r['뒤수용']}  (Δ {r['Δ수용']:+d} · Δ수용률 {r['Δ수용률']:+.4f})",
        f"         뒤만 받은 요청 {r['뒤만받은요청']} · 앞만 받은 요청 {r['앞만받은요청']}",
        f"  시간   Δ {r['Δ초']:+.6f}초 · 잡음바닥 "
        f"{(f'{바닥:.6f}초' if 바닥 is not None else '못 잼')} · "
        f"짝 {r['짝이김'][0]}/{r['짝이김'][1]} · 부호검정 p {p글}",
        _시간말(r, 바닥),
    ])


def _시간말(r: dict, 바닥) -> str:
    r"""**단측검정을 양측 문장으로 읽지 않는다.**

    실측 2026-09-13: 탐욕 vs FF 에서 `짝 0/40 · p 100%` 가 나왔는데 보고가
    "시간 차이는 잡음과 구별되지 않는다" 라고 적었다. **틀렸다** -- 마흔 짝이 전부
    반대쪽이었다. 구별이 안 되는 것이 아니라 **뒤가 뚜렷하게 느린 것**이다.

    `짝으로갈렸나` 는 "뒤가 더 빠른가" 만 본다(단측). 그러니 셋으로 갈라 적어야 한다.

        뒤가 빠르다 / **뒤가 느리다** / 못 가른다
    """
    import perf
    이김, 짝 = r["짝이김"]
    if r["시간이갈렸나"]:
        return "  **뒤가 빠르다** -- 시간 차이가 잡음과 갈린다"
    진것 = 짝 - 이김
    거꾸로p = perf.부호검정p(진것, 짝)
    if 거꾸로p is not None and 거꾸로p <= perf.부호문턱:
        return (f"  **뒤가 느리다** -- 반대쪽으로 갈린다 (앞이 이긴 짝 {진것}/{짝} · "
                f"부호검정 p {거꾸로p:.2%}). 잡음이 아니다")
    return "  시간 차이를 **못 가른다** -- 어느 쪽이 빠른지 말하지 않는다"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VNE 측정 -- 재는 쪽만")
    ap.add_argument("--재기", dest="run", default="", help="방법 이름 (예: 탐욕)")
    ap.add_argument("--견주기", dest="cmp", nargs=2, metavar=("앞", "뒤"), default=None)
    ap.add_argument("--씨앗들", type=int, default=0,
                    help="--견주기 를 씨앗 0..N-1 로 되풀이해 **씨앗 잡음까지** 잰다")
    ap.add_argument("--씨앗", type=int, default=0)
    ap.add_argument("--요청", type=int, default=기본요청수)
    ap.add_argument("--노드", type=int, default=T.바탕노드수)
    ap.add_argument("--꼴", default="waxman", choices=("waxman", "random"))
    ap.add_argument("--보고", action="store_true")
    ap.add_argument("--방법목록", action="store_true")
    ap.add_argument("--안적기", action="store_true", help="원장에 안 남긴다")
    a = ap.parse_args(argv)

    if a.방법목록:
        print("  " + " · ".join(EM.방법들))
        return 0
    if a.보고:
        print(보고())
        return 0
    if a.cmp and a.씨앗들:
        r = 여러씨앗(a.cmp[0], a.cmp[1], range(a.씨앗들), 요청수=a.요청,
                  바탕노드수=a.노드, 꼴=a.꼴, 말하기=lambda s: print(s, flush=True))
        print()
        print(여러씨앗보고(r))
        return 0 if r.get("됐나") else 3
    if a.cmp:
        판 = [한판(m, 씨앗=a.씨앗, 요청수=a.요청, 바탕노드수=a.노드, 꼴=a.꼴,
                 말하기=lambda s: print(s, flush=True)) for m in a.cmp]
        print()
        print(견줌보고(*판))
        print("\n**씨앗 하나로 잰 것이다.** 같은 두 방법이 씨앗에 따라 +0.038 ~ +0.195 로 "
              "다섯 배 움직인 적이 있다(실측). 씨앗 잡음까지 보려면 `--씨앗들 8` 을 붙여라.")
        return 0
    if a.run:
        r = 한판(a.run, 씨앗=a.씨앗, 요청수=a.요청, 바탕노드수=a.노드, 꼴=a.꼴,
               말하기=lambda s: print(s, flush=True))
        if r.get("못잼") == -1:
            print(r["말"])
            return 3
        if not a.안적기:
            r = 적기(r)
        print()
        print(f"방법 {r['방법']} · 씨앗 {r['씨앗']} · 바탕 {r['바탕노드수']}노드/{r['바탕링크수']}링크")
        print(f"  온요청 {r['온요청']} = 받음 {r['받음']} + 거절 {r['거절']} + 못잼 {r['못잼']}"
              f"  {'(맞다)' if r['맞나'] else '**(안 맞는다 -- 분모에서 빠진 것이 있다)**'}")
        print(f"  수용률 {r['수용률']} · 매출 {r['매출']} · 비용 {r['비용']} · 매출비 {r['매출비']}")
        print(f"  초합 {r['초합']} · 초중앙값 {r['초중앙값']}")
        if r["거절사유"]:
            print("  거절 사유: " + " · ".join(f"{k} {v}" for k, v in sorted(r["거절사유"].items())))
        print(f"  LP gap: {r['LP말']}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
