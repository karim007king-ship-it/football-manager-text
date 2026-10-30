"""game_v2.py — الواجهة النصية الشاملة v3.0 (مع الرعاية والإحصائيات)"""
import os
import time
import random
from engine import GameEngine

def clear(): os.system('cls' if os.name == 'nt' else 'clear')
def pause(): input("\nاضغط Enter للمتابعة...")

def get_club_name(engine, club_id):
    c = engine._conn.cursor()
    c.execute("SELECT name FROM clubs WHERE club_id=?", (club_id,))
    row = c.fetchone()
    return row[0] if row else "فريق"

def sponsor_ui(engine):
    clear()
    status = engine.get_sponsorship_status()
    print("=========================================")
    print(" 💼 عقود الرعاية")
    print("=========================================")
    if status[0] != 'none':
        print(f" ✅ لديك عقد رعاية حالياً: {status[0]}")
        print(f" 💰 المكافأة المحتملة: {status[1]:,.0f}")
    else:
        print("1. العقد الآمن: +500,000 د.ت (مضمون)")
        print("2. العقد المحفز: +200,000 د.ت (+100,000 إذا فزت بالدوري)")
        choice = input("\nاختر (1-2) أو 0 للعودة: ").strip()
        if choice == '1':
            success, msg = engine.sign_sponsorship('safe'); print(f"\n{msg}")
        elif choice == '2':
            success, msg = engine.sign_sponsorship('performance'); print(f"\n{msg}")
    pause()

def scout_opponent_ui(engine):
    clear()
    c = engine._conn.cursor()
    today = engine.current_date.strftime("%Y-%m-%d")
    c.execute("SELECT home_club_id, away_club_id FROM matches WHERE match_date=? AND status='scheduled' AND season_id=? AND (home_club_id=? OR away_club_id=?) LIMIT 1", (today, engine.active_season_id, engine.user_club_id, engine.user_club_id))
    match = c.fetchone()
    if not match: print("⚠️ لا توجد مباراة اليوم لاستكشافها."); pause(); return
    opp_id = match[1] if match[0] == engine.user_club_id else match[0]
    print("=========================================")
    print(f" 🔍 تقرير استكشاف: {get_club_name(engine, opp_id)}")
    print("=========================================")
    c.execute("SELECT tactic, formation FROM clubs WHERE club_id=?", (opp_id,))
    tac, form = c.fetchone()
    print(f" 🎯 التكتيك: {tac} | 📋 الخطة: {form}")
    c.execute("SELECT first_name||' '||last_name, position, overall_rating FROM players WHERE club_id=? ORDER BY overall_rating DESC LIMIT 3", (opp_id,))
    for p in c.fetchall(): print(f"   - [{p[1]}] {p[0]} (OVR {p[2]})")
    pause()

def board_ui(engine):
    clear()
    c = engine._conn.cursor()
    c.execute("SELECT confidence, objective FROM board_status WHERE club_id=?", (engine.user_club_id,))
    conf, obj = c.fetchone()
    print("=========================================")
    print(" 🏛️ مجلس الإدارة")
    print("=========================================")
    print(f" 🎯 هدف الموسم: {obj}")
    print(f" 📊 ثقة الإدارة: {conf}%")
    if conf < 30: print(" ⚠️ تحذير: أنت على وشك الإقالة!")
    pause()

def tactics_ui(engine):
    clear()
    d = engine.get_dashboard()
    print("=========================================")
    print(" 🎯 إدارة التكتيك وخطط اللعب")
    print("=========================================")
    print(f" التكتيك: {d['tactic']} | الخطة: {d['formation']} | الانسجام: {d['familiarity']}%")
    print("\n1. تغيير التكتيك | 2. تغيير الخطة | 0. عودة")
    choice = input("اختر: ").strip()
    if choice == '1':
        t = input("1.هجومي | 2.متوازن | 3.دفاعي: ").strip()
        engine.set_tactic('attacking' if t=='1' else 'defensive' if t=='3' else 'balanced'); pause()
    elif choice == '2':
        f = input("1.4-3-3 | 2.4-4-2 | 3.5-3-2: ").strip()
        if f in ('1','2','3'):
            success, msg = engine.set_formation('4-3-3' if f=='1' else '5-3-2' if f=='3' else '4-4-2')
            print(f"\n{'✅' if success else '❌'} {msg}"); pause()

def transfer_market_ui(engine):
    while True:
        clear()
        d = engine.get_dashboard()
        print(f" 💼 السوق | ميزانيتك: {d['budget']:,.0f} | الرواتب: {d['current_wages']:,.0f}/{d['wage_budget']:,.0f}")
        players = engine.get_transfer_market(10)
        for i, p in enumerate(players, 1):
            print(f"{i}. [{p['pos']}] {p['name']:<15} | OVR {p['ovr']} | {p['value']:,.0f}")
        print("0. عودة")
        choice = input("\nاختر اللاعب للتفاوض (أو 0): ").strip()
        if choice == '0': break
        if choice.isdigit() and 1 <= int(choice) <= len(players):
            target = players[int(choice)-1]
            offer = input(f"قيمته {target['value']:,.0f}. كم ستعرض؟ (أو 0 للإلغاء): ").strip()
            if offer.isdigit() and int(offer) > 0:
                success, msg = engine.negotiate_buy(target['id'], float(offer))
                print(f"\n{'✅' if success else '❌'} {msg}"); pause()

def sell_player_ui(engine):
    clear()
    squad = engine.get_squad()
    print(" 📤 بيع لاعب")
    for i, p in enumerate(squad, 1):
        print(f"{i}. [{p['pos']}] {p['name']:<15} | OVR {p['ovr']} | قيمة: {p['value']:,.0f}")
    choice = input("\nاختر اللاعب (أو 0): ").strip()
    if choice != '0' and choice.isdigit() and 1 <= int(choice) <= len(squad):
        target = squad[int(choice)-1]
        if input(f"بيع {target['name']}؟ (y/n): ").lower() == 'y':
            success, msg = engine.sell_player(target['id'])
            print(f"\n{'✅' if success else '❌'} {msg}"); pause()

def contracts_ui(engine):
    clear()
    expiring = engine.get_expiring_contracts()
    print(" 📝 تجديد العقود")
    if not expiring: print("✅ كل العقود آمنة."); pause(); return
    for i, p in enumerate(expiring, 1):
        print(f"{i}. [{p['pos']}] {p['name']:<15} | عقد {p['contract']} سنة")
    choice = input("\nاختر اللاعب (أو 0): ").strip()
    if choice != '0' and choice.isdigit() and 1 <= int(choice) <= len(expiring):
        years = input("كم سنة؟ (1-5): ").strip()
        if years.isdigit(): 
            success, msg = engine.renew_contract(expiring[int(choice)-1]['id'], int(years))
            print(f"\n{'✅' if success else '❌'} {msg}"); pause()

def training_ui(engine):
    clear()
    squad = engine.get_squad()
    print(" 🏋️ التدريب")
    for i, p in enumerate(squad, 1):
        print(f"{i}. [{p['pos']}] {p['name']:<15} | التركيز: {p['training_focus'] or '—'}")
    choice = input("\nاختر اللاعب (أو 0): ").strip()
    if choice != '0' and choice.isdigit() and 1 <= int(choice) <= len(squad):
        attr = input("1.سرعة | 2.تسديد | 3.تمرير | 4.دفاع | 5.بدنية | 0.إلغاء: ").strip()
        mapping = {'1':'pace', '2':'shooting', '3':'passing', '4':'defending', '5':'physical'}
        if attr in mapping: engine.set_training_focus(squad[int(choice)-1]['id'], mapping[attr])
        elif attr == '0':
            c = engine._conn.cursor(); c.execute("UPDATE players SET training_focus=NULL WHERE player_id=?", (squad[int(choice)-1]['id'],)); engine._conn.commit()
        pause()

def youth_academy_ui(engine):
    clear()
    youths = engine.get_youth_players()
    print(" 🌱 أكاديمية الشباب")
    if not youths: print("لا يوجد مواهب حالياً."); pause(); return
    for i, p in enumerate(youths, 1):
        print(f"{i}. [{p['pos']}] {p['name']} | العمر: {p['age']} | OVR {p['ovr']} | إمكانيات: {p['pot']}")
    choice = input("\nاختر الموهبة للترقية (أو 0): ").strip()
    if choice != '0' and choice.isdigit() and 1 <= int(choice) <= len(youths):
        c = engine._conn.cursor(); c.execute("UPDATE players SET is_youth=0 WHERE player_id=?", (youths[int(choice)-1]['id'],)); engine._conn.commit()
        print(f"\n✅ تم ترقية {youths[int(choice)-1]['name']}!"); pause()

def view_squad_ui(engine):
    clear()
    print(" 👥 تشكيلة الفريق")
    for p in engine.get_squad():
        status = "🚑" if p["injured"] else "🚫" if p["suspension"] > 0 else "⭐" if p["starter"] else "🪑"
        mood = "😡" if p["morale"] < 40 else "😐" if p["morale"] < 70 else "😊"
        form = "❄️" if p["form"] < 50 else "🔥" if p["form"] > 85 else "➖"
        print(f"{status} [{p['pos']}] {p['name']:<15} | OVR {p['ovr']} | {mood}{form}")
    pause()

def do_substitution(engine, user_club):
    c = engine._conn.cursor()
    c.execute("SELECT player_id, first_name||' '||last_name, position, overall_rating FROM players WHERE club_id=? AND is_starter=1 AND is_injured=0 AND suspension_matches=0", (user_club,))
    starters = c.fetchall()
    c.execute("SELECT player_id, first_name||' '||last_name, position, overall_rating FROM players WHERE club_id=? AND is_starter=0 AND is_injured=0 AND suspension_matches=0 AND is_youth=0", (user_club,))
    bench = c.fetchall()
    
    if not bench: print("\n❌ لا يوجد احتياطيون متاحون!"); return

    print("\nاللاعبون الأساسيون:")
    for i, p in enumerate(starters, 1): print(f"{i}. [{p[2]}] {p[1]} (OVR {p[3]})")
    out_idx = input("\nاختر رقم اللاعب الذي تريد استبداله (أو 0): ").strip()
    if not out_idx.isdigit() or int(out_idx) == 0 or int(out_idx) > len(starters): return
    
    print("\nالاحتياطيون:")
    for i, p in enumerate(bench, 1): print(f"{i}. [{p[2]}] {p[1]} (OVR {p[3]})")
    in_idx = input(f"\nاختر البديل لـ {starters[int(out_idx)-1][1]} (أو 0): ").strip()
    if not in_idx.isdigit() or int(in_idx) == 0 or int(in_idx) > len(bench): return

    out_p, in_p = starters[int(out_idx)-1], bench[int(in_idx)-1]
    c.execute("UPDATE players SET is_starter=1 WHERE player_id=?", (in_p[0],))
    c.execute("UPDATE players SET is_starter=0 WHERE player_id=?", (out_p[0],))
    engine._conn.commit()
    print(f"\n✅ تم التبديل: خرج {out_p[1]} ودخل {in_p[1]}!")

def play_interactive_match(engine):
    c = engine._conn.cursor()
    today = engine.current_date.strftime("%Y-%m-%d")
    c.execute("SELECT match_id, home_club_id, away_club_id, weather FROM matches WHERE match_date=? AND status='scheduled' AND season_id=? AND (home_club_id=? OR away_club_id=?) LIMIT 1", (today, engine.active_season_id, engine.user_club_id, engine.user_club_id))
    match = c.fetchone()
    if not match: print("\n⚠️ لا توجد مباراة اليوم!"); pause(); return

    mid, hid, aid, weather = match
    is_home = (hid == engine.user_club_id)
    user_club, opp_club = (hid, aid) if is_home else (aid, hid)
    user_name, opp_name = get_club_name(engine, user_club), get_club_name(engine, opp_club)
    home_goals, away_goals = 0, 0
    
    c.execute("SELECT tactic, formation FROM clubs WHERE club_id=?", (user_club,)); u_tac, u_form = c.fetchone()
    c.execute("SELECT tactic, formation FROM clubs WHERE club_id=?", (opp_club,)); o_tac, o_form = c.fetchone()
    
    def get_strength(club_id, tactic, form):
        c.execute("SELECT position, AVG(overall_rating * (morale/70.0) * (form/70.0)) FROM players WHERE club_id=? AND is_starter=1 AND is_injured=0 AND suspension_matches=0 GROUP BY position", (club_id,))
        d = dict(c.fetchall())
        atk, dfn = (d.get("FWD", 60) + d.get("MID", 60)) / 2, (d.get("DEF", 60) + d.get("GK", 60)) / 2
        if tactic == 'attacking': atk += 3; dfn -= 2
        elif tactic == 'defensive': atk -= 2; dfn += 3
        if form == '4-3-3': atk += 2; dfn -= 2
        elif form == '5-3-2': dfn += 3; atk -= 1
        return atk, dfn

    weather_ar = {"clear": "☀️ صحو", "rain": "🌧️ ممطر", "hot": "🔥 حار"}.get(weather, weather)
    clear()
    print(f"\n⚽ انطلاق المباراة: {user_name} ضد {opp_name}")
    print(f"🌡️ الطقس: {weather_ar}\n" + "="*50)
    time.sleep(1)

    for minute in range(1, 91):
        event_happened = False
        event_text = ""
        
        if random.random() < 0.01:
            c.execute("SELECT player_id, first_name||' '||last_name FROM players WHERE club_id=? AND is_starter=1 AND is_injured=0", (user_club,))
            inj = c.fetchall()
            if inj:
                victim = random.choice(inj)
                c.execute("UPDATE players SET is_injured=1 WHERE player_id=?", (victim[0],)); engine._conn.commit()
                print(f"\n🚑 إصابة! اللاعب {victim[1]} يخرج متأثراً."); event_happened = True
                
        uA, uD = get_strength(user_club, u_tac, u_form)
        oA, oD = get_strength(opp_club, o_tac, o_form)
        w_mult = 0.8 if weather == 'rain' else 0.9 if weather == 'hot' else 1.0

        hg_chance = 0.02 + ((uA - oD) / 200 if is_home else (oA - uD) / 200) * w_mult
        ag_chance = 0.02 + ((oA - uD) / 200 if is_home else (uA - oD) / 200) * w_mult

        if random.random() < hg_chance:
            home_goals += 1; event_happened = True
            c.execute("SELECT first_name||' '||last_name FROM players WHERE club_id=? AND position='FWD' LIMIT 1", (hid,))
            s_name = c.fetchone()[0] if c.fetchone() else "لاعب"
            event_text = f"⚽ هدف رائع لـ {get_club_name(engine, hid)} عن طريق {s_name}!"
        elif random.random() < ag_chance:
            away_goals += 1; event_happened = True
            c.execute("SELECT first_name||' '||last_name FROM players WHERE club_id=? AND position='FWD' LIMIT 1", (aid,))
            s_name = c.fetchone()[0] if c.fetchone() else "لاعب"
            event_text = f"⚽ هدف قاتل لـ {get_club_name(engine, aid)} عن طريق {s_name}!"

        if event_text:
            print(f"\n🎙️ [{minute}']: {event_text}")
            print(f"النتيجة: {user_name} {home_goals if is_home else away_goals} - {away_goals if is_home else home_goals} {opp_name}")
            time.sleep(2)

        if (minute % 15 == 0 or event_happened) and minute < 90:
            print(f"\n--- 🛑 توقف (د {minute}) ---")
            print("1. تغيير التكتيك | 2. تبديل | 3. متابعة")
            choice = input("اختر: ").strip()
            if choice == '1':
                t = input("1.هجومي | 2.متوازن | 3.دفاعي: ").strip()
                u_tac = 'attacking' if t == '1' else 'defensive' if t == '3' else 'balanced'
            elif choice == '2':
                do_substitution(engine, user_club)
            time.sleep(1)

        time.sleep(0.05)

    print(f"\n🏁 نهاية المباراة: {user_name} {home_goals if is_home else away_goals} - {away_goals if is_home else home_goals} {opp_name}")
    c.execute("UPDATE matches SET home_goals=?, away_goals=?, status='played' WHERE match_id=?", (home_goals, away_goals, mid))
    if (home_goals > away_goals and is_home) or (away_goals > home_goals and not is_home):
        c.execute("UPDATE players SET morale = MIN(100, morale + 5) WHERE club_id=?", (user_club,))
    elif (home_goals < away_goals and is_home) or (away_goals < home_goals and not is_home):
        c.execute("UPDATE players SET morale = MAX(0, morale - 5) WHERE club_id=?", (user_club,))
    engine._conn.commit()
    pause()

def advance_time_ui(engine):
    clear()
    days = input("كم يوماً؟ (1، 3، 7): ").strip()
    if not days.isdigit(): return
    for _ in range(int(days)):
        c = engine._conn.cursor()
        today = engine.current_date.strftime("%Y-%m-%d")
        c.execute("SELECT home_club_id, away_club_id FROM matches WHERE match_date=? AND status='scheduled' AND season_id=? AND (home_club_id=? OR away_club_id=?)", (today, engine.active_season_id, engine.user_club_id, engine.user_club_id))
        match = c.fetchone()
        if match:
            print(f"\n⚠️ مباراة اليوم: {get_club_name(engine, match[0])} × {get_club_name(engine, match[1])}")
            print("1. تفاعلي | 2. سريع | 3. إلغاء")
            choice = input("اختر (1-3): ").strip()
            if choice == '1': play_interactive_match(engine)
            elif choice == '2':
                log = engine.advance_days(1)
                for item in log:
                    if item["type"] == "match":
                        print(f"  ⚽ النتيجة: {item['text']}")
                        print(f"     {item['stats']}")
                pause()
            return
        else:
            engine.advance_days(1)
    print(f"\n✅ تم تقديم {days} أيام."); pause()

def main():
    clear()
    slot = input("اختر فتحة الحفظ (1-3) [1]: ").strip() or '1'
    engine = GameEngine(f"football_manager_{slot}.db")
    
    while True:
        clear()
        if engine.is_sacked == 1:
            print("=========================================")
            print(" ❌ لقد تمت إقالتك من منصبك!")
            print("=========================================")
            input("اضغط Enter للخروج."); break
            
        d = engine.get_dashboard()
        print("=========================================")
        print(f" 🏟️ {d['club']} | 📅 {d['date']}")
        print(f" 💰 {d['budget']:,.0f} د.ت | 🏛️ الثقة: {d['confidence']}% | 🎯 {d['objective']}")
        if d["next_match"]:
            nm = d["next_match"]
            weather_ar = {"clear": "☀️", "rain": "🌧️", "hot": "🔥"}.get(nm["weather"], "")
            print(f" ⚽ القادمة: {nm['home']} × {nm['away']} ({nm['date']}) {weather_ar}")
        print("=========================================")
        print("1. ⚽ خوض المباراة (تفاعلي)")
        print("2. ⏳ تقديم الوقت")
        print("3. 👥 الفريق")
        print("4. 🎯 خطط اللعب")
        print("5. 🔍 استكشاف الخصم")
        print("6. 💼 السوق (شراء)")
        print("7. 📤 بيع لاعبين")
        print("8. 📝 تجديد العقود")
        print("9. 🏋️ التدريب")
        print("10. 🌱 أكاديمية الشباب")
        print("11. 🏛️ مجلس الإدارة")
        print("12. 💼 عقود الرعاية")
        print("13. 🚪 خروج")
        print("=========================================")
        
        choice = input("اختر رقماً (1-13): ").strip()
        if choice == '1': play_interactive_match(engine)
        elif choice == '2': advance_time_ui(engine)
        elif choice == '3': view_squad_ui(engine)
        elif choice == '4': tactics_ui(engine)
        elif choice == '5': scout_opponent_ui(engine)
        elif choice == '6': transfer_market_ui(engine)
        elif choice == '7': sell_player_ui(engine)
        elif choice == '8': contracts_ui(engine)
        elif choice == '9': training_ui(engine)
        elif choice == '10': youth_academy_ui(engine)
        elif choice == '11': board_ui(engine)
        elif choice == '12': sponsor_ui(engine)
        elif choice == '13': break

if __name__ == "__main__":
    main()