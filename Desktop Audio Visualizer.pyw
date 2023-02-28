import pygame
import pyaudiowpatch as pyaudio  # patched pyaudio for loopback capability
import aubio  # audio feature extraction
import numpy as np
import win32api, win32con, win32gui
from screeninfo import get_monitors
from ctypes import windll
import os, sys
from winreg import *
from hashlib import md5

# Algos
import visualizers.spikes as spikes
import visualizers.blackhole as blackhole
import visualizers.soundwaves as soundwaves
import visualizers.perlinfield as perlinfield

# CORE CHANGES
# Uses patched pyaudio for loopback capability
# Applies peak normalization to audio, scaling all amplitudes to effective volumes

# The generative visualizer uses multiple algorithms to generate pleasing
# visuals using multiple audio signal features mixed with random noise as input

# Each algorithm has its own file and class so the visualizer can create the
# object, update it, and draw it along with other objects in a list each frame

class Visualizer:
    """ This object processes the audio signal and passes the values to all enabled visualizers """
    def __init__(self):
        self.setup_display()
        self.setup_audio()
        self.color = (0,0,0)
        self.colorfade = ColorFade()

    def setup_audio(self):
        # init pyaudio vars
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 48000

        # Init aubio pitch detection object
        self.pDetection = aubio.pitch("default", 2048, self.CHUNK, self.RATE)
        self.pDetection.set_unit("Hz")
        self.pDetection.set_silence(-40)

        # Set up the beat detection algorithm
        win_s = 2048  # Window size
        hop_s = win_s // 2  # Hop size
        samplerate = self.RATE  # Sampling rate
        self.tempo = aubio.tempo("default", win_s, hop_s, samplerate)
        self.max_amplitude = 0

    def setup_display(self):
        monitor = get_monitors()[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height

        # Fetch initial settings
        self.settings_checksum = ""
        self.update_config()

        # Init pygame and display
        SetWindowPos = windll.user32.SetWindowPos
        pygame.init()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0, 0)
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT),
                                              pygame.NOFRAME)
        if True:#self.settings['alwaysOnTop'] == 'enabled':
            SetWindowPos(
                pygame.display.get_wm_info()['window'], -1, 0, 0, 0, 0, 0x0001
                )
        pygame.display.set_caption('Desktop Audio Visualizer')
        self.clock = pygame.time.Clock()
        self.framecount = 0

        # Set window transparency color
        self.fuchsia = (255, 0, 128)  # Transparency color
        hwnd = win32gui.FindWindow(None, "Desktop Audio Visualizer")
        lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)
        win32gui.SetLayeredWindowAttributes(hwnd,
                                            win32api.RGB(*self.fuchsia), 0,
                                            win32con.LWA_COLORKEY)

    def start(self):
        with pyaudio.PyAudio() as p:
            # Get default WASAPI speakers
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        self.rate=int(default_speakers["defaultSampleRate"])
                        break
            self.default_device = default_speakers
            with p.open(format=self.FORMAT, channels=self.CHANNELS,
                        rate=self.RATE, input=True,
                        frames_per_buffer=self.CHUNK,
                        input_device_index=self.default_device["index"]
            ) as stream:
                self.stream = stream
                self.main()

    def main(self):
        valid_algos = {
            "spikes": spikes.Spikes(self),
            "blackhole": blackhole.BlackHole(self),
            "soundwaves": soundwaves.Soundwaves(self),
            "perlinfield": perlinfield.PerlinField(self)
        }
        self.active_algos = []
        for algo in self.settings["active_algos"]:
            if algo in valid_algos and valid_algos[algo] not in self.active_algos:
                self.active_algos.append(valid_algos[algo])
        self.done = False
        while not self.done:
            # Update settings every second
            if self.framecount % 60 == 0:
                self.update_config()

            # Process user input
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True

            # Calculate pitch and volume for this frame
            frame = self.stream.read(self.CHUNK)
            samples = np.frombuffer(frame, dtype=aubio.float_type)
            pitch = int(self.pDetection(samples)[0])
            abs_values = np.abs(samples)*100
            current_max_amp = int(np.max(abs_values))
            volume = int(self.normalize_volume(current_max_amp, abs_values))
            is_beat = self.tempo(samples)

            # update and draw visuals
            self.screen.fill(self.fuchsia)
            self.color = self.colorfade.next()
            for obj in self.active_algos:
                obj.update(pitch, volume, is_beat)
                obj.draw()

            pygame.display.flip()
            self.clock.tick(60)
            self.framecount += 1

    def update_config(self):
        with open('Config.txt', 'r') as f:
            new_checksum = md5(f.read().encode()).hexdigest()
            if self.settings_checksum:
                if new_checksum == self.settings_checksum:
                    return
            self.settings_checksum = new_checksum
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
            settings['active_algos'] = temp[0].split(', ')
            settings['color_scheme'] = temp[1]
            settings['volume_sensitivity'] = int(temp[2])
            self.settings = settings
        except Exception:
            windll.user32.MessageBoxW(0, u"Unable to load settings."
                                    " Config.txt may be formatted incorrectly"
                                    " or is missing.", u"Error", 0)
            sys.exit()

    def normalize_volume(self, current_max_amp, audio_array):
        if current_max_amp > self.max_amplitude:
            self.max_amplitude = current_max_amp
        # Reset the maximum amplitude to zero if the current maximum is zero
        elif current_max_amp == 0:
            self.max_amplitude = 0
        # Calculate the scaling factor to normalize the audio data
        scaling_factor = 1.0
        if self.max_amplitude != 0:
            scaling_factor /= self.max_amplitude
        return np.average(audio_array) * scaling_factor * self.settings["volume_sensitivity"]  # default 50

class ColorFade:
    def __init__(self):
        # Init color fade vars
        self.steps = 200
        self.color = (255, 0, 0)
        self.colorFrom = [255, 0, 0]
        self.colorTo = [0, 255, 0]
        self.inv_steps = 1.0 / self.steps
        self.step_R = (self.colorTo[0] - self.colorFrom[0]) * self.inv_steps
        self.step_G = (self.colorTo[1] - self.colorFrom[1]) * self.inv_steps
        self.step_B = (self.colorTo[2] - self.colorFrom[2]) * self.inv_steps
        self.r = self.colorFrom[0]
        self.g = self.colorFrom[1]
        self.b = self.colorFrom[2]
        self.transition_needed = False

    def calc_steps(self, colorTo):
        self.colorFrom = self.color
        self.colorTo = colorTo
        self.step_R = (self.colorTo[0] - self.colorFrom[0]) * self.inv_steps
        self.step_G = (self.colorTo[1] - self.colorFrom[1]) * self.inv_steps
        self.step_B = (self.colorTo[2] - self.colorFrom[2]) * self.inv_steps

    def next(self):
        if self.transition_needed:
            if self.color[0] >= 255:
                new_target = [0, 255, 0]
            elif self.color[1] >= 255:
                new_target = [0, 0, 255]
            else:
                new_target = [255, 0, 0]
            self.calc_steps(new_target)
            self.transition_needed = False

        self.r += self.step_R
        self.g += self.step_G
        self.b += self.step_B
        self.color = (int(self.r), int(self.g), int(self.b))

        if all([(self.step_R >= 0 and self.r >= self.colorTo[0]) or (self.step_R <= 0 and self.r <= self.colorTo[0]),
            (self.step_G >= 0 and self.g >= self.colorTo[1]) or (self.step_G <= 0 and self.g <= self.colorTo[1]),
            (self.step_B >= 0 and self.b >= self.colorTo[2]) or (self.step_B <= 0 and self.b <= self.colorTo[2])]):
            self.transition_needed = True
        
        return self.color


if __name__ == "__main__":
    visualizer = Visualizer()
    visualizer.start()
