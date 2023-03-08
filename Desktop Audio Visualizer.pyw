import pygame
import pyaudiowpatch as pyaudio  # patched pyaudio for loopback capability
import aubio  # audio feature extraction
import numpy as np
import win32api, win32con, win32gui
from screeninfo import get_monitors
from ctypes import windll
import os, sys
from hashlib import md5

import visualizers.soundwaves as soundwaves
import visualizers.freq_spikes as freq_spikes
import visualizers.spikes as spikes
import visualizers.blackhole as blackhole
#import visualizers.spirograph as spirograph
#import visualizers.perlinfield as perlinfield

# TODO
# setup new beat detection
# consider adding higher quality mode after getting new pc


class Visualizer:
    def __init__(self):
        self.color = (0,0,0)
        self.colorfade = ColorFade()
        self.settings_checksum = ""
        self.update_config(startup=True)
        self.setup_display()
        self.algos = {
            "pitch_spikes": spikes.Spikes(self),
            "blackhole": blackhole.BlackHole(self),
            "soundwaves": soundwaves.Soundwaves(self),
            #"perlinfield": perlinfield.PerlinField(self),
            #"spirograph": spirograph.Spirograph(self),
            "freq_spikes": freq_spikes.FreqSpikes(self)
        }
        self.get_algo()
        self.max_amplitude = 0
        self.done = False

    def setup_display(self):
        monitor = get_monitors()[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height
        pygame.init()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0, 0)
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT),pygame.NOFRAME)
        hwnd = pygame.display.get_wm_info()['window']
        #self.keep_topmost(hwnd)
        self.set_window_transparency(hwnd)
        pygame.display.set_caption('Desktop Audio Visualizer')
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.framecount = 0

    # Stopped working for seemingly no reason
    """
    def keep_topmost(self, hwnd):
        SetWindowPos = windll.user32.SetWindowPos
        if self.settings['alwaysOnTop'] == 'enabled':
            NOSIZE = 1
            NOMOVE = 2
            TOPMOST = -1
            SetWindowPos(hwnd, TOPMOST, 0, 0, 0, 0, NOMOVE|NOSIZE)
    """

    def set_window_transparency(self, hwnd):
        self.fuchsia = (255, 0, 128)  # Transparency color
        lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)
        win32gui.SetLayeredWindowAttributes(hwnd,
                                            win32api.RGB(*self.fuchsia), 0,
                                            win32con.LWA_COLORKEY)

    def setup_audio(self):
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.setup_pitch_detection()

    def setup_pitch_detection(self):
        self.pDetection = aubio.pitch("default", 4096, self.CHUNK, self.RATE)
        self.pDetection.set_unit("Hz")
        self.pDetection.set_silence(-40)

    def start(self):
        with pyaudio.PyAudio() as p:
            # Get default WASAPI speakers
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            self.RATE = 44100
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        self.RATE=int(default_speakers["defaultSampleRate"])
                        break
            print(self.RATE)

            self.setup_audio()
            with p.open(format=self.FORMAT, 
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.CHUNK,
                        input_device_index=default_speakers["index"]
            ) as self.stream:
                self.main()

    def main(self):
        while not self.done:
            # Update settings every second
            if self.framecount % self.fps == 0:
                self.update_config()

            # Process user input
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True

            # read in audio and calculate signal properties
            frame = self.stream.read(self.CHUNK)
            samples = np.frombuffer(frame, dtype=aubio.float_type)
            audio_features = self.process_audio(samples)

            # update and draw visuals
            self.screen.fill(self.fuchsia)
            if self.settings["color_scheme"] == "fade":
                self.color = self.colorfade.next()
            self.active_algo.update(audio_features)
            self.active_algo.draw()

            pygame.display.flip()
            self.clock.tick(self.fps)
            self.framecount += 1

    def process_audio(self, samples):
        pitch = int(self.pDetection(samples)[0])
        abs_values = np.abs(samples)*100
        volume = int(np.max(abs_values))#self.normalize_volume(abs_values))
        windowed_data = samples * self.hann_window(self.CHUNK)
        fft = np.fft.fft(windowed_data)
        amps = np.abs(fft)
        return {
                "fft": fft,
                "amps": amps,
                "pitch": pitch,
                "volume": volume,
        }

    def update_config(self, startup=False):
        with open('config.txt', 'r') as f:
            new_checksum = md5(f.read().encode()).hexdigest()
            if self.settings_checksum:
                if new_checksum == self.settings_checksum:
                    return
            self.settings_checksum = new_checksum
        try:
            temp = {}
            settings = {}
            with open('config.txt', 'r') as f:
                i = 0
                for setting in f.readlines():
                    setting = setting.strip()
                    if setting != '' and setting[0] != '#':
                        temp[i] = setting.lower()
                        i += 1
            settings['active_algo'] = temp[0]
            settings['color_scheme'] = temp[1]
            settings['volume_sensitivity'] = int(temp[2])
            self.settings = settings
            if not startup:
                self.get_algo()
            if temp[1].count(",") == 2:
                self.color = tuple([int(i) for i in temp[1].split(",")])
                self.settings["color_scheme"] = self.color
        except Exception as e:
            print(e)
            windll.user32.MessageBoxW(0, u"Unable to load settings."
                                    " config.txt may be formatted incorrectly"
                                    " or is missing.", u"Error", 0)
            sys.exit()

    def get_algo(self):
        valid_algos = [
            "pitch_spikes",
            "blackhole",
            "soundwaves",
            #"perlinfield",
            #"spirograph",
            "freq_spikes"
        ]
        algo = self.settings["active_algo"]
        if algo in valid_algos:
            self.active_algo = self.algos[algo]

    def hann_window(self, length):
        return 0.5 * (1 - np.cos(2 * np.pi * np.arange(length) / (length - 1)))

    def normalize_volume(self, audio_array):
        current_max_amp = int(np.max(audio_array))
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