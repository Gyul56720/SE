---
title: "FIFO (computing and electronics)"
domain: 01_디지털설계검증
tags: [book, concept, 01_디지털설계검증]
source_wikipedia: "https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics)"
referenced_repos: ['jatinkoshiya/fifo_sv', 'andreixmihai/Systemverilog_fifo', 'seungchan-park/systemverilog_fifo', 'Rajat205nyamagoudar/systemverilog-fifo-testbench', 'nfgithb/fifo', 'DragonDairy/fifo_verification_sv']
---

# 02. FIFO (computing and electronics)

## 1. 왜 알아야 하는가

반도체 설계 및 검증 분야에서 FIFO는 서로 다른 데이터 레이트로 동작하는 하드웨어 장치나 소프트웨어 간의 버퍼링 및 흐름 제어를 위해 필수적으로 사용되는 구조입니다. 데이터 구조 조작 및 큐 관리를 정확히 이해해야 시스템 간의 데이터 손실 없는 통신과 안정적인 스케줄링을 구현할 수 있습니다.

## 2. 정의와 이론

컴퓨터 및 시스템 이론에서 선입선출(First In, First Out, FIFO)은 데이터 구조(주로 데이터 버퍼)의 조작을 조직화하는 방법으로, 가장 오래된(첫 번째) 항목 즉 큐의 "헤드"가 가장 먼저 처리되는 방식입니다. FIFO는 하드웨어 전자 논리 회로 또는 소프트웨어로 구현될 수 있으며, 디스크 제어기의 디스크 스케줄링 알고리즘, 통신 네트워크 브리지, 스위치, 라우터, 운영체제 스케줄링, 디지털 비디오 및 오디오 스트림 버퍼링 등 다양한 응용 분야에서 널리 사용됩니다. 전자적 FIFO는 유한한 간격 동안 서로 다른 데이터 레이트로 동작하는 하드웨어 장치 간 또는 소프트웨어와 하드웨어 장치 간의 버퍼링과 흐름 제어에 사용되며, 읽기 및 쓰기 메모리 주소 레지스터로 작용하는 두 개의 카운터, 메모리 배열, 상태 및 제어 로직으로 구성됩니다.

## 3. 핵심 공식

- (근거 자료에 명시된 공식 없음)

## 4. 실제 오픈소스에서의 구현/검증

실제 오픈소스 리포지토리에서 FIFO는 주로 SystemVerilog를 기반으로 설계 및 검증됩니다. 예를 들어 jatinkoshiya/fifo_sv 리포지토리에는 SystemVerilog FIFO Design and Testbench 코드가 포함되어 있으며, Rajat205nyamagoudar/systemverilog-fifo-testbench 리포지토리에서는 무작위 자극(randomized stimuli)과 자동 자체 검증(automated self-checking) 기능을 갖춘 객체 지향 SystemVerilog 테스트벤치를 사용하여 커스텀 동기식 FIFO 메모리를 시뮬레이션하고 검증합니다. 또한 DragonDairy/fifo_verification_sv 리포지토리에서는 VCS를 사용한 SystemVerilog FIFO 검증 프로젝트가 구현되어 있습니다.

### 참고 리포지토리
- [jatinkoshiya/fifo_sv](https://github.com/jatinkoshiya/fifo_sv) (SystemVerilog, ⭐2) -- This is SystemVerilog FIFO Design and Testbench code
- [andreixmihai/Systemverilog_fifo](https://github.com/andreixmihai/Systemverilog_fifo) (SystemVerilog, ⭐0) -- 
- [seungchan-park/systemverilog_fifo](https://github.com/seungchan-park/systemverilog_fifo) (SystemVerilog, ⭐0) -- 
- [Rajat205nyamagoudar/systemverilog-fifo-testbench](https://github.com/Rajat205nyamagoudar/systemverilog-fifo-testbench) (SystemVerilog, ⭐1) -- "Simulating and verifying a custom Synchronous FIFO memory using a custom Object-Oriented SystemVerilog testbench. Features randomized stimuli and automated self-checking.
- [nfgithb/fifo](https://github.com/nfgithb/fifo) (Tcl, ⭐0) -- A parametrizable systemverilog fifo
- [DragonDairy/fifo_verification_sv](https://github.com/DragonDairy/fifo_verification_sv) (SystemVerilog, ⭐0) -- SystemVerilog FIFO Verification Project using VCS.

## 5. 실무에서 흔한 함정

소프트웨어 FIFO 구현의 경우 대부분 스레드 안전(thread safe)하지 않으므로, 한 번에 하나의 스레드만 데이터 구조 체인을 조작할 수 있도록 락(locking) 메커니즘이 필요하다는 점을 간과하기 쉽습니다.

## 6. 추론 예시

1단계: 서로 다른 데이터 레이트를 가진 하드웨어 장치 간의 데이터 유실을 방지하기 위한 버퍼링 요구사항을 파악합니다. 2단계: 큐의 가장 오래된 데이터가 먼저 처리되도록 보장하는 FIFO 구조를 적용하기로 판단합니다. 3단계: 읽기 및 쓰기 메모리 주소 레지스터로 동작하는 두 개의 카운터와 동시 읽기/쓰기를 지원하는 듀얼 포트 메모리(또는 레지스터 파일)를 설계에 반영합니다.

## 7. 다음 개념과의 연결

FIFO 개념은 큐잉 이론(Queueing theory), SCHED_FIFO 등과 직접적으로 연결되며, 추가적으로 Leaky bucket approach 등의 트래픽 쉐이핑 및 흐름 제어 방법론으로 학습을 확장할 수 있습니다.
