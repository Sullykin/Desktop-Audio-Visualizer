import pyaudio
import aubio
import numpy as np
import pygame
import win32api, win32con, win32gui
from screeninfo import get_monitors
from ctypes import windll
import os
import sys
import random
from time import sleep
from scipy import signal
import struct

# Version 1.4.0
    # removed max sw option
    
# give option for framerate
# drag function or click to pickup/release
# merge enable and custom settings?
# allow user to type the name of a vac device
# color determined by loudness
# add hotkey to put window on top
# reduce lag
# blur and shake screen on beats
# default center in settings instead of 0,0
# multi-monitor support
# separate left/right stereo channels
# option for circle thickness
# side quest: make a frequency heat map of a song


# for other branch:
    # auto select contrasting color based on bg (use chart)
    # beat blur/shake

CHUNK = 1024
FORMAT = pyaudio.paFloat32
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
deviceIndex = None
for i in range(numdevices):
    tempDevice = p.get_device_info_by_host_api_device_index(0, i).get('name')
    if 'CABLE Output' in tempDevice:
        deviceIndex = i
        break
if deviceIndex == None:
    windll.user32.MessageBoxW(0, u"Unable to locate audio device \"CABLE Output\". Please make sure it is installed correctly then try again.", u"Error", 0)
    sys.exit()
    
# init aubio pitch detection object
pDetection = aubio.pitch("default", 2048, 2048//2, 44100)
pDetection.set_unit("Hz")
pDetection.set_silence(-40)


#p = c + r*a + d*I*a
# Px, Py = tangent intersection
# Cx, Cy = circle center
# a = circle raidus

# start at center of circle, draw line to outside point using freq

class Spike_cirlce():
    def __init__(self, volume, freq):
        self.maxHeight = volume*10
        self.x = freq+400
        self.y = SCREEN_HEIGHT
        self.w = 2
        self.h = 0
        if settings['randomRGB'] == 'enabled':
            self.color = (random.randint(0,255),
                          random.randint(0,255),
                          random.randint(0,255))
        else:
            self.color = settings['customRGB']
        self.done = False

    def update(self):
        # movement
        self.h += 15
        # check radius
        if self.h <= self.maxHeight:
            self.done = True

    def draw(self):
        pygame.draw.polygon(screen, self.color, [(self.x-10,self.y), (self.x,SCREEN_HEIGHT-self.h), (self.x+10,self.y)])
        #pygame.draw.rect(screen, self.color, (self.x, SCREEN_HEIGHT-self.h, self.w, self.h))



class Spike():
    def __init__(self, volume, freq):
        self.maxHeight = volume*10
        self.x = transform(freq)
        self.y = SCREEN_HEIGHT
        self.w = 20
        self.h = 0
        if settings['randomRGB'] == 'enabled':
            self.color = (random.randint(0,255),
                          random.randint(0,255),
                          random.randint(0,255))
        else:
            self.color = settings['customRGB']
        self.done = False

    def update(self):
        # movement
        self.h += 20
        # check radius
        if self.h >= self.maxHeight:
            self.done = True

    def draw(self):
        #pygame.draw.polygon(screen, self.color, [(self.x-10,self.y), (self.x,SCREEN_HEIGHT-self.h), (self.x+10,self.y)])
        pygame.draw.rect(screen, self.color, (self.x, SCREEN_HEIGHT-self.h, self.w, self.h))


class Soundwave():
    def __init__(self, x, y, data):
        self.x = x
        self.y = y
        self.maxRadius = data*settings['sensitivity']
        self.radius = 0
        self.done = False
        if settings['randomRGB'] == 'enabled':
            self.color = (random.randint(0,255),
                          random.randint(0,255),
                          random.randint(0,255))
        else:
            self.color = settings['customRGB']
        
    def update(self):
        # movement
        self.radius += 5
        # check radius
        if self.radius >= self.maxRadius:
            self.done = True

    def draw(self):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius, 2)

def updateConfig():
    global settings
    try:
        temp = {}
        settings = {}
        with open('Config.txt', 'r') as f:
            i = 0
            for setting in f.readlines():
                setting = setting.strip()
                if setting != '' and setting[0] != '#': # ignore blank lines and hashtags
                    temp[i] = setting
                    i += 1
        temp[1] = temp[1].split(',')
        temp[3] = tuple(map(int,temp[3].split(',')))
        settings['randomRGB']        = temp[0]
        settings['customRGB']        = tuple(map(int,temp[1]))
        
        settings['randomPosition']   = temp[2]
        settings['customPositionX'], settings['customPositionY']  = temp[3]

        settings['sensitivity']      = int(temp[4])
        settings['spawnSensitivity'] = int(temp[5])
        settings['alwaysOnTop']      = temp[6]
        return settings
    except:
        windll.user32.MessageBoxW(0, u"Unable to load settings. Config.txt may be formatted incorrectly or is missing.", u"Error", 0)
        sys.exit()

def transform(x):
    # put c4 freq at center
    return (x - 0)*(SCREEN_WIDTH/1000)+400 # linear

# fetch initial settings
settings = updateConfig()

# Init pygame and display
SetWindowPos = windll.user32.SetWindowPos
pygame.init()
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,0)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
if settings['alwaysOnTop'] == 'enabled': SetWindowPos(pygame.display.get_wm_info()['window'], -1, 0, 0, 0, 0, 0x0001)
pygame.display.set_caption('Desktop Audio Visualizer')
# Set window transparency color
fuchsia = (255, 0, 128) # Transparency color
hwnd = win32gui.FindWindow(None, "Desktop Audio Visualizer") # Getting window handle
lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
lExStyle |=  win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED 
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE , lExStyle )
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)


def play():
    global settings
    framecount = 0
    soundwaves = []
    spikes = []
    clock = pygame.time.Clock()
    done = False
    while not done:
        # Every 3 seconds, update settings
        framecount += 1
        if framecount % (60*3) == 0:
            settings = updateConfig()

        # Calculate pitch and volume for this frame
        frame = stream.read(CHUNK)
        samples = np.frombuffer(frame, dtype=aubio.float_type)
        pitch = int(pDetection(samples)[0])
        volume = int(np.average(np.abs(samples))*100)
        '''
        fourier_transform = np.fft.rfft(samples)
        abs_fourier_transform = np.abs(fourier_transform)
        power_spectrum = np.square(abs_fourier_transform)
        frequency = np.linspace(0, RATE/2, len(power_spectrum))
        for freq in abs_fourier_transform:
            # combine frequencies into sections
            if freq < 100: section0_99.append(freq)
            elif freq < 200: section100_199.append(freq)
        for freq in section0_99:
        '''
        # ^ if freq in section: add amplitude to base_freq and remove freq
            
        # process user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True

        # Update and remove soundwaves
        for soundwave in soundwaves:
            soundwave.update()
            if soundwave.done:
                soundwaves.remove(soundwave)

        for spike in spikes:
            spike.update()
            if spike.done:
                spikes.remove(spike)

        screen.fill(fuchsia)
        pygame.draw.rect(screen, (255,0,0), (0,1075,SCREEN_WIDTH,10))
        # draw soundwaves according to settings
        if volume >= settings['spawnSensitivity']:
            if settings['randomPosition'] == 'enabled':
                soundwaves.append(Soundwave(random.randint(0,SCREEN_WIDTH), random.randint(0,SCREEN_HEIGHT), volume))
            elif settings['customPositionX'] != 0 and settings['customPositionY'] != 0:
                soundwaves.append(Soundwave(settings['customPositionX'], settings['customPositionY'], volume))
            else:
                soundwaves.append(Soundwave(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, volume))
        for soundwave in soundwaves:
            soundwave.draw()
        if volume >= settings['spawnSensitivity']:
            #for pitch in abs_fourier_transform:
            #    spikes.append(Spike(volume, pitch))
            spikes.append(Spike(volume, pitch))
        for spike in spikes:
            spike.draw()

        pygame.display.flip()
        clock.tick(60)


stream = p.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True, output=True,
                frames_per_buffer=CHUNK,
                input_device_index=deviceIndex)

play()
stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()
sys.exit()
