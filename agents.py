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

# Movement directions
DIRECTIONS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1)
}

STATIC_AGENTS = {VERTICAL_REFLECT, HORIZONTAL_REFLECT, CLOCKWISE_ROTATOR, COUNTERCLOCKWISE_ROTATOR, BELL}

class BaseAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        raise NotImplementedError

class RobotAgent(BaseAgent):
    agent_type = ROBOT

    def __init__(self):
        self.directions = {}  # track directions of each robot individually

    def apply_rules(self, static_grid, dynamic_grid):
        rows, cols = static_grid.shape
        new_dynamic_grid = np.zeros_like(dynamic_grid)

        robot_positions = np.argwhere(dynamic_grid == ROBOT)

        new_directions = {}

        for r, c in robot_positions:
            direction = self.directions.get((r, c), DIRECTIONS["RIGHT"])
            nr, nc = (r + direction[0]) % rows, (c + direction[1]) % cols

            cell = static_grid[nr, nc]

            # Handle reflector and rotator interactions
            if cell == VERTICAL_REFLECT:
                direction = (direction[0], -direction[1])
            elif cell == HORIZONTAL_REFLECT:
                direction = (-direction[0], direction[1])
            elif cell == CLOCKWISE_ROTATOR:
                direction = (-direction[1], direction[0])
            elif cell == COUNTERCLOCKWISE_ROTATOR:
                direction = (direction[1], -direction[0])

            # Check for bell and play sound
            if cell == BELL:
                self.play_bell_sound()

            # Move robot in the new direction
            nr, nc = (r + direction[0]) % rows, (c + direction[1]) % cols

            new_dynamic_grid[nr, nc] = ROBOT
            new_directions[(nr, nc)] = direction

        self.directions = new_directions
        return new_dynamic_grid

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
class StaticAgent:
    def apply_rules(self, static_grid, dynamic_grid):
        return static_grid


AGENTS = [RobotAgent(), StaticAgent()]
