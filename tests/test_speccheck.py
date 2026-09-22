# -*- coding: utf-8 -*-
"""**제안서를 내기 전에 스펙의 결함을 기계가 찾는가.**

사용자(2026-09-22): "이 결함을 내가 일일이 너한테 보고하는게 아니라, 결함을 스스로
고치거나 혹은 결함이 없어야해. 매번 이렇게 교정이 불가능해."

맞는 말이다. 사람이 실제 HAS 에서 찾아 준 네 결함은 **전부 기계가 찾을 수 있는 것**
이었다. 이 검사는 **그 네 개를 그대로 표본으로 들고** 잡히는지 본다.

모델도 망도 없이 돈다. 실행: python3 tests/test_speccheck.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from house import arch as A          # noqa: E402
from house import spec as S          # noqa: E402
from house import speccheck as C     # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'통과' if cond else '실패'}  {label}")
    if not cond:
        fails.append(label)


def 규칙들(난것):
    return {m["규칙"] for m in 난것}


# 2026-09-22 에 사람이 PDF 에서 찾아 준 그 스펙을 그대로 재현한다.
def 실제HAS():
    return S.스펙(
        요청="MERA-1", 문제=["속도", "면적", "정밀도"], 회로=["ADC", "AXI"],
        블록=[{"이름": "rfdc_adapter", "하는일": "x"},
            {"이름": "capture_buffer_async_fifo", "하는일": "x"},
            {"이름": "ddr_axi_master", "하는일": "x"}],
        포트=[{"이름": "clk", "방향": "input", "폭": 1, "뜻": "메인"},
            {"이름": "rfdc_tdata", "방향": "input", "폭": 0, "뜻": "폭 TBD"},
            {"이름": "s_axi_aclk", "방향": "input", "폭": 1, "뜻": "Lite 클럭"}],
        클럭=[{"이름": "clk", "주기_ns": 2.0, "도메인": "system"}],
        목표=[{"항목": "클럭 주파수", "값": "500 MHz", "어떻게 잴 것인가": "STA"}],
        검증계획=[{"시나리오": f"s{i}", "노리는 것": "t"} for i in range(5)],
        위험=["a", "b"])


print("[네 결함] 사람이 찾아 준 것을 기계가 찾는가")
난 = C.검사(실제HAS())
ok("S001" in 규칙들(난),
   "**포트 폭 0 을 잡는다** — TBD 는 0 이 아니다. 폭 0 포트는 SV 에서 불법이고 "
   "이 표가 RTL 생성기의 입력이다")
ok("S006" in 규칙들(난),
   "**숨은 CDC 를 잡는다** — 포트에 clk 가 둘인데 클럭 표에 하나뿐이다")
ok("S008" in 규칙들(난),
   "**이름과 구조의 어긋남을 잡는다** — async 인데 클럭 도메인이 하나다")
ok("S011" in 규칙들(난),
   "**문제로 읽은 것이 목표에 없는 것을 잡는다** — 목표에 없으면 아무도 안 잰다")

print()
print("[가름] 고칠 것 · 되물을 것 · 사람이 정할 것")
갈래 = {m["규칙"]: m["갈래"] for m in 난}
ok(갈래["S001"] == "고침", "폭 0 은 기계가 고친다")
ok(갈래["S008"] == "고침", "이름도 기계가 고친다")
ok(갈래["S011"] == "되물음", "빠진 목표는 모델에게 되묻는다 — 값은 기계가 못 정한다")
ok(갈래["S006"] == "남김",
   "**클럭 도메인이 몇 개인지는 사람이 정한다** — 기계가 고치면 설계 판단을 대신하는 것이다")

print()
print("[고치기] 고치고 나서 조용히 지나가지 않는가")
s = 실제HAS()
s, 고친 = C.고치기(s, C.검사(s))
폭 = [p["폭"] for p in s.포트 if p["이름"] == "rfdc_tdata"][0]
ok(폭 >= 1, f"폭이 합법한 값이 됐다 ({폭})")
ok(any("파라미터" in p.get("뜻", "") for p in s.포트),
   "**고친 자리에 '파라미터로 둘 것' 을 남긴다** — 1 이 진짜 폭인 줄 알면 안 된다")
이름 = [b["이름"] for b in s.블록 if "elastic" in b["이름"]]
ok(이름 == ["capture_elastic_buffer"], f"이름이 겹치지 않게 고친다 ({이름})")
ok(len(고친) == 2 and all("(S0" in x for x in 고친),
   f"**무엇을 왜 고쳤는지 규칙 번호와 함께 남긴다** ({고친})")
ok(not 규칙들(C.검사(s)) & {"S001", "S008"}, "고친 뒤에는 그 둘이 다시 안 걸린다")

print()
print("[안 건드림] 멀쩡한 스펙을 흔들지 않는가")
성한 = S.스펙(
    요청="x", 문제=["속도"], 블록=[{"이름": "a", "하는일": "x"}, {"이름": "b", "하는일": "y"}],
    포트=[{"이름": "clk", "방향": "input", "폭": 1, "뜻": "c"},
        {"이름": "d_in", "방향": "input", "폭": 32, "뜻": "d"}],
    클럭=[{"이름": "clk", "주기_ns": 2.0, "도메인": "m"}],
    목표=[{"항목": "주파수", "값": "500 MHz", "어떻게 잴 것인가": "STA"}],
    검증계획=[{"시나리오": f"s{i}", "노리는 것": "t"} for i in range(5)],
    위험=["r"])
ok(C.검사(성한) == [], "**결함이 없는 스펙에는 한 건도 안 낸다** — 관문이 벽이 되면 안 된다")

print()
print("[더] 나머지 규칙도 실제로 무는가")
ok("S010" in 규칙들(C.검사(S.스펙(블록=[{"이름": "one", "하는일": "x"}]))),
   "블록이 하나뿐이면 잡는다 — 나누지 않은 것은 설계가 아니다")
ok("S013" in 규칙들(C.검사(S.스펙(검증계획=[{"시나리오": "a", "노리는 것": "b"}]))),
   f"검증 시나리오가 {C.검증최소}개 미만이면 잡는다")
ok("S015" in 규칙들(C.검사(S.스펙())), "위험이 비면 잡는다")
ok("S012" in 규칙들(C.검사(S.스펙(목표=[{"항목": "a", "값": "b", "어떻게 잴 것인가": ""}]))),
   "잴 방법이 빈 목표를 잡는다 — 잴 방법 없는 목표는 광고다")
ok("S004" in 규칙들(C.검사(S.스펙(포트=[{"이름": "x", "방향": "몰라", "폭": 1, "뜻": "y"}]))),
   "방향이 이상하면 잡는다")

print()
print("[되묻기] 관문이 찾은 것이 모델 프롬프트에 실리는가")
글 = C.되물을글(난)
ok("S011" in 글 and "다시 내라" in 글,
   "되물을 글에 규칙 번호와 무엇을 하라는 말이 다 들어간다")
ok("S006" not in 글, "**사람이 정할 것은 모델에게 안 넘긴다** — 넘기면 모델이 지어낸다")

본 = {"n": 0}


def 가짜모델(프롬프트):
    본["글"] = 프롬프트
    바퀴 = 본["n"]
    본["n"] += 1
    목표 = [{"항목": "클럭 주파수", "값": "500 MHz", "어떻게 잴 것인가": "STA"}]
    if 바퀴 > 0:            # 되물으면 빠진 목표를 채운다
        목표 += [{"항목": "면적", "값": "셀 수", "어떻게 잴 것인가": "yosys 셀 수"},
                {"항목": "정밀도", "값": "16 bit", "어떻게 잴 것인가": "비트 대조"}]
    return json.dumps({
        "판독": {"쓰임새": ["계측/시험장비"], "문제": ["속도", "면적", "정밀도"],
               "회로": ["AXI"], "수": {}},
        "이름": "mera1", "한줄": "x",
        "블록": [{"이름": "capture_buffer_async_fifo", "하는일": "y"},
               {"이름": "ddr_axi_master", "하는일": "z"}],
        "포트": [{"이름": "clk", "방향": "input", "폭": 1, "뜻": "c"},
               {"이름": "rfdc_tdata", "방향": "input", "폭": 0, "뜻": "TBD"}],
        "클럭": [{"이름": "clk", "주기_ns": 2.0, "도메인": "d"}],
        "목표": 목표,
        "검증계획": [{"시나리오": f"s{i}", "노리는 것": "t"} for i in range(5)],
        "위험": ["a"]})


m = A.일하기("계측장비용 이벤트 레코더 500MHz 0.8V", 묻기=가짜모델)
검 = m["검사"]
ok(본["n"] == 2, f"**되물음이 실제로 한 번 더 부른다** ({본['n']}회)")
ok("S011" in 본["글"], "그 호출의 프롬프트에 관문이 찾은 결함이 실려 있다")
ok(m["검사_되물었나"], "되물었다고 기록한다")
ok(not any(x["규칙"] == "S011" for x in 검["난것"]),
   "**되물은 뒤에는 그 결함이 사라졌다** — 관문이 실제로 먹었다")
ok(검["고친것"], "고친 것이 기록에 남는다")
ok("모델이 같은 결함을" in 검["요약"],
   "**모델이 고쳐 준 결함을 다시 내면 그렇게 적는다** — 합쳐서 숨기지 않는다")

print()
print("[AMD 규약] 산업 스펙을 그대로 차용했는가 — AXI4 필드 폭")
# 사용자(2026-09-22): "산업에서 쓰이는 AMD 나 xillinx 스펙을 그대로 차용해.
# 실제로 제공하는 카탈로그 처럼."
#
# **이 검사의 요점은 '맞는 것을 안 흔든다' 가 먼저다.** 규약 검사는 거짓 양성을
# 내는 순간 못 쓰게 된다 -- 제안서마다 없는 결함이 뜨면 사람이 표를 안 읽는다.
def AXI스펙(포트, 이름="mera1"):
    return S.스펙(요청="x", 문제=["속도"], 회로=["AXI"],
                 블록=[{"이름": "ddr_axi_master", "하는일": "x"}],
                 포트=포트,
                 클럭=[{"이름": "m_axi_aclk", "주기_ns": 4.0, "도메인": "axi"}],
                 목표=[{"항목": "클럭 주파수", "값": "250 MHz", "어떻게 잴 것인가": "STA"}],
                 검증계획=[{"시나리오": f"s{i}", "노리는 것": "t"} for i in range(5)],
                 위험=["a", "b"], 이름=이름)


def 포트(이름, 폭, 방향="input"):
    return {"이름": 이름, "방향": 방향, "폭": 폭, "뜻": "x"}


맞는AXI = [포트("m_axi_aclk", 1), 포트("m_axi_aresetn", 1),
          포트("m_axi_awlen", 8, "output"), 포트("m_axi_awsize", 3, "output"),
          포트("m_axi_awburst", 2, "output"), 포트("m_axi_awvalid", 1, "output"),
          포트("m_axi_awready", 1), 포트("m_axi_wdata", 128, "output"),
          포트("m_axi_wstrb", 16, "output"), 포트("m_axi_wvalid", 1, "output"),
          포트("m_axi_wready", 1), 포트("m_axi_bresp", 2),
          포트("s_axis_tdata", 256), 포트("s_axis_tkeep", 32),
          포트("s_axis_tvalid", 1), 포트("s_axis_tready", 1, "output")]
난A = 규칙들(C.검사(AXI스펙(맞는AXI)))
ok(not 난A & {"S016", "S017", "S018", "S019", "S020", "S021", "S022"},
   f"**AMD 규약대로 적힌 포트표는 한 건도 안 걸린다** ({sorted(난A)})")

틀린AXI = [포트("m_axi_aclk", 1), 포트("m_axi_aresetn", 1),
          포트("m_axi_awlen", 4, "output"),          # AXI3 의 4 비트다
          포트("m_axi_wdata", 128, "output"),
          포트("m_axi_wstrb", 4, "output"),          # 128/8 = 16 이어야 한다
          포트("m_axi_bresp", 2),
          포트("s_axis_tdata", 256), 포트("s_axis_tkeep", 8),
          포트("s_axis_tvalid", 1), 포트("s_axis_tready", 1, "output")]
난B = C.검사(AXI스펙(틀린AXI))
말B = " ".join(m["말"] for m in 난B)
ok("S016" in 규칙들(난B), "**AWLEN 이 4 비트면 잡는다** — AXI3 의 폭이다, AXI4 는 8 이다")
ok("S017" in 규칙들(난B) and "16" in 말B,
   "**WSTRB 가 데이터폭/8 이 아니면 잡고 옳은 값을 말한다** (wdata 128 -> wstrb 16)")
ok("32" in 말B, "**TKEEP 도 같은 산수로 잡는다** (tdata 256 -> tkeep 32)")
sB, 고친B = C.고치기(AXI스펙(틀린AXI), 난B)
폭들 = {p["이름"]: p["폭"] for p in sB.포트}
ok((폭들["m_axi_awlen"], 폭들["m_axi_wstrb"], 폭들["s_axis_tkeep"]) == (8, 16, 32),
   f"**기계가 규약 폭으로 고친다** ({폭들['m_axi_awlen']}, {폭들['m_axi_wstrb']}, "
   f"{폭들['s_axis_tkeep']})")
ok(not 규칙들(C.검사(sB)) & {"S016", "S017"}, "고친 뒤에는 다시 안 걸린다")

print()
print("[AMD 규약] 악수 짝과 리셋 이름")
짝없음 = [포트("m_axi_aclk", 1), 포트("m_axi_aresetn", 1),
        포트("s_axis_tdata", 256), 포트("s_axis_tkeep", 32),
        포트("s_axis_tvalid", 1)]              # tready 가 없다
ok("S020" in 규칙들(C.검사(AXI스펙(짝없음))),
   "**valid 만 있고 ready 가 없으면 잡는다** — 역압이 없는 AXI-Stream 은 규약이 아니다")

나쁜리셋 = [포트("m_axi_aclk", 1), 포트("rst_n", 1),
          포트("s_axis_tdata", 256), 포트("s_axis_tkeep", 32),
          포트("s_axis_tvalid", 1), 포트("s_axis_tready", 1, "output")]
난C = C.검사(AXI스펙(나쁜리셋))
ok(규칙들(난C) & {"S021", "S022"},
   "**rst_n 을 잡는다** — AMD 가 인터페이스를 자동으로 묶는 근거가 이름 규약이다")
sC, _ = C.고치기(AXI스펙(나쁜리셋), 난C)
이름들 = [p["이름"] for p in sC.포트]
ok("aresetn" in " ".join(이름들) and "rst_n" not in 이름들,
   f"**기계가 AMD 이름으로 바꾼다** ({이름들})")

print()
print("[IP Facts] 제안서가 카탈로그 첫 표를 낸다")
# AMD 제품 가이드(PG###)는 IP Facts 표로 시작한다. 그 꼴을 빌리되 **안 만든 것을
# 만들었다고 쓰지 않는다** — 그것이 이 저장소가 다섯 번 앓은 병이다.
import re                                                        # noqa: E402
글A = A.보고서({"_s": AXI스펙(맞는AXI)}).html()
칸 = lambda h, t: len(re.findall(r"<td[^>]*>" + re.escape(t), h))  # noqa: E731
ok("IP Facts" in 글A, "제안서에 IP Facts 절이 있다")
ok("AXI4-Stream" in 글A and "AXI4 (Memory Mapped)" in 글A,
   "**포트 이름에서 인터페이스를 알아내 적는다** — Vivado 가 묶는 근거와 같은 규약이다")
# **표 칸만 센다.** 설명글에도 '아직 없음' 이 들어 있어 글 전체를 훑으면 늘 걸린다.
ok(칸(글A, "아직 없음") >= 5,
   f"**안 만든 칸은 '아직 없음' 이다** — 꼴만 빌리고 다 된 척하지 않는다 "
   f"({칸(글A, '아직 없음')}칸)")
ok("FPGA LUT" in 글A,
   "**Synthesis 칸이 ASIC 표준셀임을 못박는다** — 사용자 지시가 'FPGA가 아니고 ASIC' 이다")

# AMD PG 의 Port Descriptions 표는 인터페이스로 묶여 있다. 규약을 벗어난 포트가
# **눈에 띄게** 남는 것이 이 묶음의 값어치다 -- 그것이 손으로 이어야 하는 것들이다.
# 실측 2026-09-22: 처음에 `"(개별 신호)" not in 글A` 로 썼더니 **맞는 포트표에서도
# 걸렸다** -- 표 설명글에 그 말이 들어 있어서다. 아무것도 안 재는 거짓 초록이었다.
개별 = lambda h: len(re.findall(r"<td[^>]*>\(개별 신호\)</td>", h))  # noqa: E731
글B = A.보고서({"_s": AXI스펙(나쁜리셋)}).html()
ok(개별(글B) == 1,
   f"**규약을 벗어난 포트는 '(개별 신호)' 칸으로 남아 눈에 띈다** (rst_n, {개별(글B)}칸)")
ok(개별(글A) == 0,
   f"**규약을 지킨 포트표에는 개별 신호가 없다** — 전부 묶인다 ({개별(글A)}칸)")

print()
print("[S023·S024] 모델이 요청의 수를 바꾸면 잡는가")
# **실측 2026-09-22 — 이 관문이 없어서 틀린 제안서가 나갔다.**
# 사용자가 2,851자 스펙을 첨부로 줬는데 `dispatch.py` 의 `[:900]` 이 900자에서 잘랐고,
# 모델은 §5(`AXI4-MM ... data 128-bit` · `제어는 AXI4-Lite`)를 **아예 못 봤다.**
# 그래서 DDR 폭을 256 으로 채우고 AXI4-Lite 포트를 통째로 빠뜨렸다.
#
#     S016~S022 는 한 건도 안 걸렸다 -- 32 == 256/8 이라 S017 이 만족한다.
#     관문이 *스펙 안의 일관성*만 보고 **요청을 안 봤다.**
_요청 = """MERA-1 Event Recorder Core 를 설계해 주세요.
| RFDC 입력 | AXI4-Stream, canonical 256-bit |
| DDR 출력 | **AXI4-MM master**, address **64-bit**, data **128-bit**, **64-beat** burst |
| 제어 | **AXI4-Lite** |
목표 500 MHz, 0.8 V."""

ok(C._요청폭(_요청).get(("m_axi", "wdata")) == 128,
   f"**요청에서 MM 데이터 폭을 읽는다** ({C._요청폭(_요청).get(('m_axi','wdata'))})")
ok(C._요청폭(_요청).get(("m_axi", "awaddr")) == 64,
   "**주소 폭도 따로 읽는다** -- 한 줄에 둘이 있어도 안 섞인다")
ok(C._요청폭(_요청).get(("s_axis", "tdata")) == 256,
   "스트림 폭은 스트림 줄에서 읽는다")
ok(("m_axi", "tdata") not in C._요청폭(_요청),
   "**`tdata` 를 MM 것으로 읽지 않는다** -- 꼬리는 인터페이스마다 다르다")

def 제안서(wdata=256, wstrb=32, lite=False):
    포트 = [{"이름": n, "방향": d, "폭": w, "뜻": "x"} for n, d, w in [
        ("m_axi_awaddr", "output", 64), ("m_axi_wdata", "output", wdata),
        ("m_axi_wstrb", "output", wstrb), ("m_axi_wvalid", "output", 1),
        ("m_axi_wready", "input", 1), ("m_axi_bresp", "input", 2),
        ("s_axis_tdata", "input", 256), ("s_axis_tkeep", "input", 32),
        ("s_axis_tvalid", "input", 1), ("s_axis_tready", "output", 1)]]
    if lite:
        포트 += [{"이름": "s_axi_awaddr", "방향": "input", "폭": 32, "뜻": "x"},
               {"이름": "s_axi_wdata", "방향": "input", "폭": 32, "뜻": "x"}]
    return S.스펙(요청=_요청, 문제=["속도", "면적"], 회로=["AXI"],
                 블록=[{"이름": "a", "하는일": "x"}, {"이름": "b", "하는일": "x"}],
                 포트=포트, 클럭=[{"이름": "clk", "주기_ns": 2.0, "도메인": "d"}],
                 목표=[{"항목": "클럭 주파수", "값": "500 MHz", "어떻게 잴 것인가": "STA"}],
                 검증계획=[{"시나리오": f"s{i}", "노리는 것": "t"} for i in range(6)],
                 위험=["a"])

_난 = C.검사(제안서())
ok("S023" in 규칙들(_난),
   "**요청은 128 인데 제안이 256 이면 잡는다** -- 그 제안서가 실제로 그랬다")
ok("S024" in 규칙들(_난),
   "**요청이 요구한 AXI4-Lite 가 통째로 없는 것도 잡는다**")
_s023 = [m for m in _난 if m["규칙"] == "S023"][0]
ok("128" in _s023["말"] and "256" in _s023["말"], f"무엇을 무엇으로 바꿨는지 적는다")

# **S016~S022 는 이것을 못 잡는다.** 그 자리가 비어 있었다는 것을 못박는다.
ok(not (규칙들(_난) & {"S016", "S017", "S018", "S019", "S020", "S021", "S022"}),
   "**규약 검사들은 한 건도 안 문다** -- 32 == 256/8 이라 스펙 안에서는 일관된다. "
   "그래서 S023 이 따로 필요하다")

_s2, _고친 = C.고치기(제안서(), _난)
ok([p for p in _s2.포트 if p["이름"] == "m_axi_wdata"][0]["폭"] == 128,
   "**기계가 요청의 수로 되돌린다** (256 → 128)")
ok(any("S023" in x for x in _고친), f"무엇을 왜 고쳤는지 남긴다 ({_고친})")
ok("S017" in 규칙들(C.검사(_s2)),
   "**고친 뒤 wstrb 가 어긋난 것을 S017 이 이어받는다** (128/8 = 16 인데 32다) — "
   "관문이 층으로 물린다")

# **맞는 제안서는 안 흔든다.** 거짓 양성을 내는 관문은 못 쓰게 된다.
_맞 = C.검사(제안서(wdata=128, wstrb=16, lite=True))
ok(not (규칙들(_맞) & {"S023", "S024"}),
   f"**요청대로 적힌 제안서는 한 건도 안 걸린다** ({sorted(규칙들(_맞))})")

# 요청이 없으면(옛 경로) 아무것도 안 한다 -- 없는 것을 근거로 물지 않는다
_빈 = 제안서(); _빈.요청 = ""
ok(not (규칙들(C.검사(_빈)) & {"S023", "S024"}),
   "**요청 글이 없으면 대조하지 않는다** -- 모르는 것을 틀렸다고 하지 않는다")

print()
print("[인터페이스 이름] AXI4-Lite 가 두 묶음으로 쪼개지지 않는가")
# **실측 2026-09-22 — 제안서 포트표에 이렇게 나왔다.**
#
#     AXI4 (Memory Mapped)   s_axi_awaddr   input   32   제어용 AXI4-Lite 쓰기 주소
#
# `s_axi_awaddr` 는 AXI4-Lite 인데 Memory Mapped 로 찍혔다. 까닭은 내가 쓴 줄이
#
#     if n.startswith("m_axi") or 꼬.startswith(("aw", "ar")) and "axi" in n:
#
# 였고, 파이썬이 이것을 `A or (B and C)` 로 읽기 때문이다 -- `s_axi_awaddr` 는
# A 가 거짓이어도 B·C 가 참이라 MM 으로 갔다. **AXI4-Lite 가 두 묶음으로 쪼개져**
# `s_axi_wdata` 는 Lite, `s_axi_awaddr` 는 MM 으로 나왔다. 블록 디자인을 그리는
# 사람이 그대로 믿으면 틀리게 잇는다.
_묶 = A._인터페이스
ok(_묶({"이름": "s_axi_awaddr"}) == "AXI4-Lite",
   f"**`s_axi_awaddr` 는 Lite 다** ({_묶({'이름': 's_axi_awaddr'})})")
ok(_묶({"이름": "s_axi_araddr"}) == "AXI4-Lite", "`s_axi_araddr` 도 Lite")
ok(_묶({"이름": "s_axi_wdata"}) == "AXI4-Lite", "`s_axi_wdata` 도 Lite -- 같은 묶음이다")
ok(_묶({"이름": "m_axi_awaddr"}) == "AXI4 (Memory Mapped)", "`m_axi_*` 는 MM 그대로")
ok(_묶({"이름": "s_axis_tdata"}) == "AXI4-Stream",
   "**`s_axis_` 가 `s_axi_` 를 삼키므로 스트림을 먼저 본다**")
ok(_묶({"이름": "s_axis_tready"}) == "AXI4-Stream", "스트림의 ready 도 스트림")
ok(_묶({"이름": "tdata"}) == "AXI4-Stream", "접두사가 없으면 꼬리로 본다")
ok(_묶({"이름": "rst_n"}) == "", "규약 밖은 빈 값 -- 표에서 '(개별 신호)' 가 된다")

# **한 인터페이스가 한 묶음으로 모인다.** 쪼개지면 표가 거짓말을 한다.
_라이트 = ["s_axi_awaddr", "s_axi_awvalid", "s_axi_awready", "s_axi_wdata",
         "s_axi_wstrb", "s_axi_bresp", "s_axi_araddr", "s_axi_rdata"]
ok(len({_묶({"이름": n}) for n in _라이트}) == 1,
   f"**AXI4-Lite 포트 8개가 전부 한 묶음이다** ({ {_묶({'이름': n}) for n in _라이트} })")

print()
if fails:
    print(f"실패 {len(fails)}개: {fails}")
    raise SystemExit(1)
print("speccheck: 네 결함 · 가름 · 고치기 · 안 건드림 · 되묻기 -- 통과")
