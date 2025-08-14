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
        self.dps = data['dps_total']
        self.hps= data['hps_total']
        self.health = data['health_total']
        if flag:
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
        
        self.matchup_score = data["totalScore"]
        if flag:
            self.matchup_score2 = data["totalScore_2"]
            self.matchup_score3 = data["totalScore_3"]

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

def sort_end_results(data, flag = False):
        # assume `data` is your parsed JSON (a dict)
    sug = data["Suggestions"]

    # names sorted by totalScore (highest first)
    if flag:
        sorted_names = sorted(sug, key=lambda k: sug[k].get("CounterCatScore", float("-inf")), reverse=True)
    else:
        sorted_names = sorted(sug, key=lambda k: sug[k].get("totalScore", float("-inf")), reverse=True)

    # rebuild Suggestions in that order (dicts preserve insertion order in Py3.7+)
    data["Suggestions"] = {name: sug[name] for name in sorted_names}
    duelist    = {k:v for k,v in sug.items() if v.get("role") == "Duelist"}
    vanguard   = {k:v for k,v in sug.items() if v.get("role") == "Vanguard"}
    strategist = {k:v for k,v in sug.items() if v.get("role") == "Strategist"}
    return data, duelist, vanguard, strategist

def build_teams(data, replacements=None):
    members = []
    for member in data:
        role = data[member]["role"]
        matchup_score = data[member]["totalScore"]
        char_data = {
            "name": member,
            "role": role,
            "score": matchup_score
        }
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
    score_dict = team_stats(["Blue","Red"],score_dict)
    score_dict = score_stats_1(["Blue","Red"],score_dict)
    score_dict = get_multipliers("Blue","Red",score_dict)
    if config.USE_TEAMUP_SCORING:
        score_dict, teamup_dict = check_teamups(score_dict, "Blue", teamup_dict)
        score_dict, teamup_dict = check_teamups(score_dict, "Red", teamup_dict)
    score_dict = weigh_scores(["Blue","Red"], score_dict)
    score_dict = copy_stats("BlueTeam","New_BlueTeam", score_dict)
    
    #score_dict = copy_role_avg("Blue","Suggestions", score_dict)
    score_dict = score_suggestion_stats("Suggestions",score_dict,"New_Blue")
    #score_dict = weigh_scores(["New","Red"], score_dict)
    score_dict, duelist, vanguard, strategist = sort_end_results(score_dict,True)

    score_dict = find_newteam(score_dict, "New_Blue", unused,duelist, vanguard, strategist,blue)
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
    def split_team_role(team):
        vanguard = {}
        duelist = {}
        strategist = {}
        roles =["Strategist","Duelist","Vanguard"]
        for char in data[team]:
            char_data = data[team][char]
            role = char_data['role']
            if role == roles[0]:
                strategist[char] = char_data
            elif role == roles[1]:
                duelist[char] = char_data
            elif role == roles[2]:
                vanguard[char] = char_data
        return vanguard, duelist, strategist
       
    vanguard, duelist, strategist = split_team_role(team)
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
                
                    
                    
            
            
            

def build_new_classes(data):
    teams = []
    for team in ["Blue","New_Blue","Alt","Red"]:
        members = data[team]
        flag = False
        if team == "Red":
            flag = True
        heroes = []
        for char in members:
            heroclass = Hero(members[char],char,flag)
            heroes.append(heroclass)
        teamtotal = team + "Team"
        totals = data["Totals"][teamtotal]
        team = Team(heroes,totals,flag)
        teams.append(team)
    return teams
        
    

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
    
def find_newteam(data, new_team, unused,duelist, vanguard, strategist,bluelist):

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

        # dps = data[new_team][replacement]["dps"] - blue_team[member]["dps"]

        # hps = data[new_team][replacement]["hps"] - blue_team[member]["hps"]

        # health = data[new_team][replacement]["health"] - blue_team[member]["health"]

        # data["Totals"]["NewTeam"]["dps_total"] = data["Totals"]["NewTeam"]["dps_total"] + dps

        # data["Totals"]["NewTeam"]["hps_total"] = data["Totals"]["NewTeam"]["hps_total"] + hps

        # data["Totals"]["NewTeam"]["health_total"] = data["Totals"]["NewTeam"]["health_total"] + health
        # data["Totals"]["NewTeam"][role]["dps"] = data["Totals"]["NewTeam"][role]["dps"] + dps
        # data["Totals"]["NewTeam"][role]["hps"] = data["Totals"]["NewTeam"][role]["hps"] + hps
        # data["Totals"]["NewTeam"][role]["health"] = data["Totals"]["NewTeam"][role]["health"] + health
        # print(f"Dps diff {dps}/n{data[new_team][replacement]["dps_role_avg"]}")
        
        # data[new_team][replacement]["dps_role_avg"] = data["Totals"]["NewTeam"][role]["dps"] / data["Totals"]["NewTeam"][role]["count"]
        # data[new_team][replacement]["hps_role_avg"] = data["Totals"]["NewTeam"][role]["hps"] / data["Totals"]["NewTeam"][role]["count"]
        # data[new_team][replacement]["health_role_avg"] = data["Totals"]["NewTeam"][role]["health"] / data["Totals"]["NewTeam"][role]["count"]


    replacement_dict = {"Replacements": {}}

    blue_team = data["Blue"]

    red_team = data["Red"]

    used = []
    

    dcount = 0
    vcount = 0
    scount = 0
    
    for member in blue_team:
        bluelist.remove(member)
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
            sug_score = round((pool[sug]["CounterCatScore"]*1) + (pool[sug]["dps_weighted"]*0.15) + (pool[sug]["hps_weighted"]*0.15) + (pool[sug]["health_weighted"]*0.15),1)
            if sug_score > score and sug_score > highest_score:
                
                    
                if sug in used or sug in bluelist:
                    continue
                
                highest_score = sug_score
                replacement = sug
                
        
        if replacement:
            
            used.append(replacement)
            copteam = "Suggestions"
        if replacement is None:
            replacement = member
            copteam = "Blue"
            highest_score = score
            used.append(replacement)
            
        print(f"Member: {replacement}")
        
        cop = copy.deepcopy(data[copteam][replacement])
        data[new_team][replacement] = cop
        
        data[new_team][replacement]["totalScore"] = highest_score
        print(f"{replacement}'s Score: {highest_score}")
        update_stats_suggestions()

        
        
        print(data[new_team][replacement]["dps_role_avg"])
        data = get_multipliers("New_Blue","Red",data, True)

        data = score_suggestion_stats("Suggestions",data,new_team)

        #data, duelist, vanguard, strategist = sort_end_results(data,True)

    
    return data



#modify this to be editing a deepcopy, then adding the changes to the original after to create keys that will not affect others in data

def find_newtea2m(data, new_team, unused, duelist, vanguard, strategist):
    
    # Work on a deep copy so we don't touch the original until we commit
    work = copy.deepcopy(data)

    replacement_dict = {"Replacements": {}}
    blue_team = work["Blue"]
    red_team = work["Red"]
    used = []

    # make sure containers exist in the working copy
    work.setdefault(new_team, {})
    work.setdefault("Totals", {}).setdefault("NewTeam", {
        "dps_total": 0, "hps_total": 0, "health_total": 0
    })

    for member in blue_team:
        replacement_dict["Replacements"][member] = {}

        score = blue_team[member]["totalScore"]
        role  = blue_team[member]["role"]

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
            sug_score = round(
                (pool[sug]["CounterCatScore"] * 1) +
                (pool[sug]["dps_weighted"]     * 0.15) +
                (pool[sug]["hps_weighted"]     * 0.15) +
                (pool[sug]["health_weighted"]  * 0.15), 1
            )
            if sug_score > score and sug_score > highest_score:
                if sug in used:
                    continue
                highest_score = sug_score
                replacement = sug

        print(replacement)
        if not replacement:
            continue

        used.append(replacement)

        # copy the suggestion record safely
        work[new_team][replacement] = copy.deepcopy(work["Suggestions"][replacement])
        work[new_team][replacement]["totalScore"] = highest_score
        print(f"{replacement}'s Score: {highest_score}")

        # delta vs current member
        dps    = work[new_team][replacement]["dps"]    - blue_team[member]["dps"]
        hps    = work[new_team][replacement]["hps"]    - blue_team[member]["hps"]
        health = work[new_team][replacement]["health"] - blue_team[member]["health"]

        # update totals ONLY in the working copy
        work["Totals"]["NewTeam"]["dps_total"]    += dps
        work["Totals"]["NewTeam"]["hps_total"]    += hps
        work["Totals"]["NewTeam"]["health_total"] += health

        # run downstream calcs on the working copy
        work = get_multipliers("New", "Red", work, True)
        work = score_suggestion_stats("Suggestions", work)
        work, duelist, vanguard, strategist = sort_end_results(work, True)

    # ---- commit only the new stuff back to the original ----
    data.setdefault(new_team, {})
    data[new_team].update(work.get(new_team, {}))

    data.setdefault("Totals", {})
    if "NewTeam" in work.get("Totals", {}):
        data["Totals"]["NewTeam"] = work["Totals"]["NewTeam"]

    return data


# def find_newteam(data, new_team, unused,duelist, vanguard, strategist):
    

#     replacement_dict = {"Replacements": {}}
#     blue_team = data["Blue"]
#     red_team = data["Red"]
#     used = []
#     for member in blue_team:
#         replacement_dict["Replacements"][member] = {}
#         score = blue_team[member]["totalScore"]
#         role = blue_team[member]["role"]
#         if role == "Duelist":
#             pool = duelist
#         elif role == "Vanguard":
#             pool = vanguard
#         elif role == "Strategist":
#             pool = strategist
#         else:
#             pool = duelist
#         highest_score = 0
#         replacement = None
#         for sug in pool:
#             sug_score = round((pool[sug]["CounterCatScore"]*1) + (pool[sug]["dps_weighted"]*0.3) + (pool[sug]["hps_weighted"]*0.3) + (pool[sug]["health_weighted"]*0.3),1)
#             if sug_score > score and sug_score > highest_score:
#                 if sug in used:
#                     continue
#                 highest_score = sug_score
#                 replacement = sug
            
#         print(replacement)
#         if replacement:
#             used.append(replacement)
#         else:
#             continue
        
#         data[new_team][replacement] = data["Suggestions"][replacement].deepcopy()
#         data[new_team][replacement]["totalScore"] = highest_score
#         print(f"{replacement}'s Score: {highest_score}")
#         dps = data[new_team][replacement]["dps"] - blue_team[member]["dps"]
#         hps = data[new_team][replacement]["hps"] - blue_team[member]["hps"]
#         health = data[new_team][replacement]["health"] - blue_team[member]["health"]
#         data["Totals"]["NewTeam"]["dps_total"] = data["Totals"]["NewTeam"]["dps_total"] + dps
#         data["Totals"]["NewTeam"]["hps_total"] = data["Totals"]["NewTeam"]["hps_total"] + hps
#         data["Totals"]["NewTeam"]["health_total"] = data["Totals"]["NewTeam"]["health_total"] + health
#         data = get_multipliers("New","Red",data, True)
#         data = score_suggestion_stats("Suggestions",data)
#         data, duelist, vanguard, strategist = sort_end_results(data,True)

#     return data



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
            
            
    
#NEW SCORING
# def score_stats():
#     def total():
#         totalScore = (
#     (counted * 1) +
#     (cat * 0.15) +
#     (dps_score * multipliers["dps"] * 0.3) +
#     (hps_score * multipliers["hps"]*0.3) +
#     (hp_score  * multipliers["health"]*0.3)
# )
#     score_dict[team_name][char] = {
#             "totalScore": totalScore,
#             "total_counter_score": counted,
#             "total_category_score": cat_pos - cat_neg,
#             "role": role,
#             "category": category,
#             "dps": dps,
#             "hps": hps,
#             "health": hp,
#             "dps_score": dps_score,
#             "hps_score": hps_score,
#             "health_score": hp_score,
#             "dps_weighted": round(dps_score * multipliers["dps"], 1),
#             "hps_weighted": round(hps_score * multipliers["hps"], 1),
#             "health_weighted": round(hp_score * multipliers["health"], 1),
#             "dps_role_avg": dps_avg,
#             "hps_role_avg": hps_avg,
#             "health_role_avg": hp_avg,
#             "red_matchup": score_dict[team_name][char]["red_matchup"]
#         }
#     def role_avg():
#         avg_team1_stats = {
#     stat: team1_stats[stat] / len(team1) if team1 else 1
#     for stat in ["dps", "hps", "health"]
# }

#     role_avg_team1 = {
#     "Duelist": {},
#     "Vanguard": {},
#     "Strategist": {}
# }

#     for role, stat_key in [("Duelist", "dps"), ("Duelist", "health"),
#                         ("Vanguard", "health"), ("Vanguard", "dps"),
#                         ("Strategist", "dps"),("Strategist","hps")]:
#         stat_total_key = f"{stat_key}_total"
#         stat_count_key = f"{stat_key}_count"

#         role_info = team1_stats["roles"].get(role, {})

#         if role_info.get(stat_count_key, 0) > 0:
#             avg = role_info[stat_total_key] / role_info[stat_count_key]
#         else:
#             avg = avg_team1_stats[stat_key]  # fallback to team-wide average

#         role_avg_team1[role][stat_key] = avg
#     def stat_score(val, avg):
#             if val == 0:
#                 return 0
#             return round(max(-3, min(3, (2*(val - avg)) / avg)), 1)
#     def idk():
#             if role == "Strategist":
#                 print()
#             hp = 0
#             hps = 0
#             dps = 0
#             dps_avg = round(role_avg_team1[role]["dps"],2)
#             hps_avg = round(role_avg_team1[role]["hps"],2) if role == "Strategist" else 0
#             hp_avg  = round(role_avg_team1[role]["health"],2) if role != "Strategist" else hp
    
#             dps_score = stat_score(dps, dps_avg) if role == "Duelist" or role == "Vanguard" else stat_score(dps, dps_avg) * 1
#             hps_score = stat_score(hps, hps_avg)
#             hp_score  = stat_score(hp, hp_avg) if role == "Vanguard" else stat_score(hp, hp_avg) * 1
            
            
#             dps = data[team][char]["dps"]
#             hps = data[team][char]["hps"]
#             health = data[team][char]["health"]
#             dps_total += dps
#             hps_total += hps
#             health_total += health
#             teamteam = team + "Team"
#             data["Totals"][teamteam]["dps_total"] = dps_total
#             data["Totals"][teamteam]["hps_total"] = hps_total
#             data["Totals"][teamteam]["health_total"] = health_total
            
#     def calc_multiplier(blue_stat, red_stat):
#         diff = red_stat - blue_stat
#         if blue_stat == 0:
#             blue_stat = red_stat
#         div = red_stat / blue_stat

#         return round(div, 2)
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
