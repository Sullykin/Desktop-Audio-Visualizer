import pygame
from random import randint
import numpy as np

class Soundwaves:
    def __init__(self, visualizer):
        self.soundwaves = []
        self.visualizer = visualizer
        self.position = "center"

    def update_settings(self):
        pass

    def update(self, audio_features):
        volume = np.max(audio_features["amps"]) ** 1.3
        color = self.visualizer.color
        color = [max(x - int(volume * 2.5), 0) for x in color]
        for soundwave in self.soundwaves:
            soundwave.update()
            if soundwave.done:
                self.soundwaves.remove(soundwave)

        if volume >= 0:
            if self.position == 'random':
                self.soundwaves.append(Soundwave(self.visualizer, randint(0,self.visualizer.SCREEN_WIDTH), randint(0,self.visualizer.SCREEN_HEIGHT), volume, color))
            elif self.position == 'center':
                self.soundwaves.append(Soundwave(self.visualizer, self.visualizer.SCREEN_WIDTH//2, self.visualizer.SCREEN_HEIGHT//2, volume, color))

    def draw(self):
        for soundwave in self.soundwaves:
            soundwave.draw()

class Soundwave:
    def __init__(self, visualizer, x, y, volume, color):
        self.visualizer = visualizer
        self.x = x
        self.y = y
        self.speed = volume
        self.maxRadius = volume * self.visualizer.settings["volume_sensitivity"]
        self.radius = 0
        self.done = False
        self.color = color
        
    def update(self):
        # movement
        self.radius += self.speed
        if self.radius >= self.maxRadius:
            self.done = True

    def draw(self):
        pygame.draw.circle(self.visualizer.screen, self.color, (self.x, self.y), self.radius, 3)
