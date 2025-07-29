import json
import os
from collections import defaultdict, Counter
from matchups4 import Character, TeamResult, TeamMember, Suggestion

script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, "matchup.json")

with open(matchup_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

hero_data = list(raw.values())
heroes_by_name = raw
ALL_ROLES = ["Duelist", "Vanguard", "Strategist"]

# Organize heroes by role
heroes_by_role = defaultdict(list)
for hero in hero_data:
    heroes_by_role[hero["role"]].append(hero)


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

def most_frequent(counters, num=2):
    count = Counter(counters)
    return [name for name, _ in count.most_common(num)]

def run_simple_counter_logic(blue_names, red_names):
    # Build Character objects
    character_pool = {name: Character(data) for name, data in raw.items()}

    # Build red (enemy) team
    red_team = [character_pool[name] for name in red_names if name in character_pool]

    # Build original blue team
    original_blue_team = [character_pool[name] for name in blue_names if name in character_pool]
    original_score = sum(c.evaluate_vs_team(red_team) or c.matchup_score for c in original_blue_team)

    # Generate a new recommended counter team
    counter_team = []
    used_names = set()
    for role in ALL_ROLES:
        counter_names = gather_counters([raw[name] for name in red_names if name in raw], role)
        top_counters = most_frequent(counter_names, num=2)
        for name in top_counters:
            if name not in used_names and name in character_pool:
                used_names.add(name)
                counter_team.append(character_pool[name])
    print(f"Counter Team Alts: \n{counter_team}")

    # Re-evaluate new blue team against red team
    updated_score = sum(c.evaluate_vs_team(red_team) or c.matchup_score for c in counter_team)

    # Build suggestions for blue team
    members = []
    for i in range(6):
        orig = original_blue_team[i] if i < len(original_blue_team) else None
        new = counter_team[i] if i < len(counter_team) else None
        if orig and new:
            sug = Suggestion(orig.name, new.name, orig.matchup_score, new.matchup_score, i + 1)
            members.append(TeamMember(new, sug))
        elif new:
            sug = Suggestion(new.name, new.name, new.matchup_score, new.matchup_score, i + 1)
            members.append(TeamMember(new, sug))

    blue_result = TeamResult(members, original_score, updated_score)

    # Build red team result
    for char in red_team:
        char.evaluate_vs_team(counter_team)

    red_score = sum(c.matchup_score for c in red_team)
    red_members = [TeamMember(c, Suggestion(c.name, c.name, c.matchup_score, c.matchup_score, None)) for c in red_team]
    red_result = TeamResult(red_members, red_score, red_score)

    return blue_result, red_result
