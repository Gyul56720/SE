# -*- coding: utf-8 -*-
"""aim/rtl 의 `include 를 펴서 house/rtl/src/nsw_aim.sv 를 낸다.

흐름(합성·DFT·PD)은 `-I` 를 안 주므로 자립형 파일이어야 한다. **베끼지 않는다** --
aim/rtl 이 진실이고 이것은 거기서 나온다. 실행: python3 aim/흐름용_RTL만들기.py
"""
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
R = 뿌리 / "aim" / "rtl"
# gf128_frob.v(배럴)은 **재서 버렸다** -- 깊이가 커서 SYN 이 -368 ns 를 냈다.
# 지금 쓰는 것은 gf128_frob_sel.v(고정 선형맵 8개 + 8:1 먹스)다.
차례 = ["gf128_sqr.v", "gf128_mul.v", "gf128_frob_sel.v", "aim_mer_inv.v"]


def 내기() -> Path:
    vh = (R / "gf128.vh").read_text(encoding="utf-8")
    머리 = ("// =====================================================================\n"
            "//  nsw_aim.sv -- Nowon Silicon Works\n"
            "//  AIM2 (KpqC AIMer v2.0) 의 역 Mersenne S-box, GF(2^128)\n"
            "//\n"
            "//  **이 파일은 생성물이다.** 진실은 aim/rtl/ 이고 aim/흐름용_RTL만들기.py\n"
            "//  가 `include 를 펴서 여기에 낸다. 손으로 고치지 마라.\n"
            "// =====================================================================\n")
    몸 = []
    for f in 차례:
        s = (R / f).read_text(encoding="utf-8").replace('`include "gf128.vh"', vh)
        몸.append(f"// ---------------------------------------------------------------- {f}\n{s}")
    out = 뿌리 / "house" / "rtl" / "src" / "nsw_aim.sv"
    out.write_text(머리 + "\n".join(몸), encoding="utf-8")
    return out


if __name__ == "__main__":
    p = 내기()
    print(f"냈다: {p} ({p.stat().st_size} 바이트)")
