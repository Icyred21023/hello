import config
import helpers
from typing import List
SEASON = 9

def fetchTeammates(uid, season= -1):
    ressult = 7
    return ressult
    
    
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