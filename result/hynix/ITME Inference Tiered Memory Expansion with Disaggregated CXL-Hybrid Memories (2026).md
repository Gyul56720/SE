---
title: "ITME: Inference Tiered Memory Expansion with Disaggregated CXL-Hybrid Memories"
source_paper: "[[ITME Inference Tiered Memory Expansion with Disaggregated CXL-Hybrid Memories (2026)]]"
tags: [math-concept, paper-pipeline]
---

# ITME: Inference Tiered Memory Expansion with Disaggregated CXL-Hybrid Memories -- 수학/구조 정리

> 원 논문: [[ITME Inference Tiered Memory Expansion with Disaggregated CXL-Hybrid Memories (2026)]]

## 핵심 공식 (수치 포함)
### 메타데이터 SRAM 오버헤드 (Metadata SRAM Footprint)
$$ SRAM = \text{Sets} \times \text{Associativity} \times (bit_{valid} + bit_{tag} + bit_{dirty} + bit_{age}) $$

- 의미: CXL-하이브리드 메모리 내부의 32GB DRAM 캐시 상태를 추적하기 위해 필요한 온칩 SRAM 메타데이터의 총 용량을 결정하는 공식
- 등장 맥락: 테이블 2에서 4KB 캐시 라인과 16-way 세트 연관성을 가정할 때, 32GB DRAM과 1TB SSD 구성에서 19비트 인덱스와 9비트 태그를 사용하여 총 15MB의 메타데이터 SRAM이 소모됨을 분석하기 위해 사용됨
- 수치 대입 예: Sets = 512K, bit_{valid}=1, bit_{tag}=9, bit_{dirty}=1, bit_{age}=4 이며 총 비트 합이 15-bit일 때, 512K \times 16 \text{-way} \times 15 \text{ bits} \approx 15 \text{ MB (32GB DRAM, 1TB SSD 기준)}

### 대역폭 정렬 및 처리량 균형 (Bandwidth Alignment Condition)
$$ BW_{Host \leftrightarrow DRAM} \approx BW_{SSD \leftrightarrow DRAM} \approx BW_{PCIe \text{ x8}} $$

- 의미: 호스트 인터페이스 대역폭과 백엔드 SSD-to-DRAM 대역폭이 병목 현상 없이 일치해야 하드웨어 프리페처가 고속 데이터 전송을 유지할 수 있음을 나타내는 조건
- 등장 맥락: 표 3에서 2채널 DRAM과 1채널 SSD 조합이 9 GB/s의 백엔드 병목을 유발하여 호스트 측 성능을 저하시키는 문제를 해결하고, 4채널 DRAM과 2채널 SSD 조합을 통해 18 GB/s의 균형 잡힌 대역폭을 달성하기 위해 분석됨
- 수치 대입 예: 4-ch DRAM과 2-ch SSD 설정 시 Host-to-DRAM 측정 대역폭 18 GB/s와 SSD-to-DRAM 측정 대역폭 18 GB/s가 일치하여 PCIe x8 인터페이스를 포화시킴

### 쓰기 증폭 인자 및 순차 덧붙이기 쓰기 최적화 (Write Amplification Reduction)
$$ WAF = \frac{\text{Total Flash Write Bytes}}{\text{Host Write Bytes}} \to 1.0 \text{ (by Sequential-Append)} $$

- 의미: 임의 쓰기로 인한 쓰기 증폭(WAF)을 줄이고 NVMe 컨트롤러의 내부 가비지 컬렉션을 최소화하기 위해 KV 캐시 블록을 순차적 청크 단위로 덧붙여 기록하는 관계
- 등장 맥락: CXL-하이브리드 메모리의 NAND 플래시 내구성(SSD Durability)을 보장하기 위해, 동적 데이터인 KV 캐시를 조각난 업데이트 대신 512MB의 대규모 순차 청크로 기록하여 수명을 연장하는 논리에 사용됨
- 수치 대입 예: 블록 크기 128 기준 32개의 블록을 모아 512MB 청크 단위로 순차 덧붙이기 쓰기를 수행하여 WAF를 최소화하고 백엔드 처리량을 유지

### 사용자 지정 프리페치 오버헤드 비율 (Prefetch Overhead Ratio)
$$ Ratio = \frac{T_{prefetch}}{T_{transfer}} = \frac{1 \sim 3 \mu s}{1 \text{ MB chunk transfer time}} < 0.1\% $$

- 의미: mmap 및 /proc/pid/pagemap을 통한 사용자 정의 프리페치 API 호출 지연 시간이 전체 대용량 청크 전송 시간에 비해 무시할 수 있을 정도로 작음을 나타내는 공식
- 등장 맥락: 섹션 3.2에서 chm_prefetch() API가 가상 주소를 물리 주소로 변환하는 데 1~3 마이크로초가 소요되지만 1MB 청크 단위 전송 시 전체 시간의 0.1% 미만을 차지하여 성능 저하가 거의 없음을 입증할 때 사용됨
- 수치 대입 예: T_{prefetch} = 2 \mu s, 1 \text{ MB chunk transfer time} \approx 2000 \mu s \text{ 일 때, } \frac{2}{2000} = 0.1\%

## 아키텍처 구조
### CXL-Hybrid Memory Device
- 구조: Gen5 x8 CXL 인터페이스를 통해 호스트 CPU와 연결되며, 내부적으로 32GB DDR4 DRAM 캐시, SRAM 기반 메타데이터 버퍼(Hit/Miss Checker 및 Miss Line Handler 포함), 그리고 Gen5 x4 NVMe 컨트롤러를 거치는 2채널 1TB/2TB NAND Flash SSD로 구성됨
- 역할: 서버 내부 메모리 용량 한계를 극복하기 위해 테라바이트(TB) 스케일의 원격 바이트 주소 지정 가능한 메모리 확장 공간을 제공하고 백엔드 저장소 지연을 하드웨어 캐시로 은폐
- 규격 수치: DRAM: 32 GB, SSD: 2 TB (2-ch), SRAM Metadata: 15 MB ~ 16 MB, Host Interface: PCIe Gen5 x8, SSD Interface: Gen5 x4

### CPU Staging Buffers (Store Buffer & Load Ring Buffer)
- 구조: 호스트 CPU 메모리(T2) 내부에 고정 메모리(Pinned-memory)로 할당된 양방향 버퍼 구조로, GPU Eviction을 수집하는 Store Buffer와 프리페치된 데이터를 스테이징하는 Load Ring Buffer로 분리되어 비동기 이중 방향 데이터 흐름을 처리함
- 역할: GPU 실행 단계와 원격 CXL-하이브리드 메모리 간의 I/O 지연을 격리하고, 대규모 청크(512MB) 단위의 묶음 처리를 통해 대역폭을 극대화
- 규격 수치: Staging Buffer capacity: 30 GB 설정 (128GB 호스트 메모리 대비 일부 할당), Load Ring Buffer depth: 2~3 chunks

### Multi-Tier DMA Prefetching Engine
- 구조: 사용자 수준 프리페치 라이브러리, 커널 pagemap 인터페이스, CXL-Hybrid 레지스터 세트, 그리고 하드웨어 MSHR(Miss Status Holding Registers) 기반의 FIFO 큐가 상호 연결된 파이프라인 구조
- 역할: LLM 추론의 결정론적 액세스 패턴(레이어별 가중치, 순차적 KV 프리픽스)을 활용하여 다음 턴의 데이터를 미리 하드웨어/소프트웨어 공조로 DRAM 캐시 및 GPU로 적재하여 지연을 은폐
- 규격 수치: Command overhead: 1~3 microsecond (mmap 사용 시 1 us), Transfer granularity: 1 MB 내외 또는 512 MB 청크 단위

### Read-Priority I/O Scheduler
- 구조: CXL-Hybrid Memory 서버 내부에서 백엔드 SSD 쓰기 큐와 읽기 요청 큐를 모니터링하며, 읽기 요청이 발생할 경우 백엔드 쓰기를 강제로 억제하고 슬롯을 읽기에 양보하는 스케줄러 로직
- 역할: 대규모 비동기 백엔드 플래시 쓰기가 시간 민감형 읽기 요청을 차단하는 I/O 병목(Read/Write Contention)을 방지하여 일관된 고속 읽기 대역폭 보장
- 규격 수치: Write chunk unit: small regulated units, Decode phase idle windows 활용

## 핵심 개념 설명
- **결정론적 액세스 패턴 (Deterministic Access Patterns)**: 대규모 언어 모델(LLM)의 순전파(Forward Pass) 동안 모델 가중치가 엄격한 레이어 순서대로 소비되고, 에이전트/멀티턴 대화의 KV 캐시가 순차적으로 추가 및 복원되는 예측 가능한 데이터 접근 성질
  - 선행 개념: Transformer 모델의 순전파 연산 구조 및 KV 캐시(Key-Value Cache)의 생성 방식
- **바이트 주소 지정 가능 원격 메모리 확장 (Byte-Addressable Remote Memory Expansion)**: CXL 및 RDMA 프로토콜을 활용해 원격 테라바이트 스케일의 저장소(NAND Flash)를 복잡한 블록 기반 파일시스템 I/O 없이 CPU의 일반적인 Load/Store 명령어만으로 직접 접근 가능한 거대한 메모리 공간처럼 다루는 기술
  - 선행 개념: 컴퓨터 구조의 가상 메모리, NUMA 노드 아키텍처, CXL 캐시 일관성 프로토콜
- **지연 시간 은폐를 위한 파이프라인 프리페치 (Latency-Masking Pipelined Prefetching)**: 현재 레이어 L이 GPU에서 연산되는 동안, 다음 레이어 L+1의 가중치나 KV 캐시 청크를 원격 CXL-하이브리드 메모리로부터 미리 가져와(Prefetch) 데이터 이동 오버헤드를 연산 시간 뒤로 숨기는 기법
  - 선행 개념: 비동기 DMA 전송, 이중 버퍼링(Double Buffering), GPU 파이프라인 연산

## 사용 방법론
1. 대화 턴 진행 중 GPU 메모리 용량이 한계에 도달하면, 오래된 KV 캐시 블록을 비동기 DMA를 통해 호스트 CPU의 Store Buffer로 방출(Eviction)한다. 2. 방출된 블록들을 512MB 대규모 청크 단위로 묶어 Read-Priority I/O 스케줄러의 제어 하에 디코드 페이즈의 유휴 시간을 이용해 원격 CXL-하이브리드 메모리로 순차 기록한다. 3. 다음 추론 턴이 시작되기 전, 원격 매니저는 사용자 정의 프리페치 API(chm_prefetch_size 등)와 하드웨어 MSHR 큐를 호출하여 필요한 KV 청크 및 모델 가중치를 CXL-DRAM 캐시로 미리 스테이징한다. 4. 스테이징된 데이터는 멀티티어 DMA 파이프라인을 통해 호스트 Load Ring Buffer를 거쳐 GPU 메모리로 제때 전달되며, 캐시 미스 발생 시 GPU 상에서 동적 재연산(Recomputation)으로 폴백 처리한다.

## 근접 개념 -- 같이 접근하면 좋은 다른 수학
- **PagedAttention** (유사 방법론 / 소프트웨어 계층 캐시 관리)
  - 연관 이유: vLLM 내부에서 KV 캐시 메모리 단편화를 방지하기 위해 페이지 단위로 관리하는 기법으로, 본 논문의 청크 단위 하드웨어 프리페칭 구조와 결합되어 상위 레벨 메모리 최적화를 이룸
  - 파고들 방향: vLLM 아키텍처 및 PagedAttention 메모리 할당 테이블 구조
- **NVMe-oF (NVMe over Fabrics) Target Offload** (대체 접근 / 경쟁 타겟 아키텍처)
  - 연관 이유: DPU 기반 JBOF 시스템에서 네트워크 및 스토리지 스택을 오프로드하는 표준 기술로, 본 논문이 CXL-hybrid memory를 통해 소프트웨어 스택을 단순화하고 대역폭을 개선하려는 대상
  - 파고들 방향: DPU P2P(Peer-to-Peer) 통신 및 RDMA 네트워킹 표준
- **FlexGen / DeepSpeed-Inference Offloading** (응용 분야 확장 / 소프트웨어 오프로딩)
  - 연관 이유: GPU, CPU, NVMe SSD 간의 다단 계층 파티셔닝을 통해 대형 모델을 단일 GPU에서 실행하는 기법으로, ITME가 하드웨어 어시스트를 통해 극복하고자 하는 전통적 CPU 오프로드 모델
  - 파고들 방향: 하이브리드 메모리 계층에서 I/O 스케줄링 최적화 알고리즘
- **CXL Memory Pooling (CMM-H)** (일반화 / 하드웨어 기저 기술)
  - 연관 이유: DRAM과 NAND 플래시를 혼합하여 CXL 인터페이스로 확장하는 하드웨어 설계의 원형으로, 본 논문이 PCIe Gen5 및 전용 프리페치 엔진을 결합하여 LLM 추론에 특화시킨 모듈
  - 파고들 방향: 삼성 CMM-H 및 CXL 2.0/3.0 메모리 디스아게게이션 백서
