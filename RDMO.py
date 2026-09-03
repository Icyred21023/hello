import config
from typing import List
import re

SEASON = 9
UID = config.USER_UID if not config.mobile_mode else "1324925930"


def fetch_teammates(uid, season=-1):
    result = 7
    return result

def strip_rank_tier2(rank_str):
    m = re.match(r'^(.*?)(?:\s+(I{1,3}|IV|V))?$', rank_str.strip())
    if not m:
        return rank_str, None
    


    base_rank = m.group(1)
    roman_tier = m.group(2)
    return base_rank, roman_tier

def strip_rank_tier(rank_str):
    # Match everything except the trailing Roman numeral (if present)
    return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)
        
def getSegmentFromType(data, seg_type):
        segments = data["data"]
        hero_segment = next((segment for segment in segments if segment.get("type") == seg_type),
                                None
                            )
        return hero_segment

def hero_id_to_info(hero_id):
    hero_data = config.HERO_KEYS.get(str(hero_id), {})

    name = hero_data.get("name", "Unknown")
    role = (hero_data.get("roles") or ["Unknown"])[0]

    return name, role
    
class Stats:
    __slots__ = (
        # Context
        "role",

        # Raw totals
        "time_played",
        "matches_played",
        "matches_won",
        "kills",
        "assists",
        "deaths",
        "total_damage",
        "total_healing",
        "total_damage_taken",
        "last_kills",
        "head_kills",
        "solo_kills",
        "main_attacks",
        "main_attack_hits",
        "shield_hits",
        "critical_hits",
        "critical_hits2",
        "summoner_hits",
        "chaos_hits",
        "total_mvp",
        "total_svp",
        "time_played_won",

        # Derived
        "accuracy",
        "headshot_accuracy",
        "mvp_pct_raw",
        "mvp_pct",
        "svp_pct_raw",
        "svp_pct",
        "win_pct_raw",
        "win_pct",

        "damage_per_minute",
        "healing_per_minute",
        "total_damage_taken_per_minute",

        "kd_ratio",
        "kda_ratio",

        "avg_kills_per_match",
        "avg_assists_per_match",
        "avg_deaths_per_match",
        "avg_damage_per_match",
        "avg_healing_per_match",
        "avg_damage_taken_per_match",

        "kills_per_10",
        "assists_per_10",
        "last_kills_per_10",
        "head_kills_per_10",

        "average_lifespan",
        "avg_match_duration_minutes",

        "kills_per_game_10",
        "kills_per_game_10_raw",
        "assists_per_game_10",
        "assists_per_game_10_raw",
        "deaths_per_game_10",
        "deaths_per_game_10_raw",
        "damage_per_game_10",
        "damage_per_game_10_raw",
        "healing_per_game_10",
        "healing_per_game_10_raw",
        "damage_taken_per_game_10",
        "damage_taken_per_game_10_raw",
        "last_kills_per_game_10",
        "last_kills_per_game_10_raw",
        "head_kills_per_game_10",
        "head_kills_per_game_10_raw",

        "string",
        "dpm",
    )

    def __init__(self, stats=None, role=None):
        self.role = role

        # =====================================================
        # RAW TOTALS
        # =====================================================

        self.time_played = 0
        self.matches_played = 0
        self.matches_won = 0

        self.kills = 0
        self.assists = 0
        self.deaths = 0

        self.total_damage = 0
        self.total_healing = 0
        self.total_damage_taken = 0

        self.last_kills = 0
        self.head_kills = 0
        self.solo_kills = 0

        self.main_attacks = 0
        self.main_attack_hits = 0
        self.shield_hits = 0

        self.critical_hits = 0
        self.critical_hits2 = 0

        self.summoner_hits = 0
        self.chaos_hits = 0

        self.total_mvp = 0
        self.total_svp = 0

        self.time_played_won = 0

        # =====================================================
        # DERIVED DEFAULTS
        # =====================================================

        self.accuracy = "0%"
        self.headshot_accuracy = "0%"

        self.mvp_pct_raw = 0
        self.mvp_pct = "0%"

        self.svp_pct_raw = 0
        self.svp_pct = "0%"

        self.win_pct_raw = 0
        self.win_pct = "0%"

        self.damage_per_minute = 0
        self.healing_per_minute = 0
        self.total_damage_taken_per_minute = 0

        self.kd_ratio = 0
        self.kda_ratio = 0

        self.avg_kills_per_match = 0
        self.avg_assists_per_match = 0
        self.avg_deaths_per_match = 0
        self.avg_damage_per_match = 0
        self.avg_healing_per_match = 0
        self.avg_damage_taken_per_match = 0

        self.kills_per_10 = 0
        self.assists_per_10 = 0
        self.last_kills_per_10 = 0
        self.head_kills_per_10 = 0

        self.average_lifespan = 0
        self.avg_match_duration_minutes = 0

        self.kills_per_game_10 = 0
        self.kills_per_game_10_raw = 0

        self.assists_per_game_10 = 0
        self.assists_per_game_10_raw = 0

        self.deaths_per_game_10 = 0
        self.deaths_per_game_10_raw = 0

        self.damage_per_game_10 = 0
        self.damage_per_game_10_raw = 0

        self.healing_per_game_10 = 0
        self.healing_per_game_10_raw = 0

        self.damage_taken_per_game_10 = 0
        self.damage_taken_per_game_10_raw = 0

        self.last_kills_per_game_10 = 0
        self.last_kills_per_game_10_raw = 0

        self.head_kills_per_game_10 = 0
        self.head_kills_per_game_10_raw = 0

        self.string = "Damage"
        self.dpm = 0

        # Optional immediate parsing
        if stats:
            self.add(stats)

    # =========================================================
    # JSON HELPERS
    # =========================================================

    @staticmethod
    def _value(stats, key):
        """
        Safely extracts:
            stats[key]["value"]

        Returns 0 for None, missing keys, or invalid values.
        """
        value = stats.get(key, {}).get("value", 0)

        if isinstance(value, (int, float)):
            return value

        return 0

    # =========================================================
    # ADD / ACCUMULATE STATS
    # =========================================================

    def add(self, stats):
        value = self._value

        self.time_played += value(stats, "timePlayed")
        self.matches_played += value(stats, "matchesPlayed")
        self.matches_won += value(stats, "matchesWon")

        self.kills += value(stats, "kills")
        self.assists += value(stats, "assists")
        self.deaths += value(stats, "deaths")

        self.total_damage += value(stats, "totalHeroDamage")
        self.total_healing += value(stats, "totalHeroHeal")
        self.total_damage_taken += value(stats, "totalDamageTaken")

        self.last_kills += value(stats, "lastKills")
        self.head_kills += value(stats, "headKills")
        self.solo_kills += value(stats, "soloKills")

        self.main_attacks += value(stats, "mainAttacks")
        self.main_attack_hits += value(stats, "mainAttackHits")
        self.shield_hits += value(stats, "shieldHits")

        self.critical_hits += value(
            stats,
            "featureCriticalRate1CritHits"
        )

        self.critical_hits2 += value(
            stats,
            "featureCriticalRate1Hits"
        )

        self.summoner_hits += value(stats, "summonerHits")
        self.chaos_hits += value(stats, "chaosHits")

        self.total_mvp += value(stats, "totalMvp")
        self.total_svp += value(stats, "totalSvp")

        self.time_played_won += value(stats, "timePlayedWon")

        self._calculate()

        return self

    # =========================================================
    # DERIVED STATS
    # =========================================================

    def _calculate(self):
        # -----------------------------------------------------
        # Percentages
        # -----------------------------------------------------

        if self.matches_played > 0:
            self.mvp_pct_raw = (
                self.total_mvp / self.matches_played * 100
            )

            self.svp_pct_raw = (
                self.total_svp / self.matches_played * 100
            )

            self.mvp_pct = f"{int(self.mvp_pct_raw)}%"
            self.svp_pct = f"{int(self.svp_pct_raw)}%"
        else:
            self.mvp_pct_raw = 0
            self.svp_pct_raw = 0
            self.mvp_pct = "0%"
            self.svp_pct = "0%"

        # -----------------------------------------------------
        # Per minute
        # -----------------------------------------------------

        if self.time_played > 0:
            minutes = self.time_played / 60

            self.damage_per_minute = (
                self.total_damage / minutes
            )

            self.healing_per_minute = (
                self.total_healing / minutes
            )

            self.total_damage_taken_per_minute = (
                self.total_damage_taken / minutes
            )

            self.win_pct_raw = (
                self.time_played_won /
                self.time_played *
                100
            )

            self.win_pct = f"{int(self.win_pct_raw)}%"

        else:
            self.damage_per_minute = 0
            self.healing_per_minute = 0
            self.total_damage_taken_per_minute = 0

            self.win_pct_raw = 0
            self.win_pct = "0%"

        # -----------------------------------------------------
        # KD / KDA
        # -----------------------------------------------------

        if self.deaths > 0:
            self.kd_ratio = self.kills / self.deaths

            self.kda_ratio = (
                self.kills + self.assists
            ) / self.deaths

        else:
            self.kd_ratio = self.kills
            self.kda_ratio = self.kills + self.assists

        # -----------------------------------------------------
        # Match averages
        # -----------------------------------------------------

        if self.matches_played > 0:
            matches = self.matches_played

            self.avg_kills_per_match = (
                self.kills / matches
            )

            self.avg_assists_per_match = (
                self.assists / matches
            )

            self.avg_deaths_per_match = (
                self.deaths / matches
            )

            self.avg_damage_per_match = (
                self.total_damage / matches
            )

            self.avg_healing_per_match = (
                self.total_healing / matches
            )

            self.avg_damage_taken_per_match = (
                self.total_damage_taken / matches
            )

            self.avg_match_duration_minutes = (
                self.time_played / 60 / matches
            )

        else:
            self.avg_kills_per_match = 0
            self.avg_assists_per_match = 0
            self.avg_deaths_per_match = 0
            self.avg_damage_per_match = 0
            self.avg_healing_per_match = 0
            self.avg_damage_taken_per_match = 0
            self.avg_match_duration_minutes = 0

        # -----------------------------------------------------
        # Lifespan
        # -----------------------------------------------------

        if self.deaths > 0:
            self.average_lifespan = (
                self.time_played / self.deaths
            )
        else:
            self.average_lifespan = self.time_played

        # -----------------------------------------------------
        # Accuracy
        # -----------------------------------------------------

        self.accuracy = self.get_accuracy()
        self.headshot_accuracy = self.get_headshot_accuracy()

        # -----------------------------------------------------
        # Per 10 minutes
        # -----------------------------------------------------

        self.kills_per_10 = self.get_rate(
            self.kills,
            10
        )

        self.assists_per_10 = self.get_rate(
            self.assists,
            10
        )

        self.last_kills_per_10 = self.get_rate(
            self.last_kills,
            10
        )

        self.head_kills_per_10 = self.get_rate(
            self.head_kills,
            10
        )

        # -----------------------------------------------------
        # Match normalized to 10 minutes
        # -----------------------------------------------------

        (
            self.kills_per_game_10,
            self.kills_per_game_10_raw
        ) = self.get_match_avg(self.kills)

        (
            self.assists_per_game_10,
            self.assists_per_game_10_raw
        ) = self.get_match_avg(self.assists)

        (
            self.deaths_per_game_10,
            self.deaths_per_game_10_raw
        ) = self.get_match_avg(self.deaths)

        (
            self.damage_per_game_10,
            self.damage_per_game_10_raw
        ) = self.get_match_avg(self.total_damage)

        (
            self.healing_per_game_10,
            self.healing_per_game_10_raw
        ) = self.get_match_avg(self.total_healing)

        (
            self.damage_taken_per_game_10,
            self.damage_taken_per_game_10_raw
        ) = self.get_match_avg(
            self.total_damage_taken
        )

        (
            self.last_kills_per_game_10,
            self.last_kills_per_game_10_raw
        ) = self.get_match_avg(self.last_kills)

        (
            self.head_kills_per_game_10,
            self.head_kills_per_game_10_raw
        ) = self.get_match_avg(self.head_kills)

        # -----------------------------------------------------
        # Role-specific display value
        # -----------------------------------------------------

        if self.role == "Strategist":
            self.string = "Healing"
            self.dpm = self.healing_per_minute
        else:
            self.string = "Damage"
            self.dpm = self.damage_per_minute

    # =========================================================
    # UTILITY METHODS
    # =========================================================

    def get_rate(
        self,
        stat_value: int | float = 0,
        minutes: int = 10
    ):
        if not isinstance(stat_value, (int, float)):
            return 0

        if self.time_played <= 0:
            return 0

        played_minutes = self.time_played / 60

        segments = played_minutes / minutes

        if segments <= 0:
            return 0

        return round(stat_value / segments, 1)

    def get_match_avg(
        self,
        stat_value: int | float = 0
    ):
        if not isinstance(stat_value, (int, float)):
            return 0, 0

        if (
            self.matches_played <= 0
            or self.avg_match_duration_minutes <= 0
        ):
            return 0, 0

        stat_per_match = (
            stat_value / self.matches_played
        )

        normalized = (
            stat_per_match *
            10 /
            self.avg_match_duration_minutes
        )

        return round(normalized, 1), normalized

    def get_accuracy(self):
        if self.main_attacks <= 0:
            return "0%"

        hits = (
            self.main_attack_hits
            + self.summoner_hits
            + self.chaos_hits
            + self.critical_hits
        )

        return f"{round(hits / self.main_attacks * 100)}%"

    def get_headshot_accuracy(self):
        if self.critical_hits2 <= 0:
            return "0%"

        return (
            f"{round(self.critical_hits / self.critical_hits2 * 100)}%"
        )

    def get_time_hours(self):
        if self.time_played <= 0:
            return "N/A"

        return round(
            self.time_played / 3600,
            1
        )

    def get_match_duration(self):
        if self.avg_match_duration_minutes <= 0:
            return "N/A"

        return self.avg_match_duration_minutes
        
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
        self.bPrivate = False

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


class Role:
    def __init__(self, role_data=None, full_ov: Overview = None):
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
        
class MatchHistory:
    def __init__(self, match_data):
        #match_data = match_data.get("data", None)
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
        self.rank_delta = match_stats.get('rankedDelta', {}).get('displayValue', "??")
    def getSegmentFromType(self, data, seg_type):
        segments = data["data"]["segments"]
        hero_segment = next((segment for segment in segments if segment.get("type") == seg_type),
                                None
                            )
        return hero_segment

class Hero:
    def __init__(self, data):
        self.Id = str(data.get("hero_id", "Unknown"))

        self.Name, self.Role = hero_id_to_info(self.Id)

        self.ProficiencyLevel = data.get("level", 0)
        self.Wins = 0
        self.Losses = 0
        self.WinRate = "0%"
        self.Stats = Stats(
            role=self.Role
        )
        
    def add_stats(self, stats):
        self.Stats.add(stats)


class Player:
    def __init__(self, data):
        self.Name = data.get("name", "Unknown")
        self.Uid = str(data.get("uid", "Unknown"))
        self.best_rank = None
        self.Team = data.get("side")
        self.TeamId = data.get("team_id")

        self.Icon = data.get("icon", "Unknown")
        self.PlayerImgId = self.Icon

        self.bPrivate = "**" in self.Name

        self.Heroes: dict[str, Hero] = {}
        self.bPrivate = True if "***" in self.Name else False
        self.seasonal_overview = None
        self.full_overview = None
        self.matches: List[MatchHistory] = []

        
        for hero_data in data.get("proficiency") or []:
            hero = Hero(hero_data)
            self.Heroes[hero.Name] = hero

        for hero_data in data.get("top_heroes") or []:
            id = str(hero_data.get("hero_id", "Unknown"))
            name, role = hero_id_to_info(id)
            if not name in self.Heroes:
                continue
            hero = self.Heroes[name]
            hero.Wins = hero_data.get("wins", 0)
            hero.Losses = hero_data.get("losses", 0)
            wp_raw = hero.Wins / (hero.Wins + hero.Losses) * 100 if (hero.Wins + hero.Losses) > 0 else 0
            hero.WinRate = f"{int(wp_raw)}%"

        self.bPrivate = True if not self.seasonal_overview else False

    def getRolesData(self, data):
        roles = []
        for segment in data["data"]:
            if segment["type"] == "hero-role":
                roles.append(segment)
        return roles
    def sort_by_time(self, data):
        segments = data["data"]
        hero_segments = [segment for segment in segments if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        return sorted_heroes  
    
    def add_matches(self, matches):
        matchhistory = matches['data']['matches']
        if matchhistory:
            self.matches: List[MatchHistory] = [MatchHistory(match) for match in matchhistory]

    def add_profile(self, profile_data):
        
        if profile_data:
            overview_data = getSegmentFromType(profile_data, "overview")
            rank_data = getSegmentFromType(profile_data, "ranked-peaks")
            self.best_rank = strip_rank_tier(rank_data['stats']['lifetimePeakRanked']['metadata']['tierName'])
            self.season_rank = strip_rank_tier(overview_data['stats']['peakRanked']['metadata']['tierName'])
            self.seasons_string = ""
            if self.seasonal_overview is None:
                self.seasonal_overview = Overview()
            self.seasonal_overview.addOverviewData(overview_data)
            self.full_overview = self.seasonal_overview
            sorted_heros = self.sort_by_time(profile_data)
            
            roles_data = self.getRolesData(profile_data)
            if roles_data:
                    self.roles: List[Role] = [Role(role_seg) for role_seg in roles_data]
                    self.roles.sort(key=lambda r: r.time_played, reverse=True)
                    
            for h in sorted_heros:
                hname = h.get("metadata", {}).get("name", None)
                stats = h.get("stats",{})
                HERO = self.Heroes.get(hname, None)
                if HERO is None:
                    continue
                HERO.add_stats(stats)

            self.bPrivate = False 


            



class Match:
    def __init__(self, data):
        self.UserId = str(UID)

        self.UserTeam = None
        self.EnemyTeam = None

        self.players: list[Player] = []

        players_data = data.get("players", {}).values()

        # Convert once because we'll need to traverse twice
        players_data = list(players_data)

        # Find user's team
        for data in players_data:
            if str(data.get("uid")) == self.UserId:
                self.UserTeam = data.get("side")
                self.EnemyTeam = 1 if self.UserTeam == 2 else 2
                break

        # Build enemy players
        self.players = [
            Player(data)
            for data in players_data
            if data.get("side") == self.EnemyTeam
        ]

        print("Done")
    
class LiveMatch:
    
    class FetchedTeammate:
        def __init__(self,data):
            self.Uid = data.get("teammate_uid")
            self.Name = data.get("name")
            self.PlayerImgId = data.get("icon")
            self.Games = data.get("games")
            self.Wins = data.get("wins")
            self.Losses = data.get("losses")
            
        def convertToMatchPlayer(self,p: "LiveMatch.MatchPlayer"):
            self.bPrivate = True
            self.PrivateName = p.Name
            self.Team = p.Team
            self.Proficiency = p.Proficiency
            self.Teammates = []
            self.FetchedTeammates = []
            self.bHasFetchedTeammates = False
            self.TeamId = p.TeamId
            
        def addTeammate(self,pobj):
            self.Teammates.append(pobj)
            
            
    class MatchPlayer:
        def __init__(self, data):
            self.Name = data.get("name")
            
            self.bPrivate = True if "**" in self.Name else False
            self.Team = data.get("side")
            self.Proficiency = data.get("proficiency")
            self.Uid = data.get("uid")
            self.TeamId = data.get("team_id")
            self.PlayerImgId = data.get("icon")
            self.Teammates: List[LiveMatch.MatchPlayer] = []
            self.FetchedTeammates: List[LiveMatch.FetchedTeammate] = []
            self.bHasFetchedTeammates = False
            self.RealPlayer = None
            
        def addTeammate(self, pobj):
            self.Teammates.append(pobj)
            
        
            
    def __init__(self, json, match_id, user_id):
        self.MatchId = match_id
        self.UserId = user_id
        print(type(json))    
        self.Players: List[LiveMatch.MatchPlayer] = []
        self.PrivatePlayers: List[LiveMatch.MatchPlayer] = []
        for player in json.get("players", []):
            data = json["players"][player]
            uid = data.get("uid", None)
            if uid == str(self.UserId):
                team = data.get("side", None)
                print(team)
                self.UserTeam = team
                self.EnemyTeam = 1 if team == 2 else 2
                break
        for player in json.get("players", []):
            data = json["players"][player]
            team = data.get("side", None)
            if team == self.EnemyTeam:
                if "**" in data.get("name"):
                    self.PrivatePlayers.append(self.MatchPlayer(data))
                    print("Player '" + data.get("name") +"'"+ ": Hidden")
                else:
                    self.Players.append(self.MatchPlayer(data))
                    print("Player '" + data.get("name")+"'" + ": Public")
        print("Done")
        
    
                    
                        
                    
                    
    
                    
                
        

class RivalsDataPlayer:
    class Match:
        def __init__(self,json):
            def getMatchScore(score):
                player = score.get("player", 0)
                opp = score.get("opponent", 0)
                return player, opp
            self.MatchId = json.get("match_uid")
            self.bWin = json.get("is_win")
            self.Season = json.get("season")
            self.RankScore = json.get("rank_score")
            self.RankLevel = json.get("rank_level")
            self.ScoreChange = json.get("score_change")
            self.Team = json.get("team")
            self.HeroId = json.get("hero_id")
            self.Kills = json.get("kills")
            self.Deaths= json.get("deaths")
            self.Assists = json.get("assists")
            self.bMvp = json.get("is_mvp")
            self.bSvp = json.get("is_svp")
            self.MatchScore = getMatchScore(json.get("team_score"))
            
    class Overview:
       def __init__(self):
           self.GamesPlayed = 0
           self.Kills = 0
           self.Deaths = 0
           self.Assists = 0
           self.Wins = 0
           self.Losses = 0
           self.Kd = 0
           self.WinRate = 0
           
       def addGames(self, games):
           self.GamesPlayed += games
           
       def addKills(self, kills):
           kills = round(kills)
           self.Kills += kills
           
       def addDeaths(self, d):
           d = round(d)
           self.Deaths += d
           
       def addAssists(self, a):
           a = round(a)
           self.Assists += a
           
       def addWins(self,w):
           self.Wins += w
           
       def addLosses(self, l):
           self.Losses += l
           
       def CalculateValues(self):
           self.Kd = round(self.Kills / self.Deaths,1) if self.Deaths != 0 else round(self.Kills,1)
           g = self.GamesPlayed if self.GamesPlayed != 0 else 1
           self.WinRate= str(int(round(self.Wins / g *100,0))) + '%'

    class Hero:
        def __init__(self,json,proficiency):
            self.HeroId = json.get("hero_id")
            self.Role = None
            self.HeroName = self.getHeroName()
            self.GamesPlayed = json.get("games")
            self.Wins = json.get("wins")
            self.Losses = json.get("losses")
            self.Kills = json.get("kills")
            self.Deaths= json.get("deaths")
            self.Assists = json.get("assists")
            self.Proficiency = proficiency
            self.Kd = self.getKd()
            
            
        def getKd(self):
            k = self.Kills * self.GamesPlayed
            d = self.Deaths * self.GamesPlayed
            kd = k / d if d != 0 else k
            return round(kd,1)
            
        def getHeroName(self):
            d = config.HERO_KEYS.get(str(self.HeroId), "Unknown")
            name = d.get("name", "Unknown")
            roles = d.get("roles", [])
            self.Role = roles[0] if roles else "Unknown"

            return name
            
            
    def __init__(self, json):
      
      if json and len(json) > 0:
          player = json[0]
          self.Aid = player["aid"]
          _, self.Uid= self.Aid.split("_")
          self.Uid = int(self.Uid)
          self.Name = player["name"]
          self.PlayerImgId= player["config_server"]["cur_head_icon_id"]
          self.Heroes = []
          self.Teammates = []
          self.MatchHistory = []
          self.Rank = {}
          self.RankScore = 0
          self.RankLevel = 0
          self.Roles = {}
          self.Ov = None
          
    def UpdateRank(self, level, score):
          self.RankLevel = level
          self.RankScore = score
          
    def initOverviewRoles(self):
         vanguard = self.Overview()
         dps = self.Overview()
         heal = self.Overview()
         overview = self.Overview()
         self.Roles = {"Vanguard": vanguard, "Duelist": dps, "Strategist": heal}
         self.Ov = overview
         Ov = self.Ov
         for hero in self.Heroes:
             r = hero.Role
             #print(hero.GamesPlayed)
             Role = self.Roles[r]
             Ov.addGames(hero.GamesPlayed)
             Role.addGames(hero.GamesPlayed)
             Ov.addKills(hero.GamesPlayed * hero.Kills)
             Role.addKills(hero.GamesPlayed * hero.Kills)
             Ov.addDeaths(hero.GamesPlayed * hero.Deaths)
             Role.addDeaths(hero.GamesPlayed * hero.Deaths)
             Ov.addAssists(hero.GamesPlayed * hero.Assists)
             Role.addAssists(hero.GamesPlayed * hero.Assists)
             Ov.addWins(hero.Wins)
             Role.addWins(hero.Wins)
             Ov.addLosses(hero.Losses)
             Role.addLosses(hero.Losses)
         self.Roles["Vanguard"].CalculateValues()
         self.Roles["Duelist"].CalculateValues()
         self.Roles["Strategist"].CalculateValues()
         self.Ov.CalculateValues()
         
         
if __name__ == "__main__":
    pass
        
