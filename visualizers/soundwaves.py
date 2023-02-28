import pygame
from random import randint

class Soundwaves:
    def __init__(self, visualizer):
        self.soundwaves = []
        self.visualizer = visualizer

    def update(self, pitch, volume):
        for soundwave in self.soundwaves:
            soundwave.update()
            if soundwave.done:
                self.soundwaves.remove(soundwave)
        if volume >= self.visualizer.settings['circleSpawnSensitivity']:
            if self.visualizer.settings['circlePosition'] == 'random':
                self.soundwaves.append(Soundwave(self.visualizer, randint(0,self.visualizer.SCREEN_WIDTH), randint(0,self.visualizer.SCREEN_HEIGHT), volume))
            elif self.visualizer.settings['circlePosition'] == 'center':
                self.soundwaves.append(Soundwave(self.visualizer, self.visualizer.SCREEN_WIDTH//2, self.visualizer.SCREEN_HEIGHT//2, volume))
            else:
                position = list(map(int,self.visualizer.settings['circlePosition'].split(','))) # put coords into tuple
                self.soundwaves.append(Soundwave(self.visualizer, position[0], position[1], volume))

    def draw(self):
        for soundwave in self.soundwaves:
            soundwave.draw()

class Soundwave:
    def __init__(self, visualizer, x, y, volume):
        self.visualizer = visualizer
        self.x = x
        self.y = y
        self.maxRadius = volume*self.visualizer.settings['circleSensitivity']
        self.radius = 0
        self.done = False
        self.color = self.visualizer.color
        
    def update(self):
        # movement
        self.radius += 5
        # check radius
        if self.radius >= self.maxRadius:
            self.done = True

    def draw(self):
        pygame.draw.circle(self.visualizer.screen, self.color, (self.x, self.y), self.radius, 3)
