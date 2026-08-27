import numpy as np

def process(signal: np.ndarray) -> np.ndarray:
    if len(signal) == 0:
        return signal
    window_size = min(5, len(signal))
    kernel = np.ones(window_size) / window_size
    return np.convolve(signal, kernel, mode='same')
