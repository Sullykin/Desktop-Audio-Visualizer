import pygame
import numpy as np

# make a mirrored y-axis version for better pattern perception
    # add option in config for mirror on x, y, or both 
# apparently "girls just wanna have fun" is the perfect song to test this thing

class FreqSpikes:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.max_frequency = 1600  # technically the center frequency
        self.bin_range = 21.5332  # rate / chunk
        self.n_bins = int(self.max_frequency // self.bin_range)
        self.bin_width = int(visualizer.SCREEN_WIDTH // self.n_bins + 1)
        self.spikes = [Spike(visualizer, (self.bin_width * i), self.bin_width-5) for i in range(self.n_bins)]

    def update(self, audio_features):
        amplitudes = audio_features["amps"]
        #pitch = audio_features["pitch"]
        for i, spike in enumerate(self.spikes):
            amplitude = amplitudes[i]
            #if abs((i * self.bin_range) - pitch) < self.bin_range:
            #    amplitude *= 2
            spike.update(amplitude)

    def draw(self):
        screen = self.visualizer.screen
        color = self.visualizer.color
        screen_w, screen_h = self.visualizer.SCREEN_WIDTH, self.visualizer.SCREEN_HEIGHT
        pygame.draw.rect(screen, (0,0,0), (0, 1, screen_w, 5))  # Top
        pygame.draw.rect(screen, (0,0,0), (0, screen_h-6, screen_w, 5))  # Bottom
        for spike in self.spikes:
            if spike.h > 0:
                spike.draw()
        pygame.draw.rect(screen, color, (0, -2, screen_w, 5))  # Top
        pygame.draw.rect(screen, color, (0, screen_h-3, screen_w, 5))  # Bottom


class Spike:
    def __init__(self, visualizer, x, w):
        self.visualizer = visualizer
        self.x = x + w // 2
        self.y = self.visualizer.SCREEN_HEIGHT
        self.w = w
        self.h = 0

    def update(self, amplitude):
        # move spike up if current height lower than target height or vice versa
        target_h = int(min((amplitude**1.5)*(self.visualizer.settings["volume_sensitivity"]/3), 300))
        speed = np.abs(target_h - self.h) / 3.5
        if self.h < target_h:
            self.h += speed
        elif self.h > target_h:
            self.h -= speed

    def draw(self):
        screen = self.visualizer.screen
        color = self.visualizer.color
        screen_w = self.visualizer.SCREEN_WIDTH
        w = self.w//2
        # Black outlines
        pygame.draw.polygon(screen, (0), [(screen_w-(self.x-w-4), 2),  # Top
                                        (screen_w-self.x, self.h+4),
                                        (screen_w-(self.x+w+4), 2)])

        pygame.draw.polygon(screen, (0), [(self.x-w-4, self.y),  # Bottom
                                        (self.x, self.visualizer.SCREEN_HEIGHT-self.h-4),
                                        (self.x+w+4, self.y)])
        # Spikes
        pygame.draw.polygon(screen, color, [(screen_w-(self.x-w), 2),  # Top
                                            (screen_w-self.x, self.h),
                                            (screen_w-(self.x+w), 2)])

        pygame.draw.polygon(screen, color, [(self.x-w, self.y),  # Bottom
                                            (self.x, self.visualizer.SCREEN_HEIGHT-self.h),
                                            (self.x+w, self.y)])
