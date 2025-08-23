import os
debug_mode = False
script_dir = os.path.dirname(os.path.abspath(__file__))
season_dir = os.path.join(script_dir, "season.txt")
if not os.path.exists(season_dir):
    s = 7
    with open(season_dir, 'w') as f:
        f.write(str(s))
season = int(open(season_dir).read().strip())
mobile_mode = False
randomize_ban = False
randomize_matchup = False
real_debug = False
dex = False
debug_menu = True
USE_TEAMUP_SCORING = False
MATCHUP = "type_matchupNEWDPS.json"
