import config
from typing import List
import re

SEASON = 9
UID = config.USER_UID if not config.mobile_mode else "1660533436"


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
        self.rank_delta = match_stats['rankedDelta']['displayValue']
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


class Player:
    def __init__(self, data):
        self.Name = data.get("name", "Unknown")
        self.Uid = str(data.get("uid", "Unknown"))

        self.Team = data.get("side")
        self.TeamId = data.get("team_id")

        self.Icon = data.get("icon", "Unknown")
        self.PlayerImgId = self.Icon

        self.bPrivate = "**" in self.Name

        self.Heroes: dict[str, Hero] = {}
        self.bPrivate = True if "***" in self.Name else False

        for hero_data in data.get("proficiency") or []:
            hero = Hero(hero_data)
            self.Heroes[hero.Name] = hero

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
            self.matches: List[Match] = [MatchHistory(match) for match in matchhistory]

    def add_profile(self, profile_data):
        from playerNEW import Overview,FullOverview, Role
        if profile_data:
            overview_data = getSegmentFromType(profile_data, "overview")
            rank_data = getSegmentFromType(profile_data, "ranked-peaks")
            self.best_rank = strip_rank_tier(rank_data['stats']['lifetimePeakRanked']['metadata']['tierName'])
            self.season_rank = strip_rank_tier(overview_data['stats']['peakRanked']['metadata']['tierName'])
            self.seasons_string = ""
            self.seasonal_overview = Overview(overview_data)
            self.full_overview = self.seasonal_overview
            sorted_heros = self.sort_by_time(profile_data)
            
            roles_data = self.getRolesData(profile_data)
            if roles_data:
                    self.roles: List[Role] = [Role(role_seg) for role_seg in roles_data]
                    self.roles.sort(key=lambda r: r.time_played, reverse=True)


            



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
    matchobj = Match(config.livedebug)
    for p in matchobj.Players:
        print('\n')
        print(p.Name)
        idx = 0
        for h in p.Heroes:
            idx +=1
            hero = p.Heroes[h]
            print(f'\tHero #{idx}: {hero.Name}, Level: {hero.ProficiencyLevel}')