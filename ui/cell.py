# ui/cell.py
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Ellipse, Rectangle

import audio
import agents
from constants import BELL
from ui.fonts import FKW, UniSpinnerOption

class Cell(ButtonBehavior, BoxLayout):
    def __init__(self, grid, row, col, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.grid = grid
        self.row = row
        self.col = col

        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

        self.image = Image(source="assets/empty.png", size_hint=(1, 1))
        self.add_widget(self.image)

        Clock.schedule_interval(self.update_hover, 0.1)

    def update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_hover(self, dt):
        mouse_x, mouse_y = Window.mouse_pos
        if self.collide_point(mouse_x, mouse_y):
            self.bg_color.rgba = (0.8, 0.9, 1, 0.5)
            self.image.opacity = 0.8
        else:
            self.bg_color.rgba = (1, 1, 1, 0)
            self.image.opacity = 1.0

    def update_image(self, agent_type):
        self.image.source = self.grid.image_sources.get(
            agent_type, self.grid.image_sources[agents.EMPTY]
        )

    def on_press(self):
        selected_type = self.grid.selected_type

        if selected_type == BELL:
            bell = getattr(self.grid.app, 'current_bell', None)
            if bell:
                self.grid.set_agent_at(
                    self.row, self.col, BELL,
                    pitch=bell['pitch'],
                    duration=bell['duration'],
                    velocity=bell.get('velocity', 100),
                )
                self.update_image(BELL)
            else:
                self.prompt_pitch_duration(selected_type)
            return
        elif selected_type == agents.ROBOT:
            self.prompt_robot_speed()
            return
        else:
            if isinstance(selected_type, str):
                tool_data = next((t for t in self.grid.app.saved_tools if t['id'] == selected_type), None)
                if tool_data:
                    self.grid.set_agent_at(
                        self.row, self.col,
                        agent_type=BELL,
                        pitch=tool_data['pitch'],
                        duration=tool_data['duration'],
                        velocity=tool_data.get('velocity', 100),
                    )
                    self.update_image(BELL)
            else:
                self.grid.set_agent_at(self.row, self.col, selected_type)
                self.update_image(selected_type)

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

        speed_label = Label(text='Robot Speed: Quarter Note', size_hint_y=None, height=30, **FKW())
        direction_spinner = Spinner(
            text='RIGHT',
            values=['UP', 'DOWN', 'LEFT', 'RIGHT'],
            size_hint_y=None,
            height=40,
            option_cls=UniSpinnerOption,
            **FKW()
        )

        speed_labels = {1: "Whole Note", 2: "Half Note", 4: "Quarter Note", 8: "Eighth Note", 16: "Sixteenth Note"}
        speed_slider = Slider(min=1, max=16, step=1, value=4, size_hint_y=None, height=40)

        def update_speed_label(instance, value):
            val = int(value)
            closest = min(speed_labels.keys(), key=lambda k: abs(k - val))
            speed_slider.value = closest
            speed_label.text = f"Robot Speed: {speed_labels[closest]}"

        speed_slider.bind(value=update_speed_label)

        place_button = Button(text="Place Robot", size_hint_y=None, height=40, **FKW())

        def place_robot(_):
            speed = int(speed_slider.value)
            direction = direction_spinner.text
            self.grid.set_agent_at(self.row, self.col, agents.ROBOT, speed=speed)
            self.grid.robot_agent.directions[(self.row, self.col)] = agents.DIRECTIONS[direction]
            popup.dismiss()

        place_button.bind(on_press=place_robot)

        content.add_widget(Label(text="Initial Direction:", size_hint_y=None, height=30, **FKW()))
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
                rel_x = (pos[0] - self.x) / self.width
                rel_y = (pos[1] - self.y) / self.height
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

        pitch_label = Label(text='Pitch: --- Hz', size_hint_y=None, height=30, **FKW())
        duration_label = Label(text='Duration: --- s', size_hint_y=None, height=30, **FKW())

        selector = TwoDAxisSelector(size_hint=(1, 1))
        selector.selected_pitch = 440.0
        selector.selected_duration = 0.5

        place_button = Button(text="Place Bell", size_hint_y=None, height=40, **FKW())
        sample_button = Button(text="Play Sample", size_hint_y=None, height=40, **FKW())

        def place_bell(_):
            pitch = selector.selected_pitch
            duration = selector.selected_duration
            self.grid.set_agent_at(self.row, self.col, agent_type, pitch, duration, velocity=100)
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
