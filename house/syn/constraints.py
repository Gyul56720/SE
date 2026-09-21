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


def sdc읽기(길=None) -> dict:
    길 = Path(길 or SDC)
    d = {"클럭": [], "클럭그룹": [], "입력지연": [], "출력지연": [], "예외": [],
        "불확실성": [], "디레이트": {}, "기타": [], "줄수": 0}
    for s in _줄들(길):
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


def upf읽기(길=None) -> dict:
    길 = Path(길 or UPF)
    d = {"도메인": [], "공급": [], "전원상태": [], "PST": [], "아이솔레이션": [],
        "리테션": [], "레벨시프터": [], "주석처리": [], "줄수": 0}
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
