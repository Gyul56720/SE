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
A, D, DEV, M = "analog", "digital", "device", "mixed"


def _(이름, 한글, 층, 갈래, 식, 말, 넷="", 그림="", 이웃=()):
    return {"이름": 이름, "한글": 한글, "층": 층, "갈래": 갈래, "식": 식, "말": 말,
            "넷리스트": 넷, "회로도": 그림, "이웃": list(이웃)}


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
      이웃=["Threshold voltage", "Source follower"]),
    _("Overdrive voltage", "과구동전압 Vov", 학부, DEV,
      r"V_{OV}=V_{GS}-V_{th}=\sqrt{\tfrac{2I_D}{K'(W/L)}}",
      "설계의 손잡이. 작게 잡으면 gm/ID 가 커지고(이득·저전력), 크게 잡으면 빠르고 정합이 좋아진다.",
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
      "common_source", "공통소스", ["Miller effect", "Cascode"]),
    _("Common gate", "공통게이트", 학부, A,
      r"R_{in}=\tfrac{1}{g_m+g_{mb}},\quad A_v=+g_m R_D",
      "입력 임피던스가 낮다. 전류를 받아 전압으로 바꾸는 자리(캐스코드의 윗단)에 쓴다.",
      이웃=["Cascode", "Source follower"]),
    _("Source follower", "소스팔로워·공통드레인", 학부, A,
      r"A_v=\tfrac{g_m}{g_m+g_{mb}+1/r_o}<1,\quad R_{out}\approx\tfrac{1}{g_m}",
      "이득 1 미만의 버퍼. 출력저항이 낮아 무거운 부하를 몬다. 몸효과가 이득을 깎는다.",
      이웃=["Body effect", "Common gate"]),
    _("Cascode", "캐스코드", 학부, A,
      r"R_{out}\approx g_{m2}r_{o2}r_{o1},\quad A_v\approx-g_{m1}(g_{m2}r_{o2}r_{o1})",
      "출력저항을 gm·ro 배로 올린다. 이득이 커지고 Miller 가 줄지만 출력 스윙을 잃는다.",
      이웃=["Output resistance", "Telescopic OTA", "Miller effect"]),
    _("Miller effect", "밀러 효과", 학부, A,
      r"C_{in}=C_{gd}(1+|A_v|),\quad \omega_{p1}\approx\tfrac{1}{R_S C_{gd}(1+|A_v|)}",
      "되먹임 용량이 이득 배로 커져 보인다. 공통소스의 대역을 실제로 정하는 것이 이것이다.",
      이웃=["Cascode", "Pole splitting"]),

    # ------------------------------------------------------------ 전류·바이어스
    _("Current mirror", "전류미러", 학부, A,
      r"\tfrac{I_{OUT}}{I_{REF}}=\tfrac{(W/L)_2}{(W/L)_1}(1+\lambda V_{DS2})",
      "전류를 베낀다. 베끼기의 정확도는 두 Vth 의 정합과 Vds 차이(λ)가 정한다.",
      "current_mirror", "전류미러", ["Cascode current mirror", "Mismatch (Pelgrom)"]),
    _("Cascode current mirror", "캐스코드 전류미러", 학부, A,
      r"R_{out}\approx g_m r_o^2,\quad V_{out,min}=V_{OV1}+V_{OV2}",
      "출력저항을 ro² 로 올려 λ 오차를 지운다. 대가는 출력 스윙 한 Vov.",
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
      "diff_pair", 이웃=["CMRR", "Tail current source"]),
    _("CMRR", "공통모드 제거비", 학부, A,
      r"CMRR=\tfrac{A_d}{A_{cm}}\approx 2g_{m1}r_{o,tail}\cdot\text{(matching)}",
      "꼬리 전류원의 출력저항과 부하 정합이 정한다. 정합이 완벽하면 무한대다.",
      이웃=["Differential pair", "Mismatch (Pelgrom)"]),
    _("Tail current source", "꼬리 전류원", 학부, A,
      r"A_{cm}\approx-\tfrac{R_D}{2r_{o,tail}}",
      "차동쌍이 공통모드를 얼마나 무시하는지를 이것 하나가 정한다.",
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
      이웃=["Pole splitting", "Feedback and stability"]),
    _("Pole splitting", "극점 분리", 석사, A,
      r"\omega_{p1}\approx\tfrac{1}{g_{m2}r_{o2}r_{o1}C_C},\quad \omega_{p2}\approx\tfrac{g_{m2}}{C_L}",
      "밀러 보상이 첫 극점을 내리고 둘째를 올린다. 그래서 하나만 남은 것처럼 보인다.",
      이웃=["Two-stage Miller OTA", "RHP zero"]),
    _("RHP zero", "우반면 영점", 석사, A,
      r"z=+\tfrac{g_{m2}}{C_C}\ \Rightarrow\ \text{nulling }R_z=\tfrac{1}{g_{m2}}",
      "Cc 를 앞으로 지나는 신호가 만드는 영점. 이득은 올리고 위상은 깎아 안정도를 망친다.",
      이웃=["Pole splitting", "Feedback and stability"]),
    _("CMFB", "공통모드 되먹임", 석사, A,
      r"V_{cm,out}\to V_{cm,ref}\ \text{via } T_{cm}(s),\quad PM_{cm}>60^\circ",
      "완전차동 회로에서 출력 공통모드는 스스로 안 정해진다. 따로 되먹임을 걸어야 한다.",
      이웃=["Folded cascode OTA", "Feedback and stability"]),
    _("Feedback and stability", "되먹임과 안정도", 학부, A,
      r"A_{cl}=\tfrac{A}{1+\beta A},\quad PM=180^\circ+\angle\beta A|_{|\beta A|=1}",
      "루프이득이 모든 것을 정한다 -- 정확도도, 대역도, 울림도. PM 60° 가 관례다.",
      이웃=["Pole splitting", "Gain-bandwidth product"]),
    _("Gain-bandwidth product", "이득대역폭곱", 학부, A,
      r"GBW=A_0\omega_{p1}=\tfrac{g_m}{C_C}",
      "한 극점 계에서는 이득과 대역의 곱이 상수다. 이득을 낮추면 그만큼 빨라진다.",
      "common_source", 이웃=["Feedback and stability"]),
    _("Slew rate", "슬루율", 석사, A,
      r"SR=\tfrac{I_{SS}}{C_C},\quad t_{settle}\approx\tfrac{\Delta V}{SR}+\tfrac{\ln(1/\epsilon)}{\omega_u}",
      "큰 신호 한계. 작은신호 대역이 아무리 넓어도 여기 걸리면 못 따라간다.",
      이웃=["Two-stage Miller OTA", "Settling time"]),
    _("Settling time", "정착 시간", 석사, A,
      r"t_s=\tfrac{1}{\omega_u}\ln\tfrac{1}{\epsilon}\ (\text{linear}),\quad \epsilon=2^{-(N+1)}\ \text{for }N\text{-bit}",
      "ADC 앞단의 진짜 사양. N비트를 맞추려면 N+1 비트만큼 정착해야 한다.",
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
      "cmos_inverter_vtc", "CMOS인버터", ["Noise margins", "Propagation delay"]),
    _("Noise margins", "잡음 여유", 학부, D,
      r"NM_H=V_{OH}-V_{IH},\quad NM_L=V_{IL}-V_{OL}",
      "이득이 -1 이 되는 두 점이 VIL·VIH 다. 여유가 0 이면 논리가 무너진다.",
      "cmos_inverter_vtc", 이웃=["CMOS inverter VTC"]),
    _("Static CMOS logic", "정적 CMOS 논리", 학부, D,
      r"\text{PUN}=\overline{\text{PDN}}\ (\text{dual}),\quad \text{NAND2: }(W/L)_n=2(W/L)_{inv}",
      "직렬로 쌓인 만큼 넓혀야 같은 세기가 된다. 쌓기(stacking)가 지연을 정한다.",
      그림="CMOS낸드", 이웃=["Logical effort", "Transmission gate"]),
    _("Propagation delay", "전파 지연", 학부, D,
      r"t_{p}=0.69R_{eq}C_L,\quad R_{eq}\approx\tfrac{3}{4}\tfrac{V_{DD}}{I_{DSAT}}\left(1-\tfrac{7}{9}\lambda V_{DD}\right)",
      "RC 로 본다. 부하가 늘면 선형으로 는다 -- 그것이 fan-out 곡선이다.",
      이웃=["Logical effort", "Interconnect RC delay"]),
    _("Logical effort", "논리 노력", 학부, D,
      r"d=gh+p,\quad \hat{f}=\sqrt[N]{F},\quad N_{opt}=\ln F/\ln 4",
      "게이트 사슬을 손으로 최적화하는 법. 단마다 같은 노력을 지는 것이 최소 지연이다.",
      이웃=["Propagation delay", "Fanout of 4"]),
    _("Fanout of 4", "FO4", 학부, D,
      r"t_{FO4}\approx 5\tau_{inv},\quad \text{process-independent yardstick}",
      "공정이 달라도 FO4 로 재면 비교가 된다. 파이프라인 단 길이의 잣대.",
      이웃=["Logical effort"]),
    _("Transmission gate", "전송 게이트", 학부, D,
      r"R_{eq}=\tfrac{1}{\tfrac{1}{R_n}+\tfrac{1}{R_p}}\approx\text{const over }V_{in}",
      "NMOS 와 PMOS 를 병렬로 붙여 전 구간에서 통한다. 멀티플렉서와 래치의 재료.",
      이웃=["Pass-transistor logic", "Latch vs flip-flop"]),
    _("Pass-transistor logic", "통과 트랜지스터 논리", 학부, D,
      r"V_{out,max}=V_{DD}-V_{th}\ (\text{NMOS only})",
      "적은 소자로 만들지만 문턱 강하로 전압이 깎이고 정적 전류가 흐른다.",
      이웃=["Transmission gate"]),
    _("Dynamic / domino logic", "동적·도미노 논리", 석사, D,
      r"\text{precharge}\to\text{evaluate},\quad \Delta V=\tfrac{C_X}{C_X+C_L}V_{DD}\ (\text{charge sharing})",
      "빠르고 작지만 전하 공유·누설·잡음에 약하다. 도미노는 단끼리 잇기 위한 반전기.",
      이웃=["Leakage power", "Static CMOS logic"]),

    # ------------------------------------------------------------ 순차·타이밍
    _("Latch vs flip-flop", "래치와 플립플롭", 학부, D,
      r"\text{latch: level-sensitive},\quad \text{FF}=\text{master}+\text{slave}",
      "래치는 투명하고 플립플롭은 순간이다. 시간 빌림(time borrowing)이 래치의 장점.",
      그림="셋업홀드", 이웃=["Setup and hold", "Metastability"]),
    _("Setup and hold", "셋업·홀드", 학부, D,
      r"T\ge t_{cq}+t_{logic,max}+t_{su}+t_{skew},\quad t_{cq}+t_{logic,min}\ge t_{h}+t_{skew}",
      "타이밍의 두 부등식. 셋업은 주파수를 낮추면 풀리고 **홀드는 안 풀린다**.",
      그림="셋업홀드", 이웃=["Clock skew and jitter", "Static timing analysis"]),
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
      이웃=["Short-circuit power", "DVFS"]),
    _("Short-circuit power", "단락 전력", 학부, D,
      r"P_{sc}=\tfrac{\beta}{12}(V_{DD}-2V_{th})^3\tfrac{\tau}{T}",
      "입력이 느리면 NMOS·PMOS 가 같이 켜진 채로 있다. 입력 기울기를 세우면 준다.",
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
      이웃=["SRAM read/write margin", "Sense amplifier"]),
    _("SRAM read/write margin", "SRAM 읽기·쓰기 마진", 박사, D,
      r"SNM=\max\{a:\ a\times a\ \text{square fits in the butterfly lobe}\}",
      "읽는 동안 셀이 뒤집히지 않을 여유. 전압을 내리면 제일 먼저 무너지는 것.",
      이웃=["SRAM 6T cell", "Mismatch (Pelgrom)"]),
    _("Sense amplifier", "감지 증폭기", 석사, D,
      r"\Delta V_{BL}=\tfrac{I_{cell}t}{C_{BL}},\quad t_{sense}\propto\tfrac{C}{g_m}\ln\tfrac{V_{DD}}{\Delta V_{BL}}",
      "비트라인을 다 흔들지 않고 작은 차이만 읽어 시간과 전력을 아낀다.",
      이웃=["SRAM 6T cell", "Comparator"]),
    _("Interconnect RC delay", "배선 RC 지연", 석사, D,
      r"t_{Elmore}=\sum_i R_i C_{i\to n},\quad t_{wire}\propto \tfrac{rc\,L^2}{2}",
      "길이의 제곱으로 는다. 그래서 중계기를 넣어 선형으로 되돌린다.",
      이웃=["Repeater insertion", "Place and route"]),
    _("Repeater insertion", "중계기 삽입", 박사, D,
      r"k_{opt}=L\sqrt{\tfrac{rc}{2R_0C_0}},\quad t\propto L\ (\text{after})",
      "L² 를 L 로 바꾼다. 대가는 전력과 면적.",
      이웃=["Interconnect RC delay"]),
    _("Crosstalk", "누화", 박사, D,
      r"\Delta V=\tfrac{C_c}{C_c+C_L}V_{DD},\quad \text{Miller factor }0\text{-}2\ \text{on delay}",
      "옆 선이 같이 움직이면 지연이 최대 두 배까지 흔들린다. 실드와 순서 섞기로 막는다.",
      이웃=["Interconnect RC delay"]),
    _("Karnaugh map / logic minimization", "카르노맵·논리 최소화", 학부, D,
      r"\text{prime implicants}\to\text{minimal cover}",
      "손으로 하는 논리 최소화. 지금은 합성기가 하지만 왜 그렇게 되는지는 여기서 배운다.",
      그림="카르노맵", 이웃=["Static CMOS logic"]),
    _("Boolean / gate basics", "논리 게이트 기초", 학부, D,
      r"\overline{A\cdot B}=\overline{A}+\overline{B}\ (\text{De Morgan})",
      "드모간이 PUN/PDN 쌍대성의 뿌리다.",
      그림="논리게이트", 이웃=["Static CMOS logic", "Karnaugh map / logic minimization"]),

    # --------------------------------------------------------------- 방법론
    _("gm/ID methodology", "gm/ID 설계법", 박사, A,
      r"\tfrac{g_m}{I_D}=\tfrac{2}{V_{OV}}\ (\text{strong}),\ \tfrac{1}{nV_T}\ (\text{weak}),\quad f_T\propto V_{OV}",
      "Vov 하나로 이득·속도·전력을 한 장에 놓고 고른다. 제곱법칙이 안 맞는 공정에서도 통한다.",
      이웃=["Overdrive voltage", "Transconductance"]),
    _("RC low-pass / first-order response", "RC 저역통과", 학부, A,
      r"f_{-3dB}=\tfrac{1}{2\pi RC},\quad v(t)=V(1-e^{-t/RC})",
      "모든 대역 이야기의 밑동. 시상수 하나가 주파수와 시간 양쪽을 정한다.",
      "rc_lowpass", "RC저역", ["Gain-bandwidth product"]),
    _("RLC resonance and Q", "RLC 공진과 Q", 학부, A,
      r"f_0=\tfrac{1}{2\pi\sqrt{LC}},\quad Q=\tfrac{1}{R}\sqrt{\tfrac{L}{C}}",
      "선택도. LC 발진기와 매칭망의 밑동이고, Q 가 위상잡음을 정한다.",
      "rlc_resonance", 이웃=["VCO phase noise"]),
]


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


def 목록(층: str = "", 갈래: str = "") -> "list[dict]":
    return [c for c in 개념
            if (not 층 or c["층"] == 층) and (not 갈래 or c["갈래"] == 갈래)]


def 덮임() -> dict:
    """**몇 개가 실제로 돌아가는지 센다.** 설명뿐인 것을 숨기지 않는다."""
    돎 = [c for c in 개념 if c["넷리스트"] or c["회로도"]]
    return {"모두": len(개념), "돌려볼수있음": len(돎),
            "설명만": len(개념) - len(돎),
            "층별": {층: len(목록(층)) for 층 in (학부, 석사, 박사)},
            "갈래별": {g: len(목록(갈래=g)) for g in (A, D, DEV, M)}}


def 말로(c: dict) -> str:
    """개념 하나를 사람이 읽는 꼴로. 수식은 `$...$` 로 감싼다."""
    줄 = [f"**{c['이름']}** ({c['한글']}) — {c['층']} · {c['갈래']}",
         f"$${c['식']}$$", c["말"]]
    if c["넷리스트"]:
        줄.append(f"run it: `run_spice(\"{c['넷리스트']}\")`")
    if c["회로도"]:
        줄.append(f"draw it: `draw_circuit(example=\"{c['회로도']}\")`")
    if c["이웃"]:
        줄.append("see also: " + " · ".join(c["이웃"]))
    return "\n".join(줄)
