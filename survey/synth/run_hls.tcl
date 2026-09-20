# Vitis HLS synthesis script for the surveyed cores.
#   vitis_hls -f run_hls.tcl
# Produces csynth reports under <proj>/sol/syn/report/.
set PART   xcvu9p-flga2104-2L-e   ;# change to your device
set PERIOD 4.0                    ;# ns  (250 MHz)
set VEND   [file normalize ../vendor]

proc build {name src top incs} {
  global PART PERIOD VEND
  open_project -reset $name
  set_top $top
  set flags "-std=c++14 -I$VEND -I$VEND/etc"
  foreach i $incs { append flags " -I[file normalize $i]" }
  add_files $src -cflags $flags
  open_solution -reset "sol" -flow_target vivado
  set_part $PART
  create_clock -period $PERIOD -name default
  csynth_design
  # export_design -format ip_catalog     ;# uncomment to package as IP
  close_project
}

build cholesky_prj top_cholesky.cpp cholesky_top {../Vitis_solver ..}
build aes_prj      top_aes.cpp      aes128_top   {../Vitis_security ..}
build mvau_prj     top_mvau.cpp     mvau_top     {../finn_hlslib}
exit
