#pylint:disable=C0303
#pylint:disable=C0116
# pylint:disable= 'invalid syntax'
import os
import json
import random
from collections import defaultdict
from matchups4 import load_characters
from chatsitecopymodule import run_simple_counter_logic
import config
import copy
import math

class Suggestion:
    def __init__(self, data):
        self.original = data["original"]
        self.replacement = data["replacement"]
        self.orig_score = data["orig_score"]
        self.new_score = data["new_score"]
        self.priority = None
        self.alt_score = None  # optional third comparison score

class TeamMember:
    def __init__(self, character, suggestion=None, alt_suggestion=None):
        self.character = character
        self.suggestion = suggestion  # From matchups4
        self.alt_suggestion = alt_suggestion  # From chatsitecopy

class TeamResult:
    def __init__(self, members, original_score, updated_score):
        for i, member in enumerate(members, 1):
            setattr(self, str(i), member)
        self.original_score = original_score
        self.updated_score = updated_score

class Team:
    def __init__(self, members, data, flag=False):
        for i, member in enumerate(members, 1):
            setattr(self, str(i), member)
        
        self.total_score = data["totalScore"]
        self.teamup_score = data["teamupScore"]/ 2
        self.stats_score = data['dps_score'] + data['hps_score'] + data['health_score']
        self.dps = data['dps_total']
        self.hps= data['hps_total']
        self.health = data['health_total']
        if flag:
            self.stats_score2 = data['dps_score_2'] + data['hps_score_2'] + data['health_score_2']
            self.stats_score3 = data['dps_score_3'] + data['hps_score_3'] + data['health_score_3']
            self.total_score2 = data["totalScore_2"]
            self.total_score3 = data["totalScore_3"]

        

class Character:
    def __init__(self, data):
        self.name = data["name"]
        self.role = data["role"]
        self.countered_by = []
        self.matchup_score = data["score"]
        self.counters_given = []
        self.counters_received = []
    def evaluate_vs_team(self, enemy_team):
        self.matchup_score = 0
        self.counters_given = []
        self.counters_received = []
        for enemy in enemy_team:
            if enemy.name in self.countered_by:
                self.matchup_score -= 1
                self.counters_received.append(enemy.name)
            if self.name in enemy.countered_by:
                self.matchup_score += 1
                self.counters_given.append(enemy.name)

class Hero:
    def __init__(self, data, name,flag=False):
        self.name = name
        self.role = data["role"]
        
        self.matchup_score = data["CounterCatScore"]
        self.teamup_names = []
        if flag:
            self.matchup_score2 = data["CounterCatScore_2"]
            self.matchup_score3 = data["CounterCatScore_3"]

suggestions_team1_stats = {}
suggestions_blueteam = []
CATEGORY_ADVANTAGE = {
    "Dive": "Poke",
    "Poke": "Brawl",
    "Brawl": "Dive"
}
def save_json(path,data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "debug", path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_text(path,lines):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "debug", path)
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + "\n")
        
def print_team_result_details(team_result):
    print("=== TeamResult ===")
    print(f"Original Score: {team_result.original_score}")
    print(f"Updated Score: {team_result.updated_score}")

    for i in range(1, 7):
        member = getattr(team_result, str(i), None)
        if member:
            print(f"\n--- TeamMember {i} ---")
            print(f"Character: {member.character.name}")
            print(f"  Role: {member.character.role}")
            print(f"  Matchup Score: {member.character.matchup_score}")
            print(f"  Counters Given: {member.character.counters_given}")
            print(f"  Counters Received: {member.character.counters_received}")

            if member.suggestion:
                print("  Suggestion:")
                print(f"    Original: {member.suggestion.original}")
                print(f"    Replacement: {member.suggestion.replacement}")
                print(f"    Orig Score: {member.suggestion.orig_score}")
                print(f"    New Score: {member.suggestion.new_score}")
                print(f"    Priority: {member.suggestion.priority}")
                print(f"    Alt Score: {member.suggestion.alt_score}")
            else:
                print("  Suggestion: None")

            if member.alt_suggestion:
                print("  Alt Suggestion:")
                print(f"    Original: {member.alt_suggestion.original}")
                print(f"    Replacement: {member.alt_suggestion.replacement}")
                print(f"    Orig Score: {member.alt_suggestion.orig_score}")
                print(f"    New Score: {member.alt_suggestion.new_score}")
                print(f"    Priority: {member.alt_suggestion.priority}")
                print(f"    Alt Score: {member.alt_suggestion.alt_score}")
            else:
                print("  Alt Suggestion: None")


def build_result(blue_members, red_members, scores):
    blue_result = TeamResult(blue_members, scores["Blue"]["original"], scores["Blue"]["new"])
    red_result = TeamResult(red_members, scores["Red"]["original"], scores["Red"]["new"])
    
    return blue_result, red_result

def gen_random_teams(data):
    roles = defaultdict(list)
    for name, char_data in data.items():
        role = char_data.get("role")
        if role:
            roles[role].append(name)

    role_limit = 2
    roles_needed = ["Duelist", "Vanguard", "Strategist"]

    def generate_team(source_roles):
        selected = []
        for role in roles_needed:
            selected += random.sample(source_roles[role], role_limit)
        random.shuffle(selected)
        return selected

    team1 = generate_team(roles)
    remaining_pool = set(data.keys()) - set(team1)

    roles_remaining = defaultdict(list)
    for name in remaining_pool:
        role = data[name]["role"]
        roles_remaining[role].append(name)

    team2 = generate_team(roles_remaining)
    return team1, team2

def parse_categories(cat_str):
    return [cat.strip() for cat in cat_str.split("/")]

def get_matchup_score(attacker, defender):
    attacker_types = parse_categories(attacker)
    defender_types = parse_categories(defender)
    pos = 0
    neg = 0
    for atk in attacker_types:
        for dfn in defender_types:
            if CATEGORY_ADVANTAGE.get(atk) == dfn:
                pos += 1
            elif CATEGORY_ADVANTAGE.get(dfn) == atk:
                neg += 1
    return pos, neg

def calculate_team_stats(team, data):
    stats = {
        "dps": 0, "hps": 0, "health": 0,
        "roles": {
            "Duelist": {
                "dps_total": 0, "dps_count": 0,
                "health_total": 0, "health_count": 0
            },
            "Strategist": {
                "hps_total": 0, "hps_count": 0
            },
            "Vanguard": {
                "dps_total": 0, "dps_count": 0,
                "health_total": 0, "health_count": 0
            }
        }
    }

    for char in team:
        char_data = data[char]
        role = char_data.get("role")

        dps = char_data.get("dps", 0)
        hps = char_data.get("hps", 0)
        health = char_data.get("health", 0)

        stats["dps"] += dps
        stats["hps"] += hps
        stats["health"] += health

        if role == "Duelist":
            stats["roles"]["Duelist"]["dps_total"] += dps
            stats["roles"]["Duelist"]["dps_count"] += 1
            stats["roles"]["Duelist"]["health_total"] += health
            stats["roles"]["Duelist"]["health_count"] += 1

        elif role == "Strategist":
            stats["roles"]["Strategist"]["hps_total"] += hps
            stats["roles"]["Strategist"]["hps_count"] += 1

        elif role == "Vanguard":
            stats["roles"]["Vanguard"]["dps_total"] += dps
            stats["roles"]["Vanguard"]["dps_count"] += 1
            stats["roles"]["Vanguard"]["health_total"] += health
            stats["roles"]["Vanguard"]["health_count"] += 1

    return stats

def score_teams(team1, team2, team_name, data, score_dict, record_team_totals=False):
    team1_stats = calculate_team_stats(team1, data)
    if team_name == "Blue":
        global suggestions_team1_stats,suggestions_blueteam
        suggestions_team1_stats = team1_stats.copy()
        suggestions_blueteam = team1
    team2_stats = calculate_team_stats(team2, data)

    # Bypass using full unused team for averaging 
    if team_name == "Suggestions":
        suggestions_stats_copy = team1_stats.copy()
        team1_stats = suggestions_team1_stats.copy()
        unused_team = team1
        team1 = suggestions_blueteam

    def calc_multiplie4r(blue_val, red_val, min_gap=10, max_gap=100, max_scale=2):
        
        #Returns a multiplier that starts scaling after red_val exceeds blue_val by min_gap,
        #and reaches max_scale at max_gap difference.
        #"""
        diff = red_val - blue_val
        if diff <= min_gap:
            return 0
        scale_range = max_gap - min_gap
        scaled_diff = diff - min_gap
        return min((scaled_diff / scale_range) * max_scale, max_scale)

    def calc_multiplier4(blue_stat, red_stat):
        if red_stat == 0:
            return 0
        return round((blue_stat / red_stat), 2)

    


    def calc_multiplier(blue_stat, red_stat):
        diff = red_stat - blue_stat
        if blue_stat == 0:
            blue_stat = red_stat
        div = red_stat / blue_stat

        return round(div, 2)
        return round(1 + (diff ) / (0.1*blue_stat),2)  # Linear scale: 10→1, 100→2

    base_weights = {"dps": 0.15, "hps": 0.15, "health": 0.15}
    multipliers = {
        stat: calc_multiplier(team1_stats[stat], team2_stats[stat])
        for stat in base_weights
}
    


    avg_team1_stats = {
    stat: team1_stats[stat] / len(team1) if team1 else 1
    for stat in ["dps", "hps", "health"]
}

    role_avg_team1 = {
    "Duelist": {},
    "Vanguard": {},
    "Strategist": {}
}

    for role, stat_key in [("Duelist", "dps"), ("Duelist", "health"),
                        ("Vanguard", "health"), ("Vanguard", "dps"),
                        ("Strategist", "dps"),("Strategist","hps")]:
        stat_total_key = f"{stat_key}_total"
        stat_count_key = f"{stat_key}_count"

        role_info = team1_stats["roles"].get(role, {})

        if role_info.get(stat_count_key, 0) > 0:
            avg = role_info[stat_total_key] / role_info[stat_count_key]
        else:
            avg = avg_team1_stats[stat_key]  # fallback to team-wide average

        role_avg_team1[role][stat_key] = avg

    total_counterscore = 0
    total_category_score = 0
    tally_countering = 0
    tally_countered = 0
    teamTotalScore = 0

    if team_name == "Suggestions":
        team1 = unused_team


    for char in team1:
        score_dict[team_name][char] = {"red_matchup": {}}
        char_data = data[char]
        role = char_data["role"]
        category = char_data["category"]
        counterPicks = [cp["name"] for cp in char_data.get("counterPicks", [])]
        
        countering = 0
        countered = 0
        cat_pos = 0
        cat_neg = 0

        for enemy in team2:
            enemy_data = data[enemy]
            enemy_role = enemy_data["role"]
            enemy_category = enemy_data["category"]
            enemy_counters = [cp["name"] for cp in enemy_data.get("counterPicks", [])]

            score = 0
            if enemy in counterPicks:
                score -= 1
                countered += 1
            if char in enemy_counters:
                score += 1
                countering += 1

            pos, neg = get_matchup_score(category, enemy_category)
            cat_pos += pos
            cat_neg += neg

            score_dict[team_name][char]["red_matchup"][enemy] = {
                "counter_score": score,
                "category_score": pos - neg,
                "enemy_role": enemy_role,
                "enemy_category": enemy_category
            }

        counted = countering - countered
        total_counterscore += counted
        total_category_score += cat_pos - cat_neg
        tally_countering += countering
        tally_countered += countered

        dps = char_data.get("dps", 0)
        hps = char_data.get("hps", 0)
        hp = char_data.get("health", 0)

        def stat_score(val, avg):
            if val == 0:
                return 0
            return round(max(-3, min(3, (2*(val - avg)) / avg)), 1)
        if role == "Strategist":
            print()

        dps_avg = round(role_avg_team1[role]["dps"],2)
        hps_avg = round(role_avg_team1[role]["hps"],2) if role == "Strategist" else 0
        hp_avg  = round(role_avg_team1[role]["health"],2) if role != "Strategist" else hp

        dps_score = stat_score(dps, dps_avg) if role == "Duelist" or role == "Vanguard" else stat_score(dps, dps_avg) * 1
        hps_score = stat_score(hps, hps_avg)
        hp_score  = stat_score(hp, hp_avg) if role == "Vanguard" else stat_score(hp, hp_avg) * 1
        cat = cat_pos - cat_neg
        totalScore = (
    (counted * 1) +
    (cat * 0.15) +
    (dps_score * multipliers["dps"] * 0.3) +
    (hps_score * multipliers["hps"]*0.3) +
    (hp_score  * multipliers["health"]*0.3)
)
        
        totalScore = round(totalScore, 1)
        teamTotalScore += totalScore
        score_dict[team_name][char] = {
            "totalScore": totalScore,
            "total_counter_score": counted,
            "total_category_score": cat_pos - cat_neg,
            "role": role,
            "category": category,
            "dps": dps,
            "hps": hps,
            "health": hp,
            "dps_score": dps_score,
            "hps_score": hps_score,
            "health_score": hp_score,
            "dps_weighted": round(dps_score * multipliers["dps"], 1),
            "hps_weighted": round(hps_score * multipliers["hps"], 1),
            "health_weighted": round(hp_score * multipliers["health"], 1),
            "dps_role_avg": dps_avg,
            "hps_role_avg": hps_avg,
            "health_role_avg": hp_avg,
            "red_matchup": score_dict[team_name][char]["red_matchup"]
        }

    if record_team_totals:
        score_dict["Totals"]["BlueTeam" if team_name == "Blue" else "RedTeam"] = {
            "teamTotalScore": round(teamTotalScore, 1),
            "counters_score": tally_countering - tally_countered,
            "category_score": total_category_score,
            "dps_total": team1_stats["dps"],
            "hps_total": team1_stats["hps"],
            "health_total": team1_stats["health"],
            "team_list": team1,
            "multipliers": multipliers
        }

def homemade_scoring(red, blue, flag):
    score_dict = {"Totals": {"BlueTeam": {}, "RedTeam": {}}, "Blue": {}, "Red": {}, "Suggestions": {}}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, config.MATCHUP)

    character_pool = load_characters(matchup_path)
    with open(matchup_path, encoding="utf-8") as f:
        data = json.load(f)

    unused = [item for item in character_pool if item not in blue]

    score_teams(blue, red, "Blue", data, score_dict, record_team_totals=True)
    score_teams(red, blue, "Red", data, score_dict, record_team_totals=True)
    if flag:
        score_teams(unused, red, "Suggestions", data, score_dict, record_team_totals=False)

    return score_dict

def sort_end_results(data):
    sug = data["Suggestions"]

    # Sort names by CounterCatScore (highest first)
    sorted_names = sorted(sug, key=lambda k: sug[k].get("CounterCatScore", float("-inf")), reverse=True)

    # Overwrite Suggestions with sorted order
    sorted_sug = {name: sug[name] for name in sorted_names}
    data["Suggestions"] = sorted_sug

    # Build role-filtered dicts from the sorted Suggestions
    duelist    = {k: v for k, v in sorted_sug.items() if v.get("role") == "Duelist"}
    vanguard   = {k: v for k, v in sorted_sug.items() if v.get("role") == "Vanguard"}
    strategist = {k: v for k, v in sorted_sug.items() if v.get("role") == "Strategist"}

    # Return deep copies (if needed)
    return data, copy.deepcopy(duelist), copy.deepcopy(vanguard), copy.deepcopy(strategist)

def build_teams(data, replacements=None):
    members = []
    for member in data:
        role = data[member]["role"]
        matchup_score = data[member]["CounterCatScore"]
        teamup_score = data[member]["teamupScore"]
        if teamup_score >0:
            teamups = data[member]['teamups']
            for teamup in teamups:

        
                char_data = {
            "name": member,
            "role": role,
            "score": matchup_score,
            'teamup': role}
        
        char = Character(char_data)
        new_score = matchup_score
        new_member = member
        if replacements is not None:
            replacement_member = replacements["Replacements"][member]["replacement"]
            if replacement_member:
                new_score = replacements["Replacements"][member]["replacement_score"]
                new_member = replacement_member
        new_char_data = {
            "replacement": new_member,
            "original": member,
            "new_score": new_score,
            "orig_score": matchup_score
        }
        sugg = Suggestion(new_char_data)
        members.append(TeamMember(char, sugg))

    return members

def create_class_objects_1(data,new,replacements):
    blue_orig = data["Blue"]
    red_orig = data["Red"]
    blue_members = build_teams(blue_orig, replacements)
    red_members = build_teams(red_orig)
    #get scores
    scores = {}
    blue_original_score = data["Totals"]["BlueTeam"]["teamTotalScore"]
    red_original_score = data["Totals"]["RedTeam"]["teamTotalScore"]
    blue_new_score = new["Totals"]["BlueTeam"]["teamTotalScore"]
    red_new_score = new["Totals"]["RedTeam"]["teamTotalScore"]
    scores["Blue"] = {"original": round(blue_original_score,1), "new": round(blue_new_score,1)}
    scores["Red"] = {"original": round(red_original_score,1), "new": round(red_new_score,1)}
    blue_result, red_result = build_result(blue_members, red_members, scores)
    return blue_result, red_result
    # members = []
    # for member in blue_orig:
    #     role = blue_orig[member]["role"]
    #     matchup_score = blue_orig[member]["totalScore"]
    #     char_data = {
    #         "name": member,
    #         "role": role,
    #         "score": matchup_score
    #     }
    #     char = Character(char_data)
    #     new_score = matchup_score
    #     new_member = member
    #     replacement_member = replacements["Replacements"][member]["replacement"]
    #     if replacement_member:
    #         new_score = replacements["Replacements"][member]["replacement_score"]
    #         new_member = replacement_member
    #     new_char_data = {
    #         "replacement": new_member,
    #         "original": member,
    #         "new_score": new_score,
    #         "orig_score": matchup_score
    #     }
    #     sugg = Suggestion(new_char_data)
    #     members.append(TeamMember(char, sugg))
def update_suggestion_scores(team_result, update):
    for i in range(1, 7):  # assuming team has 6 members
        member = getattr(team_result, str(i), None)
        name = member.character.name
        new_score = update["Red"][name]["totalScore"]
        member.suggestion.new_score = new_score
    return team_result
    
def get_char_list(team_result, rd,result):
    listi = []
    for i in range(1, 7):  # assuming team has 6 members
        member = getattr(team_result, str(i), None)
        if member:
            name = member.character.name
            print(f"Debug: {name}")
            listi.append(name)
        else:
            print("Member Slot Empty. Skipping")
            continue
    print(f"List of Alt Blue : {listi}")
    dicti = homemade_scoring(rd, listi,False)
    for i in range(1, 7):  # assuming team has 6 members
        member = getattr(result, str(i), None)
        if member:
            name = member.character.name
            new_score = dicti["Red"][name]["totalScore"]
            member.suggestion.alt_score = new_score
        else:
            print("Alt Suggestion Slot Empty. Skipping")
            continue
            
       
    return result,dicti
 
def blue_alt_score(team, dicti, tots):
    hps = dicti["Totals"]["BlueTeam"]["hps_total"]
    dps = dicti["Totals"]["BlueTeam"]["dps_total"]
    health = dicti["Totals"]["BlueTeam"]["health_total"]
    ent = {"dps": dps, "hps": hps, "health": health}
    tots["Blue"]["3"] = ent
    for i in range(1, 7):  # assuming team has 6 members
        member = getattr(team, str(i), None)
        if (
        member is None
    or member.alt_suggestion is None
    or member.alt_suggestion.replacement is None
    or not member.suggestion
):
            continue
        
        name = member.alt_suggestion.replacement
        new = dicti["Blue"][name]["totalScore"]
        member.alt_suggestion.new_score = new
        if 6 == 4:
            name = list(dicti.keys())[5]
            new = dicti["Blue"][name]["totalScore"]
            role = dicti["Blue"][name]["role"]
            data = {"name":name,"role":role,"score":new}
            char = Character(data)
            
            
    return team, tots
 

        
        
def find_replacements(data, duelist, vanguard, strategist, blu):
    replacement_dict = {"Replacements": {}}
    blue_team = data["Blue"]
    red_team = data["Red"]
    used = []
    for member in blue_team:
        replacement_dict["Replacements"][member] = {}
        score = blue_team[member]["totalScore"]
        role = blue_team[member]["role"]
        if role == "Duelist":
            pool = duelist
        elif role == "Vanguard":
            pool = vanguard
        elif role == "Strategist":
            pool = strategist
        else:
            pool = duelist
        highest_score = 0
        replacement = None
        for sug in pool:
            sug_score = pool[sug]["totalScore"]
            if sug_score > score and sug_score > highest_score:
                if sug in used:
                    continue
                highest_score = sug_score
                replacement = sug
        print(replacement)
        if replacement:
            used.append(replacement)
        entry = {"original_score": score,"replacement": replacement, "replacement_score": highest_score}
        replacement_dict["Replacements"][member] = entry
    return replacement_dict
        
def combine_dicts(data, replacements):
    new_dict = {"Totals":{},"Blue": {}, "Red": {}}
    blue_dict = data["Blue"]
    red_dict = data["Red"]
    new_blue_list = []
    new_red_list = []
    for member in blue_dict:
        replace = member
        if member in replacements["Replacements"]:
            entry = replacements["Replacements"][member]
            replace = entry["replacement"]
            print(f"Replace: {replace}")

            new_dict["Blue"][member] = { member: {
                "score": entry["original_score"],
                "replacement": entry["replacement"],
                "replacement_score": entry["replacement_score"]
            }
            }
            if replace is None:
                replace = member
            new_blue_list.append(replace)
        else:
                new_dict["Blue"] = { member: {
                    "score": blue_dict[member]["totalScore"],
                    "replacement": None,
                    "replacement_score": None
                }
                }
                new_blue_list.append(replace)
        
    for member in red_dict:
        new_dict["Red"][member] = { member: {
            "score": red_dict[member]["totalScore"],
            "replacement": None,
            "replacement_score": None
        }
        }
        new_red_list.append(member)
    print(f"New Blue Team: {new_blue_list}\n\nNew Red Team: {new_red_list}")
    return new_dict, new_red_list, new_blue_list
    

red = ["Mantis", "Peni Parker", "Doctor Strange", "Squirrel Girl", "Luna Snow", "Wolverine"]
blue = ["The Thing", "Wolverine", "The Punisher", "Thor", "Luna Snow", "Ultron"]

def combine_stats(one,two):
    tots = {"Blue":{},"Red":{}}
    blue_hps_1 = one["Totals"]["BlueTeam"]["hps_total"]
    blue_dps_1 = one["Totals"]["BlueTeam"]["dps_total"]
    blue_health_1 = one["Totals"]["BlueTeam"]["health_total"]
    blue_hps_2 = two["Totals"]["BlueTeam"]["hps_total"]
    blue_dps_2 = two["Totals"]["BlueTeam"]["dps_total"]
    blue_health_2 = two["Totals"]["BlueTeam"]["health_total"]
    red_hps_1 = one["Totals"]["RedTeam"]["hps_total"]
    red_dps_1 = one["Totals"]["RedTeam"]["dps_total"]
    red_health_1 = one["Totals"]["RedTeam"]["health_total"]
    ent = {"dps": blue_dps_1, "hps": blue_hps_1, "health": blue_health_1}
    tots["Blue"]["1"]= ent
    ent = {"dps": blue_dps_2, "hps": blue_hps_2, "health": blue_health_2}
    tots["Blue"]["2"]= ent
    ent = {"dps": red_dps_1, "hps": red_hps_1, "health": red_health_1}
    tots["Red"]["1"]= ent
    return tots
    
    
#____________________________________________________________________________________________________________________________________#
###########################################________________________######################________________#############################
    
def run_counter_logic(blue, red, replacements=None):
    teamup_dict = {}
    score_dict, unused = initial_scoring(red, blue, True)

    score_dict, teamup_dict = check_teamups(score_dict, "Blue", teamup_dict)
    score_dict, teamup_dict = check_teamups(score_dict, "Red", teamup_dict)
    score_dict, teamup_dict = check_teamup_new(score_dict, "Suggestions", teamup_dict)
    save_json('-scores1.json', score_dict)
    score_dict, red_totals = finialize_redvsblue_scores(score_dict)
    save_json('-scores2.json', score_dict)
    #score_dict = weigh_scores(["Blue","Red"], score_dict)
    #score_dict = copy_stats("BlueTeam","New_BlueTeam", score_dict)
    
    #score_dict = copy_role_avg("Blue","Suggestions", score_dict)
    #score_dict = score_suggestion_stats("Suggestions",score_dict,"New_Blue")
    #score_dict = weigh_scores(["New","Red"], score_dict)
    score_dict, duelist, vanguard, strategist = sort_end_results(score_dict)

    score_dict, slots = find_slots(score_dict, "New_Blue", unused,duelist, vanguard, strategist,blue)
    save_json('-slots.json', slots)
    
    score_dict, best_team, best_total = find_best_team(score_dict, slots, "New_Blue", red_totals)
    
    save_json('-bestteam.json', best_team)
    save_json('-besttotal.json', best_total)
    score_dict = create_new_team(best_team, best_total, score_dict, "New_Blue")
    alt = run_simple_counter_logic(blue,red, True)
    data = load_matchup_json()
    score_dict = score_counters(alt, red, "Alt", data, score_dict)
    score_dict, teamup_dict = check_teamups(score_dict, "Alt", teamup_dict)
    score_dict, alt_totals = finialize_alt_scores(score_dict)
    score_dict = align_alt_generate_role_dif(score_dict, "Blue", "Alt")
    score_dict = finialize_red_scores(score_dict)
    save_json('-scores.json', score_dict)
    t = load_teamups()
    teams = build_new_classes(score_dict,t)
    return teams
    if config.USE_TEAMUP_SCORING:
        score_dict, teamup_dict = check_teamups(score_dict, "New_Blue", teamup_dict)
    #save_json("Score_Dictnewteam.json", score_dict)
    alt = run_simple_counter_logic(blue,red, True)
    data = load_matchup_json()
    score_dict = score_counters(alt, red, "Alt", data, score_dict)
    score_dict = copy_stats("BlueTeam","AltTeam", score_dict)
    score_dict = align_alt_generate_role_dif(score_dict, "Blue", "Alt")
    score_dict = score_alt_stats("Alt",score_dict)
    #save_json("Score_Dict1.json", score_dict)
    score_dict = finialize_score_totals(score_dict,data,alt,red)
    save_json("Final_Scores.json", score_dict)
    teams = build_new_classes(score_dict)
    return teams
    #blue_result, red_result, new_blue_result = create_class_objects_2(score_dict)
    score_dict, duelist, vanguard, strategist = sort_end_results(score_dict)
    replacements = find_replacements(score_dict, duelist, vanguard, strategist, blue)
    new_dict,new_red, new_blue = combine_dicts(score_dict,replacements)
    new_score_dict = homemade_scoring(new_red, new_blue, False)
    #print(new_score_dict)
   
    save_json("new_score_dict.json", new_score_dict)
    blue_result, red_result = create_class_objects_1(score_dict,new_score_dict,replacements)
    red_result = update_suggestion_scores(red_result, new_score_dict)
    print_team_result_details(red_result)
    tots12 = combine_stats(score_dict, new_score_dict)
    return blue_result, red_result,tots12

def create_new_team(team_data, total_data, data, new_team_name):
    total_name = new_team_name + "Team"
    for char in team_data:
        char_data = team_data[char]
        score = getCounterScore(char_data)
        char_data["totalScore"] = score
    data["Totals"][total_name] = total_data
    data[new_team_name] = team_data
    return data


def load_teamups():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, "teamups2.json")
    with open(matchup_path, encoding="utf-8") as f:
        data = json.load(f)
    return data

def add_teamup_data(data,team,teamup_data):
    team_data = data[team]

    for team_member in team_data:
        key = {}
        sec_key = {}
        for anchor_char in teamup_data["TeamUps"]:
            if team_member == anchor_char:
                score = teamup_data["TeamUps"][anchor_char]['score']
                for secondary in teamup_data["TeamUps"][anchor_char]['characters']:
                    sec_key[secondary] = score
            else:
                for secondary in teamup_data["TeamUps"][anchor_char]['characters']:
                    if secondary == team_member:
                        score = teamup_data["TeamUps"][anchor_char]['characters'][secondary]
                        sec_key[anchor_char] = score
        team_data[team_member]['teamups'] = sec_key
    return data


def check_teamups(data, team, team_up_dict):
    t = load_teamups()
    data = add_teamup_data(data,team,t)
    
    team_up_dict[team] = {}
    for char in data[team]:
            char_data=data[team][char]
            
            subkey = {}
            for team_up in char_data['teamups']:
                active_score = 0
                key = {}
                if team_up is None:
                    break
                if team_up in data[team]:
                    team_up_score = data[team][team_up]['teamups'][char]
                    char_score = char_data['teamups'][team_up]
                    
                    subkey[team_up] =char_score
                    active_score += char_score
                    
                    #subkey[char] = key
                elif team_up in data["Suggestions"]:
                    print("")
            team_up_dict[team][char] = subkey
            char_data['teamupScore'] = active_score
    return data,team_up_dict

def check_teamup_new(data, team, team_up_dict):
    t = load_teamups()
    data = add_teamup_data(data,team,t)
    
    return data,team_up_dict
                
                    
                    
            
            
            

def build_new_classes(data,t):

    def find_teamup_name(char1, char2):
        for anchor in t["TeamUps"]:
            if char1 == anchor and char2 in t["TeamUps"][anchor]["characters"]:
                return t["TeamUps"][anchor]["teamup"]
            elif char2 == anchor and char1 in t["TeamUps"][anchor]["characters"]:
                return t["TeamUps"][anchor]["teamup"]
        return False
    teams = []
    for team in ["Blue", "New_Blue", "Alt", "Red"]:
        team_data = data[team]
        flag = (team == "Red")

        hero_objs = {}
        hero_list = []  # <--- Track Hero objects in order
        teamup_ids = {}
        teamup_counter = 1

        # First pass: create Hero objects
        for name, char_data in team_data.items():
            hero = Hero(char_data, name, flag)
            hero.teamup_flags = []
            hero_objs[name] = hero
            hero_list.append(hero)  # <--- Append to list
        teamup_name_to_id = {}

        # Second pass: assign the SAME tid to all participants of the same named team-up
        for anchor_name, anchor_hero in hero_objs.items():
            spec = t["TeamUps"].get(anchor_name)
            if not spec:
                continue

            teamup_name = spec["teamup"]
            # Which secondaries are actually present on this team?
            present_secondaries = [
                sec for sec in spec.get("characters", {}).keys()
                if sec in hero_objs and sec != anchor_name
            ]
            if not present_secondaries:
                continue

            # get or create a tid for this teamup NAME
            tid = teamup_name_to_id.get(teamup_name)
            if tid is None:
                tid = teamup_counter
                teamup_counter += 1
                teamup_name_to_id[teamup_name] = tid

            # ensure lists exist
            if not hasattr(anchor_hero, "teamup_names"):
                anchor_hero.teamup_names = []
            if not hasattr(anchor_hero, "teamup_flags"):
                anchor_hero.teamup_flags = []

            # add ONE icon entry to the anchor for this teamup name
            if (tid, teamup_name) not in anchor_hero.teamup_names:
                anchor_hero.teamup_names.append((tid, teamup_name))

            # for each present secondary: add same tid + name, avoid duplicates
            for sec_name in present_secondaries:
                sec_hero = hero_objs[sec_name]
                if not hasattr(sec_hero, "teamup_names"):
                    sec_hero.teamup_names = []
                if not hasattr(sec_hero, "teamup_flags"):
                    sec_hero.teamup_flags = []

                # optional: keep a flag pointing back to the anchor for UI/debug
                if (tid, anchor_name) not in sec_hero.teamup_flags:
                    sec_hero.teamup_flags.append((tid, anchor_name))

                # SAME icon tuple for the secondary
                if (tid, teamup_name) not in sec_hero.teamup_names:
                    sec_hero.teamup_names.append((tid, teamup_name))
        # # Second pass: find active teamups (process each unordered pair once)
        # for name, hero in hero_objs.items():
        #     teamups = team_data[name].get("teamups", {})
        #     for teammate in teamups:
        #         if teammate == name or teammate not in hero_objs:
        #             continue

        #         # Only handle the pair when `name` is the lexicographic minimum
        #         if name < teammate:
        #             pair = (name, teammate)
        #             if pair not in teamup_ids:
        #                 teamup_ids[pair] = teamup_counter
        #                 teamup_counter += 1

        #             tid = teamup_ids[pair]
        #             # append only once per side
        #             hero_objs[name].teamup_flags.append((tid, teammate))
        #             hero_objs[teammate].teamup_flags.append((tid, name))
        #             teamup_name = find_teamup_name(name, teammate)
        #             if teamup_name:
        #                 hero_objs[name].teamup_names.append((tid,teamup_name))
        #                 hero_objs[teammate].teamup_names.append((tid,teamup_name))
                    
                        

        # Create team using the list of Hero instances
        teamtotal = team + "Team"
        totals = data["Totals"][teamtotal]
        team_obj = Team(hero_list, totals, flag)  # <--- Use list instead of dict
        teams.append(team_obj)

    return teams
    
                    
                
    #         heroclass = Hero(char_data,char,flag)
    #         heroes.append(heroclass)
    #     teamtotal = team + "Team"
    #     totals = data["Totals"][teamtotal]
    #     team = Team(heroes,totals,flag)
    #     teams.append(team)
    # return teams
        
    

def finialize_score_totals(data,json,alt,red):
    teams = ["New_Blue","Alt"]
    
    newblue = []
    for char in data['New_Blue']:
        newblue.append(char)

    data = score_red_vs_new(red,newblue,"Red",json,data,2)
    data = get_multipliers("Red","New_Blue",data, True)
    data = weigh_scores_red(["Red"],data,2)
    data = score_red_vs_new(red,alt,"Red",json,data,3)
    data = get_multipliers("Red","Alt",data, True)
    data = weigh_scores_red(["Red"],data,3)
    data = total_every_team(data)

    return data

def total_every_team(data):
    teams = ["Blue","New_Blue","Alt","Red"]
    for team in teams:
        teamtotal = team + "Team"
        total = 0
        total2 = 0
        total3 = 0
        
        for char in data[team]:
            score = data[team][char]["totalScore"]
            total += score
            if team == "Red":
                score = data[team][char]["totalScore_2"]
                total2 += score
                score = data[team][char]["totalScore_3"]
                total3 += score
        data['Totals'][teamtotal]["totalScore"] = round(total,1)
        if team == "Red":
            data['Totals'][teamtotal]["totalScore_2"] = round(total2,1)
            data['Totals'][teamtotal]["totalScore_3"] = round(total3,1)
    return data



def get_multipliers(team1,team2,dict,flag=False):
    data = copy.deepcopy(dict)
    def subfunc(blue_stat, red_stat):
        if blue_stat == 0:
            blue_stat = red_stat
        div = red_stat**2 / blue_stat**2

        return round(min(div, 4), 2)
    
    

    teamteam1 = team1 + "Team"
    teamteam2 = team2 + "Team"
    base_weights = {"dps": 0.15, "hps": 0.15, "health": 0.15}
    multipliers = {
        stat: subfunc(data["Totals"][teamteam1][stat+"_total"], data["Totals"][teamteam2][stat+"_total"])
        for stat in base_weights
}
    dict["Totals"][teamteam1]["multipliers"] = multipliers
    if not flag:
        multipliers = {
            stat: subfunc(data["Totals"][teamteam2][stat+"_total"], data["Totals"][teamteam1][stat+"_total"])
            for stat in base_weights
    }
        dict["Totals"][teamteam2]["multipliers"] = multipliers

    return dict

def weigh_scores_red(teams,dict,num):
    for team in teams:
        teamteam = team + "Team"
        if team == "New":
            team = "Suggestions"
        multipliers = copy.deepcopy(dict["Totals"][teamteam]["multipliers"])
        for char in dict[team]:
            char_data = dict[team][char]
            score = char_data["dps_score"]
            if score < -50:
                char_data["dps_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["dps"])), 1)
            else:
                char_data["dps_weighted"] = round(char_data["dps_score"] * multipliers["dps"], 1)
            score = char_data["hps_score"]
            if score <-100:
                char_data["hps_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["hps"])), 1)
            else:
                char_data["hps_weighted"] = round(char_data["hps_score"] * multipliers["hps"], 1)
            score = char_data["health_score"]
            if score < -100:
                char_data["health_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["health"])), 1)
            else:
                char_data["health_weighted"] = round(char_data["health_score"] * multipliers["health"], 1)
            num = str(num)
            char_data[f"totalScore_{num}"] = round(
                (char_data[f"CounterCatScore_{num}"] * 1) +
                (char_data["dps_weighted"] * 0.15) +
                (char_data["hps_weighted"] * 0.15) +
                (char_data["health_weighted"] * 0.15), 1
            )
    return dict
        
def weigh_scores(teams,dict):
    for team in teams:
        teamteam = team + "Team"
        if team == "New":
            team = "Suggestions"
        multipliers = copy.deepcopy(dict["Totals"][teamteam]["multipliers"])
        for char in dict[team]:
            char_data = dict[team][char]
            score = char_data["dps_score"]
            if score < -50:
                char_data["dps_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["dps"])), 1)
            else:
                char_data["dps_weighted"] = round(char_data["dps_score"] * multipliers["dps"], 1)
            score = char_data["hps_score"]
            if score <-100:
                char_data["hps_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["hps"])), 1)
            else:
                char_data["hps_weighted"] = round(char_data["hps_score"] * multipliers["hps"], 1)
            score = char_data["health_score"]
            if score < -100:
                char_data["health_weighted"] = round(score - (abs(score) - (abs(score) * multipliers["health"])), 1)
            else:
                char_data["health_weighted"] = round(char_data["health_score"] * multipliers["health"], 1)
            char_data["totalScore"] = round(
                (char_data["CounterCatScore"] * 1) +
                (char_data["teamupScore"] * 0.5) +
                (char_data["dps_weighted"] * 0.15) +
                (char_data["hps_weighted"] * 0.15) +
                (char_data["health_weighted"] * 0.15), 1
            )
    return dict


    
    #NEWWW____________________________________

def load_matchup_json():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, config.MATCHUP)
    with open(matchup_path, encoding="utf-8") as f:
        data = json.load(f)
    return data

def initial_scoring(red, blue, flag):
    score_dict = {"Totals": {"BlueTeam":{},"RedTeam":{},"New_BlueTeam":{},"AltTeam":{}},"Blue": {}, "Red": {}, "New_Blue":{},"Alt":{},"Suggestions": {}}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, config.MATCHUP)

    character_pool = load_characters(matchup_path)
    with open(matchup_path, encoding="utf-8") as f:
        data = json.load(f)

    unused = [item for item in character_pool]

    score_dict = score_counters(blue, red, "Blue", data, score_dict)
    score_dict = score_counters(red, blue, "Red", data, score_dict)
    score_dict = score_counters(unused, red, "Suggestions", data, score_dict)
    return score_dict, unused
    

    return score_dict

def score_suggestion_stats(team, data,new_team):
    def stat_score(val, avg):
            if val == 0:
                return 0
            return round(max(-3, min(3, (2*(val - avg)) / avg)), 1)
    items = ["dps_role_avg","hps_role_avg","health_role_avg"]
    teamtotal = new_team + "Team"
    for char in data[team]:
        data[team][char]["Multipliers"] = {}
        for item in items:
            type, to, too = item.split("_")
            scorekey = type + "_score"
            stat = data[team][char][type]

            role = data[team][char]["role"]
            avg = data["Totals"][teamtotal][role][type]
            data[team][char][item] = avg
            score = stat_score(stat, avg)
            data[team][char][scorekey] = score
            type_weigh = type + "_weighted"
            if score < -100:
                data[team][char][type_weigh] = round(score - (abs(score) - abs(score * data["Totals"][teamtotal]["multipliers"][type])),1)
                

            else:
                data[team][char][type_weigh] = round(score * data["Totals"][teamtotal]["multipliers"][type],1)
                data[team][char]["Multipliers"][type] = data["Totals"][teamtotal]["multipliers"][type]

    return data
        
    return score_dict
def align_alt_generate_role_dif(data, team1, team2):
    def sort_by_role(role_order):
        # assume `data` is your parsed JSON (a dict)
        alt = data[team2]

        sorted_names = sorted(
            alt,
            key=lambda k: role_order.index(alt[k]["role"])
        )
        data["alt"] = {name: alt[name] for name in sorted_names}
        #duelist    = {k:v for k,v in sug.items() if v.get("role") == "Duelist"}
        #vanguard   = {k:v for k,v in sug.items() if v.get("role") == "Vanguard"}
        #strategist = {k:v for k,v in sug.items() if v.get("role") == "Strategist"}
        return data
    alt = copy.deepcopy(data[team2])
    team1_total = team1 + "Team"
    team2_total = team2 + "Team"
    match_team = data[team1]
    order = []
    for char in match_team:
        role = match_team[char]["role"]
        order.append(role)
    used = []
    new_alt = {}
    for blue_role in order:
        flag = False
        for char in alt:
            role = alt[char]["role"]
            if role == blue_role and char not in used:
                used.append(char)
                new_alt[char] = alt[char]
                flag = True
                break
        if not flag:
            for char in alt:
                if char not in used:
                    used.append(char)
                    new_alt[char] = alt[char]
    
    data["Alt"] = new_alt      
    #data = sort_by_role(order)
    return data




def score_alt_stats(team, data):
    blue_team = data["Blue"]
    def update_stats_alt():
        strings = ["dps", "hps", "health"]
        for stat in strings:
            stat_total = stat + "_total"
            stat_change = data[team][char][stat] - blue_team[member][stat]
            #Change Stat Total
            data["Totals"][teamtotal][stat_total] = data["Totals"][teamtotal][stat_total] + stat_change
            #Change Role Stat Avg
            count = data["Totals"][teamtotal][role]["count"]
            roleaverage = ((data["Totals"][teamtotal][role][stat]*count) + stat_change) / count
            data["Totals"][teamtotal][role][stat] = roleaverage
            stat_avg = stat + "_role_avg"
            
    def stat_score(val, avg):
            
            if val == 0:
                return 0
            return round(max(-3, min(3, (2*(val - avg)) / avg)), 1)
    items = ["dps_role_avg","hps_role_avg","health_role_avg"]
    teamtotal = team + "Team"
    done = []
    for member in blue_team:
        for char in data[team]:
            if char in done:
                continue
            data[team][char]["Multipliers"] = {}
            for item in items:
                type, to, too = item.split("_")
                scorekey = type + "_score"
                stat = data[team][char][type]

                role = data[team][char]["role"]
                avg = data["Totals"][teamtotal][role][type]
                data[team][char][item] = avg
                score = stat_score(stat, avg)
                data[team][char][scorekey] = score
                type_weigh = type + "_weighted"
                if score < -100:
                    data[team][char][type_weigh] = round(score - (abs(score) - abs(score * data["Totals"][teamtotal]["multipliers"][type])),1)
                    

                else:
                    data[team][char][type_weigh] = round(score * data["Totals"][teamtotal]["multipliers"][type],1)
                    data[team][char]["Multipliers"][type] = data["Totals"][teamtotal]["multipliers"][type]
            done.append(char)
            data[team][char]["totalScore"] = round(
                (data[team][char]["CounterCatScore"] * 1) +
                (data[team][char]["dps_weighted"] * 0.15) +
                (data[team][char]["hps_weighted"] * 0.15) +
                (data[team][char]["health_weighted"] * 0.15), 1
            )
            update_stats_alt()
            data = get_multipliers("Alt","Red",data, True)
            
            break

    return data
    




#modify this to be editing a deepcopy, then adding the changes to the original after to create keys that will not affect others in data

def getRole(char):
    role = char['role']
    return role
    
def getTotalScore(char):
    score = char['totalScore']
    return score

def getTeamUpScore(char):
    score = char['teamupScore']
    return score
    
def getCounterScore(char):
    score = char['CounterCatScore']
    return score
    
def getChar(team, name):
    char = team[name]
    return char
    
def makeCopy(dct):
    cop = copy.deepcopy(dct)
    return cop
    
def getTeam(data, team):
    x = data[team]
    return x

def getDPS(char):
    dps = char['dps']
    return dps

def getHPS(char):
    hps = char['hps']
    return hps

def getHealth(char):
    health = char['health']
    return health
    
def getTotal(data, team):
    teamtotal = team + 'Team'
    totals = copy.deepcopy(data['Totals'][teamtotal])
    return totals

def getTeamStatTotals(totals):
    dps = totals['dps_total']
    hps = totals['hps_total']
    health = totals['health_total']
    return dps, hps, health

def getTeamTotalScores(totals):
    dps = totals['dps_score']
    hps = totals['hps_score']
    health = totals['health_score']
    counter = totals['teamCounterScore']
    teamup = totals['teamupScore']
    total_score = round(sum([dps, hps, health, (teamup/2), counter]), 1)
    #total_score = round( (dps * 0.5) + (hps * 0.5) + (health * 0.5) + (teamup * 1.5) + (counter) ,1)
    #totals['totalScore'] = total_score
    return total_score

def compare_and_score_totals(team1, team2, bScoreBoth=False):
    dps1, hps1, health1 = getTeamStatTotals(team1)
    dps2, hps2, health2 = getTeamStatTotals(team2)
    def staty_score(team1_stat, team2_stat, fallback_base=50, scale=1.5):
        
        a = team1_stat
        b = team2_stat if team2_stat != 0 else fallback_base
        return round(math.log2(a / b) * scale, 4)
    
    #dps_ratio = (dps1**2 / dps2**2) - 1 if dps2 != 0 else (dps1 / 50) - 1
    #hps_ratio = (hps1**2 / hps2**2) - 1 if hps2 != 0 else (hps1 / 50) - 1
    #health_ratio = (health1**2 / health2**2) - 1 if health2 != 0 else (health1 / 50) - 1
    #dps_score = min(dps_ratio, 3)
    #hps_score = min(hps_ratio, 3)
    #health_score = min(health_ratio, 3)
    dps_score = staty_score(dps1, dps2)
    hps_score = staty_score(hps1, hps2)
    health_score = staty_score(health1, health2)
    team1['dps_score'] = round(dps_score, 1)
    team1['hps_score'] = round(hps_score, 1)
    team1['health_score'] = round(health_score, 1)

    if bScoreBoth:
        dps_ratio = (dps2 / dps1) - 1 if dps1 != 0 else (dps2 / 50) - 1
        hps_ratio = (hps2 / hps1) - 1 if hps1 != 0 else (hps2 / 50) - 1
        health_ratio = (health2 / health1) - 1 if health1 != 0 else (health2 / 50) - 1
        dps_score = min(dps_ratio, 1)
        hps_score = min(hps_ratio, 1)
        health_score = min(health_ratio, 1)
        team2['dps_score'] = round(dps_score, 1)
        team2['hps_score'] = round(hps_score, 1)
        team2['health_score'] = round(health_score, 1)

def total_team_score(totals):
    total_score = getTeamTotalScores(totals)
    totals['totalScore'] = total_score
    return total_score

def finialize_alt_scores(data):
    alt_team = data["Alt"]
    alt_totals = scoreteam(alt_team)
    red_totals = data["Totals"]["RedTeam"]
    compare_and_score_totals(alt_totals, red_totals, False)
    score = total_team_score(alt_totals)
    data["Totals"]["AltTeam"] = alt_totals
    return data, alt_totals

def finialize_redvsblue_scores(data):
    blue_team = data["Blue"]
    red_team = data["Red"]
    red_totals = scoreteam(red_team)
    
    blue_totals = scoreteam(blue_team)
    
    
    compare_and_score_totals(blue_totals, red_totals, True)
    score = total_team_score(blue_totals)
    score = total_team_score(red_totals)
    data["Totals"]["RedTeam"] = red_totals
    data["Totals"]["BlueTeam"] = blue_totals
    return data, red_totals

def scoreTeamTeamups(team):
    
    for char in team:
            char_data=team[char]
            
            subkey = {}
            for team_up in char_data['teamups']:
                active_score = 0
                key = {}
                if team_up is None:
                    break
                if team_up in team:
                    team_up_score = team[team_up]['teamups'][char]
                    char_score = char_data['teamups'][team_up]
                    
                    subkey[team_up] =char_score
                    active_score += char_score
                    
            
            char_data['teamupScore'] = active_score
    return team



def scoreteam(team, vs=False ):
    teamscore = 0
    teampup_score = 0
    dps_total = 0
    hps_total = 0
    health_total = 0
    totals = {}
    
    for char in team:
        char_data = team[char]
        dps_total += getDPS(char_data)
        hps_total += getHPS(char_data)
        health_total += getHealth(char_data)
        teampup_score += getTeamUpScore(char_data)

        #score = char_data["CounterCatScore"]
        teamscore += getCounterScore(char_data)

    totals['dps_total'] = round(dps_total,1)
    totals['hps_total'] = round(hps_total,1)
    totals['health_total'] = round(health_total,1)
    totals['teamCounterScore'] = round(teamscore, 1)
    totals['teamupScore'] = round(teampup_score,1)

    
    if vs:
        enemy_dps, enemy_hps, enemy_health = getTeamStatTotals(vs)

    


    return totals

def find_best_team(score_dict, slots, red_team, red_total):
    import itertools
    t = load_teamups()
    #slot1, slot2, slot3, slot4, slot5, slot6 = slots.values()
    highest_score = float('-inf')
    best_team = {}
    team = {}
    best_totals = {}
    totals = {}
    # Generate all combinations (Cartesian product)
    slot_lists = [
    [char for char in slots[str(i)] if char is not None]
    for i in range(1, 7)
]

    # 2. Optional: Skip combos with duplicate character names
    def has_duplicates(combo):
        names = [char['name'] for char in combo]
        return len(set(names)) < len(names)



    # 4. Iterate over all combinations
    highest_score = float("-inf")
    best_team = {}
    text = []
    seen_teams = set()
    for combo in itertools.product(*slot_lists):  # Up to 3^6 = 729 combos
        if has_duplicates(combo):
            continue

        team = {char['name']: char for char in combo}
        character_names = list(team.keys())
        name_combo = tuple(sorted(character_names))
        tu = {}
        if name_combo in seen_teams:
            continue  # Already evaluated this team
        seen_teams.add(name_combo)
        team = scoreTeamTeamups(team)
        
        totals = scoreteam(team)
        #da = {"Totals": {"New_BlueTeam": totals}, "Suggestions": copy.deepcopy(score_dict['Suggestions']), "New_Blue": team}
        #da, a = check_teamups(da, "New_Blue", tu)
        
        #data = add_teamup_data(data,team,t)
        compare_and_score_totals(totals, red_total, False)
        
        teamscore = total_team_score(totals)
        string = f"Team: {character_names}, Score: {teamscore:.2f}"
        text.append(string)
        #print(f"Team: {character_names}, Score: {teamscore:.2f}")

        if teamscore > highest_score:
            print(f"###---------Team: {character_names}, Score: {teamscore:.2f}------###")
            highest_score = teamscore
            best_team = copy.deepcopy(team)
            best_totals = copy.deepcopy(totals)
            save_json('-bestteam_interim.json', best_team)
            save_json('-besttotal_interim.json', best_totals)
    save_text('-allteams.txt', text)
    # 5. Output result
    print(f"Best team score: {highest_score:.2f}")
    print("Team members:")
    for name in best_team:
        print(f" - {name}")
    return score_dict,best_team, best_totals
    

def find_slots(data, new_team, unused,duelist, vanguard, strategist,bluelist):

    teamtotal = new_team + "Team"
    def update_stats_suggestions():
        strings = ["dps", "hps", "health"]
        for stat in strings:
            stat_total = stat + "_total"
            stat_change = data[new_team][replacement][stat] - blue_team[member][stat]
            #Change Stat Total
            data["Totals"][teamtotal][stat_total] = data["Totals"][teamtotal][stat_total] + stat_change
            #Change Role Stat Avg
            count = data["Totals"][teamtotal][role]["count"]
            roleaverage = ((data["Totals"][teamtotal][role][stat]*count) + stat_change) / count
            data["Totals"][teamtotal][role][stat] = roleaverage
            stat_avg = stat + "_role_avg"
            for sug in pool:
                pool[sug][stat_avg] = roleaverage

    replacement_dict = {"Replacements": {}}
    slot_dict = {'1':[],'2':[],'3':[],'4':[],'5':[],'6':[]}

    blue_team = data["Blue"]

    red_team = data["Red"]

    used = []
    

    dcount = 0
    vcount = 0
    scount = 0
    slot = 1
    
    for member in blue_team:
        dictionary = []
        char = getChar(blue_team,member)
        bluelist.remove(member)
        replacement_dict["Replacements"][member] = {}
        score = getCounterScore(char)
        role = getRole(char)
        if role == "Duelist":
            pool = duelist            
        elif role == "Vanguard":
            pool = vanguard
        elif role == "Strategist":
            pool = strategist
        else:
            pool = duelist

        pool10 = list(pool.keys())[:12]
        for sug in pool10:
            sug_char = pool[sug]
            sug_char['name'] = sug
            dictionary.append(sug_char)

        
        slot_dict[str(slot)] = copy.deepcopy(dictionary)
        slot += 1
        continue

        highest_score = -500
        second_score = -500
        third_score = -500
        replacement = None
        replacement2 = None
        replacement3 = None
        name1 = None
        name2 = None
        name3 = None
        
        for sug in pool:
            sug_char = pool[sug]
            name = sug
            sug_char['name'] = name
            #sug_score = round((pool[sug]["CounterCatScore"]*1) + (pool[sug]["dps_weighted"]*0.15) + (pool[sug]["hps_weighted"]*0.15) + (pool[sug]["health_weighted"]*0.15),1)
            sug_score = getCounterScore(sug_char)
            if sug_score > score and sug_score > highest_score:
                
                    
                if sug in used or sug in bluelist:
                    continue
                
                highest_score = sug_score
                
                if replacement:
                    if replacement2:
                        
                        replacement3 = copy.deepcopy(replacement2)
                        name3 = name2
                    replacement2 = copy.deepcopy(replacement)
                    name2= name1
                replacement = copy.deepcopy(sug_char)
                name1 = name
            elif sug_score > score and sug_score > second_score:
                if sug in used or sug in bluelist:
                    continue
                second_score = sug_score
                if replacement2:
                    replacement3 = copy.deepcopy(replacement2)
                    name3 = name2
                replacement2 = copy.deepcopy(sug_char)
                name2= name
            elif sug_score > score and sug_score > third_score:
                if sug in used or sug in bluelist:
                    continue
                third_score = sug_score
                replacement3 = copy.deepcopy(sug_char)
                name3= name
                    
                    
                
        
        if replacement:
            
            used.append(name1)
            copteam = "Suggestions"
        if replacement2:
            used.append(name2)
        if replacement3:(name3)
        if replacement is None:
            replacement = copy.deepcopy(char)
            replacement['name'] = member
            copteam = "Blue"
            highest_score = score
            used.append(member)
            
        dictionary = [replacement,replacement2,replacement3]
        slot_dict[str(slot)] = copy.deepcopy(dictionary)
        slot += 1
        #cop = copy.deepcopy(data[copteam][replacement])
        #data[new_team][replacement] = cop
        
       # data[new_team][replacement]["totalScore"] = highest_score
       # print(f"{replacement}'s Score: {highest_score}")
        #update_stats_suggestions()

        
        
       # print(data[new_team][replacement]["dps_role_avg"])
   #     data = get_multipliers("New_Blue","Red",data, True)

     #   data = score_suggestion_stats("Suggestions",data,new_team)

        #data, duelist, vanguard, strategist = sort_end_results(data,True)

    
    return data,slot_dict


def copy_stats(teamfrom, teamto, score_dict):
    teamfrom_stats = copy.deepcopy(score_dict["Totals"][teamfrom])
    
    score_dict["Totals"][teamto] = teamfrom_stats
    return score_dict



def role_average_stats(stats,char,data):
    char_data = data[char]
    role = char_data.get("role")

    dps = char_data.get("dps", 0)
    hps = char_data.get("hps", 0)
    health = char_data.get("health", 0)

    stats["dps"] += dps
    stats["hps"] += hps
    stats["health"] += health

    if role == "Duelist":
        stats["roles"]["Duelist"]["dps_total"] += dps
        stats["roles"]["Duelist"]["dps_count"] += 1
        stats["roles"]["Duelist"]["hps_total"] += hps
        stats["roles"]["Duelist"]["hps_count"] += 1
        stats["roles"]["Duelist"]["health_total"] += health
        stats["roles"]["Duelist"]["health_count"] += 1

    elif role == "Strategist":
        if 1 ==1:
            stats["roles"]["Strategist"]["hps_total"] += hps
            stats["roles"]["Strategist"]["hps_count"] += 1
            stats["roles"]["Strategist"]["dps_total"] += dps
            stats["roles"]["Strategist"]["dps_count"] += 1
            stats["roles"]["Strategist"]["health_total"] += health
            stats["roles"]["Strategist"]["health_count"] += 1

    elif role == "Vanguard":
        if 1==1:
            stats["roles"]["Vanguard"]["dps_total"] += dps
            stats["roles"]["Vanguard"]["dps_count"] += 1
            stats["roles"]["Vanguard"]["hps_total"] += hps
            stats["roles"]["Vanguard"]["hps_count"] += 1
            stats["roles"]["Vanguard"]["health_total"] += health
            stats["roles"]["Vanguard"]["health_count"] += 1
    return stats
    
def role_avg(team1,stats):
    team1_stats = stats
    avg_team1_stats = {
    stat: team1_stats[stat] / len(team1) if team1 else 1
    for stat in ["dps", "hps", "health"]
}

    role_avg_team1 = {
    "Duelist": {},
    "Vanguard": {},
    "Strategist": {}
}

    for role, stat_key in [("Duelist", "dps"),("Duelist","hps"), ("Duelist", "health"),
                        ("Vanguard", "health"), ("Vanguard", "dps"),("Vanguard", "hps"),
                        ("Strategist", "dps"),("Strategist","hps"), ("Strategist", "health")]:
        stat_total_key = f"{stat_key}_total"
        stat_count_key = f"{stat_key}_count"

        role_info = team1_stats["roles"].get(role, {})

        if role_info.get(stat_count_key, 0) > 0:
            avg = role_info[stat_total_key] / role_info[stat_count_key]
        else:
            avg = copy.deepcopy(avg_team1_stats[stat_key])  # fallback to team-wide average

        role_avg_team1[role][stat_key] = avg
        role_avg_team1[role]["count"] = role_info[stat_count_key]
    return role_avg_team1
    
def score_stats_1(teams,data):
    
    def stat_score(val, avg):
            if val == 0:
                return 0
            return round(max(-3, min(3, (2*(val - avg)) / avg)), 1)
    items = ["dps_role_avg","hps_role_avg","health_role_avg"]
    for team in teams:
        for char in data[team]:
            for item in items:
                type, to, too = item.split("_")
                scorekey = type + "_score"
                stat = data[team][char][type]
                avg = data[team][char][item]
                score = stat_score(stat, avg)
                data[team][char][scorekey] = score
    return data
                
                
            
            
def team_stats(teams,data):
    
    
    for team in teams:
        dps_total = 0
        hps_total = 0
        health_total = 0
        stats = {
        "dps": 0, "hps": 0, "health": 0,
        "roles": {
            "Duelist": {
                "dps_total": 0, "dps_count": 0,
                "health_total": 0, "health_count": 0,
                "hps_total": 0, "hps_count": 0
            },
            "Strategist": {
                "dps_total": 0, "dps_count": 0,
                "health_total": 0, "health_count": 0,
                "hps_total": 0, "hps_count": 0
            },
            "Vanguard": {
                "dps_total": 0, "dps_count": 0,
                "health_total": 0, "health_count": 0,
                "hps_total": 0, "hps_count": 0
            }
        }
    }
        for char in data[team]:
            dat = copy.deepcopy(data[team])
            stats = role_average_stats(stats,char,dat)
        team1 = dat.keys()
        avg_stats = role_avg(team1, stats)
        print(stats,avg_stats)
        teamteam = team + "Team"
        data["Totals"][teamteam]["dps_total"] = stats["dps"]
        data["Totals"][teamteam]["hps_total"] = stats["hps"]
        data["Totals"][teamteam]["health_total"] = stats["health"]
        for char in data[team]:
            role = data[team][char]["role"]
            for type in ["dps_role_avg","hps_role_avg","health_role_avg"]:
                strip, ss, sss = type.split("_")
                data[team][char][type] = avg_stats[role][strip]
                data["Totals"][teamteam][role] = copy.deepcopy(avg_stats[role])
            
    
    return data
            
def getListChar(team):
    lisst =[]
    for char in team:
        lisst.append(char)         
    return lisst

def compare_and_score_red_stat_totals(team1, team2, num):

    dps1, hps1, health1 = getTeamStatTotals(team1)
    dps2, hps2, health2 = getTeamStatTotals(team2)
    def staty_score(team1_stat, team2_stat, fallback_base=50, scale=1.5):
        
        a = team1_stat
        b = team2_stat if team2_stat != 0 else fallback_base
        return round(math.log2(a / b) * scale, 4)
    
    #dps_ratio = (dps1**2 / dps2**2) - 1 if dps2 != 0 else (dps1 / 50) - 1
    #hps_ratio = (hps1**2 / hps2**2) - 1 if hps2 != 0 else (hps1 / 50) - 1
    #health_ratio = (health1**2 / health2**2) - 1 if health2 != 0 else (health1 / 50) - 1
    #dps_score = min(dps_ratio, 3)
    #hps_score = min(hps_ratio, 3)
    #health_score = min(health_ratio, 3)
    dps_score = staty_score(dps1, dps2)
    hps_score = staty_score(hps1, hps2)
    health_score = staty_score(health1, health2)
    team1['dps_score_' + str(num)] = round(dps_score, 1)
    team1['hps_score_' + str(num)] = round(hps_score, 1)
    team1['health_score_' + str(num)] = round(health_score, 1)
    return team1

def getRedTeamTotalScores(red, totals, num):
    total_counter_score = 0
    for char in red:
        char_data = red[char]
        counter_score = char_data['CounterCatScore_' + str(num)]
        total_counter_score += counter_score
    totals['teamCounterScore_' + str(num)] = round(total_counter_score, 1)


    dps = totals['dps_score_' + str(num)]
    hps = totals['hps_score_' + str(num)]
    health = totals['health_score_' + str(num)]
    counter = totals['teamCounterScore_' + str(num)]
    teamup = totals['teamupScore']
    total_score = round(sum([dps, hps, health, (teamup/2), counter]), 1)
    #total_score = round( (dps * 0.5) + (hps * 0.5) + (health * 0.5) + (teamup * 1.5) + (counter) ,1)
    #totals['totalScore'] = total_score
    totals['totalScore_' + str(num)] = round(total_score, 1)
    return totals
    
def finialize_red_scores(data):
    red_team = getTeam(data, "Red")
    new_blue_team = getTeam(data,'New_Blue')
    alt_team = getTeam(data,'Alt')
    json = load_matchup_json()
    red = getListChar(red_team)
    nb = getListChar(new_blue_team)
    alty = getListChar(alt_team)
    data = score_red_vs_new(red,nb,"Red",json,data,2)
    data = score_red_vs_new(red,alty, "Red",json,data,3)
    red_total = getTotal(data, "Red")
    new_blue_total = getTotal(data, "New_Blue")
    alt_total = getTotal(data, "Alt")
    red_total = compare_and_score_red_stat_totals(red_total, new_blue_total, 2)
    red_total = compare_and_score_red_stat_totals(red_total, alt_total, 3)
    red_total = getRedTeamTotalScores(red_team, red_total,2)
    red_total = getRedTeamTotalScores(red_team, red_total,3)
    data["Totals"]["RedTeam"] = red_total

    return data
#         return round(1 + (diff ) / (0.1*blue_stat),2)  # Linear scale: 10→1, 100→2
def score_red_vs_new(team1, team2, team_name, data, score_dict,num):
    #team1_stats = calculate_team_stats(team1, data)
    #if team_name == "Blue":
        #global suggestions_team1_stats,suggestions_blueteam
        #suggestions_team1_stats = team1_stats.copy()
        #suggestions_blueteam = team1
    #team2_stats = calculate_team_stats(team2, data)

    # Bypass using full unused team for averaging 
    #if team_name == "Suggestions":
        #suggestions_stats_copy = team1_stats.copy()
        #team1_stats = suggestions_team1_stats.copy()
        #unused_team = team1
        #team1 = suggestions_blueteam

    

    
    #base_weights = {"dps": 0.15, "hps": 0.15, "health": 0.15}
    #multipliers = {
        ##stat: calc_multiplier(team1_stats[stat], team2_stats[stat])
#        for stat in base_weights
#}
    

    
    
    total_counterscore = 0
    total_category_score = 0
    tally_countering = 0
    tally_countered = 0
    teamTotalScore = 0

    #if team_name == "Suggestions":
        #team1 = unused_team


    for char in team1:
        
        char_data = data[char]
        role = char_data["role"]
        category = char_data["category"]
        counterPicks = [cp["name"] for cp in char_data.get("counterPicks", [])]
        
        countering = 0
        countered = 0
        cat_pos = 0
        cat_neg = 0

        for enemy in team2:
            enemy_data = data[enemy]
            enemy_role = enemy_data["role"]
            enemy_category = enemy_data["category"]
            enemy_counters = [cp["name"] for cp in enemy_data.get("counterPicks", [])]

            score = 0
            if enemy in counterPicks:
                score -= 1
                countered += 1
            if char in enemy_counters:
                score += 1
                countering += 1

            pos, neg = get_matchup_score(category, enemy_category)
            cat_pos += pos
            cat_neg += neg

        counted = countering - countered
        total_counterscore += counted
        total_category_score += cat_pos - cat_neg
        tally_countering += countering
        tally_countered += countered



        
        cat = cat_pos - cat_neg
        totalScore = (
    (counted * 1) +
    (cat * 0.15)   
)
        score = "CounterCatScore_" + str(num)
        totalScore = round(totalScore, 1)
        teamTotalScore += totalScore
        score_dict[team_name][char][score] = totalScore
            
        
    return score_dict
            
            
        
def score_counters(team1, team2, team_name, data, score_dict):
    #team1_stats = calculate_team_stats(team1, data)
    #if team_name == "Blue":
        #global suggestions_team1_stats,suggestions_blueteam
        #suggestions_team1_stats = team1_stats.copy()
        #suggestions_blueteam = team1
    #team2_stats = calculate_team_stats(team2, data)

    # Bypass using full unused team for averaging 
    #if team_name == "Suggestions":
        #suggestions_stats_copy = team1_stats.copy()
        #team1_stats = suggestions_team1_stats.copy()
        #unused_team = team1
        #team1 = suggestions_blueteam

    

    
    #base_weights = {"dps": 0.15, "hps": 0.15, "health": 0.15}
    #multipliers = {
        ##stat: calc_multiplier(team1_stats[stat], team2_stats[stat])
#        for stat in base_weights
#}
    

    string = "red"
    if team_name == "Red":
        string = "blue"
    team_matchup = string + "_matchup"
    total_counterscore = 0
    total_category_score = 0
    tally_countering = 0
    tally_countered = 0
    teamTotalScore = 0

    #if team_name == "Suggestions":
        #team1 = unused_team


    for char in team1:
        score_dict[team_name][char] = {team_matchup: {}}
        char_data = data[char]
        role = char_data["role"]
        category = char_data["category"]
        counterPicks = [cp["name"] for cp in char_data.get("counterPicks", [])]
        
        countering = 0
        countered = 0
        cat_pos = 0
        cat_neg = 0

        for enemy in team2:
            enemy_data = data[enemy]
            enemy_role = enemy_data["role"]
            enemy_category = enemy_data["category"]
            enemy_counters = [cp["name"] for cp in enemy_data.get("counterPicks", [])]

            score = 0
            if enemy in counterPicks:
                score -= 1
                countered += 1
            if char in enemy_counters:
                score += 1
                countering += 1

            pos, neg = get_matchup_score(category, enemy_category)
            cat_pos += pos
            cat_neg += neg

            score_dict[team_name][char][team_matchup][enemy] = {
                "counter_score": score,
                "category_score": pos - neg,
                "enemy_role": enemy_role,
                "enemy_category": enemy_category
            }

        counted = countering - countered
        total_counterscore += counted
        total_category_score += cat_pos - cat_neg
        tally_countering += countering
        tally_countered += countered

        dps = char_data.get("dps", 0)
        hps = char_data.get("hps", 0)
        hp = char_data.get("health", 0)

        
        cat = cat_pos - cat_neg
        totalScore = (
    (counted * 1) +
    (cat * 0.15)   
)
        copa = copy.deepcopy(score_dict[team_name][char][team_matchup])
        totalScore = round(totalScore, 1)
        teamTotalScore += totalScore
        score_dict[team_name][char] = {
            "totalScore": None,
            "teamupScore": 0,
            "CounterCatScore": totalScore,
            "total_counter_score": counted,
            "total_category_score": cat_pos - cat_neg,
            "role": role,
            "category": category,
            "dps": dps,
            "hps": hps,
            "health": hp,
            "dps_score": None,
            "hps_score": None,
            "health_score": None,
            "dps_weighted": None,
            "hps_weighted": None,
            "health_weighted": None,
            "dps_role_avg": None,
            "hps_role_avg": None,
            "health_role_avg": None,
            team_matchup: copa
        }
    return score_dict

   
# script_dir = os.path.dirname(os.path.abspath(__file__))
# output_path = os.path.join(script_dir, "debug", "counter_output_dex2.json")
# with open(output_path, 'w', encoding='utf-8') as f:
#     json.dump(score_dict, f, indent=4, ensure_ascii=False)
# output_path2 = os.path.join(script_dir, "debug", "counter_output_dex2_replacements.json")
# with open(output_path2, 'w', encoding='utf-8') as f:
#     json.dump(replacements, f, indent=4, ensure_ascii=False)
# output_path3 = os.path.join(script_dir, "debug", "counter_output_dex2_newscore.json")
# with open(output_path3, 'w', encoding='utf-8') as f:
#     json.dump(new_score_dict, f, indent=4, ensure_ascii=False)
