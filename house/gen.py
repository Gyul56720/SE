# -*- coding: utf-8 -*-
"""house/gen -- 스펙에서 RTL 과 테스트벤치를 짓고, **관문으로 붙든다.**

## 이 파일의 가치는 생성이 아니라 검사다

모델에게 SystemVerilog 를 시키면 그럴듯한 것이 나온다. 그럴듯한 것은 아무것도
증명하지 않는다 -- 이 저장소가 반복해서 진 자리가 정확히 거기다
(CLAUDE.md: "검사하지 않은 초록불이 검사한 빨간불보다 나쁘다").

그래서 생성물은 **관문 일곱 개**를 지나야 등록된다:

    1. 문법        verilator --lint-only -Wall      (경고도 본다)
    2. 두번째도구  iverilog -g2012 엘라보레이트     (한 도구만 믿지 않는다)
    3. 빌드        verilator --cc + C++ 컴파일
    4. 골든대조    무작위 벡터 N개, 기준모델과 값 비교
    5. 초기화      리셋 직후 출력이 확정인가 (X 전파 없나)
    6. 합성        yosys 로 셀에 매핑되나 (래치 안 생기나)
    7. STA         임계경로가 목표 주기 안에 드나

**하나라도 빨가면 등록하지 않는다.** 대신 그 오류를 모델에 돌려주고 다시 시킨다
(최대 `바퀴`회). 고쳐지지 않으면 **"못 지었다" 로 보고한다** -- 반쯤 된 RTL 을
등록해서 다음 단계가 그 위에 쌓이게 두지 않는다.

## 골든 모델은 RTL 을 못 본다

같은 모델이 RTL 과 기준모델을 다 쓰면 **같은 오해를 두 번 한다** -- 그러면 둘이
사이좋게 틀리고 대조는 통과한다. 그래서 기준모델은 **스펙만 보고** 따로 부른다
(`_TB짓기` 에 RTL 을 안 넘긴다). 이것이 이 파일에서 가장 중요한 한 줄이다.

그래도 남는 구멍: 두 호출이 같은 모델이라 **스펙의 애매함을 같은 쪽으로 푼다**.
그것은 코드로 못 막는다 -- 보고서에 그렇게 적는다.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
생성방 = 뿌리 / "gen"


# ------------------------------------------------------------------ 프롬프트

RTL프롬프트 = """너는 디지털 RTL 설계자다. 아래 스펙대로 **합성 가능한 SystemVerilog** 를 써라.

스펙(JSON):
{스펙}

{되먹임}

반드시 지켜라:
1. **톱 모듈 이름은 `{top}`** 이다. 필요한 하위 모듈은 같은 파일에 써라.
2. **합성 가능한 것만.** initial · delay(#) · $display · real · 동적 배열 금지.
   (테스트벤치가 아니다. 칩에 들어갈 코드다.)
3. **리셋은 비동기 assert · 동기 deassert**, active-low `rst_n`. 모든 플롭이
   리셋에서 확정 값을 가져야 한다 -- X 가 남으면 안 된다.
4. **래치를 만들지 마라.** 조합 always 는 모든 갈래에서 값을 준다(default 를 둬라).
5. 폭을 맞춰라. 비교·대입에서 암묵 확장에 기대지 마라.
6. 파라미터로 치수를 정하라(`parameter`). 하드코딩한 상수를 흩뿌리지 마라.
7. 클럭이 둘 이상이면 건너는 신호마다 **2단 동기화기**를 둬라. 다비트가 건너면
   그레이 코드나 핸드셰이크를 써라.
8. 전력이 목표면 **클럭 게이팅**을 쓰되, 래치+AND 꼴(ICG)로 명시하고 스캔용
   `test_en` 우회로를 둬라.
9. 주석은 한국어로, **왜 그렇게 했는지**를 적어라. 무엇을 하는지는 코드가 말한다.

SystemVerilog 코드만 출력해라. ``` 울타리도 설명도 쓰지 마라.
"""

TB프롬프트 = """너는 검증 엔지니어다. 아래 스펙대로 **C++ 테스트벤치**를 써라.
verilator 로 컴파일된 DUT 를 구동한다.

스펙(JSON):
{스펙}

DUT 의 포트 (이것만 존재한다. 다른 신호를 건드리지 마라):
{포트}

{되먹임}

**너는 RTL 구현을 보지 못한다. 그것이 의도다.** 기준모델(golden model)은 스펙만
보고 따로 적어야 한다 -- 구현을 보고 적으면 같은 실수를 두 번 하고, 대조가
통과해도 아무것도 증명하지 못한다.

반드시 지켜라:
1. `#include "V{top}.h"` 와 `#include "verilated.h"` 를 써라. VCD 를 쓸 수 있게
   `#include "verilated_vcd_c.h"` 도 넣고 `--vcd <파일>` 인자를 받아라.
2. 구조를 UVM 꼴로 갈라라: 시퀀스(자극 생성) · 드라이버(핀 구동) ·
   **모니터(핀만 읽는다 -- 드라이버의 의도를 쓰지 마라)** · 기준모델 ·
   스코어보드(판정은 여기서만) · 커버리지.
3. 인자: `--seed N --txn N --cap N --vcd 파일`. 기본값을 둬라.
4. **마지막 줄에 JSON 한 줄**을 찍어라(다른 줄은 무엇을 찍든 상관없다):
   {{"pass":N,"fail":N,"timeout":N,"cycles":N,"cov_pct":F,"errs":["..."]}}
5. 타임아웃을 둬라 -- DUT 가 응답을 안 하면 영원히 매달리면 안 된다.

**아래는 팹리스 VLSI(AMD · Xilinx · Broadcom 급) 의 IP 검증이 서명 전에 요구하는
것이다. 하나씩 다 넣어라 -- 이 회로에 해당하는 것만.**

6. **지시 시험(directed)** 을 이름 붙은 함수로 따로 써라. 무작위는 이것들을
   웬만해선 안 밟는다.
     · 경계값: 0 · 1 · 최대 · 최대-1 · 최소(부호 있으면 음수 최대)
     · 포화/넘침: 누산기·카운터가 끝까지 찬 상태
     · 리셋 중 입력 · 리셋 직후 첫 주기 · 트래픽 한가운데서 리셋
     · 연속 전송(back-to-back) 과 한 칸 띄운 전송
     · 가장 짧은 패킷과 가장 긴 패킷
7. **백프레셔(backpressure).** 출력 `ready` 가 있으면 무작위로 내려라.
   `--stall P` (0~100, 기본 20) 로 받고, `--stall 0` · `--stall 90` 둘 다 돌 수
   있어야 한다. **ready 를 항상 1 로 두면 스톨 경로를 한 번도 안 본다.**
8. **프로토콜 검사.** 핸드셰이크가 있으면 모니터에서 규칙을 세고 어기면 센다.
     · `valid` 가 올라간 뒤 `ready` 가 올 때까지 **데이터와 valid 가 안 변한다**
     · 리셋 중에는 `valid` 가 0 이다
     · `last`/`keep` 같은 곁신호가 있으면 그 규칙도
   어긴 횟수를 JSON 의 `"proto"` 로 내라. **0 이 아니면 그것은 실패다.**
9. **에러 주입.** 스펙에 오류 플래그(overflow · sticky · error)가 있으면
   **일부러 그 조건을 만들어** 플래그가 서는지 보고, 안 세우는 조건에서는 안 서는지도
   봐라. 둘 다 봐야 그 플래그가 검사된 것이다.
10. **커버리지는 이름 붙인 빈으로** 세라. `std::set<std::string>` 에 넣고, 빈 이름은
   무엇을 덮었는지 알아볼 수 있게 (`"len=1"` · `"stall_high"` · `"reset_mid_txn"`).
   `cov_pct = 채운빈 / 세려던빈 * 100`. **세려던 빈 목록을 코드에 적어라** --
   분모를 자극에서 뽑으면 100% 가 공짜가 된다.
11. 인자에 `--stall P` 를 더해라. 기본값 20.

**스코어보드가 실제로 물어야 한다.** 이 테스트벤치는 나중에 **자해 검사**를 받는다 --
RTL 에 일부러 버그(`+`→`-`, `==`→`!=`, 상수 ±1)를 심고 네가 빨개지는지 센다.
변이 점수 {변이문턱:.0%} 를 못 넘으면 이 회로는 등록되지 않는다. **눈감아 주는
비교(`if (exp != got) continue;` 같은 것)를 쓰지 마라.**

C++ 코드만 출력해라. ``` 울타리도 설명도 쓰지 마라.
"""


def _묻기기본(글: str, pool_id="house_gen") -> str:
    import sys
    sys.path.insert(0, str(저장소 / "orchestrator"))
    import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 가 없다")
    return llm_pool.call(pool, 글, pool_id=pool_id)[0]


def _코드뽑기(글: str, 갈래="sv") -> str:
    """모델이 ``` 울타리를 쳐도 벗겨 낸다."""
    t = (글 or "").strip()
    if "```" in t:
        조각 = t.split("```")
        골 = []
        for c in 조각[1::2]:
            c = c.strip()
            for 머리 in ("systemverilog", "verilog", "sv", "cpp", "c++", "c"):
                if c.lower().startswith(머리):
                    c = c[len(머리):].lstrip()
                    break
            골.append(c)
        if 골:
            return max(골, key=len).strip() + "\n"
    return t + "\n"


def 포트뽑기(sv: str, top: str) -> list:
    """RTL 에서 톱 모듈의 포트를 읽는다.  **테스트벤치가 이것만 보게 한다.**

    구현을 안 보이면서 인터페이스는 줘야 하므로, 여기서 포트만 잘라 낸다.
    """
    m = re.search(rf"\bmodule\s+{re.escape(top)}\b(.*?);", sv, re.S)
    if not m:
        return []
    머리 = m.group(1)
    머리 = re.sub(r"#\s*\(.*?\)", "", 머리, flags=re.S)      # 파라미터 목록 제거
    안 = 머리[머리.find("(") + 1:머리.rfind(")")] if "(" in 머리 else ""
    안 = re.sub(r"//[^\n]*", "", 안)
    out = []
    for 조각 in 안.split(","):
        조각 = " ".join(조각.split())
        if not 조각:
            continue
        방향 = "input" if 조각.startswith("input") else (
            "output" if 조각.startswith("output") else (
                "inout" if 조각.startswith("inout") else None))
        if 방향 is None:
            continue
        w = 1
        b = re.search(r"\[\s*([^\]:]+)\s*:\s*([^\]]+)\s*\]", 조각)
        if b:
            w = f"[{b.group(1)}:{b.group(2)}]"
        이름 = 조각.split()[-1]
        out.append({"이름": 이름, "방향": 방향, "폭": w})
    return out


# ------------------------------------------------------------------ 관문

# **보증의 문턱.** 팹리스 VLSI 의 IP 사인오프가 서명 전에 요구하는 것을 수로 옮긴 것이다.
#
# 사용자(2026-09-22): "강건성을 위해 더 많은 시나리오로 더 치밀한 검증을 통한 보증을
# 가능케 해줘. 기준은 AMD나 xillinx, 브로드컴 같은 펩리스 VLSI 기준으로."
#
# 그 업계가 커버리지만으로 서명하지 않는 까닭이 있다. **커버리지는 "자극이 거기를
# 지나갔다" 는 말이지 "검사기가 틀린 값을 알아본다" 는 말이 아니다.** 그래서 둘을
# 같이 잰다 -- 커버리지(자극이 닿았나)와 변이 점수(닿았을 때 무나).
기본문턱 = {
    "커버리지_pct": 85.0,    # 기능 커버리지. 100 은 생성 회로에 가혹하므로 85 에서 시작한다
    "회귀씨앗": 16,          # 씨앗 둘은 회귀가 아니다. 씨앗을 타는 버그가 그대로 통과한다
    "변이점수": 0.60,        # fault grading. 이 밑이면 테스트벤치가 절반도 안 문다
    # **표본이 적으면 점수가 아니라 잡음이다.** 실측 2026-09-22 (같은 nsw_fir,
    # 같은 테스트벤치): 변이 14개로 재면 69%, 6개로 재면 20% 가 나왔다.
    # 6개짜리 수를 문턱에 대면 **테스트벤치를 한 줄도 안 고쳤는데 초록과 빨강이
    # 오간다** -- 그런 관문은 없느니만 못하다. 빠른 길에서도 12 밑으로 안 내린다.
    "변이수": 20,
}


def 관문(설계, 벡터=400, 주기_ns=10.0, 문턱=None, 빠르게=False) -> dict:
    """열 관문.  **하나라도 빨가면 통과가 아니다.**

    앞의 일곱은 *지어졌는가* 를 본다. 뒤에 붙은 셋은 **보증되는가** 를 본다 --
    자극이 닿았나(커버리지) · 씨앗을 안 타나(회귀) · X 가 안 남나 · 그리고
    **검사기가 정말로 무나**(변이 점수).
    """
    from house import sim as SIM
    from house import synth as SYN
    문턱 = {**기본문턱, **(문턱 or {})}
    if 빠르게:
        문턱 = {**문턱, "회귀씨앗": 4, "변이수": 12}
    결과 = {"단계": [], "통과": False, "문턱": 문턱}

    def 적기(이름, 됐나, 말="", 수=None):
        결과["단계"].append({"관문": 이름, "됐나": bool(됐나), "말": str(말)[:600],
                          "수": 수})
        return 됐나

    # 1. lint
    try:
        L = SIM.lint(설계=설계)
        if not 적기("1. verilator lint -Wall", L["rc"] == 0 and L["전체"] == 0,
                  f"경고 {L['전체']}개 {L['종류']}\n" + L["글"][-1200:], L["전체"]):
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("1. verilator lint -Wall", False, f"{type(e).__name__}: {e}")
        return 결과

    # 2. 두 번째 도구
    try:
        I = SIM.iverilog_확인(설계=설계)
        if not 적기("2. iverilog 엘라보레이트", I["됐나"], I["글"]):
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("2. iverilog 엘라보레이트", False, f"{type(e).__name__}: {e}")
        return 결과

    # 3. 빌드
    try:
        SIM.빌드(설계=설계)
        적기("3. verilator 빌드 + C++ 컴파일", True, "실행 파일 생김")
    except Exception as e:                                   # noqa: BLE001
        적기("3. verilator 빌드 + C++ 컴파일", False, f"{type(e).__name__}: {e}")
        return 결과

    # 4. 골든 대조
    try:
        r = SIM.돌리기(None, seed=1, txn=벡터, 설계=설계)
        실패 = int(r.get("fail", 0)) + int(r.get("timeout", 0))
        말 = (f"통과 {r.get('pass')} · 실패 {r.get('fail')} · 타임아웃 {r.get('timeout')}"
             f" · 커버리지 {r.get('cov_pct')}\n"
             + "\n".join(str(x) for x in (r.get("errs") or [])[:6]))
        결과["실행"] = r
        if not 적기("4. 골든 모델 대조", 실패 == 0 and int(r.get("pass", 0)) > 0, 말,
                  r.get("pass")):
            return 결과
        # **커버리지에 문턱을 둔다.** 전에는 퍼센트를 찍기만 했다 -- 30% 여도
        # 초록이었다. 자극이 안 닿은 자리는 검사한 적이 없는 자리다.
        #
        # **닫기(closure)는 긴 실행으로 잰다.** 짧은 실행의 퍼센트는 자극이
        # 모자란 것인지 테스트벤치가 못 닿는 것인지 안 가른다. 실측 2026-09-22
        # (nsw_fir): txn 100 -> 75.0% · 300 -> 76.9% · 1000 -> 78.85% ·
        # 3000 -> 78.85% · 10000 -> 78.85%. **1000 에서 포화한다** -- 남은 빈은
        # 벡터를 아무리 늘려도 안 닿고, **지시 시험으로만** 닫힌다. 그래서 두
        # 점을 재서 포화했는지까지 같이 적는다.
        닫기n = max(1000, 벡터 * 4)
        c1 = SIM.돌리기(None, seed=99, txn=닫기n, 설계=설계, 초=900)
        c2 = SIM.돌리기(None, seed=99, txn=닫기n * 3, 설계=설계, 초=900)
        cov = float(c2.get("cov_pct") or 0.0)
        포화 = abs(cov - float(c1.get("cov_pct") or 0.0)) < 0.01
        말 = (f"커버리지 {cov}% (자극 {닫기n * 3}개). "
             + (f"자극 {닫기n} 에서도 같다 -- **포화했다.** 남은 빈은 벡터를 "
                f"늘려도 안 닿는다. **지시 시험(경계·포화·리셋 중·백프레셔)으로만 "
                f"닫힌다.**" if 포화 else
                f"자극 {닫기n} 에서는 {c1.get('cov_pct')}% 였다 -- 아직 오르는 중이다."))
        결과["커버리지"] = {"pct": cov, "포화": 포화, "자극": 닫기n * 3}
        if not 적기(f"4b. 기능 커버리지 ≥ {문턱['커버리지_pct']}%",
                  cov >= 문턱["커버리지_pct"], 말, cov):
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("4. 골든 모델 대조", False, f"{type(e).__name__}: {e}")
        return 결과

    # 5. **제약 랜덤 회귀.** 씨앗 둘은 회귀가 아니다 -- 씨앗을 타는 버그가 그대로
    #    통과한다. 업계의 회귀는 밤새 수백 씨앗을 돈다. 여기서는 N 씨앗을 돌고
    #    **몇 번째 씨앗에서 깨졌는지**를 적는다(재현에 그 수가 필요하다).
    try:
        씨앗들 = [12345 + i * 7919 for i in range(int(문턱["회귀씨앗"]))]
        깬것, 총통과 = [], 0
        for s0 in 씨앗들:
            r2 = SIM.돌리기(None, seed=s0, txn=max(40, 벡터 // 4), 설계=설계)
            총통과 += int(r2.get("pass", 0))
            if int(r2.get("fail", 0)) + int(r2.get("timeout", 0)) > 0:
                깬것.append((s0, r2.get("fail"), r2.get("timeout"),
                           (r2.get("errs") or [""])[:1]))
        말 = (f"씨앗 {len(씨앗들)}개 · 통과 {총통과} · 깨진 씨앗 {len(깬것)}개"
             + ("".join(f"\n  seed={a} fail={b} timeout={c} {d}" for a, b, c, d in 깬것[:4])))
        if not 적기(f"5. 제약 랜덤 회귀 ({len(씨앗들)} 씨앗)", not 깬것, 말, len(씨앗들)):
            결과["회귀깬것"] = 깬것
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("5. 제약 랜덤 회귀", False, f"{type(e).__name__}: {e}")
        return 결과

    # 5b. **X-전파 · 리셋 확정.** 2-state 로만 돌면 미초기화 레지스터가 0 으로
    #     보여 조용히 지나간다. `--x-assign unique --x-initial unique` 는 X 자리를
    #     **씨앗마다 다른 값**으로 채운다 -- 리셋이 안 덮는 자리가 있으면 여기서 갈린다.
    try:
        Xs = [SIM.돌리기(None, seed=s0, txn=max(40, 벡터 // 4), 설계=설계,
                       깃발=["--x-assign", "unique", "--x-initial", "unique"])
              for s0 in (1, 2, 3)]
        X깨짐 = [x for x in Xs if int(x.get("fail", 0)) + int(x.get("timeout", 0)) > 0]
        적기("5b. X-전파 · 리셋 확정", not X깨짐,
            f"`--x-assign unique --x-initial unique` 로 씨앗 3개 · "
            f"깨진 것 {len(X깨짐)}개 -- 리셋이 안 덮는 레지스터가 있으면 여기서 갈린다")
        if X깨짐:
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("5b. X-전파 · 리셋 확정", False, f"{type(e).__name__}: {e}")
        return 결과

    # 5c. **자해 검사(fault grading).** 여기까지의 초록은 두 가지 중 하나다 --
    #     설계가 옳거나, **검사기가 아무것도 안 보거나.** 그 둘을 가르는 칸이다.
    #     설계를 일부러 망가뜨리고 테스트벤치가 빨개지는지 센다.
    try:
        from house.dv import automut as MUT
        mr = MUT.한바퀴(설계, 최대=int(문턱["변이수"]), txn=max(60, 벡터 // 4))
        점 = mr.get("점수")
        됐 = bool(mr.get("됐나")) and 점 is not None and 점 >= 문턱["변이점수"]
        적기(f"5c. 자해 검사 (변이 점수 ≥ {문턱['변이점수']:.0%})", 됐,
            MUT.요약글(mr), 점)
        결과["변이"] = mr
        if not 됐:
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("5c. 자해 검사", False, f"{type(e).__name__}: {e}")
        return 결과

    # 6. 합성
    try:
        S = SYN.합성(설계=설계)
        래치 = S.get("셀종류", {}).get("LATX1", 0) if isinstance(S.get("셀종류"), dict) else 0
        말 = (f"셀 {S.get('셀수')}개 · 면적 {S.get('면적_um2')} µm² · 래치 {래치}개\n"
             + str(S.get("까닭", ""))[:800])
        if not 적기("6. yosys 합성", S.get("됐나"), 말, S.get("셀수")):
            return 결과
        결과["합성"] = S
    except Exception as e:                                   # noqa: BLE001
        적기("6. yosys 합성", False, f"{type(e).__name__}: {e}")
        return 결과

    # 7. STA
    try:
        T = SYN.sta(결과["합성"], 주기=주기_ns)
        슬 = T.get("최악슬랙_ns")
        결과["sta"] = T
        # **수를 찍기만 하던 자리였다.** 실측 2026-09-22: nsw_fir 이 10 ns 에서
        # 최악 슬랙 **-3.15 ns** 인데 이 관문이 초록이었다 -- `슬 is not None`
        # 만 봤기 때문이다. 타이밍이 안 닫힌 RTL 위에 면적·전력 수를 쌓으면
        # 그 수가 전부 뜻이 없다. 문턱 없는 수는 관문이 아니다.
        적기("7. STA 임계경로 (슬랙 ≥ 0)", 슬 is not None and float(슬) >= 0.0,
            f"주기 {주기_ns} ns 에서 최악 슬랙 {슬} ns (위반 {T.get('위반수')})"
            + ("" if (슬 is not None and float(슬) >= 0.0) else
               f" -- **타이밍이 안 닫혔다.** 파이프라인을 더 끊거나 목표 주기를 "
               f"{주기_ns - float(슬):.2f} ns 이상으로 잡아야 한다"), 슬)
    except Exception as e:                                   # noqa: BLE001
        적기("7. STA 임계경로", False, f"{type(e).__name__}: {e}")

    결과["통과"] = all(x["됐나"] for x in 결과["단계"])
    return 결과


def _되먹임글(결과: dict) -> str:
    """빨간 관문을 모델에게 돌려줄 글로.  **오류 원문을 그대로 준다.**"""
    빨 = [x for x in (결과.get("단계") or []) if not x["됐나"]]
    if not 빨:
        return ""
    x = 빨[0]
    return (f"\n[직전 시도가 실패했다 -- 고쳐라]\n관문: {x['관문']}\n"
            f"도구가 낸 말:\n{x['말']}\n"
            "같은 실수를 반복하지 마라. 위 오류를 **직접** 고친 코드를 내라.\n")


# ------------------------------------------------------------------ 짓기

def 짓기(s, 키: str, 바퀴=3, 벡터=400, 주기_ns=10.0, 묻기=None, 등록=True,
        문턱=None, 빠르게=False) -> dict:
    """스펙에서 회로를 짓는다.  관문을 통과할 때만 등록한다.

    `묻기(글, pool_id)` 를 갈아 끼우면 모델 없이 검사할 수 있다.
    """
    from house import designs as DES
    묻기 = 묻기 or _묻기기본
    top = (s.이름 or f"nsw_{키}").strip().replace("-", "_")
    방 = 생성방 / 키
    방.mkdir(parents=True, exist_ok=True)
    sv길, tb길 = 방 / f"{top}.sv", 방 / f"tb_{top}.cpp"
    스펙글 = json.dumps(s.사전(), ensure_ascii=False, indent=1)

    이력 = []
    되먹임 = ""
    for 바 in range(1, 바퀴 + 1):
        t0 = time.time()
        한바퀴 = {"바퀴": 바}
        # --- RTL ---
        try:
            sv = _코드뽑기(묻기(RTL프롬프트.format(스펙=스펙글, top=top, 되먹임=되먹임),
                           "house_gen_rtl"), "sv")
        except Exception as e:                               # noqa: BLE001
            한바퀴["오류"] = f"RTL 생성 실패: {type(e).__name__}: {e}"[:200]
            이력.append(한바퀴)
            break
        sv길.write_text(sv, encoding="utf-8")
        한바퀴["RTL_줄"] = sv.count("\n")

        # --- TB: **RTL 을 안 보여 준다.** 포트만 준다 ---
        포트 = 포트뽑기(sv, top)
        한바퀴["포트수"] = len(포트)
        if not 포트:
            한바퀴["오류"] = f"톱 모듈 {top} 의 포트를 못 읽었다 -- 모듈 이름이 틀렸을 수 있다"
            이력.append(한바퀴)
            되먹임 = (f"\n[직전 시도 실패] 톱 모듈 이름이 `{top}` 이어야 하는데 "
                   f"그 모듈을 못 찾았다. 정확히 `module {top} (...)` 으로 써라.\n")
            continue
        try:
            tb = _코드뽑기(묻기(TB프롬프트.format(
                스펙=스펙글, top=top,
                포트=json.dumps(포트, ensure_ascii=False, indent=1),
                변이문턱=기본문턱["변이점수"],
                되먹임=되먹임), "house_gen_tb"), "cpp")
        except Exception as e:                               # noqa: BLE001
            한바퀴["오류"] = f"TB 생성 실패: {type(e).__name__}: {e}"[:200]
            이력.append(한바퀴)
            break
        tb길.write_text(tb, encoding="utf-8")
        한바퀴["TB_줄"] = tb.count("\n")

        # --- 관문 ---
        d = DES.설계(키=키, 이름=s.한줄 or top, top=top, RTL=[sv길], TB=tb길,
                   한줄=s.한줄 or (s.요청 or "")[:120],
                   출처=f"house/gen.py 가 요청에서 지음: {(s.요청 or '')[:80]}")
        g = 관문(d, 벡터=벡터, 주기_ns=주기_ns, 문턱=문턱, 빠르게=빠르게)
        한바퀴["관문"] = g["단계"]
        한바퀴["통과"] = g["통과"]
        한바퀴["초"] = round(time.time() - t0, 1)
        이력.append(한바퀴)
        if g["통과"]:
            if 등록:
                DES.등록(d)
            return {"됐나": True, "설계": d, "바퀴수": 바, "이력": 이력,
                    "관문": g, "RTL": str(sv길), "TB": str(tb길), "top": top}
        되먹임 = _되먹임글(g)

    return {"됐나": False, "바퀴수": len(이력), "이력": 이력, "top": top,
            "RTL": str(sv길) if sv길.exists() else None,
            "TB": str(tb길) if tb길.exists() else None,
            "까닭": "관문을 통과하지 못했다 -- 반쯤 된 RTL 은 등록하지 않는다"}


def 쓸수있나() -> dict:
    """**짓기를 시키기 전에 무엇이 없는지 말한다.**"""
    없 = []
    for c in ("verilator", "iverilog", "yosys", "g++"):
        if not shutil.which(c):
            없.append(c)
    키 = 0
    try:
        import sys
        sys.path.insert(0, str(저장소 / "orchestrator"))
        import llm_pool
        키 = len(llm_pool.api_keys())
    except Exception:                                        # noqa: BLE001
        pass
    return {"도구없음": 없, "모델키": 키,
            "됨": (not 없) and 키 > 0,
            "말": ("도구가 없다: " + ", ".join(없)) if 없 else
                 ("GEMINI_API_KEY 가 없다 -- 이 컨테이너에서는 생성을 못 한다"
                  if 키 == 0 else "쓸 수 있다")}
