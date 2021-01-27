import pygame, os, sys, random, pyaudio, audioop, win32api, win32con, win32gui

# Cinematic visualizer for dektop audio output
# VAC required to loopback output streams

# add different input options in config
# add hotkey to put window on top
# reduce lag

# Version 1.2.1
    # Added option to center the soundwaves instead of giving them random spawn positions
    # Added spawn sensitivity option
    # Reduced possible lag

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 500000

p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
    tempDevice = p.get_device_info_by_host_api_device_index(0, i).get('name')
    if 'CABLE Output' in tempDevice:
        deviceIndex = i
        break

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
white = (255,255,255)
black = (0,0,0)
RED = (255,0,0)

settings = []
with open('Setup and Config- CLICK ME\\config.txt', 'r') as f:
    lines = f.readlines()
    for setting in lines:
        setting = setting.strip()
        if setting != '':
            if setting[0] == '#':
                continue
            else:
                settings.append(setting)
settings[1] = settings[1].split(',')
settings[1] = list(map(int,settings[1]))

class Soundwave():
    def __init__(self, x, y, data):
        self.x = x
        self.y = y
        self.maxdR = data//int(settings[2])
        if self.maxdR > 300:
            self.maxdR = 300
        self.dR = 6
        self.done = False
        self.age = 255
        self.radius = 6

    def update(self):
        # movement
        self.dR += 1
        self.radius = 5*self.dR
        # check radius
        if self.dR >= self.maxdR:
            self.done = True
        # age color
        self.age = 255-(255/((self.maxdR/self.dR)+1))

    def draw(self):
        if self.radius >= int(settings[4]):
            if settings[0] == 'enabled':
                pygame.draw.circle(screen, (abs(random.randint(0,255)-self.age), abs(random.randint(0,255)-self.age), abs(random.randint(0,255)-self.age), 155), (self.x, self.y), self.radius, 2)
            else:
                pygame.draw.circle(screen, tuple(settings[1]), (self.x, self.y), self.radius, 2)

pygame.init()
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,0)
screen = pygame.display.set_mode((1920, 1080), pygame.NOFRAME)
pygame.display.set_caption('Desktop Audio Visualizer')
fuchsia = (255, 0, 128)  # Transparency color
dark_red = (139, 0, 0)

# Set window transparency color
hwnd = win32gui.FindWindow(None, "Desktop Audio Visualizer") # Getting window handle
lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
lExStyle |=  win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED 
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE , lExStyle )
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)

def play():
    global settings
    data = 0
    soundwaves = []
    frames = []
    prevFrameCount = 0
    prevRGB = black
    
    clock = pygame.time.Clock()
    done = False
    while not done:
        garbo = stream.read(CHUNK)
        rms = audioop.rms(garbo, 2) # get volume of each frame
        frames.append(rms)
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
            if len(soundwaves) >= int(settings[3]):
                soundwaves.remove(soundwaves[0])
        screen.fill(fuchsia)
        try:
            data = frames[0]
            frames.remove(frames[0])
            if settings[5] == 'enabled':
                soundwaves.append(Soundwave(random.randint(0,1920), random.randint(0,1080), data))
            else:
                soundwaves.append(Soundwave(1920//2, 1080//2, data))
        except:
            pass
        for soundwave in soundwaves:
            soundwave.draw()
        
        pygame.display.flip()
        clock.tick(60)
#-------------------------------------------------------------------------------

stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, output=True, frames_per_buffer=CHUNK, input_device_index=deviceIndex)

play()

stream.stop_stream()
stream.close()
p.terminate()
