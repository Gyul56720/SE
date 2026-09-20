// Concrete top level for Vitis HLS synthesis: complex 8x8 Cholesky, ap_fixed.
#include "hls_compat.h"
#include <ap_fixed.h>
#include <hls_x_complex.h>
#include <hls_stream.h>
#include "cholesky.hpp"

typedef hls::x_complex<ap_fixed<24,8> > in_t;
typedef hls::x_complex<ap_fixed<24,8> > out_t;
const int N = 8;

struct myTraits : xf::solver::choleskyTraits<true, N, in_t, out_t> {
    static const int ARCH          = 2;   // lowest-latency architecture
    static const int INNER_II      = 1;
    static const int UNROLL_FACTOR = 2;
};

int cholesky_top(hls::stream<in_t>& A, hls::stream<out_t>& L) {
#pragma HLS INTERFACE axis port=A
#pragma HLS INTERFACE axis port=L
#pragma HLS INTERFACE ap_ctrl_hs port=return
    return xf::solver::cholesky<true, N, in_t, out_t, myTraits>(A, L);
}
