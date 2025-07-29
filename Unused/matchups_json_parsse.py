import json
import os




new_json = {}
script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "matchup.json")
save = os.path.join(script_dir,"editmatchup.json")
with open(matchup_path, "r") as f:
    data = json.load(f)
new_json = data    
for key in data:
    
    new_json[key]["goodInto"] = []
for key in data:
    name = data[key]["name"]
    goodlist = []
    for item in data[key]["counterPicks"]:
        n = item["name"]
        goodlist = new_json[n]["goodInto"]
        goodlist.append(name)
        new_json[n]["goodInto"] = goodlist
   
with open(save, "w", encoding="utf-8") as f:
    json.dump(new_json, f, indent=2)
    
    