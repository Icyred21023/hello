# pylint:disable= 'invalid syntax'
import os
import json
import random
from collections import defaultdict
from matchups4 import load_characters

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

class Character:
    def __init__(self, data):
        self.name = data["name"]
        self.role = data["role"]
        self.countered_by = []
        self.matchup_score = data["score"]
        self.counters_given = []
        self.counters_received = []

suggestions_team1_stats = {}
suggestions_blueteam = []
CATEGORY_ADVANTAGE = {
    "Dive": "Poke",
    "Poke": "Brawl",
    "Brawl": "Dive"
}

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

    def calc_multiplier(blue_stat, red_stat):
        diff = red_stat - blue_stat
     
        return round(1 + (diff ) / 90,2)  # Linear scale: 10→1, 100→2

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
            return round(max(-3, min(3, (val - avg) / avg)), 1)
        if role == "Strategist":
            print()

        dps_avg = round(role_avg_team1[role]["dps"],2)
        hps_avg = round(role_avg_team1[role]["hps"],2) if role == "Strategist" else 0
        hp_avg  = round(role_avg_team1[role]["health"],2) if role != "Strategist" else hp

        dps_score = stat_score(dps, dps_avg) if role == "Duelist" or role == "Vanguard" else stat_score(dps, dps_avg) * 0.25
        hps_score = stat_score(hps, hps_avg)
        hp_score  = stat_score(hp, hp_avg) if role == "Vanguard" else stat_score(hp, hp_avg) * 0.5
        cat = cat_pos - cat_neg
        totalScore = (
    (counted * 1) +
    (cat * 0.3) +
    (dps_score * multipliers["dps"]) +
    (hps_score * multipliers["hps"]) +
    (hp_score  * multipliers["health"])
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
    matchup_path = os.path.join(script_dir, "type_matchupDPS.json")

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
        # assume `data` is your parsed JSON (a dict)
    sug = data["Suggestions"]

    # names sorted by totalScore (highest first)
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
    scores["Blue"] = {"original": blue_original_score, "new": blue_new_score}
    scores["Red"] = {"original": red_original_score, "new": red_new_score}
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


def find_replacements(data, duelist, vanguard, strategist, blue):
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
def run_counter_logic(blue, red, replacements=None):
    score_dict = homemade_scoring(red, blue, True)
    score_dict, duelist, vanguard, strategist = sort_end_results(score_dict)
    replacements = find_replacements(score_dict, duelist, vanguard, strategist, blue)
    new_dict,new_red, new_blue = combine_dicts(score_dict,replacements)
    new_score_dict = homemade_scoring(new_red, new_blue, False)
    blue_result, red_result = create_class_objects_1(score_dict,new_score_dict,replacements)
    return blue_result, red_result
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
