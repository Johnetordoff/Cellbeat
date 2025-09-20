# app.py
import os
import json

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window

import agents
from recorder import Recorder
from constants import SAVED_TOOLS_PATH, BELL
from ui.fonts import FKW
from ui.popups import NoteConfigurator
from ui.tools import ToolSelection
from grid import SimulationGrid, parse_coord_key, safe_items

# ---------- THEME ----------
THEME = {
    "bg_top": (0.06, 0.07, 0.09, 1),
    "bg_bot": (0.09, 0.10, 0.13, 1),
    "surface": (0.13, 0.14, 0.18, 1),
    "surface_hi": (0.18, 0.19, 0.24, 1),
    "accent": (0.25, 0.60, 1.00, 1),
    "text": (0.92, 0.95, 0.98, 1),
    "muted": (0.70, 0.75, 0.82, 1),
}

def set_btn_style(btn, *, filled=False, width=None):
    """Minimal, consistent button styling."""
    btn.background_normal = ""
    btn.background_down = ""
    btn.border = (0, 0, 0, 0)
    btn.font_size = 16
    if width:
        btn.size_hint_x = None
        btn.width = width
    if filled:
        btn.background_color = (*THEME["accent"][:3], 0.18)
        btn.color = THEME["text"]
    else:
        btn.background_color = THEME["surface"]
        btn.color = THEME["text"]


class CellularAutomataApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid_callbacks = {}
        self.grids = []
        self.recorder = Recorder(self.grids)
        self.current_index = 0
        self.current_bell = {'pitch': 440.0, 'duration': 0.5, 'velocity': 100}
        self._rec_blink = 0
        self.rec_label = None  # added in top controls

    # -----------------------
    # Actions
    # -----------------------
    def place_note(self, pitch: float, duration: float, velocity: int):
        self.current_bell = {'pitch': float(pitch), 'duration': float(duration), 'velocity': int(velocity)}
        if self.grids:
            self.grids[self.current_index].selected_type = BELL

    def save_current_grid(self, instance=None):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        filename_input = TextInput(text='grid.json', multiline=False, **FKW(color=THEME["text"]))
        save_button = Button(text='Save', **FKW(color=THEME["text"]))
        set_btn_style(save_button, filled=True)

        def do_save(_):
            name = filename_input.text.strip()
            if not name.endswith('.json'):
                name += '.json'
            with open(name, 'w') as f:
                json.dump({'grids': [g.get_state() for g in self.grids]}, f, indent=2)
            popup.dismiss()

        layout.add_widget(Label(text='Enter filename:', **FKW(color=THEME["muted"])))
        layout.add_widget(filename_input)
        layout.add_widget(save_button)
        save_button.bind(on_press=do_save)
        popup = Popup(title='Save Grid', content=layout, size_hint=(0.5, 0.3))
        popup.open()

    def toggle_recording(self, instance):
        # Provide a sensible default filename if user hasn't saved yet
        if not getattr(self, "filename", None):
            self.filename = "session.json"

        if not self.recorder.recording:
            self.recorder.grids = self.grids
            # Start recording immediately (popup 'Save' is still available separately)
            self.recorder.start_recording(self.filename)
            instance.text = "Stop"
        else:
            self.recorder.stop_recording()
            instance.text = "Record"

    def prompt_filename(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        filename_input = TextInput(text=getattr(self, "filename", "session.json"),
                                   multiline=False, **FKW(color=THEME["text"]))
        save_button = Button(text='Save', **FKW(color=THEME["text"]))
        set_btn_style(save_button, filled=True)

        def do_save(_):
            name = filename_input.text.strip()
            self.filename = name if name.endswith('.json') else name + '.json'
            # Save current JSON snapshot
            self.recorder.save_json(self.filename)
            popup.dismiss()

        layout.add_widget(Label(text='Enter filename:', **FKW(color=THEME["muted"])))
        layout.add_widget(filename_input)
        layout.add_widget(save_button)
        save_button.bind(on_press=do_save)
        popup = Popup(title='Save Recording', content=layout, size_hint=(0.5, 0.3))
        popup.open()

    # -----------------------
    # UI bars
    # -----------------------
    def build_top_controls(self):
        bar = BoxLayout(size_hint_y=None, height=56, padding=(10, 8), spacing=8)
        # Card background
        with bar.canvas.before:
            Color(*THEME["surface"])
            bar.bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *_: setattr(bar.bg, "pos", bar.pos),
                 size=lambda *_: setattr(bar.bg, "size", bar.size))

        play_btn = Button(text="▶", **FKW(color=THEME["text"]))
        stop_btn = Button(text="■", **FKW(color=THEME["text"]))
        save_btn = Button(text="Save #", **FKW(color=THEME["text"]))
        load_btn = Button(text="Load #", **FKW(color=THEME["text"]))
        audio_btn = Button(text="Save audio", **FKW(color=THEME["text"]))
        config_btn = Button(text="Edit ♫", **FKW(color=THEME["text"]))

        for b in (play_btn, stop_btn, save_btn, load_btn, audio_btn, config_btn):
            set_btn_style(b)

        set_btn_style(play_btn, filled=True)
        set_btn_style(audio_btn, filled=True)

        play_btn.bind(on_press=lambda _:
                      setattr(self.grids[self.current_index], 'running', True))
        stop_btn.bind(on_press=lambda _:
                      setattr(self.grids[self.current_index], 'running', False))
        save_btn.bind(on_press=self.save_current_grid)
        load_btn.bind(on_press=self.load_playback)
        audio_btn.bind(on_press=self.toggle_recording)
        config_btn.bind(on_press=self.open_configurator)

        # Blinking REC badge (right side)
        self.rec_label = Label(text="● REC", **FKW(color=(1, 0.28, 0.28, 1)))
        self.rec_label.size_hint_x = None
        self.rec_label.width = 70

        bar.add_widget(play_btn)
        bar.add_widget(stop_btn)
        bar.add_widget(save_btn)
        bar.add_widget(load_btn)
        bar.add_widget(audio_btn)
        bar.add_widget(config_btn)
        bar.add_widget(self.rec_label)

        # blink timer
        Clock.schedule_interval(self._update_rec_badge, 0.4)
        return bar

    def _update_rec_badge(self, dt):
        if not self.rec_label:
            return
        if self.recorder.recording:
            self._rec_blink = 1 - self._rec_blink
            # Alternate between bright and dim red
            self.rec_label.color = (1, 0.28, 0.28, 1 if self._rec_blink else 0.35)
        else:
            # Idle / muted
            self.rec_label.color = (1, 0.28, 0.28, 0.15)

    def open_configurator(self, _=None):
        NoteConfigurator(on_place=self.place_note, on_save_tool=self.add_saved_tool).open()

    def add_saved_tool(self, tool_data):
        self.saved_tools.append(tool_data)
        self.tool_selection.refresh_tools(self.built_in_tools + self.saved_tools)

    def update_bpm(self, instance, value):
        bpm = int(value)
        self.bpm_label.text = str(bpm)
        interval = 60.0 / 4.0 / bpm  # assuming 16th-note step
        Clock.unschedule(self.update_all_grids)
        Clock.schedule_interval(self.update_all_grids, interval)

    def load_playback(self, instance=None):
        chooser = FileChooserIconView(path=os.getcwd(), filters=['*.json'])
        chooser.bind(on_submit=self.load_selection)
        popup = Popup(title="Load Grid File", content=chooser, size_hint=(0.9, 0.9))
        self.load_popup = popup
        popup.open()

    def load_selection(self, filechooser_instance, selection, touch):
        try:
            with open(selection[0], 'r') as f:
                data = json.load(f)
            if 'grids' in data:
                self.load_all_grids(data['grids'])
        except Exception as e:
            print(f"Error loading grids: {e}")
        if hasattr(self, 'load_popup'):
            self.load_popup.dismiss()
            del self.load_popup

    def load_all_grids(self, grids_data):
        self.content_area.clear_widgets()
        self.toggle_container.clear_widgets()
        self.grids.clear()
        self.grid_toggles.clear()

        for grid_data in grids_data:
            emoji_label = grid_data.get('emoji', f"{len(self.grids) + 1:02d}")
            bpm = grid_data.get('bpm', 120)

            new_grid = SimulationGrid(emoji_label=emoji_label, bpm=bpm)
            new_grid.app = self
            new_grid.bpm = bpm
            # Apply volume if present, else default
            vol = float(grid_data.get("volume", getattr(new_grid, "volume", 1.0)))
            if hasattr(new_grid, "set_volume"):
                new_grid.set_volume(vol)
            else:
                new_grid.volume = vol

            # Ensure bpm exists and schedule this grid only
            if not hasattr(new_grid, "bpm"):
                new_grid.bpm = int(grid_data.get("bpm", 120))
            self._schedule_grid(new_grid)

            self.grids.append(new_grid)

            new_grid.static_grid = np.array(grid_data['static_grid'])
            new_grid.dynamic_grid = np.array(grid_data['dynamic_grid'])

            new_grid.robot_agent.directions = {
                parse_coord_key(k): tuple(v) for k, v in safe_items(grid_data.get("directions", {}))
            }
            new_grid.robot_agent.speeds = {
                parse_coord_key(k): int(v) for k, v in safe_items(grid_data.get("speeds", {}))
            }
            new_grid.robot_agent.counters = {
                parse_coord_key(k): int(v) for k, v in safe_items(grid_data.get("counters", {}))
            }

            loaded_attrs = {}
            for k, v in safe_items(grid_data.get('cell_attributes', {})):
                try:
                    loaded_attrs[parse_coord_key(k)] = v
                except Exception as ex:
                    print(f"Warning: skipping cell_attributes key {k!r}: {ex}")

            for r in range(new_grid.static_grid.shape[0]):
                for c in range(new_grid.static_grid.shape[1]):
                    new_grid.cell_attributes[(r, c)] = {
                        'agent_type': int(new_grid.static_grid[r, c]),
                        'pitch': 440.0,
                        'duration': 0.5,
                        'velocity': 100,
                    }

            for (r, c), attrs in loaded_attrs.items():
                new_grid.cell_attributes[(r, c)].update(attrs)

            idx = len(self.grids) - 1
            toggle = ToggleButton(
                text=new_grid.emoji_label,
                group="grids",
                allow_no_selection=False,
                size_hint_x=None,
                width=40,
                **FKW(color=THEME["text"])
            )
            # Style toggle like a pill
            toggle.background_normal = ""
            toggle.background_down = ""
            toggle.background_color = THEME["surface"]

            def _sync_toggle_bg(inst, state):
                inst.background_color = THEME["surface_hi"] if state == "down" else THEME["surface"]

            toggle.bind(state=lambda inst, val: _sync_toggle_bg(inst, val))
            toggle.bind(on_release=lambda instance, idx=idx: self.switch_to_grid(idx))
            self.toggle_container.add_widget(toggle)
            self.grid_toggles.append(toggle)

        def finish_grid_initialization(dt):
            self.switch_to_grid(0)
            self.grids[0].refresh_cells()
            self.grid_toggles[0].state = 'down'

        Clock.schedule_once(lambda dt: self.switch_to_grid(0), 0)
        Clock.schedule_once(lambda dt: self.grids[0].refresh_cells(), 0.1)
        Clock.schedule_once(finish_grid_initialization, 0)

    def _vol_nudge(self, delta):
        g = self.grids[self.current_index]
        v = float(getattr(g, "volume", 1.0))
        v += 0.1 if delta > 0 else -0.1
        v = max(0.0, min(1.0, v))
        if hasattr(g, "set_volume"):
            g.set_volume(v)
        else:
            g.volume = v
        self.vol_label.text = f'{int(getattr(g, "volume", v) * 100)}%'

    def build_grid_toolbar(self):
        bar = BoxLayout(size_hint_y=None, height=52, padding=(10, 6), spacing=10)
        with bar.canvas.before:
            Color(*THEME["surface"])
            bar.bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *_: setattr(bar.bg, "pos", bar.pos),
                 size=lambda *_: setattr(bar.bg, "size", bar.size))

        self.toggle_container = BoxLayout(orientation='horizontal', size_hint_x=1, spacing=6)
        add_btn = Button(text="+++", **FKW(color=THEME["text"]))
        rem_btn = Button(text="–--", **FKW(color=THEME["text"]))
        set_btn_style(add_btn, filled=True, width=46)
        set_btn_style(rem_btn, width=46)

        add_btn.bind(on_press=lambda _: self.add_grid())
        rem_btn.bind(on_press=lambda _: self.remove_current_grid())
        self.remove_btn = rem_btn

        bar.add_widget(add_btn)
        bar.add_widget(rem_btn)
        bar.add_widget(self.toggle_container)


        grid = self.grids[self.current_index]
        cur_vol = int(getattr(grid, "volume", 1.0) * 100)
        self.vol_label = Label(text=f'{cur_vol}%', size_hint_x=None, width=110, **FKW(color=THEME["muted"]))
        bar.add_widget(self.vol_label)

        # Volume chips
        for sym, delta in (('VOL–', -1), ('VOL+', +1)):
            btn = Button(text=sym, **FKW(color=THEME["text"]))
            set_btn_style(btn, width=70)
            btn.bind(on_press=lambda _, d=delta: self._vol_nudge(d))
            bar.add_widget(btn)

        self.bpm_label = Label(text=str(grid.bpm), size_hint_x=None, width=120,
                               **FKW(color=THEME["muted"]))
        bar.add_widget(self.bpm_label)

        # Compact +/- chips
        for sym, delta in (('BPM–', -1), ('BPM+', +1)):
            btn = Button(text=sym, **FKW(color=THEME["text"]))
            set_btn_style(btn, width=70)
            btn.bind(on_press=lambda _, d=delta: self._bpm_nudge(d))
            bar.add_widget(btn)

        return bar

    def _bpm_nudge(self, delta):
        g = self.grids[self.current_index]
        g.bpm = max(1, min(300, g.bpm + delta))
        self.update_bpm(None, g.bpm)

    # -----------------------
    # Build
    # -----------------------
    def build(self):
        Window.clearcolor = THEME["bg_bot"]

        root = BoxLayout(orientation='vertical')
        # Subtle vertical gradient
        with root.canvas.before:
            Color(*THEME["bg_top"])
            root.bg_top = Rectangle(pos=root.pos, size=root.size)
            Color(*THEME["bg_bot"])
            root.bg_bot = Rectangle(pos=(root.x, root.y - root.height / 2),
                                    size=(root.width, root.height * 1.2))

        def _sync_root(*_):
            root.bg_top.pos = root.pos
            root.bg_top.size = root.size
            root.bg_bot.pos = (root.x, root.y - root.height / 2)
            root.bg_bot.size = (root.width, root.height * 1.2)

        root.bind(pos=_sync_root, size=_sync_root)

        # First grid
        first_grid = SimulationGrid(emoji_label="01")
        if not hasattr(first_grid, "volume"):
            first_grid.volume = 1.0

        # Per-grid scheduling (BPM)
        self._schedule_grid(first_grid)
        first_grid.app = self
        self.grids = [first_grid]
        self.grid_toggles = []
        self.current_index = 0

        # Top bar (play/stop/save/load/config/rec)
        self.top_controls = self.build_top_controls()
        root.add_widget(self.top_controls)

        # Grid toolbar (grid toggles, bpm)
        self.grid_toolbar = self.build_grid_toolbar()
        root.add_widget(self.grid_toolbar)

        # Main content area
        self.content_area = BoxLayout(size_hint=(1, 1), orientation='vertical')
        root.add_widget(self.content_area)
        self.add_grid_toggle(first_grid, index=0)
        self.content_area.add_widget(first_grid)

        # Bottom tool palette
        self.saved_tools = self.load_saved_tools()
        self.built_in_tools = self.get_builtin_tools()
        self.tool_selection = ToolSelection(self.built_in_tools + self.saved_tools, self.tool_selected)

        bottom_bar = BoxLayout(size_hint_y=None, height=120, padding=(8, 8))
        with bottom_bar.canvas.before:
            Color(*THEME["surface"])
            bottom_bar.bg = Rectangle(pos=bottom_bar.pos, size=bottom_bar.size)
        bottom_bar.bind(pos=lambda *_: setattr(bottom_bar.bg, "pos", bottom_bar.pos),
                        size=lambda *_: setattr(bottom_bar.bg, "size", bottom_bar.size))

        bottom_bar.add_widget(self.tool_selection)
        root.add_widget(bottom_bar)

        # Tick
        Clock.schedule_interval(self.update_all_grids, 0.1)
        return root

    def _interval_from_bpm(self, bpm):
        # 16th-note step
        return 60.0 / (4.0 * max(1, bpm))

    def _schedule_grid(self, grid):
        """Schedule this grid's update using its own BPM."""
        self._unschedule_grid(grid)
        bpm = getattr(grid, "bpm", 120)
        interval = self._interval_from_bpm(bpm)

        def _tick(dt, g=grid):
            g.update()

        self.grid_callbacks[grid] = _tick
        Clock.schedule_interval(_tick, interval)

    def _unschedule_grid(self, grid):
        cb = self.grid_callbacks.pop(grid, None)
        if cb:
            Clock.unschedule(cb)

    # -----------------------
    # Misc helpers
    # -----------------------
    def grid_reset(self, _=None):
        grid = self.grids[self.current_index]
        grid.static_grid.fill(agents.EMPTY)
        grid.dynamic_grid.fill(agents.EMPTY)
        for attr in grid.cell_attributes.values():
            attr['agent_type'] = agents.EMPTY
            attr['pitch'] = 440.0
            attr['duration'] = 0.5
            attr['velocity'] = 100
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

        self.bpm_label.text = f'{grid.bpm}'
        if hasattr(self, "vol_label"):
            self.vol_label.text = f'{int(getattr(grid, "volume", 1.0) * 100)}%'

        Clock.schedule_once(lambda dt: grid.refresh_cells(), 0)

    def add_grid_toggle(self, grid, index):
        toggle = ToggleButton(
            text=grid.emoji_label,
            group="grids",
            allow_no_selection=False,
            size_hint_x=None,
            width=40,
            **FKW(color=THEME["text"])
        )
        toggle.background_normal = ""
        toggle.background_down = ""
        toggle.background_color = THEME["surface"]

        def _sync_toggle_bg(inst, state):
            inst.background_color = THEME["surface_hi"] if state == "down" else THEME["surface"]

        toggle.bind(state=lambda inst, val: _sync_toggle_bg(inst, val))
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
            {'id': BELL, 'icon': 'assets/images/tone_0.png'},
        ]

    def tool_selected(self, tool_data):
        self.grids[self.current_index].selected_type = tool_data['id']

    def load_saved_tools(self):
        if os.path.exists(SAVED_TOOLS_PATH):
            try:
                with open(SAVED_TOOLS_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load saved tools: {e}")
        return []

    def add_grid(self):
        if len(self.grids) >= 108:
            return
        next_idx = len(self.grids)
        new_emoji = f"{len(self.grids) + 1:02d}"
        new_grid = SimulationGrid(emoji_label=new_emoji)
        new_grid.app = self
        self.grids.append(new_grid)
        new_toggle = ToggleButton(
            text=new_emoji, group="grids", allow_no_selection=False,
            size_hint_x=None, width=50, **FKW(color=THEME["text"])
        )
        new_toggle.background_normal = ""
        new_toggle.background_down = ""
        new_toggle.background_color = THEME["surface"]
        new_toggle.bind(state=lambda inst, val:
                        setattr(inst, "background_color", THEME["surface_hi"] if val == "down" else THEME["surface"]))
        new_toggle.bind(on_release=lambda instance, idx=next_idx: self.switch_to_grid(idx))
        self.toggle_container.add_widget(new_toggle)
        self.grid_toggles.append(new_toggle)
        self.switch_to_grid(next_idx)
        if not hasattr(new_grid, "volume"):
            new_grid.volume = 1.0
        if not hasattr(new_grid, "bpm"):
            new_grid.bpm = 120
        self._schedule_grid(new_grid)

        new_toggle.state = 'down'

    def remove_current_grid(self):
        if len(self.grids) <= 1:
            return
        idx_to_remove = self.current_index
        self._unschedule_grid(self.grids[idx_to_remove])  # <— unschedule this grid

        idx_to_remove = self.current_index
        grid_to_remove = self.grids[idx_to_remove]
        if grid_to_remove.parent:
            self.content_area.remove_widget(grid_to_remove)
        self.grids.pop(idx_to_remove)
        toggle_to_remove = self.grid_toggles.pop(idx_to_remove)
        self.toggle_container.remove_widget(toggle_to_remove)
        if idx_to_remove >= len(self.grids):
            self.current_index = len(self.grids) - 1
        else:
            self.current_index = idx_to_remove
        new_index = self.current_index
        new_grid_widget = self.grids[new_index]
        new_grid_widget.size_hint = (1, 1)
        if not new_grid_widget.parent:
            self.content_area.add_widget(new_grid_widget)
        for i, toggle in enumerate(self.grid_toggles):
            toggle.state = 'down' if i == new_index else 'normal'

    def update_all_grids(self, dt):
        for grid in self.grids:
            grid.update()


if __name__ == '__main__':
    CellularAutomataApp().run()
