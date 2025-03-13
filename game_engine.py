import numpy as np
import importlib
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
import agents


class ToolButton(ButtonBehavior, Image):
    def __init__(self, tool_id, image_source, callback, **kwargs):
        super().__init__(**kwargs)
        self.tool_id = tool_id
        self.source = image_source
        self.callback = callback
        self.size_hint = (None, None)
        self.size = (50, 50)

    def on_press(self):
        self.callback(self.tool_id)


class ToolSelection(GridLayout):
    def __init__(self, image_sources, on_tool_selected, **kwargs):
        super().__init__(**kwargs)
        self.cols = len(image_sources)
        self.spacing = 10
        self.size_hint_y = None
        self.height = 60

        self.tool_buttons = {}
        self.on_tool_selected = on_tool_selected

        for tool_id,  image_source in image_sources.items():
            btn = ToolButton(tool_id, image_source, self.select_tool)
            btn.opacity = 0.5
            self.tool_buttons[tool_id] = btn
            self.add_widget(btn)

    def select_tool(self, tool_id):
        for btn in self.tool_buttons.values():
            btn.opacity = 0.5
        self.tool_buttons[tool_id].opacity = 1
        self.on_tool_selected(tool_id)


class Cell(ButtonBehavior, Image):
    """A single cell in the simulation grid."""

    def __init__(self, grid, row, col, **kwargs):
        super().__init__(**kwargs)
        self.grid = grid
        self.row = row
        self.col = col
        self.source = "assets/empty.png"
        self.original_source = self.source
        self.is_hovered = False

        Clock.schedule_interval(self.update_hover, 0.1)

    def update_hover(self, dt):
        mouse_x, mouse_y = Window.mouse_pos
        if self.collide_point(mouse_x, mouse_y):
            if not self.is_hovered:
                self.is_hovered = True
                self.grid.set_hovered_cell(self)
        elif self.is_hovered:
            self.is_hovered = False
            self.grid.clear_hovered_cell(self)

    def on_press(self, *args):
        r, c = self.row, self.col
        self.grid.set_agent_at(r, c, self.grid.selected_type)

    def update_source(self):
        r, c = self.row, self.col
        self.source = self.grid.image_sources[self.grid.cells[r, c]][1]


from agents import EMPTY, VERTICAL_REFLECT, HORIZONTAL_REFLECT, ROBOT, CLOCKWISE_ROTATOR, BELL, COUNTERCLOCKWISE_ROTATOR, STATIC_AGENTS, RobotAgent

class SimulationGrid(GridLayout):
    def __init__(self, rows=20, cols=20, **kwargs):
        super().__init__(**kwargs)
        self.rows = rows
        self.cols = cols
        self.static_grid = np.zeros((rows, cols), dtype=int)
        self.dynamic_grid = np.zeros((rows, cols), dtype=int)

        self.selected_type = EMPTY
        self.running = False

        self.image_sources = {
            EMPTY: "assets/empty.png",
            VERTICAL_REFLECT: "assets/horizontal_reflector.png",
            HORIZONTAL_REFLECT: "assets/vertical_reflector.png",
            ROBOT: "assets/robot.png",
            CLOCKWISE_ROTATOR: "assets/rotator.png",
            BELL: "assets/bell.png",
            COUNTERCLOCKWISE_ROTATOR: "assets/counter_rotator.png",
        }

        self.cell_widgets = []
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                cell = Cell(self, r, c)
                self.add_widget(cell)
                row_cells.append(cell)
            self.cell_widgets.append(row_cells)

        self.robot_agent = RobotAgent()

    def update_grid(self, dt):
        if not self.running:
            return

        self.dynamic_grid = self.robot_agent.apply_rules(self.static_grid, self.dynamic_grid)
        self.refresh_cells()

    def refresh_cells(self):
        for r in range(self.rows):
            for c in range(self.cols):
                dynamic_val = self.dynamic_grid[r, c]
                static_val = self.static_grid[r, c]

                if dynamic_val == ROBOT:
                    img_source = self.image_sources[ROBOT]
                elif static_val in STATIC_AGENTS:
                    img_source = self.image_sources[static_val]
                else:
                    img_source = self.image_sources[EMPTY]

                self.cell_widgets[r][c].source = img_source

    def set_agent_at(self, r, c, agent_type):
        if agent_type == ROBOT:
            self.dynamic_grid[r, c] = ROBOT
            self.static_grid[r, c] = EMPTY
        elif agent_type in STATIC_AGENTS:
            self.static_grid[r, c] = agent_type
            self.dynamic_grid[r, c] = EMPTY
        else:
            self.static_grid[r, c] = EMPTY
            self.dynamic_grid[r, c] = EMPTY
        self.refresh_cells()

    def set_hovered_cell(self, cell):
        if hasattr(self, 'hovered_cell') and self.hovered_cell != cell:
            r, c = self.hovered_cell.row, self.hovered_cell.col
            dynamic_val = self.dynamic_grid[r, c]
            static_val = self.static_grid[r, c]
            self.hovered_cell.source = self.image_sources.get(dynamic_val or static_val, self.image_sources[EMPTY])

        self.hovered_cell = cell
        cell.source = self.image_sources[self.selected_type]

    def clear_hovered_cell(self, cell):
        if hasattr(self, 'hovered_cell') and self.hovered_cell == cell:
            r, c = cell.row, cell.col
            dynamic_val = self.dynamic_grid[r, c]
            static_val = self.static_grid[r, c]
            cell.source = self.image_sources.get(dynamic_val or static_val, self.image_sources[EMPTY])
            del self.hovered_cell

    def start(self, *_):
        self.running = True

    def stop(self, *_):
        self.running = False

    def reset(self, *_):
        self.static_grid.fill(EMPTY)
        self.dynamic_grid.fill(EMPTY)
        self.refresh_cells()

    def rewind(self, *_):
        self.reset()

    def on_key_down(self, _, __, keycode, ___, ____):
        if keycode == 44:  # Spacebar
            self.running = not self.running

    def load_agents(self):
        importlib.reload(agents)
        self.agent_instances = [Agent() for Agent in agents.AGENTS]


class CellularAutomataApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.grid = SimulationGrid()

        tools = ToolSelection(self.grid.image_sources, self.select_tool)
        controls = BoxLayout(size_hint_y=None, height=50)

        buttons = [("Start", self.grid.start),
                   ("Stop", self.grid.stop),
                   ("Reset", self.grid.reset),
                   ("Rewind", self.grid.rewind)]

        for text, callback in buttons:
            controls.add_widget(Button(text=text, on_press=callback))

        layout.add_widget(tools)
        layout.add_widget(controls)
        layout.add_widget(self.grid)

        Clock.schedule_interval(self.grid.update_grid, 0.05)
        return layout

    def select_tool(self, tool_id):
        self.grid.selected_type = tool_id


if __name__ == '__main__':
    CellularAutomataApp().run()
