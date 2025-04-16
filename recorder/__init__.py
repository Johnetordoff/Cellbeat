# recorder.py
import json
import numpy as np
import audio  # C extension for audio playback/recording

class Recorder:
    def __init__(self, simulation_grid, sample_rate=44100):
        self.grid = simulation_grid
        self.recording = False
        self.frames = []
        self.audio_events = []
        self.playback_index = 0
        self.fps = 10
        self.filename = "simulation_recording.json"
        self.sample_rate = sample_rate

    def start_recording(self, filename="simulation_recording.json"):
        self.frames.clear()
        if self.audio_events:
            self.audio_events.clear()
        self.recording = True
        self.filename = filename
        audio.start_recording(self.filename.replace('.json', '.wav'))
        print(f"Recording started: {self.filename}")

    def stop_recording(self):
        self.recording = False
        audio.stop_recording()
        self.save_json(self.filename)
        print(f"Recording stopped and saved: {self.filename}")

    def record_frame(self):
        directions = {f"{k[0]}_{k[1]}": v for k, v in self.grid.robot_agent.directions.items()}
        self.frames.append({
            "static": self.grid.static_grid.tolist(),
            "dynamic": self.grid.dynamic_grid.tolist(),
            "directions": directions
        })

    def save_json(self, filename):
        with open(filename, 'w') as f:
            json.dump({"frames": self.frames, "audio_events": self.audio_events}, f)

    def load_json(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        self.frames = data["frames"]
        self.audio_events = data.get("audio_events")
        self.playback_index = 0

    def playback_step(self, dt):
        from kivy.clock import Clock  # Import locally to avoid tight coupling

        if self.playback_index >= len(self.frames):
            Clock.unschedule(self.playback_step)
            print("Playback finished.")
            return

        frame = self.frames[self.playback_index]
        self.grid.static_grid = np.array(frame["static"])
        self.grid.dynamic_grid = np.array(frame["dynamic"])
        directions = {tuple(map(int, k.split('_'))): v for k, v in frame["directions"].items()}
        self.grid.robot_agent.directions = directions
        self.grid.refresh_cells()
        self.playback_index += 1

    def start_playback(self):
        from kivy.clock import Clock
        Clock.schedule_interval(self.playback_step, 1 / self.fps)
