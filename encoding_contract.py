def encode_weight(w):
    """
    Physical Hardware Encoding:
    00 ->  0
    01 -> +1
    10 -> -1
    11 -> RESERVED
    """
    if w == 0:
        return 0b00
    elif w == 1:
        return 0b01
    elif w == -1:
        return 0b10
    raise ValueError(f"Illegal ternary weight: {w}")

def decode_weight(code):
    """
    Physical Decoding:
    00 ->  0
    01 -> +1
    10 -> -1
    """
    if code == 0b00:
        return 0
    elif code == 0b01:
        return 1
    elif code == 0b10:
        return -1
    raise ValueError(f"Illegal weight code: {code}")

def verify_encoding():
    for w in [-1, 0, 1]:
        encoded = encode_weight(w)
        decoded = decode_weight(encoded)
        assert decoded == w, f"Encoding Contract Violation: {w} -> {encoded} -> {decoded}"
    print("Encoding Contract Verified: PASS")

if __name__ == "__main__":
    verify_encoding()
