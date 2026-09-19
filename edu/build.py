# -*- coding: utf-8 -*-
"""교안 조립 · 렌더."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표지, 목차, 소스부록, 렌더, 줄수, 동물원
import p1_manual, p2_theory, p3_aes, p3_blocks, p4_chip

z, byrepo = 동물원()
총파일 = sum(len(v) for v in z.values())
총줄 = sum(f["줄"] for v in z.values() for f in v)

설명 = f"""
<p><b>이 교안은 실제로 팔리거나 팔렸던 IP 의 소스를 근거로 쓰였다.</b> 인용하는 코드는
전부 파일과 줄번호로 가리키며, 손으로 옮겨 적은 코드는 없다 &mdash; 모든 코드 인용은
디스크의 파일을 읽어 줄번호와 함께 찍는다.</p>
<p><b>수집한 실물:</b> {총파일:,}개 파일, <b>{총줄:,}줄</b>.
설계 IP(OpenTitan &middot; Caliptra &middot; CVA6 &middot; Corundum &middot; PULP &middot;
verilog-ethernet/pcie)와 모델링 자산(Spike &middot; Sail &middot; SystemC &middot;
Verilator &middot; gem5 &middot; aff3ct &middot; OpenSSL &middot; liquid-dsp)을 모두
받아 두었다.</p>
<p><b>읽는 법.</b> <span style="background:#eef7f2">초록 상자</span>는 학부 수준 복습,
<span style="background:#f4eefa">보라 상자</span>는 석사 수준 상세,
<span style="background:#fbf2f2">붉은 상자</span>는 실무에서 사고가 났던 자리다.</p>
"""

본문 = "\n".join([
    # 제1부 -- 실무 매뉴얼
    p1_manual.ch1(), p1_manual.ch2(), p1_manual.ch3(),
    p1_manual.ch4(), p1_manual.ch5(),
    # 제2부 -- 필수 이론
    p2_theory.ch_num(), p2_theory.ch_time(), p2_theory.ch_dv(),
    # 제3부 -- IP 블록별
    p3_aes.aes(), p3_blocks.axi(), p3_blocks.fifo(),
    p3_blocks.cpu(), p3_blocks.fec(),
    # 제4부 -- 칩 · 표준 · 논문 · 아이디어
    p4_chip.ch_soc(), p4_chip.ch_std(), p4_chip.ch_paper(), p4_chip.ch_idea(),
])

부록항목 = [
    # --- 모델링: 골든 모델 ---
    ("model", "kokke_tiny-AES-c/aes.c"),
    ("model", "kokke_tiny-AES-c/aes.h"),
    ("model", "B-Con_crypto-algorithms/sha256.c"),
    ("model", "B-Con_crypto-algorithms/aes.c"),
    # --- 모델링: ISS ---
    ("model", "riscv-software-src_riscv-isa-sim/riscv/insns/add.h"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/insns/mulh.h"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/insns/fadd_d.h"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/decode.h"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/processor.h"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/execute.cc"),
    ("model", "riscv-software-src_riscv-isa-sim/riscv/mmu.h"),
    # --- 설계: AES RTL ---
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_sbox_lut.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_sbox_canright.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_sbox_dom.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_sbox.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_mix_columns.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_mix_single_column.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_key_expand.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_core.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_control.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_control_fsm.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_control_fsm_n.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_control_fsm_p.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_prng_masking.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_prng_clearing.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_ctr.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_core.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes.sv"),
    ("ip", "lowRISC_opentitan/hw/ip/aes/rtl/aes_pkg.sv"),
    # --- 설계: 암호 (secworks) ---
    ("ip", "secworks_aes/src/rtl/aes_core.v"),
    ("ip", "secworks_aes/src/rtl/aes_encipher_block.v"),
    ("ip", "secworks_aes/src/rtl/aes_sbox.v"),
    ("ip", "secworks_sha256/src/rtl/sha256_core.v"),
    ("ip", "secworks_sha256/src/rtl/sha256_w_mem.v"),
    # --- 설계: 기본 셀 (CDC · FIFO · 아비터) ---
    ("ip", "pulp-platform_common_cells/src/cc_fifo_v3.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_cdc_2phase.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_cdc_fifo_gray.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_sync.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_rr_arb_tree.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_stream_fifo.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_stream_register.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_spill_register.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_gray_to_binary.sv"),
    ("ip", "pulp-platform_common_cells/src/cc_binary_to_gray.sv"),
    # --- 설계: AXI ---
    ("ip", "pulp-platform_axi/src/axi_pkg.sv"),
    ("ip", "pulp-platform_axi/src/axi_demux.sv"),
    ("ip", "pulp-platform_axi/src/axi_mux.sv"),
    ("ip", "pulp-platform_axi/src/axi_xbar.sv"),
    ("ip", "pulp-platform_axi/src/axi_cut.sv"),
    ("ip", "pulp-platform_axi/src/axi_err_slv.sv"),
    # --- 검증: 비교 장치 ---
    ("ip", "openhwgroup_core-v-verif/cv32e40p/tb/uvmt/uvmt_cv32e40p_step_compare.sv"),
    ("ip", "openhwgroup_core-v-verif/lib/uvm_agents/uvma_rvfi/uvma_rvfi_instr_mon.sv"),
    ("ip", "openhwgroup_core-v-verif/lib/uvm_agents/uvma_rvfi/uvma_rvfi_assert.sv"),
    ("ip", "openhwgroup_cv32e40p/bhv/cv32e40p_rvfi.sv"),
]
# 없는 경로는 조용히 빠지지 않게 **먼저 확인**한다.
import os
from book import ZOO
빠진것 = [(z, p) for z, p in 부록항목 if not os.path.exists(os.path.join(ZOO[z], p))]
if 빠진것:
    print("경로 없음 -- 부록에서 제외:")
    for z, p in 빠진것:
        print("   ", z, p)
부록항목 = [(z, p) for z, p in 부록항목 if (z, p) not in 빠진것]
부록, 부록줄 = 소스부록(
    부록항목, "A", "부록 A  본문이 인용한 소스 전문",
    "본문이 가리킨 파일을 전문 그대로 싣는다. 줄번호는 파일의 실제 줄번호이므로 "
    "본문의 <code>파일:시작-끝</code> 참조를 그대로 따라갈 수 있다.")

전체 = 본문 + 부록
앞 = 표지("EDU-IP-001", "모델링 팀 실무 교안",
          "실제 판매 IP 로 배우는 아키텍처 · 설계 · 모델링 · 검증", 설명) + 목차(전체)

doc = ('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
       '<title>모델링 팀 실무 교안</title></head><body>'
       + 앞 + 전체 + '</body></html>')

렌더(doc, "/home/user/SE/edu/모델링팀_실무교안.pdf")
print(f"부록 소스 {부록줄:,}줄")
