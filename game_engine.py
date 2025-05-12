import os
import json
import numpy as np
from uuid import uuid4

from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.label import Label

import audio
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

import agents
from recorder import Recorder

SAVED_TOOLS_PATH = 'saved_tools.json'
ALL_STATIC_AGENTS = agents.STATIC_AGENTS.union(agents.STATIC_AGENTS)


class ToolButton(ButtonBehavior, BoxLayout):
    def __init__(self, tool_data, select_callback, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.tool_data = tool_data
        self.select_callback = select_callback
        self.size_hint = (None, None)
        self.size = (50, 50)
        self.opacity = 0.5
        self.padding = 5
        self.spacing = 0

        if tool_data.get('icon_unicode'):
            # Unicode icon: use Label
            self.label = Label(
                text=tool_data['icon_unicode'],
                font_size=24,
                halign='center',
                valign='middle'
            )
            self.label.bind(size=self.label.setter('text_size'))
            self.add_widget(self.label)
        else:
            # Image icon
            self.image = Image(
                source=tool_data['icon'],
                allow_stretch=True,
                keep_ratio=True
            )
            self.add_widget(self.image)

        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)  # transparent
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_press(self):
        self.select_callback(self.tool_data)


class ToolSelection(GridLayout):
    def __init__(self, tools, select_callback, **kwargs):
        super().__init__(
            cols=30,
            spacing=5,
            padding=5,
            size_hint=(None, None),
            **kwargs
        )
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
            btn.opacity = 0.5
        if tool_id in self.buttons:
            self.buttons[tool_id].opacity = 1
        self.select_callback(tool_data)


class NoteConfigurator(Popup):
    def __init__(self, on_place, on_save_tool, **kwargs):
        super().__init__(
            title="Set Pitch, Duration, Velocity",
            size_hint=(0.7, 0.8),
            **kwargs
        )

        self.on_place = on_place
        self.on_save_tool = on_save_tool
        self.selected_pitch = 440.0
        self.selected_duration = 0.5
        self.selected_velocity = 100

        self.char_spinner = Spinner(
            text='Choose Icon',
            values=['Ω', '≈', 'å', '√', '∫'],
            size_hint=(1, 1),
            height=40
        )

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
        layout.add_widget(self.char_spinner)

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
            'icon_unicode': self.char_spinner.text.strip() or None,
            'icon': self.char_spinner.text if self.char_spinner.text else '🎵'
        }

        def save_tool_config(tool_data):
            def load_saved_tools():
                if os.path.exists(SAVED_TOOLS_PATH):
                    with open(SAVED_TOOLS_PATH, 'r') as f:
                        return json.load(f)
                return []

            tools = load_saved_tools()
            tools.append(tool_data)
            with open(SAVED_TOOLS_PATH, 'w') as f:
                json.dump(tools, f, indent=2)

        save_tool_config(tool_data)
        self.on_save_tool(tool_data)
        self.dismiss()

    def play_sample(self, _):
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

    def update_image(self, agent_type):
        self.image.source = self.grid.image_sources.get(
            agent_type, self.grid.image_sources[agents.EMPTY]
        )

    def on_press(self):
        selected_type = self.grid.selected_type

        if selected_type == 10:  # Bell agent
            self.prompt_pitch_duration(selected_type)
        elif selected_type == agents.ROBOT:
            self.prompt_robot_speed()
        else:
            if isinstance(selected_type, str):
                tool_data = next((t for t in self.grid.app.saved_tools if t['id'] == selected_type), None)
                if tool_data:
                    self.grid.set_agent_at(
                        self.row, self.col,
                        agent_type=10,
                        pitch=tool_data['pitch'],
                        duration=tool_data['duration']
                    )
                    self.update_image(10)  # Update immediately after placement
            else:
                self.grid.set_agent_at(self.row, self.col, selected_type)
                self.update_image(selected_type)  # Immediate visual update

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

        speed_label = Label(text='Robot Speed: Quarter Note', size_hint_y=None, height=30)
        direction_spinner = Spinner(
            text='RIGHT',
            values=['UP', 'DOWN', 'LEFT', 'RIGHT'],
            size_hint_y=None,
            height=40
        )

        # Map from speed value to musical note name
        speed_labels = {
            1: "Whole Note",
            2: "Half Note",
            4: "Quarter Note",
            8: "Eighth Note",
            16: "Sixteenth Note"
        }

        speed_slider = Slider(min=1, max=16, step=1, value=4, size_hint_y=None, height=40)

        def update_speed_label(instance, value):
            val = int(value)
            # Snap to nearest valid musical speed
            closest = min(speed_labels.keys(), key=lambda k: abs(k - val))
            speed_slider.value = closest
            speed_label.text = f"Robot Speed: {speed_labels[closest]}"

        speed_slider.bind(value=update_speed_label)

        place_button = Button(text="Place Robot", size_hint_y=None, height=40)

        def place_robot(_):
            speed = int(speed_slider.value)
            direction = direction_spinner.text
            self.grid.set_agent_at(self.row, self.col, agents.ROBOT, speed=speed)
            self.grid.robot_agent.directions[(self.row, self.col)] = agents.DIRECTIONS[direction]
            popup.dismiss()

        place_button.bind(on_press=place_robot)

        content.add_widget(Label(text="Initial Direction:", size_hint_y=None, height=30))
        content.add_widget(direction_spinner)
        content.add_widget(speed_label)
        content.add_widget(speed_slider)
        content.add_widget(place_button)

        popup = Popup(title="Configure Robot", content=content, size_hint=(0.5, 0.5))
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
    def __init__(self, rows=20, cols=20, emoji_label=None, **kwargs):
        self.emoji_label = emoji_label or "😀"  # set before super().__init__
        super().__init__(rows=rows, cols=cols, **kwargs)
        self.rows = rows
        self.cols = cols
        self.cell_attributes = {
            (r, c): {
                'agent_type': agents.EMPTY,
                'pitch': 440.0,
                'duration': 0.5
            }
            for r in range(rows) for c in range(cols)
        }
        self.static_grid = np.zeros((rows, cols), dtype=int)
        self.dynamic_grid = np.zeros((rows, cols), dtype=int)
        self.robot_agent = agents.RobotAgent()
        self.running = False
        self.selected_type = agents.EMPTY

        self.image_sources = {10: f"assets/images/tone_0.png"}
        self.image_sources.update({
            agents.ROBOT: "assets/robot.png",
            agents.EMPTY: "assets/empty.png"
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
                cell.image.source = self.image_sources.get(val, self.image_sources[agents.EMPTY])
                attr = self.cell_attributes[(r, c)]
                if attr['agent_type'] == 10:
                    cell.update_dot(attr['pitch'], attr['duration'])

    def update_grid(self, dt=None):
        if not self.running:
            return
        self.dynamic_grid = self.robot_agent.apply_rules(self.static_grid, self.dynamic_grid, self.cell_attributes)
        self.refresh_cells()

    def set_agent_at(self, r, c, agent_type, pitch=440.0, duration=0.5, speed=1):
        attr = self.cell_attributes[(r, c)]
        attr['agent_type'] = agent_type
        attr['pitch'] = pitch
        attr['duration'] = duration

        if agent_type == agents.EMPTY:
            attr['pitch'] = 0
            attr['duration'] = 0

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
            'static_grid': self.static_grid.tolist(),
            'dynamic_grid': self.dynamic_grid.tolist(),
            'cell_attributes': {
                f"{r},{c}": attr
                for (r, c), attr in self.cell_attributes.items()
            }
        }

    def update(self, dt=None):
        if not self.running:
            return
        self.dynamic_grid = self.robot_agent.apply_rules(
            self.static_grid, self.dynamic_grid, self.cell_attributes
        )
        self.refresh_cells()


class CellularAutomataApp(App):
    def __init__(self, **kwargs):
        self.grids = []
        super().__init__(**kwargs)
        # List of all SimulationGrid instances
        self.recorder = Recorder(self.grids)
        # Index of the currently active grid in the list
        self.current_index = 0

    def toggle_recording(self, instance):
        if not self.recorder.recording:
            self.recorder.start_recording()
            self.recorder.grids = self.grids
            self.prompt_filename()
            instance.text = "Stop"
        else:
            self.recorder.stop_recording()
            instance.text = "Record"

    def prompt_filename(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        filename_input = TextInput(text='session.json', multiline=False)
        save_button = Button(text='Save')

        def do_save(_):
            name = filename_input.text.strip()
            if not name.endswith('.json'):
                name += '.json'
            self.recorder.save_json(name)
            popup.dismiss()

        layout.add_widget(Label(text='Enter filename:'))
        layout.add_widget(filename_input)
        layout.add_widget(save_button)
        save_button.bind(on_press=do_save)

        popup = Popup(title='Save Recording', content=layout, size_hint=(0.5, 0.3))
        popup.open()

    def build_top_controls(self):
        layout = BoxLayout(size_hint_y=None, height=50)

        layout.add_widget(
            Button(text="Start", on_press=lambda _: setattr(self.grids[self.current_index], 'running', True)))
        layout.add_widget(
            Button(text="Stop", on_press=lambda _: setattr(self.grids[self.current_index], 'running', False)))
        layout.add_widget(Button(text="Reset", on_press=self.grid_reset))
        layout.add_widget(Button(text="Record", on_press=self.toggle_recording))
        layout.add_widget(Button(text="Load Playback", on_press=self.load_playback))

        config_btn = Button(text="?")
        config_btn.bind(on_press=self.open_configurator)
        layout.add_widget(config_btn)

        self.bpm_label = Label(text='Tempo: 120 BPM', size_hint_x=0.3)
        self.bpm_slider = Slider(min=1, max=300, value=120, step=1)
        self.bpm_slider.bind(value=self.update_bpm)

        layout.add_widget(self.bpm_label)
        layout.add_widget(self.bpm_slider)

        return layout

    def open_configurator(self, _=None):
        NoteConfigurator(
            on_place=self.place_note,
            on_save_tool=self.add_saved_tool
        ).open()

    def place_note(self, pitch, duration, velocity):
        print(f"Placing note: pitch={pitch}, duration={duration}, velocity={velocity}")
        # Optional: apply to grid immediately or show message

    def add_saved_tool(self, tool_data):
        self.saved_tools.append(tool_data)
        self.tool_selection.refresh_tools(self.built_in_tools + self.saved_tools)

    def update_bpm(self, instance, value):
        bpm = int(value)
        self.bpm_label.text = f'Tempo: {bpm} BPM'
        interval = 60.0 / 4.0 / bpm  # assuming 16th-note step
        Clock.unschedule(self.update_all_grids)
        Clock.schedule_interval(self.update_all_grids, interval)

    def load_playback(self, instance=None):
        chooser = FileChooserIconView(path=os.getcwd(), filters=['*.json'])
        chooser.bind(on_submit=self.load_selection)
        popup = Popup(title="Load Grid File", content=chooser, size_hint=(0.9, 0.9))
        self.load_popup = popup  # Save reference to popup
        popup.open()

    def load_selection(self, filechooser_instance, selection, touch):
        try:
            with open(selection[0], 'r') as f:
                data = json.load(f)
            if 'grids' in data:
                self.load_all_grids(data['grids'])
        except Exception as e:
            print(f"Error loading grids: {e}")

        # Properly dismiss the Popup
        if hasattr(self, 'load_popup'):
            self.load_popup.dismiss()
            del self.load_popup

    def load_all_grids(self, grids_data):
        # Clear existing grids and UI
        self.content_area.clear_widgets()
        self.toggle_container.clear_widgets()
        self.grids.clear()
        self.grid_toggles.clear()

        for grid_data in grids_data:
            emoji_label = grid_data.get('emoji', '😀')
            new_grid = SimulationGrid(emoji_label=emoji_label)
            new_grid.app = self
            self.grids.append(new_grid)

            # Load grid data
            new_grid.static_grid = np.array(grid_data['static_grid'])
            new_grid.dynamic_grid = np.array(grid_data['dynamic_grid'])

            loaded_attrs = {
                tuple(map(int, k.split(','))): v
                for k, v in grid_data['cell_attributes'].items()
            }

            # First initialize attributes for all cells
            for r in range(new_grid.rows):
                for c in range(new_grid.cols):
                    new_grid.cell_attributes[(r, c)] = {
                        'agent_type': agents.EMPTY,
                        'pitch': 440.0,
                        'duration': 0.5
                    }

            # Update initialized attributes with loaded values
            for key, val in loaded_attrs.items():
                new_grid.cell_attributes[key] = val

            idx = len(self.grids) - 1
            toggle = ToggleButton(
                text=new_grid.emoji_label,
                group="grids",
                allow_no_selection=False,
                size_hint_x=None,
                width=40
            )
            toggle.bind(on_release=lambda instance, idx=idx: self.switch_to_grid(idx))
            self.toggle_container.add_widget(toggle)
            self.grid_toggles.append(toggle)

        # Ensure first grid is shown and refreshed properly after adding to UI
        Clock.schedule_once(lambda dt: self.switch_to_grid(0), 0)
        Clock.schedule_once(lambda dt: self.grids[0].refresh_cells(), 0.1)

        def finish_grid_initialization(dt):
            self.switch_to_grid(0)
            self.grids[0].refresh_cells()
            self.grid_toggles[0].state = 'down'

        Clock.schedule_once(finish_grid_initialization, 0)

    def build_grid_toolbar(self):
        layout = BoxLayout(size_hint_y=None, height=40)

        self.toggle_container = BoxLayout(orientation='horizontal', size_hint_x=1)
        layout.add_widget(self.toggle_container)

        add_btn = Button(text="Add", size_hint_x=1)
        remove_btn = Button(text="Remove", size_hint_x=1)

        add_btn.bind(on_press=lambda _: self.add_grid())
        remove_btn.bind(on_press=lambda _: self.remove_current_grid())

        self.remove_btn = remove_btn  # store reference so we can disable later

        layout.add_widget(add_btn)
        layout.add_widget(remove_btn)

        return layout

    def add_grid_toggle(self, grid, index):
        toggle = ToggleButton(
            text=grid.emoji_label,
            group="grids",
            allow_no_selection=False,
            size_hint_x=None,
            width=40
        )
        toggle.bind(on_release=lambda instance: self.switch_to_grid(index))
        self.toggle_container.add_widget(toggle)
        self.grid_toggles.append(toggle)
        toggle.state = 'down'

    def get_builtin_tools(self):
        return [
            {'id': agents.EMPTY, 'icon': 'assets/empty.png'},
            {'id': agents.ROBOT, 'icon': 'assets/robot.png'},
            {'id': agents.VERTICAL_REFLECT, 'icon': 'assets/horizontal_reflector.png'},
            {'id': agents.HORIZONTAL_REFLECT, 'icon': 'assets/vertical_reflector.png'},
            {'id': agents.CLOCKWISE_ROTATOR, 'icon': 'assets/rotator.png'},
            {'id': agents.COUNTERCLOCKWISE_ROTATOR, 'icon': 'assets/counter_rotator.png'},
        ]

    def tool_selected(self, tool_data):
        # Set selected_type on the active grid
        self.grids[self.current_index].selected_type = tool_data['id']

    def load_saved_tools(self):
        if os.path.exists(SAVED_TOOLS_PATH):
            try:
                with open(SAVED_TOOLS_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load saved tools: {e}")
        return []

    def build(self):
        # Create the outermost vertical layout
        root = BoxLayout(orientation='vertical')

        # 🟦 1. Top row controls (Start, Stop, Reset, Record, Config, BPM)
        self.top_controls = self.build_top_controls()
        root.add_widget(self.top_controls)

        # 🟦 2. Emoji grid toggle toolbar (Add/Remove/Save + ToggleButtons)
        self.grid_toolbar = self.build_grid_toolbar()
        root.add_widget(self.grid_toolbar)

        # 🟦 4. Grid container area (displays current grid)
        self.content_area = BoxLayout(size_hint=(1, 1), orientation='vertical')
        root.add_widget(self.content_area)

        # 🟩 5. Initial grid setup
        first_emoji = chr(0x1F600)
        first_grid = SimulationGrid(emoji_label=first_emoji)
        first_grid.app = self
        self.grids = [first_grid]
        self.grid_toggles = []
        self.current_index = 0
        self.add_grid_toggle(first_grid, index=0)
        self.content_area.add_widget(first_grid)

        # 🟦 6. Saved Tool selector at the bottom (South of grid)
        self.saved_tools = self.load_saved_tools()
        self.built_in_tools = self.get_builtin_tools()
        self.tool_selection = ToolSelection(
            self.built_in_tools + self.saved_tools,
            self.tool_selected
        )
        bottom_bar = BoxLayout(size_hint_y=None, height=120)
        bottom_bar.add_widget(self.tool_selection)
        root.add_widget(bottom_bar)

        # 🟨 6. Start simulation loop
        Clock.schedule_interval(self.update_all_grids, 0.1)

        return root

    def grid_reset(self, _=None):
        grid = self.grids[self.current_index]
        grid.static_grid.fill(agents.EMPTY)
        grid.dynamic_grid.fill(agents.EMPTY)
        for attr in grid.cell_attributes.values():
            attr['agent_type'] = agents.EMPTY
            attr['pitch'] = 440.0
            attr['duration'] = 0.5
        grid.refresh_cells()

    def switch_to_grid(self, index):
        if index == self.current_index and self.grids[index].parent:
            return

        if self.grids[self.current_index].parent:
            self.content_area.remove_widget(self.grids[self.current_index])

        grid = self.grids[index]
        self.content_area.add_widget(grid)
        self.current_index = index

        for i, toggle in enumerate(self.grid_toggles):
            toggle.state = 'down' if i == index else 'normal'

        # Schedule refresh after layout pass
        Clock.schedule_once(lambda dt: grid.refresh_cells(), 0)

    def add_grid(self):
        """Add a new simulation grid (up to 108 total) and switch to it."""
        if len(self.grids) >= 108:
            return  # Max limit reached; do nothing or show a warning.
        # Determine an emoji label for the new grid
        next_idx = len(self.grids)
        # Example: use emoticon Unicode sequence starting from 0x1F600
        emoji_codepoint = 0x1F600 + (next_idx % 80)  # cycle after 80 emojis
        new_emoji = chr(emoji_codepoint)
        # Create the new SimulationGrid
        new_grid = SimulationGrid(emoji_label=new_emoji)
        new_grid.app = self
        self.grids.append(new_grid)
        # Create a toggle button for the new grid
        new_toggle = ToggleButton(text=new_emoji, group="grids",
                                  allow_no_selection=False,
                                  size_hint_x=None, width=40)
        # Bind the toggle to switch to the new grid's index
        new_toggle.bind(on_release=lambda instance, idx=next_idx: self.switch_to_grid(idx))
        self.toggle_container.add_widget(new_toggle)
        self.grid_toggles.append(new_toggle)
        # Enable the remove button now that we have more than one grid
        # (Find the remove button via toolbar children or store a reference)
        # Here we assume btn_remove is stored or accessible; for clarity, not shown storing it
        # Example if we stored it: self.btn_remove.disabled = False
        # [In this code snippet, one could store btn_remove as self.btn_remove above for toggling disabled state.]
        # Immediately switch to the new grid
        self.switch_to_grid(next_idx)
        # Set the new toggle as down (the switch_to_grid call will handle the visuals)
        new_toggle.state = 'down'
        # If needed, update disabled state of remove button
        # (There is definitely more than one grid now)
        # self.btn_remove.disabled = False

    def remove_current_grid(self):
        """Remove the currently active grid, if more than one grid exists."""
        if len(self.grids) <= 1:
            return  # Don't remove the last grid
        idx_to_remove = self.current_index
        # Remove the grid widget from the content area (if it's active)
        grid_to_remove = self.grids[idx_to_remove]
        if grid_to_remove.parent:
            self.content_area.remove_widget(grid_to_remove)
        # Unschedule its updates if needed (not needed in global loop scenario)
        # Clock.unschedule(grid_to_remove.update)  # only if individual scheduling was used
        # Remove from the list of grids
        self.grids.pop(idx_to_remove)
        # Remove and destroy its toggle button
        toggle_to_remove = self.grid_toggles.pop(idx_to_remove)
        self.toggle_container.remove_widget(toggle_to_remove)
        # Adjust current_index to point to a valid grid
        if idx_to_remove >= len(self.grids):
            # If we removed the last grid, show the new last grid
            self.current_index = len(self.grids) - 1
        else:
            # Otherwise, the grid that shifted into this index becomes current
            self.current_index = idx_to_remove
        # Switch display to the new current grid
        new_index = self.current_index
        new_grid_widget = self.grids[new_index]
        new_grid_widget.size_hint = (1, 1)
        if not new_grid_widget.parent:
            self.content_area.add_widget(new_grid_widget)
        # Update toggle states: mark the new current index as down
        for i, toggle in enumerate(self.grid_toggles):
            toggle.state = 'down' if i == new_index else 'normal'
        # If only one grid remains now, disable the remove button
        # if len(self.grids) == 1:
        #     self.btn_remove.disabled = True

    def update_all_grids(self, dt):
        """Update all simulation grids (called on each clock tick)."""
        for grid in self.grids:
            grid.update()


if __name__ == '__main__':
    CellularAutomataApp().run()
