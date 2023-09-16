import pygame
import pyaudiowpatch as pyaudio  # patched pyaudio for loopback capability
import aubio  # audio feature extraction
import numpy as np

import win32api, win32con, win32gui
import ctypes.wintypes
import threading
import os, sys
from screeninfo import get_monitors
from ctypes import windll
from queue import Queue

import visualizers.soundwaves as soundwaves
import visualizers.freq_spikes as freq_spikes
import visualizers.pitch_spikes as pitch_spikes
import visualizers.blackhole as blackhole
import visualizers.particle_field as particle_field
#import visualizers.spirograph as spirograph
#import visualizers.perlinfield as perlinfield
from color_manager import ColorFade
from config_manager import Config

# TODO
    # setup new beat detection
    # add frequency-based and amplitude-based color option
    # update soundwaves with vectorization

# PATCH NOTES
    # new visualizer
    # watchdog config / json
    # new options
    # performance
    # logarithmic freqs
    # improve color fade

class Visualizer:
    def __init__(self):
        self.color = (0,0,0)
        self.audio_queue = Queue()
        self.config = Config(self)
        self.setup_display()
        self.average_volume = None
        self.done = False
        self.dt = 0

    def set_visualizer(self):
        self.valid_visualizers = {
            "pitch_spikes": pitch_spikes.PitchSpikes(self),
            "blackhole": blackhole.BlackHole(self),
            "soundwaves": soundwaves.Soundwaves(self),
            #"perlinfield": perlinfield.PerlinField(self),
            #"spirograph": spirograph.Spirograph(self),
            "freq_spikes": freq_spikes.FreqSpikes(self),
            "particle_field": particle_field.ParticleField(self)
        }
        selected_visualizer = self.settings["active_visualizer"]
        self.active_visualizer = self.valid_visualizers[selected_visualizer]

    def setup_display(self):
        monitor = get_monitors()[0]
        self.SCREEN_WIDTH = monitor.width
        self.SCREEN_HEIGHT = monitor.height
        pygame.init()
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0, 0)
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT),pygame.NOFRAME)
        self.hwnd = pygame.display.get_wm_info()['window']
        self.keep_topmost()
        self.set_window_transparency()
        pygame.display.set_caption('Desktop Audio Visualizer')
        self.clock = pygame.time.Clock()
        self.fps = 60

    # FIXED with https://stackoverflow.com/questions/74589479/making-window-topmost-with-python-and-or-windows-api
    # Note: Cannot overlay fullscreen applications
    def keep_topmost(self):
        SetWindowPos = windll.user32.SetWindowPos
        NOSIZE = 1
        NOMOVE = 2
        TOPMOST = -1
        if self.settings['keep_topmost']:
            SetWindowPos(self.hwnd, ctypes.wintypes.HWND(TOPMOST), 0, 0, 0, 0, NOMOVE|NOSIZE)
        else:
            SetWindowPos(self.hwnd, 0, 0, 0, 0, 0)

    def set_window_transparency(self):
        self.fuchsia = (255, 0, 128)  # Transparency color
        lExStyle = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, lExStyle)
        win32gui.SetLayeredWindowAttributes(self.hwnd,
                                            win32api.RGB(*self.fuchsia), 0,
                                            win32con.LWA_COLORKEY)

    def setup_audio(self):
        self.RATE = 48000
        if self.settings["high_res_audio"]:
            self.CHUNK = 4096
        else:
            self.CHUNK = 2048
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.setup_pitch_detection()
        self.set_visualizer()

    def setup_pitch_detection(self):
        self.pDetection = aubio.pitch("schmitt", 8192, self.CHUNK, self.RATE)
        self.pDetection.set_unit("Hz")
        self.pDetection.set_silence(-40)

    def get_loopback_device(self, p):
        # Get default WASAPI speakers
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    self.RATE=int(default_speakers["defaultSampleRate"])
                    break
        
        return default_speakers

    def start(self):
        with pyaudio.PyAudio() as p:
            default_speakers = self.get_loopback_device(p)
            self.setup_audio()
            with p.open(format=self.FORMAT, 
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.CHUNK,
                        input_device_index=default_speakers["index"]
            ) as self.stream:
                self.main()

    def stop(self):
        self.audio_thread.join()
        self.config.stop_observer()

    def check_user_input(self):
        self.events = pygame.event.get()
        for event in self.events:
            if event.type == pygame.QUIT:
                self.done = True

    def update(self):
        # read in audio and calculate signal properties
        #print(self.audio_queue.qsize())
        if not self.audio_queue.empty():
            frame = self.audio_queue.get()
            samples = np.frombuffer(frame, dtype=aubio.float_type)
            audio_features = self.process_audio(samples)
            self.active_visualizer.update(audio_features)

    def draw(self):
        if self.color_scheme == "fade":
            self.color = self.colorfade.next()
        self.screen.fill(self.fuchsia)
        self.active_visualizer.draw()

    def send_frame(self):
        pygame.display.flip()
        self.dt = self.clock.tick(self.fps) / 1000.0
        #print(int(self.clock.get_fps()))

    def main(self):
        self.process_config_change()
        self.audio_thread = threading.Thread(target=self.read_audio)
        self.audio_thread.start()
        while not self.done:
            self.check_user_input()            
            self.update()
            self.draw()
            self.send_frame()

    def read_audio(self):
        while not self.done:
            frame = self.stream.read(self.CHUNK)
            self.audio_queue.put(frame)

    def process_audio(self, samples):
        pitch = self.pDetection(samples)[0]
        rms_volume = np.linalg.norm(samples) / np.sqrt(len(samples))
        #normalized_volume = self.normalize_volume(rms_volume)
        windowed_data = samples * self.hann_window(self.CHUNK)
        fft = np.fft.fft(windowed_data)
        amps = np.abs(fft)
        return {
                "fft": fft,
                "amps": amps,
                "pitch": pitch,
                "volume": rms_volume
        }

    def hann_window(self, length):
        return 0.5 * (1 - np.cos(2 * np.pi * np.arange(length) / (length - 1)))

    def normalize_volume(self, current_volume, alpha=0.5):
        if self.average_volume is None:
            self.average_volume = current_volume  # Initialize if it's the first sample
        else:
            # Update the average using EWMA
            self.average_volume = alpha * self.average_volume + (1 - alpha) * current_volume
        
        # Normalize the current volume
        normalized_volume = current_volume / self.average_volume if self.average_volume else 1
        return normalized_volume

    def process_config_change(self):
        self.sensitivity = self.settings["volume_sensitivity"]
        self.color_scheme = self.settings["color_scheme"]
        fade_cycle = self.settings["fade_cycle"]
        fade_speed = self.settings["fade_speed"]
        self.colorfade = ColorFade(fade_cycle, fade_speed)
        self.active_visualizer.update_settings()


if __name__ == "__main__":
    visualizer = Visualizer()
    visualizer.start()
    visualizer.stop()