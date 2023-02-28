import pygame
import noise

class PerlinField:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.p3count = 1
        self.nonce = 0

    def update(self, pitch, volume):
        self.nonce += (volume//2)+1
        self.p3count = volume
        for y in range(0, self.p3count):
            for x in range(0, self.visualizer.SCREEN_WIDTH):
                drawHeight = self.visualizer.SCREEN_HEIGHT - noise.pnoise3(x*0.002, y*0.02, self.nonce*0.02) * self.visualizer.SCREEN_HEIGHT - 500
                pygame.draw.line(self.visualizer.screen, self.visualizer.color, (x,drawHeight), (x,drawHeight), width=5)

    def draw(self):
        pass
