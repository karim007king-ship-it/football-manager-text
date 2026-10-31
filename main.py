from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from engine import GameEngine
import os

Window.clearcolor = get_color_from_hex("#0F1A24")

class FootballManagerApp(App):
    def build(self):
        try:
            db_path = os.path.join(
                self.user_data_dir,
                "football_manager_apk.db"
            )
            self.engine = GameEngine(db_path)
            self.log_text = "مرحباً بك في مدير كرة القدم!\nاضغط على الأزرار في الأسفل للبدء."
        except Exception as e:
            self.engine = None
            self.log_text = f"خطأ في التحميل: {e}\n"

        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.output = TextInput(text=self.log_text, readonly=True, 
                                background_color=(0,0,0,1), 
                                foreground_color=(0.8,0.8,0.8,1), 
                                font_size='14sp')
        root.add_widget(self.output)

        self.buttons_layout = GridLayout(cols=2, spacing=5, size_hint_y=None, height=300)
        
        buttons = [
            ("⚽ خوض المباراة", self.play_match),
            ("⏳ تقديم أسبوع", self.advance_week),
            ("👥 الفريق", self.show_squad),
            ("🏆 الترتيب", self.show_standings),
            ("💰 الميزانية", self.show_finance),
            ("💼 الرعاية", self.show_sponsor),
            ("🚪 إغلاق", self.stop)
        ]

        for text, callback in buttons:
            btn = Button(text=text, font_size='16sp', background_color=(0.2, 0.6, 0.2, 1))
            btn.bind(on_release=callback)
            self.buttons_layout.add_widget(btn)

        root.add_widget(self.buttons_layout)
        return root

    def update_log(self, text):
        self.output.text += f"\n{text}"
        self.output.cursor = (0, len(self.output.text))

    def advance_week(self, instance):
        if not self.engine: return
        self.update_log("\n⏳ جاري تقديم أسبوع...")
        log = self.engine.advance_days(7)
        for item in log:
            if item['type'] == 'match':
                self.update_log(f"⚽ {item['text']}\n{item.get('stats', '')}")
        self.update_log("✅ تم تقديم الأسبوع.")

    def play_match(self, instance):
        self.update_log("\n⚠️ لعرض المباراة التفاعلية، استخدم زر تقديم الوقت.")

    def show_squad(self, instance):
        if not self.engine: return
        self.update_log("\n--- 👥 الفريق ---")
        for p in self.engine.get_squad()[:5]:
            self.update_log(f"[{p['pos']}] {p['name']} | OVR {p['ovr']}")

    def show_standings(self, instance):
        if not self.engine: return
        self.update_log("\n--- 🏆 الترتيب ---")
        for i, r in enumerate(self.engine.get_standings()[:4], 1):
            self.update_log(f"{i}. {r['name']} - {r['pts']} نقطة")

    def show_finance(self, instance):
        if not self.engine: return
        d = self.engine.get_dashboard()
        self.update_log(f"\n💰 الميزانية: {d['budget']:,.0f} د.ت")

    def show_sponsor(self, instance):
        if not self.engine: return
        status = self.engine.get_sponsorship_status()
        self.update_log(f"\n💼 حالة الرعاية: {status[0]}")

if __name__ == '__main__':
    FootballManagerApp().run()
