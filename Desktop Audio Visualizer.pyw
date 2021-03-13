import pygame
import pyaudio
import aubio
import numpy as np
import win32api
import win32con
import win32gui
from screeninfo import get_monitors
from ctypes import windll
import os
import sys
from random import randint
from winreg import *


monitor = get_monitors()
SCREEN_WIDTH = monitor[0].width
SCREEN_HEIGHT = monitor[0].height


class Visualizer:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 44100

        # Init pyaudio and find VAC
        self.p = pyaudio.PyAudio()
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        self.deviceIndex = None
        for i in range(numdevices):
            tempDevice = self.p.get_device_info_by_host_api_device_index(
                0, i
                ).get('name')
            if 'CABLE Output' in tempDevice:
                self.deviceIndex = i
                break
        if self.deviceIndex is None:
            windll.user32.MessageBoxW(0, u'Unable to locate audio device'
                                      ' "CABLE Output". Please make sure it is'
                                      ' installed correctly then try again.',
                                      u"Error", 0)

        # Init aubio pitch detection object
        self.pDetection = aubio.pitch("default", 2048, 2048//2, 44100)
        self.pDetection.set_unit("Hz")
        self.pDetection.set_silence(-40)

        # Init color fade vars
        self.steps = 200
        self.color = (255, 0, 0)
        self.colorFrom = [255, 0, 0]
        self.colorTo = [0, 255, 0]
        self.step_R = (self.colorTo[0] - self.colorFrom[0]) / self.steps
        self.step_G = (self.colorTo[1] - self.colorFrom[1]) / self.steps
        self.step_B = (self.colorTo[2] - self.colorFrom[2]) / self.steps
        self.r = int(self.colorFrom[0])
        self.g = int(self.colorFrom[1])
        self.b = int(self.colorFrom[2])

        # Fetch initial settings
        settings = update_config()

        # Init pygame and display
        SetWindowPos = windll.user32.SetWindowPos
        pygame.init()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0, 0)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                              pygame.NOFRAME)
        if settings['alwaysOnTop'] == 'enabled':
            SetWindowPos(
                pygame.display.get_wm_info()['window'], -1, 0, 0, 0, 0, 0x0001
                )
        pygame.display.set_caption('Desktop Audio Visualizer')
        # Set window transparency color
        self.fuchsia = (255, 0, 128)  # Transparency color
        hwnd = win32gui.FindWindow(None, "Desktop Audio Visualizer")
        lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)
        win32gui.SetLayeredWindowAttributes(hwnd,
                                            win32api.RGB(*self.fuchsia), 0,
                                            win32con.LWA_COLORKEY)

        self.start()

    def main(self):
        global settings
        self.framecount = 0
        self.spikes = []
        self.soundwaves = []
        self.clock = pygame.time.Clock()
        self.done = False
        while not self.done:
            # Every 5 seconds, update settings and color
            self.framecount += 1
            if self.framecount % (60*3) == 0:
                settings = update_config()

            # Process user input
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True

            # Calculate pitch and volume for this frame
            frame = self.stream.read(self.CHUNK)
            samples = np.frombuffer(frame, dtype=aubio.float_type)
            pitch = int(self.pDetection(samples)[0])
            volume = int(np.average(np.abs(samples))*100)

            # Assign color to spikes according to pitch/volume
            if volume > 5:
                self.outline = volume // 5
            else:
                self.outline = 1

            self.color = list(self.color)
            if self.color[0] > 250:
                self.calc_steps([0, 255, 0])
            elif self.color[1] > 250:
                self.calc_steps([0, 0, 255])
            elif self.color[2] > 250:
                self.calc_steps([255, 0, 0])

            self.color = (int(self.r), int(self.g), int(self.b))
            self.r += self.step_R
            self.g += self.step_G
            self.b += self.step_B

            for spike in self.spikes:
                spike.update()
                if spike.done:
                    self.spikes.remove(spike)

            for soundwave in self.soundwaves:
                soundwave.update()
                if soundwave.done:
                    self.soundwaves.remove(soundwave)

            self.screen.fill(self.fuchsia)

            # Spikes
            if settings['spikes'] == 'enabled':
                if settings['spikeColor'] == 'random':
                    spikeColor = (randint(0,255),
                                  randint(0,255),
                                  randint(0,255))
                elif settings['spikeColor'] == 'fade':
                    spikeColor = self.color
                else:
                    spikeColor = tuple(map(int,settings['spikeColor'].split(',')))
                    
                pygame.draw.rect(self.screen, (0), (0, 1, SCREEN_WIDTH, 5))  # Top
                pygame.draw.rect(self.screen, (0), (0, SCREEN_HEIGHT-6, SCREEN_WIDTH, 5))  # Bottom
                if volume >= settings['spikeSpawnSensitivity']:
                    self.spikes.append(Spike(volume, pitch, spikeColor))
                for spike in self.spikes:
                    spike.draw(self.screen)
                if settings['spikeColor'] == 'random':
                    spikeColor = (255,255,255)
                pygame.draw.rect(self.screen, spikeColor, (0, -2, SCREEN_WIDTH, 5))  # Top
                pygame.draw.rect(self.screen, spikeColor, (0, SCREEN_HEIGHT-3, SCREEN_WIDTH, 5))  # Bottom

            # Soundwaves
            if settings['soundwaves'] == 'enabled':
                if volume >= settings['circleSpawnSensitivity']:
                    if settings['circlePosition'] == 'random':
                        self.soundwaves.append(Soundwave(randint(0,SCREEN_WIDTH), randint(0,SCREEN_HEIGHT), volume, self.color))
                    elif settings['circlePosition'] == 'center':
                        self.soundwaves.append(Soundwave(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, volume, self.color))
                    else:
                        position = list(map(int,settings['circlePosition'].split(','))) # put coords into tuple
                        self.soundwaves.append(Soundwave(position[0], position[1], volume, self.color))
                for soundwave in self.soundwaves:
                    soundwave.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

    def calc_steps(self, colorTo):
        self.colorFrom = self.color
        self.colorTo = colorTo
        self.step_R = (self.colorTo[0] - self.colorFrom[0]) / self.steps
        self.step_G = (self.colorTo[1] - self.colorFrom[1]) / self.steps
        self.step_B = (self.colorTo[2] - self.colorFrom[2]) / self.steps

    def start(self):
        self.stream = self.p.open(format=self.FORMAT, channels=self.CHANNELS,
                                  rate=self.RATE, input=True, output=True,
                                  frames_per_buffer=self.CHUNK,
                                  input_device_index=self.deviceIndex)
        self.main()

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class Spike:
    def __init__(self, volume, freq, color):
        self.volume = volume
        self.maxHeight = volume*settings['spikeSensitivity']
        self.x = transform(freq)
        self.y = SCREEN_HEIGHT-4
        self.w = 20
        self.h = 0
        self.done = False
        self.rise = True
        self.speed = (self.maxHeight//5)
        self.color = color

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
        pygame.draw.polygon(screen, (0), [(SCREEN_WIDTH-(self.x-10-4), 2),  # Top
                                          (SCREEN_WIDTH-self.x, self.h+4),
                                          (SCREEN_WIDTH-(self.x+10+4), 2)])

        pygame.draw.polygon(screen, (0), [(self.x-10-4, self.y),  # Bottom
                                          (self.x, SCREEN_HEIGHT-self.h-4),
                                          (self.x+10+4, self.y)])
        # Beat outlines
        '''
        if self.rise and self.volume > 20:
            ocolor = list(self.color)
            ocolor[0] = 255-ocolor[0]
            ocolor[1] = 255-ocolor[1]
            ocolor[2] = 255-ocolor[2]
            ocolor = tuple(ocolor)
            pygame.draw.polygon(screen, ocolor,  # Top
                                [(SCREEN_WIDTH-(self.x-10-outline), 2),
                                 (SCREEN_WIDTH-self.x, self.h-outline),
                                 (SCREEN_WIDTH-(self.x+10+outline), 2)])
            
            pygame.draw.polygon(screen, ocolor,  # Bottom
                                [(self.x-10-outline, self.y),
                                 (self.x, SCREEN_HEIGHT-self.h-outline),
                                 (self.x+10+outline, self.y)])
        '''
        # Spikes
        pygame.draw.polygon(screen, self.color, [(SCREEN_WIDTH-(self.x-10), 2),  # Top
                                            (SCREEN_WIDTH-self.x, self.h),
                                            (SCREEN_WIDTH-(self.x+10), 2)])

        pygame.draw.polygon(screen, self.color, [(self.x-10, self.y),  # bottom
                                            (self.x, SCREEN_HEIGHT-self.h),
                                            (self.x+10, self.y)])


class Soundwave():
    def __init__(self, x, y, data, color):
        self.x = x
        self.y = y
        self.maxRadius = data*settings['circleSensitivity']
        self.radius = 0
        self.done = False
        if settings['circleColor'] == 'random':
            self.color = (randint(0,255),
                          randint(0,255),
                          randint(0,255))
        elif settings['circleColor'] == 'fade':
            self.color = color
        else:
            self.color = tuple(map(int,settings['circleColor'].split(',')))
        
    def update(self):
        # movement
        self.radius += 5
        # check radius
        if self.radius >= self.maxRadius:
            self.done = True

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius, 3)


def update_config():
    global settings
    try:
        temp = {}
        settings = {}
        with open('Config.txt', 'r') as f:
            i = 0
            for setting in f.readlines():
                setting = setting.strip()
                if setting != '' and setting[0] != '#':
                    temp[i] = setting.lower()
                    i += 1
        # General settings
        settings['soundwaves'] = temp[0]
        settings['spikes'] = temp[1]
        settings['alwaysOnTop'] = temp[2]
        # Circle settings
        settings['circleColor'] = temp[3]
        settings['circlePosition'] = temp[4]
        settings['circleSensitivity'] = int(temp[5])
        settings['circleSpawnSensitivity'] = int(temp[6])
        # Spike settings
        settings['spikeColor'] = temp[7]
        settings['spikeSensitivity'] = int(temp[8])
        settings['spikeSpawnSensitivity'] = int(temp[9])
        return settings
    except Exception:
        windll.user32.MessageBoxW(0, u"Unable to load settings."
                                  " Config.txt may be formatted incorrectly"
                                  " or is missing.", u"Error", 0)
        sys.exit()


def transform(pitch):
    # Put c4 freq at ~center using linear range conversion
    OldRange = (1000 - 0)
    NewRange = (SCREEN_WIDTH - 0)
    return (((pitch - 0) * NewRange) / OldRange) + 400


if __name__ == "__main__":
    visualizer = Visualizer()
    visualizer.start()
