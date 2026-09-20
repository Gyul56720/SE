# -*- coding: utf-8 -*-
"""se10 표준셀 라이브러리를 **계산해서** 낸다 -- 손으로 적지 않는다.

## 왜 짓나

파운드리의 `.lib` 는 받을 수도 팔 수도 없다.  그렇다고 수를 손으로 지어 넣으면
그 수가 어디서 왔는지 아무도 모르게 되고, 이 저장소가 가장 싫어하는 꼴
(**검사하지 않은 초록불**)이 된다.  그래서 **모형 하나에서 전부 계산한다.**

## 모형 -- T2 의 RC 지연 그대로

    R      = R단위 / d              d 는 구동 세기 (단위 인버터의 몇 배인가)
    Cin    = d · g · C단위          g 는 논리적 노력
    C자체  = d · p · C단위          p 는 기생 인자
    지연   = 0.69 · R · (C자체 + C부하) + 0.5 · 입력천이
    천이   = 2.2  · R · (C자체 + C부하)

`0.69 = ln 2` 는 RC 계단응답이 50 % 에 이르는 시각이고, `2.2 = ln 9` 는
10 %에서 90 %까지 걸리는 시각이다.  둘 다 유도해서 나오는 수다.

## 이 라이브러리가 어느 공정인가 -- 재서 말한다

단위 인버터(d=1)가 같은 인버터 넷을 몰 때의 지연이 FO4 다.

    R단위 = 8 kΩ, C단위 = 2 fF
    FO4 = 0.69 × 8e3 × (2 + 8) fF = 55.2 ps

FO4 55 ps 는 **180 nm 언저리**다.  그래서 VDD 를 1.8 V 로 둔다 -- T18~T22 가
쓰는 전압과 같다.  두 자리가 다른 공정을 말하면 수를 견줄 수 없다.

자리(SITE)는 사용자가 붙인 강의 화면의 LEF 그대로 0.660 × 5.040 µm 다.
"""
from __future__ import annotations

import os

# --- 모형 상수.  이 넷이 라이브러리 전체를 정한다. ---------------------------
R단위 = 8.0e3        # Ω
C단위 = 2.0e-15      # F
자리폭, 행높이 = 0.660, 5.040          # µm -- LEF SITE

# 표의 축.  ABC 는 2차원 표를 받아야 하므로 둘 다 준다.
입력천이축 = [0.010, 0.040, 0.160, 0.640]        # ns
부하축 = [0.001, 0.004, 0.016, 0.064]            # pF


def FO4():
    """단위 인버터가 같은 인버터 넷을 몰 때의 지연 (초)."""
    return 0.69 * R단위 * (1 * 1 * C단위 + 4 * 1 * C단위)


def _지연(d, p, 부하_pF, 천이_ns):
    """초 단위가 아니라 **ns** 로 돌려준다 (.lib 의 time_unit 이 1ns)."""
    R = R단위 / d
    C = d * p * C단위 + 부하_pF * 1e-12
    return 0.69 * R * C * 1e9 + 0.5 * 천이_ns


def _천이(d, p, 부하_pF):
    R = R단위 / d
    C = d * p * C단위 + 부하_pF * 1e-12
    return 2.2 * R * C * 1e9


def _자리수(셀):
    """셀 폭을 자리 수로 -- **반드시 정수**다.

    표준셀은 자리(SITE)의 정수배여야 한다.  그래야 배치가 격자에 맞고,
    합법화가 자리 경계에 딱 놓을 수 있다.  실측: 처음에 반자리(2.5)를
    허용했더니 배치 합법화가 행을 못 채우고 터졌다 -- 라이브러리 쪽 잘못을
    배치기가 대신 앓은 것이다.

    폭은 입력 용량의 합이 정한다고 본다(트랜지스터가 넓으면 자리를 먹는다).
    거기에 **자리 하나를 더한다** -- 어느 셀이나 우물 접속과 경계 간격을
    치르기 때문이다.  그래서 단위 인버터가 2 자리(1.32 µm)이고, 이 높이
    (5.04 µm)의 라이브러리에서 그 값이 실제 180 nm 셀과 비슷한 꼴이 된다.
    """
    import math as _m
    d = 셀["d"]
    if 셀.get("ff"):
        return 8 if 셀["이름"] == "DFFX1" else 9
    합 = sum(셀["g"].values())
    return max(2, int(_m.ceil(d * 합)) + 1)


# --- 셀 목록.  g 는 핀마다, p 는 셀마다. ------------------------------------
# g(논리적 노력)와 p(기생)는 T2 에서 유도한 표준값이다.  지어낸 수가 아니다.
셀들 = [
    dict(이름="INVX1",  d=1, p=1.0, 함수="!A",            g={"A": 1.0},
         감={"A": "negative_unate"}),
    dict(이름="INVX4",  d=4, p=1.0, 함수="!A",            g={"A": 1.0},
         감={"A": "negative_unate"}),
    dict(이름="BUFX2",  d=2, p=2.0, 함수="A",             g={"A": 1.0},
         감={"A": "positive_unate"}),
    dict(이름="NAND2X1", d=1, p=2.0, 함수="!(A&B)",
         g={"A": 4 / 3, "B": 4 / 3},
         감={"A": "negative_unate", "B": "negative_unate"}),
    dict(이름="NOR2X1", d=1, p=2.0, 함수="!(A|B)",
         g={"A": 5 / 3, "B": 5 / 3},
         감={"A": "negative_unate", "B": "negative_unate"}),
    dict(이름="AND2X1", d=1, p=3.0, 함수="(A&B)",
         g={"A": 4 / 3, "B": 4 / 3},
         감={"A": "positive_unate", "B": "positive_unate"}),
    dict(이름="OR2X1",  d=1, p=3.0, 함수="(A|B)",
         g={"A": 5 / 3, "B": 5 / 3},
         감={"A": "positive_unate", "B": "positive_unate"}),
    dict(이름="XOR2X1", d=1, p=4.0, 함수="(A^B)",
         g={"A": 4.0, "B": 4.0}, 감={"A": "non_unate", "B": "non_unate"}),
    dict(이름="XNOR2X1", d=1, p=4.0, 함수="!(A^B)",
         g={"A": 4.0, "B": 4.0}, 감={"A": "non_unate", "B": "non_unate"}),
    dict(이름="MUX2X1", d=1, p=4.0, 함수="(A&!S)|(B&S)",
         g={"A": 2.0, "B": 2.0, "S": 2.0},
         감={"A": "positive_unate", "B": "positive_unate", "S": "non_unate"}),
    dict(이름="AOI21X1", d=1, p=3.0, 함수="!((A1&A2)|B)",
         g={"A1": 2.0, "A2": 2.0, "B": 4 / 3},
         감={"A1": "negative_unate", "A2": "negative_unate",
            "B": "negative_unate"}),
    dict(이름="OAI21X1", d=1, p=3.0, 함수="!((A1|A2)&B)",
         g={"A1": 2.0, "A2": 2.0, "B": 4 / 3},
         감={"A1": "negative_unate", "A2": "negative_unate",
            "B": "negative_unate"}),
    dict(이름="DFFX1",  d=2, p=4.0, ff=True, 리셋=False),
    dict(이름="DFFRX1", d=2, p=4.0, ff=True, 리셋=True),
]


def _표(값내기):
    줄 = []
    for s in 입력천이축:
        줄.append('"' + ", ".join(f"{값내기(s, c):.5f}" for c in 부하축) + '"')
    return ", \\\n            ".join(줄)


def _셀글(셀):
    이름 = 셀["이름"]
    자리 = _자리수(셀)
    면적 = 자리 * 자리폭 * 행높이
    d, p = 셀["d"], 셀["p"]
    o = [f'  cell ({이름}) {{',
         f'    area : {면적:.4f};   /* {자리} 자리 */']
    if 셀.get("ff"):
        Cd = d * 1.5 * C단위 * 1e12
        Cck = d * 2.0 * C단위 * 1e12
        o.append('    ff (IQ, IQN) { clocked_on : "CK"; next_state : "D";'
                 + (' clear : "!RN";' if 셀["리셋"] else '') + ' }')
        o.append(f'    pin (CK) {{ direction : input; clock : true; '
                 f'capacitance : {Cck:.5f}; }}')
        if 셀["리셋"]:
            o.append('    pin (RN) { direction : input; capacitance : '
                     f'{Cd:.5f}; }}')
        셋업 = 0.69 * (R단위 / d) * (d * 2.0 * C단위) * 1e9 * 2      # 두 단
        홀드 = 셋업 / 3.0
        o += [f'    pin (D) {{ direction : input; capacitance : {Cd:.5f};',
              '      timing () { related_pin : "CK"; '
              'timing_type : setup_rising;',
              '        rise_constraint (con) { values ( \\',
              '            ' + _표(lambda s, c: 셋업) + '); }',
              '        fall_constraint (con) { values ( \\',
              '            ' + _표(lambda s, c: 셋업) + '); } }',
              '      timing () { related_pin : "CK"; '
              'timing_type : hold_rising;',
              '        rise_constraint (con) { values ( \\',
              '            ' + _표(lambda s, c: 홀드) + '); }',
              '        fall_constraint (con) { values ( \\',
              '            ' + _표(lambda s, c: 홀드) + '); } } }']
        o += ['    pin (Q) { direction : output; function : "IQ";',
              f'      max_capacitance : {max(부하축):.4f};',
              '      timing () { related_pin : "CK"; '
              'timing_type : rising_edge;',
              '        cell_rise (dly) { values ( \\',
              '            ' + _표(lambda s, c: _지연(d, p, c, 0.0)) + '); }',
              '        cell_fall (dly) { values ( \\',
              '            ' + _표(lambda s, c: _지연(d, p, c, 0.0)) + '); }',
              '        rise_transition (dly) { values ( \\',
              '            ' + _표(lambda s, c: _천이(d, p, c)) + '); }',
              '        fall_transition (dly) { values ( \\',
              '            ' + _표(lambda s, c: _천이(d, p, c)) + '); } } }']
        o.append('  }')
        return "\n".join(o)

    for 핀, g in 셀["g"].items():
        o.append(f'    pin ({핀}) {{ direction : input; '
                 f'capacitance : {d*g*C단위*1e12:.5f}; }}')
    o += ['    pin (Y) { direction : output; function : "' + 셀["함수"] + '";',
          f'      max_capacitance : {max(부하축)*d:.4f};']
    for 핀 in 셀["g"]:
        o += [f'      timing () {{ related_pin : "{핀}"; '
              f'timing_sense : {셀["감"][핀]};',
              '        cell_rise (dly) { values ( \\',
              '            ' + _표(lambda s, c: _지연(d, p, c, s)) + '); }',
              '        cell_fall (dly) { values ( \\',
              '            ' + _표(lambda s, c: _지연(d, p, c, s)) + '); }',
              '        rise_transition (dly) { values ( \\',
              '            ' + _표(lambda s, c: _천이(d, p, c)) + '); }',
              '        fall_transition (dly) { values ( \\',
              '            ' + _표(lambda s, c: _천이(d, p, c)) + '); } }']
    o += ['    }', '  }']
    return "\n".join(o)


def 글():
    축1 = ", ".join(f"{v}" for v in 입력천이축)
    축2 = ", ".join(f"{v}" for v in 부하축)
    머리 = f"""/* se10 -- 이 저장소의 실습용 표준셀 라이브러리.
 *
 * **손으로 적은 파일이 아니다.**  `lab/se/mklib.py` 가 RC 모형 하나에서
 * 전부 계산해 낸다.  고치려면 그 파일의 모형을 고치고 다시 내라:
 *
 *     python3 lab/se/mklib.py
 *
 * 모형:  지연 = 0.69·R·(C자체 + C부하) + 0.5·입력천이,  R = R단위/d,
 *        C자체 = d·p·C단위,  Cin = d·g·C단위
 * 상수:  R단위 = {R단위:.0f} Ω,  C단위 = {C단위*1e15:.0f} fF
 * 그래서: FO4 = {FO4()*1e12:.1f} ps  ->  180 nm 언저리 -> VDD 1.8 V
 * 자리:   {자리폭} × {행높이} µm (강의 화면의 LEF SITE 그대로)
 *
 * 진짜 공정이 아니다.  흐름이 도는 것을 보이는 데 필요한 만큼만 있다.
 */
library (se10) {{
  technology (cmos);
  delay_model            : table_lookup;
  time_unit              : "1ns";
  voltage_unit           : "1V";
  current_unit           : "1mA";
  capacitive_load_unit   (1, pf);
  pulling_resistance_unit: "1kohm";
  leakage_power_unit     : "1nW";

  nom_voltage     : 1.8;
  nom_temperature : 25.0;
  nom_process     : 1.0;

  default_input_pin_cap  : 0.002;
  default_output_pin_cap : 0.0;
  default_inout_pin_cap  : 0.0;
  default_fanout_load    : 1.0;
  default_max_transition : {max(입력천이축)};

  lu_table_template (dly) {{
    variable_1 : input_net_transition;
    variable_2 : total_output_net_capacitance;
    index_1 ("{축1}");
    index_2 ("{축2}");
  }}
  lu_table_template (con) {{
    variable_1 : related_pin_transition;
    variable_2 : constrained_pin_transition;
    index_1 ("{축1}");
    index_2 ("{축1}");
  }}
"""
    return 머리 + "\n".join(_셀글(c) for c in 셀들) + "\n}\n"


if __name__ == "__main__":
    뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    길 = os.path.join(뿌리, "lib", "se10.lib")
    with open(길, "w", encoding="utf-8") as f:
        f.write(글())
    print(f"{길} -- 셀 {len(셀들)}개, FO4 {FO4()*1e12:.1f} ps")
