# ui/popups.py
import os
import json
from uuid import uuid4

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle

import audio
from constants import SAVED_TOOLS_PATH
from ui.fonts import FKW, UniSpinnerOption

class NoteConfigurator(Popup):
    def __init__(self, on_place, on_save_tool, **kwargs):
        super().__init__(title="Set Pitch, Duration, Velocity", size_hint=(0.7, 0.8), **kwargs)

        self.on_place = on_place
        self.on_save_tool = on_save_tool
        self.selected_pitch = 440.0
        self.selected_duration = 0.5
        self.selected_velocity = 100

        self.char_spinner = Spinner(
            text='Choose Icon',
            values=['Ω', '≈', 'å', '√', '∫'],
            size_hint=(1, 1),
            height=40,
            option_cls=UniSpinnerOption,
            **FKW()
        )

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.pitch_label = Label(text='Pitch: 440 Hz', **FKW())
        self.duration_label = Label(text='Duration: 0.5 s', **FKW())
        self.velocity_label = Label(text='Velocity: 100', **FKW())

        selector = self.TwoDAxisSelector(self)

        self.velocity_slider = Slider(min=0, max=127, value=100, step=1)
        self.velocity_slider.bind(value=self.on_velocity_change)

        sample_button = Button(text="Play Sample", **FKW())
        place_button = Button(text="Place Bell", **FKW())
        save_button = Button(text="Save as Tool", **FKW())

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

        def load_saved_tools():
            if os.path.exists(SAVED_TOOLS_PATH):
                with open(SAVED_TOOLS_PATH, 'r') as f:
                    return json.load(f)
            return []

        tools = load_saved_tools()
        tools.append(tool_data)
        with open(SAVED_TOOLS_PATH, 'w') as f:
            json.dump(tools, f, indent=2)

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
