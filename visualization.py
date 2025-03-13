import numpy as np
from agents import Agents


def update_texture(state, mouse_pos=None, canvas_size=None):
    """Update the entire texture to visualize the game map."""
    game_mask = state["game_map"]
    res_x, res_y = game_mask.shape
    buf = np.zeros((res_x, res_y, 4), dtype=np.uint8)

    # Assign colors from the Cells class

    # Highlight the cell under the mouse
    if mouse_pos is not None and canvas_size is not None:
        # Calculate cell coordinates
        cell_size_x = canvas_size[0] / res_x
        cell_size_y = canvas_size[1] / res_y
        cell_x = int(mouse_pos[0] / cell_size_x)
        cell_y = int(mouse_pos[1] / cell_size_y)
        # Ensure the coordinates are within bounds
        if 0 <= cell_x < res_x and 0 <= cell_y < res_y:
            if state.get('tool_name'):
                agent = Agents.AGENT_SINGLES.get(state.get('tool_name').upper())
                if getattr(agent, 'color', None):
                    buf[cell_y - 1, cell_x] = list(agent.color) + [255]
                    buf[cell_y, cell_x - 1] = list(agent.color) + [255]
                    buf[cell_y, cell_x + 1] = list(agent.color) + [255]
                    buf[cell_y, cell_x] = list(agent.color) + [255]

    for key, type in Agents.AGENT_TYPES.items():
        value = Agents.AGENT_VALUES[key]
        if getattr(type, 'color', False) and value:
            buf[game_mask == value] = np.array(list(type.color) + [255])

    state["texture"].blit_buffer(
        buf.tobytes(), colorfmt="rgba", bufferfmt="ubyte", size=(res_x, res_y)
    )