# -*- coding: utf-8 -*-
"""이론서만 따로 낸다 -- `IP_Theory.pdf`.

## 왜 따로 내나

`IP_Design_Textbook.pdf` 는 이론·코드·실무를 한 권에 담는다.  그런데
**이론만 공부할 때는 그 셋이 섞여 있는 것이 방해가 된다** -- 납품 문서
템플릿이나 값매기기가 중간에 끼면 흐름이 끊긴다.

그래서 이 빌드는 **이론 장만** 모은다.  실무(W·Y·Z1~Z16·Z18~Z23)와
코드 부록은 넣지 않는다.  대신 대학원 수준의 소자·혼성신호 장(T 계열)을
더한다.

## 무엇이 이론인가

    Z_found0 ~ S_iface2   기초부터 인터페이스까지
    X1 ~ X43              심화 (고정소수점·STA·CDC·FEC·PDN 등)
    Z17                   트랜지스터 -> 게이트 -> 데이터패스
    T1 ~                  대학원 소자·혼성신호 (이 빌드에서 더한다)
"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookE import cover, toc, render, E
import bookE

# 이론 장만.  실무와 코드 부록은 뺀다.
이론 = [
    ("Z_found0",  ["ch_abstraction", "ch_boolean", "ch_sequential", "ch_circuits"]),
    ("A_found",   ["ch_lti", "ch_transform", "ch_sampling", "ch_prob", "ch_linalg"]),
    ("B_device",  ["ch_mos", "ch_cmos", "ch_timing", "ch_interconnect", "ch_analog"]),
    ("C_digital", ["ch_arith", "ch_control", "ch_cdc"]),
    ("D_arch",    ["ch_isa", "ch_pipeline", "ch_memory"]),
    ("E_dsp",     ["ch_filters", "ch_fft"]),
    ("F_comm",    ["ch_link", "ch_fec"]),
    ("G_rf",      ["ch_tline", "ch_radar"]),
    ("H_verif",   ["ch_verif", "ch_eda", "ch_sec"]),
    ("I_info",    ["ch_info", "ch_algebra", "ch_opt", "ch_discrete"]),
    ("J_blocks",  ["ch_memory_design", "ch_accel", "ch_noc", "ch_codec"]),
    ("K_wireless",["ch_wireless", "ch_protocol", "ch_reliability", "ch_modern"]),
    ("L_phys",    ["ch_semi", "ch_power", "ch_thermal", "ch_control"]),
    ("M_soft",    ["ch_hwsw", "ch_ml", "ch_image", "ch_measure"]),
    ("N_extra",   ["ch_async", "ch_physdes", "ch_stats", "ch_optics"]),
    ("Q_more",    ["ch_queue", "ch_hls", "ch_embedded", "ch_emc"]),
    ("R_crypto",  ["ch_cryptomath", "ch_test", "ch_quantum"]),
    ("P_iface",   ["ch_mipi", "ch_pcie", "ch_gmac"]),
    ("S_iface2",  ["ch_storage", "ch_display", "ch_clocking", "ch_ipxact"]),
] + [(f"X{i}_{n}", [c]) for i, n, c in [
    (1,"fixed","ch_fixed"), (2,"timing","ch_sta"), (3,"cdc","ch_cdc"),
    (4,"link","ch_linkbudget"), (5,"fec","ch_rs"), (6,"fft","ch_fft"),
    (7,"power","ch_power"), (8,"verif","ch_verifmath"), (9,"arith","ch_arith2"),
    (10,"mem","ch_mem2"), (11,"noc","ch_noc2"), (12,"ams","ch_ams"),
    (13,"ml","ch_mlhw"), (14,"physdes","ch_physdes2"), (15,"sec","ch_hwsec"),
    (16,"rel","ch_reliability2"), (17,"modern","ch_modern2"), (18,"queue","ch_perf2"),
    (19,"isa","ch_cores"), (20,"codec","ch_codec2"), (21,"control","ch_control2"),
    (22,"dsp2","ch_resample"), (23,"math","ch_complex"), (24,"linalg","ch_numlin"),
    (25,"detect","ch_detect"), (26,"opt","ch_opt2"), (27,"dft","ch_dft"),
    (28,"cache","ch_cache"), (29,"ldpc","ch_ldpc"), (30,"wireless","ch_ofdm"),
    (31,"analog","ch_analog2"), (32,"pdn","ch_pdn"), (33,"boolean","ch_boolreason"),
    (34,"synth","ch_synth"), (35,"netds","ch_hwds"), (36,"crypto","ch_cryptoeng"),
    (37,"bus","ch_bus"), (38,"isp","ch_isp2"), (39,"clock","ch_clocking2"),
    (40,"map","ch_map"), (41,"dram","ch_dram"), (42,"async","ch_reset"),
    (43,"lowpower","ch_powerintent"),
]] + [
    ("Z17_gates", ["ch_gates"]),
]

# 대학원 소자·혼성신호.  있는 것만 싣는다 (차례로 지어 나간다).
대학원 = [
    ("T1_device",   ["ch_device"]),
    ("T2_delay",    ["ch_delay"]),
    ("T3_meta",     ["ch_meta"]),
    ("T4_noise",    ["ch_noise"]),
    ("T5_sample",   ["ch_sample"]),
    ("T6_dataconv", ["ch_dataconv"]),
    ("T7_pll",      ["ch_pll"]),
    ("T8_serdes",   ["ch_serdes"]),
    ("T9_channel",  ["ch_channel"]),
    ("T10_switchcap", ["ch_switchcap"]),
    ("T11_bias",    ["ch_bias"]),
    ("T12_match",   ["ch_match"]),
    ("T13_pi",      ["ch_pi"]),
    ("T14_rel",     ["ch_reldev"]),
    ("T15_layout",  ["ch_layout"]),
    ("T16_esd",     ["ch_esd"]),
]


def body(목록):
    out, 빠진 = [], []
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
            h = fn()
            bookE._검사(모듈, f, h) if hasattr(bookE, "_검사") else None
            out.append(h)
    return "\n".join(out), 빠진


if __name__ == "__main__":
    본문, 빠진1 = body(이론)
    대학원본문, 빠진2 = body(대학원)
    full = 본문 + 대학원본문

    meta = """
<p>A graduate-level theory volume for mixed-signal and digital integrated-circuit
design. It carries the analysis a working designer must be able to do from first
principles &mdash; device operating regions, delay, metastability, noise, sampling,
data conversion, clocking, links, matching and reliability &mdash; with every number
computed at build time rather than quoted.</p>
<p><b>Theory only.</b> The practice volume (design-house workflow, deliverables,
pricing) and the source-code appendix are in the companion book,
<i>Semiconductor IP Design</i>. Nothing here depends on them.</p>
<p><b>How to read.</b> <span style="background:#eef7f2">Green</span> boxes recall
undergraduate material; <span style="background:#f4eefa">purple</span> boxes carry
graduate detail; <span style="background:#fbf2f2">red</span> boxes mark places where
real designs have failed.</p>"""
    front = cover("EECS-IP-002", "Mixed-Signal and Digital IC Design",
                  "A Graduate Theory Volume", meta) + toc(full)
    doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           '<title>Mixed-Signal and Digital IC Design</title></head><body>'
           + front + full + '</body></html>')
    render(doc, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "IP_Theory.pdf"))
    if 빠진1:
        print("이론에서 빠진 것:", 빠진1)
    if 빠진2:
        print(f"대학원 장 {len(빠진2)}개가 아직 없다 (차례로 짓는다): {빠진2[:4]} ...")
