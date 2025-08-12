import json
import os
from collections import defaultdict, Counter
from matchups4 import Character, TeamResult, TeamMember, Suggestion
import config
script_dir = os.path.dirname(os.path.abspath(__file__))
matchup_path = os.path.join(script_dir, config.MATCHUP)

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

def most_frequent(counters, num=4):
    count = Counter(counters)
    return [name for name, _ in count.most_common(len(count))]

def run_simple_counter_logic(blue_names, red_names,flag=False):
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
    track = {}
    noneflag = False
    for role in ALL_ROLES:
        counter_names = gather_counters([raw[name] for name in red_names if name in raw], role)
        top_counters = most_frequent(counter_names, num=4)
        count = 0
        track[role] = {}
        track[role]['count'] = count
        track[role]['top_counters'] = top_counters
        for name in top_counters:    
                
            if name not in used_names and name in character_pool:
                count +=1
                track[role]['count'] = count
                used_names.add(name)
                counter_team.append(character_pool[name])
                if count == 2:
                    track[role]['count'] = count
                    break
    print(f"Counter Team Alts: \n{counter_team}")
    total_count = 0
    for roles in ALL_ROLES:
        total_count += track[roles]['count']
    for roles in ALL_ROLES:
        print(f"Total Count: {total_count}")
        count = track[roles]['count']
        if total_count ==6:
            break
        if count <2:
            
            if roles == 'Duelist':
                subrole = "Vanguard"
            elif roles == 'Vanguard':
                subrole = "Duelist"
            elif roles == "Strategist":
                subrole = "Duelist"
            else:
               subrole = "Duelist"
            top = track[subrole]["top_counters"]
            for character in top:
                
                if character in used_names:
                    continue
                else:
                    
                    print(f"Adding extra {subrole}: {character}")
                    used_names.add(character)
                    total_count += 1
                    count += 1
                    track[roles]['count'] = count
                    print(f"Total Count After Add {total_count}")
                    if total_count == 6:
                        break
               
            
    if flag:
        return used_names
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
