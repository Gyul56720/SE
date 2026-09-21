# -*- coding: utf-8 -*-
"""에이전트 인프라 공학 교안을 낸다.

`edu/buildT.py` 와 같은 얼개다 -- 장 모듈을 importlib 로 들여 `ch_*` 를 부르고
한 권으로 렌더한다. **빠진 장은 빠졌다고 찍는다**(조용히 건너뛰지 않는다).

이 책이 감당해야 하는 채용공고 세 장은 `agentbook/jd.py` 에 코드로 적혀 있고,
`tests/test_agentbook.py` 가 **감당하는 장이 없는 요구가 있으면 빨간불**을 낸다.
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
    ("3부. 디코딩과 표본의 수학", [
        ("B1_grammar",   ["ch_grammar"]),
        ("B2_kvcache",   ["ch_kvcache"]),
        ("B3_ensemble",  ["ch_ensemble"]),
        ("B4_search",    ["ch_search"]),
    ]),
    ("4부. 검색과 지식 — RAG", [
        ("D1_vector",    ["ch_vector"]),
        ("D2_lexical",   ["ch_lexical"]),
        ("D3_ann",       ["ch_ann"]),
        ("D4_graphrag",  ["ch_graphrag"]),
    ]),
    ("5부. 학습 — 에이전트를 정책으로 본다", [
        ("E1_mdp",       ["ch_mdp"]),
        ("E2_pg",        ["ch_pg"]),
        ("E3_ppo",       ["ch_ppo"]),
        ("E4_grpo",      ["ch_grpo"]),
        ("E5_reward",    ["ch_reward"]),
    ]),
    ("6부. 신뢰성", [
        ("A10_failure",  ["ch_failure"]),
        ("A11_quota",    ["ch_quota"]),
        ("A12_eval",     ["ch_eval"]),
        ("A13_observe",  ["ch_observe"]),
        ("A14_safety",   ["ch_safety"]),
    ]),
    ("7부. 분산과 상태", [
        ("C1_replay",    ["ch_replay"]),
        ("C2_impossible", ["ch_impossible"]),
        ("C3_crdt",      ["ch_crdt"]),
        ("C4_checkpoint", ["ch_checkpoint"]),
    ]),
    ("8부. 개발자 인터페이스 — SDK · CLI · 그리고 파일 하나", [
        ("A15_sdk",      ["ch_sdk"]),
        ("A16_cli",      ["ch_cli"]),
        ("A17_mcp",      ["ch_mcp"]),
        ("S1_decl",      ["ch_decl"]),
        ("S2_invent",    ["ch_invent"]),
    ]),
    ("9부. 규모와 비용", [
        ("A18_cost",     ["ch_cost"]),
        ("A19_tenancy",  ["ch_tenancy"]),
        ("A20_deploy",   ["ch_deploy"]),
    ]),
    ("10부. 말과 문법 — 여섯 언어", [
        ("L1_langs",     ["ch_langs"]),
        ("L2_types",     ["ch_types"]),
        ("L3_shell",     ["ch_shell"]),
    ]),
    ("11부. 레포 해부 — 읽은 커밋만 인용한다", [
        ("R1_langgraph", ["ch_langgraph"]),
        ("R2_mcp_sdk",   ["ch_mcp_sdk"]),
        ("R3_swe",       ["ch_swe"]),
        ("R4_aider",     ["ch_aider"]),
        ("R5_codeact",   ["ch_codeact"]),
        ("R6_dspy",      ["ch_dspy"]),
        ("R7_vllm",      ["ch_vllm"]),
        ("R8_cline",     ["ch_cline"]),
        ("R9_multi",     ["ch_multi"]),
        ("R10_sdks",     ["ch_sdks"]),
    ]),
    ("12부. 최신 논문을 읽는 법", [
        ("P1_read",      ["ch_read"]),
        ("P2_frontier",  ["ch_frontier"]),
        ("P3_repro",     ["ch_repro"]),
    ]),
    ("13부. 현장", [
        ("A21_thisagent", ["ch_thisagent"]),
        ("A22_se",       ["ch_se"]),
        ("A23_incident", ["ch_incident"]),
        ("A24_lab",      ["ch_lab"]),
    ]),
]


def 모듈들():
    return [m for _, 목록 in 차례 for m, _ in 목록]


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
    import bookA
    meta = """
<p>에이전트 시스템 <b>프레임워크</b>를 짓는 사람을 위한 대학원 수준 이론서다.
모형을 쓰는 법이 아니라 <b>그 위에 런타임을 짓는 법</b>을 다룬다 &mdash; 제어 루프,
오케스트레이션, 컨텍스트 예산, 도구 실행, 메모리 추상, 검색, 정책 학습, 그리고
그 전부가 깨지는 자리.</p>
<p><b>모든 이론에는 근거가 있다.</b> 이 책의 주장은 <b>정리</b>와 <b>증명</b>으로
적혀 있고, 증명의 한 걸음마다 &lsquo;왜냐하면&rsquo; 이 붙는다. 증명 없는 정리는
이 책의 빌드가 거부한다 &mdash; 인자가 아니라 강제다.</p>
<p><b>수는 인용하지 않는다.</b> 이 책의 모든 수는 빌드할 때 계산되거나, 이 저장소
또는 <b>실제로 클론해 읽은 오픈소스 저장소</b>에서 잰 것이다. 저장소마다 읽은 커밋
해시를 적었다.</p>
<p><b>사고 상자</b>(붉은 칸)는 <i>실제로 난 일</i>이다. 대부분은 이 저장소에서 났고,
커밋 해시와 날짜가 붙어 있다. 교과서가 아니라 현장 기록인 까닭이 그것이다.</p>"""
    front = cover("CS-AGENT-001", "에이전트 인프라 공학",
                  "Agent Infrastructure Engineering — 런타임을 짓는 사람을 위한 이론서",
                  meta) + toc(본문)
    doc = ('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
           '<title>에이전트 인프라 공학</title></head><body>'
           + front + 본문 + '</body></html>')
    이름 = "Agent_Theory_EN.pdf" if 영어 else "Agent_Theory_KR.pdf"
    render(doc, os.path.join(여기, 이름),
           css=os.path.join(저장소, "edu", "agent_style.css"))
    print(f"정리 {len(bookA.정리들)}개 · 증명 걸음 "
          f"{sum(n for _, _, n in bookA.정리들)}개")
    if 빠진:
        print(f"아직 없는 장 {len(빠진)}개: {빠진}")
