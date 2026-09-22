# -*- coding: utf-8 -*-
"""house/syn/constraints -- SDC 와 UPF 를 **실제로 파싱한다**.

상용 도구가 없다고 제약 파일을 그림의 떡으로 두지 않는다. 여기서 읽어서
  · SDC -> 클럭 정의 · IO 지연 · 예외 · 디레이트를 STA 에 건다
  · UPF -> 전원 도메인 · 아이솔레이션 · 리테션이 **빠진 자리**를 찾는다
는 두 가지를 한다. 못 하는 것(와일드카드 전개, 계층 경로 해석)은 그대로 적는다.
"""
from __future__ import annotations

import re
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
SDC = 뿌리 / "nsw_fir.sdc"
UPF = 뿌리 / "nsw_fir.upf"


def _줄들(길: Path):
    for raw in 길.read_text(encoding="utf-8").splitlines():
        s = raw.split("#")[0].strip()
        if s:
            yield s


# ------------------------------------------------- 회로마다 SDC 가 있어야 한다
#
# **실측 2026-09-22.** `sdc읽기()` 가 인자를 안 받고 늘 `house/syn/nsw_fir.sdc` 를
# 읽었다. MERA 를 넘겨도 FIR 의 클럭 정의(clk 13 ns · cfg_clk 40 ns)로 STA 를 걸고,
# 그 수로 사인오프 보고서를 냈다. **다른 회로의 제약으로 잰 타이밍은 수가 아니다.**
#
# 이 SDC 파일의 머리말은 이렇게 적혀 있다: *"이 파일은 흐름에서 도구가 못 만드는
# 유일한 파일이다. '타이밍을 맞춘다' 가 무슨 뜻인지를 정하는 것은 사람이다."*
# 그 말이 맞다. 그래서 **지어내되 지어냈다고 적는다.**
#
#   · 회로에 SDC 가 있으면      -> 그것을 읽는다      (출처: 사람이 적은 것)
#   · 없으면 RTL 에서 클럭을 찾아 -> 시작 SDC 를 짓는다 (출처: 기계가 지은 것)
#
# 기계가 지은 SDC 는 **클럭 주기와 비동기 그룹까지만** 안다. 거짓 경로 · 멀티사이클 ·
# IO 예산은 설계 판단이므로 안 지어낸다 -- 지어내면 사람이 정한 것처럼 보인다.
def _글줄들(글: str):
    """`_줄들` 과 같은 일을 파일이 아니라 글에 대해 한다."""
    for raw in (글 or "").splitlines():
        t = raw.split("#")[0].strip()
        if t:
            yield t


def sdc짓기(설계=None, 훑기=None, 기본주기_ns=10.0) -> str:
    """RTL 에서 찾은 클럭으로 **시작 SDC** 를 짓는다. 글을 돌려준다."""
    from house import rtlscan as SCAN
    d = 설계
    훑 = 훑기
    if 훑 is None and d is not None:
        훑 = SCAN.훑기(getattr(d, "RTL", []), getattr(d, "top", ""))
    클럭들 = list((훑 or {}).get("클럭") or [])
    주기표 = dict(getattr(d, "클럭", {}) or {})
    if not 클럭들:
        클럭들 = list(주기표) or ["clk"]
    줄 = ["# ---------------------------------------------------------------",
         f"# **기계가 지은 SDC 다.** 회로 `{getattr(d, '키', '?')}` 에 SDC 가 없어서",
         "# RTL 의 `posedge` 에서 클럭을 찾아 지었다. 주기는 스펙의 목표에서 온다.",
         "# 거짓 경로 · 멀티사이클 · IO 예산은 **설계 판단이라 안 지어냈다** --",
         "# 지어내면 사람이 정한 것처럼 보인다.",
         "# ---------------------------------------------------------------"]
    for c in 클럭들:
        주기 = float(주기표.get(c, 기본주기_ns) or 기본주기_ns)
        줄.append(f"create_clock -name {c} -period {주기:g} "
                 f"-waveform {{0 {주기 / 2:g}}} [get_ports {c}]")
    if len(클럭들) > 1:
        묶 = " ".join(f"-group {{{c}}}" for c in 클럭들)
        줄 += ["", "# 클럭이 둘 이상이면 **비동기로 본다.** 같은 소스에서 나온 것이라면",
              "# 사람이 이 줄을 고쳐야 한다 -- 기계는 그것을 모른다.",
              f"set_clock_groups -asynchronous {묶}"]
    줄 += ["", "# CTS 전이므로 클럭 트리가 없다 -- 불확실성으로 대신한다."]
    for c in 클럭들:
        주기 = float(주기표.get(c, 기본주기_ns) or 기본주기_ns)
        줄.append(f"set_clock_uncertainty -setup {주기 * 0.05:.3f} [get_clocks {c}]")
    return "\n".join(줄) + "\n"


def sdc읽기(길=None, 설계=None) -> dict:
    """SDC 를 읽는다. 회로에 SDC 가 없으면 **지어서 읽고 그렇게 적는다.**"""
    글 = None
    출처 = "사람이 적은 것"
    if 길 is None and 설계 is not None:
        제것 = getattr(설계, "SDC", None)
        if 제것 and Path(제것).exists():
            길 = Path(제것)
        else:
            글 = sdc짓기(설계)
            출처 = "기계가 지은 것"
    길 = Path(길 or SDC)
    d = {"클럭": [], "클럭그룹": [], "입력지연": [], "출력지연": [], "예외": [],
        "불확실성": [], "디레이트": {}, "기타": [], "줄수": 0,
        "출처": 출처, "파일": (None if 글 else str(길))}
    for s in (_글줄들(글) if 글 is not None else _줄들(길)):
        d["줄수"] += 1
        if s.startswith("create_clock"):
            이름 = re.search(r"-name\s+(\S+)", s)
            주기 = re.search(r"-period\s+([\d.]+)", s)
            핀 = re.search(r"\[get_ports\s+([^\]]+)\]", s)
            d["클럭"].append({"이름": 이름.group(1) if 이름 else "?",
                            "주기_ns": float(주기.group(1)) if 주기 else None,
                            "핀": 핀.group(1).strip() if 핀 else "?",
                            "주파수_MHz": round(1e3 / float(주기.group(1)), 2) if 주기 else None})
        elif s.startswith("set_clock_groups"):
            d["클럭그룹"].append({"비동기": "-asynchronous" in s,
                              "묶음": re.findall(r"-group\s+\{([^}]*)\}", s)})
        elif s.startswith("set_input_delay"):
            v = re.search(r"-clock\s+(\S+)\s+([\d.]+)", s)
            p = re.search(r"\[get_ports\s+\{?([^}\]]+)\}?\]", s)
            d["입력지연"].append({"클럭": v.group(1) if v else "?",
                              "지연_ns": float(v.group(2)) if v else None,
                              "포트": (p.group(1).strip() if p else "?")})
        elif s.startswith("set_output_delay"):
            v = re.search(r"-clock\s+(\S+)\s+([\d.]+)", s)
            p = re.search(r"\[get_ports\s+\{?([^}\]]+)\}?\]", s)
            d["출력지연"].append({"클럭": v.group(1) if v else "?",
                              "지연_ns": float(v.group(2)) if v else None,
                              "포트": (p.group(1).strip() if p else "?")})
        elif s.startswith(("set_false_path", "set_multicycle_path", "set_max_delay",
                          "set_min_delay")):
            d["예외"].append({"종류": s.split()[0], "글": s[:110]})
        elif s.startswith("set_clock_uncertainty"):
            v = re.search(r"(setup|hold)\s+([\d.]+)", s)
            d["불확실성"].append({"종류": v.group(1) if v else "?",
                              "값_ns": float(v.group(2)) if v else None})
        elif s.startswith("set_timing_derate"):
            v = re.search(r"-(early|late)\s+([\d.]+)", s)
            if v:
                d["디레이트"][v.group(1)] = float(v.group(2))
        else:
            d["기타"].append(s[:80])
    return d


def upf읽기(길=None, 설계=None) -> dict:
    """UPF 를 읽는다.

    **SDC 와 달리 UPF 는 안 지어낸다.** 클럭 주기는 스펙에 적혀 있지만 전원
    도메인 · 아이솔레이션 · 리테션은 **설계 판단**이다. 지어내면 사람이 정한
    저전력 구조가 있는 것처럼 보이고, 그 위에 낸 전력 수가 거짓이 된다.
    없으면 없다고 한다.
    """
    if 길 is None and 설계 is not None:
        제것 = getattr(설계, "UPF", None)
        if 제것 and Path(제것).exists():
            길 = Path(제것)
        else:
            return {"도메인": [], "공급": [], "전원상태": [], "PST": [],
                    "아이솔레이션": [], "리테션": [], "레벨시프터": [],
                    "주석처리": [], "줄수": 0, "없다": True,
                    "까닭": f"회로 `{getattr(설계, '키', '?')}` 에 UPF 가 없다 -- "
                          "전원 의도는 설계 판단이라 **지어내지 않는다**"}
    길 = Path(길 or UPF)
    d = {"도메인": [], "공급": [], "전원상태": [], "PST": [], "아이솔레이션": [],
        "리테션": [], "레벨시프터": [], "주석처리": [], "줄수": 0, "없다": False}
    원본 = Path(길).read_text(encoding="utf-8")
    for raw in 원본.splitlines():
        t = raw.strip()
        if t.startswith("#") and "set_level_shifter" in t:
            d["주석처리"].append(t.lstrip("# ")[:90])
    for s in _줄들(길):
        d["줄수"] += 1
        if s.startswith("create_power_domain"):
            이름 = s.split()[1]
            el = re.search(r"-elements\s+\{([^}]*)\}", s)
            d["도메인"].append({"이름": 이름, "요소": (el.group(1).split() if el else [])})
        elif s.startswith(("create_supply_net", "create_supply_port")):
            d["공급"].append(s.split()[1])
        elif s.startswith("add_power_state"):
            d["전원상태"].append({"공급": s.split()[1],
                              "상태": re.findall(r"-state\s+\{(\w+)", s)})
        elif s.startswith("add_pst_state"):
            d["PST"].append({"이름": s.split()[1],
                           "상태": re.search(r"-state\s+\{([^}]*)\}", s).group(1)
                                  if re.search(r"-state\s+\{([^}]*)\}", s) else ""})
        elif s.startswith("set_isolation_control"):
            d["아이솔레이션"].append({"이름": s.split()[1], "제어": True, "글": s[:100]})
        elif s.startswith("set_isolation"):
            dm = re.search(r"-domain\s+(\S+)", s)
            cv = re.search(r"-clamp_value\s+(\S+)", s)
            d["아이솔레이션"].append({"이름": s.split()[1], "도메인": dm.group(1) if dm else "?",
                                "클램프": cv.group(1) if cv else "?", "제어": False})
        elif s.startswith("set_retention_control"):
            d["리테션"].append({"이름": s.split()[1], "제어": True, "글": s[:100]})
        elif s.startswith("set_retention"):
            dm = re.search(r"-domain\s+(\S+)", s)
            el = re.search(r"-elements\s+\{([^}]*)\}", s)
            d["리테션"].append({"이름": s.split()[1], "도메인": dm.group(1) if dm else "?",
                             "요소": (el.group(1).split() if el else []), "제어": False})
        elif s.startswith("set_level_shifter"):
            d["레벨시프터"].append(s.split()[1])
    return d


def upf점검(u: dict, rtl글: str = "") -> list:
    """UPF 정합성 점검.  **빠진 것을 찾는 것이 목적이다.**"""
    문제 = []
    끌수있는 = []
    for st in u["전원상태"]:
        if "OFF" in st["상태"]:
            끌수있는.append(st["공급"])
    iso정의 = {x["이름"] for x in u["아이솔레이션"] if not x.get("제어")}
    iso제어 = {x["이름"] for x in u["아이솔레이션"] if x.get("제어")}
    ret정의 = {x["이름"] for x in u["리테션"] if not x.get("제어")}
    ret제어 = {x["이름"] for x in u["리테션"] if x.get("제어")}

    for nm in iso정의 - iso제어:
        문제.append({"심각도": "CRITICAL", "무엇": f"isolation `{nm}` has no control signal",
                   "왜": "without knowing when to clamp, the cell gets inserted and never engages"})
    for nm in ret정의 - ret제어:
        문제.append({"심각도": "CRITICAL", "무엇": f"retention `{nm}` has no save/restore",
                   "왜": "with no save point a retention flop is just a larger flop"})

    꺼지는도메인 = set()
    for st in u["전원상태"]:
        if "OFF" in st["상태"]:
            for dmn in u["도메인"]:
                꺼지는도메인.add(dmn["이름"])
    실제꺼짐 = [d for d in u["도메인"] if d["이름"] == "PD_DP"]
    if 실제꺼짐 and not iso정의:
        문제.append({"심각도": "CRITICAL",
                   "무엇": "a switchable domain exists but has no isolation",
                   "왜": "floating outputs -> crowbar current in the receiver. Every functional test still passes"})
    if 실제꺼짐 and not ret정의:
        문제.append({"심각도": "WARNING",
                   "무엇": "a switchable domain has no retention",
                   "왜": "state is lost across an off/on cycle. Fine if intended"})
    if not u["레벨시프터"]:
        문제.append({"심각도": "CHECKED",
                   "무엇": "no level shifters are declared",
                   "왜": "correct for now \u2014 both domains sit at the same 1.8 V. One becomes mandatory the moment those voltages diverge"
                        + (f" (prepared as comments in the UPF: {len(u['주석처리'])} lines)" if u["주석처리"] else "")})
    if rtl글:
        for dmn in u["도메인"]:
            for e in dmn["요소"]:
                if e and e not in rtl글:
                    문제.append({"심각도": "CRITICAL", "무엇": f"UPF references `{e}`, which does not exist in the RTL",
                               "왜": "a name mismatch leaves the domain empty and passes silently"})
    return 문제
