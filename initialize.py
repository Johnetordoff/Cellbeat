from agents import Agents
import numpy as np
import random


def initialize_generic_state(state, height=30, width=30):
    """
    Initialize a generic game state.
    """
    # Set up a simple camera
    state["camera"] = {
        "position": np.array([50.0, 50.0], dtype=float),
    }

    Agents.load_from_config('config.json')
    # Initialize game_map with default EMPTY cells
    state["game_map"] = np.full((width, height), Agents.get("EMPTY").value, dtype=int)

    # Setup Robot on a path to hit Bells
    robot_positions = [(random.randint(0, width-1), random.randint(0, height-1)) for _ in range(50)]
    for x, y in robot_positions:
        state["game_map"][x, y] = Agents.get("ROBOT").value

    state["game_map"][width//2, height//2] = Agents.get("BELL").value
    state["game_map"][width//2 - 1, height//2] = Agents.get("PLAYER").value
    state["game_map"][width//2 + 1, height//2] = Agents.get("ROTATOR").value
    state["game_map"][width//2 + 2, height//2] = Agents.get("ROTATOR").value
    state["game_map"][width//2 + 3, height//2] = Agents.get("ROTATOR").value
    state["game_map"][width//2 + 4, height//2] = Agents.get("ROTATOR").value
    state['agent_values'] = Agents.AGENT_TYPES

    return state


def set_cell(game_map, x, y, cell_type):
    """
    Set a specific cell in the game_map to a value from the Cells class.
    """
    if not isinstance(cell_type, Agents):
        raise ValueError("Invalid cell type. Must be an instance of CellType.")

    game_map[x, y] = cell_type.value
