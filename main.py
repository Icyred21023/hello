from admin_utils import elevate_if_needed

elevate_if_needed()
from ocr_capture import capture_names
from tracker_lookup import open_multiple_tracker_profiles
from player import Player
import gui
from gui import show_gui, show_launcher, show_team_comparison_gui, show_countdown,show_suggestion_gui
from main3 import main3,create_heromatches_from_lists,load_hero_assets
#from matchups2 import counters
from chatsitecopymodule import run_simple_counter_logic
from matchups4 import counters, load_characters
from merge_suggestions import add_alt_suggestions
import json
import os
import tkinter as tk
import config
import random
import updater
from collections import Counter



def on_f8_pressed():
    
    print(">> Script running. Press F8 to OCR names and check tracker.gg...")
    
    

    if config.debug_mode:
        all_data = local_all_data
        if not config.randomize_ban:
            print("First 6")
            names = list(local_all_data.keys())[:6]
        else:
            print("Random 6")
            all_keys = list(local_all_data.keys())
            names = random.sample(all_keys, min(6, len(all_keys)))
        
    else:
        names = capture_names()

    print("\n🎯 Captured Player Names:")
    for name in names:
        print(f"- {name}")

    print("\n🔎 Tracker.gg Profile URLs:")
    players = []
    if not config.debug_mode:
        all_data = open_multiple_tracker_profiles(names)
        
    for name in names:
        data = all_data[name]
        if "errors" in data:
            print(f"Skipping {name}: Private Account")
            continue
        if len(data["data"]["segments"]) < 3:
            print(f"Skipping {name}, no current season data found.")
            continue
        players.append(Player(name, data))

    if players:
        show_gui(players)
        if not config.debug_mode:
            new_dict = {}
            for player in players:
                name = player.name
                nest = all_data[name]
                new_dict[name] = nest
            local = local_all_data.copy()
            local.update(new_dict)
            with open(debug_path_alldata, 'w', encoding='utf-8') as f:
                json.dump(local, f, indent=4, ensure_ascii=False)

def generate_random_team(character_pool):
    count = Counter()
    total = 0
    team = []
    while total < 6:
        char = random.choice(list(character_pool.values()))
        if count[char.name] >= 1:
            continue
        if count[char.role] > 1:
            continue
        count[char.name] += 1
        count[char.role] += 1
        team.append(char.name)
        total += 1
    return team

def on_matchup():
    print(f"Debug_Mode: {config.debug_mode}")
    if not config.debug_mode:
        show_countdown()
        
    #if config.debug_mode and not config.randomize_matchup:
        blueteam, redteam,blueclass,redclass,map = main3()
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if config.dex:
            matchup_path = os.path.join(script_dir, "dexerto_matchup.json")
        else:
            matchup_path = os.path.join(script_dir, "matchup.json")
        if config.randomize_matchup:

            character_pool = load_characters(matchup_path)
            blue = generate_random_team(character_pool) 
            red = generate_random_team(character_pool)
            blueteam, redteam,blueclass,redclass,map = create_heromatches_from_lists(blue,red)
        else:
            blueteam, redteam,blueclass,redclass,map = main3()

    
    if not blueclass:
        show_launcher(on_f8_pressed,on_matchup)
    while True:
        blue, red, image_map = show_team_comparison_gui(blueclass, redclass, map)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if config.dex:
            matchup_path = os.path.join(script_dir, "dexerto_matchup.json")
            print("NEW: Dexerto Counters Loaded")
        else:
            matchup_path = os.path.join(script_dir, "matchup.json")
            print("Standard: PeakRivals Counters Loaded")
        blueresult, redresult = counters(blue, red,matchup_path)
        alt_blueresult, _ = run_simple_counter_logic(blue, red)
        #print(alt_blueresult)
        blueresult = add_alt_suggestions(blueresult, alt_blueresult, redresult)

        # Capture modified teams if go_back is hit
        go_back_result = show_suggestion_gui(blueresult, redresult, image_map)

        if go_back_result:
            # unpack the modified teams and loop again
            blueclass, redclass = go_back_result
            continue
        else:
            break  # if no go_back, proceed normally

    
    


    


if __name__ == "__main__":
    updater.check_for_update()
    config.debug_menu = True
    config.debug_mode = False
    config.dex = False
    config.mobile_mode = False
    script_dir = os.path.dirname(os.path.abspath(__file__))
    debug_path = os.path.join(script_dir, "debug")
    debug_path_list = os.path.join(debug_path, "names_list.txt")
    debug_path_alldata = os.path.join(debug_path, "alldata.json")
    with open(debug_path_alldata, "r") as f:
        local_all_data = json.load(f)
    while True:
        show_launcher(on_f8_pressed, on_matchup)
    