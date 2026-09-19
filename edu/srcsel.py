# -*- coding: utf-8 -*-
"""코드 부록 선별기 -- 줄 예산 안에서 **블록 단위로** 고른다.

1000쪽 목표. 2단 5.9pt 로 쪽당 약 157줄이므로 **약 157,000줄**이 목표다.
파일을 무작위로 담지 않고 **완결된 블록**(한 IP 의 rtl 디렉터리 전체 등)으로
담아, 읽는 사람이 블록 하나를 끝까지 볼 수 있게 한다.
"""
import os, sys
sys.path.insert(0, "/home/user/SE/edu")
from book import ZOO

# (존, 상대경로, 확장자들, 설명) -- 순서가 곧 부록의 순서다
묶음 = [
 ("model","kokke_tiny-AES-c",{".c",".h"},"AES 골든 모델 (C)"),
 ("model","B-Con_crypto-algorithms",{".c",".h"},"AES·SHA·MD5 C 참조 구현"),
 ("ip","secworks_aes/src/rtl",{".v"},"AES 코어 (Verilog)"),
 ("ip","secworks_sha256/src/rtl",{".v"},"SHA-256 코어 (Verilog)"),
 ("ip","lowRISC_opentitan/hw/ip/aes/rtl",{".sv"},"OpenTitan AES -- 양산 보안 RTL"),
 ("ip","lowRISC_opentitan/hw/ip/hmac/rtl",{".sv"},"OpenTitan HMAC-SHA256"),
 ("ip","lowRISC_opentitan/hw/ip/kmac/rtl",{".sv"},"OpenTitan KMAC (Keccak/SHA-3)"),
 ("ip","lowRISC_opentitan/hw/ip/csrng/rtl",{".sv"},"OpenTitan CSRNG (SP800-90A)"),
 ("ip","lowRISC_opentitan/hw/ip/entropy_src/rtl",{".sv"},"OpenTitan 엔트로피원 (SP800-90B)"),
 ("ip","lowRISC_opentitan/hw/ip/otbn/rtl",{".sv"},"OpenTitan OTBN -- 빅넘버 코프로세서"),
 ("ip","lowRISC_opentitan/hw/ip/spi_host/rtl",{".sv"},"SPI 호스트"),
 ("ip","lowRISC_opentitan/hw/ip/i2c/rtl",{".sv"},"I2C 컨트롤러"),
 ("ip","lowRISC_opentitan/hw/ip/uart/rtl",{".sv"},"UART"),
 ("ip","lowRISC_opentitan/hw/ip/usbdev/rtl",{".sv"},"USB 디바이스"),
 ("ip","lowRISC_opentitan/hw/ip/rv_timer/rtl",{".sv"},"RISC-V 타이머"),
 ("ip","lowRISC_opentitan/hw/ip/rv_dm/rtl",{".sv"},"RISC-V 디버그 모듈"),
 ("ip","lowRISC_opentitan/hw/ip/tlul/rtl",{".sv"},"TL-UL 버스 구조"),
 ("ip","lowRISC_opentitan/hw/ip/sram_ctrl/rtl",{".sv"},"SRAM 컨트롤러(스크램블)"),
 ("ip","lowRISC_opentitan/hw/ip/otp_ctrl/rtl",{".sv"},"OTP 컨트롤러"),
 ("ip","lowRISC_opentitan/hw/ip/keymgr/rtl",{".sv"},"키 관리자"),
 ("ip","lowRISC_opentitan/hw/ip/lc_ctrl/rtl",{".sv"},"수명주기 컨트롤러"),
 ("ip","lowRISC_opentitan/hw/ip/flash_ctrl/rtl",{".sv"},"플래시 컨트롤러"),
 ("ip","lowRISC_opentitan/hw/ip/prim/rtl",{".sv"},"OpenTitan 기본 셀 라이브러리"),
 ("ip","chipsalliance_caliptra-rtl/src/sha512/rtl",{".sv",".v"},"Caliptra SHA-512"),
 ("ip","chipsalliance_caliptra-rtl/src/sha256/rtl",{".sv",".v"},"Caliptra SHA-256"),
 ("ip","chipsalliance_caliptra-rtl/src/hmac/rtl",{".sv",".v"},"Caliptra HMAC"),
 ("ip","chipsalliance_caliptra-rtl/src/ecc/rtl",{".sv",".v"},"Caliptra ECC (P-384)"),
 ("ip","chipsalliance_caliptra-rtl/src/aes/rtl",{".sv",".v"},"Caliptra AES"),
 ("ip","pulp-platform_common_cells/src",{".sv"},"PULP 기본 셀 (FIFO·CDC·아비터)"),
 ("ip","pulp-platform_axi/src",{".sv"},"AXI4 상호연결"),
 ("ip","pulp-platform_apb/src",{".sv"},"APB"),
 ("ip","pulp-platform_riscv-dbg/src",{".sv"},"RISC-V 디버그"),
 ("ip","openhwgroup_cv32e40p/rtl",{".sv"},"CV32E40P RISC-V 코어"),
 ("ip","openhwgroup_cv32e40p/bhv",{".sv"},"CV32E40P RVFI 트레이스"),
 ("ip","YosysHQ_picorv32",{".v"},"PicoRV32 -- 초소형 RISC-V"),
 ("ip","olofk_serv/rtl",{".v"},"SERV -- 비트직렬 RISC-V"),
 ("ip","ZipCPU_wb2axip/rtl",{".v"},"형식검증된 AXI/Wishbone 브리지"),
 ("ip","alexforencich_verilog-pcie/rtl",{".v"},"PCIe 코어"),
 ("ip","openhwgroup_core-v-verif/lib/uvm_agents/uvma_rvfi",{".sv"},"RVFI UVM 에이전트"),
 ("ip","openhwgroup_core-v-verif/cv32e40p/tb/uvmt",{".sv"},"step-compare 테스트벤치"),
 ("model","riscv-software-src_riscv-isa-sim/riscv",{".h",".cc"},"Spike ISS -- 참조모델 본체"),
 ("model","riscv-software-src_riscv-isa-sim/softfloat",{".h",".c"},"Berkeley SoftFloat"),
 ("model","riscv_sail-riscv/model",{".sail"},"RISC-V 형식 명세 (Sail)"),
 ("model","aff3ct_aff3ct/src/Module/Encoder",{".cpp",".hpp"},"AFF3CT 부호기 (RS·LDPC·Polar)"),
 ("model","aff3ct_aff3ct/src/Module/Decoder",{".cpp",".hpp"},"AFF3CT 복호기"),
 ("model","accellera-official_systemc/src/sysc/kernel",{".h",".cpp"},"SystemC 커널"),
 ("model","accellera-official_systemc/src/tlm_core/tlm_2",{".h"},"TLM 2.0"),
 ("model","jgaeddert_liquid-dsp/src/filter/src",{".c",".h"},"liquid-dsp 필터"),
 ("model","jgaeddert_liquid-dsp/src/equalization/src",{".c",".h"},"liquid-dsp 등화기"),
 ("model","jgaeddert_liquid-dsp/src/modem/src",{".c",".h"},"liquid-dsp 변복조"),
 ("model","cocotb_cocotb/src/cocotb",{".py"},"cocotb -- 파이썬 공동시뮬"),
]


def 고르기(예산=157000, 파일당최대=6000, 묶음상한=5200):
    """두 번 훑는다.

    **첫 판은 틀렸다** -- 앞 묶음이 예산을 다 먹어 CPU 코어 · Spike · SystemC ·
    aff3ct 가 통째로 잘렸다.  코드 1000쪽이 OpenTitan 하나로 채워지면 교재로서
    쓸모가 없다.  그래서 1차로 묶음마다 `묶음상한` 까지만 담아 **다양성을 먼저
    확보**하고, 2차로 남은 예산을 큰 묶음에 돌려준다.
    """
    후보 = []
    for 존, 밑, 확장, 설명 in 묶음:
        뿌리 = os.path.join(ZOO[존], 밑)
        if not os.path.isdir(뿌리):
            continue
        fs_ = []
        for r, ds, fs in os.walk(뿌리):
            ds[:] = [d for d in ds if d not in (".git", "__pycache__")]
            for f in sorted(fs):
                if os.path.splitext(f)[1] not in 확장:
                    continue
                p = os.path.join(r, f)
                try:
                    n = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
                except OSError:
                    continue
                if 0 < n <= 파일당최대:
                    fs_.append((존, os.path.relpath(p, ZOO[존]), n))
        if fs_:
            후보.append([설명, fs_, 0])          # [설명, 전체파일, 담은수]

    총 = 0
    # 1차 -- 묶음마다 상한까지
    for c in 후보:
        줄 = 0
        for i, (z, p, n) in enumerate(c[1]):
            if 줄 + n > 묶음상한 or 총 + n > 예산:
                break
            줄 += n; 총 += n; c[2] = i + 1
    # 2차 -- 남은 예산을 순서대로 돌려준다
    바뀜 = True
    while 총 < 예산 and 바뀜:
        바뀜 = False
        for c in 후보:
            if c[2] >= len(c[1]):
                continue
            z, p, n = c[1][c[2]]
            if 총 + n <= 예산:
                총 += n; c[2] += 1; 바뀜 = True

    난것, 로그 = [], []
    for 설명, fs_, k in 후보:
        if k:
            난것.append((설명, fs_[:k]))
            로그.append(f"  {설명[:40]:42s} {k:4d}파일 "
                        f"{sum(n for _,_,n in fs_[:k]):8,d}줄")
    return 난것, 총, 로그


if __name__ == "__main__":
    g, t, log = 고르기()
    print("\n".join(log))
    print(f"\n묶음 {len(g)}개, 총 {t:,}줄  (쪽당 157줄 가정 -> 약 {t//157:,}쪽)")
