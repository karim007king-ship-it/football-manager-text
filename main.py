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

# ---- Police arabe (à placer dans fonts/NotoNaskhArabic-Regular.ttf) ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "NotoNaskhArabic-Regular.ttf")
FONT = "Roboto"
if os.path.exists(FONT_PATH):
    try:
        from kivy.core.text import Label as _CoreLabel
        _CoreLabel(text="a", font_name=FONT_PATH).refresh()
        FONT = FONT_PATH
    except Exception:
        FONT = "Roboto"  # fichier de police invalide

# ---- Mise en forme du texte arabe (module local, sans dépendance) ----
try:
    from arabic_fix import ar
except Exception:
    def ar(text):
        return text


class FootballManagerApp(App):

    def write_startup_log(self, message):
        try:
            log_path = os.path.join(self.user_data_dir, "startup_error.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n" + message + "\n")
        except Exception:
            pass

    def build(self):
        try:
            return self._build()
        except Exception:
            err = traceback.format_exc()
            self.write_startup_log("Crash build():\n" + err)
            from kivy.uix.scrollview import ScrollView
            from kivy.uix.label import Label
            sv = ScrollView()
            lb = Label(text="ERREUR:\n\n" + err, size_hint_y=None,
                       halign="left", valign="top", font_size="12sp")
            lb.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
            lb.bind(texture_size=lambda i, s: setattr(i, "height", s[1]))
            sv.add_widget(lb)
            return sv

    def _build(self):
        self.engine = None
        self.write_startup_log("build() atteint")

        try:
            from engine import GameEngine
            db_path = os.path.join(self.user_data_dir, "football_manager_apk.db")
            self.engine = GameEngine(db_path)
            log_text = ar(
                "مرحباً بك في مدير كرة القدم!\n"
                "اضغط على الأزرار في الأسفل للبدء."
            )
        except Exception:
            error_text = traceback.format_exc()
            self.write_startup_log("Échec moteur/base:\n" + error_text)
            log_text = "Erreur au chargement du jeu:\n\n" + error_text

        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        self.output = TextInput(
            text=log_text,
            readonly=True,
            background_color=(0, 0, 0, 1),
            foreground_color=(0.8, 0.8, 0.8, 1),
            font_name=FONT,
            font_size="14sp",
        )
        root.add_widget(self.output)

        self.buttons_layout = GridLayout(
            cols=2, spacing=5, size_hint_y=None, height=300
        )

        # Pas d'emojis : aucune police embarquée ne les affiche
        buttons = [
            ("خوض المباراة", self.play_match),
            ("تقديم أسبوع", self.advance_week),
            ("الفريق", self.show_squad),
            ("الترتيب", self.show_standings),
            ("الميزانية", self.show_finance),
            ("الرعاية", self.show_sponsor),
            ("إغلاق", self.stop),
        ]
        for button_text, callback in buttons:
            btn = Button(
                text=ar(button_text),
                font_name=FONT,
                font_size="18sp",
                background_color=(0.2, 0.6, 0.2, 1),
            )
            btn.bind(on_release=callback)
            self.buttons_layout.add_widget(btn)

        root.add_widget(self.buttons_layout)
        return root

    def update_log(self, text):
        self.output.text += "\n" + ar(text)
        self.output.cursor = (0, len(self.output.text))

    def advance_week(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح بسبب خطأ التحميل.")
            return
        try:
            self.update_log("جاري تقديم أسبوع...")
            log = self.engine.advance_days(7)
            for item in log:
                if item.get("type") == "match":
                    self.update_log(
                        "- " + str(item.get("text", ""))
                        + "\n" + str(item.get("stats", ""))
                    )
            self.update_log("تم تقديم الأسبوع.")
        except Exception:
            error_text = traceback.format_exc()
            self.write_startup_log("Erreur advance_week:\n" + error_text)
            self.output.text += "\n" + error_text

    def play_match(self, instance):
        self.update_log("لعرض المباراة التفاعلية، استخدم زر تقديم أسبوع.")

    def show_squad(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return
        try:
            self.update_log("--- الفريق ---")
            for p in self.engine.get_squad()[:5]:
                self.update_log("[{}] {} | OVR {}".format(
                    p.get("pos", ""), p.get("name", ""), p.get("ovr", "")))
        except Exception:
            self.output.text += "\n" + traceback.format_exc()

    def show_standings(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return
        try:
            self.update_log("--- الترتيب ---")
            for i, row in enumerate(self.engine.get_standings()[:4], 1):
                self.update_log("{}. {} - {} نقطة".format(
                    i, row.get("name", ""), row.get("pts", "")))
        except Exception:
            self.output.text += "\n" + traceback.format_exc()

    def show_finance(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return
        try:
            d = self.engine.get_dashboard()
            self.update_log("الميزانية: {:,.0f} د.ت".format(d["budget"]))
        except Exception:
            self.output.text += "\n" + traceback.format_exc()

    def show_sponsor(self, instance):
        if not self.engine:
            self.update_log("المحرك غير متاح.")
            return
        try:
            status = self.engine.get_sponsorship_status()
            self.update_log("حالة الرعاية: {}".format(status[0]))
        except Exception:
            self.output.text += "\n" + traceback.format_exc()


if __name__ == "__main__":
    FootballManagerApp().run()