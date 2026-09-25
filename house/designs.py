# -*- coding: utf-8 -*-
"""house/designs -- **설계 등록부.** 이 회사가 맡은 회로들.

지금까지 `nsw_fir` 가 경로에 박혀 있었다. 한 회로만 맡는 설계 하우스는 하우스가
아니라 그 회로다. 그래서 회로를 **인자**로 뺀다 -- 합성 · 시뮬 · DFT · PD 는
회로를 모르고, 회로가 무엇인지는 여기서만 안다.

## 새 회로를 등록하려면

    설계(
        키="uart", 이름="NSW-UART",
        RTL=[뿌리/"rtl"/"src"/"nsw_uart.sv"], top="nsw_uart",
        TB=뿌리/"dv"/"tb_nsw_uart.cpp",
        파라={"CLK_HZ": 100_000_000, "BAUD": 115200},
        SDC=..., UPF=...,
    )

**RTL 과 테스트벤치는 회로마다 새로 써야 한다** -- 정답이 회로마다 다르기 때문이다.
나머지(합성 · STA · 27코너 · UPF 점검 · 스캔 · ATPG · BIST · 플로어플랜 · 배치 ·
CTS · 배선 · GDSII · 보고서 · 그림)는 넷리스트만 있으면 돌아간다.

## `등록()` 으로 실행 중에 더할 수 있다

`house/gen.py` 가 자연어 요청에서 회로를 지어낼 때 그 회로를 여기 등록한다.
등록부는 **파일로 남는다**(`house/designs.json`) -- 다음 세션이 같은 회로를
다시 부를 수 있어야 하기 때문이다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
등록부길 = 뿌리 / "designs.json"


@dataclass
class 설계:
    키: str                                  # !회사 검증 <키>
    이름: str
    top: str
    RTL: list                                # [Path] -- verilator/yosys 가 읽는 순서
    TB: "Path | None" = None                 # C++ 테스트벤치 (없으면 DV 를 못 돈다)
    파라: dict = field(default_factory=dict)  # 기본 파라미터 (-G)
    SDC: "Path | None" = None
    UPF: "Path | None" = None
    한줄: str = ""
    클럭: dict = field(default_factory=dict)  # {"clk": 주기_ns, ...}
    # **이 회로에서 흔들어야 뜻이 있는 파라미터.** {이름: [값들]}
    #
    # 실측 2026-09-25: RTL 직무의 스윕은 "수 파라미터를 반/두 배로 흔든다" 는
    # 어림으로 돈다. 그런데 `MODE` 처럼 **갈래를 고르는 파라미터**에는 그 어림이
    # 뜻이 없다 -- MODE=1 을 두 배 해서 MODE=2 가 나왔고, RTL 이 `MODE != 0` 로
    # 가르므로 **같은 갈래 두 판**을 돌고는 "MODE 를 흔들어 면적 1,528,910~
    # 1,584,717 µm²" 라고 적었다. MODE=0(이진법)은 한 번도 안 돌았다.
    # 회로가 직접 말하게 한다.
    스윕: dict = field(default_factory=dict)
    출처: str = "손으로 쓴 것"                 # 또는 "gen.py 가 <요청> 에서 지음"
    메모: str = ""

    # -- 이 회로로 무엇까지 할 수 있나 --------------------------------
    def 할수있는것(self) -> dict:
        """**없는 것을 있다고 하지 않는다.** 보고서 머리에 그대로 적는다."""
        있 = all(Path(p).exists() for p in self.RTL)
        return {
            "RTL": 있,
            "DV": 있 and bool(self.TB) and Path(self.TB).exists(),
            "합성": 있,
            "STA": 있,
            "SDC": bool(self.SDC) and Path(self.SDC).exists(),
            "UPF": bool(self.UPF) and Path(self.UPF).exists(),
            "DFT": 있,
            "PD": 있,
        }

    def 모자란것(self) -> list:
        ㄱ = self.할수있는것()
        말 = {"RTL": "RTL 소스가 없다", "DV": "테스트벤치가 없다 -- 검증을 못 돈다",
             "SDC": "SDC 가 없다 -- STA 가 기본 주기로만 돈다",
             "UPF": "UPF 가 없다 -- 저전력 점검을 건너뛴다"}
        return [말[k] for k in ("RTL", "DV", "SDC", "UPF") if not ㄱ[k]]

    def 사전(self) -> dict:
        return {"키": self.키, "이름": self.이름, "top": self.top,
                "RTL": [str(p) for p in self.RTL],
                "TB": str(self.TB) if self.TB else None,
                "파라": self.파라,
                "SDC": str(self.SDC) if self.SDC else None,
                "UPF": str(self.UPF) if self.UPF else None,
                "한줄": self.한줄, "클럭": self.클럭, "출처": self.출처,
                "메모": self.메모, "스윕": self.스윕}

    @staticmethod
    def 사전에서(d: dict) -> "설계":
        return 설계(키=d["키"], 이름=d["이름"], top=d["top"],
                  RTL=[Path(p) for p in d["RTL"]],
                  TB=Path(d["TB"]) if d.get("TB") else None,
                  파라=d.get("파라") or {},
                  SDC=Path(d["SDC"]) if d.get("SDC") else None,
                  UPF=Path(d["UPF"]) if d.get("UPF") else None,
                  한줄=d.get("한줄", ""), 클럭=d.get("클럭") or {},
                  출처=d.get("출처", ""), 메모=d.get("메모", ""),
                  스윕=d.get("스윕") or {})


# ------------------------------------------------------------------ 붙박이

NSW_FIR = 설계(
    키="fir", 이름="NSW-FIR v1.0", top="nsw_fir",
    RTL=[뿌리 / "rtl" / "src" / "nsw_fir.sv"],
    TB=뿌리 / "dv" / "tb_nsw_fir.cpp",
    파라={},
    SDC=뿌리 / "syn" / "nsw_fir.sdc",
    UPF=뿌리 / "syn" / "nsw_fir.upf",
    한줄="파라미터로 치수가 정해지는 8탭 FIR/MAC 가속기 -- 원핫 FSM · 3단 파이프라인 · "
      "ICG 클럭게이팅 · 그레이 비동기 FIFO",
    클럭={"clk": 13.0, "cfg_clk": 40.0},
    출처="손으로 쓴 것 (이 회사의 첫 IP)",
)

붙박이 = [NSW_FIR]


# ------------------------------------------------------------------ 등록부

def 읽기() -> dict:
    """붙박이 + 파일에 등록된 것.  같은 키면 파일 쪽이 이긴다(새로 지은 것)."""
    표 = {d.키: d for d in 붙박이}
    if 등록부길.exists():
        try:
            for d in json.loads(등록부길.read_text(encoding="utf-8")):
                표[d["키"]] = 설계.사전에서(d)
        except Exception:                                    # noqa: BLE001
            pass
    return 표


def 등록(d: 설계) -> 설계:
    """등록부 파일에 적는다.  **다음 세션이 같은 회로를 부를 수 있어야 한다.**"""
    있 = []
    if 등록부길.exists():
        try:
            있 = json.loads(등록부길.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            있 = []
    있 = [x for x in 있 if x.get("키") != d.키] + [d.사전()]
    등록부길.write_text(json.dumps(있, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def 최근() -> "str | None":
    """**마지막으로 등록된 회로의 키.** 없으면 None.

    실측 2026-09-22: `!회사 승인` 으로 새 회로를 지어 등록해 놓고 `!회사 전체` 를
    치면 **붙박이 회로(`fir`)가 돌았다** -- 승인한 스펙이 다섯 명에게 안 갔다.
    `등록()` 이 목록 끝에 붙이므로 마지막 줄이 가장 새것이다.
    """
    if not 등록부길.exists():
        return None
    try:
        있 = json.loads(등록부길.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None
    return (있[-1].get("키") or None) if 있 else None


def 찾기(키: "str | None") -> 설계:
    """키로 고른다.  없으면 기본(fir).  **모르는 키는 조용히 기본으로 넘기지 않는다.**"""
    표 = 읽기()
    if not 키:
        return NSW_FIR
    k = str(키).strip().lower()
    if k in 표:
        return 표[k]
    for 키2, d in 표.items():
        if k in 키2 or k in d.이름.lower():
            return d
    raise KeyError(f"모르는 회로: {키!r} -- 있는 것: {', '.join(sorted(표))}")


def 목록() -> list:
    return sorted(읽기().values(), key=lambda d: d.키)


def 목록글() -> str:
    줄 = []
    for d in 목록():
        ㄱ = d.할수있는것()
        할 = " ".join(k for k in ("RTL", "DV", "합성", "DFT", "PD") if ㄱ[k])
        줄.append(f"· **{d.키}** — {d.이름}  [{할}]\n   {d.한줄}")
    return "\n".join(줄) or "_등록된 회로가 없다._"


# ------------------------------------------------------------------ 파라미터
#
# **회로마다 파라미터 이름이 다르다.** 그런데 에이전트들이 `{"TAPS": 8,
# "STAGES": 3, "GATE_POLICY": 1}` 처럼 FIR 의 이름을 박아 두고 있었다 --
# 다섯 에이전트에 같은 꼴로(실측 2026-09-23). 다른 회로를 넘기면 없는
# 파라미터를 넘기게 되고, verilator 는 그것을 조용히 무시하거나 죽는다.
#
# 그리고 같은 코드가 `dv/agent.py` 와 `rtl/agent.py` 에 따로 있었다.
# 한 군데에 둔다 -- 규칙을 여러 곳에 적으면 한 곳만 고치게 된다.

_정책말 = ("policy", "정책", "gate", "게이팅", "mode", "모드", "enable", "en_")


def 파라기본(설계) -> dict:
    """이 회로의 파라미터 기본값. `설계.파라` + **톱 모듈의 파라미터**.

    `설계.파라` 는 대개 비어 있다(실측: nsw_fir 도 `{}` 다) -- 값은 RTL 에 있다.
    **톱 모듈 것만** 쓴다. 하위 모듈 것을 섞으면 verilator 가
    "Parameters from the command line were not found in the design" 으로 죽는다.
    """
    기본 = dict(getattr(설계, "파라", {}) or {})
    try:
        from house import rtlscan as _SCAN
        훑 = _SCAN.훑기(getattr(설계, "RTL", []), getattr(설계, "top", ""))
        for k, v in (훑.get("톱파라미터") or {}).items():
            if k not in 기본 and str(v).strip().isdigit():
                기본[k] = int(str(v).strip())
    except Exception:                                        # noqa: BLE001
        pass
    return 기본


def 정책파라(기본: dict) -> "str | None":
    """클럭 게이팅 정책처럼 **0/1 로 모드를 고르는** 파라미터 이름. 없으면 None.

    없으면 **없다고 답한다** -- A/B 비교를 지어내지 않는다.
    """
    for k, v in sorted((기본 or {}).items()):
        if isinstance(v, int) and v in (0, 1) and \
           any(w in k.lower() for w in _정책말):
            return k
    return None
