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
5. 무작위 자극뿐 아니라 **지시 시험**(경계값 · 최대/최소 · 포화 · 리셋 중 입력)을
   넣어라.
6. 타임아웃을 둬라 -- DUT 가 응답을 안 하면 영원히 매달리면 안 된다.
7. 커버리지는 `std::set` 으로 빈을 세고 퍼센트를 내라.

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

def 관문(설계, 벡터=400, 주기_ns=10.0) -> dict:
    """일곱 관문.  **하나라도 빨가면 통과가 아니다.**"""
    from house import sim as SIM
    from house import synth as SYN
    결과 = {"단계": [], "통과": False}

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
        if not 적기("4. 골든 모델 대조", 실패 == 0 and int(r.get("pass", 0)) > 0, 말,
                  r.get("pass")):
            결과["실행"] = r
            return 결과
        결과["실행"] = r
    except Exception as e:                                   # noqa: BLE001
        적기("4. 골든 모델 대조", False, f"{type(e).__name__}: {e}")
        return 결과

    # 5. 리셋 직후 확정 -- 다른 씨앗으로 한 번 더 (X 가 남으면 씨앗을 타는 수가 나온다)
    try:
        r2 = SIM.돌리기(None, seed=12345, txn=max(40, 벡터 // 8), 설계=설계)
        같 = (int(r2.get("fail", 0)) + int(r2.get("timeout", 0))) == 0
        적기("5. 다른 씨앗 재현", 같,
            f"seed=12345 에서 통과 {r2.get('pass')} · 실패 {r2.get('fail')}")
        if not 같:
            return 결과
    except Exception as e:                                   # noqa: BLE001
        적기("5. 다른 씨앗 재현", False, f"{type(e).__name__}: {e}")
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
        적기("7. STA 임계경로", 슬 is not None,
            f"주기 {주기_ns} ns 에서 최악 슬랙 {슬} ns (위반 {T.get('위반수')})", 슬)
        결과["sta"] = T
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

def 짓기(s, 키: str, 바퀴=3, 벡터=400, 주기_ns=10.0, 묻기=None, 등록=True) -> dict:
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
        g = 관문(d, 벡터=벡터, 주기_ns=주기_ns)
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
