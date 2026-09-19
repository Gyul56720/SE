# Synthesis harness for the surveyed cores

These are **concrete top levels**: the corpus files are templates and cannot be
synthesised as they stand.  Each wrapper instantiates one core with real
parameters and adds interface pragmas.

    top_cholesky.cpp   complex 8x8 Cholesky, ap_fixed<24,8>, ARCH=2, UNROLL_FACTOR=2
    top_aes.cpp        AES-128 single block, II=1
    top_mvau.cpp       FINN MVAU 64x64, SIMD=8, PE=4, 4-bit weights, 1-bit output

## Verified here

All three compile cleanly with `clang++ -std=c++14` against the public Xilinx
headers in `../vendor`, which proves the template instantiations are correct.

    clang++ -std=c++14 -w -fsyntax-only -I ../vendor -I ../vendor/etc \
            -I ../Vitis_solver -I .. top_cholesky.cpp      # OK
    clang++ ... -I ../Vitis_security -I .. top_aes.cpp     # OK
    clang++ ... -I ../finn_hlslib      top_mvau.cpp        # OK

## Not verified here -- and why

**No synthesis was run.**  A C-to-RTL compiler that accepts this dialect could
not be obtained in this environment.  Five channels were checked:

    apt                 no such package
    GitHub releases     403 through the proxy (Bambu/PandA binaries)
    PyPI                only wrappers that require Vitis HLS (tapa) or
                        orchestrators that fetch tools at run time (siliconcompiler)
    conda-forge         verilator and yosys, but no HLS compiler
    upstream host       release.bambuhls.eu unreachable

So the numbers a synthesis run would give -- latency, initiation interval,
LUT/FF/DSP/BRAM -- are **not in this repository and are not claimed anywhere**.

## To get them

Install Vitis HLS (the free edition is enough for these parts), then:

    vitis_hls -f run_hls.tcl

Reports land in `*_prj/sol/syn/report/*_csynth.rpt`.  Change `PART` and
`PERIOD` at the top of the script for your device and target frequency.

Sweeping is the interesting part: edit `ARCH` and `UNROLL_FACTOR` in
`top_cholesky.cpp`, or `SIMD`/`PE` in `top_mvau.cpp`, re-run, and compare the
reports.  That sweep is exactly what Section VI-E of the survey describes and
could not measure.

## One thing this harness uncovered

`bnn-library.h` is FINN's aggregate header, but it does not reach every file.
Dumping the include tree with `clang -H` shows 15 of the 16 headers arrive,
several of them only indirectly:

    bnn-library.h
    |- weights.hpp  mmv.hpp  streamtools.h  dma.h
    |- slidingwindow.h -> utils.hpp
    |- maxpool.h       -> interpret.hpp
    |- convlayer.h     -> mvau.hpp -> mac.hpp
    |                  -> tmrcheck.hpp
    `- vvau.hpp  upsample.hpp

The one it never reaches is **`activations.hpp`**.  Since every MVAU and VVAU
instantiation needs an activation type, any top level that uses them must
include it explicitly.  That is the single extra line in `top_mvau.cpp`.

An earlier note in this file claimed `mvau.hpp` and `interpret.hpp` were also
missing.  That was wrong; both arrive transitively.  The claim was made from
reading the direct `#include` list rather than from the preprocessor.
