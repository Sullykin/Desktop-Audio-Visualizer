import pygame
import numpy as np

class PitchSpikes:
    MAX_TARGET_HEIGHT = 400
    DECAY_FACTOR = 0.75  # Moved decay factor here to align with FreqSpikes
    LOG_BIN_SCALING_FACTOR = 1.5  # Similar to FreqSpikes

    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.update_settings()
        self.spikes = np.zeros(self.n_bins, dtype=float)
        self.velocities = np.zeros(self.n_bins, dtype=float)
        self.decay_factor = 0.6
        self.screen_w, self.screen_h = visualizer.SCREEN_WIDTH, visualizer.SCREEN_HEIGHT
        self.bin_width = self.screen_w / self.n_bins
        self.half_screen_h = self.screen_h // 2

    def update_settings(self):
        self.sensitivity = self.visualizer.settings["volume_sensitivity"]
        self.n_bins = self.visualizer.settings["pitch_spikes"]["bins"]

    def scale_bins(self, pitch):
        n = 4000  # max pitch
        pitch_linear = np.linspace(0, n, n+1)

        # Create more bins for lower pitches
        more_bins_for_low_pitch = np.logspace(np.log10(pitch_linear[1]), np.log10(pitch_linear[-1]), int(self.n_bins * self.LOG_BIN_SCALING_FACTOR))
        log_pitches = more_bins_for_low_pitch[:self.n_bins]  # take only the required number of bins

        return log_pitches

    def update(self, audio_features):
        # Apply decay to all spikes first
        self.spikes *= self.DECAY_FACTOR

        # Update spike based on pitch
        pitch = audio_features["pitch"]
        log_pitches = self.scale_bins(pitch)
        bin_index = (np.abs(log_pitches - pitch)).argmin()
        volume = (np.max(audio_features["amps"])) * 50
        if 0 <= bin_index < self.n_bins:
            target_height = min(volume * self.sensitivity, self.MAX_TARGET_HEIGHT)
            self.spikes[bin_index] = self.DECAY_FACTOR * self.spikes[bin_index] + (1 - self.DECAY_FACTOR) * target_height

    def draw_spikes(self, screen):
        w = self.bin_width // 2
        for i, h in enumerate(self.spikes):
            offset = 250 * self.LOG_BIN_SCALING_FACTOR
            x = int(i * self.bin_width + w) - offset
            if h > 0 and x != - offset:
                pygame.draw.polygon(screen, (0, 0, 0), [(x - w-3, self.screen_h), (x, self.screen_h - h-3), (x + w+3, self.screen_h)])
                pygame.draw.polygon(screen, self.visualizer.color, [(x - w, self.screen_h), (x, self.screen_h - h), (x + w, self.screen_h)])

    def draw(self):
        screen = self.visualizer.screen
        pygame.draw.rect(screen, (0, 0, 0), (0, self.screen_h-6, self.screen_w, 5))
        self.draw_spikes(screen)
        pygame.draw.rect(screen, self.visualizer.color, (0, self.screen_h-3, self.screen_w, 5))
