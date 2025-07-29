import json
from collections import defaultdict, Counter
import pandas as pd
import os

# Load the JSON data (replace path with your actual file location)

script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "matchup.json")
with open(matchup_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

# Convert dict to hero list and retain name-based lookup
hero_data = list(raw.values())
heroes_by_name = raw  # already in name: hero format

# Organize heroes by role
heroes_by_role = defaultdict(list)
for hero in hero_data:
    heroes_by_role[hero["role"]].append(hero)

ALL_ROLES = ["Duelist", "Vanguard", "Strategist"]

# Function to gather counter picks of a specific role against the enemy team
def gather_counters(enemy_team, role):
    counters = []
    if role != "Strategist":
        for enemy in enemy_team:
            counters.extend([
                cp["name"] for cp in enemy.get("counterPicks", [])
                if cp["role"] == role
            ])
    else:
        for enemy in enemy_team:
            if enemy["role"] in ["Duelist", "Vanguard"]:
                counters.extend([
                    cp["name"] for cp in enemy.get("counterPicks", [])
                    if cp["role"] == role
                ])
    return counters

# Function to return top N most frequent names
def most_frequent(counters, num=2):
    count = Counter(counters)
    return [name for name, _ in count.most_common(num)]

# 🟦 EXAMPLE enemy team (you can replace this with any 6 hero names)
enemy_team_names = ["Venom", "Peni Parker", "Hawkeye", "Black Panther", "Luna Snow", "Loki"]

# Get hero data for enemy team
enemy_team = [heroes_by_name[name] for name in enemy_team_names if name in heroes_by_name]

# Generate the recommended counter team
counter_team = []
used_names = set()

for role in ALL_ROLES:
    counter_names = gather_counters(enemy_team, role)
    top_counters = most_frequent(counter_names, num=2)
    for name in top_counters:
        if name not in used_names and name in heroes_by_name:
            used_names.add(name)
            counter_team.append(heroes_by_name[name])

# Show output
counter_team_df = pd.DataFrame(counter_team)
print("Recommended Counter Team:")
print(counter_team_df[["name", "role", "tier"]])
