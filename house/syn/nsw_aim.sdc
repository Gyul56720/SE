# =====================================================================
#  nsw_aim.sdc -- Nowon Silicon Works / Synthesis & PI
#  Owner : Marcus Webb
#
#  AIM2 (KpqC AIMer v2.0) 의 역 Mersenne S-box, GF(2^128).
#  클럭 하나짜리 단순한 회로다 -- 비동기 도메인이 없으므로 clock_groups 도 없다.
#
#  **주기 20 ns 를 고른 까닭**: 이 회로의 임계경로는 GF(2^128) 무캐리 곱
#  하나(교과서 꼴, AND 16384 + XOR 트리)이고, 가수 모드에서는 그 앞에
#  Frobenius 배럴 7 단이 더 붙는다. 둘 다 조합회로 한 판이라 느리다.
#  **이 수는 재 보기 전의 출발점이지 사인오프 목표가 아니다** -- STA 가 낸 값을
#  보고 다시 정한다. (카라추바 곱과 파이프라인이 다음 걸음이다.)
# =====================================================================

# ---------------------------------------------------------------- 클럭
create_clock -name clk -period 20.0 -waveform {0 10} [get_ports clk]

# 클럭 트리가 아직 없다 -- CTS 전이므로 불확실성으로 대신한다.
set_clock_uncertainty -setup 0.15 [get_clocks clk]
set_clock_uncertainty -hold  0.05 [get_clocks clk]
set_clock_transition 0.10 [get_clocks clk]

# ---------------------------------------------------------------- 입출력
# x 는 128 비트가 한꺼번에 들어온다. 앞단이 무엇인지 아직 모르므로 주기의 40% 를 준다.
set_input_delay  -clock clk 8.0 [remove_from_collection [all_inputs] [get_ports clk]]
set_output_delay -clock clk 4.0 [all_outputs]

# rst_n 은 비동기 리셋이다. 해제만 동기화되면 되므로 타이밍에서 뺀다.
set_false_path -from [get_ports rst_n]

# ---------------------------------------------------------------- 구동/부하
set_driving_cell -lib_cell BUFX2 [remove_from_collection [all_inputs] [get_ports clk]]
set_load 0.05 [all_outputs]

# ---------------------------------------------------------------- 최대 천이
set_max_transition 0.60 [current_design]
set_max_fanout 16 [current_design]
