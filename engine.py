"""engine.py — محرك اللعبة الشامل v3.0 (النسخة المستقرة النهائية)"""
import sqlite3, random, os
from datetime import datetime, timedelta
from db import (initialize, _schedule_league, _schedule_cup,
                _schedule_continental, FIRST, LAST)

def _parse(d): return datetime.strptime(d, "%Y-%m-%d")
def _fmt(d): return d.strftime("%Y-%m-%d")

TRAIN_COST_PER_PLAYER_WEEK = 800

class GameEngine:
    def __init__(self, db_path="football_manager_1.db"):
        self.db_path = db_path
        self._conn = initialize(db_path)
        self.last_season_summary = None
        self._load_state()
        self._load_settings()

    def _load_state(self):
        row = self._conn.execute("""SELECT current_date,active_season_id,
            user_club_id,last_weekly_process, is_sacked FROM game_state WHERE id=1""").fetchone()
        self.current_date = _parse(row[0])
        self.active_season_id = row[1]
        self.user_club_id = row[2]
        self.last_weekly_process = _parse(row[3]) if row[3] else _parse(row[0])
        self.is_sacked = row[4]

    def _load_settings(self):
        self.settings = {k: v for k, v in self._conn.execute("SELECT key,value FROM settings").fetchall()}

    def _save_state(self):
        self._conn.execute("""UPDATE game_state SET current_date=?, active_season_id=?, 
            last_weekly_process=?, is_sacked=? WHERE id=1""",
            (_fmt(self.current_date), self.active_season_id, _fmt(self.last_weekly_process), self.is_sacked))
        self._conn.commit()

    def get_dashboard(self):
        c = self._conn.cursor()
        c.execute("""SELECT name,budget,wage_budget,stadium_capacity,tactic,formation,tactical_familiarity
            FROM clubs WHERE club_id=?""", (self.user_club_id,))
        name, budget, wage_b, cap, tactic, form, fam = c.fetchone()
        
        c.execute("SELECT confidence,objective FROM board_status WHERE club_id=?", (self.user_club_id,))
        conf, obj = c.fetchone()
        
        c.execute("SELECT COALESCE(SUM(wage),0) FROM players WHERE club_id=?", (self.user_club_id,))
        current_wages = c.fetchone()[0]
        
        c.execute("SELECT name FROM seasons WHERE season_id=?", (self.active_season_id,))
        season = c.fetchone()[0]
        
        c.execute("""SELECT match_date,home_club_id,away_club_id,competition,round_name,weather FROM matches 
            WHERE (home_club_id=? OR away_club_id=?) AND status='scheduled' AND season_id=? ORDER BY match_date LIMIT 1""",
            (self.user_club_id, self.user_club_id, self.active_season_id))
        nxt = c.fetchone()
        next_match = None
        if nxt:
            hn = c.execute("SELECT name FROM clubs WHERE club_id=?", (nxt[1],)).fetchone()[0]
            an = c.execute("SELECT name FROM clubs WHERE club_id=?", (nxt[2],)).fetchone()[0]
            next_match = {"date": nxt[0], "home": hn, "away": an, "comp": nxt[3], "round": nxt[4], "weather": nxt[5]}
            
        st = self.get_standings()
        pos = next((i for i, r in enumerate(st, 1) if r["club_id"] == self.user_club_id), None)
        
        return {"club": name, "budget": budget, "wage_budget": wage_b, "current_wages": current_wages,
                "confidence": conf, "objective": obj, "season": season, "date": _fmt(self.current_date),
                "next_match": next_match, "position": pos, "stadium": cap, "tactic": tactic, 
                "formation": form, "familiarity": fam}

    def get_squad(self):
        c = self._conn.cursor()
        c.execute("""SELECT p.player_id, p.first_name||' '||p.last_name, p.position, p.age, 
            p.overall_rating, p.potential_rating, p.is_starter, p.is_injured, p.contract_years,
            p.wage, p.market_value, p.morale, p.form, p.is_youth, p.training_focus,
            p.seasons_at_club, p.personality, p.suspension_matches,
            s.appearances, s.goals, s.assists, s.motm
            FROM players p LEFT JOIN player_stats s ON s.player_id=p.player_id
            WHERE p.club_id=? ORDER BY p.is_starter DESC, p.overall_rating DESC""", (self.user_club_id,))
        return [dict(zip(["id","name","pos","age","ovr","pot","starter","injured","contract","wage",
                          "value","morale","form","youth","training_focus","seasons_at_club",
                          "personality","suspension","apps","goals","assists","motm"], r)) for r in c.fetchall()]

    def get_standings(self):
        c = self._conn.cursor()
        c.execute("SELECT club_id,name FROM clubs")
        st = {cid: {"club_id": cid, "name": n, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0} for cid, n in c.fetchall()}
        c.execute("SELECT home_club_id,away_club_id,home_goals,away_goals FROM matches WHERE status='played' AND season_id=? AND competition='league'", (self.active_season_id,))
        for h, a, hg, ag in c.fetchall():
            for t, gf, ga in [(h, hg, ag), (a, ag, hg)]:
                st[t]["p"] += 1; st[t]["gf"] += gf; st[t]["ga"] += ga
                if gf > ga: st[t]["w"] += 1; st[t]["pts"] += 3
                elif gf == ga: st[t]["d"] += 1; st[t]["pts"] += 1
                else: st[t]["l"] += 1
        for v in st.values(): v["gd"] = v["gf"] - v["ga"]
        return sorted(st.values(), key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)

    def get_youth_players(self):
        c = self._conn.cursor()
        c.execute("SELECT player_id, first_name||' '||last_name, position, age, overall_rating, potential_rating FROM players WHERE club_id=? AND is_youth=1 AND age < 20", (self.user_club_id,))
        return [{"id": r[0], "name": r[1], "pos": r[2], "age": r[3], "ovr": r[4], "pot": r[5]} for r in c.fetchall()]

    def get_expiring_contracts(self):
        c = self._conn.cursor()
        c.execute("""SELECT player_id, first_name||' '||last_name, position, age, overall_rating, wage, contract_years, market_value
            FROM players WHERE club_id=? AND contract_years<=1 ORDER BY contract_years, overall_rating DESC""", (self.user_club_id,))
        return [{"id": r[0], "name": r[1], "pos": r[2], "age": r[3], "ovr": r[4], "wage": r[5], "contract": r[6], "value": r[7]} for r in c.fetchall()]

    def get_transfer_market(self, limit=15):
        c = self._conn.cursor()
        c.execute("""SELECT p.player_id, p.first_name||' '||p.last_name, p.position, p.age, p.overall_rating, p.market_value, c.name
            FROM players p JOIN clubs c ON c.club_id=p.club_id WHERE p.club_id != ? AND p.overall_rating >= 55 ORDER BY RANDOM() LIMIT ?""", (self.user_club_id, limit))
        return [{"id": r[0], "name": r[1], "pos": r[2], "age": r[3], "ovr": r[4], "value": r[5], "club": r[6]} for r in c.fetchall()]

    def set_tactic(self, tactic):
        self._conn.execute("UPDATE clubs SET tactic=? WHERE club_id=?", (tactic, self.user_club_id))
        self._conn.commit()
        return True, "تم تحديث التكتيك"

    def set_formation(self, formation):
        c = self._conn.cursor()
        c.execute("SELECT formation FROM clubs WHERE club_id=?", (self.user_club_id,))
        if c.fetchone()[0] != formation:
            c.execute("UPDATE clubs SET formation=?, tactical_familiarity=MAX(30, tactical_familiarity - 25) WHERE club_id=?", (formation, self.user_club_id))
            self._conn.commit()
            return True, "تم تغيير الخطة (انخفض الانسجام مؤقتاً)"
        return False, "هذه هي خطتك الحالية"

    def get_sponsorship_status(self):
        c = self._conn.cursor()
        c.execute("SELECT sponsor_type, sponsor_bonus FROM clubs WHERE club_id=?", (self.user_club_id,))
        return c.fetchone()

    def sign_sponsorship(self, deal_type):
        c = self._conn.cursor()
        if deal_type == 'safe':
            c.execute("UPDATE clubs SET budget=budget+500000, sponsor_type='safe', sponsor_bonus=0 WHERE club_id=?", (self.user_club_id,))
            msg = "تم توقيع العقد الآمن: +500,000 د.ت"
        elif deal_type == 'performance':
            c.execute("UPDATE clubs SET budget=budget+200000, sponsor_type='performance', sponsor_bonus=100000 WHERE club_id=?", (self.user_club_id,))
            msg = "تم توقيع العقد المحفز: +200,000 د.ت (+100,000 إذا فزت بالدوري)"
        else:
            return False, "عقد غير صالح"
        self._conn.commit()
        return True, msg

    def negotiate_buy(self, pid, offer_price):
        c = self._conn.cursor()
        c.execute("SELECT p.market_value, p.wage, p.club_id, p.first_name||' '||p.last_name FROM players p WHERE p.player_id=?", (pid,))
        row = c.fetchone()
        if not row: return False, "لاعب غير موجود"
        value, wage, seller, pname = row
        
        c.execute("SELECT wage_budget, budget FROM clubs WHERE club_id=?", (self.user_club_id,))
        w_budget, budget = c.fetchone()
        c.execute("SELECT COALESCE(SUM(wage),0) FROM players WHERE club_id=?", (self.user_club_id,))
        current_wages = c.fetchone()[0]
        
        if current_wages + wage > w_budget: return False, "الإدارة رفضت الصفقة: سقف الرواتب لا يسمح!"
        if budget < offer_price: return False, "ميزانيتك لا تكفي لهذا العرض"

        accepted = True if offer_price >= value * 1.2 else (random.random() < 0.7 if offer_price >= value else False)

        if accepted:
            c.execute("UPDATE players SET club_id=?, is_starter=0, seasons_at_club=0 WHERE player_id=?", (self.user_club_id, pid))
            c.execute("UPDATE clubs SET budget=budget-? WHERE club_id=?", (offer_price, self.user_club_id))
            c.execute("UPDATE clubs SET budget=budget+? WHERE club_id=?", (offer_price*0.8, seller))
            self._log_finance(c, -offer_price, f"شراء {pname}")
            self._conn.commit()
            return True, f"تمت الصفقة! انضم {pname} للفريق بـ {offer_price:,.0f}"
        else:
            return False, f"النادي رفض العرض ويطلب مبلغاً أعلى (المطلوب: {value:,.0f})"

    def sell_player(self, pid):
        c = self._conn.cursor()
        c.execute("SELECT market_value, first_name||' '||last_name FROM players WHERE player_id=? AND club_id=?", (pid, self.user_club_id))
        row = c.fetchone()
        if not row: return False, "لاعب ليس في فريقك"
        value, pname = row
        c.execute("UPDATE players SET club_id=NULL,is_starter=0 WHERE player_id=?", (pid,))
        c.execute("UPDATE clubs SET budget=budget+? WHERE club_id=?", (value * 0.85, self.user_club_id))
        self._log_finance(c, value * 0.85, f"بيع {pname}")
        self._conn.commit()
        return True, f"تم بيع {pname} مقابل {value*0.85:,.0f}"

    def renew_contract(self, pid, years):
        c = self._conn.cursor()
        c.execute("SELECT overall_rating, wage FROM players WHERE player_id=? AND club_id=?", (pid, self.user_club_id))
        row = c.fetchone()
        if not row: return False, "لاعب ليس في فريقك"
        ovr, wage = row
        new_wage = int(wage * (1 + (ovr - 60) / 200)) if ovr > 60 else wage
        c.execute("UPDATE players SET contract_years=?, wage=?, contract_warned=0 WHERE player_id=?", (years, new_wage, pid))
        self._conn.commit()
        return True, f"تم التجديد {years} سنوات براتب {new_wage:,.0f}"

    def set_training_focus(self, pid, attribute):
        c = self._conn.cursor()
        c.execute("SELECT overall_rating, potential_rating, training_focus FROM players WHERE player_id=? AND club_id=?", (pid, self.user_club_id))
        row = c.fetchone()
        if not row: return False, "لاعب ليس في فريقك"
        ovr, pot, current = row
        if current == attribute:
            c.execute("UPDATE players SET training_focus=NULL WHERE player_id=?", (pid,))
            msg = "تم إيقاف التركيز"
        else:
            c.execute("UPDATE players SET training_focus=? WHERE player_id=?", (attribute, pid))
            msg = f"تم التركيز على {attribute}"
        self._conn.commit()
        return True, msg

    def _log_finance(self, c, amount, desc):
        balance = c.execute("SELECT budget FROM clubs WHERE club_id=?", (self.user_club_id,)).fetchone()[0]
        c.execute("INSERT INTO finances_log (club_id,date,amount,description,balance_after) VALUES (?,?,?,?,?)", (self.user_club_id, _fmt(self.current_date), amount, desc, balance))

    def advance_days(self, days=7):
        self.last_season_summary = None
        log = []
        c = self._conn.cursor()
        for _ in range(days):
            today = _fmt(self.current_date)
            log.append({"type": "date", "text": today})
            c.execute("UPDATE players SET suspension_matches=MAX(0, suspension_matches-1) WHERE suspension_matches>0")
            c.execute("UPDATE clubs SET tactical_familiarity=MIN(100, tactical_familiarity+5) WHERE club_id=?", (self.user_club_id,))
            
            c.execute("SELECT match_id,home_club_id,away_club_id,competition,round_name FROM matches WHERE match_date=? AND status='scheduled' AND season_id=?", (today, self.active_season_id))
            for mid, h, a, comp, rnd in c.fetchall():
                res = self._simulate_match(mid, h, a, comp)
                log.append({"type": "match", "comp": comp, "round": rnd, "text": res["result"], "stats": res["stats"]})
            
            self._process_weekly_stuff(c, 1)
            self.current_date += timedelta(days=1)

        self._process_board(c)
        self._check_cup_progression(c, 'cup')
        self._check_cup_progression(c, 'continental')
        self._check_season_end(c, log)
        self._conn.commit()
        self._save_state()
        return log

    def _process_weekly_stuff(self, c, days):
        weekly = c.execute("SELECT COALESCE(SUM(wage),0)/52 FROM players WHERE club_id=?", (self.user_club_id,)).fetchone()[0]
        amt = (weekly / 7.0) * days
        if amt > 0:
            c.execute("UPDATE clubs SET budget=budget-? WHERE club_id=?", (amt, self.user_club_id))
            self._log_finance(c, -amt, f"رواتب {days} يوم")
        c.execute("UPDATE players SET is_injured=0, injury_until=NULL WHERE is_injured=1 AND injury_until<=?", (_fmt(self.current_date),))
        c.execute("UPDATE players SET form=MAX(30, MIN(100, form + ?)) WHERE club_id IS NOT NULL", (random.randint(-5, 5),))

    def _process_board(self, c):
        rows = c.execute("SELECT home_club_id,away_club_id,home_goals,away_goals FROM matches WHERE status='played' AND (home_club_id=? OR away_club_id=?) AND season_id=? ORDER BY match_date DESC LIMIT 5", (self.user_club_id, self.user_club_id, self.active_season_id)).fetchall()
        if not rows: return
        delta = sum(2 if (h == self.user_club_id and hg > ag) or (a == self.user_club_id and ag > hg) else -3 for h, a, hg, ag in rows if hg != ag)
        cur_conf = c.execute("SELECT confidence FROM board_status WHERE club_id=?", (self.user_club_id,)).fetchone()[0]
        new_conf = max(0, min(100, cur_conf + delta))
        c.execute("UPDATE board_status SET confidence=? WHERE club_id=?", (new_conf, self.user_club_id))
        if new_conf <= 0 and not self.is_sacked:
            self.is_sacked = 1
            c.execute("UPDATE game_state SET is_sacked=1 WHERE id=1")

    def _simulate_match(self, mid, hid, aid, comp):
        c = self._conn.cursor()
        c.execute("SELECT tactic, formation, tactical_familiarity FROM clubs WHERE club_id=?", (hid,))
        htac, hform, hfam = c.fetchone()
        c.execute("SELECT tactic, formation, tactical_familiarity FROM clubs WHERE club_id=?", (aid,))
        atac, aform, afam = c.fetchone()

        weather = random.choices(['clear', 'rain', 'hot'], weights=[0.7, 0.2, 0.1])[0]
        c.execute("UPDATE matches SET weather=? WHERE match_id=?", (weather, mid))
        
        def get_power(cid, tactic, form, fam):
            c.execute("SELECT position, AVG(overall_rating * (morale/70.0) * (form/70.0)) FROM players WHERE club_id=? AND is_starter=1 AND is_injured=0 AND suspension_matches=0 GROUP BY position", (cid,))
            d = dict(c.fetchall())
            atk, dfn = (d.get("FWD", 60) + d.get("MID", 60)) / 2, (d.get("DEF", 60) + d.get("GK", 60)) / 2
            fam_mult = 0.8 + (fam / 100) * 0.2
            atk *= fam_mult; dfn *= fam_mult
            if tactic == 'attacking': atk += 3; dfn -= 2
            elif tactic == 'defensive': atk -= 2; dfn += 3
            if form == '4-3-3': atk += 2; dfn -= 2
            elif form == '5-3-2': dfn += 3; atk -= 1
            return atk, dfn

        hA, hD = get_power(hid, htac, hform, hfam)
        aA, aD = get_power(aid, atac, aform, afam)
        w_mult = 0.8 if weather == 'rain' else 0.9 if weather == 'hot' else 1.0

        hg = self._poisson(max(0, (1.35 + (hA - aD) / 20 + 0.3) * w_mult))
        ag = self._poisson(max(0, (1.15 + (aA - hD) / 20) * w_mult))
        if comp in ('cup', 'continental') and hg == ag:
            hg += 1 if random.random() < 0.5 else 0
            ag += 1 if hg == ag else 0

        self._record_events(mid, hid, hg, c, 'goal')
        self._record_events(mid, aid, ag, c, 'goal')
        self._record_cards_and_injuries(mid, hid, c, weather)
        self._record_cards_and_injuries(mid, aid, c, weather)
        
        h_poss = max(30, min(70, int(50 + (hA - aA) / 2 + random.randint(-5, 5))))
        a_poss = 100 - h_poss
        h_shots = hg * 3 + random.randint(2, 8)
        a_shots = ag * 3 + random.randint(2, 8)
        
        motm_name = "لا يوجد"
        if hg != ag:
            winner_id = hid if hg > ag else aid
            motm = c.execute("SELECT first_name||' '||last_name FROM players WHERE club_id=? AND is_starter=1 ORDER BY overall_rating DESC LIMIT 1", (winner_id,)).fetchone()
            if motm: motm_name = motm[0]

        c.execute("UPDATE matches SET home_goals=?,away_goals=?,status='played',attendance=? WHERE match_id=?", (hg, ag, random.randint(5000, 40000), mid))
        rev = c.execute("SELECT ticket_price FROM clubs WHERE club_id=?", (hid,)).fetchone()[0] * random.randint(3000, 30000) * 0.4
        c.execute("UPDATE clubs SET budget=budget+? WHERE club_id=?", (rev, hid))

        hn = c.execute("SELECT name FROM clubs WHERE club_id=?", (hid,)).fetchone()[0]
        an = c.execute("SELECT name FROM clubs WHERE club_id=?", (aid,)).fetchone()[0]
        
        stats_text = f"📊 استحواذ: {h_poss}%-{a_poss}% | تسديدات: {h_shots}-{a_shots} | ⭐ رجل المباراة: {motm_name}"
        return {"result": f"{hn} {hg} - {ag} {an}", "stats": stats_text}

    def _poisson(self, mean):
        L = 2.718281828 ** (-mean)
        k, p = 0, 1.0
        while True:
            k += 1; p *= random.random()
            if p <= L: return k - 1

    def _record_events(self, mid, club_id, count, c, ev_type):
        if count == 0: return
        c.execute("SELECT player_id, position, first_name||' '||last_name FROM players WHERE club_id=? AND is_starter=1 AND is_injured=0 AND suspension_matches=0", (club_id,))
        squad = c.fetchall()
        if not squad: return
        w = {"FWD": 5, "MID": 3, "DEF": 1, "GK": 0}
        pool = []
        for pid, pos, name in squad: pool += [(pid, name)] * w.get(pos, 1)
        if not pool: return
        
        for _ in range(count):
            scorer, s_name = random.choice(pool)
            c.execute("INSERT INTO match_events (match_id,minute,event_type,player_id,club_id,detail) VALUES (?,?,?,?,?,?)", (mid, random.randint(1, 90), ev_type, scorer, club_id, f'هدف: {s_name}'))
            c.execute("UPDATE player_stats SET goals=goals+1 WHERE player_id=?", (scorer,))
            if random.random() < 0.6:
                creator, c_name = random.choice(pool)
                if creator != scorer: c.execute("UPDATE player_stats SET assists=assists+1 WHERE player_id=?", (creator,))

    def _record_cards_and_injuries(self, mid, club_id, c, weather):
        c.execute("SELECT player_id, first_name||' '||last_name, personality FROM players WHERE club_id=? AND is_starter=1", (club_id,))
        for pid, name, pers in c.fetchall():
            if random.random() < 0.08:
                is_red = random.random() < 0.05
                c.execute("INSERT INTO match_events (match_id,minute,event_type,player_id,club_id,detail) VALUES (?,?,?,?,?,?)", (mid, random.randint(10, 90), 'red' if is_red else 'yellow', pid, club_id, f'{"طرد" if is_red else "إنذار"}: {name}'))
                if is_red:
                    c.execute("UPDATE players SET suspension_matches=2 WHERE player_id=?", (pid,))
                    c.execute("UPDATE player_stats SET red_cards=red_cards+1 WHERE player_id=?", (pid,))
                else: c.execute("UPDATE player_stats SET yellow_cards=yellow_cards+1 WHERE player_id=?", (pid,))
            
            inj_chance = 0.03 + (0.02 if weather == 'hot' else 0) + (0.05 if pers == 'injury_prone' else 0)
            if random.random() < inj_chance:
                days = random.randint(7, 42)
                c.execute("UPDATE players SET is_injured=1, injury_until=? WHERE player_id=?", (_fmt(self.current_date + timedelta(days=days)), pid))
                c.execute("INSERT INTO match_events (match_id,minute,event_type,player_id,club_id,detail) VALUES (?,?,?,?,?,?)", (mid, random.randint(10, 90), 'injury', pid, club_id, f'إصابة: {name}'))

    def _check_season_end(self, c, log):
        if c.execute("SELECT COUNT(*) FROM matches WHERE season_id=? AND status='scheduled'", (self.active_season_id,)).fetchone()[0] > 0: return
        st = self.get_standings()
        user_pos = next((i for i, r in enumerate(st, 1) if r["club_id"] == self.user_club_id), 8)
        obj = c.execute("SELECT objective FROM board_status WHERE club_id=?", (self.user_club_id,)).fetchone()[0]
        
        failed = ("الفوز" in obj and user_pos > 1) or ("المنافسة" in obj and user_pos > 3) or ("البقاء" in obj and user_pos > 6)
        if failed and not self.is_sacked:
            self.is_sacked = 1
            c.execute("UPDATE game_state SET is_sacked=1 WHERE id=1")
            log.append({"type": "sacked", "text": "❌ فشلت في تحقيق هدف الإدارة. تمت إقالتك!"})
        
        if not self.is_sacked:
            spon = c.execute("SELECT sponsor_type, sponsor_bonus FROM clubs WHERE club_id=?", (self.user_club_id,)).fetchone()
            if spon[0] == 'performance' and user_pos == 1:
                c.execute("UPDATE clubs SET budget=budget+? WHERE club_id=?", (spon[1], self.user_club_id))
                self._log_finance(c, spon[1], "مكافأة رعاية (تحقيق هدف)")
            c.execute("UPDATE clubs SET sponsor_type='none', sponsor_bonus=0 WHERE club_id=?", (self.user_club_id,))

            c.execute("UPDATE seasons SET is_active=0 WHERE season_id=?", (self.active_season_id,))
            c.execute("INSERT INTO seasons (name,is_active) VALUES (?,1)", (f"موسم {self.current_date.year + 1}/{self.current_date.year + 2}",))
            self.active_season_id = c.lastrowid
            c.execute("UPDATE players SET age=age+1, seasons_at_club=seasons_at_club+1 WHERE club_id IS NOT NULL")
            c.execute("UPDATE clubs SET tactical_familiarity=100")
            
            ids = [r[0] for r in c.execute("SELECT club_id FROM clubs").fetchall()]
            random.shuffle(ids)
            start = _fmt(self.current_date + timedelta(days=30))
            _schedule_league(c, self.active_season_id, ids, start)
            _schedule_cup(c, self.active_season_id, ids, start)
            _schedule_continental(c, self.active_season_id, ids, start)
            for _ in range(random.randint(2, 4)):
                c.execute("INSERT INTO players (first_name,last_name,position,age,overall_rating,potential_rating,club_id,is_youth) VALUES (?,?,?,?,?,?,?,1)", (random.choice(FIRST), random.choice(LAST), random.choice(['DEF','MID','FWD']), random.randint(15,17), random.randint(42,58), random.randint(72,95), self.user_club_id))

    def _check_cup_progression(self, c, comp):
        rounds = {'cup': ['ربع النهائي', 'نصف النهائي', 'النهائي'], 'continental': ['نصف النهائي', 'النهائي']}[comp]
        for i, cur_r in enumerate(rounds):
            if c.execute("SELECT COUNT(*) FROM matches WHERE round_name=? AND competition=? AND season_id=? AND status='scheduled'", (cur_r, comp, self.active_season_id)).fetchone()[0] > 0: return
            matches = c.execute("SELECT home_club_id,away_club_id,home_goals,away_goals FROM matches WHERE round_name=? AND competition=? AND season_id=? AND status='played'", (cur_r, comp, self.active_season_id)).fetchall()
            if not matches: return
            winners = [h if hg > ag else (a if ag > hg else random.choice([h,a])) for h,a,hg,ag in matches]
            if cur_r == 'النهائي':
                if winners: c.execute(f"UPDATE seasons SET {'cup_winner_id' if comp == 'cup' else 'continental_winner_id'}=? WHERE season_id=?", (winners[0], self.active_season_id))
                return
            nxt = rounds[i + 1]
            if c.execute("SELECT COUNT(*) FROM matches WHERE round_name=? AND competition=? AND season_id=?", (nxt, comp, self.active_season_id)).fetchone()[0] > 0: continue
            nd = _fmt(self.current_date + timedelta(days=14))
            for j in range(0, len(winners), 2):
                if j + 1 < len(winners): c.execute("INSERT INTO matches (season_id,competition,round_name,match_date,home_club_id,away_club_id) VALUES (?,?,?,?,?,?)", (self.active_season_id, comp, nxt, nd, winners[j], winners[j+1]))