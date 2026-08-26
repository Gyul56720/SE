"""
FuriosaAI 시스템 아키텍처/SDK/오픈소스 개념서·이론서 생성기.
theory_generator.py("math_chatbox" 편입수학 이론서)의 8단 문법(동기->정의/정리->핵심 공식(killing
equation)->테크닉->흔한 실수->대표예제->유제->다음 연결)을 그대로 따르되, book_generator.py의
grounding 원칙(근거자료 밖 사실 금지)을 적용한다. 편입수학은 정립된 지식이라 grounding 없이 써도
안전하지만, FuriosaAI의 실존 칩/SDK 스펙은 WebFetch로 직접 확인한 원문(sources 딕셔너리)만 근거로
삼아야 한다 -- 수치나 API 이름을 지어내면 안 된다. 단, "대표예제"/"유제"는 사실 서술이 아니라
추론 연습이므로 새로 창작 가능.

  python furiosa_theory_generator.py
"""

from __future__ import annotations
import re
from pathlib import Path

import gemini_client

VAULT_ROOT = Path("/Users/cogito/Documents/Obsidian Vault")
BOOK_ROOT = VAULT_ROOT / "project_furiosa"

PERSONA = """당신은 AI 가속기(NPU) 시스템 아키텍처와 SDK를 분석하는 시니어 반도체/시스템 엔지니어이자,
후배 엔지니어를 위한 개념/이론서를 쓰는 저자입니다. 처음 배우는 사람도 이해할 수 있도록 쉽고
꼼꼼하게, 그러나 사실관계에 한 치의 오류나 지어낸 내용도 없이 설명합니다. 모든 논리는
"~하기 때문에 ~하다"처럼 인과관계를 명확히 밝힙니다.

절대 원칙: 아래 "근거 자료"(WebFetch로 실제 확인한 FuriosaAI 공식 문서/블로그/제품 페이지 원문)
밖의 수치, API 이름, 리포지토리 이름, 스펙을 절대 지어내지 않습니다. 근거 자료에 없으면
"근거 자료에 명시되지 않음"이라고 밝히십시오. 단, "대표예제"와 "유제"는 사실 서술이 아니라 이
개념을 응용해보는 추론 연습 문제이므로 새로 창작해도 됩니다(단 근거 자료의 숫자/이름과 모순되지
않게)."""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "motivation": {"type": "STRING", "description": "이 개념을 왜 알아야 하는지, 실무/면접에서 왜 중요한지 (2-4문장, 인과관계 명확히)"},
        "definitions_and_theory": {
            "type": "STRING",
            "description": "근거 자료 기반 핵심 정의/구조/동작 원리 설명 (마크다운, 필요시 LaTeX). "
                            "근거 자료에 없는 내용을 추가하지 말 것. ### 소제목으로 구분 가능.",
        },
        "killing_fact_latex": {
            "type": "STRING",
            "description": "이 토픽의 핵심을 나타내는 단 하나의 수식/부등식/규칙(LaTeX). 근거 자료에 "
                            "등장하는 수치 관계식이나 제약조건(예: TP*PP*DP = 전체 PE 수)만 쓸 것. "
                            "근거 자료에 그런 수식이 전혀 없으면 대신 가장 핵심적인 스펙 수치 한 줄을 "
                            "\\text{} 형태로 넣을 것.",
        },
        "killing_fact_explanation": {"type": "STRING", "description": "이 핵심 수식/사실이 왜 이 토픽의 핵심인지 설명"},
        "techniques": {
            "type": "ARRAY",
            "description": "이 토픽의 핵심 설계 기법/메커니즘 3-6개 (근거 자료에 등장하는 것만)",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "method": {"type": "STRING", "description": "구체적으로 어떻게 동작하는지, 근거 자료 인용 포함"},
                    "reasoning": {"type": "STRING", "description": "왜 이렇게 설계했는지 인과적 설명"},
                },
                "required": ["name", "method", "reasoning"],
            },
        },
        "common_mistakes": {
            "type": "STRING",
            "description": "이 토픽을 처음 접할 때 흔히 오해하거나 놓치는 부분, GPU/기존 방식과 헷갈리기 쉬운 지점을 빠짐없이 짚어줄 것.",
        },
        "worked_examples": {
            "type": "ARRAY",
            "description": "이 개념을 적용해 실무/면접 상황을 추론하는 대표예제 정확히 2개. 새로 창작하되 "
                            "근거 자료의 수치/이름과 모순되지 않을 것.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "problem": {"type": "STRING"},
                    "solution_steps": {"type": "STRING", "description": "'1단계 — ...' 형식, 왜 그런지 논리 포함"},
                    "answer": {"type": "STRING"},
                },
                "required": ["problem", "solution_steps", "answer"],
            },
        },
        "practice_problems": {
            "type": "ARRAY",
            "description": "스스로 생각해볼 유제(면접 예상 질문 형태) 정확히 3개, 풀이 없이 문제+짧은 힌트만.",
            "items": {
                "type": "OBJECT",
                "properties": {"problem": {"type": "STRING"}, "hint": {"type": "STRING"}},
                "required": ["problem", "hint"],
            },
        },
        "next_topic_connection": {"type": "STRING", "description": "이 챕터가 다음 챕터와 구체적으로 어떻게 연결되는지 (1-3문장)"},
    },
    "required": [
        "motivation", "definitions_and_theory", "killing_fact_latex", "killing_fact_explanation",
        "techniques", "common_mistakes", "worked_examples", "practice_problems", "next_topic_connection",
    ],
}

PROMPT_TMPL = PERSONA + """

도메인: {domain}
챕터 주제: "{topic}"

--- 근거 자료 (WebFetch로 확인한 FuriosaAI 공식 원문) ---
{grounding}

위 근거 자료만 바탕으로 지정된 JSON 스키마에 맞춰 개념/이론서 챕터 하나를 작성하라.
반드시 한국어로, 필요한 수식은 LaTeX($$...$$ 또는 $...$)로 작성하라.
"""

_TEMPLATE = """---
title: "{title}"
domain: {domain}
tags: [project_furiosa, 이론서, {domain}]
killing_fact: "{killing_fact_frontmatter}"
sources: {sources_list}
---

# {index:02d}. {title}

## 1. 왜 알아야 하는가

{motivation}

## 2. 정의와 구조

{definitions_and_theory}

## 3. 핵심 사실 (Killing Fact)

$$ \\boxed{{\\ {killing_fact_latex}\\ }} $$

{killing_fact_explanation}

## 4. 핵심 설계 기법

{techniques_block}

## 5. 자주 하는 오해 / 주의할 점

{common_mistakes}

## 6. 대표예제 (추론 연습)

{examples_block}

## 7. 유제 (면접 예상 질문)

{practice_block}

## 8. 다음 챕터와의 연결

{next_topic_connection}
"""


def _techniques_block(techniques: list[dict]) -> str:
    parts = []
    for i, t in enumerate(techniques, 1):
        parts.append(
            f"### 기법 {chr(64+i)}: {t.get('name','')}\n\n"
            f"{t.get('method','')}\n\n"
            f"**왜 이렇게 설계했는가:** {t.get('reasoning','')}"
        )
    return "\n\n".join(parts)


def _examples_block(examples: list[dict]) -> str:
    parts = []
    for i, ex in enumerate(examples, 1):
        parts.append(
            f"### 예제 {i}\n\n{ex.get('problem','')}\n\n"
            f"**풀이:**\n\n{ex.get('solution_steps','')}\n\n"
            f"**답: {ex.get('answer','')}**"
        )
    return "\n\n".join(parts)


def _practice_block(problems: list[dict]) -> str:
    return "\n".join(f"{i}. {p.get('problem','')} *(힌트: {p.get('hint','')})*" for i, p in enumerate(problems, 1))


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s가-힣-]", "", title).strip()
    return re.sub(r"\s+", " ", slug)


def _strip_dollar_wrapping(latex: str) -> str:
    s = latex.strip()
    while s.startswith("$$") and s.endswith("$$") and len(s) > 4:
        s = s[2:-2].strip()
    while s.startswith("$") and s.endswith("$") and len(s) > 2:
        s = s[1:-1].strip()
    return s


def generate_chapter(domain: str, index: int, topic: str, grounding: str, sources: list[str]) -> Path:
    prompt = PROMPT_TMPL.format(domain=domain, topic=topic, grounding=grounding)
    print(f"  [Gemini 호출] {domain} #{index} {topic} ...")
    data = gemini_client.generate_json(prompt, SCHEMA)
    killing_fact_latex = _strip_dollar_wrapping(data["killing_fact_latex"])

    content = _TEMPLATE.format(
        title=topic, domain=domain, index=index,
        killing_fact_frontmatter=killing_fact_latex.replace('"', "'"),
        killing_fact_latex=killing_fact_latex,
        killing_fact_explanation=data["killing_fact_explanation"],
        motivation=data["motivation"],
        definitions_and_theory=data["definitions_and_theory"],
        techniques_block=_techniques_block(data["techniques"]),
        common_mistakes=data["common_mistakes"],
        examples_block=_examples_block(data["worked_examples"]),
        practice_block=_practice_block(data["practice_problems"]),
        next_topic_connection=data["next_topic_connection"],
        sources_list=sources,
    )
    out_dir = BOOK_ROOT / domain
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{index:02d}_{_slug(topic)}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  [저장] {out_path}")
    return out_path


CHAPTERS = [
    dict(
        domain="01_시스템아키텍처",
        index=1,
        topic="RNGD Tensor Contraction Processor 아키텍처",
        sources=["https://developer.furiosa.ai/latest/en/overview/rngd.html",
                  "https://furiosa.ai/blog/tensor-contraction-processor-ai-chip-architecture",
                  "https://furiosa.ai/rngd"],
        grounding="""[developer.furiosa.ai/overview/rngd.html]
핵심 아키텍처: "Tensor Contraction Processor (TCP)". 공정: TSMC 5nm, 클럭 1.0GHz.
성능: 256 TFLOPS(BF16), 512 TFLOPS(FP8), 512 TOPS(INT8), 1024 TOPS(INT4).
메모리: HBM3 모듈, 총 대역폭 1.5TB/s, 용량 48GB, 온칩 SRAM 256MB.
가상화: SR-IOV(Single Root I/O Virtualization)로 최대 8개 독립 인스턴스.

[furiosa.ai/rngd 제품 페이지]
연산 성능: 512 TFLOPS(요약 스펙), 64 TFLOPS(FP8) x 8개 처리 요소. 메모리: 48GB HBM3, 대역폭
1.5TB/s, 온칩 대역폭 384TB/s, SRAM 256MB. 인터페이스: 2x HBM3(CoWoS-S, 6.0Gbps), PCIe P2P 지원.
전력: 180W TDP. 지원 포맷: BF16, FP8, INT8, INT4. Multiple-Instance/Virtualization, 안전 부팅,
모델 암호화 지원. 협력사: SK hynix, TSMC, GUC, Samsung SDS.

[furiosa.ai 블로그: Tensor Contraction Processor: AI Chip Architecture]
"the fundamental data structure for the TCP is the tensor and the fundamental operation it
performs is tensor contraction" -- GPU는 먼저 텐서를 2D 행렬로 변환(flatten)한 뒤 GEMM으로
계산하는데, "When a tensor is flattened or broken into a 2D matrix, this parallelism is often
destroyed"라고 지적. TCP는 "does not need to take the extra step of dividing tensors into 2D
matrices before performing computations"이므로 다차원 구조의 병렬성을 그대로 유지.
"The RNGD chip has eight processing elements, each with 64 'slices'", 각 슬라이스는 독립 SRAM
보유. 어텐션 연산 예시: "Key and Query partitioned tensors can be divided into one-dimensional
vectors", "Each slice takes vectors from the Query partitioned tensor and 'streams' them from
SRAM into the Dot-Product Engine". 에너지 문제: "transferring data between DRAM and the chip's
processing elements uses much more energy (as much as 10,000 times more) than performing the
computations". 재사용 메커니즘: "Data is also multicast from the SRAM of each slice to other
slices, which enables greater data reuse without additional DRAM reads". QK^T 예시: "both the
Query and Key tensors are fetched from DRAM only once, then stored in SRAM and reused repeatedly
for all QK^T operations". 레이어간 캐싱: "the chip uses the output activation of a layer directly
as the input activation of the next layer in on-chip memory – without any additional DRAM
accesses". GPU 대비 주장: "GPUs offer tremendous computational power, of course, but they
struggle to combine this with easy programmability and power efficiency", "Each generation of
GPUs consumes much more power than the last, with the latest hardware using more than 1,000W per
chip". 컴파일러: "a general compiler that can treat an entire model as a single fused operation"
로 "deploy and optimize new models automatically, even when they use a novel architecture". GPU는
"allocate resources dynamically, making it difficult to precisely predict performance". 목표:
"delivers the computational power to run high-performance generative AI models like Llama 3, as
well as significantly improved power efficiency". 접근성 철학: "If tomorrow's most useful AI
tools only run on difficult to use, extremely energy intensive chips, those tools will be out of
reach for most people".

[ISCA 2024 논문 원문 확인 완료: "TCP: A Tensor Contraction Processor for AI Workloads
(Industrial Product)", Hanjoon Kim 외 다수, Furiosa AI Inc. / INESC-ID·Lisbon대 / 서울대,
cloudfront.net에 공개 PDF 존재, 저자가 직접 PDF로 읽어서 확인함]

**Abstract 핵심**: "TCP is composed of coarse-grained processing elements (PEs) to simplify
software development... designed to be flexible enough to be utilized as a large-scale single
unit or a set of small independent units." "propose a circuit switch-based fetch network to
flexibly connect compute units to enable inter-compute unit data reuse. We also exploit input
buffer broadcast to multiple contraction engines and input buffer reuse." "designed and
fabricated in 5nm technology as the second-generation product of Furiosa AI, offering 256/512/
1024 TOPS (BF16/FP8 or INT8/INT4) with 256 MB SRAM and 1.5 TB/s 48 GB HBM3 under 150 W TDP.
Commercialization will start in August 2024." LLaMA-2 7B 케이스 스터디: "TCP is 2.7x and 4.1x
better than H100 and L40s, respectively, in terms of performance per watt."

**Table I: Characteristics of TCP** (칩 스펙 원문 그대로): Technology TSMC 5nm / Frequency 1GHz /
Dimensions 24.59 x 25.71mm (632.1 mm^2) / TDP 150W / DRAM 2x HBM3 stack, 48GB, 1.5TB/s /
On-Chip SRAM 256MB, 384TB/s / Host Connectivity PCIe Gen5 x16 (128GB/s) / MACs 512 TOPS(INT8),
1024 TOPS(INT4), 256 TFLOPS(BF16), 512 TFLOPS(FP8) / Vector Engine 512 ways per PE,
transcendental functions(exp, cos, tanh etc).

**SoC 구성(Section III)**: "TCP consists of eight PEs... Each PE can function as an independent
device from the host, similar to the multi-instance capabilities of some GPUs. Additionally, up
to four PEs can be fused to form a single, larger PE." SoC는 SR-IOV로 다중 VM 지원, 멀티테넌시.
스파스성: "The TCP architecture is not optimized for fine-grained sparsity due to its area and
power overhead and, instead, focuses on dense models... low precision has proven more effective
than pruning" (LLM 기준).

**Processing Element 구조(Fig.3)**: "the PE, which consists of a CPU core, a tensor unit (TU) for
executing large-scale tensor operations, and a tensor DMA engine (TDMA) for transfers of
tensors." TU: "32 MB of SRAM and is capable of 64 TOPS." CPU 코어: "64 KB of L1 I/D caches and
256 KB of L2 cache... 3.5 MB scratch pad memory" (예측가능한 성능을 위해 캐시 미스 페널티를
줄이려 스크래치패드에서 코드 실행 가능). TU는 "64+1 slices, with one reserved as spare to
improve chip yields." 각 슬라이스는 메인/서브 두 실행 컨텍스트를 가지며 비동기 병렬 실행.
멀티칩: "TCP is connected via PCIe Gen5 and supports peer-to-peer (P2P) communication, allowing
PEs across multiple chips to transfer data at up to 64 GB/s in each direction." 각 PE는 독립
주소공간을 가지며 address translation unit으로 비인가 접근 차단, 이 추상화가 PE간/칩간 통신과
동적 메모리 할당의 기반.

**Tensor Unit 미세구조(Section IV)**: TU 슬라이스 = Data Memory(DM) slice + Fetch Unit(FU) +
Operation Unit(OU: Contraction/Vector/Transpose Engine) + Commit Unit(CU).
- DM slice: "16 banks, each with an 8B width, providing a maximum SRAM bandwidth of 128GB/s per
  slice." 가상주소 지원(페이지 테이블)으로 동적 연속 메모리 할당.
- Fetch Unit: 슬라이스당 메인/서브 두 개의 FU. Fetch network는 "works like a circuit-switched
  network during tensor operations, maintaining a fixed topology... There is no network
  congestion since the network is circuit-switched with strictly ordered arbitration."
- Contraction Engine(CE, Fig.6): "contains eight DPEs (dot-product engines) each of which
  performs dot products by spatially summing element-wise multiplication results... through a
  reduction tree." "Each input can hold 32 BF16 values, 64 FP8 values, 64 INT8 values, or 128
  INT4 values." "The eight DPEs share the input from the feed unit... but receive separate inputs
  from the RFs." 누산기: "The accumulation unit contains a total of 1024 accumulators."
- Vector Engine(VE, Fig.7): "Each slice's VE has a throughput of 8-way INT32 and 4-way FP32...
  the VE supports INT32/FP32 dot products as well as other arithmetic operations for
  flexibility. These facilitate rapid processing of key LLM operations like softmax and
  layer-norm." "the expand operation of the feed forward layer of LLaMA-2 can be fused with
  activation functions such as SiLU."
- Transpose Engine(TE): "transposes the last axis of a tensor with other axes within a slice."
- Commit Unit: 저장 대역폭을 8B/16B/32B/cycle 중 선택 가능(commit size parameter), 패딩 제거로
  압축 저장 지원.

**프로그래밍 인터페이스(Section V-A)**: TU 명령어 -- "dma(addr, id)"(HBM 송수신),
"load(addr, csr addr, size)"(메모리→제어레지스터 로드), "exec(id)"(텐서 축약 연산 실행),
"wait_d/e(id)"(DMA/실행 완료 대기). 전형적 시퀀스: "dma(., 0)-load()-wait_d(0)-exec(0)-
dma(., 1)-load()-wait_e(0)-exec(1)-...". PE간 통신은 메시지 패싱(IPC 메모리 영역 + head/tail
doorbell 레지스터)과 address translation으로 구현, 멀티칩에서도 동일 추상화 사용.

**End-to-End 컴파일러(Section V-C, 5단계)**:
1) Primitive Operator Conversion -- PyTorch 등 프레임워크의 방대한 연산자(2000개 이상)를
   element-wise 연산, 축별 reduction, 선형대수 연산, reshape/indexing/slice, type conversion,
   비교 연산 등 소수의 기본 연산자로 분해.
2) Tensor Kernel Generation -- 기본 연산자를 클러스터링해 read-contraction-vector-write 순서의
   커널로 묶음(연산자 융합으로 데이터 재사용 극대화, 중복 텐서 사용 제거).
3) Low-Level Operator Generation -- 커널을 저수준 연산자로 컴파일, 인접 레이어 간 텐서 shape
   불일치 시 bridge operator 삽입, 비용함수로 최적안 선택.
4) Command Generation -- 저수준 연산자를 하드웨어 기능 단위(fetch/contraction/vector/transpose
   engine 등)에 1:1 대응하는 커맨드 리스트로 변환.
5) Binary Creation through Scheduling & Resource Allocation -- 커맨드 실행 시점/버퍼 배치를
   결정(휴리스틱 + ILP(정수계획법) + 유전 알고리즘 혼합), SRAM(DM 슬라이스)/RF에 텐서 매핑.

**LLaMA-2 7B 케이스 스터디(Section VI, Table II)**: (성능/전력 비교, *스파스성 미적용 기준)
| 항목 | L40s | H100 | TCP |
|---|---|---|---|
| 공정 | TSMC 5nm | TSMC 4nm | TSMC 5nm |
| BF16/FP8(TFLOPS) | 362/733 | 989/1979 | 256/512 |
| INT8/INT4(TOPS) | 733/733 | 1979/- | 512/1024 |
| 메모리 용량(GB) | 48 | 80 | 48 |
| 메모리 대역폭(TB/s) | 0.86 | 3.35 | 1.5 |
| Host I/F | PCIe Gen4 x16 | PCIe Gen5 x16 | PCIe Gen5 x16 |
| TDP(W) | 350 | 700 | 150 |
| 지연(B=1,L=128, msec) | 14 | 7 | 8 |
| 지연(B=1,L=2K, msec) | 36 | - | 65 |
| 처리량(B=16,IL/OL=2K, tokens/sec) | 531 | - | 935 |
| 처리량(B=32,IL/OL=2K, tokens/sec) | - | 2230 | 1293 |
| Perf/Watt(B=16) | 1.52 | - | 6.24 |
| Perf/Watt(B=32) | - | 3.19 | 8.62 |

결론: "TCP has 1.7x higher peak memory bandwidth than L40s and is 1.76x faster, despite having a
57% lower TDP." "H100 has 2.2x larger memory bandwidth than TCP and is 1.72x faster. However,
H100 has a 4.7x higher TDP than TCP." 짧은 시퀀스(L=128)에서 TCP가 L40s 대비 41% 낮은 지연,
긴 시퀀스(L=2048)에서 11% 낮은 지연 -- "TCP achieves higher utilization due to its architecture
which makes better use of parallelism and data reuse available in tensor contractions."

**교훈(Section VII)**: 연산자마다 데이터 재사용 패턴이 다양해 유연한 대응 필요; SRAM 지역성과
레이어 간 텐서 이동 최적화가 핵심(레이어 출력/입력 레이아웃 불일치는 비용이 큰 레이아웃 변환을
유발); 다중 컨텍스트 지원이 데이터 이동 오버헤드를 숨기는 데 핵심적; 정확한 비용 모델이
성능/전력을 정확히 예측하는 데 필수; LLM 추론처럼 컨텍스트 길이/배치 크기가 동적으로 변하는
환경에서는 동적 shape/제어흐름 지원이 핵심(제어 레지스터를 즉시 수정하는 방식으로 지원);
매핑 문제는 축약이 임의의 축을 따라 가능해 탐색 공간이 매우 크다는 복잡성이 있음.

RTL 게이트 레벨 구현이나 실리콘 레이아웃 자체(넷리스트)는 이 논문에도, 공개 저장소에도 없음
(팹리스 기업, RTL 비공개) -- 이 사실을 명시할 것. 논문은 마이크로아키텍처를 블록 다이어그램/
표 수준으로 공개한 것이며 RTL 코드 자체는 아님.""",
    ),
    dict(
        domain="01_시스템아키텍처",
        index=2,
        topic="Warboy 1세대 NPU와 RNGD로의 세대 진화",
        sources=["http://developer.furiosa.ai/docs/latest/en/npu/warboy.html"],
        grounding="""[developer.furiosa.ai/npu/warboy.html]
PE 구조: "Warboy consists of two processing elements (PE), which each delivers 32 TOPS
performance and can be deployed independently." 두 PE는 독립 운영 또는 "fused so as to minimize
response time"로 단일 PE처럼 통합 가능. 온칩 SRAM: 32MB. DRAM: "Memory Size 16 GB (max. 32 GB)",
LPDDR4X. 대역폭: "Peak Memory Bandwidth 66 GB/s". 정밀도: INT8 quantization scheme 표준 지원,
"Post Training Quantization" 도구로 부동소수점 모델 변환. 칩 스펙: "5 billion transistors",
"dimensions of 180mm²", 클럭 "2.0 GHz", 성능 "64 TOPS of INT8". 지원 워크로드: "Image
Classification, Object Detection, OCR, Super Resolution, and Pose Estimation" 등 CNN 모델,
"depthwise/group convolution" 연산에 특히 최적화. 지원 모델 형식: "TFLite or ONNX".

[RNGD와 비교용 근거 -- 앞 챕터의 rngd.html/블로그 수치 재사용]
RNGD: TCP 아키텍처(텐서 축약 직접 처리), TSMC 5nm, 1.0GHz, 256 TFLOPS(BF16)/512 TFLOPS(FP8)/
1024 TOPS(INT4), HBM3 48GB@1.5TB/s, SRAM 256MB, 8개 PE x 64 슬라이스. Warboy: 범용 CNN
아키텍처(2D GEMM 기반으로 추정되나 문서에 TCP라는 명시적 표현 없음), TSMC 공정노드 미명시,
2.0GHz, 64 TOPS(INT8 전용), LPDDR4X 16-32GB@66GB/s, SRAM 32MB, PE 2개.
공정노드는 Warboy 문서에 명시 안 됨 -- 지어내지 말 것.

[ISCA 2024 논문 "TCP: A Tensor Contraction Processor for AI Workloads" 원문 교차 확인]
RNGD(TCP) 상용화 시점: "Commercialization will start in August 2024." Warboy는 CNN
전용(depthwise/group convolution 최적화, INT8 고정)인 반면, RNGD는 텐서 축약을 하드웨어
기본 연산으로 삼아 LLM/멀티모달까지 범용적으로 처리하도록 세대가 바뀐 것 -- 이 아키텍처적
전환(2D 행렬 기반 -> 다차원 텐서 직접 축약)이 세대 간 가장 근본적인 차이.""",
    ),
    dict(
        domain="02_소프트웨어스택",
        index=1,
        topic="Furiosa 소프트웨어 스택 전체 구조",
        sources=["https://developer.furiosa.ai/v2026.3.0/en/overview/software_stack.html"],
        grounding="""[developer.furiosa.ai/overview/software_stack.html]
6개 레이어:
1) 커널 디바이스 드라이버 + 펌웨어 + PE 런타임(PERT, 최하층): "The kernel device driver enables
   the Linux operating system to recognize NPU devices and expose them as Linux device files."
   펌웨어는 NPU에서 실행, PERT가 저수준 API 제공, 호스트 런타임과 통신 및 PE 리소스 스케줄링/관리.
2) Furiosa 컴파일러: "The Furiosa Compiler optimizes model graphs and generates executable
   programs for the NPU." 최적화 작업: 그래프 레벨 최적화, 연산자 융합(operator fusion), 메모리
   할당 최적화, 스케줄링, 크로스 레이어 데이터 이동 최적화. torch.compile()의 FuriosaBackend 또는
   furiosa-llm 패키지 사용 시 투명하게 동작.
3) Furiosa 런타임: "The Runtime loads the executables generated by the Furiosa compiler and runs
   them on the NPU." 기능: NPU 프로그램 스케줄링, NPU/호스트 RAM 메모리 할당, 다중 NPU 지원 및
   통합 인터페이스.
4) Furiosa 모델 컴프레서(양자화): "The Furiosa Model Compressor is a toolkit for model
   calibration and quantization." 지원: BF16(W16A16), FP8(W8A8), INT8/INT4(계획 중).
5) Furiosa-LLM(응용 계층): "Furiosa-LLM is a high-performance inference engine for LLM models,
   such as Llama and GPT-J." 기능: vLLM 호환 API, PagedAttention, continuous batching, Hugging
   Face Hub 지원, OpenAI 호환 API 서버.
6) Kubernetes 지원(배포 계층): "FuriosaAI's device plugin enables Kubernetes clusters to
   recognize FuriosaAI's NPUs and schedule them for workloads."

[github.com/furiosa-ai/furiosa-sdk 저장소 구조 -- 이전 리서치에서 확인]
목적: "deep-neural network inference using FuriosaAI NPU chips"용 SDK, 컴파일러/프로파일러/CLI/
Python 바인딩. 최상위: cpp/(C++), python/, docs/, examples/, tests/, Dockerfile, LICENSE.txt
(Apache-2.0). 커밋 1,594개, 최신 릴리스 v0.9.0, archived/deprecated 아님.

[ISCA 2024 논문 "TCP" Section V-C: End-to-End Compiler, 5단계 -- Furiosa Compiler의 실제 동작
원리로, 위 소프트웨어 스택의 "Furiosa 컴파일러" 레이어가 내부적으로 무엇을 하는지 설명하는
근거자료]
1) Primitive Operator Conversion -- "ML frameworks like PyTorch have a huge set of operations...
   many of these can be decomposed into a small set of primitive operators." 예: element-wise
   연산, 특정 축 reduction, 선형대수 연산, reshape/indexing/slice, type conversion, 비교 연산.
2) Tensor Kernel Generation -- "cluster primitive operators to form kernels" (read-contraction-
   vector-write 순서 단위), "clustering process aims to maximize data reuse by fusing operators
   and eliminating redundant tensor usage."
3) Low-Level Operator Generation -- 커널을 저수준 연산자로 변환, 인접 레이어 간 lowered shape
   불일치 시 bridge operator 삽입, 비용 함수로 최적 옵션 선택.
4) Command Generation -- 저수준 연산자를 하드웨어 서브유닛(fetch/contraction/vector/transpose
   engine 등)에 대응하는 커맨드 리스트로 변환(대체로 1:1, 버퍼/RF 크기 고려해 세분화).
5) Binary Creation through Scheduling & Resource Allocation -- "a mix of heuristics, ILP (integer
   linear programming), and genetic algorithms"로 커맨드 실행 시점/메모리 오버랩을 스케줄링,
   SRAM(DM 슬라이스)/RF에 텐서 매핑 후 실행 파일 생성. 목표: "reduce memory pressure... run
   memory operations concurrently with computations."

[developer.furiosa.ai/get_started/prerequisites.html -- 실제 설치 절차]
지원 OS: "Ubuntu 22.04 LTS (or Debian Bookworm) or later, or Rocky Linux 10 / RHEL 10", 최소
커널 "Linux Kernel 6.3 or later". 설치(APT): `sudo apt install build-essential
linux-modules-extra-$(uname -r)` 후 `sudo apt install furiosa-driver-rngd furiosa-smi`. 설치
확인: `furiosa-smi info`로 NPU 목록 조회. 이는 소프트웨어 스택의 최하층(커널 드라이버 + 펌웨어)
설치 과정과 직접 대응됨.

[developer.furiosa.ai/overview/roadmap.html -- 스택의 실제 개발 이력]
최신 버전 2026.3.0. 2025 Q3-Q4에 프리픽스 캐싱 완료, 텐서 병렬화 Phase 2(칩 간 지원), 세밀한
FP8 양자화(동적/혼합) 구현. 2026 Q1-Q2에 Qwen3 MoE/gpt-oss/K-EXAONE/Solar-Open 지원 및 FXB
(Furiosa Executable Bundle) 형식, Responses API, Data Parallel 라우터 완료, ARM64(aarch64) 지원
확대. 2026 Q3 계획: EXAONE 4.5/Qwen 3.6/Gemma 4 지원, 계층적 KV 캐싱/오프로딩, 투기적 디코딩
(speculative decoding), PD(prefill/decode) 분리. 이는 "Furiosa-LLM(응용 계층)"이 정적으로
고정된 게 아니라 분기별로 빠르게 기능이 추가되는 활성 개발 스택임을 보여줌.""",
    ),
    dict(
        domain="03_Furiosa-LLM런타임",
        index=1,
        topic="Furiosa-LLM 서빙: OpenAI 호환 API와 Prefix Caching",
        sources=["https://developer.furiosa.ai/v2026.3.0/en/furiosa_llm/intro.html",
                  "https://developer.furiosa.ai/v2026.3.0/en/furiosa_llm/furiosa-llm-serve.html",
                  "https://developer.furiosa.ai/v2026.3.0/en/furiosa_llm/prefix-caching.html"],
        grounding="""[furiosa_llm/intro.html]
정의: "a high-performance inference engine for large language models (LLMs) and multi-modal
(vision-language) models". 메모리 최적화: "Efficient KV cache management with PagedAttention",
"Radix-tree prefix caching for reuse of shared prompt prefixes", "Hybrid KV cache for models that
mix sliding-window and global attention". 요청 처리: "Continuous batching of incoming requests".
양자화: "INT4, INT8, BF16, FP8, MXFP4, and NVFP4". 병렬화: "Support for data, tensor, and
pipeline parallelism across multiple NPUs". 디코딩: "greedy search, top-k/top-p, and speculative
decoding (planned)". 추가: Tool calling, structured output generation, "Chunked prefill with
mixed prefill/decode batching". API: "vLLM-compatible API (LLM, LLMEngine, AsyncLLMEngine API)"
및 OpenAI 호환 서버. 아키텍처 다이어그램은 문서에 없음.

[furiosa_llm/furiosa-llm-serve.html]
실행: `furiosa-llm serve [ARTIFACT_PATH]`, 채팅 템플릿 `--chat-template`, 도구 호출 예시
`furiosa-llm serve furiosa-ai/EXAONE-4.0-32B-FP8 --enable-auto-tool-choice --tool-call-parser
hermes`, reasoning 예시 `furiosa-llm serve furiosa-ai/Qwen3-32B-FP8 --reasoning-parser qwen3`.
Docker: `docker run -it --rm --device /dev/rngd:/dev/rngd --security-opt seccomp=unconfined
--env HF_TOKEN=$HF_TOKEN -v $HOME/.cache/huggingface:/root/.cache/huggingface -p 8000:8000
furiosaai/furiosa-llm:latest serve furiosa-ai/Qwen2.5-0.5B-Instruct`.
엔드포인트: /v1/chat/completions, /v1/completions, /v1/responses, /v1/embeddings, /score,
/v1/score, /rerank, /v1/rerank, /v2/rerank, GET /v1/models, GET /version, GET /metrics,
/tokenize, /detokenize, /tokenizer_info. 파라미터: model(필수, 서버에서 무시됨), messages,
stream(기본 false), temperature(기본 1.0), top_p(기본 1.0), top_k(기본 -1),
max_completion_tokens, tools, tool_choice. cURL 예시:
`curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model":
"EMPTY","messages":[{"role":"user","content":"What is the capital of France?"}]}'`. 주의: beam
search는 stream과 병행 불가. 샘플링 파라미터 우선순위: 요청 본문 > generation_config.json >
API 기본값.

[furiosa_llm/prefix-caching.html]
목적: 공통 프롬프트 접두사를 가진 여러 요청에서 이전 계산된 KV 캐시 재사용, 중복 계산 제거
(반복 시스템 프롬프트/공통 명령 템플릿/문서 기반 QA에 유용). 동작: 스케줄러가 자동 관리, 캐시
항목 저장 후 새 요청과 대조, 일치 항목 재사용. "토큰 레벨에서 작동하며 효율적인 접두사 매칭을
위해 radix tree 데이터 구조를 사용", 가장 긴 토큰 정확 일치의 KV 블록 재사용. 하이브리드
어텐션 모델은 "전역 어텐션과 슬라이딩 윈도우 어텐션이 동일한 범위에서 유효할 때만" 접두사 재사용
가능. 성능: "긴 공유 접두사를 가진 요청에서 첫 토큰까지의 시간이 50~90% 단축". 기본 활성화,
비활성화 옵션: `furiosa-llm serve --no-enable-prefix-caching ...`. 메모리 압력 증가 시 자동 축출.

[furiosa_llm/reference.html -- API 클래스 목록]
주요 클래스: LLM class, SamplingParams class, PoolingParams class, ArtifactBuilder(및
ArtifactConfig, ArtifactMetadata), LLMEngine class, AsyncLLMEngine class. 관련 기능 섹션:
구조화된 출력(Structured Output), 도구 호출(Tool Calling), 비전-언어 모델(Vision-Language
Models), 프리픽스 캐싱, 하이브리드 KV 캐시 관리. (각 클래스의 메서드 시그니처/파라미터 상세는
이 목차 페이지에는 없음 -- "명시되지 않음"으로 처리할 것.)

[furiosa_llm/k8s_deployment.html -- 실제 배포 요구사항]
배포 5단계: 1) Hugging Face 토큰용 Kubernetes Secret 생성 2) 모델 캐시용 PVC(Persistent Volume
Claim) 구성 3) Furiosa-LLM 서버 Deployment 생성 4) Service로 외부 노출 5) 엔드포인트 테스트로
검증. 요구사항: "Furiosa RNGD 장치가 장착된 Kubernetes 클러스터", 동적 볼륨 프로비저닝 지원
스토리지 클래스, HF 계정/토큰. 리소스 권장치: "1개 RNGD 카드당 10 CPU 코어 및 100GB 메모리",
디바이스 리소스 `furiosa.ai/rngd: "1"`. 헬스체크: `initialDelaySeconds: 180`(대형 모델 로딩
대비), 경로 `/health`(포트 8000). 스토리지: `/root/.cache/huggingface` 마운트, PVC 권장
(에피머럴 스토리지는 디스크 압박 시 캐시 제거 위험).

[huggingface.co/furiosa-ai/gpt-oss-120b 모델 카드 -- 실사용 예시]
서버 실행: `furiosa-llm serve furiosa-ai/gpt-oss-120b`. Python 클라이언트:
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
response = client.chat.completions.create(
    model="furiosa-ai/gpt-oss-120b",
    messages=[{"role": "user", "content": "질문"}],
)
```
추론 강도 제어: `extra_body={"reasoning_effort": "high"}`. "RNGD에서 gpt-oss-120b는 32 PE의
텐서-병렬 크기로 실행되며, 이는 4개의 RNGD 카드에 매핑"됨(117B 파라미터, 하모니 응답 형식으로
추론 내용 자동 파싱). 이 실사용 예시는 다음 챕터(Model Parallelism)의 tensor_parallel_size
제약과 연결됨.""",
    ),
    dict(
        domain="03_Furiosa-LLM런타임",
        index=2,
        topic="Model Parallelism: Tensor/Pipeline/Data Parallelism",
        sources=["https://developer.furiosa.ai/v2026.3.0/en/furiosa_llm/model-parallelism.html"],
        grounding="""[furiosa_llm/model-parallelism.html]
Tensor Parallelism(TP): 지원함. "각 레이어를 특정 차원을 따라 여러 청크로 분할", "각 디바이스는
전체 레이어의 1/N만 보유". 효과: 가중치/KV캐시/활성화 메모리 요구량 감소, 단일 디바이스 메모리
용량을 넘는 대형 모델 지원, 배치/시퀀스 확대 가능. 한계: "TP 정도가 너무 높으면 통신 오버헤드가
성능 저하를 초래".
Pipeline Parallelism(PP): 지원함. "모델을 수직으로(일반적으로 레이어 수준에서) 여러 디바이스에
분할". 특징: 메모리 절감, 처리량 증대(지연시간 증가 대가), 각 디바이스가 모델의 다른 부분을
순차 처리.
설정: ArtifactBuilder API의 `tensor_parallel_size`, `furiosa-llm serve`의
`--pipeline-parallel-size`(`-pp`), `--data-parallel-size`(`-dp`). LLM/LLMEngine/AsyncLLMEngine
에서도 지정 가능.
제약: 2026.3.0 릴리스 기준 "tensor_parallel_size 파라미터는 4 또는 8만 가능". 핵심 규칙:
"tensor_parallel_size x pipeline_parallel_size x data_parallel_size의 곱은 머신의 전체 PE 수와
같아야 함". 예시(RNGD 카드 4개, 각 8 PE, 총 32 PE): tensor_parallel_size=8,
pipeline_parallel_size=4, data_parallel_size=1 / 또는 tensor_parallel_size=4,
pipeline_parallel_size=2, data_parallel_size=2.
[앞 챕터 근거 재사용] RNGD 1개 칩 = PE 8개(각 PE 64+1 슬라이스, 1개는 예비), TCP 아키텍처.

[huggingface.co/furiosa-ai/gpt-oss-120b 모델 카드 -- 실제 다중 카드 배치 사례]
"RNGD에서 gpt-oss-120b(117B 파라미터)는 32 PE의 텐서-병렬 크기로 실행되며, 이는 4개의 RNGD
카드에 매핑"됨. RNGD 카드 1개 = PE 8개이므로, 카드 4개 = 총 32 PE. 이는 model-parallelism.html의
제약("tensor_parallel_size는 4 또는 8만 가능", "tensor_parallel_size x pipeline_parallel_size x
data_parallel_size = 전체 PE 수")과 함께 놓고 보면, 32 PE 전체를 하나의 텐서-병렬 그룹으로 쓴
것인지(tensor_parallel_size=8이면서 카드 4장에 걸쳐 파이프라인/데이터 병렬을 조합한 것인지)
모델 카드 원문만으로는 정확한 tp/pp/dp 조합까지는 특정되지 않음 -- "모델 카드에 tp=32라는
명시적 표현은 없고 '32 PE 텐서-병렬 크기'라고만 되어 있어, 정확한 파라미터 조합은 근거 자료에
명시되지 않음"이라고 다룰 것. 다만 32 = tensor_parallel_size(8) x pipeline_parallel_size(4) x
data_parallel_size(1) 조합이 model-parallelism.html의 예시와 정확히 일치하는 조합 중 하나임은
사실.""",
    ),
    dict(
        domain="04_오픈소스와모델생태계",
        index=1,
        topic="GitHub 오픈소스 저장소 구조: furiosa-sdk와 furiosa-models",
        sources=["https://github.com/furiosa-ai/furiosa-sdk", "https://github.com/furiosa-ai/furiosa-models"],
        grounding="""[github.com/furiosa-ai/furiosa-sdk]
목적: "deep-neural network inference using FuriosaAI NPU chips"용 SDK -- 컴파일러, 프로파일러,
CLI 도구, Python 바인딩 제공. 최상위 구조: .github/, .prow/, jenkins/, kubernetes/, tekton/
(CI/CD), cpp/(C++ 코드), python/(Python 코드), docs/, examples/, tests/, Dockerfile, README.md,
LICENSE.txt(Apache-2.0), bors.toml, CHANGELOG.md. 언어: Python + C++. 상태: 활성(archived 아님,
deprecated 문구 없음), 총 커밋 1,594개, 최신 릴리스 v0.9.0.

[github.com/furiosa-ai/furiosa-models]
목적: "FuriosaAI NPU를 위한 공개 모델 동물원" -- 학습/데모용 사전학습·양자화 모델 제공, ONNX/
tflite 표준이라 CPU/GPU에서도 실행 가능, NPU용 최적화 전후처리 유틸리티와 컴파일러 설정 포함.
최상위 구조: .dvc, .github/workflows, docker/, docs/, licenses/, furiosa/models(핵심 코드),
tekton/, tests/, pyproject.toml, Makefile. 포함 모델: 이미지 분류(ResNet50, EfficientNetB0,
EfficientNetV2-S), 물체 감지(SSDMobileNet, SSDResNet34, YOLOv5M/L), 자세 추정(YOLOv7w6Pose).
상태: 최신 릴리스 v0.10.2(2024-05-29), 총 커밋 357개, archived/deprecated 문구 원문에서 확인 안
됨. 이 저장소들은 Warboy(1세대, INT8/ONNX/TFLite 중심) 시대의 산물로 보이며, RNGD/Furiosa-LLM
관련 코드는 이 두 저장소에 없음(별도로 furiosa-llm 패키지/컨테이너 이미지로 배포, PyPI/Docker
Hub 등 -- 이 사실은 소프트웨어 스택 챕터의 근거 자료 기반 추정이며, 저장소 원문에 명시된 것은
아님. 지어내지 말고 "추정"으로 표현할 것).

[ISCA 2024 논문 "TCP" -- 공개 저장소의 코드와 실제 컴파일러 내부 구조의 관계]
furiosa-sdk 저장소가 공개하는 것은 cpp/(컴파일러·런타임 C++ 구현으로 추정)와 python/(바인딩)
구조뿐이며, 논문에 기술된 5단계 컴파일러 파이프라인(Primitive Operator Conversion -> Tensor
Kernel Generation -> Low-Level Operator Generation -> Command Generation -> Binary Creation via
Scheduling & Resource Allocation)이나 마이크로아키텍처 세부(PE/슬라이스/DPE/CE/VE/TE, TU 명령어
dma/load/exec/wait 등)의 실제 구현 코드는 이 저장소의 공개 파일 목록만으로는 확인되지 않음 --
컴파일러의 스케줄링 알고리즘(ILP+유전 알고리즘 혼합)이나 커맨드 생성 로직이 저장소의 어느
파일에 있는지는 "근거 자료에 명시되지 않음"으로 다룰 것. 즉 이 챕터가 다루는 것은 저장소의
"공개된 폴더 구조/메타데이터" 수준이며, 그 안의 실제 알고리즘 구현은 별개 근거(논문)로만 알 수
있다는 점을 챕터 도입부에서 분명히 할 것.""",
    ),
    dict(
        domain="04_오픈소스와모델생태계",
        index=2,
        topic="Hugging Face 모델 라인업과 양자화 포맷(FP8/NVFP4A16 등)",
        sources=["https://huggingface.co/furiosa-ai", "https://huggingface.co/furiosa-ai/models",
                  "https://huggingface.co/furiosa-ai/collections"],
        grounding="""[huggingface.co/furiosa-ai]
등록 모델 47개. 대표: Qwen3-Embedding-8B(Sentence Similarity), Qwen3-Reranker-8B(Text
Classification), Qwen3-VL-32B-Thinking/Instruct(Image-Text-to-Text, 33B), gpt-oss-120b(Text
Generation, 117B), Solar-Open-100B-NVFP4A16(Text Generation, 60B). 공개 데이터셋 없음. Space
3개(OCR, MOT 등). 조직 소개: "FuriosaAI develops data center AI accelerators. Our RNGD
accelerator, currently sampling, excels at high-performance inference for LLMs and agentic AI."
각 모델은 Furiosa Executable Bundle(FXB) 포함, RNGD에서 즉시 실행 가능하게 구성. 팀 51명.

[huggingface.co/furiosa-ai/collections]
K-EXAONE: K-EXAONE-236B-A23B-NVFP4A16(138B). gpt-oss: gpt-oss-120b(117B), gpt-oss-20b(21B).
EXAONE 4: EXAONE-4.0-32B-FP8(32B). Qwen 2.5: 32B/14B/7B/0.5B-Instruct. Llama 3.3:
70B-Instruct-FP8-dynamic(71B), 70B-Instruct, 70B-Instruct-INT8. Solar Open:
Solar-Open-100B-NVFP4A16(60B). Qwen3 Generation&Pooling: 32B-FP8(33B), 8B-FP8, 4B-FP8,
30B-A3B-FP8(31B). EXAONE 3.5: 7.8B-Instruct, 32B-Instruct. DeepSeek R1 Distill: Llama-70B,
Llama-8B, Qwen-7B, Qwen-14B. Llama 3.1: Meta-Llama-3.1-8B-Instruct-FP8-dynamic(8B),
Llama-3.1-8B-Instruct-FP8, Llama-3.1-8B-Instruct.
관찰되는 양자화 포맷 표기: FP8, FP8-dynamic, INT8, NVFP4A16(NVIDIA FP4 계열 포맷으로 이름에서
유추되나, 원문에 포맷 스펙 정의는 없음 -- "이름에서 유추"라고 명시할 것). 모델 크기 표기 방식
관찰: 파라미터 수(예: 70B) 뒤에 양자화 방식이 접미사로 붙는 명명 규칙.

[개발자 문서 furiosa_llm/intro.html 재인용]
"Quantization: INT4, INT8, BF16, FP8, MXFP4, and NVFP4" -- Furiosa-LLM 런타임이 실제 지원하는
양자화 포맷 목록. Hugging Face 모델명의 NVFP4A16, FP8-dynamic 등은 이 지원 포맷 목록과 대응됨.

[huggingface.co/furiosa-ai/gpt-oss-120b 모델 카드 -- 실제 양자화 방식 확인]
"이 저장소는 openai/gpt-oss-120b를 FuriosaAI RNGD에서 실행하기 위해 Furiosa Executable Bundle
(FXB)과 함께 제공"함(원본은 Apache 2.0). 양자화 방식: "MoE 전문가 가중치는 MXFP4로 양자화되며,
주의 메커니즘, 라우터, 임베딩은 더 높은 정밀도로 유지"됨 -- 즉 모델 전체를 균일하게 양자화하지
않고 컴포넌트별로 정밀도를 차등 적용하는 혼합 정밀도(mixed precision) 방식임이 실제 모델 카드로
확인됨. 이는 이전 챕터(소프트웨어 스택)의 "Furiosa 모델 컴프레서 -- 모델 캘리브레이션/양자화
툴킷" 설명과 직접 연결되는 실사례.

[ISCA 2024 논문 재인용 -- 정밀도와 하드웨어의 관계]
CE(Contraction Engine)의 DPE는 "32 BF16 values, 64 FP8 values, 64 INT8 values, or 128 INT4
values"를 입력으로 받을 수 있음 -- 즉 저정밀도일수록 한 번에 더 많은 값을 레지스터/DPE에 채워
처리량을 높일 수 있는 구조. 이는 HF 모델명에 붙는 접미사(FP8, FP8-dynamic, INT8, NVFP4A16,
MXFP4)가 단순 "용량을 줄이는 압축"이 아니라 "DPE가 한 사이클에 처리할 수 있는 원소 개수 자체를
바꾸는" 하드웨어적 의미를 가진다는 근거가 됨.""",
    ),
]


if __name__ == "__main__":
    for ch in CHAPTERS:
        try:
            generate_chapter(ch["domain"], ch["index"], ch["topic"], ch["grounding"], ch["sources"])
        except Exception as e:
            print(f"  [실패] {ch['topic']}: {e}")
