import getpass
import platform
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
import threading
import helpers
import json
import __RIVALSDATA as api
import tkinter as tk
from tkinter import simpledialog

HERO_KEYS = helpers.load_json(path=os.path.join(script_dir,"_HeroKeys.json"))


    

bFrames = True
bBadges = True

DEFAULT_UI_STATS_CONFIG = {
    "Stat 1": "Time",
    "Stat 2": "Usage",
    "Stat 3": "Win %",
    "Stat A": "Mvp %",
    "Stat B": "Kills",
    "Stat C": "Deaths",
    "Stat D": "Damage/Healing",
    
}

UI_STAT_ORDER = [
    "Stat 1",
    "Stat 2",
    "Stat 3",
    "Stat A",
    "Stat B",
    "Stat C",
    "Stat D",
    
]
ADMIN_USERNAMES = {"Chloroform", "icyre", "Corey"}
bUseCloudSync = False
def get_local_username():
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USERNAME", "unknown")
    

if 'storage/emulated/0' in script_dir:
    print('Android Detected')
    debug_mode = True
    mobile_mode = True
else:
    print("Windows detected")
    debug_mode = False
    mobile_mode = False
    
api_key = 'null'
if mobile_mode:
    # Android (Pydroid-safe)
    local_marvel_tracker_path = os.path.join(
        os.path.expanduser("~"),
        "MarvelTrackerV5"
    )
else:
    # Windows
    local_marvel_tracker_path = os.path.join(
        os.environ["LOCALAPPDATA"],
        "MarvelTrackerV5"
    )
    appdata_local = os.environ.get("LOCALAPPDATA")
    brave_data_dir = os.path.join(appdata_local, "BraveSoftware", "Brave-Browser", "User Data")

LOCAL_USERNAME = get_local_username()

IS_ADMIN = LOCAL_USERNAME in ADMIN_USERNAMES

def load_extract_user(path, bReturn_json=False):
    account_json = helpers.load_json(path)
    user = account_json.get("name")
    uid = account_json.get("uid")
    if bReturn_json:
        return user, uid, account_json
    return user, uid

def askdialog(title, prompt):
    root = tk.Tk()
    root.withdraw()  # hide main window
    result = simpledialog.askstring(title, prompt)
    root.destroy()
    return result

if IS_ADMIN:
    print(f"[CONFIG] Admin user detected: {LOCAL_USERNAME}")
else:
    print(f"[CONFIG] User detected: {LOCAL_USERNAME}")
if not os.path.exists(local_marvel_tracker_path):
    os.makedirs(local_marvel_tracker_path)
    os.makedirs(os.path.join(local_marvel_tracker_path, "config"))
api_key_path = os.path.join(local_marvel_tracker_path, "config", "api_key.txt")
stats_config_path = os.path.join(local_marvel_tracker_path, "config", "ui_config.json")



ap = helpers.create_path("user_account.json", "debug")
ap2 = os.path.join(local_marvel_tracker_path, "config", "user_account.json")


if os.path.exists(ap2):
    USER_NAME, USER_UID = load_extract_user(ap2)

else:
    if os.path.exists(ap):
        user, uid, account_json = load_extract_user(ap, bReturn_json=True)
        USER_NAME = askdialog("Missing Info", "Enter Marvel Rivals Username:")
        if USER_NAME.lower() == user.lower():
            helpers.save_json(ap2, account_json)
            USER_UID = uid
        else:
            USER_UID = askdialog("Missing Info", "Enter Marvel Rivals UID Number:")
            account_json = {"name": USER_NAME,"uid": USER_UID}
            helpers.save_json(ap2, account_json)    
    else:
        USER_NAME = askdialog("Missing Info", "Enter Marvel Rivals Username:")
        USER_UID = askdialog("Missing Info", "Enter Marvel Rivals UID Number:")
        account_json = {"name": USER_NAME,"uid": USER_UID}
        helpers.save_json(ap2, account_json)
        
# if not os.path.exists(ap2):
#     root = tk.Tk()
#     root.withdraw()
#     USER_NAME = simpledialog.askstring("Missing Info", "Enter Marvel Rivals Username:")
#     if os.path.exists(ap):
#         account_json_old = helpers.load_json(ap)
#         old_name = account_json_old["name"]
#         if USER_NAME.lower() == old_name.lower():
#             account_json = account_json_old
            
#         else:
#             USER_UID = simpledialog.askstring("Missing Info", "Enter Marvel Rivals UID Number:")
#     root.destroy()
#     account_json = {"name": USER_NAME,"uid": USER_UID}
#     helpers.save_json(ap2,account_json)

# else:
#     account_json = helpers.load_json(ap2)
#     USER_NAME = account_json["name"]
#     USER_UID = account_json["uid"]
    
# if os.path.exists(ap):
#     account_json = helpers.load_json(ap)
#     USER_NAME = account_json["name"]
#     USER_UID = account_json["uid"]
# else:
#     root = tk.Tk()
#     root.withdraw()  
#     USER_NAME = simpledialog.askstring("Missing Info", "Enter Marvel Rivals Username:")   
#     root.destroy()
#     result = api.fetchUid(USER_NAME)
#     p = api.RivalsDataPlayer(result)
#     USER_UID = p.Uid
#     account_json = {"name": USER_NAME,"uid": USER_UID}
#     helpers.save_json(ap,account_json)


def load_ui_stats_config():
    config = DEFAULT_UI_STATS_CONFIG.copy()

    try:
        if os.path.exists(stats_config_path):
            loaded = helpers.load_json(stats_config_path)

            if isinstance(loaded, dict):
                config.update(loaded)

        # auto-save if file was missing keys or did not exist
        save_ui_stats_config_dict(config)

    except Exception as e:
        print(f"Error loading UI stats config: {e}\nUsing default stats.")
        save_ui_stats_config_dict(config)

    return [config[key] for key in UI_STAT_ORDER]

def save_ui_stats_config(stat_list):
    config = DEFAULT_UI_STATS_CONFIG.copy()

    for i, key in enumerate(UI_STAT_ORDER):
        if i < len(stat_list):
            config[key] = stat_list[i]

    save_ui_stats_config_dict(config)

def save_ui_stats_config_dict(config):
    with open(stats_config_path, "w") as f:
        json.dump(config, f, indent=4)

ui_stats_list = load_ui_stats_config()

# def save_ui_stats_config(stat_list):
#     ui_stats_config = {
#         "Stat 1": stat_list[0],
#         "Stat 2": stat_list[1],
#         "Stat A": stat_list[2],
#         "Stat B": stat_list[3],
#         "Stat C": stat_list[4],
#         "Stat D": stat_list[5],
#     }
#     with open(stats_config_path, 'w') as f:
#         json.dump(ui_stats_config, f, indent=4)

        
# if not os.path.exists(stats_config_path):
#     ui_stats_config = {
#         "Stat 1": "Time",
#         "Stat 2": "Usage",
#         "Stat A": "Mvp %",
#         "Stat B": "Kills",
#         "Stat C": "Deaths",
#         "Stat D": "Damage/Healing",
#     }
#     with open(stats_config_path, 'w') as f:
#         json.dump(ui_stats_config, f, indent=4)
#     ui_stats_list = ["Time", "Usage", "Mvp %", "Kills", "Deaths", "Damage/Healing"]
# else:
    
#     ui_stats_config = helpers.load_json(stats_config_path)
#     ui_stats_list = load_ui_stats_config()
    #ui_stats_list = [ui_stats_config["stat1"], ui_stats_config["stat2"], ui_stats_config["statA"], ui_stats_config["statB"], ui_stats_config["statC"], ui_stats_config["statD"]]


    
sqlite_db_dir = os.path.join(local_marvel_tracker_path, "players_db_New")
if not os.path.exists(sqlite_db_dir):
    os.makedirs(sqlite_db_dir)
sqlite_db_path = os.path.join(sqlite_db_dir, "players_stats.db")
def ask_api_key():
    from tkinter import simpledialog
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()  # hide main window

    name = simpledialog.askstring(
        title="OpenAI API Key",
        prompt="Please enter your OpenAI API Key:"
    )

    return name

def save_api_key(key,path=api_key_path):
    with open(path, 'w') as f:
        f.write(key)

def load_config():
    configfolder = os.path.join(script_dir, "config")
    if not os.path.exists(configfolder):
        os.makedirs(configfolder)
    configpath = helpers.create_path("config.json", "config")
    if os.path.exists(configpath):
        config_json = helpers.load_json(configpath)
        auto_update = config_json['auto_update']
        dependency_check = config_json['dependency_check']
        return auto_update, dependency_check
    else:
        config_json = {
            "auto_update": False,
            "dependency_check": False,
        }
        helpers.save_json(configpath, config_json)
        return 69, False
    
OCR = threading.Event()
f8hotkey = None

cloud_checkpoint_dir = os.path.join(sqlite_db_dir, "cloud_checkpoint")
if not os.path.exists(cloud_checkpoint_dir):
    os.makedirs(cloud_checkpoint_dir)

cloud_checkpoint_db = os.path.join(cloud_checkpoint_dir, "checkpoint_master.db")
cloud_checkpoint_meta = os.path.join(cloud_checkpoint_dir, "checkpoint_meta.json")

pending_diffs_path = os.path.join(sqlite_db_dir, "pending_diffs.jsonl")

if 'storage/emulated/0' in script_dir:
    print('Android Detected')
    debug_mode = True
    mobile_mode = True
else:
    print("Windows detected")
    debug_mode = False
    mobile_mode = False



if os.path.exists(api_key_path):
    api_key = open(api_key_path).read().strip()
    if api_key == 'null' or api_key == '':
        print("Invalid API key found, asking user to input a new one.")
        api_key = ask_api_key()
        save_api_key(api_key)
else:
    print("No saved API key found, asking user to input one.")
    api_key = ask_api_key()
    save_api_key(api_key)

script_dir = os.path.dirname(os.path.abspath(__file__))
season_dir = os.path.join(script_dir, "season.txt")
auto_update, dependency_check = load_config()



if not os.path.exists(season_dir):
    s = 7
    with open(season_dir, 'w') as f:
        f.write(str(s))

season = int(open(season_dir).read().strip())

randomize_ban = False
randomize_matchup = False
real_debug = False
dex = False
debug_menu = True
USE_TEAMUP_SCORING = False
bPrivateLookup = False
MATCHUP = "type_matchupNEWDPS.json"

if mobile_mode:
                    p = os.path.join(script_dir, "debug","LiveDebug.json")
                    livedebug= helpers.load_json(path=p)
