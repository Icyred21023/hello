import re
import math
import helpers
from collections import  defaultdict, OrderedDict
from typing import List, Dict, Optional


class Overview:
    def __init__(self):
        
        
        self.kills = 0
        self.assists = 0
        self.deaths = 0
        self.kd_ratio = 0
        self.kda_ratio = 0
        self.total_damage = 0
        self.total_healing = 0
        self.mvps = 0
        self.mvp_pct = '0%'
        self.damage_per_minute = 0
        self.svps = 0
        self.svp_pct = '0%'
        self.healing_per_minute = 0
        self.total_damage_taken = 0
        self.total_damage_taken_per_minute = 0
        self.last_kills = 0
        self.head_kills = 0
        self.solo_kills = 0
        self.matches_played = 0
        self.matches_won = 0
        self.win_pct = '0%'
        self.time_played = 0

    def addOverviewData(self, overview_data):
        overview_stats = overview_data['stats']
        self.kills += overview_stats['kills']['value']
        self.assists += overview_stats['assists']['value']
        self.deaths += overview_stats['deaths']['value']
        #self.kd_ratio = overview_stats['kdRatio']['value']
        #self.kda_ratio = overview_stats['kdaRatio']['value']
        self.total_damage += overview_stats['totalHeroDamage']['value']
        self.total_healing += overview_stats['totalHeroHeal']['value']
        self.mvps += overview_stats['totalMvp']['value']
        #self.mvp_pct = str(int(round(overview_stats['totalMvpPct']['value']))) + '%'
        #self.damage_per_minute = int(round(overview_stats['totalHeroDamagePerMinute']['value']))
        self.svps += overview_stats['totalSvp']['value']
        #self.svp_pct = str(int(round(overview_stats['totalSvpPct']['value']))) + '%'
        #self.healing_per_minute = int(round(overview_stats['totalHeroHealPerMinute']['value']))
        self.total_damage_taken += overview_stats['totalDamageTaken']['value']
        #self.total_damage_taken_per_minute = int(round(overview_stats['totalDamageTakenPerMinute']['value']))
        self.last_kills += overview_stats['lastKills']['value']
        self.head_kills += overview_stats['headKills']['value']
        self.solo_kills += overview_stats['soloKills']['value']
        self.matches_played += overview_stats['matchesPlayed']['value']
        self.matches_won += overview_stats['matchesWon']['value']
        #self.win_pct = str(int(round(overview_stats['matchesWinPct']['value']))) + '%'
        self.time_played += overview_stats['timePlayed']['value']
        self.calculateValues()

    def calculateValues(self):

        # KD
        self.kd_ratio = (
            round(self.kills / self.deaths, 2)
            if self.deaths > 0
            else float(self.kills)
        )

        # KDA
        self.kda_ratio = (
            round((self.kills + self.assists) / self.deaths, 2)
            if self.deaths > 0
            else float(self.kills + self.assists)
        )

        # MVP %
        self.mvp_pct = (
            str(int(round((self.mvps / self.matches_played) * 100))) + '%'
            if self.matches_played > 0
            else '0%'
        )

        # SVP %
        self.svp_pct = (
            str(int(round((self.svps / self.matches_played) * 100))) + '%'
            if self.matches_played > 0
            else '0%'
        )

        # Win %
        self.win_pct = (
            str(int(round((self.matches_won / self.matches_played) * 100))) + '%'
            if self.matches_played > 0
            else '0%'
        )

        # Convert time played from seconds -> minutes
        minutes_played = self.time_played / 60

        # Damage per minute
        self.damage_per_minute = (
            int(round(self.total_damage / minutes_played))
            if minutes_played > 0
            else 0
        )

        # Healing per minute
        self.healing_per_minute = (
            int(round(self.total_healing / minutes_played))
            if minutes_played > 0
            else 0
        )

        # Damage taken per minute
        self.total_damage_taken_per_minute = (
            int(round(self.total_damage_taken / minutes_played))
            if minutes_played > 0
            else 0
        )
    def getOverviewMatchesPlayed(self):
        return self.matches_played
    def getOverviewMatchesWon(self):
        return self.matches_won
    def getOverviewKills(self):
        return self.kills
    def getOverviewAssists(self):
        return self.assists
    def getOverviewDeaths(self):
        return self.deaths
    def getOverviewKDRatio(self):
        return self.kd_ratio
    def getOverviewKDARatio(self):
        return self.kda_ratio
    def getOverviewTotalDamage(self):
        return self.total_damage
    def getOverviewTotalHealing(self):
        return self.total_healing
    def getOverviewDamagePerMinute(self):
        return self.damage_per_minute
    def getOverviewHealingPerMinute(self):
        return self.healing_per_minute
    def getOverviewTotalDamageTaken(self):
        return self.total_damage_taken
    def getOverviewTotalDamageTakenPerMinute(self):
        return self.total_damage_taken_per_minute
    def getOverviewLastKills(self):
        return self.last_kills
    def getOverviewHeadKills(self):
        return self.head_kills
    def getOverviewSoloKills(self):
        return self.solo_kills
    def getOverviewTotalMVP(self):
        return self.mvps
    def getOverviewMvpPct(self):
        return self.mvp_pct
    def getOverviewTotalSVP(self):
        return self.svps
    def getOverviewSvpPct(self):
        return self.svp_pct
    def getOverviewTimePlayed(self):
        return self.time_played
    def getOverviewWinPct(self):
        return self.win_pct
    def getOverviewStatRate(self, stat_value: int | float = 0, minutes: int = 10):
        if isinstance(stat_value, (int, float)):
            time = self.getOverviewTimePlayed()
            minutes = time / 60
            ten_minute_segments = minutes / minutes
            return round(stat_value / ten_minute_segments,1) if ten_minute_segments > 0 else 0
        return 0
    
    def getOverviewAvgLifespan(self, stat_value: int | float = None):
        if stat_value is None:
            stat_value = self.deaths
        if isinstance(stat_value, (int, float)) and stat_value > 0:
            seconds = self.getOverviewTimePlayed()
            minutes = seconds / 60
            lifespan = minutes / stat_value
            if lifespan < 1:
                return round(lifespan,2)
            return round(lifespan,1)

        return 0

class FullOverview:
    def __init__(self, overview_data,player: "Player" = None):
        self.player = player
        ov = overview_data[0]
        overview_stats = ov['stats']
        self.kills = overview_stats['kills']['value']
        self.assists = overview_stats['assists']['value']
        self.deaths = overview_stats['deaths']['value']
        self.kd_ratio = overview_stats['kdRatio']['value']
        self.kda_ratio = overview_stats['kdaRatio']['value']
        self.total_damage = overview_stats['totalHeroDamage']['value']
        self.total_healing = overview_stats['totalHeroHeal']['value']
        self.mvps = overview_stats['totalMvp']['value']
        self.mvp_pct = str(int(round(overview_stats['totalMvpPct']['value']))) + '%'
        self.damage_per_minute = int(round(overview_stats['totalHeroDamagePerMinute']['value']))
        self.svps = overview_stats['totalSvp']['value']
        self.svp_pct = str(int(round(overview_stats['totalSvpPct']['value']))) + '%'
        self.healing_per_minute = int(round(overview_stats['totalHeroHealPerMinute']['value']))
        self.total_damage_taken = overview_stats['totalDamageTaken']['value']
        self.total_damage_taken_per_minute = int(round(overview_stats['totalDamageTakenPerMinute']['value']))
        self.last_kills = overview_stats['lastKills']['value']
        self.matches_played = overview_stats['matchesPlayed']['value']
        self.matches_won = overview_stats['matchesWon']['value']
        self.win_pct = str(int(round(overview_stats['matchesWinPct']['value']))) + '%'
        self.time_played = overview_stats['timePlayed']['value']
        #self.time_played_won = overview_stats['timePlayedWon']['value']
        self.time_played_hours = self.convertSecondstoHours(self.time_played)
        #self.time_played_won_hours = self.convertSecondstoHours(self.time_played_won)

        self.ace_pct = self.calculatePct(self.mvps+self.svps, self.matches_played)
        
        sorted_heros = self.sort_by_time2(overview_data)
        if sorted_heros:
            self.heroes: List[Hero] = [Hero(seg) for seg in sorted_heros]
        else:
            self.heroes = []
        role_totals = self.getRolesData(overview_data)
        self.role_objs: List[Role] = [Role(role_totals[seg], self) for seg in role_totals]
        self.role_objs.sort(key=lambda role: role.time_played, reverse=True)
        self.total_roles_time = 0
        # for role in self.role_objs:
        #     self.total_roles_time = self.get_role_time_total(role=role, total_time=self.total_roles_time)
        #for role in self.role_objs:
            #usage = role.usage
            #name = role.role_name
            #print(f"\n{name} time: {usage} sec\n")
        pass
        #print(f"Total {self.time_played}\nRole Calc: {self.total_roles_time}")
        # self.duelist_role_data = role_totals.get("Duelist", None)
        # self.vanguard_role_data = role_totals.get("Vanguard", None)
        # self.strategist_role_data = role_totals.get("Strategist", None)

        # self.dps_time = role_totals.get("Duelist", 0)
        # self.tank_time = role_totals.get("Vanguard", 0)
        # self.support_time = role_totals.get("Strategist", 0)
        # print(f"{self.player.name}'s Role Time Totals: DPS={self.dps_time} sec, Tank={self.tank_time} sec, Support={self.support_time} sec")
    def sort_by_time2(self, data):
        if len(data) <= 1:
            return False
        hero_segments = [segment for segment in data if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        return sorted_heroes  
    def getSegmentFromType(self, data, seg_type):
        segments = data["data"]["segments"]
        hero_segment = next((segment for segment in segments if segment.get("type") == seg_type),
                                None
                            )
        return hero_segment   
    def getRolesData(self, data):
        roles = {}
        for segment in data:
            if segment["type"] == "hero-role":
                role_name = segment["metadata"]["name"]
                
                roles[role_name] = segment
        return roles
    def get_role_time_total(self,role: "Role" = None, total_time: int = 0):
        total_time += role.time_played
        return total_time
    
    def calculatePct(self, value, total):
        if total > 0:
            return str(int(round((value / total) * 100))) + '%'
        return '0%'

    def convertSecondstoHours(self, seconds):
        if not seconds:
            return 0
        if seconds <= 30:
            return 0
        if isinstance(seconds, (int, float)):
            hours = seconds / 3600
            return round(hours, 1)


class Match:
    def __init__(self, match_data):
        match_stats = match_data['segments'][0]['stats']
        self.duration = match_data['metadata']['duration']
        self.winning_team = match_data['metadata']['winningTeamId']
        self.result = match_data['segments'][0]['metadata']['result']
        self.isMvp = match_data['segments'][0]['metadata']['isMvp']
        self.isSvp = match_data['segments'][0]['metadata']['isSvp']
        self.scores = match_data['metadata']['scores']
        self.player_team = match_data['segments'][0]['metadata']['teamId']
        self.heroes_used = [hero['name'] for hero in match_data['segments'][0]['metadata']['heroes']]
        self.time_played = match_stats['timePlayed']['value']
        self.kills = match_stats['kills']['value']
        self.assists = match_stats['assists']['value']
        self.deaths = match_stats['deaths']['value']
        self.kd_ratio = match_stats['kdRatio']['value']
        self.kda_ratio = match_stats['kdaRatio']['value']
        self.total_damage = match_stats['totalHeroDamage']['value']
        self.total_healing = match_stats['totalHeroHeal']['value']
        self.damage_per_minute = int(round(match_stats['totalHeroDamagePerMinute']['value']))
        self.healing_per_minute = int(round(match_stats['totalHeroHealPerMinute']['value']))
        self.total_damage_taken = match_stats['totalDamageTaken']['value']
        self.total_damage_taken_per_minute = int(round(match_stats['totalDamageTakenPerMinute']['value']))
        self.last_kills = match_stats['lastKills']['value']
        self.rank, self.rank_tier = strip_rank_tier2(match_stats['ranked']['metadata']['tierName'])
        self.rank_delta = match_stats['rankedDelta']['displayValue']
    def getSegmentFromType(self, data, seg_type):
        segments = data["data"]["segments"]
        hero_segment = next((segment for segment in segments if segment.get("type") == seg_type),
                                None
                            )
        return hero_segment
    
    

class Hero:
    def __init__(self, hero_data, player: "Player" = None):
        self.player = player
        self.time_played_All = None
        self.score = None
        stats = hero_data.get('stats', {})
        meta = hero_data.get('metadata', {})
        self.heroname = meta.get('name', 'Unknown')
        if self.player and hasattr(self.player, "alltime_dict"):
            self.time_played_All = self.player.alltime_dict.get(self.heroname, False)
            #print(f"Time played for {self.heroname} across all seasons: {self.time_played_All} hours")
            self.bAnimated, self.Frame, self.Badge, self.HeroIconName, self.Proficiency_Rank = self.DoProficiencyLogic(self.time_played_All)
        elif self.player:
            self.bAnimated, self.Frame, self.Badge, self.HeroIconName, self.Proficiency_Rank = self.DoProficiencyLogic(self.time_played_All)
        else:
            pass
        self.time_played = stats.get('timePlayed', {}).get('value', 0)
        self.matches_played = stats.get('matchesPlayed', {}).get('value', 0)
        self.role = meta.get('roleName', 'Unknown')
        self.kills = stats.get('kills', {}).get('value', 0)
        self.assists = stats.get('assists', {}).get('value', 0)
        self.deaths = stats.get('deaths', {}).get('value', 0)
        self.kd_ratio = self.kills / self.deaths if self.deaths > 0 else self.kills
        self.kda_ratio = (self.kills + self.assists) / self.deaths if self.deaths > 0 else self.kills + self.assists
        self.total_damage = stats.get('totalHeroDamage', {}).get('value') or 0
        self.total_healing = stats.get('totalHeroHeal', {}).get('value') or 0
        self.damage_per_minute = self.total_damage * 3600 / self.time_played if self.time_played > 0 else self.total_damage
        self.healing_per_minute = self.total_healing * 3600 / self.time_played if self.time_played > 0 else self.total_healing
        self.total_damage_taken = stats.get('totalDamageTaken', {}).get('value') or 0
        self.total_damage_taken_per_minute = self.total_damage_taken * 3600 / self.time_played if self.time_played > 0 else self.total_damage_taken
        self.last_kills = stats.get('lastKills', {}).get('value', 0)
        self.head_kills = stats.get('headKills', {}).get('value', 0)
        self.solo_kills = stats.get('soloKills', {}).get('value', 0)
        self.main_attacks = stats.get('mainAttacks', {}).get('value', 0)
        self.main_attack_hits = stats.get('mainAttackHits', {}).get('value', 0)
        self.shield_hits = stats.get('shieldHits', {}).get('value', 0)
        self.critical_hits =  stats.get('featureCriticalRate1CritHits', {}).get('value', 0)
        self.critical_hits2 =  stats.get('featureCriticalRate1Hits', {}).get('value', 0)
        self.summoner_hits =  stats.get('summonerHits', {}).get('value', 0)
        self.chaos_hits =  stats.get('chaosHits', {}).get('value', 0)
        try:
            self.accuracy = self.getHeroAccuracy()
            self.headshot_accuracy = self.getHeroHeadshotAccuracy()
        except Exception:
            self.accuracy = '0%'
            self.headshot_accuracy = '0%'
        self.total_mvp = stats.get('totalMvp', {}).get('value', 0)
        self.total_svp = stats.get('totalSvp', {}).get('value', 0)
        self.mvp_pct_raw = self.total_mvp / self.matches_played * 100 if self.matches_played > 0 else 0
        self.svp_pct_raw = self.total_svp / self.matches_played * 100 if self.matches_played > 0 else 0
        self.svp_pct = str(int(self.svp_pct_raw)) + '%' if self.matches_played > 0 else '0%'
        self.mvp_pct = str(int(self.mvp_pct_raw)) + '%' if self.matches_played > 0 else '0%'
        
        self.matches_won = stats.get('matchesWon', {}).get('value', 0)

        self.avg_kills_per_match = self.kills / self.matches_played if self.matches_played > 0 else 0
        self.avg_assists_per_match = self.assists / self.matches_played if self.matches_played > 0 else 0
        self.avg_deaths_per_match = self.deaths / self.matches_played if self.matches_played > 0 else 0
        self.avg_damage_per_match = self.total_damage / self.matches_played if self.matches_played > 0 else 0
        self.avg_healing_per_match = self.total_healing / self.matches_played if self.matches_played > 0 else 0
        self.avg_damage_taken_per_match = self.total_damage_taken / self.matches_played if self.matches_played > 0 else 0


        self.time_played_won = stats.get('timePlayedWon', {}).get('value', 0)
        self.win_pct_raw = self.time_played_won / self.time_played * 100 if self.time_played > 0 else 0
        self.win_pct = str(int(self.win_pct_raw)) + '%' if self.time_played > 0 else '0%'
        
        self.kills_per_10 = self.getHeroStatRate(self.kills, 10)
        self.assists_per_10 = self.getHeroStatRate(self.assists, 10)
        self.average_lifespan = self.getHeroAvgLifespan()
        self.last_kills_per_10 = self.getHeroStatRate(self.last_kills, 10)
        self.head_kills_per_10 = self.getHeroStatRate(self.head_kills, 10)
        self.string = "Damage" if self.role != "Strategist" else "Healing"
        self.dpm = self.damage_per_minute if self.role != "Strategist" else self.healing_per_minute
        self.avg_match_duration_minutes = self.getHeroMatchDuration()
        
        self.kills_per_game_10,self.kills_per_game_10_raw = self.getHeroStatMatchAvg(self.kills)
        self.assists_per_game_10,self.assists_per_game_10_raw = self.getHeroStatMatchAvg(self.assists)
        self.deaths_per_game_10,self.deaths_per_game_10_raw = self.getHeroStatMatchAvg(self.deaths)
        self.damage_per_game_10,self.damage_per_game_10_raw = self.getHeroStatMatchAvg(self.total_damage)
        self.healing_per_game_10,self.healing_per_game_10_raw = self.getHeroStatMatchAvg(self.total_healing)
        self.damage_taken_per_game_10,self.damage_taken_per_game_10_raw = self.getHeroStatMatchAvg(self.total_damage_taken)
        self.last_kills_per_game_10,self.last_kills_per_game_10_raw = self.getHeroStatMatchAvg(self.last_kills)
        self.head_kills_per_game_10,self.head_kills_per_game_10_raw = self.getHeroStatMatchAvg(self.head_kills)
    

    def DoProficiencyLogic(self, time_played_all):
        if time_played_all:
            hours = time_played_all
            return self.proficiency_handlerAll(hours, self.heroname)
        else:
            time_played_h = 0
            for h in self.player.fov_heroes:
                if h.heroname == self.heroname:
                    time_played_s = h.time_played
                    time_played_m = time_played_s / 60
                    time_played_h = time_played_m / 60
                    break
            hours = time_played_h
            return self.proficiency_handler(hours, self.heroname)

    def proficiency_handler(self,hours, hero):
        lv60 = 195/2 #AnimatedLord, Badge4, Gold
        lv55 = 165/2 #AnimatedLord, Badge4, Gold
        lv50 = 137.5/2 #AnimatedLord, Badge3, Gold
        lv45 = 112.5/2 #Lord, Badge3, Gold
        lv40 = 90/2 #Lord, Badge2, Gold
        lv35 = 70/2 #Lord, Badge2, Purple
        lv30 = 52.5/2 #Lord, Badge1, Purple
        lv25 = 37/2 #Lord, Badge1
        lv20 = 25/2 #Lord
        lv15 = 15/2
        lv10 = 7.5/2
        lv5 = 2.5/2

        if hours > lv55: #200:
            return True, "gold", 4, hero, "Champion"
        elif hours > lv50: #140:
            return True, "gold", 3, hero, "Champion" 
        elif hours > lv45: #100:    
            return False, "gold", 3, hero + "_l", "Guardian"
        elif hours > lv40: #100:    
            return False, "gold", 2, hero + "_l", "Elite"
        elif hours > lv35: #80:
            return False, "purp", 2, hero + "_l", "Warrior"
        elif hours > lv30: #55:
            return False, 'purp', 1, hero + "_l", "Colonel"
        elif hours > lv25: #35:
            return False, False, 1, hero + "_l", "Count"
        elif hours > lv20: #25:
            return False, False, False, hero + "_l", "Lord"
        elif hours > lv15: #15:
            return False, False, False, hero, "Centurion"
        elif hours > lv10: #7.5:
            return False, False, False, hero, "Captain"
        elif hours > lv5: #2.5:
            return False, False, False, hero, "Knight"
        else:
            return False, False, False, hero, "Agent"
            
    def proficiency_handlerAll(self,hours, hero):
        lv60 = 195 #AnimatedLord, Badge4, Gold
        lv55 = 165 #AnimatedLord, Badge4, Gold
        lv50 = 136.5 #AnimatedLord, Badge3, Gold
        lv45 = 112.5 #Lord, Badge3, Gold
        lv40 = 90 #Lord, Badge2, Gold
        lv35 = 70 #Lord, Badge2, Purple
        lv30 = 52.5 #Lord, Badge1, Purple
        lv25 = 37 #Lord, Badge1
        lv20 = 25 #Lord
        lv15 = 15
        lv10 = 7.5
        lv5 = 2.5

        if hours > lv55: #200:
            return True, "gold", 4, hero, "Champion"
        elif hours > lv50: #140:
            return True, "gold", 3, hero, "Champion" 
        elif hours > lv45: #100:    
            return False, "gold", 3, hero + "_l", "Guardian"
        elif hours > lv40: #100:    
            return False, "gold", 2, hero + "_l", "Elite"
        elif hours > lv35: #80:
            return False, "purp", 2, hero + "_l", "Warrior"
        elif hours > lv30: #55:
            return False, 'purp', 1, hero + "_l", "Colonel"
        elif hours > lv25: #35:
            return False, False, 1, hero + "_l", "Count"
        elif hours > lv20: #25:
            return False, False, False, hero + "_l", "Lord"
        elif hours > lv15: #15:
            return False, False, False, hero, "Centurion"
        elif hours > lv10: #7.5:
            return False, False, False, hero, "Captain"
        elif hours > lv5: #2.5:
            return False, False, False, hero, "Knight"
        else:
            return False, False, False, hero, "Agent"
        
    def getHeroUsagePct(self):
        """
        Standard usage share:
        this hero's time / total time of all heroes for this player
        """
        if not hasattr(self, "player") or self.player is None:
            return "0%"

        total_time = sum(
            hero.time_played for hero in self.player.heroes
            if isinstance(hero.time_played, (int, float))
        )

        if total_time <= 0:
            return "0%"

        return f"{round((self.time_played / total_time) * 100)}%"


    def getHeroUsagePctVsOthers(self):
        """
        Requested formula:
        this hero's time / total time of every OTHER hero
        """
        if not hasattr(self, "player") or self.player is None:
            return "0%"

        other_time = sum(
            hero.time_played for hero in self.player.heroes
            if hero is not self and isinstance(hero.time_played, (int, float))
        )

        if other_time <= 0:
            return "0%"

        return f"{round((self.time_played / other_time) * 100)}%"
    def getHeroTimeHours(self):
        if self.time_played > 0:
            hours = self.time_played / 3600
            return round(hours, 1)
        return "N/A"
    def getHeroMatchDuration(self):
        if self.matches_played > 0 and self.time_played > 0:
            minutes = self.time_played / 60
            avg_duration_minutes = minutes / self.matches_played

            # avg_duration_seconds = time_played / matches_played
            # minutes = int(avg_duration_seconds // 60)
            # seconds = int(avg_duration_seconds % 60)
            return avg_duration_minutes
        return "N/A"
    def getHeroName(self):
        return self.heroname
    def getHeroMatchesPlayed(self):
        return self.matches_played
    def getHeroRole(self):
        return self.role
    def getHeroKills(self):
        return self.kills
    def getHeroAssists(self):
        return self.assists
    def getHeroDeaths(self):
        return self.deaths
    def getHeroKDRatio(self):
        return self.kd_ratio
    def getHeroKDARatio(self):
        return self.kda_ratio
    def getHeroTotalDamage(self):
        return self.total_damage
    def getHeroTotalHealing(self):
        return self.total_healing
    def getHeroDamagePerMinute(self):
        return self.damage_per_minute
    def getHeroHealingPerMinute(self):
        return self.healing_per_minute
    def getHeroTotalDamageTaken(self):
        return self.total_damage_taken
    def getHeroTotalDamageTakenPerMinute(self):
        return self.total_damage_taken_per_minute
    def getHeroLastKills(self):
        return self.last_kills
    def getHeroHeadKills(self):
        return self.head_kills
    def getHeroSoloKills(self):
        return self.solo_kills
    def getHeroMainAttacks(self):
        return self.main_attacks
    def getHeroMainAttackHits(self):
        return self.main_attack_hits
    
    def getHeroTotalMVP(self):
        return self.total_mvp
    def getHeroTotalSVP(self):
        return self.total_svp
    def getHeroMatchesWon(self):
        return self.matches_won
    def getHeroTimePlayed(self):
        return self.time_played
    def getHeroTimePlayedWon(self):
        return self.time_played_won
    def getHeroWinPct(self):
        return self.win_pct
    def getHeroMvpPct(self):
        return self.mvp_pct
    def getHeroMvpPctRaw(self):
        return self.mvp_pct_raw
    def getHeroKillsPer10(self):
        return self.kills_per_10
    def getHeroAssistsPer10(self):
        return self.assists_per_10
    
    def getHeroAvgLifespan(self):
        return self.average_lifespan
    def getHeroAvgKillsPerMatch(self):
        return round(self.avg_kills_per_match, 1)
    def getHeroAvgAssistsPerMatch(self):
        return round(self.avg_assists_per_match, 1)
    def getHeroAvgDeathsPerMatch(self):
        return round(self.avg_deaths_per_match, 1)
    def getHeroAvgDamagePerMatch(self):
        return round(self.avg_damage_per_match, 1)
    def getHeroAvgHealingPerMatch(self):
        return round(self.avg_healing_per_match, 1)
    def getHeroAvgDamageTakenPerMatch(self):
        return round(self.avg_damage_taken_per_match, 1)
    def getHeroAvgMatchDurationMinutes(self):
        return round(self.avg_match_duration_minutes, 1)
    def getHeroWinRaw(self):
        return self.win_pct_raw
    def getHeroStatMatchAvg(self, stat_value: int | float = 0):
        if isinstance(stat_value, (int, float)) and self.matches_played > 0.2:
            stat_per_match = stat_value / self.matches_played
            avg = stat_per_match*10 / self.avg_match_duration_minutes
            
            return round(avg, 1), avg

        return 0, 0
    def getHeroStatRate(self, stat_value: int | float = 0, minutes: int = 10):
        if isinstance(stat_value, (int, float)):
            time = self.getHeroTimePlayed()
            min = time / 60
            ten_minute_segments = min / minutes
            return round(stat_value / ten_minute_segments,1) if ten_minute_segments > 0 else 0
        return 0
    
    def getHeroAvgLifespan(self, stat_value: int | float = None):
        if stat_value is None:
            stat_value = self.deaths
        if isinstance(stat_value, (int, float)) and stat_value > 0:
            seconds = self.getHeroTimePlayed()
            minutes = seconds / 60
            lifespan = minutes / stat_value
            if lifespan < 1:
                return round(lifespan,2)
            return round(lifespan,1)

        return 0
    
    def getHeroAccuracy(self):
        try:
            a = self.main_attack_hits
            b = self.summoner_hits
            c = self.chaos_hits
            d = self.critical_hits
            e = self.main_attacks
            if a is None:
                a = 0
            if b is None:
                b = 0
            if c is None:
                c = 0
            if d is None:
                d = 0
            if e is None or e == 0:
                return '0%'
            
            if not isinstance(self.main_attack_hits, (int, float)):
                return "0%"
            if not isinstance(self.main_attacks, (int, float)):
                return "0%"
            if not isinstance(self.critical_hits, (int, float)):
                return "0%"
            if not isinstance(self.critical_hits2, (int, float)):
                return "0%"
            if not isinstance(self.summoner_hits, (int, float)):
                return "0%"
            if not isinstance(self.chaos_hits, (int, float)):
                return "0%"
            if self.main_attacks > 0:


                return str(round(int(round((self.main_attack_hits+self.summoner_hits+self.chaos_hits+self.critical_hits) / self.main_attacks * 100,0)))) + '%'
            return '0%'
        except Exception:
            return "0%"
    
    def getHeroHeadshotAccuracy(self):
        if not isinstance(self.critical_hits, (int, float)):
            return "N/A"
        if not isinstance(self.critical_hits2, (int, float)):
            return "N/A"
        if self.main_attack_hits > 0:
            
            return str(round(int((self.critical_hits / self.critical_hits2) * 100))) + '%'
        return '0%'

class Role:
    def __init__(self, role_data=None, full_ov: FullOverview = None):
        try:

            stats = role_data.get('stats', {})
            meta = role_data.get('metadata', {})
            self.usage = None
            self.parent_full_ov = None
            self.role_name = meta.get("name", "Unknown")

            self.kills = stats.get('kills', {}).get('value', 0)
            self.assists = stats.get('assists', {}).get('value', 0)
            self.deaths = stats.get('deaths', {}).get('value', 0)
            self.kd_ratio = stats.get('kdRatio', {}).get('value', 0)
            self.kda_ratio = stats.get('kdaRatio', {}).get('value', 0)
            self.total_damage = stats.get('totalHeroDamage', {}).get('value', 0)
            self.total_healing = stats.get('totalHeroHeal', {}).get('value', 0)

            self.damage_per_minute = int(round(stats.get('totalHeroDamagePerMinute', {}).get('value', 0)))
            self.healing_per_minute = int(round(stats.get('totalHeroHealPerMinute', {}).get('value', 0)))

            self.total_damage_taken = stats.get('totalDamageTaken', {}).get('value', 0)
            self.total_damage_taken_per_minute = int(round(stats.get('totalDamageTakenPerMinute', {}).get('value', 0)))

            self.last_kills = stats.get('lastKills', {}).get('value', 0)
            self.head_kills = stats.get('headKills', {}).get('value', 0)

            self.total_mvp = stats.get('totalMvp', {}).get('value', 0)
            self.total_svp = stats.get('totalSvp', {}).get('value', 0)

            self.matches_played = stats.get('matchesPlayed', {}).get('value', 0)
            self.matches_won = stats.get('matchesWon', {}).get('value', 0)

            self.time_played = stats.get('timePlayed', {}).get('value', 0)
            self.time_played_won = stats.get('timePlayedWon', {}).get('value', 0)

            self.time_played_hours = self.convertSecondstoHours(self.time_played)
            self.time_played_won_hours = self.convertSecondstoHours(self.time_played_won)
            if full_ov:
                self.parent_full_ov = full_ov
                self.calculateUsage(role_time=self.time_played, total_time=full_ov.time_played)
                



            self.win_pct = str(int(round(stats.get('matchesWinPct', {}).get('value', 0)))) + '%'
            self.mvp_pct =self.calculatePct(self.total_mvp, self.matches_won)
            self.svp_pct = self.calculatePct(self.total_svp, self.matches_played - self.matches_won)
            self.ace_pct = self.calculatePct(self.total_mvp + self.total_svp, self.matches_played)
            #self.matches_played = stats.get('matchesPlayed', {}).get('value', 0)
        except Exception as e:
            print(f"Error initializing Role: {e}")
    def calculateUsage(self, role_time, total_time):
        if total_time > 0:
            self.usage = str(int(round((role_time / total_time) * 100))) + '%'
        else:
            self.usage = '0%'
        print(f"{self.parent_full_ov.player.name}: {self.role_name} usage: {self.usage}")
    def calculatePct(self, value, total):
        if total > 0:
            return str(int(round((value / total) * 100))) + '%'
        return '0%'

    def convertSecondstoHours(self, seconds):
        if not seconds:
            return 0
        if seconds <= 30:
            return 0
        if isinstance(seconds, (int, float)):
            hours = seconds / 3600
            return round(hours, 1)
        
        


class Player:
    def __init__(self, name=None, json_data=None,bDB=False):
        self.best_hero = None

        self.name = name
        try:
            if not bDB:
                overview_data = self.getSegmentFromType(json_data, "overview")
                rank_data = self.getSegmentFromType(json_data, "ranked-peaks")
                self.best_rank = strip_rank_tier(rank_data['stats']['lifetimePeakRanked']['metadata']['tierName'])
                self.season_rank = strip_rank_tier(overview_data['stats']['peakRanked']['metadata']['tierName'])
                seas = json_data['data']['seas']
                self.seasons_string = self.buildSeasonsString(seas)
                self.seasonal_overview = Overview(overview_data)
            full_overview = json_data['data']['full_overview']
            
            alltime_data = json_data['data']['alltime_segments']
            if alltime_data:
                self.alltime_dict = self.buildAlltimeDict(alltime_data)
            
            self.full_overview = FullOverview(full_overview, player=self)
            self.fov_heroes = self.full_overview.heroes if hasattr(self.full_overview, "heroes") else []
            
            if not bDB:
                matches = json_data['data'].get('matches', [])
                roles_data = self.getRolesData(json_data)
                self.bPrivate = True if json_data['data']['userInfo']['isPremium'] == 69 else False
                sorted_heros = self.sort_by_time(json_data)
                self.heroes: list[Hero] = []
                self.top_heroes: List[Hero] = []
                if sorted_heros:
                    
                    self.heroes = [
                                Hero(seg, player=self)
                                for seg in sorted_heros
                                if seg.get('stats', {}).get('timePlayed', {}).get('value', 0) != 0
                            ]
                    for hero in self.heroes:
                        hero.player = self
                # If you often want "top 3"
                    self.top_heroes: List[Hero] = self.heroes[:3]
                if roles_data:
                    self.roles: List[Role] = [Role(role_seg) for role_seg in roles_data]
                    self.roles.sort(key=lambda r: r.time_played, reverse=True)
                if matches:
                    self.matches: List[Match] = [Match(match) for match in matches]

        except Exception as e:
            print(f"Error initializing Player: {e}")

    def getSegmentFromType(self, data, seg_type):
        segments = data["data"]["segments"]
        hero_segment = next((segment for segment in segments if segment.get("type") == seg_type),
                                None
                            )
        return hero_segment
    
    def buildSeasonsString(self, seas):
        if not seas or not isinstance(seas, list):
            return "N/A"
        pt1 = "Season" if len(seas) == 1 else "Seasons"
        converted_seasons = []
        for season in seas:
            number = int(season)
            con = 0 if number <= 1 else round(number / 2, 1)
            converted_seasons.append(str(con))

        p2 = " & ".join(str(n) for n in reversed(converted_seasons))

        return f"{pt1} {p2}" if converted_seasons else "N/A"
    def buildAlltimeDict(self, alltime_data):
        try:
            alltime_dict = {}
            if not alltime_data or not isinstance(alltime_data, list):
                return False
            
            
            for segment in alltime_data:
                if segment.get("type") == "hero":
                    hero_name = segment["metadata"]["name"]
                    time_played_s = segment["stats"]["timePlayed"]["value"]
                    time_played_h = round(time_played_s / 3600,1)
                    alltime_dict[hero_name] = time_played_h
            return alltime_dict
        except Exception as e:
            print(f"Error building alltime dict: {e}")
            return False

    def sort_by_time(self, data):
        segments = data["data"]["segments"]
        hero_segments = [segment for segment in segments if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        return sorted_heroes
        
    def get_hero(self, name: str) -> Optional[Hero]:
        #from typing import Dict

        self.heroes_by_name: Dict[str, Hero] = {h.heroname: h for h in self.heroes}
        return self.heroes_by_name.get(name)

    def top(self, n: int = 3) -> List[Hero]:
        return self.heroes[:n]

    def sorted_by(self, key: str, reverse: bool = True) -> List[Hero]:
        """
        Example: player.sorted_by("time_played")
                player.sorted_by("kd_ratio")
        """
        return sorted(self.heroes, key=lambda h: getattr(h, key, 0) or 0, reverse=reverse)
    
    def getRolesData(self, data):
        roles = []
        for segment in data["data"]["segments"]:
            if segment["type"] == "hero-role":
                roles.append(segment)
        return roles    
    
def strip_rank_tier(rank_str):
    # Match everything except the trailing Roman numeral (if present)
    return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)

def strip_rank_tier2(rank_str):
    m = re.match(r'^(.*?)(?:\s+(I{1,3}|IV|V))?$', rank_str.strip())
    if not m:
        return rank_str, None

    base_rank = m.group(1)
    roman_tier = m.group(2)
    return base_rank, roman_tier
        