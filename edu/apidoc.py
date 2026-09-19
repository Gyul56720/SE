# -*- coding: utf-8 -*-
"""코드 부록에 실린 파일의 **API 사전**을 기계로 만든다.

사용자 요구: "클래스·함수가 받는 파라미터가 무엇인지, #define 과 namespace 는
무슨 용도인지 적어라. 이름만 보면 헷갈린다."

손으로 적으면 코드가 바뀔 때 조용히 틀려진다.  그래서 **파일에서 뽑는다.**
정규식 기반이므로 완벽한 파서는 아니다 -- 그 한계를 문서에 적는다.
"""
import os, re, sys
sys.path.insert(0, "/home/user/SE/edu")
from book import ZOO, E

# ---------------------------------------------------------------- C/C++
_CPP_NS    = re.compile(r"^\s*namespace\s+(\w+)\s*\{", re.M)
_CPP_CLASS = re.compile(r"^\s*(?:template\s*<([^>]*)>\s*)?"
                        r"(class|struct)\s+(\w+)\s*(?::\s*([^{\n]+))?\s*\{", re.M)
_CPP_FUNC  = re.compile(
    r"^(?!\s*(?:if|for|while|switch|return|else|catch)\b)"
    r"([A-Za-z_][\w\s\*&:<>,~]*?)\s+(\w+)\s*\(([^;{)]*)\)\s*(const\s*)?(?:noexcept\s*)?\{",
    re.M)
_CPP_DEF   = re.compile(r"^\s*#\s*define\s+(\w+)(\([^)]*\))?\s*(.*)$", re.M)
_CPP_TYPEDEF = re.compile(r"^\s*(?:typedef\s+(.+?)\s+(\w+)|using\s+(\w+)\s*=\s*(.+?))\s*;",
                          re.M)

# ---------------------------------------------------------------- SV/V
_SV_MOD    = re.compile(r"^\s*(module|interface|package|program)\s+(?:automatic\s+)?(\w+)",
                        re.M)
_SV_PARAM  = re.compile(r"^\s*parameter\s+(?:type\s+)?([\w\s\[\]:\-\$]*?)\s*(\w+)\s*=\s*([^,;\n]+)",
                        re.M)
_SV_LOCAL  = re.compile(r"^\s*localparam\s+(?:type\s+)?([\w\s\[\]:\-\$]*?)\s*(\w+)\s*=\s*([^,;\n]+)",
                        re.M)
_SV_PORT   = re.compile(r"^\s*(input|output|inout)\s+([^,;\n]*?)\s*(\w+)\s*(?:,|\)|;|$)", re.M)
_SV_DEF    = re.compile(r"^\s*`define\s+(\w+)(\([^)]*\))?\s*(.*)$", re.M)
_SV_TYPEDEF = re.compile(r"^\s*typedef\s+(.+?)\s+(\w+)\s*(?:\[[^\]]*\])?\s*;", re.M)


def _자르기(s, n=110):
    s = re.sub(r"\s+", " ", (s or "").strip())
    return (s[:n] + "…") if len(s) > n else s


def cpp훑기(t):
    """C/C++ 파일에서 namespace · class · function · define · typedef 를 뽑는다."""
    r = {}
    r["namespace"] = [(m.group(1),) for m in _CPP_NS.finditer(t)]
    r["class"] = [(m.group(3), _자르기(m.group(1)), m.group(2), _자르기(m.group(4)))
                  for m in _CPP_CLASS.finditer(t)]
    fn = []
    for m in _CPP_FUNC.finditer(t):
        ret, name, params = _자르기(m.group(1), 60), m.group(2), _자르기(m.group(3), 150)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        if len(ret) > 58 or "=" in ret:
            continue
        fn.append((name, ret, params))
    r["function"] = fn
    r["define"] = [(m.group(1), _자르기(m.group(2), 60), _자르기(m.group(3), 90))
                   for m in _CPP_DEF.finditer(t)]
    td = []
    for m in _CPP_TYPEDEF.finditer(t):
        if m.group(2):
            td.append((m.group(2), _자르기(m.group(1), 80)))
        elif m.group(3):
            td.append((m.group(3), _자르기(m.group(4), 80)))
    r["typedef"] = td
    return r


def sv훑기(t):
    """SystemVerilog/Verilog 에서 module · parameter · port · `define · typedef 를 뽑는다."""
    r = {}
    r["module"] = [(m.group(2), m.group(1)) for m in _SV_MOD.finditer(t)]
    r["parameter"] = [(m.group(2), _자르기(m.group(1), 40), _자르기(m.group(3), 60))
                      for m in _SV_PARAM.finditer(t)]
    r["localparam"] = [(m.group(2), _자르기(m.group(1), 40), _자르기(m.group(3), 60))
                       for m in _SV_LOCAL.finditer(t)]
    r["port"] = [(m.group(3), m.group(1), _자르기(m.group(2), 50))
                 for m in _SV_PORT.finditer(t)]
    r["define"] = [(m.group(1), _자르기(m.group(2), 60), _자르기(m.group(3), 90))
                   for m in _SV_DEF.finditer(t)]
    r["typedef"] = [(m.group(2), _자르기(m.group(1), 80)) for m in _SV_TYPEDEF.finditer(t)]
    return r


def 훑기(존, rel):
    p = os.path.join(ZOO[존], rel)
    t = open(p, encoding="utf-8", errors="replace").read()
    확 = os.path.splitext(rel)[1]
    if 확 in (".sv", ".v", ".svh", ".vh"):
        return "sv", sv훑기(t)
    if 확 in (".c", ".cc", ".cpp", ".h", ".hpp", ".hh"):
        return "cpp", cpp훑기(t)
    return None, {}


_머리 = {
    "namespace": (["namespace", "용도(이름에서 읽히는 것)"],
                  "이름 충돌을 막고 소속을 밝힌다"),
    "class":     (["이름", "템플릿 인자", "종류", "상속"], ""),
    "function":  (["함수", "반환형", "<b>받는 파라미터</b>"], ""),
    "define":    (["매크로", "인자", "정의"], ""),
    "typedef":   (["새 이름", "원래 형"], ""),
    "module":    (["이름", "종류"], ""),
    "parameter": (["파라미터", "형/폭", "기본값"], ""),
    "localparam":(["상수", "형/폭", "값"], ""),
    "port":      (["포트", "방향", "형/폭"], ""),
}


def 표로(종류, 항목들, 표함수, 파일, 최대=60):
    if not 항목들:
        return ""
    머리, _ = _머리[종류]
    보임 = 항목들[:최대]
    행 = [[f"<code>{E(str(c))}</code>" if i == 0 else E(str(c))
           for i, c in enumerate(행0)] for 행0 in 보임]
    꼬리 = (f" &mdash; 앞 {최대}개만 표시(전체 {len(항목들)}개, 본문 소스 참조)"
            if len(항목들) > 최대 else "")
    이름 = {"namespace": "namespace", "class": "클래스/구조체", "function": "함수",
            "define": "#define / `define 매크로", "typedef": "typedef / using",
            "module": "module / interface / package", "parameter": "parameter",
            "localparam": "localparam", "port": "포트"}[종류]
    return 표함수(f"<code>{E(파일)}</code> &mdash; {이름} ({len(항목들)}개){꼬리}",
                  머리, 행)
