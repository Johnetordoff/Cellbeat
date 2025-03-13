from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from game_engine import GameEngineWidget


class MainMenu(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=10, padding=50)

        new_game_btn = Button(text="New Game")
        new_game_btn.bind(on_release=self.start_new_game)

        load_game_btn = Button(text="Load Game")
        load_game_btn.bind(on_release=self.load_game)

        options_btn = Button(text="Options")
        options_btn.bind(on_release=self.open_options)

        exit_btn = Button(text="Exit")
        exit_btn.bind(on_release=self.exit_game)

        layout.add_widget(new_game_btn)
        layout.add_widget(load_game_btn)
        layout.add_widget(options_btn)
        layout.add_widget(exit_btn)

        self.add_widget(layout)

    def start_new_game(self, instance):
        self.manager.current = "game"

    def load_game(self, instance):
        print("Load game feature not implemented yet.")

    def open_options(self, instance):
        print("Options feature not implemented yet.")

    def exit_game(self, instance):
        App.get_running_app().stop()

class MainApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainMenu(name="menu"))
        sm.add_widget(GameEngineWidget(name="game"))
        return sm

if __name__ == "__main__":
    MainApp().run()
