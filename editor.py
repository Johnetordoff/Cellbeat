import os
import numpy as np
import wave
import time
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Line, Rectangle
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.properties import ObjectProperty, ListProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.core.window import Window

# Set dark background
Window.clearcolor = (0.1, 0.1, 0.1, 1)

SAMPLES_DIR = 'samples'


class WaveformWidget(Widget):
    sound = ObjectProperty(None)
    waveform_points = ListProperty([])
    sound_length = NumericProperty(0.0)
    tempo = NumericProperty(1.0)
    pitch = NumericProperty(1.0)

    playback_start_time = None
    start_pos = 0
    is_playing = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(waveform_points=lambda *a: self.draw_waveform())
        self.bind(sound_length=lambda *a: self.draw_waveform())

        self.cursor_frac = 0.0
        self.is_dragging = False
        self.cursor_line = None

        Clock.schedule_interval(self._update_cursor, 1 / 60)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def draw_waveform(self, *args):
        if not self.waveform_points:
            return

        self.canvas.clear()

        with self.canvas:
            Color(0.3, 0.3, 0.3, 1)
            mid_y = self.y + self.height / 2
            half_h = self.height / 2

            Line(points=[self.x, mid_y, self.right, mid_y], dash_length=5)
            Line(points=[self.x, mid_y + half_h / 2, self.right, mid_y + half_h / 2], dash_length=5)
            Line(points=[self.x, mid_y - half_h / 2, self.right, mid_y - half_h / 2], dash_length=5)

            display_duration = self.sound_length / self.tempo if self.sound_length else 1
            for sec in range(1, int(display_duration) + 1):
                x = self.x + (sec / display_duration) * self.width
                Line(points=[x, self.y, x, self.top], dash_length=5)

            Color(0, 1, 1, 1)
            points = []
            n = len(self.waveform_points)
            if n < 2:
                return

            for idx, amp in enumerate(self.waveform_points):
                x = self.x + (idx / (n - 1)) * self.width
                y = mid_y + (amp * self.pitch) * half_h
                points.extend([x, y])

            Line(points=points, width=1.5)

            Color(1, 0, 1, 1)
            cx = self.x + self.cursor_frac * self.width
            self.cursor_line = Line(points=[cx, self.y, cx, self.top], width=2)

    def _update_cursor(self, dt):
        if self.is_dragging or not self.is_playing:
            return

        elapsed = time.perf_counter() - self.playback_start_time
        speed_factor = self.tempo * self.pitch
        display_duration = self.sound_length / self.tempo

        self.cursor_frac = self.start_pos + (elapsed * speed_factor) / self.sound_length
        self.cursor_frac = max(0, min(1, self.cursor_frac))

        if self.cursor_frac >= 1.0:
            self.stop_playback()
            return

        if self.cursor_line:
            cx = self.x + self.cursor_frac * self.width
            self.cursor_line.points = [cx, self.y, cx, self.top]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.is_dragging = True
            self._seek_from_touch(touch.x)
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._seek_from_touch(touch.x)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self.is_dragging = False
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _seek_from_touch(self, x_pos):
        frac = (x_pos - self.x) / float(self.width)
        self.cursor_frac = max(0, min(1, frac))

        display_duration = self.sound_length / self.tempo if self.tempo else self.sound_length
        if self.sound:
            self.sound.seek(self.cursor_frac * display_duration)

        if self.cursor_line:
            cx = self.x + self.cursor_frac * self.width
            self.cursor_line.points = [cx, self.y, cx, self.top]

    def start_playback(self):
        self.playback_start_time = time.perf_counter()
        self.start_pos = self.cursor_frac
        self.is_playing = True

    def stop_playback(self):
        self.is_playing = False
        if self.sound:
            self.sound.stop()
        self.cursor_frac = 0
        self.draw_waveform()


class SampleViewerApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.waveform_widget = WaveformWidget(size_hint_y=0.7)
        root.add_widget(self.waveform_widget)

        controls = BoxLayout(size_hint_y=0.3, spacing=10)

        self.spinner = Spinner(
            text='Select Sample',
            values=self.get_sample_files(),
            size_hint_x=None,
            width=200
        )
        self.spinner.bind(text=self.on_select_sample)

        self.play_btn = Button(text='Play', size_hint_x=None, width=80)
        stop_btn = Button(text='Stop', size_hint_x=None, width=80)
        save_btn = Button(text='Save', size_hint_x=None, width=80)

        tempo_label = Label(text='Tempo', size_hint_x=None, width=60, color=(0.9, 0.9, 0.9, 1))
        self.tempo_slider = Slider(min=0.5, max=2.0, value=1.0)

        pitch_label = Label(text='Pitch', size_hint_x=None, width=50, color=(0.9, 0.9, 0.9, 1))
        self.pitch_slider = Slider(min=0.1, max=2.0, value=1.0)

        for btn in (self.play_btn, stop_btn, save_btn):
            btn.background_normal = ''
            btn.background_color = (0.2, 0.2, 0.2, 1)
            btn.color = (1, 1, 1, 1)

        for slider in (self.tempo_slider, self.pitch_slider):
            slider.background_width = 0
            slider.value_track = True
            slider.value_track_color = (0, 0.7, 0.7, 1)
            slider.cursor_height = 20
            slider.cursor_width = 20
            slider.cursor_image = ''

        self.play_btn.bind(on_release=self.toggle_play)
        stop_btn.bind(on_release=self.stop_playback)
        save_btn.bind(on_release=self.save_sample)

        self.tempo_slider.bind(value=self.update_tempo_pitch)
        self.pitch_slider.bind(value=self.update_tempo_pitch)

        controls.add_widget(self.spinner)
        controls.add_widget(self.play_btn)
        controls.add_widget(stop_btn)
        controls.add_widget(save_btn)
        controls.add_widget(tempo_label)
        controls.add_widget(self.tempo_slider)
        controls.add_widget(pitch_label)
        controls.add_widget(self.pitch_slider)

        root.add_widget(controls)

        return root

    def get_sample_files(self):
        if not os.path.exists(SAMPLES_DIR):
            os.makedirs(SAMPLES_DIR)
        files = [f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith('.wav')]
        return files if files else ['(No files found)']

    def on_select_sample(self, spinner, filename):
        if filename == '(No files found)':
            return
        full_path = os.path.join(SAMPLES_DIR, filename)
        self.load_audio(full_path)

    def load_audio(self, audio_file):
        self.sound = SoundLoader.load(audio_file)

        if not self.sound:
            print(f"Failed to load {audio_file}!")
            return

        self.waveform_widget.sound = self.sound
        self.waveform_widget.sound_length = self.sound.length or 0

        try:
            wav = wave.open(audio_file, 'rb')
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            n_frames = wav.getnframes()
            data = wav.readframes(n_frames)
            wav.close()

            if sampwidth == 1:
                dtype = np.uint8
            elif sampwidth == 2:
                dtype = np.int16
            else:
                dtype = np.int16

            audio = np.frombuffer(data, dtype=dtype)

            if n_channels > 1:
                audio = audio.reshape(-1, n_channels)
                audio = audio.mean(axis=1)

            audio = audio.astype(np.float32)

            if dtype == np.uint8:
                audio = (audio - 128) / 128.0
            elif dtype == np.int16:
                audio /= 32768

            self.audio_data = audio

            max_points = 1000
            if audio.shape[0] > max_points:
                factor = audio.shape[0] // max_points
                downsampled = audio[::factor]
            else:
                downsampled = audio

            self.waveform_widget.waveform_points = downsampled.tolist()

        except Exception as e:
            print(f"Waveform generation error for {audio_file}:", e)
            self.waveform_widget.waveform_points = [0.0] * 200

    def toggle_play(self, instance):
        if not self.sound:
            return
        if self.waveform_widget.is_playing:
            self.waveform_widget.stop_playback()
            self.play_btn.text = 'Play'
        else:
            display_duration = self.waveform_widget.sound_length / self.waveform_widget.tempo
            current_pos = self.waveform_widget.cursor_frac * display_duration
            self.sound.seek(current_pos)
            self.sound.play()
            self.waveform_widget.start_playback()
            self.play_btn.text = 'Pause'

    def stop_playback(self, instance):
        self.waveform_widget.stop_playback()
        self.play_btn.text = 'Play'

    def save_sample(self, instance):
        print("Save function placeholder (implement as needed)")

    def update_tempo_pitch(self, instance, value):
        self.waveform_widget.tempo = self.tempo_slider.value
        self.waveform_widget.pitch = self.pitch_slider.value
        self.waveform_widget.draw_waveform()

        if self.sound:
            tempo = self.tempo_slider.value
            pitch = self.pitch_slider.value
            self.sound.pitch = tempo * pitch


if __name__ == '__main__':
    SampleViewerApp().run()
