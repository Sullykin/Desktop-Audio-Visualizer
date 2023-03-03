import pygame
import numpy as np

# spin in a circle constantly, tracing with
# radius = amplitude

class Spirograph:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.color = self.visualizer.color
        self.center = (self.visualizer.SCREEN_WIDTH // 2, self.visualizer.SCREEN_HEIGHT // 2)
        self.angle = 0
        self.speed = 0
        self.radius = 0
        self.theta = 0

    def update(self, audio_features):
        fft = audio_features["fft"]
        # Calculate spirograph parameters based on audio data
        index = 10
        self.speed = np.abs(fft[index])
        self.radius = np.abs(fft[index + 5])
        self.theta += self.speed / 100
        self.angle += np.deg2rad(self.theta)

    def draw(self):
        # Draw spirograph on screen
        x = int(self.center[0] + self.radius * np.cos(self.angle))
        y = int(self.center[1] + self.radius * np.sin(self.angle))
        pygame.draw.circle(self.visualizer.screen, self.visualizer.color, (x, y), 5)