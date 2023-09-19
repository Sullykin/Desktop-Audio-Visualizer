import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from ctypes import windll
import time
import os

SETTING_SCHEMA = {
    "active_visualizer": {"type": str, "valid_values": ["blackhole", "soundwaves", "freq_spikes", "particle_field"]},
    "color_scheme": {"type": str, "valid_values": ["fade", "static"]},
    "static_color": {"type": list, "length": 3, "tuple_range": [(0, 255), (0, 255), (0, 255)]},
    "fade_cycle": {"type": str, "valid_values": ["rainbow", "rgb", "warm", "cool"]},
    "fade_speed": {"type": int, "range": (1, 50)},
    "volume_sensitivity": {"type": int, "range": (0, 100)},
    "keep_topmost": {"type": bool},
    "freq_spikes": {
        "type": dict,
        "sub_keys": {
            "mirror_x": {"type": bool},
            "mirror_y": {"type": bool},
            "invert_x_mirror": {"type": bool},
            "invert_y_mirror": {"type": bool},
            "bins": {"type": int, "range": (10, 400)}
        }
    },
    "blackhole": {
        "type": dict,
        "sub_keys": {
            "disk_particles": {"type": int, "range": (500, 8000)},
            "inner_disk_radius": {"type": int, "range": (100, 300)},
            "outer_disk_radius": {"type": int, "range": (350, 1000)}
        }
    },
    "particle_field": {
        "type": dict,
        "sub_keys": {
            "grid_size": {"type": int, "range": (1, 3)},
            "zoom_factor": {"type": int, "range": (1, 10)},
            "edge_waves": {"type": bool},
            "radial_waves": {"type": bool}
        }
    }
}

class MyHandler(FileSystemEventHandler):
    def __init__(self, config_obj):
        self.config_obj = config_obj
        self.error_flag = False

    def process(self, event):
        if os.path.basename(event.src_path) == os.path.basename(self.config_obj.filepath):
            if not self.error_flag:  # skips the next trigger after thread resumes
                self.config_obj.load_from_file()
                #self.config_obj.visualizer.process_config_change()
            else:
                self.error_flag = False

    def on_modified(self, event):
        self.process(event)


class Config:
    def __init__(self, visualizer, filepath='config.json'):
        self.default_settings = {
            "active_visualizer": "freq_spikes",
            "color_scheme": "fade",
            "static_color": [120, 6, 225],
            "fade_cycle": "rainbow",
            "fade_speed": 3,
            "volume_sensitivity": 50,
            "keep_topmost": False,
            "freq_spikes": {
                "mirror_x": False,
                "mirror_y": False,
                "invert_x_mirror": False,
                "invert_y_mirror": False,
                "bins": 120
            },
            "blackhole": {
                "disk_particles": 3000,
                "inner_disk_radius": 130,
                "outer_disk_radius": 700
            },
            "particle_field": {
                "grid_size": 2,
                "zoom_factor": 4,
                "edge_waves": True,
                "radial_waves": True
            }
        }
        self.settings = self.default_settings.copy()
        self.visualizer = visualizer
        self.filepath = filepath

        # Watchdog setup
        self.event_handler = MyHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=os.path.dirname(os.path.abspath(self.filepath)), recursive=False)
        
        # Run observer in a separate thread
        self.observer_thread = Thread(target=self.observer.start)
        self.observer_thread.start()

        self.load_from_file(startup=True)

    def stop_observer(self):
        self.observer.stop()
        self.observer.join()

    def load_from_file(self, startup=False):
        try:
            with open(self.filepath, 'r') as f:
                try:
                    self.settings = json.load(f)
                    #print(f"Configuration loaded: {self.settings}")
                except json.JSONDecodeError as e:
                    self.settings = self.default_settings
                    windll.user32.MessageBoxW(0, f"Config validation failed (continuing with default settings). Reason: {e}", u"Error", 0)
                    #print(f"Failed to load configuration: {e}")
        except FileNotFoundError as e:
            windll.user32.MessageBoxW(0, f"Config file not found. {e}", u"Error", 0)

        errors = self.validate_settings(self.settings, SETTING_SCHEMA)
        if errors:
            self.event_handler.error_flag = True
            self.settings = self.default_settings
            windll.user32.MessageBoxW(0, f"Config validation failed (continuing with default settings). Reason: {errors[0]}", u"Error", 0)

        self.visualizer.settings = self.settings
        if not startup:
            self.visualizer.set_visualizer()
            self.visualizer.process_config_change()

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def validate_settings(self, settings, schema, prefix=''):
        errors = []
        for key, rule in schema.items():
            full_key = f"{prefix}.{key}" if prefix else key  # For better error messages

            # Check if the key exists in the settings
            if key not in settings:
                errors.append(f"Missing key: '{full_key}'")
                continue  # Skip to the next iteration, no point in validating this key

            value = settings[key]
            expected_type = rule.get("type")

            # Check if the type matches
            if not isinstance(value, expected_type):
                errors.append(f"Invalid type for '{full_key}'. Expected {expected_type}, got {type(value)}")
                return errors

            # Check against a list of valid values
            if "valid_values" in rule and value not in rule["valid_values"]:
                errors.append(f"Invalid value for '{full_key}'. Must be one of {rule['valid_values']}")

            if expected_type == list:
                if "length" in rule and len(value) != rule["length"]:
                    errors.append(f"Invalid length for '{full_key}'. Expected length {rule['length']}, got {len(value)}")

                if "tuple_range" in rule:
                    for i, (min_val, max_val) in enumerate(rule["tuple_range"]):
                        if not (min_val <= value[i] <= max_val):
                            errors.append(f"Invalid value for '{full_key}[{i}]'. Must be between {min_val} and {max_val}")

            # Check against a range
            if "range" in rule:
                min_val, max_val = rule["range"]
                if not (min_val <= value <= max_val):
                    errors.append(f"Invalid value for '{full_key}'. Must be between {min_val} and {max_val}")

            # Validate sub-keys if it's a dictionary
            if "sub_keys" in rule and isinstance(value, dict):
                sub_errors = self.validate_settings(value, rule["sub_keys"], full_key)
                errors.extend(sub_errors)

        return errors

if __name__ == "__main__":
    config = Config()
