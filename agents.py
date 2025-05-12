import audio
import numpy as np

# Agent types
EMPTY, VERTICAL_REFLECT, HORIZONTAL_REFLECT = 0, 1, 2
ROBOT, CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR = 3, 4, 6
BELL_0 = 10
DJ = 20
DOWNSTAIRS = 30
UPSTAIRS = 31

DIRECTIONS = {
    "UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)
}

STATIC_AGENTS = {
    EMPTY,
    VERTICAL_REFLECT, HORIZONTAL_REFLECT,
    CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR,
    BELL_0,
    DOWNSTAIRS, UPSTAIRS
}


class BaseAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        raise NotImplementedError


class MovingAgent(BaseAgent):
    def __init__(self, agent_type):
        self.agent_type = agent_type
        self.directions = {}
        self.speeds = {}
        self.counters = {}

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

            dir = self.directions.get((r, c), 'RIGHT')  # Default to RIGHT
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
        audio.play_tone(attr['pitch'], attr['duration'], attr.get('velocity', 100), [1.0])


class RobotAgent(MovingAgent):
    def __init__(self):
        super().__init__(ROBOT)


class DJAgent(MovingAgent):
    def __init__(self):
        super().__init__(DJ)


class StaticAgent(BaseAgent):
    def apply_rules(self, static_grid, dynamic_grid):
        return static_grid


AGENTS = [RobotAgent(), DJAgent(), StaticAgent()]
