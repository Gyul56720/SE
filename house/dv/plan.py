# -*- coding: utf-8 -*-
"""house/dv/plan -- **검증 시나리오를 회로에서 설계한다.**

## 왜 있나

사용자(2026-09-22): *"DV 의 기준모델은 범용일 수 없다"* 고 내가 적었더니 --
**"이건 DV agent 가 시나리오 설계하는 기능을 추가해야지."**

맞는 말이고, 내가 두 가지를 뭉쳐서 말했다. 갈라야 한다.

    기준모델(무엇이 옳은 값인가)   -- 회로마다 다르다. 스펙에서 나온다
    시나리오(무엇을 시험할 것인가) -- **회로에서 기계로 뽑을 수 있다**

두 번째는 범용이다. 팹리스의 검증 계획(verification plan / test plan)이 실제로
그렇게 만들어진다 -- 인터페이스를 보고 핸드셰이크 시나리오를 적고, 리셋을 보고
리셋 시나리오를 적고, 클럭 도메인을 보고 CDC 시나리오를 적는다. **사람이
창의적으로 지어내는 것이 아니라 인터페이스에서 따라 나온다.**

## 무엇에서 무엇을 뽑나 -- 근거 없는 시나리오는 안 만든다

    포트의 `*valid`/`*ready` 짝  -> 백프레셔 · valid 유지 · 리셋 중 valid
    포트의 `*last`               -> 최단/최장 패킷 · 연속 전송
    포트의 `*strb`/`*keep`       -> 부분 바이트 · 전체 바이트
    스캔의 리셋                   -> 리셋 직후 · 트래픽 중 리셋 · 비동기 해제
    스캔의 CDC 건넘               -> 클럭비 쓸기(느린쪽/빠른쪽)
    스캔의 FSM                   -> 모든 상태 방문 · 허용 안 된 전이
    포트의 데이터 폭              -> 0 · 1 · 최대 · 최소(부호) · 교대 패턴
    톱 파라미터(깊이류)           -> 가득참 · 비어있음 · 되돌이(wrap)
    스펙/포트의 오류 플래그        -> 세우는 조건 · 안 세우는 조건

**시나리오마다 `출처` 를 적는다.** 어느 포트, 어느 스캔 결과에서 나왔는지.
출처가 없으면 그것은 설계한 것이 아니라 지어낸 것이다.

## 커버리지 분모가 여기서 나온다

`gen.py` 의 테스트벤치 프롬프트가 *"세려던 빈 목록을 코드에 적어라 -- 분모를
자극에서 뽑으면 100% 가 공짜가 된다"* 고 한다. **그 목록이 이것이다.**

실행: python3 house/dv/plan.py [회로키]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent.parent
if str(저장소) not in sys.path:
    sys.path.insert(0, str(저장소))


def _폭수(폭) -> "int | None":
    """`[15:0]` · `16` · `[W-1:0]` -> 16 · 16 · None."""
    if isinstance(폭, int):
        return 폭
    t = str(폭 or "").strip()
    if t.isdigit():
        return int(t)
    m = re.fullmatch(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", t)
    if m:
        return abs(int(m.group(1)) - int(m.group(2))) + 1
    return None


# **깊이와 파이프라인 단수를 섞으면 안 된다.** 실측 2026-09-22: `STAGES=3` 과
# `CDC_STAGES=2` 에 "가득참 · 비어있음 · 되돌이" 시나리오가 붙었다. 파이프라인
# 단수에는 가득참도 되돌이도 없다 -- **그럴듯하지만 뜻이 없는 줄**이다.
_깊이말 = ("depth", "size", "entries", "fifo", "buf", "num", "count", "taps", "len")
_단수말 = ("stage", "stages", "pipe", "latency", "sync")


def 세우기(설계=None, 훑기=None, 스펙=None) -> dict:
    """회로에서 검증 시나리오를 뽑는다. {"시나리오": [...], "빈": [...], "출처없음": ...}."""
    from house import rtlscan as SCAN
    훑 = 훑기
    if 훑 is None and 설계 is not None:
        훑 = SCAN.훑기(getattr(설계, "RTL", []), getattr(설계, "top", ""))
    훑 = 훑 or {}
    포트 = list(훑.get("포트") or [])
    이름들 = [str(p.get("이름") or "") for p in 포트]
    낮 = {n.lower(): n for n in 이름들}

    시 = []

    def 적기(id, 이름, 왜, 어떻게, 빈, 출처):
        시.append({"id": id, "이름": 이름, "왜": 왜, "어떻게": 어떻게,
                  "빈": list(빈), "출처": 출처})

    # ---------------------------------------------------------- 핸드셰이크
    # **`valid`/`ready` 만 보면 안 된다.** 실측 2026-09-22: nsw_fir 의 포트는
    # `in_vld`/`in_rdy` · `out_vld` 다. `valid` 로만 찾으니 **핸드셰이크
    # 시나리오가 0개**로 나왔다 -- 핸드셰이크가 빤히 있는 회로에서.
    _v꼬 = ("valid", "vld", "_v")
    _r꼬 = ("ready", "rdy", "_r")
    짝 = []
    for n in 이름들:
        낮n = n.lower()
        꼬 = next((k for k in _v꼬 if 낮n.endswith(k)), None)
        if not 꼬:
            continue
        기 = n[:len(n) - len(꼬)]
        상대 = next((낮[(기 + k).lower()] for k in _r꼬 if (기 + k).lower() in 낮), None)
        짝.append((n, 상대, 기))
    for v, r, 기 in 짝:
        꼬 = 기.rstrip("_") or "if"
        if r:
            적기(f"hs_{꼬}_stall0", f"{꼬}: 백프레셔 없음",
               "스톨 경로를 한 번도 안 타면 그 경로는 검사된 적이 없다",
               f"`{r}` 를 항상 1 로 두고 연속 전송", [f"{꼬}_stall0"],
               f"포트 {v}/{r}")
            적기(f"hs_{꼬}_stall90", f"{꼬}: 백프레셔 최대",
               "받는 쪽이 거의 안 받을 때 보내는 쪽이 데이터를 잃지 않아야 한다",
               f"`{r}` 를 10% 확률로만 1 로", [f"{꼬}_stall_high"],
               f"포트 {v}/{r}")
            적기(f"hs_{꼬}_hold", f"{꼬}: valid 유지 규칙",
               "AXI 계열의 기본 규칙 -- valid 가 선 뒤 ready 가 올 때까지 "
               "데이터와 valid 가 변하면 안 된다. **프로토콜 위반은 0 이어야 한다**",
               f"`{v}` 가 1 인 동안 `{r}` 가 0 이면 데이터 불변을 모니터에서 센다",
               [f"{꼬}_hold_ok"], f"포트 {v}/{r}")
        else:
            적기(f"hs_{꼬}_noready", f"{꼬}: ready 없는 valid",
               "짝이 없는 valid 는 받는 쪽이 항상 받는다는 뜻이다 -- "
               "그 가정이 스펙에 적혀 있는지 사람이 봐야 한다",
               f"`{v}` 를 연속으로 세우고 놓치는 beat 가 없는지 센다",
               [f"{꼬}_noready"], f"포트 {v} (ready 짝 없음)")
        적기(f"hs_{꼬}_rstvalid", f"{꼬}: 리셋 중 valid=0",
           "리셋 중에 valid 가 서면 받는 쪽이 쓰레기를 받는다",
           f"리셋을 누른 채 `{v}` 가 0 인지 센다", [f"{꼬}_rst_valid0"],
           f"포트 {v} + 리셋")

    # ---------------------------------------------------------- 패킷 경계
    for n in 이름들:
        if n.lower().endswith(("last", "tlast")):
            기 = n[:-4].rstrip("_") or "pkt"
            적기(f"pkt_{기}_min", f"{기}: 한 beat 짜리 패킷",
               "가장 짧은 패킷은 first 와 last 가 같은 beat 다 -- 상태기가 "
               "가장 자주 틀리는 자리",
               f"`{n}` 를 첫 beat 에 세운다", [f"{기}_len1"], f"포트 {n}")
            적기(f"pkt_{기}_max", f"{기}: 가장 긴 패킷",
               "카운터 폭을 넘는 길이에서 되돌이(wrap)가 난다",
               "스펙의 최대 길이까지 이어서 보낸다", [f"{기}_len_max"], f"포트 {n}")
            적기(f"pkt_{기}_b2b", f"{기}: 연속 패킷",
               "패킷 사이에 쉬는 주기가 없으면 상태 복귀를 안 한 채 다음이 온다",
               "last 다음 beat 에 바로 다음 패킷을 시작한다",
               [f"{기}_back2back"], f"포트 {n}")
        if n.lower().endswith(("strb", "keep", "tstrb", "tkeep")):
            기 = n.rstrip("_")
            적기(f"strb_{기}", f"{기}: 부분 바이트",
               "모든 바이트가 유효한 경우만 보면 바이트 마스크 경로가 안 검사된다",
               f"`{n}` 를 전부 1 · 일부만 1 · 마지막 beat 에서 일부만 1",
               [f"{기}_all", f"{기}_partial"], f"포트 {n}")

    # ---------------------------------------------------------- 리셋
    리셋들 = list(훑.get("비동기리셋") or []) + list(훑.get("동기리셋") or [])
    for rst in 리셋들[:3]:
        적기(f"rst_{rst}_first", f"{rst}: 리셋 직후 첫 주기",
           "리셋이 안 덮는 레지스터는 첫 주기에 X 를 내보낸다",
           "리셋 해제 다음 주기부터 출력을 본다", [f"{rst}_first_cycle"],
           f"스캔: 리셋 {rst}")
        적기(f"rst_{rst}_mid", f"{rst}: 트래픽 한가운데 리셋",
           "**가장 자주 빠지는 시나리오다.** 전송 중에 리셋이 오면 절반만 쓴 "
           "상태가 남고, 그 위에 다음 전송이 쌓인다",
           "전송 도중 무작위 시점에 리셋을 넣고, 푼 뒤 정상 전송이 되는지 본다",
           [f"{rst}_mid_txn"], f"스캔: 리셋 {rst}")
    if 훑.get("비동기리셋"):
        적기("rst_async_release", "비동기 리셋의 해제",
           "비동기로 걸고 **동기로 푸는** 것이 규칙이다 -- 해제가 클럭 에지에 "
           "가까우면 준안정이 난다",
           "클럭 에지에 대해 해제 시점을 여러 군데로 옮겨 본다",
           ["rst_release_sweep"], f"스캔: 비동기리셋 {훑['비동기리셋']}")

    # ---------------------------------------------------------- CDC
    for x in (훑.get("CDC건넘") or [])[:6]:
        신호 = x["신호"]
        적기(f"cdc_{신호}", f"CDC: {신호} ({'/'.join(x['보내는곳'])} → {'/'.join(x['받는곳'])})",
           "두 클럭의 비가 바뀌면 건네는 쪽과 받는 쪽의 상대 속도가 바뀐다 -- "
           "한 비에서만 돌면 나머지는 검사된 적이 없다",
           "보내는 클럭을 받는 클럭보다 느리게 · 같게 · 빠르게 세 번",
           [f"cdc_{신호}_slow", f"cdc_{신호}_same", f"cdc_{신호}_fast"],
           f"스캔: CDC {신호}")

    # ---------------------------------------------------------- FSM
    for i, f in enumerate((훑.get("FSM") or [])[:3]):
        상태 = f.get("상태후보") or []
        적기(f"fsm{i}_all", f"FSM `{f['신호']}`: 모든 상태 방문",
           "안 가 본 상태는 검사된 적이 없다",
           "상태별 커버 빈을 두고 전부 채울 때까지 자극을 늘린다",
           [f"fsm{i}_{s}" for s in 상태[:12]] or [f"fsm{i}_visited"],
           f"스캔: case({f['신호']})")
        적기(f"fsm{i}_illegal", f"FSM `{f['신호']}`: 허용 안 된 입력",
           "정상 순서만 주면 `default` 가지가 안 검사된다",
           "각 상태에서 그 상태가 안 받는 입력을 넣고 죽지 않는지 본다",
           [f"fsm{i}_illegal"], f"스캔: case({f['신호']})")

    # ---------------------------------------------------------- 데이터 경계
    # **폭을 모른다고 데이터가 아닌 것은 아니다.** 실측 2026-09-22: `[DW-1:0]`
    # 처럼 파라미터로 된 폭은 `_폭수()` 가 None 을 내는데, `(None or 0) > 1` 이
    # 거짓이라 **데이터 포트가 전부 걸러졌다.** nsw_fir 의 `in_data`·`cfg_coef`
    # 가 다 빠져 데이터 경계 시나리오가 0개였다.
    def _데이터인가(p):
        낮n = str(p.get("이름") or "").lower()
        if not str(p.get("방향")).startswith("in"):
            return False
        if any(k in 낮n for k in ("valid", "vld", "ready", "rdy", "last", "keep",
                                  "strb", "clk", "rst", "reset", "scan_en",
                                  "start", "ack", "_we", "soft")):
            return False
        w = _폭수(p.get("폭"))
        return w is None or w > 1      # 모르는 폭도 데이터로 본다

    데이터 = [p for p in 포트 if _데이터인가(p)]
    for p in 데이터[:4]:
        n, w = p["이름"], _폭수(p.get("폭"))
        빈 = [f"{n}_zero", f"{n}_one", f"{n}_max", f"{n}_min_signed"]
        폭글 = f"{w}비트" if w else f"`{p.get('폭')}` 비트 (파라미터라 수는 빌드 때 정해진다)"
        적기(f"data_{n}", f"{n}: 경계값",
           "무작위는 최대/최소를 거의 안 뽑는다 -- 2^N 분의 몇이다. "
           "**지시 시험으로 넣어야 한다**",
           f"0 · 1 · 최대({폭글}) · 부호 있으면 최소 · 교대 패턴(0x55/0xAA)",
           빈, f"포트 {n} 폭 {p.get('폭')}")

    # ---------------------------------------------------------- 깊이/되돌이
    for k, v in (훑.get("톱파라미터") or {}).items():
        if not re.fullmatch(r"\d+", str(v).strip()):
            continue
        낮k = k.lower()
        if any(w in 낮k for w in _단수말):
            적기(f"pipe_{k}", f"{k}={v}: 파이프라인 채움과 비움",
               "단수를 정하는 파라미터는 **채우는 동안**과 **비우는 동안**에 "
               "틀린다 -- 첫 결과가 나오기 전과 마지막 결과가 나온 뒤",
               f"{v}개보다 짧은 전송(파이프가 안 참) · 정확히 {v}개 · "
               f"긴 전송 뒤 비움(flush)이 끝났는지",
               [f"{k}_underfill", f"{k}_exact", f"{k}_flush"],
               f"톱 파라미터 {k}={v} (단수)")
        elif any(w in 낮k for w in _깊이말):
            적기(f"depth_{k}", f"{k}={v}: 가득참 · 비어있음 · 되돌이",
               "깊이를 정하는 파라미터는 경계에서 틀린다 -- 하나 더 넣기, "
               "빈 상태에서 읽기, 포인터 되돌이",
               f"{v}개를 채우고 하나 더 · 빈 상태에서 읽기 · {v}*2 개를 흘려 되돌이",
               [f"{k}_full", f"{k}_empty", f"{k}_wrap"], f"톱 파라미터 {k}={v} (깊이)")

    # ---------------------------------------------------------- 오류 플래그
    오류포트 = [n for n in 이름들
             if any(w in n.lower() for w in ("err", "ovf", "overflow", "sticky",
                                             "fault", "underflow", "drop"))]
    스펙글 = ""
    if 스펙 is not None:
        스펙글 = " ".join(str(x) for x in (getattr(스펙, "모른다", []) or [])) + \
               " " + str(getattr(스펙, "요청", ""))
    if 오류포트 or re.search(r"overflow|sticky|error flag|오버플로|에러 플래그", 스펙글, re.I):
        적기("err_inject", "오류 플래그: 세우는 조건과 안 세우는 조건",
           "**플래그가 서는 것만 보면 절반만 검사한 것이다.** 안 서야 할 때 "
           "서지 않는 것까지 봐야 그 플래그가 검사된 것이다",
           "일부러 넘치게 만들어 플래그를 세우고, 정상 범위에서는 안 서는지 본다",
           ["err_set", "err_clear_stays_low"],
           f"포트 {오류포트}" if 오류포트 else "스펙 글에 오류 플래그가 있다")

    빈 = []
    for x in 시:
        for b in x["빈"]:
            if b not in 빈:
                빈.append(b)
    return {"됐나": bool(시), "시나리오": 시, "빈": 빈,
            "회로": getattr(설계, "키", ""), "포트수": len(포트),
            # **뽑을 수 없던 것을 적는다.** 빈 목록을 보고 "다 덮었다" 로 읽으면 안 된다.
            "못뽑는것": [
                "기능의 옳고 그름(골든 모델) -- 스펙에서 나온다",
                "성능 목표(처리율·지연)의 수 -- 스펙에서 나온다",
                "전원/클럭 게이팅 시나리오 -- UPF 가 있어야 한다",
                "보안·안전 요구(ISO 26262 따위) -- 인증 범위가 정해져야 한다",
            ]}


def 계획글(p: dict, 최대=40) -> str:
    """테스트벤치 프롬프트에 넣을 글. **모델이 이대로 짜야 한다.**"""
    if not p.get("됐나"):
        return ""
    줄 = ["아래는 **이 회로의 인터페이스에서 기계로 뽑은 검증 시나리오**다. "
         "하나씩 이름 붙은 함수로 구현하고, 각 시나리오가 제 커버 빈을 채워라."]
    for x in p["시나리오"][:최대]:
        줄.append(f"  · [{x['id']}] {x['이름']}\n"
                 f"      왜: {x['왜']}\n"
                 f"      어떻게: {x['어떻게']}\n"
                 f"      커버 빈: {', '.join(x['빈'])}")
    줄.append("")
    줄.append(f"**커버리지 분모는 이 빈 {len(p['빈'])}개다.** 코드에 그대로 적고 "
             f"`cov_pct = 채운빈/{len(p['빈'])}*100` 으로 내라. "
             f"자극에서 분모를 뽑으면 100% 가 공짜가 된다.")
    return "\n".join(줄)


def 요약글(p: dict) -> str:
    if not p.get("됐나"):
        return "시나리오를 못 뽑았다 -- 포트를 못 읽었다"
    갈래 = {}
    for x in p["시나리오"]:
        k = x["id"].split("_")[0]
        갈래[k] = 갈래.get(k, 0) + 1
    return (f"시나리오 {len(p['시나리오'])}개 · 커버 빈 {len(p['빈'])}개  ("
            + " · ".join(f"{k} {v}" for k, v in sorted(갈래.items())) + ")")


if __name__ == "__main__":
    from house import designs as DES
    키 = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    d = DES.찾기(키)
    p = 세우기(d)
    print(f"[plan] {d.키} ({d.이름})")
    print(요약글(p))
    print()
    for x in p["시나리오"]:
        print(f"  [{x['id']:22}] {x['이름']}")
        print(f"      출처: {x['출처']}   빈: {', '.join(x['빈'])}")
    print("\n못 뽑는 것:")
    for x in p["못뽑는것"]:
        print("  · " + x)
