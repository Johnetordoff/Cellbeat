# grid.py
from typing import Dict, Tuple, Any
import numpy as np
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout

import agents
from constants import BELL
from ui.cell import Cell

def parse_coord_key(k) -> Tuple[int, int]:
    """Accept 'r,c', 'r_c', 'r c', ['r','c'], (r,c) with str/int parts."""
    if isinstance(k, (list, tuple)) and len(k) == 2:
        r, c = k
        return int(r), int(c)
    if isinstance(k, str):
        if ',' in k:
            parts = k.split(',', 1)
        elif '_' in k:
            parts = k.split('_', 1)
        elif ' ' in k:
            parts = k.split(' ', 1)
        else:
            raise ValueError(f"Bad coord key: {k!r}")
        return int(parts[0]), int(parts[1])
    raise ValueError(f"Bad coord key type: {type(k).__name__}")

def safe_items(d):
    return d.items() if isinstance(d, dict) else []


class SimulationGrid(GridLayout):
    def __init__(self, rows=20, cols=20, emoji_label=None, bpm=120, **kwargs):
        self.emoji_label = emoji_label or 'å'
        self.bpm = bpm

        super().__init__(rows=rows, cols=cols, **kwargs)

        self.rows = rows
        self.cols = cols
        self.volume = 1.0  # 0.0 .. 2.0 (200%)
        self._clock_ev = None  # per-grid Clock event
        self.cell_attributes: Dict[Tuple[int, int], Dict[str, Any]] = {
            (r, c): {
                'agent_type': agents.EMPTY,
                'pitch': 440.0,
                'duration': 0.5,
                'velocity': 100,
            }
            for r in range(rows) for c in range(cols)
        }

        self._store_volume_meta()
        self._reschedule_tick()

        self.static_grid = np.zeros((rows, cols), dtype=int)
        self.dynamic_grid = np.zeros((rows, cols), dtype=int)
        self.robot_agent = agents.RobotAgent()
        self.running = False
        self.selected_type = agents.EMPTY

        self.image_sources = {
            BELL: "assets/images/tone_0.png",
            agents.ROBOT: "assets/robot.png",
            agents.EMPTY: "assets/empty.png",
            agents.VERTICAL_REFLECT: "assets/horizontal_reflector.png",
            agents.HORIZONTAL_REFLECT: "assets/vertical_reflector.png",
            agents.CLOCKWISE_ROTATOR: "assets/rotator.png",
            agents.COUNTERCLOCKWISE_ROTATOR: "assets/counter_rotator.png",
        }

        self.cell_widgets = []
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                cell = Cell(self, r, c)
                self.add_widget(cell)
                row_cells.append(cell)
            self.cell_widgets.append(row_cells)

    def _store_volume_meta(self):
        # Sentinel meta entry read by agents.MovingAgent.play_tone()
        self.cell_attributes[(-1, -1)] = {'grid_volume': float(self.volume)}

    def set_volume(self, vol: float):
        self.volume = max(0.0, min(2.0, float(vol)))
        self._store_volume_meta()

    def seconds_per_tick(self) -> float:
        # 16th-note tick
        return 60.0 / (float(self.bpm) * 4.0)

    def _reschedule_tick(self):
        if self._clock_ev:
            Clock.unschedule(self._clock_ev)
        # Schedule this grid's own update loop
        self._clock_ev = Clock.schedule_interval(self.update, self.seconds_per_tick())

    def set_bpm(self, bpm: int):
        self.bpm = int(max(1, min(300, bpm)))
        self._reschedule_tick()

    def refresh_cells(self):
        for r in range(self.rows):
            for c in range(self.cols):
                val = self.dynamic_grid[r, c] or self.static_grid[r, c]
                cell = self.cell_widgets[r][c]
                cell.image.source = self.image_sources.get(val, self.image_sources[agents.EMPTY])
                attr = self.cell_attributes[(r, c)]
                if val:
                    cell.update_dot(attr['pitch'], attr['duration'])

    def update_grid(self, dt=None):
        if not self.running:
            return
        self.dynamic_grid = self.robot_agent.apply_rules(self.static_grid, self.dynamic_grid, self.cell_attributes)
        self.refresh_cells()

    def set_agent_at(self, r, c, agent_type, pitch=440.0, duration=0.5, velocity=100, speed=1):
        attr = self.cell_attributes[(r, c)]
        attr['agent_type'] = agent_type
        attr['pitch'] = pitch
        attr['duration'] = duration
        attr['velocity'] = velocity

        if agent_type == agents.EMPTY:
            attr['pitch'] = 0.0
            attr['duration'] = 0.0
            attr['velocity'] = 0

        if agent_type == agents.ROBOT:
            self.dynamic_grid[r, c] = agents.ROBOT
            self.static_grid[r, c] = agents.EMPTY
            self.robot_agent.speeds[(r, c)] = speed
            self.robot_agent.counters[(r, c)] = 0
        else:
            self.static_grid[r, c] = agent_type
            self.dynamic_grid[r, c] = agents.EMPTY
            self.robot_agent.speeds.pop((r, c), None)
            self.robot_agent.counters.pop((r, c), None)

        self.refresh_cells()

    def get_state(self):
        return {
            'emoji': self.emoji_label,
            'bpm': self.bpm,
            'volume': self.volume,
            'static_grid': self.static_grid.tolist(),
            'dynamic_grid': self.dynamic_grid.tolist(),
            'cell_attributes': {
                f"{r},{c}": attr
                for (r, c), attr in self.cell_attributes.items()
            },
            'directions': {f"{r}_{c}": v for (r, c), v in self.robot_agent.directions.items()},
            'speeds': {f"{r}_{c}": v for (r, c), v in self.robot_agent.speeds.items()},
            'counters': {f"{r}_{c}": v for (r, c), v in self.robot_agent.counters.items()},
        }

    def update(self, dt=None):
        if not self.running:
            return
        self.dynamic_grid = self.robot_agent.apply_rules(
            self.static_grid, self.dynamic_grid, self.cell_attributes
        )
        self.refresh_cells()
