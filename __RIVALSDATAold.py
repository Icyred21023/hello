#pylint:disable= ''{' was never closed (__RIVALSDATA, line 154)'
import requests
import helpers
import config
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
DEBUG_PRIVATE = True
debug_private_path = helpers.create_path("_0LiveMatchPrivates.json","debug")
USE_THREADING = False
TIME = 0.025
DEBUG_JSON = True
MAX_PLAYER_WORKERS = 2
SEASON = 18
DEBUG={}
LiveDebug = True
class LiveMatch:
    
    class FetchedTeammate:
        def __init__(self,data):
            self.Uid = data.get("teammate_uid")
            self.Name = data.get("name")
            self.PlayerImgId = data.get("icon")
            self.Games = data.get("games")
            self.Wins = data.get("wins")
            self.Losses = data.get("losses")
            
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
            
        def addTeammate(self, pobj):
            self.Teammates.append(pobj)
    def __init__(self, json, match_id, user_id):
        self.MatchId = match_id
        self.UserId = user_id

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
        
    def findPrivateTeammates(self):
        
        for p in self.PrivatePlayers:
            #print(p.PlayerImgId)
            for t in self.Players:
                if p.TeamId == t.TeamId:
                    print("Teammate found: "+p.Name+" & "+t.Name)
                    p.addTeammate(t)
            for t in p.Teammates:
            #    print(t.Uid, SEASON)
                d = fetchTeammates(int(t.Uid), SEASON)
                if isinstance(d,list):
                    for item in d:
                        ft = LiveMatch.FetchedTeammate(item)
                        t.FetchedTeammates.append(ft)
                     #   print("Fetched " + ft.Name +" "+str(ft.PlayerImgId))
            for t in p.Teammates:
                    for item in t.FetchedTeammates:
                            if str(item.PlayerImgId) == p.PlayerImgId:
                                print("Found matching profile for " + p.Name + ": " + item.Name)
                                return item
                        
                    
                    
    
                    
                
        

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
         
             
             
             
        
    
    
def fetchUid(name):
    
    URL = "https://api.rivalsdata.com/players/search"
    pl= {"name": name}
    ressult = api_rivalsdata(URL, pl)
    return ressult

def fetchPlayer(uid):
    URL = "https://api.rivalsdata.com/player"
    pl= {"uid": uid}
    ressult = api_rivalsdata(URL,pl)
    return ressult
    
def fetchHeroes(uid, season= -1):
    URL = "https://api.rivalsdata.com/player/heroes"
    pl= {"uid": uid, "season": SEASON,"mode":2}
    ressult = api_rivalsdata(URL,pl)
    return ressult
    
def fetchTeammates(uid, season= -1):
    URL = "https://api.rivalsdata.com/player/teammates"
    pl= {"uid": uid, "season": SEASON}
    ressult = api_rivalsdata(URL,pl)
    return ressult
    
def fetchMatchesUpdate(uid, season= -1):
    URL = "https://api.rivalsdata.com/player/matches"
    pl= {"uid": uid, "cursor": None, "season": SEASON}
    ressult = api_rivalsdata(URL,pl)
    return ressult
    
def fetchMatchHistory(uid, season= -1):
    URL = "https://api.rivalsdata.com/player/matches/cached"
    pl= {"uid": uid, "cursor": None, "season": SEASON, "mode": 2}
    ressult = api_rivalsdata(URL,pl)
    return ressult

def fetchProficiency(uid):
    URL = "https://api.rivalsdata.com/player/proficiency"
    pl= {"uid": uid}
    ressult = api_rivalsdata(URL,pl)
    return ressult

def fetchLive(uid, mid):
    URL = "https://api.rivalsdata.com/live"
    pl= {"match_id": mid, "uid": uid}
    ressult = api_rivalsdata(URL,pl)
    return ressult
    



def api_rivalsdata(url: str, payload: dict):
    

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://rivalsdata.com",
        "Referer": "https://rivalsdata.com/",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 16; SM-S938U1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Mobile Safari/537.36"
        ),
    }

    r = requests.post(url, json=payload, headers=headers, timeout=20)
    #print("Status:", r.status_code)
    #print("Text:", r.text[:500])
    r.raise_for_status()
    return r.json()

#if __name__ == "__main__":
#    
#    for n in ["ProfChloroform","BicZilla","EyeingFlux"]:
#        
#        result = fetchUid(n)
#        p = RivalsDataPlayer(result)
#        print(p.Name, p.Uid, p.PlayerImgId)
#        print("\n") 
#        
#        resultRank= fetchPlayer(p.Uid)
#        print(resultRank)
#        print("\n")
#        
#        resultHeroes = fetchHeroes(p.Uid, season=17)
#        print(resultHeroes)
#        print("\n")
#        
#        resultProficiency=fetchProficiency(p.Uid)
#        print(resultProficiency)
#        print("\n")
#        
#        resultMatches = fetchMatchHistory(p.Uid, season=17)
#        print(resultMatches)
#        print("\n")
#        
#        resultTeammates = fetchTeammates(p.Uid, season=17)
#        print(resultTeammates)
#        print("\n")

def parsePlayerStatus(json):
    status = json.get("status").get("status")
    matchid = False
    for code in status:
        if code == "6":
            matchid = status[code]['extra'].get('battle_id', None)

            return matchid
    return False

def run_player(n):
    
    def initialize_heroes():
        for hero in resultHeroes:
            #"print(resultProficiency[p.Aid]["hero_proficiency_infos"])
            p.Heroes.append(
                RivalsDataPlayer.Hero(hero, resultProficiency[p.Aid]["hero_proficiency_infos"][str(hero.get("hero_id"))[:4]][ "proficiency_level"])
                    )
                    
    result = fetchUid(n)
    
    time.sleep(TIME)
    p = RivalsDataPlayer(result)
    #print(p.Name, p.Uid, p.PlayerImgId)
    #print("\n")
    time.sleep(TIME)
    resultRank = fetchPlayer(p.Uid)
    #print(resultRank)
    #print("\n")
    ranks = resultRank.get("rank_game_season", None)
    max_lv = 0
    max_score = 0
    for rank in ranks:
        s = ranks[rank]["max_rank_score"]
        l = ranks[rank]["max_level"]
        if s > max_score:
            max_lv = l
            max_score = s
   # r = fetchMatchesUpdate(p.Uid, season=SEASON)
    time.sleep(0.25)
    p.UpdateRank(max_lv, max_score)
    time.sleep(TIME)
    resultHeroes = fetchHeroes(p.Uid, season=SEASON)
    #print(resultHeroes)
    #print("\n")
    time.sleep(TIME)
    resultProficiency = fetchProficiency(p.Uid)
    #print(resultProficiency)
    #print("\n")
    time.sleep(TIME)
    initialize_heroes()
    #r = fetchMatchesUpdate(p.Uid, season=SEASON)
    #time.sleep(2)
    resultMatches = fetchMatchHistory(p.Uid, season=SEASON)
    #print(resultMatches)
    #print("\n")
    matches = resultMatches.get("matches", None)
    for match in matches:
        #print(match)
        p.MatchHistory.append(RivalsDataPlayer.Match(match))
    time.sleep(TIME)

    resultTeammates = fetchTeammates(p.Uid, season=SEASON)
    #print(resultTeammates)
    #print("\n")
    p.initOverviewRoles()
    print("Overview")
    print(p.Ov.GamesPlayed,p.Ov.Kills, p.Ov.Deaths, p.Ov.Assists, p.Ov.WinRate, p.Ov.Kd)
    print("\n")
    print("Vanguard")
    v = p.Roles["Vanguard"]
    print(v.GamesPlayed, v.Kills, v.Deaths, v.Assists, v.WinRate, v.Kd)
    print("\n")
    print("Duelist")
    v = p.Roles["Duelist"]
    print(v.GamesPlayed, v.Kills, v.Deaths, v.Assists, v.WinRate, v.Kd)
    print("\n")
    print("Strategist")
    v = p.Roles["Strategist"]
    print(v.GamesPlayed, v.Kills, v.Deaths, v.Assists, v.WinRate, v.Kd)
    print("\n")
    if DEBUG_JSON:
        global DEBUG
        DEBUG[p.Name] = {"Uid": result,"Rank": resultRank,"Heroes": resultHeroes, "Teammates":resultTeammates, "Proficiency": resultProficiency, "Match History": resultMatches}
    return p


def getLiveMatchNames(u):
    
    
    while True:
        try:
            
            status = fetchPlayer(u)
            status_result = parsePlayerStatus(status)
            if status_result:
                print(f"Player with UID {u} is in a match with ID: {status_result}")
                break
            time.sleep(1.5)
        except Exception as e:
             print(f"Error occurred: {e}. Stage 1. Retrying in 1.5 seconds.")
             time.sleep(1.5)
        
            
    while True:
        try:
            match = fetchLive(u, status_result)
            LiveMatchObject = LiveMatch(match, status_result, u)
            name_list = [player.Name for player in LiveMatchObject.Players]
            return name_list
        except Exception as e:
            print(f"Error occurred: {e}. Stage 2. Retrying in 3 seconds.")
            time.sleep(3)
    
    match = fetchLive(u, status_result)
    LiveMatchObject = LiveMatch(match, status_result, u)
    
    # Block for find STAR names
    
    name_list = [player.Name for player in LiveMatchObject.Players]
    return name_list
             
             
             
             


if __name__ == "__main__":
    if DEBUG_PRIVATE:
        private_match_data = helpers.load_json(debug_private_path)
        match= private_match_data[1]
        try:
            print(config.USER_UID)
            LiveMatchObject = LiveMatch(match, 100001, config.USER_UID)
            Matched_Player = LiveMatchObject.findPrivateTeammates()
        except Exception as e:
            print("Exception", e)
    
    import sys
    sys.exit()
    names = ["ProfChloroform"]
    names = helpers.load_list(helpers.create_path("_1Names.txt","debug"))
    
    

    
    first_result = fetchUid("ProfChloroform")
    
    p = RivalsDataPlayer(first_result)

    bInGame = False
    if not LiveDebug:
        while not bInGame:
            status = fetchPlayer(p.Uid)
            status_result = parsePlayerStatus(status)
            if status_result:
                print(f"{p.Name} is in a match with ID: {status_result}")
                bInGame = True
            else:
                print(f"{p.Name} is not in a match. Retrying...")
                time.sleep(2)  # Wait for 2 seconds before checking again
        time.sleep(TIME)

        match_json = fetchLive(p.Uid, status_result)
        live_match = LiveMatch(match_json, status_result, p.Uid)
        dj = {"Match": match_json, "PlayerStatus": status}
        po = helpers.create_path("__RivalsDataPlayerStatus.json","debug")
        helpers.save_json(po, dj)
    else:
        po = helpers.create_path("__RivalsDataPlayerStatus.json","debug")
        data = helpers.load_json(po)
        match_json = data.get("Match")
        status = data.get("PlayerStatus")
        live_match = LiveMatch(match_json, status["status"]["status"]["6"]["extra"]['battle_id'], p.Uid)

    playas = []

    if USE_THREADING:
        with ThreadPoolExecutor(max_workers=MAX_PLAYER_WORKERS) as executor:
            futures = {
                executor.submit(run_player, n.Name): (index, n.Name)
                for index, n in enumerate(live_match.Players)
            }

            results = [None] * len(live_match.Players)

            for future in as_completed(futures):
                index, name = futures[future]

                
                results[index] = future.result()
                

            # Remove failed results while preserving original order
            playas = [p for p in results]

    else:
        for n in live_match.Players:
            p = run_player(n.Name)
            playas.append(p)
    dp = helpers.create_path("_RivalsDataDebug.json","debug")
    helpers.save_json(dp, DEBUG)
   # path = helpers.create_path("Api.json", "debug")
    #helpers.save_json(path, result)
    #result = fetchUid("ProfChloroform")
#    p = RivalsDataPlayer(result)
#    print(p.Name, p.Uid, p.PlayerImgId)
#    print("\n") 
#    resultRank= fetchPlayer(p.Uid)
#    print(resultRank)
#    print("\n")
#    
#    resultHeroes = fetchHeroes(p.Uid, season=17)
#    print(resultHeroes)
#    print("\n")
#    
#    resultProficiency=fetchProficiency(p.Uid)
#    print(resultProficiency)
#    print("\n")
#    
#    resultMatches = fetchMatchHistory(p.Uid, season=17)
#    print(resultMatches)
#    print("\n")
#    
#    resultTeammates = fetchTeammates(p.Uid, season=17)
#    print(resultTeammates)
#    print("\n")
#    
#    path = helpers.create_path("Api.json", "debug")
#    helpers.save_json(path, result)
    