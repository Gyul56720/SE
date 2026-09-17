"""**규격 문턱으로 구조를 견준다** -- "몇 배 좋아졌나" 가 아니라 "몇 dB 가 드나".

## 잣대를 바꾼다

앞판은 **BER 비(比)** 로 말했다: "표가 baseline 보다 7.98배 좋다". 그 문장의 문제는
**어느 BER 에서인가**를 안 적으면 아무 뜻이 없다는 것이다. 실제로 그 7.98배는
1e-2 에서 2.27 dB 였고 1e-12 에서는 0.34 dB 였다 -- 같은 "7.98배" 가 동작점에 따라
일곱 배 다른 값이 된다.

그래서 잣대를 **규격의 잣대**로 바꾼다.

    물음:  KP4 pre-FEC 문턱(~2.2e-4)에 닿는 데 SNR 이 몇 dB 드나?
    답:    팔마다 그 dB. 그 차이가 **규격 여유(compliance margin)** 다.

이 잣대는 동작점을 고를 여지가 없다 -- 문턱이 부호가 정한 값이다.

## **바닥을 먼저 본다** -- 이것이 이 모듈의 핵심

SNR 을 올려도 안 내려가는 바닥이 문턱 위에 있으면, 그 구조는 **어떤 SNR 로도 규격을
못 넘는다.** 이분법으로 "필요 SNR" 을 찾으면 그런 경우에도 **숫자 하나가 나와서**
닿은 줄 알게 된다 -- 그것이 정확히 앞판이 저지른 잘못이다.

그래서 `필요SNR()` 은 **이분법 전에** 아주 높은 SNR(`바닥SNR`, 기본 55 dB)에서 한 번
돌려 본다.

    바닥BER > 문턱   ->  판정 `바닥` : 규격 불가. **필요 SNR 을 내지 않는다.**
    바닥BER <= 문턱  ->  이분법으로 필요 SNR 을 찾는다

## 오류 0 을 BER 0 으로 읽지 않는다

3의 규칙으로 위쪽 한계 `3/N` 을 쓴다. 그리고 그 한계가 문턱보다 **크면** 판정을
못 한다 -- 그때는 심볼을 더 보내야 한다고 말한다(`모자란다`).
"""
from __future__ import annotations

import math

import numpy as np

import fec
import serdes


def _BER위한계(r: dict) -> float:
    """오류 0 이면 3의 규칙, 아니면 잰 값."""
    if r.get("오류수", 0) > 0:
        return float(r["BER"])
    return 3.0 / max(int(r.get("잰비트", 0)), 1)


def 필요SNR(구성: dict, 부호: str = "KP4", 목표: float = 0.0,
         바닥SNR: float = 55.0, 낮게: float = 10.0, 높게: float = 55.0,
         되풀이: int = 15, 씨: int = 0) -> dict:
    """**문턱에 닿는 데 드는 SNR.** 못 닿으면 못 닿는다고 말한다.

    `구성` 은 `serdes.링크` 에 그대로 넘어가는 딕셔너리다(SNRdB 와 씨는 여기서 준다).
    """
    목표 = float(목표) if 목표 else fec.문턱(1e-15, 부호)
    인자 = {k: v for k, v in 구성.items() if k not in ("SNRdB", "씨")}

    # (가) **바닥 먼저.** 아주 높은 SNR 에서도 문턱을 못 넘으면 이분법은 뜻이 없다.
    바닥r = serdes.링크(SNRdB=float(바닥SNR), 씨=씨, **인자)
    if 바닥r.get("판정") != serdes.PASS:
        return {"판정": serdes.못잼, "왜": 바닥r.get("왜", ""), "목표": 목표}
    바닥p = _BER위한계(바닥r)
    잰비트 = int(바닥r["잰비트"])
    if 3.0 / max(잰비트, 1) > 목표:
        return {"판정": serdes.못잼, "목표": 목표, "바닥BER": 바닥p,
                "왜": (f"심볼이 모자란다 -- 오류 0 이어도 위한계가 {3.0/잰비트:.2e} 로 "
                      f"문턱 {목표:.2e} 보다 크다. 심볼수를 "
                      f"{int(3.0/목표/max(1,바닥r.get('M',2)))*2:,} 이상으로")}
    if 바닥p > 목표:
        return {"판정": serdes.PASS, "결과": "바닥", "목표": 목표,
                "바닥BER": 바닥p, "바닥SNR": float(바닥SNR),
                "SNRdB": float("nan"), "닿나": False,
                "문턱대비": 바닥p / 목표,
                "왜": (f"SNR {바닥SNR:.0f} dB 에서도 BER {바닥p:.3e} 로 문턱 "
                      f"{목표:.2e} 의 {바닥p/목표:.1f}배 -- **바닥에 걸려 어떤 SNR "
                      f"로도 규격을 못 넘는다**")}

    # (나) 이분법
    낮, 높 = float(낮게), float(높게)
    for _ in range(int(되풀이)):
        가 = 0.5 * (낮 + 높)
        p = _BER위한계(serdes.링크(SNRdB=가, 씨=씨, **인자))
        if p > 목표:
            낮 = 가
        else:
            높 = 가
    SNR = 0.5 * (낮 + 높)
    끝 = serdes.링크(SNRdB=SNR, 씨=씨, **인자)
    p = _BER위한계(끝)
    닿았나 = 끝["오류수"] > 0 and 0.2 * 목표 < 끝["BER"] < 5.0 * 목표
    판 = fec.판정(끝.get("비트오류자리", np.array([], dtype=np.int64)),
                끝["잰비트"], 부호)
    return {"판정": serdes.PASS, "결과": "닿는다", "목표": 목표,
            "SNRdB": float(SNR), "BER": p, "오류수": int(끝["오류수"]),
            "잰비트": int(끝["잰비트"]), "바닥BER": 바닥p, "닿나": True,
            "이분법닿았나": bool(닿았나), "FEC": 판,
            "왜": (f"SNR {SNR:.2f} dB 에서 BER {p:.3e} (문턱 {목표:.2e})"
                  + ("" if 닿았나 else "  **이분법이 목표에 못 앉았다 -- 믿지 마라**"))}


def 팔들(바탕: dict, 팔: dict, 부호: str = "KP4", 씨들=(0, 1, 2), **인자) -> dict:
    """여러 구조를 **필요 SNR** 로 견준다. 씨마다 재고 씨 사이 흩어짐을 같이 낸다.

    돌려주는 `여유dB` 는 **기준 팔 대비 아낀 dB** 다 -- 양수면 그만큼 싼 링크로도
    규격을 넘는다는 뜻이다. 어느 팔이 `바닥` 이면 그 팔에는 dB 가 없다(그것이 답이다).
    """
    이름들 = list(팔.keys())
    난것 = {}
    for 이름 in 이름들:
        줄 = []
        for s in 씨들:
            r = 필요SNR({**바탕, **팔[이름]}, 부호=부호, 씨=s, **인자)
            줄.append(r)
        닿 = [x for x in 줄 if x.get("닿나")]
        바닥들 = [x for x in 줄 if x.get("결과") == "바닥"]
        난것[이름] = {
            "줄": 줄, "닿은씨": len(닿), "씨수": len(줄),
            "바닥씨": len(바닥들),
            "SNRdB평균": float(np.mean([x["SNRdB"] for x in 닿])) if 닿 else float("nan"),
            "SNRdB최대차": (float(np.ptp([x["SNRdB"] for x in 닿]))
                        if len(닿) > 1 else 0.0),
            "바닥BER평균": float(np.mean([x["바닥BER"] for x in 줄
                                    if np.isfinite(x.get("바닥BER", np.nan))]))
                        if 줄 else float("nan"),
        }
    기준 = 이름들[0]
    for 이름 in 이름들:
        a, b = 난것[기준]["SNRdB평균"], 난것[이름]["SNRdB평균"]
        난것[이름]["여유dB"] = (a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
    return {"판정": serdes.PASS, "기준": 기준, "부호": 부호, "팔": 난것}


def 말로(r: dict) -> str:
    if r.get("판정") != serdes.PASS:
        return f"못 잼: {r.get('왜','')}"
    줄 = [f"[{r['부호']} 문턱 기준 -- 필요 SNR, 기준={r['기준']}]"]
    for 이름, d in r["팔"].items():
        if d["닿은씨"] == 0:
            줄.append(f"  {이름:22s} **못 넘는다** -- {d['바닥씨']}/{d['씨수']} 씨가 "
                     f"바닥(평균 {d['바닥BER평균']:.2e})")
        else:
            줄.append(f"  {이름:22s} {d['SNRdB평균']:6.2f} dB "
                     f"(씨 {d['닿은씨']}/{d['씨수']}, 흩어짐 {d['SNRdB최대차']:.2f} dB)"
                     + ("" if 이름 == r["기준"] else f"  여유 {d['여유dB']:+.2f} dB"))
    return "\n".join(줄)
