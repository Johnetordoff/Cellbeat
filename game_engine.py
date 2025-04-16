import json
import os
from uuid import uuid4
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import numpy as np

SAVED_TOOLS_PATH = 'saved_tools.json'

def load_saved_tools():
    if os.path.exists(SAVED_TOOLS_PATH):
        with open(SAVED_TOOLS_PATH, 'r') as f:
            return json.load(f)
    return []

def save_tool_config(tool_data):
    tools = load_saved_tools()
    tools.append(tool_data)
    with open(SAVED_TOOLS_PATH, 'w') as f:
        json.dump(tools, f, indent=2)


class ToolButton(ButtonBehavior, Image):
    def __init__(self, tool_data, select_callback, **kwargs):
        super().__init__(**kwargs)
        self.tool_data = tool_data
        self.source = tool_data['icon']
        self.select_callback = select_callback
        self.size_hint = (None, None)
        self.size = (50, 50)
        self.opacity = 0.25

    def on_press(self):
        self.select_callback(self.tool_data)


class ToolSelection(GridLayout):
    def __init__(self, tools, select_callback, **kwargs):
        super().__init__(cols=30, spacing=5, padding=5, size_hint=(None, None), **kwargs)
        self.buttons = {}
        self.select_callback = select_callback
        self.refresh_tools(tools)

    def refresh_tools(self, tools):
        self.clear_widgets()
        self.buttons.clear()
        for tool_data in tools:
            tool_id = tool_data['id']
            btn = ToolButton(tool_data, self.select_tool)
            self.buttons[tool_id] = btn
            self.add_widget(btn)

    def select_tool(self, tool_data):
        tool_id = tool_data['id']
        for btn in self.buttons.values():
            btn.opacity = 0.25
        if tool_id in self.buttons:
            self.buttons[tool_id].opacity = 1
        self.select_callback(tool_data)


class NoteConfigurator(Popup):
    def __init__(self, on_place, on_save_tool, **kwargs):
        super().__init__(title="Set Pitch, Duration, Velocity", size_hint=(0.7, 0.8), **kwargs)

        self.on_place = on_place
        self.on_save_tool = on_save_tool
        self.selected_pitch = 440.0
        self.selected_duration = 0.5
        self.selected_velocity = 100

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.pitch_label = Label(text='Pitch: 440 Hz')
        self.duration_label = Label(text='Duration: 0.5 s')
        self.velocity_label = Label(text='Velocity: 100')

        selector = self.TwoDAxisSelector(self)

        self.velocity_slider = Slider(min=0, max=127, value=100, step=1)
        self.velocity_slider.bind(value=self.on_velocity_change)

        sample_button = Button(text="Play Sample")
        place_button = Button(text="Place Bell")
        save_button = Button(text="Save as Tool")

        sample_button.bind(on_press=self.play_sample)
        place_button.bind(on_press=self.place)
        save_button.bind(on_press=self.save_tool)

        layout.add_widget(self.pitch_label)
        layout.add_widget(self.duration_label)
        layout.add_widget(selector)
        layout.add_widget(self.velocity_label)
        layout.add_widget(self.velocity_slider)
        layout.add_widget(sample_button)
        layout.add_widget(place_button)
        layout.add_widget(save_button)

        self.content = layout

    def on_velocity_change(self, instance, value):
        self.selected_velocity = int(value)
        self.velocity_label.text = f'Velocity: {int(value)}'

    def place(self, _):
        self.on_place(self.selected_pitch, self.selected_duration, self.selected_velocity)
        self.dismiss()

    def save_tool(self, _):
        tool_data = {
            'id': str(uuid4()),
            'pitch': self.selected_pitch,
            'duration': self.selected_duration,
            'velocity': self.selected_velocity,
            'icon': 'assets/images/tone_0.png'
        }
        save_tool_config(tool_data)
        self.on_save_tool(tool_data)
        self.dismiss()

    def play_sample(self, _):
        import audio
        audio.play_tone(self.selected_pitch, self.selected_duration, self.selected_velocity, [1.0])

    class TwoDAxisSelector(FloatLayout):
        def __init__(self, parent, **kwargs):
            super().__init__(**kwargs)
            self.parent_popup = parent
            with self.canvas:
                Color(0.95, 0.95, 0.95)
                self.bg = Rectangle(pos=self.pos, size=self.size)
                Color(0.2, 0.6, 1)
                self.crosshair = Ellipse(size=(12, 12), pos=(0, 0))
            self.bind(pos=self.update_canvas, size=self.update_canvas)

        def update_canvas(self, *args):
            self.bg.pos = self.pos
            self.bg.size = self.size

        def on_touch_down(self, touch):
            if self.collide_point(*touch.pos):
                self.update_selection(touch.pos)
                return True
            return super().on_touch_down(touch)

        def on_touch_move(self, touch):
            if self.collide_point(*touch.pos):
                self.update_selection(touch.pos)
                return True
            return super().on_touch_move(touch)

        def update_selection(self, pos):
            rel_x = (pos[0] - self.x) / self.width
            rel_y = (pos[1] - self.y) / self.height
            rel_x = max(0, min(1, rel_x))
            rel_y = max(0, min(1, rel_y))
            duration = 0.1 + rel_x * (2.0 - 0.1)
            pitch = 100 + rel_y * (2000 - 100)

            self.parent_popup.selected_pitch = pitch
            self.parent_popup.selected_duration = duration

            self.crosshair.pos = (
                self.x + rel_x * self.width - 6,
                self.y + rel_y * self.height - 6
            )
            self.parent_popup.pitch_label.text = f"Pitch: {pitch:.1f} Hz"
            self.parent_popup.duration_label.text = f"Duration: {duration:.2f} s"

import os
import numpy as np
from kivy.core.window import Window
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from recorder import Recorder
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Line

from agents import (
    EMPTY, ROBOT, VERTICAL_REFLECT, HORIZONTAL_REFLECT,
    COUNTERCLOCKWISE_ROTATOR, CLOCKWISE_ROTATOR,
    STATIC_AGENTS, NOISE_AGENT, RobotAgent
)

VOCAL_AGENT = NOISE_AGENT + 1
STATIC_AGENTS = STATIC_AGENTS.union({VOCAL_AGENT})
ALL_STATIC_AGENTS = STATIC_AGENTS.union(STATIC_AGENTS)

class Cell(ButtonBehavior, BoxLayout):
    def __init__(self, grid, row, col, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.grid = grid
        self.row = row
        self.col = col

        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)  # Transparent by default
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

        self.image = Image(source="assets/empty.png", allow_stretch=True, keep_ratio=False, size_hint=(1, 1))
        self.add_widget(self.image)

        Clock.schedule_interval(self.update_hover, 0.1)

    def update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_hover(self, dt):
        mouse_x, mouse_y = Window.mouse_pos
        if self.collide_point(mouse_x, mouse_y):
            self.bg_color.rgba = (0.8, 0.9, 1, 0.5)  # Light blueish tint
            self.image.opacity = 0.8
        else:
            self.bg_color.rgba = (1, 1, 1, 0)  # Transparent
            self.image.opacity = 1.0

    def on_press(self):
        selected_type = self.grid.selected_type

        if selected_type == 10:  # Bell agent
            self.prompt_pitch_duration(selected_type)
        elif selected_type == ROBOT:
            self.prompt_robot_speed()
        else:
            if isinstance(selected_type, str):
                # Assume it's a saved bell tool UUID
                tool_data = next((t for t in self.grid.app.saved_tools if t['id'] == selected_type), None)
                if tool_data:
                    self.grid.set_agent_at(
                        self.row, self.col,
                        agent_type=10,
                        pitch=tool_data['pitch'],
                        duration=tool_data['duration']
                    )
            else:
                self.grid.set_agent_at(self.row, self.col, selected_type)


    def update_dot(self, pitch, duration):
        if pitch and duration:
            normalized_pitch = (pitch - 100) / (2000 - 100)
            normalized_duration = (duration - 0.1) / (2.0 - 0.1)
            x = normalized_duration * self.width + self.x
            y = normalized_pitch * self.height + self.y
            self.image.canvas.after.clear()
            with self.image.canvas.after:
                Color(1, 0, 0)
                Ellipse(pos=(x, y), size=(10, 10))

    def prompt_robot_speed(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)

        speed_label = Label(text='Robot Speed: 1', size_hint_y=None, height=30)
        speed_slider = Slider(min=1, max=10, value=1, step=1, size_hint_y=None, height=40)

        def on_slider_value(instance, value):
            speed_label.text = f'Robot Speed: {int(value)}'

        speed_slider.bind(value=on_slider_value)

        place_button = Button(text="Place Robot", size_hint_y=None, height=40)

        def place_robot(_):
            speed = int(speed_slider.value)
            self.grid.set_agent_at(self.row, self.col, ROBOT, speed=speed)
            popup.dismiss()

        place_button.bind(on_press=place_robot)

        content.add_widget(speed_label)
        content.add_widget(speed_slider)
        content.add_widget(place_button)

        popup = Popup(title="Set Robot Speed", content=content, size_hint=(0.5, 0.4))
        popup.open()


    def prompt_pitch_duration(self, agent_type):
        class TwoDAxisSelector(FloatLayout):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                with self.canvas:
                    Color(0.95, 0.95, 0.95)
                    self.bg = Rectangle(pos=self.pos, size=self.size)
                    Color(0.2, 0.6, 1)
                    self.crosshair = Ellipse(size=(12, 12), pos=(0, 0))
                self.bind(pos=self.update_canvas, size=self.update_canvas)

            def update_canvas(self, *args):
                self.bg.pos = self.pos
                self.bg.size = self.size

            def on_touch_down(self, touch):
                if self.collide_point(*touch.pos):
                    self.update_selection(touch.pos)
                    return True
                return super().on_touch_down(touch)

            def on_touch_move(self, touch):
                if self.collide_point(*touch.pos):
                    self.update_selection(touch.pos)
                    return True
                return super().on_touch_move(touch)

            def update_selection(self, pos):
                # Convert pos to relative
                rel_x = (pos[0] - self.x) / self.width
                rel_y = (pos[1] - self.y) / self.height

                # Clamp values
                rel_x = max(0, min(1, rel_x))
                rel_y = max(0, min(1, rel_y))

                duration = 0.1 + rel_x * (2.0 - 0.1)
                pitch = 100 + rel_y * (2000 - 100)

                self.crosshair.pos = (
                    self.x + rel_x * self.width - 6,
                    self.y + rel_y * self.height - 6
                )

                pitch_label.text = f"Pitch: {pitch:.1f} Hz"
                duration_label.text = f"Duration: {duration:.2f} s"

                self.selected_pitch = pitch
                self.selected_duration = duration

        pitch_label = Label(text='Pitch: --- Hz', size_hint_y=None, height=30)
        duration_label = Label(text='Duration: --- s', size_hint_y=None, height=30)

        selector = TwoDAxisSelector(size_hint=(1, 1))
        selector.selected_pitch = 440.0
        selector.selected_duration = 0.5

        place_button = Button(text="Place Bell", size_hint_y=None, height=40)
        sample_button = Button(text="Play Sample", size_hint_y=None, height=40)

        def place_bell(_):
            pitch = selector.selected_pitch
            duration = selector.selected_duration
            self.grid.set_agent_at(self.row, self.col, agent_type, pitch, duration)
            popup.dismiss()

        def play_sample(_):
            pitch = selector.selected_pitch
            duration = selector.selected_duration
            import audio
            audio.play_tone(pitch, duration, 100, [1.0])

        place_button.bind(on_press=place_bell)
        sample_button.bind(on_press=play_sample)

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        layout.add_widget(pitch_label)
        layout.add_widget(duration_label)
        layout.add_widget(selector)
        layout.add_widget(place_button)
        layout.add_widget(sample_button)

        popup = Popup(title="Set Pitch & Duration", content=layout, size_hint=(0.7, 0.7))
        popup.open()


class SimulationGrid(GridLayout):
    def __init__(self, rows=20, cols=20, **kwargs):
        super().__init__(rows=rows, cols=cols, spacing=1, padding=1, **kwargs)
        self.rows = rows
        self.cols = cols
        self.cell_attributes = {(r, c): {'agent_type': EMPTY, 'pitch': 440.0, 'duration': 0.5}
                                for r in range(rows) for c in range(cols)}
        self.static_grid = np.zeros((rows, cols), dtype=int)
        self.dynamic_grid = np.zeros((rows, cols), dtype=int)
        self.robot_agent = RobotAgent()
        self.recorder = Recorder(self)
        self.running = False
        self.selected_type = EMPTY

        self.image_sources = {10: f"assets/images/tone_0.png"}
        self.image_sources.update({
            EMPTY: "assets/empty.png",
            ROBOT: "assets/robot.png"
        })

        self.cell_widgets = []
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                cell = Cell(self, r, c)
                self.add_widget(cell)
                row_cells.append(cell)
            self.cell_widgets.append(row_cells)

    def refresh_cells(self):
        for r in range(self.rows):
            for c in range(self.cols):
                val = self.dynamic_grid[r, c] or self.static_grid[r, c]
                cell = self.cell_widgets[r][c]
                cell.image.source = self.image_sources.get(val, self.image_sources[EMPTY])
                attr = self.cell_attributes[(r, c)]
                if attr['agent_type'] in [10,]:
                    cell.update_dot(attr['pitch'], attr['duration'])

    def update_grid(self, dt=None):
        if not self.running:
            return
        self.dynamic_grid = self.robot_agent.apply_rules(self.static_grid, self.dynamic_grid, self.cell_attributes)
        self.refresh_cells()
        if self.recorder.recording:
            self.recorder.record_frame()

    def set_agent_at(self, r, c, agent_type, pitch=440.0, duration=0.5, speed=1):
        attr = self.cell_attributes[(r, c)]
        attr['agent_type'] = agent_type
        attr['pitch'] = pitch
        attr['duration'] = duration

        if agent_type == EMPTY:
            attr['pitch'] = 0
            attr['duration'] = 0

        if agent_type == ROBOT:
            self.dynamic_grid[r, c] = ROBOT
            self.static_grid[r, c] = EMPTY
            self.robot_agent.speeds[(r, c)] = speed
            self.robot_agent.counters[(r, c)] = 0
        else:
            self.static_grid[r, c] = agent_type
            self.dynamic_grid[r, c] = EMPTY
            self.robot_agent.speeds.pop((r, c), None)
            self.robot_agent.counters.pop((r, c), None)

        self.refresh_cells()


class CellularAutomataApp(App):
    def open_configurator(self, _):
        NoteConfigurator(
            on_place=self.place_note,
            on_save_tool=self.add_saved_tool
        ).open()

    def place_note(self, pitch, duration, velocity):
        print(f"Placing note: pitch={pitch}, duration={duration}, velocity={velocity}")

    def add_saved_tool(self, tool_data):
        self.saved_tools.append(tool_data)
        self.tool_selection.refresh_tools(self.saved_tools + self.built_in_tools)

    def tool_selected(self, tool_data):
        self.grid.selected_type = tool_data['id']

    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.grid = SimulationGrid()
        self.grid.app = self
        additional_tools = {
            VERTICAL_REFLECT: "assets/horizontal_reflector.png",
            HORIZONTAL_REFLECT: "assets/vertical_reflector.png",
            CLOCKWISE_ROTATOR: "assets/rotator.png",
            COUNTERCLOCKWISE_ROTATOR: "assets/counter_rotator.png",
            NOISE_AGENT: "assets/noise_agent.png",
            VOCAL_AGENT: "assets/vocal_agent.png",
        }

        self.grid.image_sources.update(additional_tools)

        controls = BoxLayout(size_hint_y=None, height=90, orientation='vertical')

        top_controls = BoxLayout(size_hint_y=None, height=50)
        top_controls.add_widget(Button(text="Start", on_press=lambda _: setattr(self.grid, 'running', True)))
        top_controls.add_widget(Button(text="Stop", on_press=lambda _: setattr(self.grid, 'running', False)))
        top_controls.add_widget(Button(text="Reset", on_press=self.grid_reset))
        top_controls.add_widget(Button(text="Record", on_press=self.toggle_recording))
        top_controls.add_widget(Button(text="Load Playback", on_press=self.load_playback))

        config_btn = Button(text="√")
        config_btn.bind(on_press=self.open_configurator)
        top_controls.add_widget(config_btn)

        bpm_controls = BoxLayout(size_hint_y=None, height=40)
        self.bpm_label = Label(text='Tempo: 120 BPM', size_hint_x=0.3)
        self.bpm_slider = Slider(min=1, max=300, value=120, step=1)
        self.bpm_slider.bind(value=self.update_bpm)

        bpm_controls.add_widget(self.bpm_label)
        bpm_controls.add_widget(self.bpm_slider)

        controls.add_widget(top_controls)
        controls.add_widget(bpm_controls)

        layout.add_widget(controls)
        layout.add_widget(self.grid)

        self.grid_update_event = Clock.schedule_interval(lambda dt: self.grid.update_grid(), 1)

        self.saved_tools = load_saved_tools()
        self.built_in_tools = [
            {'id': ROBOT, 'icon': 'assets/robot.png'},
            {'id': VERTICAL_REFLECT, 'icon': 'assets/horizontal_reflector.png'},
            {'id': HORIZONTAL_REFLECT, 'icon': 'assets/vertical_reflector.png'},
            {'id': CLOCKWISE_ROTATOR, 'icon': 'assets/rotator.png'},
            {'id': COUNTERCLOCKWISE_ROTATOR, 'icon': 'assets/counter_rotator.png'},
            {'id': NOISE_AGENT, 'icon': 'assets/noise_agent.png'},
            {'id': VOCAL_AGENT, 'icon': 'assets/vocal_agent.png'},
        ]

        self.tool_selection = ToolSelection(self.built_in_tools + self.saved_tools, self.tool_selected)
        tool_scroll = ScrollView(size_hint_y=None, height=120)
        tool_scroll.add_widget(self.tool_selection)

        layout.add_widget(tool_scroll)

        return layout

    def update_bpm(self, instance, value):
        self.current_bpm = int(value)
        self.bpm_label.text = f'Tempo: {self.current_bpm} BPM'
        self.grid_update_event.cancel()
        self.grid.recorder.bpm = self.current_bpm
        self.grid_update_event = Clock.schedule_interval(
            lambda dt: self.grid.update_grid(),
            60.0 / 4.0 / float(self.current_bpm)
        )

    def select_tool(self, tool_id):
        self.grid.selected_type = tool_id

    def toggle_recording(self, instance):
        if not self.grid.recorder.recording:
            self.prompt_recording_name(instance)
        else:
            self.grid.recorder.stop_recording()
            instance.text = "Record"

    def prompt_recording_name(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        filename_input = TextInput(text='new_recording.json', multiline=False, size_hint_y=None, height=40)
        save_button = Button(text="Start Recording", size_hint_y=None, height=40)

        def start_recording(_):
            filename = filename_input.text.strip()
            if not filename.endswith('.json'):
                filename += '.json'
            self.grid.recorder.start_recording(filename)
            instance.text = "Stop Record"
            popup.dismiss()

        save_button.bind(on_press=start_recording)

        content.add_widget(filename_input)
        content.add_widget(save_button)

        popup = Popup(title="Save Recording As", content=content, size_hint=(0.6, 0.3))
        popup.open()

    def grid_reset(self, _):
        self.grid.static_grid.fill(EMPTY)
        self.grid.dynamic_grid.fill(EMPTY)
        self.grid.refresh_cells()

    def load_playback(self, _):
        filechooser = FileChooserIconView(path=os.getcwd(), filters=['*.json'])
        popup = Popup(title="Load Recording", content=filechooser, size_hint=(0.9, 0.9))

        def load_selection(fc, selection, touch=None):
            if selection:
                self.grid.recorder.load_json(selection[0])
                self.grid.recorder.start_playback()
                popup.dismiss()

        filechooser.bind(on_submit=load_selection)
        popup.open()


if __name__ == '__main__':
    CellularAutomataApp().run()
