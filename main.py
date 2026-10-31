
import os
import traceback

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

Window.clearcolor = get_color_from_hex("#0F1A24")


class FootballManagerApp(App):

    def write_startup_log(self, message):
        try:
            log_path = os.path.join(
                self.user_data_dir,
                "startup_error.log"
            )
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n" + message + "\n")
        except Exception:
            pass

    def build(self):
        self.engine = None
        self.write_startup_log(
            "وصل التطبيق إلى FootballManagerApp.build()"
        )

        try:
            from engine import GameEngine

            db_path = os.path.join(
                self.user_data_dir,
                "football_manager_apk.db"
            )

            self.engine = GameEngine(db_path)

            log_text = (
                "مرحباً بك في مدير كرة القدم!\n"
                "اضغط على الأزرار في الأسفل للبدء."
            )

        except Exception:
            error_text = traceback.format_exc()
            self.write_startup_log(
                "فشل تحميل المحرك أو قاعدة البيانات:\n"
                + error_text
            )
            log_text = (
                "حدث خطأ أثناء تحميل اللعبة:\n\n"
                + error_text
            )

        root = BoxLayout(
            orientation="vertical",
            padding=10,
            spacing=10
        )

        self.output = TextInput(
            text=log_text,
            readonly=True,
            background_color=(0, 0, 0, 1),
            foreground_color=(0.8, 0.8, 0.8, 1),
            font_size="12sp"
        )

        root.add_widget(self.output)

        self.buttons_layout = GridLayout(
            cols=2,
            spacing=5,
            size_hint_y=None,
            height=300
        )

        buttons = [
            ("⚽ خوض المباراة", self.play_match),
            ("⏳ تقديم أسبوع", self.advance_week),
            ("👥 الفريق", self.show_squad),
            ("🏆 الترتيب", self.show_standings),
            ("💰 الميزانية", self.show_finance),
            ("💼 الرعاية", self.show_sponsor),
            ("🚪 إغلاق", self.stop),
        ]

        for button_text, callback in buttons:
            btn = Button(
                text=button_text,
                font_size="16sp",
                background_color=(0.2, 0.6, 0.2, 1)
            )
            btn.bind(on_release=callback)
            self.buttons_layout.add_widget(btn)

        root.add_widget(self.buttons_layout)

        return root

    def update_log(self, text):
        self.output.text += "\n" + text
        self.output.cursor = (0, len(self.output.text))

    def advance_week(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح بسبب خطأ التحميل.")
            return

        try:
            self.update_log("⏳ جاري تقديم أسبوع...")
            log = self.engine.advance_days(7)

            for item in log:
                if item.get("type") == "match":
                    self.update_log(
                        "⚽ " + str(item.get("text", ""))
                        + "\n"
                        + str(item.get("stats", ""))
                    )

            self.update_log("✅ تم تقديم الأسبوع.")

        except Exception:
            error_text = traceback.format_exc()
            self.write_startup_log(
                "خطأ أثناء تقديم الأسبوع:\n" + error_text
            )
            self.update_log(
                "حدث خطأ أثناء تقديم الأسبوع:\n" + error_text
            )

    def play_match(self, instance):
        self.update_log(
            "⚠️ لعرض المباراة التفاعلية، استخدم زر تقديم الوقت."
        )

    def show_squad(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return

        try:
            self.update_log("--- 👥 الفريق ---")

            for player in self.engine.get_squad()[:5]:
                self.update_log(
                    "[{}] {} | OVR {}".format(
                        player.get("pos", ""),
                        player.get("name", ""),
                        player.get("ovr", "")
                    )
                )

        except Exception:
            self.update_log(traceback.format_exc())

    def show_standings(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return

        try:
            self.update_log("--- 🏆 الترتيب ---")

            for index, row in enumerate(
                self.engine.get_standings()[:4], 1
            ):
                self.update_log(
                    "{}. {} - {} نقطة".format(
                        index,
                        row.get("name", ""),
                        row.get("pts", "")
                    )
                )

        except Exception:
            self.update_log(traceback.format_exc())

    def show_finance(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return

        try:
            dashboard = self.engine.get_dashboard()
            self.update_log(
                "💰 الميزانية: {:,.0f} د.ت".format(
                    dashboard["budget"]
                )
            )

        except Exception:
            self.update_log(traceback.format_exc())

    def show_sponsor(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return

        try:
            status = self.engine.get_sponsorship_status()
            self.update_log(
                "💼 حالة الرعاية: {}".format(status[0])
            )

        except Exception:
            self.update_log(traceback.format_exc())


if __name__ == "__main__":
    FootballManagerApp().run()
