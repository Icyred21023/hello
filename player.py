import re

class Player:
    def __init__(self, name, json_data):
        sorted_heros = self.sort_by_time(json_data)
        self.hero1 = sorted_heros[0]["metadata"]["name"]
        if sorted_heros[0]["metadata"]["roleName"] == "Strategist":
            self.string1 = "Healing / Min:"
            self.dpm1 = sorted_heros[0]["stats"]["totalHeroHealPerMinute"]["value"]
        else:
            self.string1 = "Damage / Min:"
            self.dpm1 = sorted_heros[0]["stats"]["totalHeroDamagePerMinute"]["value"]
        self.kd1 = round(sorted_heros[0]["stats"]["kdRatio"]["value"],2)
        self.hero2 = "Question"
        self.string2 = "Null"
        self.dpm2 = "Null"
        self.kd2 = "Null"
        if len(sorted_heros) > 1:
            self.hero2 = sorted_heros[1]["metadata"]["name"]
            if sorted_heros[1]["metadata"]["roleName"] == "Strategist":
                self.string2 = "Healing / Min:"
                self.dpm2 = sorted_heros[1]["stats"]["totalHeroHealPerMinute"]["value"]
            else:
                self.string2 = "Damage / Min:"
                self.dpm2 = sorted_heros[1]["stats"]["totalHeroDamagePerMinute"]["value"]
            self.kd2 = round(sorted_heros[1]["stats"]["kdRatio"]["value"],2)
            self.rank = self.strip_rank_tier(json_data["data"]["segments"][1]["stats"]["lifetimePeakRanked"]["metadata"]["tierName"])
            self.name = name
        # Add other values


    def strip_rank_tier(self, rank_str):
        # Match everything except the trailing Roman numeral (if present)
        return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)
    def sort_by_time(self, data):
        segments = data["data"]["segments"]
        hero_segments = [segment for segment in segments if segment.get("type") == "hero"]
        sorted_heroes = sorted(hero_segments, key=lambda x: x["stats"]["timePlayed"]["value"], reverse=True)
        return sorted_heroes
    
    def __repr__(self):
        return f"Player(name={self.name}, rank={self.rank})"