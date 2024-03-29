import pygame
import numpy as np
from scipy.interpolate import interp1d

# Considerations
    # Calculate a bounding rect every frame for local screen updates
    # Figure out how to make a hybrid scale
    # Lookup tables?

class FreqSpikes:
    DECAY_FACTOR = 0.5
    LOG_BIN_SCALING_FACTOR = 1.1
    MAX_TARGET_HEIGHT = 540

    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.update_settings()
        self.initialize_parameters()

    def initialize_parameters(self):
        self.heights = np.zeros(self.n_bins, dtype=float)
        self.velocities = np.zeros(self.n_bins, dtype=float)
        self.mirror_surf = pygame.Surface((self.screen_w, self.half_screen_h))

    def update_settings(self):
        self.sensitivity = self.visualizer.settings["volume_sensitivity"]
        self.mirror_x = self.visualizer.settings["freq_spikes"]["mirror_x"]
        self.mirror_y = self.visualizer.settings["freq_spikes"]["mirror_y"]
        self.invert_x = self.visualizer.settings["freq_spikes"]["invert_x_mirror"]
        self.invert_y = self.visualizer.settings["freq_spikes"]["invert_y_mirror"]
        self.n_bins = self.visualizer.settings["freq_spikes"]["bins"]
        self.color = self.visualizer.color
        self.screen_w, self.screen_h = self.visualizer.SCREEN_WIDTH, self.visualizer.SCREEN_HEIGHT
        self.half_screen_h = self.screen_h // 2
        self.half_n_bins = self.n_bins // 2
        self.bin_width = self.screen_w / self.n_bins
        remaining_space = self.screen_w - (self.bin_width * self.n_bins)        
        self.bin_width += remaining_space / self.n_bins  # Distribute remaining space

    def scale_bins(self, raw_amplitudes):
        n = len(raw_amplitudes)
        freqs_linear = np.fft.fftfreq(n)[:n//2]
        
        cutoff_frequency = 220
        normalized_cutoff = cutoff_frequency / self.visualizer.RATE
        cutoff_index = np.argmin(np.abs(freqs_linear - normalized_cutoff))
        
        lower_freqs = freqs_linear[:cutoff_index]
        upper_freqs = freqs_linear[cutoff_index:]

        # Apply linear scaling to frequencies below the cutoff
        scaled_lower_freqs = lower_freqs ** 1.3

        # Make sure the two parts add up to n_bins
        n_lower_bins = cutoff_index
        n_upper_bins = self.n_bins - n_lower_bins

        # Apply custom exponent to upper frequencies
        scaled_upper_freqs = upper_freqs ** 1.5

        # Make sure there's no gap between the scales
        first_log_freq = scaled_lower_freqs[-1]

        # Adjust the scaled_upper_freqs to avoid gap
        scaled_upper_freqs = scaled_upper_freqs * (first_log_freq / scaled_upper_freqs[0])

        # Combine the two scales
        blended_freqs = np.concatenate([scaled_lower_freqs, scaled_upper_freqs])

        # Interpolate to the blended scale
        interpolate_func = interp1d(freqs_linear, raw_amplitudes[:n//2], kind='linear', fill_value='extrapolate')
        return blended_freqs, interpolate_func(blended_freqs)

    def calculate_heights(self, log_freqs, log_amplitudes):
        boost_factor = np.exp(-log_freqs / max(log_freqs))
        dampen_factor = 1 - np.exp(-log_freqs / (max(log_freqs) / 200))
        adjusted_amplitudes = np.abs(log_amplitudes * boost_factor * dampen_factor)
        amplitudes = np.multiply(adjusted_amplitudes, 5) ** 1.3
        target_heights = np.minimum(amplitudes * self.sensitivity, self.MAX_TARGET_HEIGHT * 5) / 5
        target_heights = target_heights[:self.n_bins]
        self.heights = self.DECAY_FACTOR * self.heights + (1 - self.DECAY_FACTOR) * target_heights

    def update(self, audio_features):
        raw_amplitudes = np.array(audio_features["amps"])
        log_freqs, log_amplitudes = self.scale_bins(raw_amplitudes)
        self.calculate_heights(log_freqs, log_amplitudes)

    def get_mirrored_heights(self):
        first_half = self.heights[:len(self.heights)//2]
        mirrored_half = first_half[::-1]
        return np.concatenate([mirrored_half, first_half]) if self.invert_x else np.concatenate([first_half, mirrored_half])

    def draw_spikes(self, screen, w):
        heights = self.heights if not self.mirror_x else self.get_mirrored_heights()
        for i, h in enumerate(heights):
            x = int(i * self.bin_width + w)
            if h > 0:
                # Black outline then spike
                pygame.draw.polygon(screen, (0, 0, 0), [(x - w-3, self.screen_h), (x, self.screen_h - h-3), (x + w+3, self.screen_h)])
                pygame.draw.polygon(screen, self.visualizer.color, [(x - w, self.screen_h), (x, self.screen_h - h), (x + w, self.screen_h)])

    def draw_mirrored_view(self, screen):
        mirrored_snapshot = pygame.transform.flip(screen, self.invert_y, True)
        self.mirror_surf.blit(mirrored_snapshot, (0, 0))
        screen.blit(self.mirror_surf, (0, 0))

    def draw(self):
        screen = self.visualizer.screen
        w = self.bin_width // 2
        pygame.draw.rect(screen, (0, 0, 0), (0, self.screen_h-6, self.screen_w, 5))
        self.draw_spikes(screen, w)
        pygame.draw.rect(screen, self.visualizer.color, (0, self.screen_h-3, self.screen_w, 5))
        if self.mirror_y:
            self.draw_mirrored_view(screen)
