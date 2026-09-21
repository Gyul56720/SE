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
                "메모": self.메모}

    @staticmethod
    def 사전에서(d: dict) -> "설계":
        return 설계(키=d["키"], 이름=d["이름"], top=d["top"],
                  RTL=[Path(p) for p in d["RTL"]],
                  TB=Path(d["TB"]) if d.get("TB") else None,
                  파라=d.get("파라") or {},
                  SDC=Path(d["SDC"]) if d.get("SDC") else None,
                  UPF=Path(d["UPF"]) if d.get("UPF") else None,
                  한줄=d.get("한줄", ""), 클럭=d.get("클럭") or {},
                  출처=d.get("출처", ""), 메모=d.get("메모", ""))


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
