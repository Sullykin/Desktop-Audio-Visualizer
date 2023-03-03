import pygame

class Spikes:
    def __init__(self, visualizer):
        self.spikes = []
        self.visualizer = visualizer

    def update(self, audio_features):
        pitch = audio_features["pitch"]
        volume = audio_features["volume"]
        for spike in self.spikes:
            spike.update()
            if spike.done:
                self.spikes.remove(spike)
        if volume > 0:
            self.spikes.append(Spike(self.visualizer, pitch, volume))

    def draw(self):
        screen = self.visualizer.screen
        color = self.visualizer.color
        screen_w = self.visualizer.SCREEN_WIDTH
        screen_h = self.visualizer.SCREEN_HEIGHT
        pygame.draw.rect(screen, (0,0,0), (0, 1, screen_w, 5))  # Top
        pygame.draw.rect(screen, (0,0,0), (0, screen_h-6, screen_w, 5))  # Bottom
        for spike in self.spikes:
            spike.draw()
        pygame.draw.rect(screen, color, (0, -2, screen_w, 5))  # Top
        pygame.draw.rect(screen, color, (0, screen_h-3, screen_w, 5))  # Bottom


class Spike:
    def __init__(self, visualizer, pitch, volume):
        self.visualizer = visualizer
        self.volume = volume
        self.x = ((pitch * self.visualizer.SCREEN_WIDTH) / 1000) + 200
        self.y = self.visualizer.SCREEN_HEIGHT - 4
        self.w = 20
        self.h = 0
        self.rise = True
        self.done = False
        self.maxHeight = (volume ** 1.15) * (visualizer.settings["volume_sensitivity"] / 3)
        self.speed = self.maxHeight / 4

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

    def draw(self):
        screen = self.visualizer.screen
        color = self.visualizer.color
        screen_w = self.visualizer.SCREEN_WIDTH
        screen_h = self.visualizer.SCREEN_HEIGHT
        # Black outlines
        pygame.draw.polygon(screen, (0,0,0), [(screen_w-(self.x-10-4), 2),  # Top
                                        (screen_w-self.x, self.h+4),
                                        (screen_w-(self.x+10+4), 2)])

        pygame.draw.polygon(screen, (0,0,0), [(self.x-10-4, self.y),  # Bottom
                                        (self.x, screen_h-self.h-4),
                                        (self.x+10+4, self.y)])
        # Spikes
        pygame.draw.polygon(screen, color, [(screen_w-(self.x-10), 2),  # Top
                                            (screen_w-self.x, self.h),
                                            (screen_w-(self.x+10), 2)])

        pygame.draw.polygon(screen, color, [(self.x-10, self.y),  # Bottom
                                            (self.x, screen_h-self.h),
                                            (self.x+10, self.y)])
