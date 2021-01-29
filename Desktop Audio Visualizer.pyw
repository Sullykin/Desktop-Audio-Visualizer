import pyaudio
import audioop
import pygame
import os
import sys
import random
import win32api, win32con, win32gui
from screeninfo import get_monitors
from ctypes import windll
from time import sleep

# The waveform level is loosely related the the beat of the music
# because loudness values are typically higher during a beat.

# add different input options in config
# add hotkey to put window on top
# reduce lag

# Version 1.3.0
    # program checks for the audio cable before starting
    # took out audio cable from release // users must now download the cable themselves
    # added support for different resolutions
    # custom position
    # put settings into variables
    # make each soundwave one color through its lifetime
    # add option for always on top
    # error dialog boxes
# automatically switch devices
# give option for framerate
# fix fade out

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

monitor = get_monitors()
SCREEN_WIDTH = monitor[0].width
SCREEN_HEIGHT = monitor[0].height
white = (255,255,255)
black = (0,0,0)
RED = (255,0,0)

# init pyaudio and find VAC
p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
    tempDevice = p.get_device_info_by_host_api_device_index(0, i).get('name')
    if 'CABLE Output' in tempDevice:
        deviceIndex = i
        break
    else: deviceIndex = None
if deviceIndex == None:
    windll.user32.MessageBoxW(0, u"Unable to locate virtual audio cable. Please make sure it is installed correctly then try again.", u"Error", 0)
    sys.exit()

# fetch settings
try:
    settings = []
    with open('Config.txt', 'r') as f:
        lines = f.readlines()
        for setting in lines:
            setting = setting.strip()
            if setting != '':
                if setting[0] == '#':
                    continue
                else:
                    settings.append(setting)
    settings[1] = settings[1].split(',')
    settings[3] = settings[3].split(',')
    customPosition = tuple(map(int,settings[3]))
    randomRGB = settings[0]
    customRGB = tuple(map(int,settings[1]))
    sensitivity = int(settings[4])
    maxSW = int(settings[6])
    spawnSensitivity = int(settings[5])
    randomPosition = settings[2]
    customPositionX, customPositionY = customPosition
    alwaysOnTop = settings[7]
except:
    windll.user32.MessageBoxW(0, u"Unable to load settings. Config.txt may be formatted incorrectly or is missing.", u"Error", 0)
    sys.exit()

class Soundwave():
    def __init__(self, x, y, data):
        self.x = x
        self.y = y
        self.maxdR = data//sensitivity
        if self.maxdR > 300:
            self.maxdR = 300
        self.dR = 6
        self.done = False
        self.radius = 6
        self.color = abs(random.randint(0,255)), abs(random.randint(0,255)), abs(random.randint(0,255))

    def update(self):
        # movement
        self.dR += 1
        self.radius = 5*self.dR
        # check radius
        if self.dR >= self.maxdR:
            self.done = True

    def draw(self):
        if self.radius >= spawnSensitivity:
            if randomRGB == 'enabled':
                pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius, 2)
            else:
                pygame.draw.circle(screen, customRGB, (self.x, self.y), self.radius, 2)

SetWindowPos = windll.user32.SetWindowPos
pygame.init()
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,0)
screen = pygame.display.set_mode((1920, 1080), pygame.NOFRAME)
if alwaysOnTop == 'enabled': SetWindowPos(pygame.display.get_wm_info()['window'], -1, 0, 0, 0, 0, 0x0001)
pygame.display.set_caption('Desktop Audio Visualizer')
fuchsia = (255, 0, 128) # Transparency color
dark_red = (139, 0, 0)
# Set window transparency color
hwnd = win32gui.FindWindow(None, "Desktop Audio Visualizer") # Getting window handle
lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
lExStyle |=  win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED 
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE , lExStyle )
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)

def play():
    data = 0
    soundwaves = []
    frames = []
    prevFrameCount = 0
    prevRGB = black
    
    clock = pygame.time.Clock()
    done = False
    while not done:
        frame = stream.read(CHUNK)
        volume = audioop.rms(frame, 2) # get volume of each frame
        # process user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
                pygame.quit()

        for soundwave in soundwaves:
            soundwave.update()
            if soundwave.done:
                soundwaves.remove(soundwave)
            # limit num of soundwaves to 100 by default
            if len(soundwaves) >= maxSW:
                soundwaves.remove(soundwaves[0])
        screen.fill(fuchsia)
        if randomPosition == 'enabled':
            soundwaves.append(Soundwave(random.randint(0,1920), random.randint(0,1080), volume))
        elif customPosition != (0,0):
            soundwaves.append(Soundwave(customPositionX, customPositionY, volume))
        else:
            soundwaves.append(Soundwave(1920//2, 1080//2, volume))
        for soundwave in soundwaves:
            soundwave.draw()
        
        pygame.display.flip()
        clock.tick(60)
#-------------------------------------------------------------------------------
stream = p.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True, output=True,
                frames_per_buffer=CHUNK,
                input_device_index=deviceIndex)
play()
stream.stop_stream()
stream.close()
p.terminate()
