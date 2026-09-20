// Concrete top level: FINN matrix-vector-activate, 64x64, SIMD=8, PE=4.
#include "hls_compat.h"
#include "bnn-library.h"
// bnn-library.h pulls in 15 of the 16 FINN headers, including mvau.hpp
// (via convlayer.h) and interpret.hpp (via maxpool.h).  activations.hpp is the
// one it does not reach, and every MVAU instantiation needs an activation type,
// so it must be included explicitly.  Verified with clang -H.
#include "activations.hpp"

#define MW 64
#define MH 64
#define SIMD_ 8
#define PE_ 4
#define WBITS 4
#define ABITS 4

static FixedPointWeights<SIMD_, ap_int<WBITS>, PE_, (MW/SIMD_)*(MH/PE_)> weights;
static ThresholdsActivation<(MH/PE_), PE_, 1, ap_int<16>, ap_uint<1> > thresh;

void mvau_top(hls::stream<ap_uint<SIMD_*ABITS> >& in,
              hls::stream<ap_uint<PE_*1> >& out) {
#pragma HLS INTERFACE axis port=in
#pragma HLS INTERFACE axis port=out
#pragma HLS INTERFACE ap_ctrl_hs port=return
#pragma HLS DATAFLOW
    Matrix_Vector_Activate_Batch<MW, MH, SIMD_, PE_, 1,
        Slice<ap_int<ABITS> >, Slice<ap_uint<1> >, Identity>
        (in, out, weights, thresh, 1, ap_resource_lut());
}
