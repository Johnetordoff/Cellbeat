import sys
import numpy as np
import subprocess

# Constants for agent types
EMPTY = 0
VERTICAL_REFLECT = 1
HORIZONTAL_REFLECT = 2
ROBOT = 3
CLOCKWISE_ROTATOR = 4
BELL = 5
COUNTERCLOCKWISE_ROTATOR = 6

STATIC_AGENTS = {VERTICAL_REFLECT, HORIZONTAL_REFLECT, CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR, BELL}

DIRECTIONS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1)
}

class BaseAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        raise NotImplementedError

class RobotAgent(BaseAgent):
    def __init__(self):
        self.directions = {}

    def apply_rules(self, static_grid, dynamic_grid):
        rows, cols = dynamic_grid.shape
        robot_positions = np.argwhere(dynamic_grid == ROBOT)
        new_dynamic_grid = np.zeros_like(dynamic_grid)

        for r, c in robot_positions:
            direction = self.directions.get((r, c), DIRECTIONS["RIGHT"])
            nr, nc = (r + direction[0]) % rows, (c + direction[1]) % cols

            # Process static cell effects without altering static grid
            cell = static_grid[nr, nc]
            new_direction = self.process_cell_effects(direction, cell)

            # Play bell sound if robot steps onto a bell
            if cell == BELL:
                self.play_bell_sound()

            # Update robot's new position and direction
            new_dynamic_grid[nr, nc] = ROBOT
            self.directions[(nr, nc)] = new_direction

        return new_dynamic_grid

    def process_cell_effects(self, direction, cell):
        if cell == VERTICAL_REFLECT:
            return (direction[0], -direction[1])
        elif cell == HORIZONTAL_REFLECT:
            return (-direction[0], direction[1])
        elif cell == CLOCKWISE_ROTATOR:
            return (-direction[1], direction[0])
        elif cell == COUNTERCLOCKWISE_ROTATOR:
            return (direction[1], -direction[0])
        return direction

    @staticmethod
    def play_bell_sound():
        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["afplay", "assets/audio/bell_sound.wav"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith("linux"):
                subprocess.Popen(["aplay", "assets/audio/bell_sound.wav"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith("win"):
                subprocess.Popen(["start", "assets/audio/bell_sound.wav"],
                                 shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("Warning: Sound file not found or playback command failed.")

# Static agents don't need rules since they never change
class StaticAgent(BaseAgent):
    def apply_rules(self, static_grid, dynamic_grid):
        return static_grid

AGENTS = [RobotAgent(), StaticAgent()]
