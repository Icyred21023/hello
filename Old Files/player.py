import re
STRATEGISTS = ["Cloak & Dagger", 'Mantis', 'Luna Snow', 'Loki', 'Ultron', 'Invisible Woman', 'Jeff The Land Shark', 'Rocket Raccoon']
class Player:
    def __init__(self, name, json_data):
        sorted_heros = self.sort_by_time(json_data)
        hero_data = sorted_heros[0]
        self.hero1 = self.smart_capitalize(hero_data["hero_name"])
        self.name = name
        rank_data = json_data['player']['info']['rank_game_season']
        self.season, self.rank = self.sort_by_rank(rank_data)
        self.ace = False
        overview = json_data['overall_stats']
        self.playermvp = self.getCharMvps(overview)
        if self.hero1 in STRATEGISTS:
            self.string1 = "Healing/Min"
            healing = hero_data['heal']
            time = hero_data['play_time'] / 60
            self.dpm1 = round(healing / time, 0) if time != 0 else round(healing / 1, 2)

        else:
            self.string1 = "Damage/Min"
            damage = hero_data['damage']
            time = hero_data['play_time'] / 60
            self.dpm1 = round(damage / time, 0) if time != 0 else round(damage / 1, 2)
        #char = sorted_heros[0]['stats']
        self.mvp1 = self.getHeroMvps(hero_data)

        self.kd1 = self.getKD(hero_data)
        self.hero2 = "Question"
        self.string2 = "Null"
        self.dpm2 = "Null"
        self.kd2 = "Null"
        if len(sorted_heros) > 1:
            hero_data = sorted_heros[1]
            self.hero2 = self.smart_capitalize(hero_data["hero_name"])
            if self.hero2 in STRATEGISTS:
                self.string2 = "Healing/Min"
                healing = hero_data['heal']
                time = hero_data['play_time'] / 60
                self.dpm2 = round(healing / time, 0) if time != 0 else round(healing / 1, 2)
            else:
                self.string2 = "Damage/Min"
                damage = hero_data['damage']
                time = hero_data['play_time'] / 60
                self.dpm2 = round(damage / time, 0) if time != 0 else round(damage / 1, 2)
            #char = sorted_heros[1]['stats']
            self.mvp2 = self.getHeroMvps(hero_data)
            self.kd2 = self.getKD(hero_data)


            
    def smart_capitalize(self, s):
        return re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), s)

    def getPlayerMvps(self,ov):
        print("")
        return
    
    def getKD(self,char):
        kills = char['kills']
        deaths = char['deaths']
        
        
        
        return round(kills / deaths,2) if deaths != 0 else kills / 1
    
    def getHeroMvps(self,char):
        mvps = char['mvp']
        svps = char['svp']
        num_games = char['matches']
        
        value = (mvps + svps) / num_games if num_games != 0 else (mvps+svps) / 1
        val = str(round(value * 100,1))
        string = val + '%'
        return string
        
    def getCharMvps(self,char):
        mvps = char['ranked']['total_mvp']
        svps = char['ranked']['total_svp']
        num_games = char['ranked']['total_matches']
        
        value = (mvps + svps) / num_games if num_games != 0 else (mvps+svps) / 1
        val = str(round(value * 100,1))
        string = val + '%'
        return string
        
    def strip_rank_tier(self, rank_str):
        # Match everything except the trailing Roman numeral (if present)
        return re.sub(r'\s+(I{1,3}|IV|V)$', '', rank_str)
    def sort_by_time(self, data):
        heroes = data["heroes_ranked"]
        
        sorted_heroes = sorted(heroes, key=lambda x: x["matches"], reverse=True)
        return sorted_heroes
    def sort_by_rank(self, data):
        highest = 0
        for key in data:
            score = data[key]['max_rank_score']
            season = data[key]['rank_game_id']
            if score > highest:
                highest = score
                best = season
        if int(highest) < 3300:
            rank = "Bronze"
        elif int(highest) < 3600:
            rank = "Silver"
        elif int(highest) < 3900:
            rank = "Gold"
        elif int(highest) < 4200:
            rank = "Platinum"
        elif int(highest) < 4500:
            rank = "Diamond"
        elif int(highest) < 4800:
            rank = "Grandmaster"
        elif int(highest) < 5100:
            rank = "Celestial"
        elif int(highest) < 5400:
            rank = "Eternity"
        elif int(highest) > 5400:
            rank = "One Above All"
        else:
            rank = "Bronze"
        return best, rank
    
    def __repr__(self):
        return f"Player(name={self.name}, rank={self.rank})"
    
def parse_api_create_objects(data):
    def sort_by_time(data):
        heroes = data["heroes_ranked"]
        
        sorted_heroes = sorted(heroes, key=lambda x: x["matches"], reverse=True)
        return sorted_heroes
    

