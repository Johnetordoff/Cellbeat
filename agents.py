import audio
import numpy as np

# Agent types
EMPTY, VERTICAL_REFLECT, HORIZONTAL_REFLECT = 0, 1, 2
ROBOT, CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR = 3, 4, 6
BELL_0 = 10
NOISE_AGENT = 11  # New agent type for noise!

# Movement directions
DIRECTIONS = {
    "UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)
}

STATIC_AGENTS = {
    VERTICAL_REFLECT, HORIZONTAL_REFLECT,
    CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR,
    BELL_0,
    NOISE_AGENT  # Include the noise agent in static agents
}

BELL_FREQUENCIES = [
    261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392.00, 415.30, 440.00,
    466.16, 493.88, 523.25, 554.37, 587.33, 622.25, 659.25, 698.46, 739.99, 783.99,
    830.61, 880.00, 932.33, 987.77, 1046.50, 1108.73, 1174.66, 1244.51, 1318.51, 1396.91
]

DEFAULT_NOISE_DURATION = .25  # Customize as needed!


class BaseAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        raise NotImplementedError


class RobotAgent(BaseAgent):
    # existing init and other methods remain
    def __init__(self):
        self.directions = {}
        self.speeds = {}  # Track speed per robot cell
        self.counters = {}  # Internal counters to control movement

    def apply_rules(self, static_grid, dynamic_grid, cell_attributes):
        rows, cols = static_grid.shape
        new_dynamic = np.zeros_like(dynamic_grid)
        new_dirs, new_speeds, new_counters = {}, {}, {}

        for r, c in np.argwhere(dynamic_grid == ROBOT):
            speed = self.speeds.get((r, c), 1)
            counter = self.counters.get((r, c), 0)

            if counter < speed - 1:
                new_dynamic[r, c] = ROBOT
                new_dirs[(r, c)] = self.directions.get((r, c), DIRECTIONS["RIGHT"])
                new_speeds[(r, c)] = speed
                new_counters[(r, c)] = counter + 1
                continue

            new_counters[(r, c)] = 0
            dir = self.directions.get((r, c), DIRECTIONS["RIGHT"])
            nr, nc = (r + dir[0]) % rows, (c + dir[1]) % cols
            cell = static_grid[nr, nc]

            if cell == VERTICAL_REFLECT:
                dir = (dir[0], -dir[1])
            elif cell == HORIZONTAL_REFLECT:
                dir = (-dir[0], dir[1])
            elif cell == CLOCKWISE_ROTATOR:
                dir = (-dir[1], dir[0])
            elif cell == COUNTERCLOCKWISE_ROTATOR:
                dir = (dir[1], -dir[0])

            final_r, final_c = (r + dir[0]) % rows, (c + dir[1]) % cols
            final_cell = static_grid[final_r, final_c]

            new_dynamic[final_r, final_c] = ROBOT
            new_dirs[(final_r, final_c)] = dir
            new_speeds[(final_r, final_c)] = speed
            new_counters[(final_r, final_c)] = 0

            if final_cell:
                self.play_tone(final_r, final_c, cell_attributes)

        self.directions, self.speeds, self.counters = new_dirs, new_speeds, new_counters
        return new_dynamic

    def play_tone(self, r, c, cell_attributes):
        attr = cell_attributes.get((r, c), {'pitch': 440.0, 'duration': 0.5, 'velocity': 100})
        freq, duration, velocity = attr['pitch'], attr['duration'], attr.get('velocity', 100)
        audio.play_tone(freq, duration, velocity, [1.0])


class StaticAgent(BaseAgent):
    def apply_rules(self, static_grid, dynamic_grid):
        return static_grid

AGENTS = [RobotAgent(), StaticAgent()]
