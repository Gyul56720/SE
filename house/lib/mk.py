# -*- coding: utf-8 -*-
"""house/lib/mk -- nsw10.lib 를 만든다 = lab/lib/se10.lib + LATX1.

**왜 별도 파일인가.** se10 에는 래치가 없다(조합 셀과 플롭만 있다). 그런데 ICG(통합
클럭 게이팅 셀)는 래치를 쓴다 -- 합성하면 `$_DLATCH_N_` 이 남고, yosys 는
"Area for cell type $_DLATCH_N_ is unknown" 을 찍고, STA 는 그 셀을 못 찾아 죽는다.
se10 을 고치면 `lab/기준.json` 의 회귀 기준값이 통째로 흔들리므로 **se10 은 손대지
않고** 여기서 한 셀을 더한 사본을 만든다.

LATX1 의 표는 DFFX1 의 CK->Q 표를 그대로 쓴다(같은 구동단을 가정). 래치이므로
투명 구간의 D->Q 조합 아크도 같이 둔다 -- 그것이 없으면 STA 가 래치를 지나갈 수 없다.

    python3 house/lib/mk.py            # house/lib/nsw10.lib 를 다시 만든다
"""
from __future__ import annotations

from pathlib import Path

뿌리 = Path(__file__).resolve().parent
원본 = 뿌리.parent.parent / "lab" / "lib" / "se10.lib"
내는곳 = 뿌리 / "nsw10.lib"

_표 = '"0.04692, 0.05520, 0.08832, 0.22080"'
_천이 = '"0.14960, 0.17600, 0.28160, 0.70400"'


def _네줄(값: str) -> str:
    return (" \\\n            ".join([값 + ","] * 3 + [값]))


LATX1 = f"""
  /* LATX1 -- 레벨 센시티브 래치.  house/lib/mk.py 가 더한 것이다(se10 에는 없다).
   * ICG 가 이 셀을 쓴다: G 가 높을 때 투명, 낮을 때 붙든다.
   * 표는 DFFX1 의 CK->Q 를 그대로 쓴다(같은 구동단 가정).  면적은 플롭의 0.75 배.
   * G->Q 는 열릴 때의 아크, D->Q 는 투명 구간의 조합 아크다 -- 뒤엣것이 없으면
   * STA 가 래치를 지나가지 못한다(실측 2026-09-21: KeyError). */
  cell (LATX1) {{
    area : 19.9584;
    latch (IQ, IQN) {{ enable : "G"; data_in : "D"; }}
    pin (G) {{ direction : input; capacitance : 0.00800; }}
    pin (D) {{ direction : input; capacitance : 0.00600; }}
    pin (Q) {{ direction : output; function : "IQ";
      max_capacitance : 0.0640;
      timing () {{ related_pin : "G"; timing_type : rising_edge;
        cell_rise (dly) {{ values ( {_네줄(_표)}); }}
        cell_fall (dly) {{ values ( {_네줄(_표)}); }}
        rise_transition (dly) {{ values ( {_네줄(_천이)}); }}
        fall_transition (dly) {{ values ( {_네줄(_천이)}); }} }}
      timing () {{ related_pin : "D"; timing_sense : positive_unate;
        cell_rise (dly) {{ values ( {_네줄(_표)}); }}
        cell_fall (dly) {{ values ( {_네줄(_표)}); }}
        rise_transition (dly) {{ values ( {_네줄(_천이)}); }}
        fall_transition (dly) {{ values ( {_네줄(_천이)}); }} }} }}
  }}
"""

머리 = ("/* nsw10 = lab/lib/se10.lib + LATX1.  **손으로 적지 마라** --\n"
      " * `python3 house/lib/mk.py` 가 만든다.  se10 은 안 고친다(lab 기준값이 묶여 있다). */\n")


DFT머리 = ("/* nsw10_dft = nsw10 에서 LATX1 을 **투명한 것으로 본 뷰**.\n"
        " *\n"
        " * 스캔 시프트 중에는 ICG 의 test_en 이 1 이라 래치가 계속 열려 있다 --\n"
        " * 그 상태에서 래치는 사실상 배선이다. 스캔/ATPG 해석은 그 모드에서 하므로\n"
        " * 여기서는 Q 의 함수를 IQ(래치 상태) 대신 D(입력) 로 둔다.\n"
        " *\n"
        " * **이것은 눈속임이 아니라 모드다.** 기능 모드의 타이밍은 nsw10.lib 으로\n"
        " * 보고, 시험 모드의 논리는 이 파일로 본다. 두 파일을 섞어 쓰지 않는다. */\n")
DFT내는곳 = 뿌리 / "nsw10_dft.lib"


def 만들기() -> "tuple[Path, Path]":
    글 = 원본.read_text(encoding="utf-8")
    i = 글.rstrip().rfind("}")
    내는곳.write_text(머리 + 글[:i] + LATX1 + "}\n", encoding="utf-8")
    # 시험 모드 뷰: 래치를 투명하게 본다
    dft = (머리 + 글[:i] + LATX1 + "}\n").replace(
        'latch (IQ, IQN) { enable : "G"; data_in : "D"; }', "")
    dft = dft.replace('pin (Q) { direction : output; function : "IQ";\n      max_capacitance : 0.0640;\n      timing () { related_pin : "G"; timing_type : rising_edge;',
                      'pin (Q) { direction : output; function : "D";\n      max_capacitance : 0.0640;\n      timing () { related_pin : "G"; timing_type : rising_edge;')
    dft = DFT머리 + dft.split("*/", 1)[1].lstrip() if "*/" in dft else dft
    DFT내는곳.write_text(dft, encoding="utf-8")
    return 내는곳, DFT내는곳


if __name__ == "__main__":
    for p in 만들기():
        print(f"{p}  ({p.stat().st_size:,} bytes)")
