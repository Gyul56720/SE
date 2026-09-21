# -*- coding: utf-8 -*-
"""Agent Infrastructure Engineering 교안을 낸다.

`edu/buildT.py` 와 같은 얼개다 -- 장 모듈을 importlib 로 들여 `ch_*` 를 부르고
한 권으로 렌더한다. **빠진 장은 빠졌다고 찍는다**(조용히 건너뛰지 않는다).
"""
import importlib
import os
import sys

여기 = os.path.dirname(os.path.abspath(__file__))
저장소 = os.path.dirname(여기)
sys.path.insert(0, os.path.join(저장소, "edu"))
sys.path.insert(0, 여기)

from bookE import cover, toc, render          # noqa: E402
import bookK                                   # noqa: E402

# 부 -> (모듈, [장 함수])
차례 = [
    ("1부. 무엇이 에이전트인가", [
        ("A1_agent",     ["ch_agent"]),
        ("A2_runtime",   ["ch_llm_runtime"]),
        ("A3_sampling",  ["ch_sampling"]),
    ]),
    ("2부. 런타임 코어", [
        ("A4_loop",      ["ch_loop"]),
        ("A5_orch",      ["ch_orchestration"]),
        ("A6_context",   ["ch_context"]),
        ("A7_tools",     ["ch_tools"]),
        ("A8_memory",    ["ch_memory"]),
        ("A9_state",     ["ch_state"]),
    ]),
    ("3부. 신뢰성", [
        ("A10_failure",  ["ch_failure"]),
        ("A11_quota",    ["ch_quota"]),
        ("A12_eval",     ["ch_eval"]),
        ("A13_observe",  ["ch_observe"]),
        ("A14_safety",   ["ch_safety"]),
    ]),
    ("4부. 개발자 인터페이스", [
        ("A15_sdk",      ["ch_sdk"]),
        ("A16_cli",      ["ch_cli"]),
        ("A17_ext",      ["ch_ext"]),
    ]),
    ("5부. 규모", [
        ("A18_cost",     ["ch_cost"]),
        ("A19_tenancy",  ["ch_tenancy"]),
        ("A20_deploy",   ["ch_deploy"]),
    ]),
    ("6부. 현장", [
        ("A21_case",     ["ch_case"]),
        ("A22_incident", ["ch_incident"]),
        ("A23_lab",      ["ch_lab"]),
    ]),
]


def body(차례):
    out, 빠진 = [], []
    for 부이름, 목록 in 차례:
        조각 = []
        for 모듈, 함수들 in 목록:
            try:
                m = importlib.import_module(모듈)
            except ModuleNotFoundError:
                빠진.append(모듈)
                continue
            for f in 함수들:
                fn = getattr(m, f, None)
                if fn is None:
                    빠진.append(f"{모듈}.{f}")
                    continue
                조각.append(fn())
        if 조각:
            out.append(f'<h1 class="부">{부이름}</h1>')
            out.extend(조각)
    return "\n".join(out), 빠진


if __name__ == "__main__":
    영어 = "--영어" in sys.argv or "--en" in sys.argv
    if 영어:
        bookK.언어("en")
    본문, 빠진 = body(차례)
    meta = """
<p>에이전트 시스템 <b>프레임워크</b>를 짓는 사람을 위한 이론서다. 모형을 쓰는 법이
아니라 <b>그 위에 런타임을 짓는 법</b>을 다룬다 &mdash; 제어 루프, 오케스트레이션,
컨텍스트 예산, 도구 실행, 메모리 추상, 그리고 그 전부가 깨지는 자리.</p>
<p><b>수는 인용하지 않는다.</b> 이 책의 모든 수는 빌드할 때 계산되거나 이 저장소에서
실제로 잰 것이다. 계산이 바뀌면 책의 수도 바뀐다.</p>
<p><b>사고 상자</b>(붉은 칸)는 <i>실제로 난 일</i>이다. 대부분은 이 저장소에서
났고, 커밋 해시와 날짜가 붙어 있다. 교과서가 아니라 현장 기록인 까닭이 그것이다.</p>"""
    front = cover("CS-AGENT-001", "에이전트 인프라 공학",
                  "Agent Infrastructure Engineering — 런타임을 짓는 사람을 위한 이론서",
                  meta) + toc(본문)
    doc = ('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
           '<title>에이전트 인프라 공학</title></head><body>'
           + front + 본문 + '</body></html>')
    이름 = "Agent_Theory_EN.pdf" if 영어 else "Agent_Theory_KR.pdf"
    render(doc, os.path.join(여기, 이름))
    if 빠진:
        print(f"아직 없는 장 {len(빠진)}개: {빠진}")
