import pygame
from random import randint

class Spikes:
    def __init__(self, visualizer):
        self.spikes = []
        self.visualizer = visualizer

    def update(self, pitch, volume, is_beat):
        for spike in self.spikes:
            spike.update()
            if spike.done:
                self.spikes.remove(spike)
        if volume > 0:
            self.spikes.append(Spike(self.visualizer, pitch, volume))

    def draw(self):
        pygame.draw.rect(self.visualizer.screen, (0), (0, 1, self.visualizer.SCREEN_WIDTH, 5))  # Top
        pygame.draw.rect(self.visualizer.screen, (0), (0, self.visualizer.SCREEN_HEIGHT-6, self.visualizer.SCREEN_WIDTH, 5))  # Bottom
        for spike in self.spikes:
            spike.draw(self.visualizer.screen)
        pygame.draw.rect(self.visualizer.screen, self.visualizer.color, (0, -2, self.visualizer.SCREEN_WIDTH, 5))  # Top
        pygame.draw.rect(self.visualizer.screen, self.visualizer.color, (0, self.visualizer.SCREEN_HEIGHT-3, self.visualizer.SCREEN_WIDTH, 5))  # Bottom


class Spike:
    def __init__(self, visualizer, pitch, volume):
        self.visualizer = visualizer
        self.volume = volume
        self.maxHeight = volume*20
        self.x = ((pitch * self.visualizer.SCREEN_WIDTH) / 1000) + 400
        self.y = self.visualizer.SCREEN_HEIGHT-4
        self.w = 20
        self.h = 0
        self.done = False
        self.rise = True
        self.speed = (self.maxHeight//5)

    def update(self):
        # Movement
        if self.rise:
            self.h += self.speed
            if self.h >= self.maxHeight:
                self.rise = False
        else:
            self.h -= self.speed
            if self.h <= 0:
                self.done = True

    def draw(self, screen):
        # Black outlines
        pygame.draw.polygon(self.visualizer.screen, (0), [(self.visualizer.SCREEN_WIDTH-(self.x-10-4), 2),  # Top
                                        (self.visualizer.SCREEN_WIDTH-self.x, self.h+4),
                                        (self.visualizer.SCREEN_WIDTH-(self.x+10+4), 2)])

        pygame.draw.polygon(self.visualizer.screen, (0), [(self.x-10-4, self.y),  # Bottom
                                        (self.x, self.visualizer.SCREEN_HEIGHT-self.h-4),
                                        (self.x+10+4, self.y)])
        # Spikes
        pygame.draw.polygon(self.visualizer.screen, self.visualizer.color, [(self.visualizer.SCREEN_WIDTH-(self.x-10), 2),  # Top
                                            (self.visualizer.SCREEN_WIDTH-self.x, self.h),
                                            (self.visualizer.SCREEN_WIDTH-(self.x+10), 2)])

        pygame.draw.polygon(self.visualizer.screen, self.visualizer.color, [(self.x-10, self.y),  # Bottom
                                            (self.x, self.visualizer.SCREEN_HEIGHT-self.h),
                                            (self.x+10, self.y)])
