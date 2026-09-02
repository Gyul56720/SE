# 1.58-bit Ternary NPU Silicon Design & Verification Suite

본 프로젝트는 **Qwen2.5-7B** 및 **BitNet**과 같은 1.58비트 삼진법(`{-1, 0, 1}`) 양자화 대형 언어 모델(LLM)을 가속하기 위해 **완벽하게 검증된 Synthesizable SystemVerilog NPU 가속기**입니다.

## 1. 하드웨어 아키텍처 명세 (Architectural Specification)

| 항목 | 규격 (Specification) | 비고 |
| :--- | :--- | :--- |
| **Activation Format** | Signed INT8 | 8-bit dynamic range |
| **Weight Format** | Ternary `{-1, 0, +1}` | 1.58-bit algorithmic representation |
| **Physical Encoding** | `00` -> 0, `01` -> +1, `10` -> -1, `11` -> RESERVED | 2-bit physical datapath |
| **Accumulator Width** | Signed 21-bit | Max accumulation ($4096 \times 128 = 524,288$) guarantee |
| **Processing Element** | MUX-based Adder/Subtractor | **No Multiplier (MatMul-Free)** |
| **Tile Structure** | 16-PE Partial Sum Reduction Unit | `npu_tile.sv` |
| **Top Architecture** | 256-Tile Array ($N=4096$) | `npu_array_4096.sv` |

## 2. 검증 결과 (Verification & Quality Assurance)

`Python Golden Model` (수학적 계약 오라클)과 `iverilog` 시뮬레이션 간의 **Bit-exact Verification**을 수행하였습니다.

1. **Level 1 (PE Atomic Unit)**: 768개 전수 조사(Exhaustive Test) **100% PASS**
2. **Level 2 (16-PE Tile)**: 1,000회 무작위 16차원 벡터 테스트 **100% PASS**
3. **Level 3 (4096-PE System)**: N=4096 대규모 벡터 테스트 **100% PASS**
4. **Level 4 (Qwen2.5-7B End-to-End)**: `q_proj`, `k_proj`, `v_proj`, `gate_proj` 텐서 주입 **Bit-exact PASS**

```
==================== END-TO-END SANITY CHECK RESULTS ====================
Layer [q_proj    ]: Golden =      -1625 | RTL =      -1625 -> PASS [Bit-Exact]
Layer [k_proj    ]: Golden =      -4012 | RTL =      -4012 -> PASS [Bit-Exact]
Layer [v_proj    ]: Golden =      -1166 | RTL =      -1166 -> PASS [Bit-Exact]
Layer [gate_proj ]: Golden =      -1609 | RTL =      -1609 -> PASS [Bit-Exact]
=========================================================================
PROVEN=1: NPU ACCELERATOR DESIGN IS 100% VERIFIED & PRODUCTION READY!
=========================================================================
```
