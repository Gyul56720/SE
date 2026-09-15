"""집적회로 개념 목록. **학부 · 석사 · 박사 전 범위를 한 자리에 둔다.**

사용자(2026-09-15): "current mirror 말고도 학부 석사 박사 아날로그 집적회로,
디지털 집적 회로에 쓰이는 개념들을 모두 cover 할 수 있어야 해."

## 왜 프롬프트에 늘어놓지 않나

개념 이름 백 개를 프롬프트에 적는 것은 **coverage 가 아니다.** 그것은 이 저장소가
내내 말해 온 "검사하지 않은 초록"이다 -- 적혀 있으니 된 줄 알지만 아무도 확인 안 했다.

그래서 목록을 **데이터**로 둔다. 항목마다 돌아가는 본보기(`넷리스트` · `회로도`)를
가리키고, `tests/test_concepts.py` 가 **그 본보기를 전부 실제로 돌린다.**
가리키는 데가 없거나 안 돌면 빨간불이다. 그러면 목록이 자라도 거짓말을 못 한다.

## 항목 하나가 무엇인가

    이름     영어 이름. 이 바닥의 말은 영어다.
    한글     찾기용. 사용자는 한국어로 묻는다.
    층       학부 · 석사 · 박사 -- 어느 깊이로 답할지 가른다.
    갈래     analog · digital · device · mixed
    식       핵심 식 하나. LaTeX. `$...$` 없이 알맹이만 -- 부르는 쪽이 감싼다.
    말       한 문장. **무엇을 정하는 양인지**를 적는다(정의가 아니라 쓸모).
    넷리스트 spice.본보기 의 이름. 있으면 돌려 볼 수 있다.
    회로도   circuitdraw.본보기 의 이름. 있으면 그려 볼 수 있다.
    이웃     같이 봐야 하는 개념들.

`넷리스트`·`회로도` 가 비면 **설명만 되는 개념**이다. 그것을 숨기지 않는다 --
`덮임()` 이 몇 개가 돌아가고 몇 개가 설명뿐인지 세어서 말한다.
"""
from __future__ import annotations

import re

학부, 석사, 박사 = "학부", "석사", "박사"

# 트랙 -- 사용자(2026-09-15)가 준 IP 디자인하우스 입사 로드맵의 갈래다.
# **백엔드는 디지털도 아날로그도 아닌 제3의 영역이다.** 트랜지스터를 직접 설계·시뮬레이션
# 하지 않고, 파운드리·셀 라이브러리 팀이 SPICE 로 캐릭터라이즈해 `.lib` 로 넘긴 스탠다드
# 셀을 **블랙박스로 받아** 배치·배선·타이밍을 다룬다. 배선의 RC 기생만 직접 추출한다.
공통, 프론트, 백엔드, 아날로그, IP특화, 포트폴리오, 생태계 = (
    "공통기초", "프론트엔드", "백엔드", "아날로그", "IP특화", "포트폴리오", "생태계")
# 사용자(2026-09-15)가 고른 연구 주제의 트랙. SK하이닉스 SerDes/PHY 와 커널 최적화·
# 양자화가 만나는 자리이고, 교안(2026 VLSI ch0 의 Eye Diagram · ch4 의 PLL/CDR)이
# 바로 여기로 이어진다. `serdes.py` 가 이 트랙의 본보기를 **실제로 돌린다.**
고속링크 = "고속링크"
트랙들 = (공통, 프론트, 백엔드, 아날로그, IP특화, 포트폴리오, 생태계, 고속링크)
A, D, DEV, M = "analog", "digital", "device", "mixed"


def _(이름, 한글, 층, 갈래, 식, 말, 넷="", 그림="", 이웃=(), 트랙="", 링크=""):
    return {"이름": 이름, "한글": 한글, "층": 층, "갈래": 갈래, "식": 식, "말": 말,
            "넷리스트": 넷, "회로도": 그림, "링크": 링크, "이웃": list(이웃), "트랙": 트랙}


개념: "list[dict]" = [
    # ---------------------------------------------------------------- 소자
    _("MOSFET square law", "제곱법칙·MOS 전류식", 학부, DEV,
      r"I_D=\tfrac{1}{2}K'\tfrac{W}{L}(V_{GS}-V_{th})^2(1+\lambda V_{DS})",
      "포화에서의 드레인 전류. W/L 과 과구동전압이 전류를 정하고, 그것이 다른 모든 것의 밑동이다.",
      "mosfet_iv", 이웃=["Overdrive voltage", "Channel-length modulation"]),
    _("Triode vs saturation", "삼극관·포화 영역", 학부, DEV,
      r"V_{DS}<V_{OV}\Rightarrow\text{triode},\quad V_{DS}\ge V_{OV}\Rightarrow\text{saturation}",
      "증폭기는 포화에서만 산다. 삼극관으로 넘어가면 이득이 무너진다 -- 바이어스 점검의 첫 줄.",
      "mosfet_iv", 이웃=["Overdrive voltage"]),
    _("Threshold voltage", "문턱전압 Vth", 학부, DEV,
      r"V_{th}=V_{th0}+\gamma\left(\sqrt{2\phi_F+V_{SB}}-\sqrt{2\phi_F}\right)",
      "채널이 생기는 문턱. 소스-벌크 전압이 붙으면 올라간다(몸효과).",
      "nmos_vth", 이웃=["Body effect", "Subthreshold conduction"]),
    _("Body effect", "몸효과·백게이트", 학부, DEV,
      r"g_{mb}=\eta g_m,\quad \eta=\tfrac{\gamma}{2\sqrt{2\phi_F+V_{SB}}}",
      "벌크가 두 번째 게이트로 작동한다. 소스팔로워와 캐스코드에서 이득을 갉아먹는다.",
      "body_effect",
      이웃=["Threshold voltage", "Source follower"]),
    _("Overdrive voltage", "과구동전압 Vov", 학부, DEV,
      r"V_{OV}=V_{GS}-V_{th}=\sqrt{\tfrac{2I_D}{K'(W/L)}}",
      "설계의 손잡이. 작게 잡으면 gm/ID 가 커지고(이득·저전력), 크게 잡으면 빠르고 정합이 좋아진다.",
      "gm_id",
      이웃=["gm/ID methodology", "Transconductance"]),
    _("Transconductance", "전달컨덕턴스 gm", 학부, A,
      r"g_m=\tfrac{\partial I_D}{\partial V_{GS}}=\tfrac{2I_D}{V_{OV}}=\sqrt{2K'\tfrac{W}{L}I_D}",
      "입력 전압을 출력 전류로 바꾸는 비율. 이득도 잡음도 대역도 전부 여기서 나온다.",
      "common_source", 이웃=["Output resistance", "gm/ID methodology"]),
    _("Channel-length modulation", "채널길이변조 λ", 학부, DEV,
      r"r_o=\tfrac{1}{\lambda I_D}=\tfrac{V_A}{I_D}",
      "포화에서 Vds 가 늘면 유효 채널이 짧아져 Id 가 조금씩 는다. 그 기울기가 출력저항이다.",
      "mosfet_iv", 이웃=["Output resistance", "Cascode"]),
    _("Output resistance", "출력저항 ro", 학부, A,
      r"A_v^{max}=g_m r_o=\tfrac{2}{\lambda V_{OV}}",
      "한 단이 낼 수 있는 이득의 상한(내재이득). 전류를 늘려도 안 늘어난다 -- L 을 늘려야 는다.",
      "common_source", 이웃=["Channel-length modulation", "Cascode"]),
    _("Short-channel effects", "단채널 효과", 박사, DEV,
      r"I_D\propto W(V_{GS}-V_{th})\ (v_{sat}),\quad \Delta V_{th}=-\eta_{DIBL}V_{DS}\ (\text{DIBL})",
      "짧은 채널에서는 제곱법칙이 깨져 전류가 Vov 에 선형이 된다. gm 이 전류에 덜 붙는다.",
      이웃=["MOSFET square law", "Subthreshold conduction"]),
    _("Subthreshold conduction", "문턱아래 전도", 석사, DEV,
      r"I_D=I_0\tfrac{W}{L}e^{\tfrac{V_{GS}-V_{th}}{nV_T}},\quad S=n V_T\ln 10\ \ge 60\,\mathrm{mV/dec}",
      "문턱 아래에서 전류는 지수다. 초저전력 아날로그와 누설전력이 둘 다 여기서 산다.",
      이웃=["Leakage power", "gm/ID methodology"]),
    _("Intrinsic capacitances", "기생 용량 Cgs·Cgd·Cdb", 학부, DEV,
      r"C_{gs}\approx\tfrac{2}{3}WLC_{ox}+WC_{ov},\quad f_T=\tfrac{g_m}{2\pi(C_{gs}+C_{gd})}",
      "속도의 한계. ft 는 소자가 낼 수 있는 최대 속도이고 Vov 에 비례한다.",
      이웃=["Miller effect", "gm/ID methodology"]),

    # ------------------------------------------------------- 단일단 증폭기
    _("Common source", "공통소스 증폭기", 학부, A,
      r"A_v=-g_m(R_D\parallel r_o)",
      "기본 전압 증폭단. 반전이고 이득이 크지만 Miller 때문에 대역이 좁다.",
      "common_source", "common_source_amp", ["Miller effect", "Cascode"]),
    _("Common gate", "공통게이트", 학부, A,
      r"R_{in}=\tfrac{1}{g_m+g_{mb}},\quad A_v=+g_m R_D",
      "입력 임피던스가 낮다. 전류를 받아 전압으로 바꾸는 자리(캐스코드의 윗단)에 쓴다.",
      "common_gate", "common_gate",
      이웃=["Cascode", "Source follower"]),
    _("Source follower", "소스팔로워·공통드레인", 학부, A,
      r"A_v=\tfrac{g_m}{g_m+g_{mb}+1/r_o}<1,\quad R_{out}\approx\tfrac{1}{g_m}",
      "이득 1 미만의 버퍼. 출력저항이 낮아 무거운 부하를 몬다. 몸효과가 이득을 깎는다.",
      "source_follower", "source_follower",
      이웃=["Body effect", "Common gate"]),
    _("Cascode", "캐스코드", 학부, A,
      r"R_{out}\approx g_{m2}r_{o2}r_{o1},\quad A_v\approx-g_{m1}(g_{m2}r_{o2}r_{o1})",
      "출력저항을 gm·ro 배로 올린다. 이득이 커지고 Miller 가 줄지만 출력 스윙을 잃는다.",
      "cascode", "cascode",
      이웃=["Output resistance", "Telescopic OTA", "Miller effect"]),
    _("Miller effect", "밀러 효과", 학부, A,
      r"C_{in}=C_{gd}(1+|A_v|),\quad \omega_{p1}\approx\tfrac{1}{R_S C_{gd}(1+|A_v|)}",
      "되먹임 용량이 이득 배로 커져 보인다. 공통소스의 대역을 실제로 정하는 것이 이것이다.",
      "miller",
      이웃=["Cascode", "Pole splitting"]),

    # ------------------------------------------------------------ 전류·바이어스
    _("Current mirror", "전류미러", 학부, A,
      r"\tfrac{I_{OUT}}{I_{REF}}=\tfrac{(W/L)_2}{(W/L)_1}(1+\lambda V_{DS2})",
      "전류를 베낀다. 베끼기의 정확도는 두 Vth 의 정합과 Vds 차이(λ)가 정한다.",
      "current_mirror", "current_mirror", ["Cascode current mirror", "Mismatch (Pelgrom)"]),
    _("Cascode current mirror", "캐스코드 전류미러", 학부, A,
      r"R_{out}\approx g_m r_o^2,\quad V_{out,min}=V_{OV1}+V_{OV2}",
      "출력저항을 ro² 로 올려 λ 오차를 지운다. 대가는 출력 스윙 한 Vov.",
      "cascode_mirror",
      이웃=["Current mirror", "Wide-swing cascode"]),
    _("Wide-swing cascode", "저전압 캐스코드", 석사, A,
      r"V_{out,min}=2V_{OV}\ \text{(vs }V_{th}+2V_{OV})",
      "바이어스를 따로 만들어 캐스코드의 스윙 손실을 Vth 만큼 되찾는다.",
      이웃=["Cascode current mirror"]),
    _("Widlar / Wilson mirror", "위들러·윌슨 미러", 학부, A,
      r"I_{OUT}R_E=V_T\ln\tfrac{I_{REF}}{I_{OUT}}",
      "작은 전류를 저항 하나로 만든다(위들러). 윌슨은 되먹임으로 정확도를 올린다.",
      이웃=["Current mirror"]),
    _("Bandgap reference", "밴드갭 기준전압", 석사, A,
      r"V_{REF}=V_{BE}+K\,V_T\ln N,\quad \tfrac{\partial V_{REF}}{\partial T}=0\ \text{at } V_{REF}\approx1.25\,\mathrm{V}",
      "온도에 내려가는 VBE 와 올라가는 VT 를 더해 상쇄시킨다. 모든 아날로그 칩의 기준점.",
      이웃=["PTAT / CTAT", "LDO regulator"]),
    _("PTAT / CTAT", "PTAT·CTAT", 석사, A,
      r"\Delta V_{BE}=V_T\ln N\ (\text{PTAT}),\quad \tfrac{\partial V_{BE}}{\partial T}\approx-2\,\mathrm{mV/K}\ (\text{CTAT})",
      "밴드갭의 두 재료. 온도계도 여기서 나온다.",
      이웃=["Bandgap reference"]),
    _("LDO regulator", "LDO 레귤레이터", 석사, A,
      r"PSRR(s)=\tfrac{1}{1+T(s)},\quad V_{drop}=V_{OV,pass}",
      "되먹임으로 전원을 깨끗하게 만든다. 안정도가 출력 커패시터의 ESR 에 달린다.",
      이웃=["Feedback and stability", "Bandgap reference"]),

    # ---------------------------------------------------------- 차동·연산증폭기
    _("Differential pair", "차동쌍", 학부, A,
      r"A_d=-g_m R_D,\quad I_{D1,2}=\tfrac{I_{SS}}{2}\pm\tfrac{I_{SS}}{2}\tfrac{V_{id}}{V_{OV}}\sqrt{1-\left(\tfrac{V_{id}}{2V_{OV}}\right)^2}",
      "아날로그의 입력단. 공통모드를 지우고 차동만 키운다. 선형 범위는 √2·Vov.",
      "diff_pair", "diff_pair", 이웃=["CMRR", "Tail current source"]),
    _("CMRR", "공통모드 제거비", 학부, A,
      r"CMRR=\tfrac{A_d}{A_{cm}}\approx 2g_{m1}r_{o,tail}\cdot\text{(matching)}",
      "꼬리 전류원의 출력저항과 부하 정합이 정한다. 정합이 완벽하면 무한대다.",
      "cmrr", "diff_pair",
      이웃=["Differential pair", "Mismatch (Pelgrom)"]),
    _("Tail current source", "꼬리 전류원", 학부, A,
      r"A_{cm}\approx-\tfrac{R_D}{2r_{o,tail}}",
      "차동쌍이 공통모드를 얼마나 무시하는지를 이것 하나가 정한다.",
      "cmrr",
      이웃=["CMRR", "Cascode"]),
    _("Telescopic OTA", "텔레스코픽 OTA", 석사, A,
      r"A_v\approx g_{m1}\left[(g_{m2}r_{o2}r_{o1})\parallel(g_{m3}r_{o3}r_{o4})\right]",
      "가장 빠르고 가장 저전력인 고이득 단. 대가는 좁은 출력 스윙과 입출력 공통모드 충돌.",
      이웃=["Folded cascode OTA", "Cascode"]),
    _("Folded cascode OTA", "폴디드 캐스코드", 석사, A,
      r"A_v\approx g_{m1}(R_{up}\parallel R_{down}),\quad \omega_u=\tfrac{g_{m1}}{C_L}",
      "캐스코드를 접어 입출력 공통모드를 풀어 준다. 전류를 두 배 쓰고 잡음이 는다.",
      이웃=["Telescopic OTA", "CMFB"]),
    _("Two-stage Miller OTA", "2단 밀러 보상 OTA", 석사, A,
      r"A_v=g_{m1}r_{o1}\cdot g_{m2}r_{o2},\quad \omega_u=\tfrac{g_{m1}}{C_C},\quad PM=90^\circ-\arctan\tfrac{\omega_u}{\omega_{p2}}",
      "이득과 스윙을 둘 다 얻는 표준 구조. 보상 커패시터가 극점을 갈라 놓는다.",
      "twostage_ota",
      이웃=["Pole splitting", "Feedback and stability"]),
    _("Pole splitting", "극점 분리", 석사, A,
      r"\omega_{p1}\approx\tfrac{1}{g_{m2}r_{o2}r_{o1}C_C},\quad \omega_{p2}\approx\tfrac{g_{m2}}{C_L}",
      "밀러 보상이 첫 극점을 내리고 둘째를 올린다. 그래서 하나만 남은 것처럼 보인다.",
      "twostage_ota",
      이웃=["Two-stage Miller OTA", "RHP zero"]),
    _("RHP zero", "우반면 영점", 석사, A,
      r"z=+\tfrac{g_{m2}}{C_C}\ \Rightarrow\ \text{nulling }R_z=\tfrac{1}{g_{m2}}",
      "Cc 를 앞으로 지나는 신호가 만드는 영점. 이득은 올리고 위상은 깎아 안정도를 망친다.",
      "twostage_ota",
      이웃=["Pole splitting", "Feedback and stability"]),
    _("CMFB", "공통모드 되먹임", 석사, A,
      r"V_{cm,out}\to V_{cm,ref}\ \text{via } T_{cm}(s),\quad PM_{cm}>60^\circ",
      "완전차동 회로에서 출력 공통모드는 스스로 안 정해진다. 따로 되먹임을 걸어야 한다.",
      이웃=["Folded cascode OTA", "Feedback and stability"]),
    _("Feedback and stability", "되먹임과 안정도", 학부, A,
      r"A_{cl}=\tfrac{A}{1+\beta A},\quad PM=180^\circ+\angle\beta A|_{|\beta A|=1}",
      "루프이득이 모든 것을 정한다 -- 정확도도, 대역도, 울림도. PM 60° 가 관례다.",
      "twostage_ota",
      이웃=["Pole splitting", "Gain-bandwidth product"]),
    _("Gain-bandwidth product", "이득대역폭곱", 학부, A,
      r"GBW=A_0\omega_{p1}=\tfrac{g_m}{C_C}",
      "한 극점 계에서는 이득과 대역의 곱이 상수다. 이득을 낮추면 그만큼 빨라진다.",
      "common_source", 이웃=["Feedback and stability"]),
    _("Slew rate", "슬루율", 석사, A,
      r"SR=\tfrac{I_{SS}}{C_C},\quad t_{settle}\approx\tfrac{\Delta V}{SR}+\tfrac{\ln(1/\epsilon)}{\omega_u}",
      "큰 신호 한계. 작은신호 대역이 아무리 넓어도 여기 걸리면 못 따라간다.",
      "slew_rate",
      이웃=["Two-stage Miller OTA", "Settling time"]),
    _("Settling time", "정착 시간", 석사, A,
      r"t_s=\tfrac{1}{\omega_u}\ln\tfrac{1}{\epsilon}\ (\text{linear}),\quad \epsilon=2^{-(N+1)}\ \text{for }N\text{-bit}",
      "ADC 앞단의 진짜 사양. N비트를 맞추려면 N+1 비트만큼 정착해야 한다.",
      "slew_rate",
      이웃=["Slew rate", "SAR ADC"]),

    # --------------------------------------------------------------- 잡음·정합
    _("Thermal noise", "열잡음", 학부, A,
      r"\overline{v_n^2}=4kTR\,\Delta f,\quad \overline{i_{n,MOS}^2}=4kT\gamma g_m\,\Delta f",
      "모든 저항성 손실이 잡음을 낸다. MOS 는 채널 자체가 저항이라 gm 에 비례한다.",
      "rc_noise", 이웃=["kT/C noise", "Flicker noise"]),
    _("kT/C noise", "kT/C 잡음", 석사, A,
      r"\overline{v_n^2}=\tfrac{kT}{C}\quad(R\ \text{cancels})",
      "샘플링 커패시터가 정하는 잡음 바닥. 저항을 아무리 바꿔도 안 변한다 -- C 를 키우는 수밖에.",
      "rc_noise", 이웃=["Switched-capacitor circuits", "SAR ADC"]),
    _("Flicker noise", "플리커·1/f 잡음", 석사, A,
      r"\overline{v_n^2}=\tfrac{K}{C_{ox}WL}\cdot\tfrac{1}{f},\quad f_{corner}=\tfrac{K g_m}{C_{ox}WL\,4kT\gamma}",
      "저주파를 덮는 잡음. 면적(WL)으로만 줄고, PMOS 가 NMOS 보다 낫다.",
      "flicker_noise",
      이웃=["Chopping", "Correlated double sampling"]),
    _("Noise figure / input-referred noise", "입력환산 잡음", 석사, A,
      r"\overline{v_{n,in}^2}=\tfrac{\overline{v_{n,out}^2}}{A_v^2},\quad NF=10\log\tfrac{SNR_{in}}{SNR_{out}}",
      "잡음은 입력으로 환산해야 단끼리 비교된다. 앞단이 잡음을 지배한다(Friis).",
      "rc_noise", 이웃=["Thermal noise"]),
    _("Mismatch (Pelgrom)", "정합·펠그롬", 석사, DEV,
      r"\sigma_{\Delta V_{th}}=\tfrac{A_{VT}}{\sqrt{WL}},\quad \tfrac{\sigma_{\Delta I}}{I}\approx\tfrac{2\sigma_{\Delta V_{th}}}{V_{OV}}",
      "정합은 면적을 먹는다. 전류미러·차동쌍·ADC 의 정확도가 전부 이 식에 걸린다.",
      "mc_mirror", 이웃=["Monte Carlo", "Layout matching"]),
    _("Monte Carlo", "몬테카를로", 석사, M,
      r"\hat{Y}\pm z\sqrt{\tfrac{\hat{Y}(1-\hat{Y})}{N}},\quad \text{0 fail}\Rightarrow p<\tfrac{3}{N}",
      "수율은 한 판으로 안 나온다. 그리고 수율 숫자 자체에 오차가 있다.",
      "mc_mirror", 이웃=["Mismatch (Pelgrom)"]),
    _("Layout matching", "레이아웃 정합", 석사, DEV,
      r"\text{common-centroid, dummy, }\ \sigma\propto\tfrac{1}{\sqrt{WL}}",
      "같은 방향·같은 둘레·공통 중심·더미. 회로가 아니라 판이 정합을 정한다.",
      이웃=["Mismatch (Pelgrom)"]),
    _("Chopping", "초핑", 박사, A,
      r"v_{in}\to\times m(t)\to A\to\times m(t),\ \ f_{chop}>f_{corner}",
      "신호를 고주파로 올려 1/f 를 피하고 다시 내린다. 오프셋도 같이 지워진다.",
      이웃=["Flicker noise", "Correlated double sampling"]),
    _("Correlated double sampling", "상관 이중 샘플링", 박사, A,
      r"v_{out}=v[n]-v[n-1]\ \Rightarrow\ H(f)=2\sin(\pi f T)",
      "오프셋과 저주파 잡음을 빼기로 지운다. 대신 열잡음은 √2 배로 는다.",
      이웃=["Chopping", "Switched-capacitor circuits"]),
    _("Distortion HD2/HD3/IIP3", "왜곡·HD·IIP3", 박사, A,
      r"HD_3\approx\tfrac{a_3A^2}{4a_1},\quad IIP_3=\sqrt{\tfrac{4}{3}\left|\tfrac{a_1}{a_3}\right|},\quad P_{1dB}\approx IIP_3-9.6\,\mathrm{dB}",
      "선형성의 사양. 차동은 짝수 차수를 지우므로 HD3 가 남는 싸움이 된다.",
      "distortion",
      이웃=["Differential pair", "SNDR / ENOB"]),

    # ----------------------------------------------------------- 스위치드커패시터·변환기
    _("Switched-capacitor circuits", "스위치드 커패시터", 석사, A,
      r"R_{eq}=\tfrac{1}{f_s C},\quad H(z)=\tfrac{C_1}{C_2}\tfrac{z^{-1}}{1-z^{-1}}",
      "저항을 스위치와 커패시터로 대신한다. 정확도가 저항 절대값이 아니라 **용량 비**가 된다.",
      이웃=["Charge injection / clock feedthrough", "kT/C noise"]),
    _("Charge injection / clock feedthrough", "전하주입·클럭 피드스루", 석사, A,
      r"\Delta V=-\tfrac{W L C_{ox}(V_{GS}-V_{th})}{2C_H},\quad \text{dummy: }W_d=\tfrac{W}{2}",
      "스위치가 꺼질 때 채널 전하가 커패시터로 쏟아진다. 더미 스위치와 바텀플레이트로 막는다.",
      이웃=["Switched-capacitor circuits", "Sample and hold"]),
    _("Sample and hold", "샘플앤홀드", 석사, M,
      r"\text{aperture jitter: } SNR_{jitter}=-20\log(2\pi f_{in}\sigma_t)",
      "ADC 앞단. 지터가 고주파 입력에서 SNR 상한을 정한다.",
      이웃=["kT/C noise", "SAR ADC"]),
    _("SAR ADC", "SAR ADC", 석사, M,
      r"N\text{ cycles},\ \ V_{DAC}\to V_{in},\quad E_{conv}\propto C_{tot}V_{ref}^2",
      "이진 탐색. 저전력 중해상도의 표준이고, 커패시터 DAC 정합이 선형성을 정한다.",
      이웃=["Settling time", "DNL / INL"]),
    _("Flash / pipeline ADC", "플래시·파이프라인 ADC", 석사, M,
      r"\text{flash: }2^N-1\text{ comparators},\quad \text{pipeline: }V_{res}=G(V_{in}-D V_{ref})",
      "플래시는 빠르고 면적이 지수로 큰다. 파이프라인은 그 사이를 잇는다.",
      이웃=["Comparator", "SNDR / ENOB"]),
    _("Delta-sigma modulator", "델타시그마", 박사, M,
      r"SQNR=6.02N+1.76+10\log\tfrac{(2L+1)}{\pi^{2L}}OSR^{2L+1}\ \mathrm{dB}",
      "과표본화와 잡음정형으로 해상도를 산다. 차수 L 과 OSR 이 곧 비트다.",
      이웃=["SNDR / ENOB", "Sample and hold"]),
    _("DNL / INL", "DNL·INL", 석사, M,
      r"DNL_k=\tfrac{V_{k+1}-V_k}{V_{LSB}}-1,\quad INL_k=\sum_{i\le k}DNL_i",
      "변환기의 정적 선형성. DNL < -1 이면 코드가 사라진다(missing code).",
      이웃=["SAR ADC", "Mismatch (Pelgrom)"]),
    _("SNDR / ENOB", "SNDR·ENOB", 석사, M,
      r"ENOB=\tfrac{SNDR-1.76}{6.02},\quad SNDR=-10\log(10^{-SNR/10}+10^{-THD/10})",
      "잡음과 왜곡을 한 숫자로 묶은 실효 비트. 카탈로그의 N 비트가 아니라 이것이 진짜다.",
      이웃=["Distortion HD2/HD3/IIP3", "Delta-sigma modulator"]),
    _("Comparator", "비교기", 석사, M,
      r"t_{latch}=\tfrac{C_L}{g_m}\ln\tfrac{\Delta V_{out}}{\Delta V_{in}},\quad P_{meta}\propto e^{-t/\tau}",
      "되먹임 래치가 지수로 키운다. 입력이 작을수록 오래 걸리고, 어느 순간 못 정한다.",
      이웃=["Metastability", "Flash / pipeline ADC"]),

    # ------------------------------------------------------------------ PLL
    _("PLL basics", "PLL 기초", 석사, M,
      r"\omega_n=\sqrt{\tfrac{I_{CP}K_{VCO}}{2\pi C N}},\quad \zeta=\tfrac{R}{2}\sqrt{\tfrac{I_{CP}K_{VCO}C}{2\pi N}}",
      "위상을 맞추는 되먹임 루프. 루프대역이 VCO 잡음과 기준 잡음의 경계를 정한다.",
      이웃=["VCO phase noise", "Charge pump"]),
    _("VCO phase noise", "VCO 위상잡음", 박사, A,
      r"\mathcal{L}(\Delta f)=10\log\left[\tfrac{2FkT}{P_{sig}}\left(1+\left(\tfrac{f_0}{2Q\Delta f}\right)^2\right)\right]\ (\text{Leeson})",
      "Q 의 제곱으로 좋아진다. 전력과 Q 를 사는 것이 위상잡음을 사는 것이다.",
      이웃=["PLL basics", "Jitter"]),
    _("Charge pump", "차지펌프", 석사, M,
      r"I_{CP}\text{ mismatch}\Rightarrow\text{ref spur},\quad \text{dead zone}\Rightarrow\text{jitter}",
      "위상차를 전류로 바꾼다. 업/다운 전류 부정합이 그대로 스퍼가 된다.",
      이웃=["PLL basics"]),
    _("Jitter", "지터", 석사, M,
      r"\sigma_t^2=\tfrac{1}{(2\pi f_0)^2}\int 2\mathcal{L}(f)\,df",
      "위상잡음의 시간축 얼굴. 샘플링에서는 곧바로 SNR 상한이 된다.",
      이웃=["VCO phase noise", "Sample and hold", "Clock skew and jitter"]),

    # ------------------------------------------------------------ 디지털 기본
    _("CMOS inverter VTC", "CMOS 인버터 전달곡선", 학부, D,
      r"V_M=\tfrac{V_{DD}-|V_{thp}|+V_{thn}\sqrt{r}}{1+\sqrt{r}},\quad r=\tfrac{k_p'(W/L)_p}{k_n'(W/L)_n}",
      "디지털의 원자. 스위칭 문턱이 β 비로 움직인다.",
      "cmos_inverter_vtc", "cmos_inverter", ["Noise margins", "Propagation delay"]),
    _("Noise margins", "잡음 여유", 학부, D,
      r"NM_H=V_{OH}-V_{IH},\quad NM_L=V_{IL}-V_{OL}",
      "이득이 -1 이 되는 두 점이 VIL·VIH 다. 여유가 0 이면 논리가 무너진다.",
      "noise_margins", 이웃=["CMOS inverter VTC"]),
    _("Static CMOS logic", "정적 CMOS 논리", 학부, D,
      r"\text{PUN}=\overline{\text{PDN}}\ (\text{dual}),\quad \text{NAND2: }(W/L)_n=2(W/L)_{inv}",
      "직렬로 쌓인 만큼 넓혀야 같은 세기가 된다. 쌓기(stacking)가 지연을 정한다.",
      "nand_stack", "cmos_nand2", 이웃=["Logical effort", "Transmission gate"]),
    _("Propagation delay", "전파 지연", 학부, D,
      r"t_{p}=0.69R_{eq}C_L,\quad R_{eq}\approx\tfrac{3}{4}\tfrac{V_{DD}}{I_{DSAT}}\left(1-\tfrac{7}{9}\lambda V_{DD}\right)",
      "RC 로 본다. 부하가 늘면 선형으로 는다 -- 그것이 fan-out 곡선이다.",
      "inverter_delay",
      이웃=["Logical effort", "Interconnect RC delay"]),
    _("Logical effort", "논리 노력", 학부, D,
      r"d=gh+p,\quad \hat{f}=\sqrt[N]{F},\quad N_{opt}=\ln F/\ln 4",
      "게이트 사슬을 손으로 최적화하는 법. 단마다 같은 노력을 지는 것이 최소 지연이다.",
      "inverter_delay",
      이웃=["Propagation delay", "Fanout of 4"]),
    _("Fanout of 4", "FO4", 학부, D,
      r"t_{FO4}\approx 5\tau_{inv},\quad \text{process-independent yardstick}",
      "공정이 달라도 FO4 로 재면 비교가 된다. 파이프라인 단 길이의 잣대.",
      "inverter_delay",
      이웃=["Logical effort"]),
    _("Transmission gate", "전송 게이트", 학부, D,
      r"R_{eq}=\tfrac{1}{\tfrac{1}{R_n}+\tfrac{1}{R_p}}\approx\text{const over }V_{in}",
      "NMOS 와 PMOS 를 병렬로 붙여 전 구간에서 통한다. 멀티플렉서와 래치의 재료.",
      "transmission_gate", "transmission_gate",
      이웃=["Pass-transistor logic", "Latch vs flip-flop"]),
    _("Pass-transistor logic", "통과 트랜지스터 논리", 학부, D,
      r"V_{out,max}=V_{DD}-V_{th}\ (\text{NMOS only})",
      "적은 소자로 만들지만 문턱 강하로 전압이 깎이고 정적 전류가 흐른다.",
      "transmission_gate",
      이웃=["Transmission gate"]),
    _("Dynamic / domino logic", "동적·도미노 논리", 석사, D,
      r"\text{precharge}\to\text{evaluate},\quad \Delta V=\tfrac{C_X}{C_X+C_L}V_{DD}\ (\text{charge sharing})",
      "빠르고 작지만 전하 공유·누설·잡음에 약하다. 도미노는 단끼리 잇기 위한 반전기.",
      "charge_sharing",
      이웃=["Leakage power", "Static CMOS logic"]),

    # ------------------------------------------------------------ 순차·타이밍
    _("Latch vs flip-flop", "래치와 플립플롭", 학부, D,
      r"\text{latch: level-sensitive},\quad \text{FF}=\text{master}+\text{slave}",
      "래치는 투명하고 플립플롭은 순간이다. 시간 빌림(time borrowing)이 래치의 장점.",
      그림="setup_hold", 이웃=["Setup and hold", "Metastability"]),
    _("Setup and hold", "셋업·홀드", 학부, D,
      r"T\ge t_{cq}+t_{logic,max}+t_{su}+t_{skew},\quad t_{cq}+t_{logic,min}\ge t_{h}+t_{skew}",
      "타이밍의 두 부등식. 셋업은 주파수를 낮추면 풀리고 **홀드는 안 풀린다**.",
      그림="setup_hold", 이웃=["Clock skew and jitter", "Static timing analysis"]),
    _("Clock skew and jitter", "클럭 스큐·지터", 석사, D,
      r"T\ge t_{cq}+t_{logic}+t_{su}+\delta_{skew}+2\sigma_{jitter}",
      "스큐는 자리에 따른 차이, 지터는 판마다의 차이. 스큐는 홀드를 깨는 쪽이 더 무섭다.",
      이웃=["Setup and hold", "Clock distribution"]),
    _("Clock distribution", "클럭 분배", 석사, D,
      r"\text{H-tree, mesh},\quad P_{clk}\approx 0.3\text{-}0.4\,P_{total}",
      "칩 전력의 3분의 1이 클럭에 간다. H-트리는 스큐를, 메시는 지터를 잡는다.",
      이웃=["Clock skew and jitter", "Clock gating"]),
    _("Metastability", "준안정", 석사, D,
      r"MTBF=\tfrac{e^{t_r/\tau}}{T_0 f_{clk} f_{data}}",
      "셋업/홀드를 어기면 출력이 정해지는 데 지수 시간이 걸린다. 확률은 0 이 안 된다.",
      이웃=["CDC and synchronizers", "Comparator"]),
    _("CDC and synchronizers", "클럭 도메인 교차", 석사, D,
      r"\text{2-FF sync (1-bit)},\quad \text{gray code / handshake / async FIFO (multi-bit)}",
      "여러 비트를 2단 동기화기로 넘기면 비트마다 다른 판에 잡혀 없는 값이 생긴다.",
      이웃=["Metastability", "Static timing analysis"]),
    _("Static timing analysis", "정적 타이밍 분석", 석사, D,
      r"\text{slack}=T_{req}-T_{arr},\quad \text{setup slack}=T-t_{cq}-t_{logic}-t_{su}",
      "모든 경로를 벡터 없이 훑는다. 음의 슬랙 하나가 곧 못 쓰는 칩이다.",
      이웃=["Setup and hold", "Place and route"]),
    _("Place and route", "배치·배선", 석사, D,
      r"f_{max}=\tfrac{1}{t_{crit}},\quad t_{crit}=t_{logic}+t_{wire}",
      "지연의 대부분이 배선이다. 합성 게이트 수만으로는 속도를 못 말한다.",
      이웃=["Static timing analysis", "Interconnect RC delay"]),

    # ------------------------------------------------------------ 전력
    _("Dynamic power", "동적 전력", 학부, D,
      r"P_{dyn}=\alpha C_L V_{DD}^2 f",
      "전압의 제곱. 전압을 내리는 것이 언제나 제일 크게 먹힌다.",
      "inverter_power",
      이웃=["Short-circuit power", "DVFS"]),
    _("Short-circuit power", "단락 전력", 학부, D,
      r"P_{sc}=\tfrac{\beta}{12}(V_{DD}-2V_{th})^3\tfrac{\tau}{T}",
      "입력이 느리면 NMOS·PMOS 가 같이 켜진 채로 있다. 입력 기울기를 세우면 준다.",
      "inverter_power",
      이웃=["Dynamic power"]),
    _("Leakage power", "누설 전력", 석사, D,
      r"I_{sub}=I_0\tfrac{W}{L}e^{\tfrac{-V_{th}}{nV_T}}(1-e^{-V_{DS}/V_T}),\quad I_{gate},\ I_{GIDL}",
      "Vth 를 내리면 빨라지고 누설이 지수로 는다. multi-Vt 와 파워게이팅이 답.",
      이웃=["Subthreshold conduction", "Power gating"]),
    _("Clock gating", "클럭 게이팅", 석사, D,
      r"P\to\alpha_{eff}C V^2 f,\quad \alpha_{eff}=\alpha\cdot(\text{enable rate})",
      "안 쓰는 플립플롭의 클럭을 끊는다. 가장 값싼 저전력 기법.",
      이웃=["Dynamic power", "Clock distribution"]),
    _("Power gating", "파워 게이팅", 석사, D,
      r"V_{virtual}=V_{DD}-I R_{sleep},\quad t_{wake}\propto C_{block}R_{sleep}",
      "블록의 전원을 끊어 누설까지 지운다. 깨는 데 드는 시간과 돌진 전류가 대가.",
      이웃=["Leakage power", "DVFS"]),
    _("DVFS", "동적 전압·주파수 조절", 석사, D,
      r"E\propto V^2,\quad f\propto\tfrac{(V-V_{th})^2}{V}\ \Rightarrow\ E\propto f^{\sim2}",
      "느려도 되면 전압을 내려 에너지를 제곱으로 아낀다.",
      이웃=["Dynamic power", "Power gating"]),

    # ------------------------------------------------------- 산술·메모리·배선
    _("Adders", "가산기", 석사, D,
      r"\text{ripple }O(N),\ \text{CLA }O(\log N),\ G_{i:j}=G_i+P_iG_{i-1:j}",
      "전파 지연을 로그로 줄이는 것이 전부. Kogge-Stone 은 면적과 배선으로 그것을 산다.",
      이웃=["Multipliers", "Logical effort"]),
    _("Multipliers", "곱셈기", 석사, D,
      r"\text{Wallace: }O(\log N)\ \text{depth},\quad \text{Booth: } \tfrac{N}{2}\ \text{partial products}",
      "부분곱을 줄이고(Booth) 더하는 깊이를 줄인다(Wallace).",
      이웃=["Adders"]),
    _("SRAM 6T cell", "6T SRAM 셀", 석사, D,
      r"CR=\tfrac{(W/L)_{driver}}{(W/L)_{access}}>1.2,\quad PR=\tfrac{(W/L)_{access}}{(W/L)_{pull-up}}",
      "읽기는 셀을 흔들면 안 되고 쓰기는 흔들어야 한다. 그 둘이 셀 비를 반대로 민다.",
      "sram_read_disturb",
      이웃=["SRAM read/write margin", "Sense amplifier"]),
    _("SRAM read/write margin", "SRAM 읽기·쓰기 마진", 박사, D,
      r"SNM=\max\{a:\ a\times a\ \text{square fits in the butterfly lobe}\}",
      "읽는 동안 셀이 뒤집히지 않을 여유. 전압을 내리면 제일 먼저 무너지는 것.",
      "sram_read_disturb",
      이웃=["SRAM 6T cell", "Mismatch (Pelgrom)"]),
    _("Sense amplifier", "감지 증폭기", 석사, D,
      r"\Delta V_{BL}=\tfrac{I_{cell}t}{C_{BL}},\quad t_{sense}\propto\tfrac{C}{g_m}\ln\tfrac{V_{DD}}{\Delta V_{BL}}",
      "비트라인을 다 흔들지 않고 작은 차이만 읽어 시간과 전력을 아낀다.",
      이웃=["SRAM 6T cell", "Comparator"]),
    _("Interconnect RC delay", "배선 RC 지연", 석사, D,
      r"t_{Elmore}=\sum_i R_i C_{i\to n},\quad t_{wire}\propto \tfrac{rc\,L^2}{2}",
      "길이의 제곱으로 는다. 그래서 중계기를 넣어 선형으로 되돌린다.",
      "elmore",
      이웃=["Repeater insertion", "Place and route"]),
    _("Repeater insertion", "중계기 삽입", 박사, D,
      r"k_{opt}=L\sqrt{\tfrac{rc}{2R_0C_0}},\quad t\propto L\ (\text{after})",
      "L² 를 L 로 바꾼다. 대가는 전력과 면적.",
      "elmore",
      이웃=["Interconnect RC delay"]),
    _("Crosstalk", "누화", 박사, D,
      r"\Delta V=\tfrac{C_c}{C_c+C_L}V_{DD},\quad \text{Miller factor }0\text{-}2\ \text{on delay}",
      "옆 선이 같이 움직이면 지연이 최대 두 배까지 흔들린다. 실드와 순서 섞기로 막는다.",
      이웃=["Interconnect RC delay"]),
    _("Karnaugh map / logic minimization", "카르노맵·논리 최소화", 학부, D,
      r"\text{prime implicants}\to\text{minimal cover}",
      "손으로 하는 논리 최소화. 지금은 합성기가 하지만 왜 그렇게 되는지는 여기서 배운다.",
      그림="karnaugh_map", 이웃=["Static CMOS logic"]),
    _("Boolean / gate basics", "논리 게이트 기초", 학부, D,
      r"\overline{A\cdot B}=\overline{A}+\overline{B}\ (\text{De Morgan})",
      "드모간이 PUN/PDN 쌍대성의 뿌리다.",
      그림="logic_gates", 이웃=["Static CMOS logic", "Karnaugh map / logic minimization"]),

    # --------------------------------------------------------------- 방법론
    _("gm/ID methodology", "gm/ID 설계법", 박사, A,
      r"\tfrac{g_m}{I_D}=\tfrac{2}{V_{OV}}\ (\text{strong}),\ \tfrac{1}{nV_T}\ (\text{weak}),\quad f_T\propto V_{OV}",
      "Vov 하나로 이득·속도·전력을 한 장에 놓고 고른다. 제곱법칙이 안 맞는 공정에서도 통한다.",
      "gm_id",
      이웃=["Overdrive voltage", "Transconductance"]),
    _("RC low-pass / first-order response", "RC 저역통과", 학부, A,
      r"f_{-3dB}=\tfrac{1}{2\pi RC},\quad v(t)=V(1-e^{-t/RC})",
      "모든 대역 이야기의 밑동. 시상수 하나가 주파수와 시간 양쪽을 정한다.",
      "rc_lowpass", "rc_lowpass", ["Gain-bandwidth product"]),
    _("RLC resonance and Q", "RLC 공진과 Q", 학부, A,
      r"f_0=\tfrac{1}{2\pi\sqrt{LC}},\quad Q=\tfrac{1}{R}\sqrt{\tfrac{L}{C}}",
      "선택도. LC 발진기와 매칭망의 밑동이고, Q 가 위상잡음을 정한다.",
      "rlc_resonance", 이웃=["VCO phase noise"]),
    # ============================================================ 프론트엔드: 검증
    _("SystemVerilog for design", "설계용 SystemVerilog", 학부, D,
      r"\text{logic, always\_ff / always\_comb, packed vs unpacked, interface, package}",
      "합성되는 것과 시뮬레이션 전용을 가르는 것이 실력이다. `always_ff` 는 의도를 도구에 말하는 문법이다.",
      이웃=["Static CMOS logic", "Lint and coding standards"], 트랙=프론트),
    _("SystemVerilog Assertions", "SVA 단언", 석사, D,
      r"\text{assert property (@(posedge clk) req |-> \#\#[1:3] ack);}",
      "성질을 설계 옆에 붙여 둔다. 시뮬에서도 형식검증에서도 같은 문장이 쓰인다.",
      이웃=["Formal property verification", "Functional coverage"],
      트랙=프론트),
    _("Constrained-random verification", "제약 난수 검증", 석사, D,
      r"\text{class}\ \to\ \text{rand + constraint}\ \to\ \text{solver}\ \to\ \text{coverage feedback}",
      "직접 벡터로는 상태공간을 못 덮는다. 난수를 제약으로 몰아 넣고 커버리지로 되먹인다.",
      이웃=["Functional coverage", "UVM"], 트랙=프론트),
    _("Functional coverage", "기능 커버리지", 석사, D,
      r"\text{covergroup / coverpoint / cross}\ \to\ \text{hit all intended scenarios}",
      "코드 커버리지는 '돌았나', 기능 커버리지는 '의도한 상황을 봤나'. 둘 다 없으면 검증이 아니다.",
      이웃=["Code coverage", "Constrained-random verification"], 트랙=프론트),
    _("Code coverage", "코드 커버리지", 석사, D,
      r"\text{line, branch, toggle, FSM, expression}",
      "벤치가 설계의 얼마를 건드렸나. 통과한 벤치가 절반만 건드리는 일이 실제로 난다.",
      이웃=["Functional coverage", "Regression"], 트랙=프론트),
    _("UVM", "UVM 검증 방법론", 석사, D,
      r"\text{sequence}\to\text{driver}\to\text{DUT}\to\text{monitor}\to\text{scoreboard}",
      "검증 환경을 재사용 가능한 부품으로 쪼개는 표준. IP 와 함께 파는 VIP 가 이 꼴이다.",
      이웃=["Verification IP", "Constrained-random verification"], 트랙=프론트),
    _("Formal property verification", "형식 속성 검증", 석사, D,
      r"\text{BMC: } \exists\ \text{trace} \le k,\quad \text{induction: } \forall k",
      "솔버가 모든 입력을 뒤진다. 유계는 증명이 아니다 -- 귀납이 끝나야 증명이다.",
      이웃=["SystemVerilog Assertions", "CDC and synchronizers"],
      트랙=프론트),
    _("Regression", "회귀 검증", 석사, D,
      r"\text{nightly: } N\ \text{seeds}\times M\ \text{tests}\ \to\ \text{pass rate + coverage trend}",
      "한 번 통과는 우연일 수 있다. 상용 IP 는 시드를 바꿔 매일 돌린 결과를 딜리버러블로 낸다.",
      이웃=["Constrained-random verification", "Code coverage"], 트랙=프론트),
    _("Lint and coding standards", "린트와 코딩 표준", 학부, D,
      r"\text{width mismatch, inferred latch, blocking in seq, unused/undriven}",
      "시뮬은 통과하고 합성에서 무는 것들. IP 딜리버러블에는 린트 클린 리포트가 들어간다.",
      이웃=["SystemVerilog for design", "Static timing analysis"], 트랙=프론트),
    _("Low-power design and UPF", "저전력 설계·UPF", 석사, D,
      r"\text{power domain, isolation, level shifter, retention, state table}",
      "전원이 여럿인 칩에서 무엇을 끄고 무엇을 지킬지 UPF 로 적는다. RTL 에는 안 보인다.",
      이웃=["Power gating", "Clock gating"], 트랙=프론트),

    # ============================================================ 백엔드: 물리 구현
    _("Physical design is a third domain", "백엔드는 제3의 영역", 학부, D,
      r"\text{RTL}\ \to\ \text{netlist of characterized cells}\ \to\ \text{GDSII}",
      "백엔드는 트랜지스터를 설계·시뮬레이션하지 않는다. 캐릭터라이즈된 셀을 블랙박스로 받아 배치·배선·타이밍을 다룬다 -- 디지털 논리도 아날로그도 아니다.",
      이웃=["Standard cell library", "Place and route"], 트랙=백엔드),
    _("Standard cell library", "스탠다드 셀 라이브러리", 석사, D,
      r"\text{.lib: } t_{pd}=f(\text{input slew},\ C_{load})\ \text{lookup table (NLDM)}",
      "셀의 지연·전력은 파운드리가 SPICE 로 미리 재서 표로 넘긴다. 백엔드는 그것을 **블랙박스**로 받아 값만 쓰고, 왜 그 지연이 나는지 트랜지스터 식으로 유도하지 않는다.",
      이웃=["Physical design is a third domain", "Static timing analysis"], 트랙=백엔드),
    _("Logic synthesis", "논리 합성", 석사, D,
      r"\text{RTL}\to\text{generic}\to\text{technology mapping}\to\text{gate netlist + area/timing}",
      "제약(SDC)과 라이브러리를 주면 게이트로 바꿔 준다. 제약 없는 합성은 뜻이 없다.",
      이웃=["Standard cell library", "Timing constraints (SDC)"],
      트랙=백엔드),
    _("Timing constraints (SDC)", "타이밍 제약 SDC", 석사, D,
      r"\text{create\_clock, set\_input\_delay, set\_false\_path, set\_multicycle\_path}",
      "도구에게 무엇이 맞는지 알려 주는 유일한 통로. 제약이 틀리면 초록불이 거짓말을 한다.",
      이웃=["Static timing analysis", "Logic synthesis"], 트랙=백엔드),
    _("Floorplanning", "플로어플랜", 석사, D,
      r"\text{utilization} = \tfrac{\text{cell area}}{\text{core area}},\quad \text{macro placement, pin assignment}",
      "칩의 첫 결정이고 뒤를 다 좌우한다. 여기서 틀리면 배선에서 못 푼다.",
      이웃=["Placement", "Power grid and IR drop"], 트랙=백엔드),
    _("Placement", "배치", 석사, D,
      r"\min \sum \text{HPWL} \ \text{s.t. legality, density, timing}",
      "선 길이를 줄이는 문제이자 타이밍 문제다. 배선 지연의 대부분이 여기서 정해진다.",
      이웃=["Floorplanning", "Routing"], 트랙=백엔드),
    _("Clock tree synthesis", "클럭 트리 합성 CTS", 석사, D,
      r"\text{skew} = \max_i t_i - \min_i t_i,\quad \text{insertion delay, H-tree / mesh}",
      "클럭을 모든 플립플롭에 같은 때에 넣는 일. 칩 전력의 3분의 1이 여기 간다.",
      이웃=["Clock skew and jitter", "Clock distribution"], 트랙=백엔드),
    _("Routing", "배선", 석사, D,
      r"\text{global}\to\text{track assign}\to\text{detail},\quad \text{DRC clean}",
      "금속층에 실제 선을 긋는다. 여기서 생긴 RC 가 타이밍을 다시 흔든다.",
      이웃=["Placement", "Parasitic extraction"], 트랙=백엔드),
    _("Parasitic extraction", "기생 추출", 석사, D,
      r"\text{SPEF: } R,\ C_{gnd},\ C_{coupling}\ \text{per net}",
      "배선의 저항·용량을 뽑아 타이밍에 되먹인다. **백엔드가 직접 다루는 유일한 회로 이론**이다.",
      "elmore", 이웃=["Interconnect RC delay", "Crosstalk"], 트랙=백엔드),
    _("Timing closure", "타이밍 클로저", 석사, D,
      r"\text{WNS} \ge 0\ \text{and}\ \text{TNS}=0\ \text{across all corners and modes}",
      "음의 슬랙 하나가 못 쓰는 칩이다. 합성-배치-배선을 되풀이하며 좁혀 간다.",
      이웃=["Static timing analysis", "MCMM"], 트랙=백엔드),
    _("MCMM", "다중 코너·다중 모드", 석사, D,
      r"\text{corner} \in \{SS,TT,FF\}\times\{V_{min},V_{max}\}\times\{T_{min},T_{max}\}",
      "느린 코너가 셋업을, 빠른 코너가 홀드를 깬다. 한 코너만 맞추면 칩이 안 돈다.",
      이웃=["Timing closure", "Static timing analysis"], 트랙=백엔드),
    _("DFT: scan and ATPG", "DFT 스캔·ATPG", 석사, D,
      r"\text{coverage} = \tfrac{\text{detected faults}}{\text{total faults}},\ \text{stuck-at / transition}",
      "다 만든 칩이 제대로 만들어졌는지 테스트하는 회로를 미리 넣는다. 면적과 타이밍을 먹는다.",
      이웃=["MBIST", "Timing closure"], 트랙=백엔드),
    _("MBIST", "메모리 내장 자가시험", 석사, D,
      r"\text{March C-}:\ \Uparrow(w0)\Uparrow(r0,w1)\Uparrow(r1,w0)\Downarrow(r0,w1)\Downarrow(r1,w0)\Uparrow(r0)",
      "메모리는 스캔으로 못 본다. 패턴 발생기를 칩 안에 넣어 스스로 돌린다.",
      이웃=["DFT: scan and ATPG", "SRAM 6T cell"], 트랙=백엔드),
    _("Power grid and IR drop", "전원망과 IR 드롭", 박사, D,
      r"\Delta V = I R_{grid},\quad \text{dynamic: } L\tfrac{di}{dt}\ \text{(di/dt noise)}",
      "전원이 내려앉으면 셀이 느려지고 타이밍이 깨진다. 플로어플랜에서 같이 푼다.",
      이웃=["Floorplanning", "Signal integrity"], 트랙=백엔드),
    _("Signal integrity", "신호 무결성 SI", 박사, D,
      r"\text{crosstalk delay/noise},\quad \text{EM: } J < J_{max}",
      "옆 선과 전자이동. 미세 공정에서 이것이 실제로 칩을 죽인다.",
      이웃=["Crosstalk", "Power grid and IR drop"], 트랙=백엔드),
    _("Physical verification (DRC/LVS)", "물리 검증 DRC·LVS", 석사, D,
      r"\text{DRC: layout} \models \text{rules},\quad \text{LVS: layout} \equiv \text{schematic}",
      "파운드리에 넘기기 전 마지막 관문. 여기서 빨간불이면 테이프아웃이 안 된다.",
      이웃=["Routing", "GDSII and tapeout"], 트랙=백엔드),
    _("GDSII and tapeout", "GDSII·테이프아웃", 석사, D,
      r"\text{GDSII / OASIS} \to \text{mask} \to \text{wafer}",
      "설계가 마스크가 되는 자리. 되돌릴 수 없어서 그 앞의 모든 검사가 존재한다.",
      이웃=["Physical verification (DRC/LVS)", "MPW shuttle"], 트랙=백엔드),
    _("PDK", "공정 설계 키트", 석사, D,
      r"\text{models (SPICE) + .lib + LEF/DEF + DRC/LVS rules + layers}",
      "파운드리가 주는 한 벌. 오픈 PDK(Skywater 130nm)로 상용 툴 없이 전 과정을 실습할 수 있다.",
      이웃=["Standard cell library", "Open EDA flow"], 트랙=백엔드),
    _("Open EDA flow", "오픈 EDA 흐름", 석사, D,
      r"\text{Yosys}\to\text{OpenROAD/OpenLane}\to\text{GDSII},\ \text{Skywater 130nm}",
      "라이선스 없이 RTL 에서 GDSII 까지 손으로 돌려 볼 수 있다. 백엔드는 손으로 해 봐야 붙는다.",
      이웃=["PDK", "Place and route"], 트랙=백엔드),

    # ============================================================ IP 특화
    _("AMBA AXI / AHB / APB", "AMBA 버스", 석사, D,
      r"\text{AXI: 5 channels, } \text{VALID}/\text{READY handshake, out-of-order via ID}",
      "팔리는 IP 는 대부분 표준 버스를 구현한 것이다. 스펙 문서를 읽고 해석하는 능력이 핵심이다.",
      이웃=["Verification IP", "Soft IP vs hard IP"], 트랙=IP특화),
    _("High-speed interface IP", "고속 인터페이스 IP", 석사, M,
      r"\text{PCIe, USB, DDR/HBM, MIPI, UCIe} = \text{PHY} + \text{controller}",
      "가장 비싸게 팔리는 IP 갈래. PHY 는 아날로그, 컨트롤러는 디지털이라 둘 다 필요하다.",
      이웃=["AMBA AXI / AHB / APB", "PLL basics"], 트랙=IP특화),
    _("Soft IP vs hard IP", "소프트 IP·하드 IP", 석사, D,
      r"\text{soft}=\text{RTL (portable)},\quad \text{hard}=\text{GDSII (fixed process)}",
      "소프트는 공정을 옮길 수 있고 하드는 성능이 보장된다. 파는 물건의 꼴이 다르다.",
      이웃=["Design reuse", "PDK"], 트랙=IP특화),
    _("Design reuse", "재사용 설계", 석사, D,
      r"\text{parameterize, no hard-coded timing, clean CDC, documented interfaces}",
      "여러 공정·여러 SoC 에 이식되도록 짓는 원칙. IP 를 제품으로 만드는 것은 이것이다.",
      이웃=["Soft IP vs hard IP", "IP deliverables"], 트랙=IP특화),
    _("Verification IP", "검증 IP (VIP)", 석사, D,
      r"\text{protocol checker + stimulus generator + coverage model}",
      "IP 만 파는 것이 아니라 그것을 검증하는 IP 까지 같이 판다. 업계 관행이다.",
      이웃=["UVM", "AMBA AXI / AHB / APB"], 트랙=IP특화),
    _("IP deliverables", "IP 딜리버러블", 석사, D,
      r"\text{RTL + VIP + coverage + synth/timing + SDC + TRM + integration guide}",
      "'도는 RTL' 은 딜리버러블이 아니다. 무엇을 함께 내야 하는지가 상용과 습작을 가른다.",
      이웃=["Technical documentation (TRM)", "Silicon proven"], 트랙=IP특화),
    _("Technical documentation (TRM)", "기술 문서·TRM", 석사, D,
      r"\text{register map + timing diagrams + integration + programming model}",
      "영어 기술 문서 작성력이 실제 채용 기준에 든다. Arm Cortex-M TRM 이 그 표준 꼴이다.",
      이웃=["IP deliverables", "Design reuse"], 트랙=IP특화),
    _("Silicon proven", "실리콘 검증", 석사, D,
      r"\text{test chip}\to\text{bring-up}\to\text{shmoo plot}\ (V_{DD}\times f)",
      "돌아 본 적 있는 IP 와 없는 IP 는 값이 다르다. 그래서 테스트칩 이력이 팔린다.",
      이웃=["IP deliverables", "MPW shuttle"], 트랙=IP특화),

    # ============================================================ 포트폴리오
    _("MPW shuttle", "MPW 셔틀", 석사, D,
      r"\text{many designs on one wafer}\ \Rightarrow\ \text{cost}/N",
      "Efabless·Europractice 로 실제 테이프아웃 경험을 싸게 얻는다. 이력서에서 가장 센 한 줄.",
      이웃=["GDSII and tapeout", "Open EDA flow"], 트랙=포트폴리오),
    _("Open source IP cores", "오픈소스 IP 코어", 학부, D,
      r"\text{Ibex/OpenTitan (lowRISC), Caliptra/VeeR (CHIPS), CVA6, PULP, OpenCores}",
      "상용에 가장 가까운 공개 실물. 검증 파이프라인(CI, riscv-dv)까지 그대로 배울 수 있다.",
      이웃=["Regression", "IP deliverables"], 트랙=포트폴리오),
    _("Reading a real IP datasheet", "IP 데이터시트 읽기", 학부, D,
      r"\text{D and R catalog},\ \text{Synopsys DesignWare},\ \text{Arm TRM}",
      "무엇이 스펙으로 적히는지 보면 무엇을 만들어야 하는지 보인다. RTL 은 NDA 지만 스펙은 공개다.",
      이웃=["Technical documentation (TRM)", "High-speed interface IP"], 트랙=포트폴리오),
    # ============================================================ 생태계
    # 출처: 사용자 강의자료 `반도체공학개론` Lecture 4 "The Semiconductor Ecosystem"
    # (Jaeeun Jang, Department of Semiconductor System). IP 디자인하우스가 밸류체인의
    # 어디에 앉고 무엇을 파는지를 여기 둔다 -- 기술만 알고 자리를 모르면 진로가 안 잡힌다.
    _("Company types", "회사 갈래", 학부, D,
      r"\text{IDM},\ \text{Fabless},\ \text{Foundry},\ \text{OSAT},\ \text{Chipless (IP + design house)}",
      "IDM 은 설계와 제조를 다 하고, 팹리스는 설계만, 파운드리는 제조만, OSAT 는 패키지·테스트, 칩리스는 설계 자체를 판다.",
      이웃=["IP and design house", "Fabless-foundry model"], 트랙=생태계),
    _("IP and design house", "IP·디자인하우스", 학부, D,
      r"\text{revenue} = \text{license fee} + \text{royalty}\times\text{units}",
      "ARM 은 청사진을 팔지 칩을 안 판다 -- 스마트폰의 약 99% 안에 들어 있다. 디자인하우스는 팀이 없는 회사를 대신해 설계해 주는 곳이고, 이 학과 졸업생의 실제 진로다.",
      이웃=["Company types", "Why buy IP", "Value capture"], 트랙=생태계),
    _("Why buy IP", "왜 IP 를 사는가", 학부, D,
      r"\text{modern SoC} \supset 100+\ \text{IP blocks}",
      "한 팀이 다 설계할 수 없다. 표준 부품은 사고 차별화되는 데에 재능을 쓴다 -- 그래서 IP 시장이 존재한다.",
      이웃=["IP and design house", "RISC-V and open ISA"], 트랙=생태계),
    _("RISC-V and open ISA", "RISC-V·개방 ISA", 학부, D,
      r"\text{ISA}\ \text{free}\ \ne\ \text{implementation free}",
      "프로세서의 리눅스 같은 것. MCU 와 AI 칩에서 빠르게 는다. 명령어 집합은 공짜여도 구현(코어)은 여전히 만들거나 사야 한다.",
      이웃=["Why buy IP", "Open source IP cores"], 트랙=생태계),
    _("Fields of chip design", "칩 설계의 갈래", 학부, M,
      r"\text{digital},\ \text{analog},\ \text{mixed-signal},\ \text{RF},\ \text{memory}",
      "디지털은 HDL 로 쓰고 도구가 배치하는 큰 팀, 아날로그는 Virtuoso 에서 트랜지스터를 손으로 그리는 작은 정예 팀. 같은 칩 안에 다섯 가지 공학 문화가 있다.",
      이웃=["Physical design is a third domain", "Company types"], 트랙=생태계),
    _("Fabless-foundry model", "팹리스·파운드리 모델", 학부, D,
      r"1987:\ \text{TSMC} \Rightarrow \text{design}\ \perp\ \text{manufacturing}",
      "설계와 제조를 갈라 놓은 사업 모델 하나가 산업 전체를 다시 그렸다. 팹이 없어도 칩을 팔 수 있게 됐다.",
      이웃=["Company types", "PDK and tape-out"], 트랙=생태계),
    _("PDK and tape-out", "PDK 와 테이프아웃", 학부, D,
      r"\text{PDK}\ \to\ \text{design in rules}\ \to\ \text{GDS}\ \to\ \text{mask}\ (5\text{-}20\ \mathrm{M\ USD})",
      "파운드리가 그 공정의 규칙서와 부품 목록(PDK)을 준다. 테이프아웃은 GDS 를 넘기는 날이고, 그 뒤로는 고칠 수 없다.",
      이웃=["PDK", "GDSII and tapeout", "MPW shuttle"], 트랙=생태계),
    _("Foundry process menu", "파운드리 공정 메뉴", 학부, M,
      r"\text{2-5nm logic},\ \text{28-180nm mature},\ \text{BCD},\ \text{RF-SOI/SiGe},\ \text{CIS}",
      "최신 공정만 있는 게 아니다. MCU 와 차량용은 성숙 공정이 싸고 검증됐고, PMIC 는 BCD, 라디오는 RF-SOI 가 맞다. 공정은 일에 맞춰 고른다.",
      이웃=["PDK and tape-out", "High-speed interface IP"], 트랙=생태계),
    _("EDA industry", "EDA 산업", 학부, D,
      r"\text{SPICE},\ \text{layout},\ \text{DRC/LVS},\ \text{synthesis + P and R}:\ \sim 15\text{-}20\ \mathrm{B\ USD}",
      "920억 개 트랜지스터를 손으로 그릴 수 없다. Synopsys·Cadence·Siemens 셋이 지배한다 -- 이 저장소가 쓰는 오픈 도구들이 그 자리의 무료판이다.",
      이웃=["Open EDA flow", "Value capture"], 트랙=생태계),
    _("Equipment and materials layer", "장비·소재 층", 학부, D,
      r"\text{ASML EUV }13.5\,\mathrm{nm},\ \sim 200\ \mathrm{M\ USD/tool};\ \text{wafer purity } 99.9999999\%",
      "EUV 는 ASML 한 곳만 만든다. 2019년 일본의 소재 3종 수출 규제가 한국 반도체를 흔들었다 -- '지루한' 층이 700조 산업을 하루아침에 멈출 수 있다.",
      이웃=["EDA industry", "Company types"], 트랙=생태계),
    _("Advanced packaging", "선단 패키징", 석사, M,
      r"\text{2.5D: interposer},\quad \text{3D: HBM }8\text{-}12\ \text{dies stacked}",
      "트랜지스터 미세화가 느려지자 패키징이 새 전선이 됐다. TSMC 의 CoWoS 용량이 세계 AI GPU 공급을 정한다.",
      이웃=["Foundry process menu", "High-speed interface IP"], 트랙=생태계),
    _("Chip development timeline", "칩 개발 기간", 학부, D,
      r"12\text{-}24\ \text{mo design} + 3\text{-}4\ \text{mo fab} + 3\text{-}6\ \text{mo test} \approx 2\text{-}3\ \text{yr}",
      "NRE 가 1억 달러대로 앞에 들고, 칩당 원가는 몇 달러다. 그래서 칩은 큰 시장을 쫓고 실수는 몇 년을 먹는다.",
      이웃=["PDK and tape-out", "Value capture"], 트랙=생태계),
    _("Value capture", "값은 누가 가져가나", 학부, D,
      r"\text{EDA/IP } 85\text{-}95\%\ >\ \text{fabless } 60\text{-}75\%\ >\ \text{foundry } 50\text{-}55\%\ >\ \text{OSAT } 10\text{-}20\%",
      "사슬에 있는 것과 돈을 버는 것은 다르다. IP 와 EDA 가 소프트웨어 경제학으로 가장 높은 마진을 가져간다 -- IP 디자인하우스를 노리는 이유가 여기 있다.",
      이웃=["IP and design house", "EDA industry"], 트랙=생태계),
    _("Chip design spreads everywhere", "칩 설계가 퍼진다", 학부, D,
      r"\text{Apple M-series},\ \text{Google TPU},\ \text{Tesla FSD}\ \to\ \text{custom} \Rightarrow \text{differentiation}",
      "애플·구글·테슬라는 칩을 설계하지만 팔지 않는다. 자기 작업부하에 맞춘 칩이 가장 빠르기 때문이다 -- 장래 고용주가 반도체 회사만은 아니라는 뜻이다.",
      이웃=["Company types", "IP and design house"], 트랙=생태계),

    # ------------------------------------------------ 교안: 2026 VLSI ch0 (Introduction)
    _("Design abstraction levels", "설계 추상 계층", 학부, D,
      r"\text{device}\to\text{circuit}\to\text{gate}\to\text{module}\to\text{system}",
      "한 칩을 다섯 층으로 나눠 본다. 어느 층의 물음인지 먼저 정해야 답의 도구가 정해진다 -- "
      "소자는 SPICE, 게이트 위는 RTL 과 합성이다.",
      이웃=["Analog versus digital design", "Standard cell library"], 트랙=공통),
    _("Analog versus digital design", "아날로그 대 디지털 설계", 학부, M,
      r"\text{analog: not rail-to-rail},\quad \text{digital: rail-to-rail, fixed }T",
      "아날로그 신호는 레일 사이 아무 값이고 주기가 없으며 잡음에 약해 손으로 레이아웃한다. "
      "디지털은 레일 투 레일에 주기가 일정하고 잡음에 강해 도구가 배치한다. 같은 칩, 다른 공학 문화다.",
      그림="cmos_inverter", 이웃=["Noise margins", "Design abstraction levels"], 트랙=공통),
    _("Combinational versus sequential", "조합 대 순차", 학부, D,
      r"\text{comb: }Y=f(X),\quad \text{seq: }Q^{+}=f(X,Q)",
      "조합은 클럭도 기억도 없어 출력이 입력에 곧바로 따른다. 순차는 클럭과 임시 기억이 있어 "
      "이전 상태를 쓴다 -- 그 기억을 위해 이상적인 경우에도 D 에서 Q 까지 지연이 있다고 본다.",
      그림="setup_hold", 이웃=["Setup and hold", "Static timing analysis"], 트랙=공통),
    _("Eye diagram", "아이 다이어그램", 학부, M,
      r"\text{fold }v(t)\text{ modulo }T_{UI}\Rightarrow(\text{eye height},\ \text{eye width})",
      "한 주기씩 접어 한 틀에 겹쳐 그린다. 눈으로는 안 보이던 잡음과 ISI 가 눈높이(V)와 "
      "눈너비(UI)라는 두 숫자가 된다. 고속 링크에서 가장 먼저 보는 그림이다.",
      이웃=["Intersymbol interference", "Clock skew and jitter", "Bit error rate"],
      트랙=고속링크, 링크="isi_closed_eye"),
    _("Clock versus data rate", "클럭과 데이터율의 단위", 학부, D,
      r"f_{clk}=500\,\text{MHz}\ \ne\ 500\,\text{Mb/s data}",
      "500MHz 클럭은 한 주기에 1과 0을 한 번씩 내지만 500Mb/s 데이터는 한 UI 에 한 비트다. "
      "같은 그림을 1100 이라 읽을 수도 11000 이라 읽을 수도 있다 -- 단위를 못 박지 않으면 둘이 섞인다.",
      이웃=["Eye diagram", "Clock and data recovery"], 트랙=고속링크),

    # ------------------------------------------------ 교안: ch1 (Inverter, Fanout)
    _("Inverter VTC", "인버터 전달특성", 학부, D,
      r"V_{M}:\ V_{out}=V_{in},\quad \tfrac{\partial V_{out}}{\partial V_{in}}\ll -1",
      "입력을 쓸었을 때 출력이 그리는 곡선. PMOS 와 NMOS 의 Ron 싸움이 출력을 0 이나 VDD 로 "
      "밀고, 둘이 비기는 점이 스위칭 문턱 VM 이다. 잡음 여유가 전부 이 곡선에서 나온다.",
      넷="cmos_inverter_vtc", 그림="cmos_inverter",
      이웃=["Noise margins", "PMOS to NMOS width ratio"], 트랙=공통),
    _("PMOS to NMOS width ratio", "WP 대 WN 비", 학부, D,
      r"R_{on}\propto\frac{1}{\mu C_{ox}(W/L)(V_{DD}-V_{th})}\Rightarrow W_P=\frac{\mu_n}{\mu_p}W_N",
      "Ron 을 맞추려면 이동도 비만큼 PMOS 를 넓혀야 한다. 긴 채널에서 mu_n 은 mu_p 의 약 2배라 "
      "WP=2WN 이다. 짧은 채널에서는 속도포화로 1.3~1.5배까지 줄어든다.",
      넷="cmos_inverter_vtc", 그림="cmos_inverter",
      이웃=["Short-channel effects", "Inverter VTC"], 트랙=공통),
    _("Ideal switch RC delay model", "이상 스위치-RC 지연 모형", 학부, D,
      r"t_{pHL}=\ln 2\cdot R_{on,N}C_L,\qquad t_{pLH}=\ln 2\cdot R_{on,P}C_L",
      "트랜지스터를 켜짐 저항으로, 부하를 커패시터로 바꿔 RC 로 푼다. VDD/2 를 지나는 데 "
      "걸리는 시간이 ln2·RC 다 -- 디지털 지연 계산의 밑동이고, 0.69RC 라는 숫자가 여기서 나온다.",
      넷="inverter_delay", 그림="cmos_inverter",
      이웃=["Interconnect RC delay", "Fanout"], 트랙=공통),
    _("Fanout", "팬아웃", 학부, D,
      r"C_L=3C_{out}+f\cdot 3C_{in},\qquad t_p=\ln 2\cdot R_{on}\cdot 3C_{in}(\alpha+f)",
      "다음 단이 이번 단보다 f 배 크다는 비율. 한 단의 지연이 (alpha+f) 에 비례하므로 "
      "f 가 커지면 한 단은 느려지지만 필요한 단수는 준다 -- 그 맞바꿈이 다음 항목이다.",
      이웃=["FO4 delay", "Ideal switch RC delay model"], 트랙=공통),
    _("FO4 delay", "FO4 지연", 학부, D,
      r"t_{p,total}=N\ln 2\,R_{on}3C_{in}(\alpha+f),\ \ 3C_{in}=\frac{C_L}{f^{N}}\Rightarrow f=e^{1+\alpha/f}",
      "전체 지연을 f 로 미분해 0 으로 두면 최적 팬아웃이 f=e^(1+alpha/f) 를 푼 값이다. "
      "기생이 없으면 e=2.718, 실제 공정(alpha~1)에서는 4 근처라 FO4 를 공정 무관 속도 잣대로 쓴다.",
      이웃=["Fanout", "Logical effort"], 트랙=공통),
    _("Ring oscillator", "링 오실레이터", 학부, M,
      r"f_{osc}=\frac{1}{2N t_{p}},\qquad N\ \text{odd}",
      "인버터를 홀수 개 고리로 이으면 발진한다. 한 바퀴에 반주기가 지나가므로 주기가 2N·tp 다. "
      "공정 속도를 재는 자와 VCO 의 몸통 둘 다로 쓴다 -- 단수가 짝수면 래치가 되어 안 돈다.",
      이웃=["Voltage controlled oscillator", "FO4 delay"], 트랙=공통),

    # ------------------------------------------------ 교안: ch4 (PLL / DPLL)
    _("H-tree clock distribution", "H 트리 클럭 분배", 석사, D,
      r"\ell(\text{root}\to\text{leaf})=\text{const}\Rightarrow\text{skew}\approx 0",
      "뿌리에서 모든 잎까지 배선 길이를 같게 만드는 레이아웃. 길이가 같으면 지연이 같고, "
      "그래야 스큐가 안 생긴다. 클럭을 '어디서 얻나' 의 다음 물음이 '어떻게 고르게 뿌리나' 다.",
      이웃=["Clock skew and jitter", "Phase-locked loop"], 트랙=백엔드),
    _("Phase-locked loop", "위상고정루프 PLL", 석사, M,
      r"\frac{\Phi_{out}}{\Phi_{ref}}(s)=\frac{K_{PD}K_{VCO}F(s)/s}{1+K_{PD}K_{VCO}F(s)/(sN)}",
      "밖에서 온 느리지만 정확한 기준 클럭에 칩 안의 빠른 발진기를 음되먹임으로 묶는다. "
      "빠른 클럭은 핀 부하 때문에 밖에서 못 받고, 칩 안 발진기는 공정 산포로 주파수가 안 맞기 때문이다.",
      이웃=["Phase frequency detector", "Phase-locked loop",
          "Voltage controlled oscillator", "Frequency divider"], 트랙=고속링크),
    _("Phase frequency detector", "위상주파수 검출기 PFD", 석사, M,
      r"\text{UP}-\text{DN}\ \propto\ \Delta\phi\quad(\text{range }\pm 2\pi)",
      "두 클럭의 앞섬/뒤짐을 UP·DN 펄스 폭으로 낸다. 단순 XOR 위상검출기와 달리 주파수 차이도 "
      "구별해서 락 범위가 ±2pi 로 넓다 -- 그래서 PLL 이 처음부터 잡을 수 있다.",
      이웃=["Phase-locked loop", "Phase-locked loop", "Bang-bang phase detector"], 트랙=고속링크),
    _("Voltage controlled oscillator", "전압제어 발진기 VCO", 석사, M,
      r"\omega_{out}=\omega_0+K_{VCO}V_{ctrl},\qquad \Phi_{out}=\frac{K_{VCO}}{s}V_{ctrl}",
      "제어 전압으로 주파수를 움직인다. 위상은 주파수의 적분이므로 루프에 1/s 극점을 하나 "
      "공짜로 넣는다 -- PLL 이 최소 2차가 되는 까닭이다.",
      이웃=["Ring oscillator", "LC versus ring oscillator",
          "Digitally controlled oscillator"], 트랙=고속링크),
    _("LC versus ring oscillator", "LC 대 링 발진기", 석사, A,
      r"Q_{LC}\gg Q_{ring}\Rightarrow \mathcal{L}(\Delta f)_{LC}\ll \mathcal{L}(\Delta f)_{ring}",
      "LC 는 위상잡음이 낮지만 주파수 범위가 좁고 인덕터가 면적을 먹는다. 링은 범위가 넓고 "
      "작지만 위상잡음이 크다. 무엇을 살지 고르는 맞바꿈이다.",
      이웃=["Ring oscillator", "Voltage controlled oscillator", "Clock skew and jitter"], 트랙=고속링크),
    _("Frequency divider", "주파수 분주기", 석사, D,
      r"f_{out}=\frac{f_{in}}{2}\ \ (\text{toggle FF}),\qquad f_{out}=\frac{f_{in}}{N}",
      "되먹임 플립플롭 하나가 상태 둘을 오가며 2분주한다. 분주기는 상태 기계이고, PLL 의 "
      "되먹임 경로에 들어가 출력 주파수를 기준의 N 배로 곱한다.",
      이웃=["Dual-modulus divider", "Phase-locked loop"], 트랙=고속링크),
    _("Dual-modulus divider", "듀얼 모듈러스 분주기", 박사, D,
      r"N=P\cdot M+S\quad(\text{swallow }S\text{ of }P\text{ cycles at }M{+}1)",
      "제어 비트로 M 과 M+1 을 오가는 분주기를 펄스 스왈로 카운터와 엮으면 임의의 정수 N 이 "
      "나온다. 빠른 앞단만 고속으로 짓고 뒷단은 느리게 지어도 되게 하는 구조다.",
      이웃=["Frequency divider", "Phase-locked loop"], 트랙=고속링크),
    _("Current mode logic latch", "CML 래치 current mode logic", 박사, M,
      r"V_{swing}=I_{SS}R_D\ \ (\ll V_{DD}),\qquad f_{max}\propto\frac{1}{R_D C_L}",
      "차동쌍이 꼬리전류를 좌우로 옮겨 작은 스윙으로 판정한다. 스윙이 작아 CMOS 보다 훨씬 "
      "빠르고 전원 잡음에 강하지만 정적 전류를 늘 먹는다 -- VCO 바로 뒤의 분주기가 이것을 쓴다.",
      그림="diff_pair", 이웃=["Differential pair", "Frequency divider"], 트랙=고속링크),
    _("All-digital PLL", "전디지털 PLL ADPLL", 박사, D,
      r"\text{TDC}\to\text{DLF}(K_P,K_I)\to\text{DCO},\quad \text{feedback }1/N",
      "위상 검출을 TDC 로, 루프 필터를 디지털 덧셈기와 누산기로, 발진기를 DCO 로 바꾼다. "
      "면적이 작고 공정 미세화의 이득을 그대로 받으며 다른 공정으로 옮기기 쉽다.",
      이웃=["Time-to-digital converter", "Digital loop filter",
          "Digitally controlled oscillator"], 트랙=고속링크),
    _("Time-to-digital converter", "시간-디지털 변환기 TDC", 박사, M,
      r"B_{TDC}=\left\lfloor\frac{\Delta t}{\Delta t_{resol}}\right\rfloor\ (\text{2's complement})",
      "두 클럭의 시간 차이를 지연 소자 사슬로 재서 정수로 낸다. 분해능이 한 지연 소자이고, "
      "앞섬/뒤짐을 부호로 내야 하므로 2의 보수로 적는다 -- 이것이 ADPLL 의 위상 검출기다.",
      이웃=["All-digital PLL", "Ring oscillator", "Quantized equalizer taps"], 트랙=고속링크),
    _("Digital loop filter", "디지털 루프 필터 DLF", 박사, D,
      r"B_{ctrl}[n]=K_P B_{TDC}[n]+K_I\sum_{k\le n}B_{TDC}[k],\quad H(z)=K_P+\frac{K_I}{1-z^{-1}}",
      "비례항이 응답 속도를, 적분항이 정상상태 오차 0 을 맡는다. 이득 곱셈은 2의 거듭제곱이라 "
      "곱셈기 없이 MUX 로 자리 옮김만 하면 된다 -- 2의 보수라 부호 확장까지 같이 해야 한다.",
      이웃=["All-digital PLL", "Carry lookahead adder", "Loop phase margin"], 트랙=고속링크),
    _("Digitally controlled oscillator", "디지털 제어 발진기 DCO", 박사, M,
      r"f_{DCO}=f_0+K_{DCO}\cdot B_{ctrl},\qquad [K_{DCO}]=\text{Hz/LSB}",
      "VCO 의 제어 전압 자리에 정수 코드가 들어간다. 이득의 단위가 Hz/V 가 아니라 Hz/LSB 이고, "
      "그 LSB 크기가 곧 주파수 양자화 잡음이 된다.",
      이웃=["Voltage controlled oscillator", "All-digital PLL",
          "Digital-to-analog converter"], 트랙=고속링크),
    _("Digital-to-analog converter", "디지털-아날로그 변환기 DAC", 석사, M,
      r"V_{out}=V_{DD}-R_D I_0\sum_k 2^{k}D[k]\quad(\text{binary-weighted current steering})",
      "코드를 전압/전류로 되돌린다. 전류 스티어링은 빠르지만 소자 정합에 기대고, R-2R 은 저항 "
      "두 값만 써서 정합이 쉽다. ADPLL 에서는 내부 버스를 눈으로 보려고 모니터용으로도 쓴다.",
      이웃=["Digitally controlled oscillator", "Current mirror"], 트랙=고속링크),
    _("Carry lookahead adder", "캐리 예측 덧셈기", 학부, D,
      r"G_i=A_iB_i,\ P_i=A_i\!\oplus\!B_i,\quad C_{i+1}=G_i+P_iC_i",
      "리플 캐리는 캐리가 n 단을 줄줄이 지나 지연이 O(n) 이다. 생성(G)과 전파(P)를 미리 뽑아 "
      "캐리를 병렬로 펼치면 O(log n) 이 된다 -- DPLL 루프 필터의 속도를 정하는 것이 이 덧셈기다.",
      이웃=["Digital loop filter", "Static timing analysis"], 트랙=프론트),
    _("Loop phase margin", "루프 위상 여유", 박사, M,
      r"PM=180^\circ+\angle L(j\omega_c),\quad |L(j\omega_c)|=1",
      "열린 루프 이득이 1이 되는 주파수에서 위상이 -180도에서 얼마나 떨어져 있나. 60~70도가 "
      "넘으면 과도응답이 안 출렁인다. 교안 예제(Fref 10MHz, Tresol 1.592ns, KI 1e-3, KP 1e-1, "
      "KDCO 10MHz/LSB, Ndiv 100)에서 73도가 나온다.",
      이웃=["Digital loop filter", "Loop phase margin", "All-digital PLL"], 트랙=고속링크),

    # ------------------------------------------------ 와이어라인 SerDes / PHY
    _("Intersymbol interference", "심볼간 간섭 ISI", 석사, M,
      r"y[n]=p_0 b[n]+\sum_{k\ne 0}p_k b[n-k],\quad \text{eye}=2(|p_0|-\sum_{k\ne0}|p_k|)",
      "채널이 한 심볼의 에너지를 뒤로 끌어 이웃 심볼에 얹는다. 메인 커서 밖의 커서 합이 ISI 이고, "
      "그 합이 메인을 넘으면 잡음이 없어도 눈이 닫힌다(peak distortion).",
      이웃=["Eye diagram", "Decision feedback equalizer", "Channel loss"],
      트랙=고속링크, 링크="isi_closed_eye"),
    _("Channel loss", "채널 손실", 석사, M,
      r"|H(f)|_{dB}\approx-\left(a\sqrt{f}+bf\right)\ell\quad(\text{skin effect}+\text{dielectric})",
      "구리 손실은 표피효과로 sqrt(f) 에, 유전체 손실은 f 에 비례한다. 규격은 보통 Nyquist "
      "주파수에서 몇 dB 인지로 채널을 말한다 -- 그 한 숫자가 등화기 예산을 정한다.",
      이웃=["Intersymbol interference", "Continuous time linear equalizer"],
      트랙=고속링크, 링크="isi_closed_eye"),
    _("Continuous time linear equalizer", "연속시간 선형 등화기 CTLE", 석사, A,
      r"H_{CTLE}(s)=A\frac{1+s/\omega_z}{(1+s/\omega_{p1})(1+s/\omega_{p2})}",
      "영점으로 고주파를 들어 올려 채널 손실을 거꾸로 돌린다. **선형이라 잡음도 같이 든다** -- "
      "실측으로 피킹을 6dB 에서 12dB 로 올리면 BER 이 도리어 나빠진다.",
      이웃=["Channel loss", "Feed-forward equalizer", "Decision feedback equalizer"],
      트랙=고속링크, 링크="ctle_only"),
    _("Feed-forward equalizer", "피드포워드 등화기 FFE", 석사, M,
      r"y[n]=\sum_{k=0}^{L-1}w_k x[n-k],\qquad w=\arg\min E\{|b[n-d]-y[n]|^2\}",
      "선행·후행 커서를 함께 지우는 선형 FIR. LMS 나 MMSE 로 탭을 맞춘다. 선형이므로 잡음을 "
      "증폭하지만 DFE 와 달리 선행 커서도 지울 수 있다.",
      이웃=["Least mean squares adaptation", "Decision feedback equalizer"],
      트랙=고속링크, 링크="ffe_dfe"),
    _("Decision feedback equalizer", "결정 궤환 등화기 DFE", 석사, M,
      r"v[n]=x[n]-\sum_{k=1}^{M}c_k\hat{b}[n-k],\qquad \hat{b}[n]=\mathrm{sgn}(v[n])",
      "이미 내린 판정으로 후행 커서만 빼므로 **잡음을 증폭하지 않는다**. 대신 한 번 틀리면 그 "
      "오류가 뒤로 번진다(error propagation) -- 정답 비트를 되먹이면 그 번짐이 사라져 BER 이 "
      "실제보다 좋게 나온다.",
      이웃=["Feed-forward equalizer", "Error propagation"],
      트랙=고속링크, 링크="dfe_only"),
    _("Error propagation", "오류 번짐", 박사, M,
      r"\Pr\{\text{burst}\}\ \text{grows with}\ \sum_k|c_k|",
      "DFE 가 제 판정을 되먹이므로 한 번의 오판이 다음 심볼들의 되먹임 값을 틀리게 만든다. "
      "시뮬에서 정답을 먹이면 이것이 통째로 사라진다 -- 하드웨어는 정답을 모른다.",
      이웃=["Decision feedback equalizer", "Bit error rate"],
      트랙=고속링크, 링크="ideal_decision_dfe"),
    _("Least mean squares adaptation", "LMS 적응 최소평균제곱", 석사, M,
      r"w[n+1]=w[n]+\mu\,e[n]\,x[n],\qquad 0<\mu<\frac{2}{\lambda_{max}}",
      "오차와 입력의 곱으로 탭을 조금씩 옮긴다. 레이더 적응필터(LMS/RLS)와 수학이 같은 계열이다. "
      "걸음 mu 가 크면 발산하는데, 발산한 탭도 BER 은 그냥 나쁘게 나올 뿐이라 따로 봐야 한다.",
      이웃=["Feed-forward equalizer", "Decision feedback equalizer"],
      트랙=고속링크, 링크="ffe_dfe"),
    _("Bit error rate", "비트 오류율 BER", 석사, M,
      r"\mathrm{BER}=Q\!\left(\frac{A}{\sigma}\right),\qquad Q(x)=\tfrac{1}{2}\mathrm{erfc}\!\left(\tfrac{x}{\sqrt{2}}\right)",
      "링크의 최종 성적. ISI 가 없으면 눈높이 대 잡음비의 Q 함수로 닫힌 꼴이 나오고, 그 닫힌 꼴이 "
      "시뮬레이터를 **교정하는** 잣대다. 재는 것과 맞는지 먼저 확인하지 않은 BER 은 아무 숫자다.",
      이웃=["Rule of three", "Eye diagram"], 트랙=고속링크, 링크="awgn_calibration"),
    _("Rule of three", "3의 규칙", 석사, M,
      r"n\ \text{errors}=0\ \Rightarrow\ \mathrm{BER}<\frac{3}{N}\ (95\%)",
      "N 비트에 오류가 0 이어도 참 BER 은 3/N 까지 갈 수 있다. **오류 0 은 BER 0 이 아니다** -- "
      "1e-12 를 주장하려면 적어도 3e12 비트를 봐야 한다는 뜻이고, 그래서 규격은 BER 바닥을 외삽한다.",
      이웃=["Bit error rate", "Eye diagram"], 트랙=고속링크, 링크="ffe_dfe"),
    _("Clock and data recovery", "클럭·데이터 복원 CDR", 박사, M,
      r"\text{sample at}\ \arg\max_{\phi}\ \text{eye height}(\phi)",
      "받은 데이터에서 클럭을 뽑아 눈 한가운데를 찍는다. 링크에는 기준 클럭이 따로 안 오므로 "
      "CDR 이 없으면 아무리 눈이 열려도 못 읽는다.",
      이웃=["Bang-bang phase detector", "Mueller-Muller CDR", "Phase-locked loop"],
      트랙=고속링크),
    _("Bang-bang phase detector", "뱅뱅 위상검출기", 박사, M,
      r"e[n]=\mathrm{sgn}(x_{edge}[n])\left(\hat b[n]-\hat b[n-1]\right)",
      "가장자리 표본이 앞 비트 쪽인지 뒤 비트 쪽인지 부호만 낸다(Alexander PD). 이득이 비선형이라 "
      "지터 추적 대역이 입력 지터 크기에 따라 달라진다.",
      이웃=["Clock and data recovery", "Clock skew and jitter"], 트랙=고속링크),
    _("Mueller-Muller CDR", "뮐러-뮐러 CDR", 박사, M,
      r"e[n]=\hat b[n-1]y[n]-\hat b[n]y[n-1]\ \to\ 0\ \Rightarrow\ p_{-1}=p_{+1}",
      "가장자리 표본을 따로 뜨지 않고 **데이터 표본만으로** 위상을 맞춘다(baud-rate). 선행 커서와 "
      "후행 커서가 같아지는 자리에 잠기므로 2배 오버샘플이 필요 없어 전력이 준다.",
      이웃=["Clock and data recovery", "Intersymbol interference"], 트랙=고속링크),
    _("Channel operating margin", "채널 동작 여유(COM)", 박사, M,
      r"\mathrm{COM}=20\log_{10}\frac{A_{signal}}{A_{noise}}\ \ge\ 3\,\text{dB}",
      "IEEE 802.3 이 채널 합격을 재는 한 숫자. 규격 송수신기 모형(TX FFE + CTLE + DFE)을 쓴 뒤 "
      "남은 신호 대 잡음 여유를 dB 로 낸다 -- 눈 그림 대신 수치로 통과/불통을 가른다.",
      이웃=["Bit error rate", "Eye diagram", "Channel loss"], 트랙=고속링크),
    _("Quantized equalizer taps", "등화기 탭 양자화", 박사, M,
      r"w_q=\frac{\max|w|}{2^{B-1}-1}\left\lfloor\frac{w(2^{B-1}-1)}{\max|w|}\right\rceil",
      "탭을 몇 비트로 자를 수 있나. 연구 기여가 서는 자리다 -- **오차막대 안의 차이를 '열화 없음' "
      "이라 적으면 안 된다.** 오류 11개와 8개는 차이가 아니라 셈의 흔들림이다.",
      이웃=["Pruned equalizer taps", "Bit error rate", "Rule of three"],
      트랙=고속링크, 링크="quantized_4bit"),
    _("Pruned equalizer taps", "등화기 탭 프루닝", 박사, M,
      r"w_p=w\odot\mathbb{1}\{|w|\ge\tau\},\qquad \|w_p\|_0=\lceil\rho L\rceil",
      "작은 탭을 0 으로 만들어 곱셈기를 없앤다. 양자화와 함께 쓰면 신경망 등화기를 FPGA 에 "
      "올릴 수 있는 크기로 줄인다 -- 줄인 만큼 BER 이 상하는지는 재야 안다.",
      이웃=["Quantized equalizer taps", "Neural network equalizer"],
      트랙=고속링크, 링크="pruned_half"),
    _("Neural network equalizer", "신경망 등화기", 박사, M,
      r"\hat b[n]=\mathrm{sgn}(W_2\,\phi(W_1 x_{n-L:n+L}+b_1)+b_2)",
      "선형 FFE 와 판정 되먹임이 못 잡는 비선형 왜곡(드라이버 압축, 크로스토크)을 비선형 사상으로 "
      "잡는다. 광통신 쪽에서는 이미 양자화·프루닝해 FPGA 에 올린 사례가 있고, 전기 와이어라인 "
      "쪽이 상대적으로 비어 있다 -- 거기가 파고들 틈이다.",
      이웃=["Quantized equalizer taps", "Pruned equalizer taps",
          "Decision feedback equalizer"], 트랙=고속링크),

]


# ---------------------------------------------------------------------------
# 트랙 붙이기. 항목마다 인자를 더 쓰는 대신 **한 표에 모아** 감사할 수 있게 둔다.
# 규칙: 소자물리와 디지털 논리 기초는 공통, 아날로그 회로는 아날로그, RTL·검증은
# 프론트엔드, 물리 구현은 백엔드. 안 적힌 것은 `_기본트랙` 이 갈래로 정한다.
# ---------------------------------------------------------------------------
_트랙표 = {
    공통: ["MOSFET square law", "Triode vs saturation", "Threshold voltage",
          "Body effect", "Overdrive voltage", "Transconductance",
          "Channel-length modulation", "Output resistance", "Short-channel effects",
          "Subthreshold conduction", "Intrinsic capacitances",
          "CMOS inverter VTC", "Noise margins", "Static CMOS logic",
          "Propagation delay", "Logical effort", "Fanout of 4",
          "Transmission gate", "Pass-transistor logic",
          "Karnaugh map / logic minimization", "Boolean / gate basics",
          "RC low-pass / first-order response", "RLC resonance and Q"],
    프론트: ["Latch vs flip-flop", "Setup and hold", "Metastability",
            "CDC and synchronizers", "Dynamic / domino logic", "Adders",
            "Multipliers", "SRAM 6T cell", "SRAM read/write margin",
            "Sense amplifier", "Clock gating"],
    백엔드: ["Clock skew and jitter", "Clock distribution",
            "Static timing analysis", "Place and route", "Interconnect RC delay",
            "Repeater insertion", "Crosstalk", "Power gating", "DVFS",
            "Dynamic power", "Short-circuit power", "Leakage power"],
}
_어디 = {c["이름"]: c for c in 개념}
for _트, _목록 in _트랙표.items():
    for _n in _목록:
        if _n in _어디:
            _어디[_n]["트랙"] = _트
# 남은 것은 갈래로 정한다 -- 아날로그 회로는 아날로그 트랙, 나머지는 공통.
for _c in 개념:
    if not _c["트랙"]:
        _c["트랙"] = 아날로그 if _c["갈래"] in (A, M) else 공통


별칭 = {
    "clm": "Channel-length modulation", "lambda": "Channel-length modulation",
    "vth": "Threshold voltage", "gm": "Transconductance", "ro": "Output resistance",
    "vov": "Overdrive voltage", "cs": "Common source", "cg": "Common gate",
    "cd": "Source follower", "sf": "Source follower",
    "mirror": "Current mirror", "cm": "Current mirror",
    "ota": "Two-stage Miller OTA", "opamp": "Two-stage Miller OTA",
    "op-amp": "Two-stage Miller OTA", "miller": "Miller effect",
    "pm": "Feedback and stability", "phase margin": "Feedback and stability",
    "gbw": "Gain-bandwidth product", "ugb": "Gain-bandwidth product",
    "sr": "Slew rate", "ktc": "kT/C noise", "1/f": "Flicker noise",
    "pelgrom": "Mismatch (Pelgrom)", "mc": "Monte Carlo",
    "sc": "Switched-capacitor circuits", "s/h": "Sample and hold",
    "sar": "SAR ADC", "adc": "SAR ADC", "dac": "DNL / INL",
    "sigma-delta": "Delta-sigma modulator", "enob": "SNDR / ENOB",
    "pll": "PLL basics", "vco": "VCO phase noise",
    "vtc": "CMOS inverter VTC", "inverter": "CMOS inverter VTC",
    "nm": "Noise margins", "le": "Logical effort", "fo4": "Fanout of 4",
    "tg": "Transmission gate", "domino": "Dynamic / domino logic",
    "ff": "Latch vs flip-flop", "setup": "Setup and hold", "hold": "Setup and hold",
    "sta": "Static timing analysis", "cdc": "CDC and synchronizers",
    "pnr": "Place and route", "p&r": "Place and route",
    "sram": "SRAM 6T cell", "snm": "SRAM read/write margin",
    "elmore": "Interconnect RC delay", "kmap": "Karnaugh map / logic minimization",
    "gm/id": "gm/ID methodology", "rc": "RC low-pass / first-order response",
    "rlc": "RLC resonance and Q", "q": "RLC resonance and Q",
}

_토막 = re.compile(r"[^0-9a-z가-힣/]+")


def _고르게(글: str) -> str:
    return _토막.sub(" ", (글 or "").lower()).strip()


def 찾기(질의: str, 최대: int = 6) -> "list[dict]":
    """이름·한글·별칭·설명에서 찾는다. 가장 잘 맞는 것부터."""
    q = _고르게(질의)
    if not q:
        return []
    맞음 = 별칭.get(q) or 별칭.get((질의 or "").strip().lower())
    난것 = []
    for c in 개념:
        점 = 0
        이름q, 한글q = _고르게(c["이름"]), _고르게(c["한글"])
        if 맞음 and c["이름"] == 맞음:
            점 = 100
        elif q == 이름q or q == 한글q:
            점 = 90
        elif q in 이름q.split() or q in 한글q.split():
            점 = 70
        elif q in 이름q or q in 한글q:
            점 = 60
        elif any(t and t in 이름q + " " + 한글q for t in q.split()):
            점 = 40
        elif q in _고르게(c["말"]):
            점 = 20
        if 점:
            난것.append((점, c))
    난것.sort(key=lambda x: -x[0])
    return [c for _, c in 난것[:최대]]


def 목록(층: str = "", 갈래: str = "", 트랙: str = "") -> "list[dict]":
    return [c for c in 개념
            if (not 층 or c["층"] == 층) and (not 갈래 or c["갈래"] == 갈래)
            and (not 트랙 or c["트랙"] == 트랙)]


def 덮임() -> dict:
    """**몇 개가 실제로 돌아가는지 센다.** 설명뿐인 것을 숨기지 않는다."""
    돎 = [c for c in 개념 if c["넷리스트"] or c["회로도"] or c.get("링크")]
    return {"모두": len(개념), "돌려볼수있음": len(돎),
            "설명만": len(개념) - len(돎),
            "층별": {층: len(목록(층)) for 층 in (학부, 석사, 박사)},
            "갈래별": {g: len(목록(갈래=g)) for g in (A, D, DEV, M)},
            "트랙별": {t: len(목록(트랙=t)) for t in 트랙들}}


def 말로(c: dict) -> str:
    """개념 하나를 사람이 읽는 꼴로. 수식은 `$...$` 로 감싼다."""
    줄 = [f"**{c['이름']}** ({c['한글']}) — {c['층']} · {c['갈래']} · {c['트랙']}",
         f"$${c['식']}$$", c["말"]]
    if c["넷리스트"]:
        줄.append(f"run it: `run_spice(\"{c['넷리스트']}\")`")
    if c["회로도"]:
        줄.append(f"draw it: `draw_circuit(example=\"{c['회로도']}\")`")
    if c.get("링크"):
        줄.append(f"measure it: `serdes_link(...)` — example `{c['링크']}`")
    if c["이웃"]:
        줄.append("see also: " + " · ".join(c["이웃"]))
    return "\n".join(줄)
