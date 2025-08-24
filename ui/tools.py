# ui/tools.py
from typing import Any, Dict
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle

from ui.fonts import FKW


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
            self.label = Label(
                text=tool_data['icon_unicode'],
                font_size=24,
                halign='center',
                valign='middle',
                **FKW()
            )
            self.label.bind(size=self.label.setter('text_size'))
            self.add_widget(self.label)
        else:
            self.image = Image(source=tool_data['icon'])
            self.add_widget(self.image)

        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_press(self):
        self.select_callback(self.tool_data)


class ToolSelection(GridLayout):
    def __init__(self, tools, select_callback, **kwargs):
        from kivy.uix.gridlayout import GridLayout  # local to avoid circulars in some setups
        super().__init__(cols=30, spacing=5, padding=5, size_hint=(None, None), **kwargs)
        self.buttons: Dict[Any, ToolButton] = {}
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
