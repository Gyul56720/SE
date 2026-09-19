// Concrete top level: AES-128 single-block encryption.
#include "hls_compat.h"
#include <ap_int.h>
#include <hls_stream.h>
#include "aes.hpp"

void aes128_top(ap_uint<128> plaintext, ap_uint<128> key, ap_uint<128>& ciphertext) {
#pragma HLS INTERFACE ap_none port=plaintext
#pragma HLS INTERFACE ap_none port=key
#pragma HLS INTERFACE ap_none port=ciphertext
#pragma HLS INTERFACE ap_ctrl_hs port=return
#pragma HLS PIPELINE II=1
    static xf::security::aesEnc<128> cipher;
    cipher.updateKey(key);
    cipher.process(plaintext, key, ciphertext);
}
