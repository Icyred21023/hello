import json
import os
import copy

def build(paths):
    dex_path, reg_path, base_path, output_path = paths
    with open(dex_path, "r") as f:
        dex_dict = json.load(f)
    with open(reg_path, "r") as f:
        reg_dict = json.load(f)
    copy_dict = copy.deepcopy(reg_dict)
    new_json = {}
    for key, subdict in dex_dict.items():
        role = reg_dict[key]["role"]
        tier = reg_dict[key]["tier"]
        entry = {
                    key: {
                    "name": key, 
                    "role": role,
                    "tier": tier,
                    "counterPicks": [],
                    "goodAgainst": [],
                    "weakness": "qrqwr"
                    }
                }
        for subkey, inner_dict in subdict.items():
            big_counterpick_list = []
            for list_name, values in inner_dict.items():
                for character in values:
                    counter_entry = {
                        "name": character,
                        "role": list_name,
                        "score": 10,
                        "description": False
                    }
                    big_counterpick_list.append(counter_entry)

            # Set the flattened list to counterPicks
            entry[key]["counterPicks"] = big_counterpick_list
        new_json[key] = entry[key]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_json, f, indent=4, ensure_ascii=False)
                    
        







paths = []
new_path = r"C:\Users\Corey\Desktop\marvel_tracker_V5.1\html\new_matchups.json"
base_path = r"C:\Users\Corey\Desktop\marvel_tracker_V5"
old_path = os.path.join(base_path, "matchup.json")
output_path = os.path.join(base_path, "dexerto_matchup.json")
paths.extend([new_path, old_path, base_path, output_path])
build(paths)

