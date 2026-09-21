# =====================================================================
#  nsw_fir.sdc -- Nowon Silicon Works / Synthesis & PI
#  Owner : Marcus Webb
#
#  **이 파일은 흐름에서 도구가 못 만드는 유일한 파일이다.**  넷리스트는 합성이,
#  기생은 추출이, 배치는 배치기가 만든다.  '타이밍을 맞춘다' 가 무슨 뜻인지를
#  정하는 것은 사람이고, 그것이 여기 적혀 있다.
#
#  house/syn/sdc.py 가 이 파일을 실제로 파싱해서 STA 에 건다.
# =====================================================================

# ---------------------------------------------------------------- 클럭
create_clock -name clk     -period 13.0 -waveform {0 6.5} [get_ports clk]
create_clock -name cfg_clk -period 40.0 -waveform {0 20}  [get_ports cfg_clk]

# 두 클럭은 서로 비동기다.  이 한 줄이 없으면 STA 가 도메인 사이 경로를
# 단일 주기로 잡아 **닫히지 않는 가짜 위반 수천 개**를 낸다.
set_clock_groups -asynchronous -group {clk} -group {cfg_clk}

# 클럭 트리가 아직 없다 -- CTS 전이므로 불확실성으로 대신한다.
set_clock_uncertainty -setup 0.25 [get_clocks clk]
set_clock_uncertainty -hold  0.08 [get_clocks clk]
set_clock_latency -source 0.8 [get_clocks clk]
set_clock_transition 0.15 [get_clocks clk]

# ---------------------------------------------------------------- 입출력
set_input_delay  -clock clk 3.5 [get_ports {in_vld in_data* start ack len*}]
set_output_delay -clock clk 3.0 [get_ports {out_acc* out_vld busy done state_o*}]
set_input_delay  -clock cfg_clk 12.0 [get_ports {cfg_we cfg_coef* cfg_soft_rst}]
set_output_delay -clock cfg_clk 10.0 [get_ports {cfg_full}]
set_driving_cell -lib_cell INVX4 [all_inputs]
set_load 0.020 [all_outputs]

# ---------------------------------------------------------------- 예외
# 스캔 인에이블은 기능 모드에서 안 바뀐다.
set_false_path -from [get_ports scan_en]

# **리셋은 거짓 경로가 아니다.**  걸릴 때는 비동기이지만 풀릴 때는 동기다 --
# 통째로 false_path 를 걸면 리커버리 검사가 사라진다(T17 의 사고 기록).
# 그래서 걸리는 쪽만 예외로 두고 풀리는 쪽은 검사한다.
set_false_path -fall_from [get_ports rst_n]

# 설정 도메인의 계수는 FIFO 가 동기화한다 -- 포인터 건넘만 예외로 둔다.
set_max_delay 40.0 -from [get_clocks cfg_clk] -to [get_clocks clk]
set_max_delay 13.0 -from [get_clocks clk] -to [get_clocks cfg_clk]

# ---------------------------------------------------------------- 코너 디레이트
# OCV: 발사 경로는 늦게, 포획 경로는 이르게.  공통 경로 비관은 CPPR 이 돌려준다.
set_timing_derate -early 0.93
set_timing_derate -late  1.07

# ---------------------------------------------------------------- 면적/전력
set_max_area 0
set_max_transition 0.40
set_max_fanout 24
