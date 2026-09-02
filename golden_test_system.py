import numpy as np

# Specification Constraints
INT8_MIN, INT8_MAX = -128, 127
ACC_BITS = 21

def ternary_mac_golden(x, w):
    """
    Mathematical reference model.
    """
    x = np.asarray(x, dtype=np.int64)
    w = np.asarray(w, dtype=np.int64)

    assert x.shape == w.shape
    assert np.all((x >= INT8_MIN) & (x <= INT8_MAX))
    assert np.all(np.isin(w, [-1, 0, 1]))

    return int(np.sum(x * w))

def run_random_tests(num_tests=10000, N=4096):
    rng = np.random.default_rng(42)
    print(f"Starting Random Regression: {num_tests} tests, N={N}")

    for test_id in range(num_tests):
        x = rng.integers(INT8_MIN, INT8_MAX + 1, size=N, dtype=np.int16)
        w = rng.choice([-1, 0, 1], size=N).astype(np.int8)

        expected = ternary_mac_golden(x, w)

        # 21-bit Accumulator Contract check
        # Min: -2^20 = -1,048,576
        # Max: 2^20 - 1 = 1,048,575
        ACC_MIN = -(1 << (ACC_BITS - 1))
        ACC_MAX = (1 << (ACC_BITS - 1)) - 1
        
        # Verify Golden Model is within RTL contract range
        assert ACC_MIN <= expected <= ACC_MAX, f"Golden Model overflowed at test {test_id}: {expected}"
        
        # Here we will eventually compare actual RTL output
        # actual = run_rtl(x, w)
        # assert actual == expected

    print(f"Random Regression Passed: {num_tests} tests verified against mathematical contract.")

if __name__ == "__main__":
    run_random_tests()
