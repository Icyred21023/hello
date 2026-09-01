import re
import math
import helpers
from collections import defaultdict, OrderedDict



p = helpers.create_path("hero_data_keys.json")
data = helpers.load_json(p)
DATA = data['data']['items']
p = helpers.create_path("mvp_index.json")
MVP_INDEX = helpers.load_json(p)
MVP_DICT = MVP_INDEX[0]['Rows']['mvp_index']
DEFAULT_STANDARD = MVP_DICT['DefaultStandardScore']
STANDARD_LIST = MVP_DICT['StandardScore']


class Player2:
    def __init__(self, name, json_data):
        self.best_hero = None
        self.score_hero1 = None
        self.score_hero2 = None
        self.score_hero3 = None
        self.ranking = None         # 1, 2, 3, ...
        self.final_score = None   # numeric score
        self.overall_score = None # normalized weighted overall
        self.char1_score = None 
        self.bPrivate = True if json_data['data']['userInfo']['isPremium'] == 69 else False

        sorted_heros = self.sort_by_time(json_data)

        roles_data = self.getRolesData(json_data)
        best_role, second_best_role, second_best_role_data, total_matches_played = self.getBestRole(roles_data)
        self.setBestRole(best_role, second_best_role_data,total_matches_played)
        self.setMatchHistory(json_data)

        heroes = self.getHerosList(json_data)
        time_sorted_heroes = self.sortHeroesbyTime(heroes)
        heroes_dict_by_role = self.getRoleSortedHeroLists(time_sorted_heroes)
        best_role_heroes, second_best_role_hero = self.createHeroDict(heroes_dict_by_role, second_best_role)


        best = self.extractHeroNew(best_role_heroes, 0)
        if best:
            (heroname, role,  kd, kda, damage, damage_min, healing, healing_min, dam_blocked,
                final_hits, mvp_amount, matches_played, matches_won,win_pct, deaths) = best
        # top2 = self.getBestHerosv11(heroes)

        # best = self.extractHero(top2, 1)
        # if best:
        #     (heroname, role, score, kd, kda, damage, damage_min, healing,healing_min, dam_blocked,
        #     final_hits, mvp_amount, mvp_score, kd_score,
        #     matches_played, matches_won, win_pct, deaths) = best
        matches_played = self.smart_round(matches_played,0)
        self.getPlayerOverviewStats(json_data)
        ranked_seg = next(seg for seg in json_data["data"]["segments"] if seg.get("type") == "ranked-peaks")

        self.rank_season_string = ranked_seg["stats"]["lifetimePeakRanked"]["metadata"]["seasonShortName"]
        self.rank = self.strip_rank_tier(ranked_seg["stats"]["lifetimePeakRanked"]["metadata"]["tierName"])

        # self.rank_season_string = json_data["data"]["segments"][1]["stats"]["lifetimePeakRanked"]["metadata"]["seasonShortName"]
        # self.rank = self.strip_rank_tier(json_data["data"]["segments"][1]["stats"]["lifetimePeakRanked"]["metadata"]["tierName"])
        self.ace = False
        self.hero1 = heroname
        self.finalhits1 = final_hits
        self.win_pct1 = win_pct
        self.matches_played1 = matches_played
        self.name = name
        overview = json_data['data']['segments'][0]['stats']
        #self.playermvp = self.getCharMvps(overview)
        if role == "Strategist":
            self.string1 = "HPM"
            self.string1 = "Heals"
            self.dpm1 = round(healing_min,0)
            self.kdstring1 = "KDA Ratio"
            self.kd1 = round(kda,1)
            
        else:
            self.string1 = "DPM"
            self.string1 = "Damage"
            self.dpm1 = round(damage_min,0)
            self.kdstring1 = "KD Ratio"
            self.kd1 = round(kd,1)
        #char = sorted_heros[0]['stats']
        self.mvp1 = self.getCharMvps(matches_won, mvp_amount)
        
        self.score1 = 55

        self.hero2 = "Null"
        self.string2 = "Null"
        self.dpm2 = 0
        self.kd2 = 0
        if len(best_role_heroes) > 1:
            best = self.extractHeroNew(best_role_heroes, 1)
            if best:
                (heroname, role,  kd, kda, damage, damage_min, healing, healing_min, dam_blocked,
                final_hits, mvp_amount, matches_played, matches_won,win_pct, deaths) = best

            self.hero2 = heroname
            if role == "Strategist":
                self.string2 = "Heals"
                self.dpm2 = round(healing_min,0)
                self.kdstring2 = "KDA Ratio"
                self.kd2 = round(kda,1)
            else:
                self.string2 = "Damage"
                self.dpm2 = round(damage_min,0)
                self.kdstring2 = "KD Ratio"
                self.kd2 = round(kd,1)
            char = sorted_heros[1]['stats']
            self.mvp2 = self.getCharMvps(matches_won, mvp_amount)
            
            self.finalhits2 = final_hits 
            self.win_pct2 = win_pct
            self.matches_played2 = matches_played
            self.score2 = 50
        else:
            print()
        self.hero3 = "Null"
        self.string3 = "Null"
        self.dpm3 = 0
        self.kd3 = 0
        if second_best_role_hero:
            best = self.extractHeroNew(second_best_role_hero, 0)
            if best:
                (heroname, role,  kd, kda, damage, damage_min, healing, healing_min, dam_blocked,
                final_hits, mvp_amount, matches_played, matches_won,win_pct, deaths) = best
            self.hero3 = heroname
            if role == "Strategist":
                self.string3 = "Heals"
                self.dpm3 = round(healing_min,0)
                self.kdstring3 = "KDA Ratio"
                self.kd3 = round(kda,1)
            else:
                self.string3 = "Damage"
                self.dpm3 = round(damage_min,0)
                self.kdstring3 = "KD Ratio"
                self.kd3 = round(kd,1)
            char = sorted_heros[1]['stats']
            self.mvp3 = self.getCharMvps(matches_won, mvp_amount)
            
            self.finalhits3 = final_hits 
            self.win_pct3 = win_pct
            self.matches_played3 = matches_played

        # self.hero1 = sorted_heros[0]["metadata"]["name"]

        # self.name = name
        # self.rank_season_string = json_data["data"]["segments"][1]["stats"]["lifetimePeakRanked"]["metadata"]["seasonShortName"]
        # self.rank = self.strip_rank_tier(json_data["data"]["segments"][1]["stats"]["lifetimePeakRanked"]["metadata"]["tierName"])
        # self.ace = False
        # overview = json_data['data']['segments'][0]['stats']
        # self.playermvp = self.getCharMvps(overview)
        # if sorted_heros[0]["metadata"]["roleName"] == "Strategist":
        #     self.string1 = "Healing/Min"
        #     self.dpm1 = sorted_heros[0]["stats"]["totalHeroHealPerMinute"]["value"]
            
        # else:
        #     self.string1 = "Damage/Min"
        #     self.dpm1 = sorted_heros[0]["stats"]["totalHeroDamagePerMinute"]["value"]
        # char = sorted_heros[0]['stats']
        # self.mvp1 = self.getCharMvps(char)
        # self.kd1 = round(sorted_heros[0]["stats"]["kdRatio"]["value"],2)
        # self.hero2 = "Null"
        # self.string2 = "Null"
        # self.dpm2 = 0
        # self.kd2 = 0
        # if len(sorted_heros) > 1:
        #     self.hero2 = sorted_heros[1]["metadata"]["name"]
        #     if sorted_heros[1]["metadata"]["roleName"] == "Strategist":
        #         self.string2 = "Healing/Min"
        #         self.dpm2 = sorted_heros[1]["stats"]["totalHeroHealPerMinute"]["value"]
        #     else:
        #         self.string2 = "Damage/Min"
        #         self.dpm2 = sorted_heros[1]["stats"]["totalHeroDamagePerMinute"]["value"]
        #     char = sorted_heros[1]['stats']
        #     self.mvp2 = self.getCharMvps(char)
        #     self.kd2 = round(sorted_heros[1]["stats"]["kdRatio"]["value"],2)
    def createHeroDict(self, heros, second_best_role):
        
        best_r = self._roleName.lower()
        if self._role2Name is not None:
            second_best_role = self._role2Name.lower()
        
        best_appended = 0
        second_appended = 0

        best_heroes = heros[best_r]
        if second_best_role is not None and second_best_role in heros:
            
            second_best_heroes = heros[second_best_role]
        
            second_best_heroes = second_best_heroes[:1]
        else:
            second_best_heroes = None
        best_heroes = best_heroes[:2]
        return best_heroes, second_best_heroes
        


        hero_dict = {best_r: {}, second_best_r: {}}
        role_list = [best_r, second_best_r]
        for hero in heros:
            
            name = hero['metadata']['name']
            role = hero['metadata']['roleName']
            if role not in role_list:
                continue
            if role == best_r:
                if best_appended > 1:
                    continue
            if role == second_best_r:
                if second_appended > 0:
                    continue
            stats = hero['stats']
            hero_dict[name] = hero
        return hero_dict
    def setMatchHistory(self, json_data):
        matches = json_data['data'].get('matches', [])
        if len(matches) == 0:
            self.match_history = None
            return
        elif len(matches) <= 7 :
            self.match_history = matches
            return
        else:
            count = 0
            sorted_matches = []
            for match in matches:
                if count >=7:
                    break
                if len(match['segments'][0]['metadata']['heroes']) > 0:
                    sorted_matches.append(match)
                    count += 1
                continue
            matches = sorted_matches
        self.match_history = matches


    def setBestRole(self, best_role, second_best_role, total_matches_played):
        #role 1
        self._roleName = best_role["metadata"]["name"]
        self._roleMatchesPlayed = best_role["stats"]["matchesPlayed"]["value"]
        self._roleUsagePct = round((self._roleMatchesPlayed / total_matches_played) * 100) if total_matches_played > 0 else 0
        self._roleTimePlayed = best_role["stats"]["timePlayed"]["value"]
        self._roleHealing = best_role["stats"]["totalHeroHealPerMinute"]["value"]
        self._roleDamage = best_role["stats"]["totalHeroDamagePerMinute"]["value"]
        self._roleDamageTaken = best_role["stats"]["totalDamageTakenPerMinute"]["value"]
        self._roleMvps = best_role["stats"]["totalMvp"]["value"]
        


        self._roleWinPct = best_role["stats"]["matchesWinPct"]["value"]
        self._roleKdRatio = best_role["stats"]["kdRatio"]["value"]
        self._roleKdaRatio = best_role["stats"]["kdaRatio"]["value"]

        # Role 2
        self._role2Name = None
        self._role2MatchesPlayed = None
        self._role2TimePlayed = None
        self._role2Healing = None
        self._role2Damage = None
        self._role2DamageTaken = None
        self._role2Mvps = None
        self._role2WinPct = None
        self._role2KdRatio = None
        self._role2KdaRatio = None
        self._role2UsagePct = 0

        if second_best_role is not None:
            self._role2Name = second_best_role["metadata"]["name"]
            self._role2MatchesPlayed = second_best_role["stats"]["matchesPlayed"]["value"]
            self._role2UsagePct = round((self._role2MatchesPlayed / total_matches_played) * 100) if total_matches_played > 0 else 0
            self._role2TimePlayed = second_best_role["stats"]["timePlayed"]["value"]
            self._role2Healing = second_best_role["stats"]["totalHeroHealPerMinute"]["value"]
            self._role2Damage = second_best_role["stats"]["totalHeroDamagePerMinute"]["value"]
            self._role2DamageTaken = second_best_role["stats"]["totalDamageTakenPerMinute"]["value"]
            self._role2Mvps = second_best_role["stats"]["totalMvp"]["value"]


            self._role2WinPct = second_best_role["stats"]["matchesWinPct"]["value"]
            self._role2KdRatio = second_best_role["stats"]["kdRatio"]["value"]
            self._role2KdaRatio = second_best_role["stats"]["kdaRatio"]["value"]

    def getBestRole(self, roles_data):
        roles_data = sorted(
    roles_data,
    key=lambda d: d["stats"]["matchesPlayed"]["value"],
    reverse=True
)
        best_role = None
        second_best_role = None
        second_best_role_data = None
        second_most_matches = -100
        total_matches_played = 0
        most_matches = -100
        for role_segment in roles_data:
            role_name = role_segment["metadata"]["name"]
            role_matches_played = role_segment["stats"]["matchesPlayed"]["value"]
            total_matches_played += role_matches_played
        if len(roles_data) >= 2:
            first = roles_data[0]
            second = roles_data[1]
            nam = second["metadata"]["name"]
        else:
            first = roles_data[0]
            second = None
            nam = None

        return first, nam, second, total_matches_played
        #     if role_matches_played > most_matches:
        #         if role_matches_played - 5 <= most_matches and most_matches >= 7:
        #             current_winpct = role_segment["stats"]["matchesWinPct"]["value"]
        #             current_kd = role_segment["stats"]["kdRatio"]["value"]
        #             best_winpct = best_role["stats"]["matchesWinPct"]["value"]
        #             best_kd = best_role["stats"]["kdRatio"]["value"]
        #             if current_kd > best_kd and current_winpct > best_winpct:
        #                 kddiff = current_kd - best_kd
        #                 windiff = current_winpct - best_winpct
        #                 if kddiff >= 0.25 and windiff >= 2.5:
        #                     if best_role is not None:
        #                         second_best_role = best_role["metadata"]["name"]
        #                         second_best_role_data = best_role
        #                     most_matches = role_matches_played
        #                     best_role = role_segment
        #                     continue
        #             elif best_kd > current_kd and best_winpct > current_winpct:
        #                 kddiff = best_kd - current_kd
        #                 windiff = best_winpct - current_winpct
        #                 if kddiff >= 0.25 and windiff >= 2.5:
        #                     continue
        #             elif current_kd > best_kd and current_winpct < best_winpct:
        #                 kddiff = current_kd - best_kd
        #                 windiff = best_winpct - current_winpct
        #                 if kddiff >= 0.25 and windiff <= 2.5:
        #                     if best_role is not None:
        #                         second_best_role = best_role["metadata"]["name"]
        #                         second_best_role_data = best_role
        #                     most_matches = role_matches_played
        #                     best_role = role_segment
        #                     continue
        #             elif current_kd < best_kd and current_winpct > best_winpct:
        #                 kddiff = best_kd - current_kd
        #                 windiff = current_winpct - best_winpct
        #                 if kddiff <= 0.25 and windiff >= 2.5:
        #                     if best_role is not None:
        #                         second_best_role = best_role["metadata"]["name"]
        #                         second_best_role_data = best_role
        #                     most_matches = role_matches_played
        #                     best_role = role_segment
        #                     continue
        #             elif best_kd > current_kd and best_winpct < current_winpct:
        #                 kddiff = best_kd - current_kd
        #                 windiff = current_winpct - best_winpct
        #                 if kddiff >= 0.25 and windiff <= 2.5:
        #                     continue
        #             elif best_kd < current_kd and best_winpct > current_winpct:
        #                 kddiff = current_kd - best_kd
        #                 windiff = best_winpct - current_winpct
        #                 if kddiff <= 0.25 and windiff >= 2.5:
        #                     continue
        #             elif best_kd < current_kd and best_winpct < current_winpct:
        #                 kddiff = current_kd - best_kd
        #                 windiff = current_winpct - best_winpct
        #                 if kddiff >= 0.25 and windiff >= 2.5:
        #                     continue
        #             else:
        #                 if best_role is not None:
        #                     second_best_role = best_role["metadata"]["name"]
        #                     second_best_role_data = best_role
        #                 most_matches = role_matches_played
        #                 best_role = role_segment
        #                 continue
        #         else:
        #             if best_role is not None:
        #                 second_best_role = best_role["metadata"]["name"]
        #                 second_best_role_data = best_role
        #             most_matches = role_matches_played
        #             best_role = role_segment

        #     else:
        #         if second_best_role is None:

        #             second_best_role = role_segment["metadata"]["name"]
        #             second_best_role_data = role_segment
        #             second_most_matches = role_matches_played
        #         else:
        #             if role_matches_played > second_most_matches:
        #                 second_best_role = role_segment["metadata"]["name"]
        #                 second_best_role_data = role_segment
        #                 second_most_matches = role_matches_played
        #             else:
        #                 continue
        # return best_role, second_best_role, second_best_role_data, total_matches_played
           
    def getRolesData(self, data):
        roles = []
        for segment in data["data"]["segments"]:
            if segment["type"] == "hero-role":
                roles.append(segment)
        return roles    
    def getHerosList(self,dat):
            heros = []
            for segment in dat["data"]["segments"]:
                if segment["type"] == "hero":
                    heros.append(segment)
            return heros       

    def smart_round(self, value, ndigits=0):
            if value < 1:
                # round up to the next integer (ceiling)
                return math.ceil(value)
            else:
                # normal rounding
                return round(value, ndigits)
             
    def getBestHeros(self, heros):
        hero_results = []

        for hero in heros:
            stats = hero['stats']
            name = hero['metadata']['name']
            matches_played = stats['matchesPlayed']['value']
            role = hero['metadata']['roleName']
            deaths = stats['deaths']['value']
            matches_won = stats['matchesWon']['value']
            win_pct = stats['matchesWinPct']['value']
            win_pct = str(int(round(win_pct))) + '%'
            kd = stats['kdRatio']['value']
            kda = stats['kdaRatio']['value']
            timeplayed = stats['timePlayed']['value']
            damage = stats['totalHeroDamage']['value']
            damage_min = int(round(stats['totalHeroDamagePerMinute']['value']))
            healing = stats['totalHeroHeal']['value']
            healing_min = int(round(stats['totalHeroHealPerMinute']['value']))
            dam_blocked = stats['totalDamageTaken']['value']
            final_hits = stats['lastKills']['value']
            mvp_amount = stats['totalMvp']['value']
            if matches_played == 0:
                continue
            elif matches_played < 1:
                matches_played = 1
            matches_played = self.smart_round(matches_played,0)
            # calculate scores
            mvp_score = self.mvp_score(matches_won, mvp_amount)
            kd_score = self.kd_score(3, 30, matches_played)
            matches_played2 = timeplayed / 600
            matches_score = (1-(1-0.05)**matches_played2)
            if matches_played2 < 1:
                matches_played2 = 1

            check_nulls = [final_hits, damage, dam_blocked, healing]
            check_nulls = [0 if v is None else v for v in check_nulls]
            final_hits, damage, dam_blocked, healing = check_nulls
            score = (
                ((final_hits / matches_played2) * 1110) +
                (damage / matches_played2) +
                ((dam_blocked / matches_played2) / 1.6) +
                ((healing / matches_played2) / 0.9) +
                (matches_score * 15000)
               #(mvp_score * 15000) 
              # (kd_score * 500)
            )
            hi = final_hits / matches_played2
            hero_results.append({
                "name": name,
                "role": role,
                "matches_time": matches_played2,
                "score": score,
                "matches_score": matches_score* 12000,
                "damage_score":  (damage / matches_played2),
                "lasthit_score": ((final_hits / matches_played2) * 1110),
                "damage_blocked_score": ((dam_blocked /matches_played2) / 1.6),
                "healing_score": ((healing / matches_played2) / 0.9),
                "kd": kd,
                "kda": kda,
                "damage": damage,
                "damage_min": damage_min,
                "healing": healing,
                "healing_min": healing_min,
                "dam_blocked": dam_blocked,
                "final_hits": int(round(hi,0)),
                "mvp_amount": mvp_amount,
                "mvp_score": mvp_score,
                "kd_score": kd_score,
                "matches_played": int(round(matches_played,0)),
                "matches_won": matches_won,
                "win_pct": win_pct,
                "deaths": deaths
            })
        self.result = hero_results
        # sort descending by score
        hero_results.sort(key=lambda x: x["score"], reverse=True)

        # take the top 2
        return hero_results[:2]
    
    def getBestHerosv11(self, heros):
        hero_results = []

        for hero in heros:
            stats = hero['stats']
            name = hero['metadata']['name']
            matches_played = stats['matchesPlayed']['value']
            role = hero['metadata']['roleName']
            deaths = stats['deaths']['value']
            kills = stats['kills']['value']
            matches_won = stats['matchesWon']['value']
            win_pct = stats['matchesWinPct']['value']
            win_pct = str(int(round(win_pct))) + '%'
            kd = stats['kdRatio']['value']
            kda = stats['kdaRatio']['value']
            timeplayed = stats['timePlayed']['value']
            damage = stats['totalHeroDamage']['value']
            damage_min = int(round(stats['totalHeroDamagePerMinute']['value']))
            healing = stats['totalHeroHeal']['value']
            healing_min = int(round(stats['totalHeroHealPerMinute']['value']))
            dam_blocked = stats['totalDamageTaken']['value']
            final_hits = stats['lastKills']['value']
            mvp_amount = stats['totalMvp']['value']
            if matches_played == 0:
                continue
            elif matches_played < 1:
                matches_played = 1
            matches_played = self.smart_round(matches_played,0)
            # calculate scores
            mvp_score = self.mvp_score(matches_won, mvp_amount)
            kd_score = self.kd_score(3, 30, matches_played)
            matches_played2 = timeplayed / 600
            matches_score = (1-(1-0.05)**matches_played2)
            if matches_played2 < 1:
                matches_played2 = 1

            check_nulls = [final_hits, damage, dam_blocked, healing]
            check_nulls = [0 if v is None else v for v in check_nulls]
            final_hits, damage, dam_blocked, healing = check_nulls
            if timeplayed == 0:
                timeplayed = 1  
            if matches_played2 == 0:
                matches_played2 = 10
            score = (
                ((matches_played * 1500)) +
                ((kd * 10000)) +
                ((kills / (timeplayed / 600)) * 1250) +
                (damage / matches_played2) +
                #((dam_blocked / matches_played2) / 3) +
                ((healing / matches_played2) / 2) +
                (matches_score * 15000)+
               (mvp_amount * 6000) 
              # (kd_score * 500)
            )
            score = (
                (matches_played*1500) +
                (kills/ matches_played2 *1500) 
            )
            hi = final_hits / matches_played2
            hero_results.append({
                "name": name,
                "role": role,
                "matches_time": matches_played2,
                "score": score,
                "matches_score": matches_score* 12000,
                "damage_score":  (damage / matches_played2),
                "lasthit_score": ((final_hits / matches_played2) * 1110),
                "damage_blocked_score": ((dam_blocked /matches_played2) / 1.6),
                "healing_score": ((healing / matches_played2) / 0.9),
                "kd": kd,
                "kda": kda,
                "damage": damage,
                "damage_min": damage_min,
                "healing": healing,
                "healing_min": healing_min,
                "dam_blocked": dam_blocked,
                "final_hits": int(round(hi,0)),
                "mvp_amount": mvp_amount,
                "mvp_score": mvp_score,
                "kd_score": kd_score,
                "matches_played": int(round(matches_played,0)),
                "matches_won": matches_won,
                "win_pct": win_pct,
                "deaths": deaths
            })
        self.result = hero_results
        # sort descending by score
        hero_results.sort(key=lambda x: x["score"], reverse=True)

        # take the top 2
        return hero_results[:2]
    
    def getBestHeros2(self, heros):
        hero_results = []

        for hero in heros:
            stats = hero['stats']
            name = hero['metadata']['name']
            matches_played = stats['matchesPlayed']['value']
            role = hero['metadata']['roleName']
            deaths = stats['deaths']['value']
            matches_won = stats['matchesWon']['value']
            win_pct = stats['matchesWinPct']['value']
            win_pct = str(int(round(win_pct))) + '%'
            kd = stats['kdRatio']['value']
            kda = stats['kdaRatio']['value']
            timeplayed = stats['timePlayed']['value']
            damage = stats['totalHeroDamage']['value']
            damage_min = int(round(stats['totalHeroDamagePerMinute']['value']))
            healing = stats['totalHeroHeal']['value']
            healing_min = int(round(stats['totalHeroHealPerMinute']['value']))
            dam_blocked = stats['totalDamageTaken']['value']
            final_hits = stats['lastKills']['value']
            mvp_amount = stats['totalMvp']['value']

            hero_key = None
            for dicty in DATA:
                n = dicty["name"]
                n = n.lower()
                if n == name:
                    hero_key = dicty["key"]
                    break
            if hero_key is None:
                print(f"Hero key not found for player: {name}")
                break
            else:
                standard_score = None
                for standard in STANDARD_LIST:
                    if standard['Key'] == hero_key:
                        standard_score = standard['Value']
                        break
                if standard_score is None:
                    print(f"Standard score not found for hero key: {hero_key}")
                    standard_score = DEFAULT_STANDARD
            if one is None:
                name1 = name
                std1 = standard_score
                one = True
            else:
                name2 = name
                std2 = standard_score
            heroes = {
            name1: dict(kills=15,deaths=7,assists=1,damage=12023,healing=0,damage_taken=6648,final_hits=10,std=std1),
            name2: dict(kills=11,deaths=7,assists=2,damage=8899,healing=0,damage_taken=33511,final_hits=6,std=std2)
            }


            if matches_played == 0:
                continue
            elif matches_played < 1:
                matches_played = 1
            matches_played = self.smart_round(matches_played,0)
            # calculate scores
            mvp_score = self.mvp_score(matches_won, mvp_amount)
            kd_score = self.kd_score(3, 30, matches_played)
            matches_played2 = timeplayed / 600
            matches_score = (1-(1-0.05)**matches_played2)
            if matches_played2 < 1:
                matches_played2 = 1

            check_nulls = [final_hits, damage, dam_blocked, healing]
            check_nulls = [0 if v is None else v for v in check_nulls]
            final_hits, damage, dam_blocked, healing = check_nulls
            score = (
                ((final_hits / matches_played2) * 1110) +
                (damage / matches_played2) +
                ((dam_blocked / matches_played2) / 1.6) +
                ((healing / matches_played2) / 0.9) +
                (matches_score * 15000)
               #(mvp_score * 15000) 
              # (kd_score * 500)
            )
            hi = final_hits / matches_played2
            hero_results.append({
                "name": name,
                "role": role,
                "matches_time": matches_played2,
                "score": score,
                "matches_score": matches_score* 12000,
                "damage_score":  (damage / matches_played2),
                "lasthit_score": ((final_hits / matches_played2) * 1110),
                "damage_blocked_score": ((dam_blocked /matches_played2) / 1.6),
                "healing_score": ((healing / matches_played2) / 0.9),
                "kd": kd,
                "kda": kda,
                "damage": damage,
                "damage_min": damage_min,
                "healing": healing,
                "healing_min": healing_min,
                "dam_blocked": dam_blocked,
                "final_hits": int(round(hi,0)),
                "mvp_amount": mvp_amount,
                "mvp_score": mvp_score,
                "kd_score": kd_score,
                "matches_played": int(round(matches_played,0)),
                "matches_won": matches_won,
                "win_pct": win_pct,
                "deaths": deaths
            })
        self.result = hero_results
        # sort descending by score
        hero_results.sort(key=lambda x: x["score"], reverse=True)

        # take the top 2
        return hero_results[:2]
    def extractHeroNew(self,hero_list, index=0):
        hero = hero_list[index]
        stats = hero['stats']
        name = hero['metadata']['name']
        matches_played = stats['matchesPlayed']['value']
        matches_played = self.smart_round(matches_played,0)
        role = hero['metadata']['roleName']
        deaths = stats['deaths']['value']
        matches_won = stats['matchesWon']['value']
        win_pct = stats['matchesWinPct']['value']
        win_pct = str(int(round(win_pct))) + '%'
        kd = stats['kdRatio']['value']
        kda = stats['kdaRatio']['value']
        timeplayed = stats['timePlayed']['value']
        damage = stats['totalHeroDamage']['value']
        damage_min = int(round(stats['totalHeroDamagePerMinute']['value']))
        healing = stats['totalHeroHeal']['value']
        healing_min = int(round(stats['totalHeroHealPerMinute']['value']))
        dam_blocked = stats['totalDamageTaken']['value']
        final_hits = stats['lastKills']['value']
        mvp_amount = stats['totalMvp']['value']
        return (name, role,  kd, kda, damage, damage_min, healing, healing_min, dam_blocked,
                final_hits, mvp_amount, matches_played, matches_won,win_pct, deaths)
    def extractHero(self,top2, index=1):
        """
        Extract hero data from top2 list.
        index = 1 → best hero, index = 2 → second best hero.
        Returns all values individually as variables (tuple unpacking).
        """
        if not top2 or index < 1 or index > len(top2):
            return None

        hero = top2[index - 1]  # 1-based index → 0 or 1

        # break out each field into a variable
        name           = hero["name"]
        role           = hero["role"]
        score          = hero["score"]
        kd             = hero["kd"]
        kda            = hero["kda"]
        damage         = hero["damage"]
        damage_min     = hero["damage_min"]
        healing        = hero["healing"]
        healing_min    = hero["healing_min"]
        dam_blocked    = hero["dam_blocked"]
        final_hits     = hero["final_hits"]
        mvp_amount     = hero["mvp_amount"]
        mvp_score      = hero["mvp_score"]
        kd_score       = hero["kd_score"]
        matches_played = hero["matches_played"]
        matches_won    = hero["matches_won"]
        win_pct        = hero["win_pct"]
        deaths         = hero["deaths"]

        # return all individually (caller can unpack)
        return (name, role, score, kd, kda, damage, damage_min, healing, healing_min, dam_blocked,
                final_hits, mvp_amount, mvp_score, kd_score,
                matches_played, matches_won,win_pct, deaths)
        
        # Add other values
    def getPlayerMvps(self,ov):
        print("")
        return
    
    def getSeasonByID(self, seasons, season_id):
        for season in seasons:
            if season['id'] == season_id:
                return season['shortName']
        return None
    
    def getPlayerOverviewStats(self, data):
        metadata = data['data']['metadata']
        seasons = metadata['seasons']
        ov = data['data']['segments'][0]
        seasons_list = data['data']['seas']
        sea_str = None
        combo = ''
        snum1 = ''
        snum2 = ''
        if seasons_list and len(seasons_list) >=1:
            for sid in seasons_list:
                
                    sea_str = self.getSeasonByID(seasons, int(sid))
                    if snum1 == '':
                        snum1 = sea_str[1:]
                    elif snum2 == '':
                        snum2 = sea_str[1:]
                    else:
                        print("")
                    if combo == '':
                        combo = sea_str 
                    else:
                        combo = combo + '   +   ' + sea_str
               
                
        current_seasonID = ov['attributes']['season']
        season_string = self.getSeasonByID(seasons, current_seasonID)
        if season_string is None:
            season_string = "N/A"
        if combo == '':
            combo = "N/A"

        # Class Attribute Set
        self._current_season = combo
        self._season1 = snum1
        self._season2 = snum2
        # Done with season string

        stats = None
        for seg in data['data']['segments']:
            if seg.get('type') == 'overview':
                stats = seg['stats']
                break
        matches_played = str(stats['matchesPlayed']['value'])
        matches_won_pct = str(int(round(stats['matchesWinPct']['value']))) + '%'
        kda = str(round(stats['kdaRatio']['value'], 2))
        kd = str(round(stats['kdRatio']['value'], 1))
        mvpPct = str(int(round(stats['totalMvpPct']['value']))) + '%'
        current_rank = self.strip_rank_tier(stats['ranked']['metadata']['tierName'])
        self._matches_played = matches_played
        self._matches_won_pct = matches_won_pct
        self._kda = kda
        self._kd = kd
        self._mvpPct = mvpPct
        self._current_rank = current_rank
        self.playermvp = mvpPct
        
    def getCharMvps(self,matches, mvps):
        if matches == 0:
            return "0%"
        if mvps > matches:
            return "100%"
        pct = str(int(round((mvps / matches) * 100))) + '%'

        
        
        return pct
        
    def strip_rank_tier(self, rank_str):
        # Match everything except the trailing Roman numeral (if present)
        return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)
    def sort_by_time(self, data):
        segments = data["data"]["segments"]
        hero_segments = [segment for segment in segments if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["matchesPlayed"]["value"], reverse=True)
        return sorted_heroes
    
    def sortHeroesbyTime(self, data):
        sorted_heroes = sorted(data, key=lambda x: x["stats"]["matchesPlayed"]["value"], reverse=True)
        return sorted_heroes
    
    def getRoleSortedHeroLists(self, entries):
        groups = OrderedDict()

        for entry in entries:
            role = entry["attributes"]["role"]
            if role not in groups:
                groups[role] = []
            groups[role].append(entry)

        return groups   # ← keep role → list mapping
    
    def __repr__(self):
        return f"Player(name={self.name}, rank={self.rank})"
    
    



    def mvp_score(self,matches_won, mvp_amount, k=20, damp="power", gamma=0.2, s=10):
        """
        Shrunken MVP score for a single player.
        
        matches_won : int or float
        mvp_amount  : int or float
        k           : prior strength (larger = stronger pull toward 0)
        damp        : 
            "none"  -> no volume reward, pure shrunken rate
            "power" -> n**gamma (small gamma like 0.1–0.3)
            "exp"   -> 1 - exp(-n/s), saturates after ~s wins
        gamma       : exponent if damp="power"
        s           : scale for damp="exp"
        """
        n, m = matches_won, mvp_amount

        # Shrunken MVP rate, pulled toward 0
        r_hat = m / (n + k) if (n + k) > 0 else 0.0

        # Dampening for match count
        if damp == "none":
            factor = 1.0
        elif damp == "power":
            factor = (n ** gamma) if n > 0 else 0.0
        elif damp == "exp":
            factor = 1.0 - math.exp(-n / s) if n > 0 else 0.0
        else:
            raise ValueError("damp must be 'none', 'power', or 'exp'")

        return r_hat * factor
    
    def kd_score(self,kd, deaths, matches, k=1, gamma_m=0.15, s_d=5):
        kd_shrunk = (kd * deaths + k * 1.0) / (deaths + k) if deaths + k > 0 else 1.0
        match_factor = matches ** gamma_m if matches > 0 else 0.0
        death_factor = 1.0 - math.exp(-deaths / s_d) if deaths > 0 else 0.0
        return kd_shrunk * match_factor * death_factor