# -*- coding: utf-8 -*-
"""house/dv/scenes -- **파형에 뽑을 신호를 역할로 고른다.**

## 왜 있나

`rtl/agent.py` 가 파형 네 장면(FSM · 파이프라인 · 게이팅 · CDC)에 뽑을 신호를
**이름으로 박아** 두고 있었다.

    u_ctrl.state_o · u_mac.p_s1 · u_icg.en_lat · u_coef_fifo.wgray

nsw_fir 의 인스턴스 이름이다. 다른 회로에서는 하나도 못 찾아 **네 장면이
통째로 빠진다.** 틀린 파형을 그리는 것보다는 낫지만, 그림 넷이 없는 보고서가
된다.

## 이름이 아니라 **역할**로 고른다

VCD 에는 계층 이름이 그대로 들어 있다(`TOP.nsw_fir.u_mac.p_s1`). 그러니
**거기 실제로 있는 것 중에서** 역할에 맞는 것을 고르면 된다.

    클럭      잎 이름이 `clk` 로 끝난다. 토글이 가장 많은 것
    FSM       스캔이 찾은 상태 신호 + 같은 자리의 1비트 제어선
    파이프라인 잎 이름이 `_s1`·`_s2`… 처럼 **단 번호로 끝나는** 무리
    게이팅    `_lat` 로 끝나는 잎이 있는 자리 (래치가 곧 ICG 다)
    CDC       스캔이 찾은 건넘 신호 + 그 이름을 **품은** 신호들(동기화 단)

## 지어내지 않는다

  · **VCD 에 실제로 있는 이름만** 돌려준다
  · **안 바뀌는 신호는 뺀다** -- 파라미터(`TAPS`·`SAT_HI`)도 VCD 에 신호로
    들어 있는데, 그것을 파형에 그리면 평평한 줄만 는다
  · 한 장면에 신호가 너무 적으면 **그 장면을 안 낸다**. 까닭을 같이 돌려준다

실행: python3 house/dv/scenes.py <vcd 파일> [회로키]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent.parent
if str(저장소) not in sys.path:
    sys.path.insert(0, str(저장소))

_최소신호 = 3          # 이보다 적으면 장면을 안 낸다
# **`wclk` 도 클럭이다.** 첫 판은 `(^|_)a?clk\w*$` 였는데 `wclk` 는 `clk` 앞이
# `w` 라 안 걸렸다 -- 그래서 CDC 장면에 클럭이 한 줄도 안 들어갔다(실측).
_클럭꼴 = re.compile(r"^[a-z]{0,3}clk[0-9a-z_]*$", re.I)
_단번호 = re.compile(r"_(?:s|r|q|d|p)(\d+)$", re.I)
_제어말 = ("start", "busy", "done", "ack", "vld", "valid", "rdy", "ready",
        "en", "push", "pop", "we", "req", "gnt", "err", "ovf", "empty", "full")


def _잎(이름: str) -> str:
    return 이름.rsplit(".", 1)[-1]


def _자리(이름: str) -> str:
    """`TOP.nsw_fir.u_mac.p_s1` -> `TOP.nsw_fir.u_mac`."""
    return 이름.rsplit(".", 1)[0] if "." in 이름 else ""


def 바뀌는것(d: dict) -> list:
    """**값이 실제로 바뀌는 신호만.** 파라미터는 VCD 에 있어도 한 번만 찍힌다.

    실측: `TOP.nsw_fir.u_mac.SAT_HI`(폭 40) · `u_ctrl.TAPS`(폭 32) 가 신호로
    들어 있다. 그것을 파형에 그리면 평평한 줄만 는다.
    """
    난것 = []
    for 이름, 이력 in (d.get("신호") or {}).items():
        if "[" in 이름:                       # 메모리 배열 낱칸은 뺀다
            continue
        if len(이력 or []) > 1:
            난것.append(이름)
    return sorted(난것)


def 클럭들(d: dict, 이름들=None) -> list:
    """토글이 많은 차례로. **가장 많이 토글하는 것이 그 회로의 클럭이다.**"""
    이름들 = 이름들 if 이름들 is not None else 바뀌는것(d)
    클 = [n for n in 이름들 if _클럭꼴.search(_잎(n))]
    return sorted(클, key=lambda n: -len(d["신호"].get(n) or []))


def _한비트(d: dict, 이름들) -> list:
    return [n for n in 이름들 if int(d.get("폭", {}).get(n, 1) or 1) == 1]


def 장면들(d: dict, 훑기: dict = None, 장면당=10) -> dict:
    """{"fsm": {...}, "파이프": {...}, "게이팅": {...}, "cdc": {...}, "못찾은것": []}

    장면마다 `{"신호": [이름…], "어디서": "왜 이것들을 골랐나"}`.
    """
    훑 = 훑기 or {}
    산것 = 바뀌는것(d)
    클 = 클럭들(d, 산것)
    으뜸클럭 = 클[0] if 클 else None
    난것, 못찾음 = {}, []

    def 담기(키, 신호, 어디서, 까닭없을때):
        신호 = [n for n in dict.fromkeys(신호) if n][:장면당]
        if len(신호) < _최소신호:
            못찾음.append(f"{키}: {까닭없을때} (찾은 신호 {len(신호)}개)")
            return
        난것[키] = {"신호": 신호, "어디서": 어디서}

    # ------------------------------------------------ FSM
    fsm이름 = ((훑.get("FSM") or [{}])[0] or {}).get("신호") or ""
    # **부분문자열로 찾으면 안 된다.** 첫 판은 `fsm이름 in _잎(n)` 이었는데
    # `st` 가 `wrst_n` 안에 들어 있어서 **다른 인스턴스의 리셋선**이 FSM 장면에
    # 끼었다(실측 2026-09-23). 이 저장소가 여러 번 겪은 꼴이다
    # (`ack` 가 `backpressure` 속에 든 것과 같다).
    #
    # 낱말로 본다: 잎이 그 이름이거나 `<이름>_무엇` 꼴이고, **같은 자리**여야 한다.
    상태 = [n for n in 산것 if fsm이름 and _잎(n) == fsm이름]
    자리 = _자리(상태[0]) if 상태 else ""
    if 자리:
        곁 = re.compile(rf"{re.escape(fsm이름)}(_\w+)?$")
        상태 += [n for n in 산것 if _자리(n) == 자리 and n not in 상태
               and 곁.fullmatch(_잎(n))]
    제어 = [n for n in _한비트(d, 산것)
          if 자리 and _자리(n) == 자리 and any(w in _잎(n).lower() for w in _제어말)]
    담기("fsm", ([으뜸클럭] if 으뜸클럭 else []) + 상태[:2] + 제어,
       f"스캔이 찾은 상태 신호 `{fsm이름}` 과 같은 자리의 1비트 제어선"
       if fsm이름 else "상태 신호를 못 찾았다",
       "스캔이 FSM 을 못 찾았거나 그 신호가 VCD 에 없다")

    # ------------------------------------------------ 파이프라인
    # 잎 이름이 단 번호로 끝나는 무리를 찾는다: `p_s1` · `a_s2` · `v_s3`
    무리 = {}
    for n in 산것:
        m = _단번호.search(_잎(n))
        if m:
            무리.setdefault(_자리(n), []).append((int(m.group(1)), n))
    파자리 = max(무리, key=lambda k: len(무리[k])) if 무리 else ""
    단들 = [n for _i, n in sorted(무리.get(파자리, []))]
    파클럭 = next((n for n in 클 if _자리(n) == 파자리), 으뜸클럭)
    파제어 = [n for n in _한비트(d, 산것)
           if 파자리 and _자리(n) == 파자리 and n not in 단들
           and any(w in _잎(n).lower() for w in ("push", "en", "vld", "valid"))]
    # **단은 다 보여야 한다.** 첫 판은 장면당 7개로 잘라서 `a_s3`·`v_s3` 가
    # 빠졌다 -- 파이프라인 그림에서 마지막 단이 없으면 미는 것이 안 보인다.
    담기("파이프", ([파클럭] if 파클럭 else []) + 파제어[:1] + 단들,
       f"잎 이름이 단 번호로 끝나는 신호 무리 (`{파자리.rsplit('.', 1)[-1]}`)"
       if 파자리 else "단 번호로 끝나는 신호가 없다",
       "이름이 `_s1`·`_s2` 꼴인 파이프라인 단이 VCD 에 없다")

    # ------------------------------------------------ 클럭 게이팅
    # 래치가 곧 ICG 다 -- 잎 이름이 `_lat` 로 끝나는 자리를 찾는다.
    래치 = [n for n in 산것 if _잎(n).lower().endswith(("_lat", "_latch"))]
    게자리 = _자리(래치[0]) if 래치 else ""
    게신호 = [n for n in 산것 if 게자리 and _자리(n) == 게자리]
    # **게이팅된 클럭은 가장 적게 토글하는 클럭이다** -- 게이팅이 엣지를 빼니까.
    # 첫 판은 `클` 이 토글 많은 차례라 **다른 도메인의 클럭**(wclk)을 집었다.
    # 실측 2026-09-23: srst_sync.clk 738 · wclk 247 · **u_mac.clk 239**(게이팅된 것).
    #
    # **이것은 구조가 아니라 셈으로 고른 것이다.** 느린 설정 도메인이 게이팅된
    # 클럭보다 더 적게 토글하면 엉뚱한 것을 집는다 -- 그래서 둘을 같이 낸다.
    게클럭 = sorted((n for n in 클 if _자리(n) != 게자리),
                 key=lambda n: len(d["신호"].get(n) or []))[:2]
    담기("게이팅", ([으뜸클럭] if 으뜸클럭 else []) + 게신호 + 게클럭,
       f"래치(`_lat`)가 있는 자리 (`{게자리.rsplit('.', 1)[-1]}`) 와 그것이 "
       f"만드는 클럭" if 게자리 else "래치를 못 찾았다",
       "잎 이름이 `_lat` 인 신호가 없다 — 통합 클럭 게이팅 셀을 못 찾았다")

    # ------------------------------------------------ CDC
    건넘 = [str(x.get("신호") or "") for x in (훑.get("CDC건넘") or [])]
    cdc = []
    for s in 건넘:
        if not s:
            continue
        # 그 이름을 **품은** 신호가 동기화 단이다: `wgray` -> `rq1_wgray` · `rq2_wgray`
        cdc += sorted(n for n in 산것 if s in _잎(n))
    cdc자리 = _자리(cdc[0]) if cdc else ""
    cdc클럭 = [n for n in 클 if _자리(n) == cdc자리][:1]
    담기("cdc", cdc클럭 + cdc,
       f"스캔이 찾은 건넘 신호 {건넘[:3]} 와 그 이름을 품은 동기화 단"
       if 건넘 else "건넘 신호가 없다",
       "스캔이 CDC 건넘을 못 찾았거나 그 신호가 VCD 에 없다")

    난것["못찾은것"] = 못찾음
    난것["못하는것"] = [
        "게이팅된 클럭은 **토글이 가장 적은 클럭**으로 고른다 — 구조가 아니라 "
        "셈이다. 느린 설정 도메인이 더 적게 토글하면 엉뚱한 것을 집는다",
        "파이프라인은 이름이 `_s1`·`_s2` 꼴일 때만 찾는다 — 다른 이름 규칙은 못 본다",
        "무엇이 옳은 파형인지는 모른다 — 어디를 보일지만 고른다",
    ]
    난것["으뜸클럭"] = 으뜸클럭
    난것["산신호수"] = len(산것)
    return 난것


def 띠신호(d: dict, 훑기: dict = None) -> str:
    """상태 띠를 그릴 신호 하나. 없으면 빈 글."""
    fsm = ((훑기 or {}).get("FSM") or [{}])[0] or {}
    이름 = fsm.get("신호") or ""
    for n in 바뀌는것(d):
        if 이름 and _잎(n) == 이름:
            return n
    for n in 바뀌는것(d):
        if 이름 and 이름 in _잎(n):
            return n
    return ""


def 이름표(훑기: dict = None) -> dict:
    """상태 띠의 값 -> 이름. **스캔이 읽은 선언값에서 만든다.**

    선언값은 `훑기["로컬파라"]` 에 있다(`S_IDLE` -> `5'b00001`). 첫 판은
    `FSM[0]["값"]` 을 봤는데 **그런 칸이 없어서 이름표가 늘 비었다** --
    상태 띠가 `00001` 같은 생수로 찍혔을 자리다(실측 2026-09-23).
    """
    훑 = 훑기 or {}
    fsm = (훑.get("FSM") or [{}])[0] or {}
    상태 = set(fsm.get("상태후보") or [])
    표 = {}
    for 이름, 값 in (훑.get("로컬파라") or {}).items():
        if 상태 and 이름 not in 상태:
            continue
        v = str(값).strip()
        m = re.fullmatch(r"\d+'[bB]([01_]+)", v)
        if m:
            빗 = m.group(1).replace("_", "")
            # VCD 는 앞의 0 을 떼고 찍는다 -- 양쪽을 다 넣어 둔다
            표[빗] = 이름
            표[빗.lstrip("0") or "0"] = 이름
        elif re.fullmatch(r"\d+'[dD]?\d+", v) or v.isdigit():
            수 = int(re.sub(r"^\d+'[dD]?", "", v))
            표[bin(수)[2:]] = 이름
    return 표


if __name__ == "__main__":
    from house.dv import vcd as VCD
    from house import designs as DES
    from house import rtlscan as SCAN
    길 = next((a for a in sys.argv[1:] if a.endswith(".vcd")), None)
    키 = next((a for a in sys.argv[1:] if not a.startswith("-")
             and not a.endswith(".vcd")), None)
    d = VCD.읽기(길)
    훑 = None
    if 키:
        dd = DES.찾기(키)
        훑 = SCAN.훑기(dd.RTL, dd.top)
    s = 장면들(d, 훑)
    print(f"[scenes] {길}  산 신호 {s['산신호수']}개 · 으뜸클럭 {s['으뜸클럭']}")
    for k in ("fsm", "파이프", "게이팅", "cdc"):
        if k in s:
            print(f"\n  {k}  ({s[k]['어디서']})")
            for n in s[k]["신호"]:
                print("     ", n)
        else:
            print(f"\n  {k}  **안 냈다**")
    print("\n못 찾은 것:")
    for x in s["못찾은것"]:
        print("  · " + x)
