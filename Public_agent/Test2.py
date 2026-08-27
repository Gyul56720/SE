import numpy as np
from scipy.signal.windows import chebwin

class AdvancedFMCWProcessor:
    def __init__(self, raw_beat_signal: np.ndarray):
        self.signal = raw_beat_signal
        self.range_doppler_map = None

    def apply_moisture_phase_correction(self, moisture_coefficient: float):
        num_chirps, num_rx, samples = self.signal.shape
        t = np.arange(samples).reshape(1, 1, samples)
        phase_shift = moisture_coefficient * (t ** 2)
        self.signal = self.signal * np.exp(1j * phase_shift)

    def generate_range_doppler(self, attenuation_db: float = 40.0):
        num_chirps, num_rx, samples = self.signal.shape
        
        range_win = chebwin(samples, at=attenuation_db)
        doppler_win = chebwin(num_chirps, at=attenuation_db)
        
        windowed = self.signal * range_win[np.newaxis, np.newaxis, :]
        range_fft = np.fft.fft(windowed, axis=-1)
        
        windowed_rd = range_fft * doppler_win[:, np.newaxis, np.newaxis]
        rd_map = np.fft.fft(windowed_rd, axis=0)
        
        self.range_doppler_map = np.fft.fftshift(rd_map, axes=(0,))
        return self.range_doppler_map
