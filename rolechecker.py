import config
import os
import json


script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, config.MATCHUP)

with open(matchup_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

for char in raw:
    counters = raw[char]["counterPicks"]
    for counter in counters:
        if "role" not in counter:
            print(f"{char}'s counter: {counter['name']}, no role found")
            name = counter['name']
            counter['role'] = raw[name]['role']
            print(f"----- {counter['role']} added to {counter['name']}")

matchup_path = os.path.join(script_dir, "type_matchup_ROLEFIX")

with open(matchup_path, 'w', encoding='utf-8') as f:
        json.dump(raw, f, indent=4, ensure_ascii=False)