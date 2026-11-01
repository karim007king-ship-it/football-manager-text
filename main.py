from kivy.app import App
from kivy.uix.label import Label


class KivyDiagnosticApp(App):
    def build(self):
        return Label(
            text="KIVY STARTUP TEST\n\nIf this screen stays open, the minimal Kivy/SDL2 app started successfully.",
            font_name="Roboto",
            font_size="22sp",
            halign="center",
            valign="middle",
        )


if __name__ == "__main__":
    KivyDiagnosticApp().run()
