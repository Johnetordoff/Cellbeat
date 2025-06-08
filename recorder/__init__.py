import json
import numpy as np
import agents
import audio  # C extension for audio playback/recording

class Recorder:
    def __init__(self, grids, sample_rate=44100):
        self.grids = grids
        self.recording = False
        self.audio_events = []
        self.sample_rate = sample_rate
        self.filename = "simulation_recording.json"

    def start_recording(self, filename="simulation_recording.json"):
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

    def save_json(self, filename):
        all_grids_state = []
        for grid in self.grids:
            grid_state = {
                "emoji_label": grid.emoji_label,
                "bpm": getattr(grid, "bpm", 121),
                "static_grid": grid.static_grid.tolist(),
                "dynamic_grid": grid.dynamic_grid.tolist(),
                "directions": {
                    f"{k[0]}_{k[1]}": list(v)  # Save direction as list to preserve tuple
                    for k, v in grid.robot_agent.directions.items()
                },
                "speeds": {
                    f"{k[0]}_{k[1]}": v
                    for k, v in grid.robot_agent.speeds.items()
                },
                "counters": {
                    f"{k[0]}_{k[1]}": v
                    for k, v in grid.robot_agent.counters.items()
                },
                "cell_attributes": {
                    f"{r}_{c}": {
                        "agent_type": grid.cell_attributes.get((r, c), {}).get("agent_type",
                                                                               int(grid.static_grid[r, c])),
                        "pitch": grid.cell_attributes.get((r, c), {}).get("pitch", 440.0),
                        "duration": grid.cell_attributes.get((r, c), {}).get("duration", 0.5),
                        "velocity": grid.cell_attributes.get((r, c), {}).get("velocity", 100)
                    }
                    for r in range(grid.static_grid.shape[0])
                    for c in range(grid.static_grid.shape[1])
                }
            }
            all_grids_state.append(grid_state)

        full_state = {
            "grids": all_grids_state,
            "audio_events": self.audio_events
        }

        with open(filename, 'w') as f:
            json.dump(full_state, f, indent=2)

    def load_json(self, source):
        if isinstance(source, str):
            with open(source, 'r') as f:
                data = json.load(f)
        elif isinstance(source, dict):
            data = source
        else:
            raise TypeError(f"Unsupported type for load_json: {type(source)}")

        grids_data = data.get("grids", [])
        if len(grids_data) != len(self.grids):
            raise ValueError("Mismatch between saved grids and current grids")

        for grid, grid_data in zip(self.grids, grids_data):
            grid.static_grid = np.array(grid_data["static_grid"])
            grid.dynamic_grid = np.array(grid_data["dynamic_grid"])

            grid.robot_agent.directions = {
                tuple(map(int, k.split('_'))): agents.DIRECTIONS[v] if isinstance(v, str) else v
                for k, v in grid_data["directions"].items()
            }

            grid.robot_agent.speeds = {tuple(map(int, k.split('_'))): v for k, v in grid_data["speeds"].items()}
            grid.robot_agent.counters = {tuple(map(int, k.split('_'))): v for k, v in grid_data["counters"].items()}

            grid.cell_attributes = {}
            for k_str, v in grid_data["cell_attributes"].items():
                r, c = map(int, k_str.split('_'))
                grid.cell_attributes[(r, c)] = {
                    "agent_type": v.get("agent_type", agents.EMPTY),
                    "pitch": float(v.get("pitch", 440.0)),
                    "duration": float(v.get("duration", 0.5)),
                    "velocity": int(v.get("velocity", 100))
                }

            grid.refresh_cells()

        self.audio_events = data.get("audio_events", [])
