# -*- coding: utf-8 -*-
"""house/dv/trace -- **요구사항과 시나리오를 잇는다(traceability).**

## 왜 있나

`house/req.py` 가 번호를 붙였고 `house/dv/plan.py` 가 시나리오를 뽑았는데,
**둘이 서로를 모른다.** 업계 사슬의 화살표 하나가 비어 있다.

    요구사항(REQ-ID) --???--> 시나리오 -> 커버 빈 -> PASS/FAIL -> 되짚기

이 파일이 그 화살표다. 그리고 이 화살표의 값은 **걸린 것이 아니라 안 걸린 것**에
있다 -- *"REQ-MERA-012 는 시험할 시나리오가 하나도 없다"* 가 이 표가 내는 말이다.

## 글자로 맞추지 않는다 -- **id 로 맞춘다**

두 쪽 다 출처에 포트 이름을 적는다. 그래서 낱말이 겹치는지로 이을 수 있을 것
같지만, 그러면 `in_vld` 에서 나온 물음 하나가 `in_vld` 에서 나온 시나리오
**전부**에 걸린다. "리셋 중 valid 가 0인가" 가 "백프레셔 최대" 에 걸리는 식이다.

**그것은 거짓 초록이다.** 시나리오가 그 물음을 가리지 않는데 가린다고 적으면,
사람은 그 요구사항이 시험된다고 믿는다. 이 저장소의 규율이 정확히 그 반대다 --
*검사하지 않은 초록불이 검사한 빨간불보다 나쁘다.*

그래서 **물음 id 와 시나리오 id 를 짝지은 표**만 쓴다. 양쪽 id 가 다 규칙에서
나오므로(`q_valid_hold` · `hs_<이름>_hold`) 이 짝은 회로를 안 가린다.

## 헷갈리면 **안 걸린 것으로 둔다**

`q_overflow`("포화인가 되돌이인가")를 `err_inject` 에 안 건다. `err_inject` 는
플래그가 서는지를 보지, **포화인지 되돌이인지를 가리지 않는다.** 곁에 있다고
거는 것은 안 이은 것보다 나쁘다.

## 이 파일이 못 하는 것

  · **걸렸다고 검증된 것이 아니다.** 시나리오가 있다는 뜻일 뿐, 그 시나리오가
    돌았는지 · 통과했는지는 관문(`house/gen.py`)이 따로 잰다
  · 요청 표가 못박은 수는 대개 안 걸린다 -- 톱 파라미터와 **이름이 똑같을 때**만
    잇는다. 그 수를 시험으로 옮기는 것은 아직 사람의 몫이다
  · 산술(포화·반올림·누산기 폭)과 성능(처리율·지연)에는 **짝이 아예 없다**

실행: python3 house/dv/trace.py [회로키]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent.parent
if str(저장소) not in sys.path:
    sys.path.insert(0, str(저장소))


# 물음 id -> 그 물음을 **실제로 가리는** 시나리오 id 꼴.
#
# **여기 없는 물음은 안 걸린다.** 그것이 이 표의 요점이다 -- 빈 자리가
# "아직 시험이 없다" 를 말한다.
이음표 = {
    "q_backpressure": (r"^hs_.*_stall90$", r"^hs_.*_noready$"),
    "q_valid_hold":   (r"^hs_.*_hold$",),
    "q_reset_valid":  (r"^hs_.*_rstvalid$",),
    "q_pkt_len":      (r"^pkt_.*_min$", r"^pkt_.*_max$"),
    "q_partial":      (r"^strb_",),
    "q_rst_kind":     (r"^rst_async_release$",),
    "q_rst_value":    (r"^rst_.*_first$",),
    "q_clk_rel":      (r"^cdc_",),
    "q_err_clear":    (r"^err_inject$",),
    # 아래는 **일부러 비워 둔다** -- 짝이 될 시나리오가 없다.
    #   q_overflow  포화/되돌이를 가리는 시나리오가 없다 (err_inject 는 플래그만 본다)
    #   q_round     반올림/버림을 가리는 시나리오가 없다
    #   q_accw      누산기 폭은 시험이 아니라 설계 판단이다
    #   q_throughput · q_latency   성능은 plan.py 가 "못 뽑는 것" 으로 적어 둔 칸이다
    #   q_regmap    레지스터 맵이 정해져야 시나리오가 나온다
}

_물음id = re.compile(r"물음\s+(q_[a-z_]+)")
_톱파라 = re.compile(r"톱 파라미터\s+([A-Za-z_][0-9A-Za-z_]*)\s*=")


from house.dv import plan as PLAN      # noqa: E402


def _물음에서(r: dict) -> str:
    """요구사항 줄의 출처에서 물음 id 를 꺼낸다."""
    m = _물음id.search(str(r.get("출처") or ""))
    return m.group(1) if m else ""


def 걸기(요구: dict, 계획: dict) -> dict:
    """요구사항에 시나리오를 건다. **요구 줄의 `검증` 칸을 채운다.**"""
    시나리오 = list((계획 or {}).get("시나리오") or [])
    줄들 = list((요구 or {}).get("요구사항") or [])
    if not 줄들:
        return {"됐나": False, "까닭": "요구사항이 없다"}

    이은시나리오 = set()
    for r in 줄들:
        q = _물음에서(r)
        걸린 = []
        for 꼴 in 이음표.get(q, ()):
            걸린 += [x for x in 시나리오 if re.search(꼴, x["id"])]

        # 요청 표가 못박은 수 ↔ **그 줄에서 나온 시나리오**.
        # `plan.표에서()` 가 시나리오에 `표항목` 을 적어 두므로 글자가 아니라
        # **같은 줄인지**로 잇는다. 그 다음이 이름이 똑같은 톱 파라미터다.
        항 = str(r.get("글") or "").split(":")[0].split(" = ")[0].strip()
        if not 걸린 and r.get("상태") == "못박힘" and 항:
            걸린 += [x for x in 시나리오 if str(x.get("표항목") or "") == 항]
            열쇠 = re.sub(r"[^0-9A-Za-z]+", "", 항).lower()
            if not 걸린 and 열쇠:
                for x in 시나리오:
                    m = _톱파라.search(str(x.get("출처") or ""))
                    if m and m.group(1).lower() == 열쇠:
                        걸린.append(x)

        본것, 고른것 = set(), []
        for x in 걸린:
            if x["id"] in 본것:
                continue
            본것.add(x["id"])
            고른것.append(x)
        r["검증"] = [x["id"] for x in 고른것]
        r["빈"] = [b for x in 고른것 for b in x["빈"]]
        이은시나리오 |= 본것

        # **테스트벤치가 안 재는 것도 있다.** 동작 주파수는 시나리오가 아니라
        # 관문 7(STA 슬랙 ≥ 0)이 잰다 -- 그것을 "시험 없음" 으로 적으면 거짓
        # 빨간불이다. 다만 **없는 관문을 있다고 하지 않는다**: 처리율·샘플레이트
        # 에는 잴 관문이 아예 없고, 그것은 그대로 적는다.
        r["관문"] = ""
        if not 고른것 and r.get("상태") == "못박힘" and 항:
            값 = str(r.get("글") or "")
            갈래, _ = PLAN.표줄갈래(항, 값)
            if 갈래 == "클럭":
                r["관문"] = "관문 7 (STA 슬랙 ≥ 0)"
            elif 갈래 == "속도":
                r["관문"] = "— 처리율을 재는 관문이 없다"

    걸린줄 = [r for r in 줄들 if r["검증"]]
    # **TBD 는 따로 센다.** 아직 요구사항이 아닌 것을 "시험이 없다" 로 세면
    # 그 수가 사실은 "아직 안 물어본 것" 의 수가 된다 (req.py 가 배운 것과 같다).
    안걸린 = [r for r in 줄들 if not r["검증"] and r.get("상태") != "TBD"
           and not (r.get("관문") or "").startswith("관문")]
    관문이잰다 = [r for r in 줄들 if (r.get("관문") or "").startswith("관문")]
    안걸린TBD = [r for r in 줄들 if not r["검증"] and r.get("상태") == "TBD"]
    떠있는 = [x for x in 시나리오 if x["id"] not in 이은시나리오]
    return {"됐나": True, "요구사항": 줄들,
            "걸린수": len(걸린줄), "안걸린": 안걸린, "안걸린수": len(안걸린),
            "안걸린TBD": 안걸린TBD, "관문이잰다": 관문이잰다,
            "떠있는시나리오": 떠있는, "떠있는수": len(떠있는),
            "시나리오수": len(시나리오),
            "못하는것": [
                "걸렸다고 검증된 것이 아니다 — 시나리오가 있다는 뜻일 뿐이다",
                "요청 표의 수는 톱 파라미터와 이름이 똑같을 때만 걸린다",
                "산술(포화·반올림·누산기 폭)과 성능(처리율·지연)에는 짝이 아예 없다",
            ]}


def 포트세우기(스펙=None, 미정: "dict | None" = None) -> list:
    """제안 단계에는 RTL 이 없다. **포트로 시나리오를 뽑게** 자리를 만든다.

    모델 키가 없으면 `s.포트` 도 비므로, specq 가 요청 글에서 세운 인터페이스를
    빌려 쓴다 -- 없는 것을 지어내는 것이 아니라 **요청 글이 이름으로 부른 것**이다.
    """
    포트 = [dict(p) for p in (getattr(스펙, "포트", None) or [])]
    if 포트:
        return 포트
    본것 = []
    for _, 포트들 in ((미정 or {}).get("글로본것") or []):
        for n in 포트들:
            if n not in [p["이름"] for p in 본것]:
                본것.append({"이름": n, "방향": "input", "폭": 1})
    return 본것


def 요약글(t: dict) -> str:
    if not t.get("됐나"):
        return "요구사항에 시나리오를 못 걸었다"
    조각 = [f"시나리오가 걸린 요구사항 {t['걸린수']}개"]
    if t.get("관문이잰다"):
        조각.append(f"관문이 재는 것 {len(t['관문이잰다'])}개")
    if t.get("안걸린수"):
        조각.append(f"**시험이 없는 요구사항 {t['안걸린수']}개**")
    if t.get("안걸린TBD"):
        조각.append(f"아직 TBD {len(t['안걸린TBD'])}개")
    if t.get("떠있는수"):
        조각.append(f"요구사항에 안 걸린 시나리오 {t['떠있는수']}개")
    return " · ".join(조각)


if __name__ == "__main__":
    from house import designs as DES
    from house import spec as SPEC
    from house import specq as SPECQ
    from house import req as REQ
    from house import rtlscan as SCAN
    from house.dv import plan as PLAN
    키 = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = DES.찾기(키)
    훑 = SCAN.훑기(d.RTL, d.top)
    s = SPEC.스펙(요청=f"{d.이름} -- {d.한줄}", 이름=d.이름,
                포트=훑.get("포트") or [], 수={"주파수_Hz": [1e8]})
    미 = SPECQ.세우기(s)
    t = 걸기(REQ.붙이기(s, 미, 키=d.키), PLAN.세우기(d, 훑))
    print(f"[trace] {d.키}")
    print(요약글(t))
    print()
    for r in t["요구사항"]:
        표 = ", ".join(r["검증"]) or r.get("관문") or "— 시험 없음"
        print(f"  {r['id']}  {r['글'][:52]}")
        print(f"      {표}")
