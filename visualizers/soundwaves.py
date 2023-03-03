import pygame
from random import randint

class Soundwaves:
    def __init__(self, visualizer):
        self.soundwaves = []
        self.visualizer = visualizer
        self.position = "center"

    def update(self, audio_features):
        volume = audio_features["volume"]
        pitch = audio_features["pitch"]
        color = self.visualizer.color
        if pitch < 500:  # good limit for voices and bass
            color = [pitch//2 if i == 0 else x for i, x in enumerate(color)]
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
        self.maxRadius = volume * self.visualizer.settings["volume_sensitivity"] // 2
        self.radius = 0
        self.done = False
        self.color = color
        
    def update(self):
        # movement
        self.radius += 5
        if self.radius >= self.maxRadius:
            self.done = True

    def draw(self):
        pygame.draw.circle(self.visualizer.screen, self.color, (self.x, self.y), self.radius, 3)
