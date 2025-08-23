import json
import config
import os
from icyred_matchup_logic import save_json


def load_json(p):
    debug_dir = os.path.join(config.script_dir, 'debug')
    pa = os.path.join(debug_dir, p)
    with open(pa, "r") as f:
        j = json.load(f)
    return j

alldata = load_json('alldata.json')
chloro = load_json('me.json')
seg = chloro['data']
for player in alldata:
    alldata[player]['data']['segments'] = seg
    break
save_json('alldata5.json',alldata)



