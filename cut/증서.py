"""증서 -- **판정을 파일로 내보내고, 판정기가 그것을 다시 읽어 독립으로 재판정한다.**

까닭. 지금까지 판정은 메모리 안에서 나고 끝났다. 그러면 "이 부등식이 유효했다" 는 말이
**그 실행에만** 있고, 그 뒤로는 아무도 다시 못 잰다. 증서를 남기면 세 가지가 생긴다.

  1. 발견기가 뱉은 것을 판정기가 **따로** 확인한다 -- 같은 프로세스 안이 아니라 파일을 건너
  2. 바탕이 바뀌면 **옛 증서를 못 쓴다는 것이 드러난다**(바탕지문)
  3. 남이 재현할 수 있다 -- 증서에 씨앗이 들어 있어 인스턴스를 다시 지을 수 있다

## 바탕은 바뀌면 안 된다

사용자(2026-09-13): *"개선 전 파일을 절대로 건드리지 않는 것. baseline 자체가 변하면 안
된다. 그래야 ΔGap, ΔNodes, ΔTime 을 정확하게 측정할 수 있다."*

그것을 규칙으로 적는 대신 **재는 값**으로 만든다. 증서마다 바탕(FF 를 짓는 코드와 인스턴스를
짓는 코드)의 지문을 넣는다. 바탕이 한 글자라도 바뀌면 `다시판정` 이 **못잼**을 돌려준다 --
"틀렸다" 가 아니라 "이 증서로는 더 못 견준다" 다. 그 둘은 다르다.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from . import ff as FF
from . import 판정 as J

증서자리 = "cut/증서"
바탕파일 = ("cut/ff.py", "vne/topo.py")        # **이 둘이 바탕이다.** 바뀌면 옛 증서를 못 쓴다


def _뿌리() -> Path:
    return Path(__file__).resolve().parent.parent


def 바탕지문(repo=None) -> str:
    """바탕 파일들의 지문. **한 글자만 바뀌어도 달라진다.**"""
    h = hashlib.sha256()
    for f in 바탕파일:
        p = Path(repo or _뿌리()) / f
        h.update(f.encode("utf-8"))
        h.update(p.read_bytes() if p.is_file() else b"<missing>")
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ a 를 JSON 으로
def a풀기(a: dict) -> list:
    """`{("x", v, u): 계수}` 를 JSON 에 담기는 꼴로. **튜플 열쇠는 JSON 에 못 들어간다.**"""
    난것 = []
    for 열쇠, 계수 in sorted((a or {}).items(), key=lambda kv: str(kv[0])):
        if 열쇠[0] == "x":
            난것.append({"갈래": "x", "가상노드": 열쇠[1], "바탕노드": 열쇠[2], "계수": float(계수)})
        elif 열쇠[0] == "y":
            난것.append({"갈래": "y", "가상링크": list(열쇠[1]), "호": list(열쇠[2]),
                       "계수": float(계수)})
        else:
            raise KeyError(f"모르는 변수 갈래: {열쇠[0]!r}")
    return 난것


def a묶기(풀린것: list) -> dict:
    """되돌린다. **모르는 갈래는 터뜨린다** -- 조용히 빼면 다른 부등식을 재게 된다."""
    a = {}
    for x in 풀린것 or ():
        if x["갈래"] == "x":
            a[("x", x["가상노드"], x["바탕노드"])] = float(x["계수"])
        elif x["갈래"] == "y":
            a[("y", tuple(x["가상링크"]), tuple(x["호"]))] = float(x["계수"])
        else:
            raise KeyError(f"모르는 변수 갈래: {x.get('갈래')!r}")
    return a


# ------------------------------------------------------------------ 쓰기 · 읽기
def 쓰기(이름: str, a: dict, b: float, 판정결과: dict, 인스턴스: dict,
       족: str = "", repo=None) -> Path:
    """증서 하나를 남긴다. `인스턴스` 는 **다시 지을 수 있는 만큼** 담아야 한다(씨앗 등)."""
    뿌 = Path(repo or _뿌리())
    자리 = 뿌 / 증서자리
    자리.mkdir(parents=True, exist_ok=True)
    때 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    쪽 = 자리 / f"{때}_{hashlib.sha256(이름.encode()).hexdigest()[:8]}.json"
    ㅇ, ㅈ, ㅁ = 판정결과.get("유효") or {}, 판정결과.get("자름") or {}, 판정결과.get("조임") or {}
    쪽.write_text(json.dumps({
        "증서id": 쪽.stem, "때": 때, "이름": 이름, "족": 족,
        # **바탕이 바뀌면 이 증서는 못 쓴다.** 그것이 드러나게 지문을 박는다
        "바탕지문": 바탕지문(repo), "바탕파일": list(바탕파일),
        "인스턴스": 인스턴스,
        "부등식": {"a": a풀기(a), "b": float(b)},
        "결정": 판정결과.get("결정"), "막힌곳": 판정결과.get("막힌곳", ""),
        "유효": {"판정": ㅇ.get("판정"), "최대정수": ㅇ.get("최대")},
        "자름": {"판정": ㅈ.get("판정"), "최대LP": ㅈ.get("최대")},
        "조임": {"판정": ㅁ.get("판정"), "앞": ㅁ.get("앞"), "뒤": ㅁ.get("뒤"), "Δ": ㅁ.get("Δ")},
        # **증명의 갈래를 이름으로 적는다.** 표본이 아니라 최적까지 푼 MIP 다 --
        # 다만 그것은 **이 인스턴스 하나**에 대한 증명이고 family 는 아니다
        "증명갈래": "exact_mip_이_인스턴스",
        "한계": "이 인스턴스에 대한 증명이다. 모든 인스턴스(inequality family)는 아니다",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 쪽


def 읽기(쪽) -> dict:
    return json.loads(Path(쪽).read_text(encoding="utf-8"))


def 증서들(repo=None) -> list:
    자리 = Path(repo or _뿌리()) / 증서자리
    return sorted(자리.glob("*.json")) if 자리.is_dir() else []


# ------------------------------------------------------------------ 다시 판정
def 인스턴스짓기(속: dict):
    """증서에 적힌 씨앗으로 **같은 인스턴스를 다시 짓는다.**"""
    from vne import topo as T
    바탕 = T.바탕망(씨앗=속["바탕씨앗"], 노드수=속["바탕노드수"], 꼴=속["꼴"],
                cpu범위=tuple(속["바탕cpu범위"]), 대역범위=tuple(속["바탕대역범위"]),
                p=속.get("p", 0.5))
    요청 = T.요청망(씨앗=속["요청씨앗"], 노드범위=tuple(속["요청노드범위"]),
                cpu범위=tuple(속["요청cpu범위"]), 대역범위=tuple(속["요청대역범위"]))
    return 바탕, 요청


def 다시판정(쪽, repo=None, 시한초: float = 60.0) -> dict:
    r"""**증서를 파일에서 읽어 처음부터 다시 잰다.** 쓴 쪽의 말을 하나도 안 믿는다.

    셋 중 하나를 돌려준다.

      맞다     다시 재니 증서에 적힌 것과 같다
      어긋난다 다시 재니 다르다  -> **증서가 거짓이다**
      못잼     바탕이 바뀌었거나 인스턴스를 못 지었다 -> 이 증서로는 더 못 견준다
    """
    증 = 읽기(쪽)
    지금 = 바탕지문(repo)
    if 증.get("바탕지문") != 지금:
        return {"판정": "못잼", "어긋남": [],
                "말": f"**바탕이 바뀌었다** (증서 {증.get('바탕지문')} vs 지금 {지금}) -- "
                    f"{', '.join(증.get('바탕파일') or 바탕파일)} 가운데 무엇인가 달라졌다. "
                    "이 증서로는 더 못 견준다(틀렸다는 뜻이 아니다)"}
    try:
        바탕, 요청 = 인스턴스짓기(증["인스턴스"])
        p = FF.짓기(바탕, 요청)
        a, b = a묶기(증["부등식"]["a"]), float(증["부등식"]["b"])
    except Exception as e:                                          # noqa: BLE001
        return {"판정": "못잼", "어긋남": [], "말": f"인스턴스를 못 지었다: {type(e).__name__}: {e}"[:160]}

    다시 = J.채택판정(p, a, b, 시한초=시한초)
    어긋 = []
    if 다시["결정"] != 증.get("결정"):
        어긋.append(f"결정: 증서 {증.get('결정')} vs 다시 {다시['결정']}")
    for 칸 in ("유효", "자름", "조임"):
        옛 = (증.get(칸) or {}).get("판정")
        새 = (다시.get(칸) or {}).get("판정")
        if 옛 is not None and 새 is not None and 옛 != 새:
            어긋.append(f"{칸}: 증서 {옛} vs 다시 {새}")
    옛최대 = (증.get("유효") or {}).get("최대정수")
    새최대 = (다시.get("유효") or {}).get("최대")
    if 옛최대 is not None and 새최대 is not None and abs(float(옛최대) - float(새최대)) > 1e-6:
        어긋.append(f"최대정수: 증서 {옛최대} vs 다시 {새최대}")
    if 어긋:
        return {"판정": "어긋난다", "어긋남": 어긋, "다시": 다시,
                "말": f"**증서와 다시 잰 것이 {len(어긋)}군데 다르다** -- {어긋[0]}"}
    return {"판정": "맞다", "어긋남": [], "다시": 다시,
            "말": f"다시 재니 증서와 같다 (결정 {다시['결정']})"}


def 다시판정모두(repo=None, 시한초: float = 60.0) -> dict:
    셈 = {"맞다": 0, "어긋난다": 0, "못잼": 0}
    자세히 = []
    for 쪽 in 증서들(repo):
        r = 다시판정(쪽, repo, 시한초)
        셈[r["판정"]] += 1
        자세히.append({"쪽": 쪽.name, **{k: v for k, v in r.items() if k != "다시"}})
    return {"증서수": sum(셈.values()), **셈, "자세히": 자세히,
            "맞나": sum(셈.values()) == len(자세히)}
