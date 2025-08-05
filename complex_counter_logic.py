import os
import json
from collections import Counter
from matchups4 import load_characters

CATEGORY_ADVANTAGE = {
    "Dive": "Poke",
    "Poke": "Brawl",
    "Brawl": "Dive"
}

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
                pos += 0.5
            elif CATEGORY_ADVANTAGE.get(dfn) == atk:
                neg += 0.5
    return pos, neg

def score_logic(list1, list2 ,key, data,score_dictionary):
    for char in list1:

        score_dictionary[key][char] = {}
        score_dictionary[key][char]["red_matchup"] = {}
        tally_countering = 0
        tally_countered = 0
        tally_category_pos = 0
        tally_category_neg = 0
        blue_counters = data[char]["counterPicks"]
        blue_counters = [entry["name"] for entry in data[char].get("counterPicks", [])]
        role = data[char]["role"]
        category = data[char]["category"]
        for enemy in list2:
            score = 0
            multiplier = 1
            enemy_role = data[enemy]["role"]
            if enemy in blue_counters:
                if role == "Strategist" and enemy_role != "Strategist":
                    multiplier = 0.4
                score -= 1.25 * multiplier
                tally_countered += 1.25 * multiplier
            enemy_counters = data[enemy]["counterPicks"]
            enemy_counters = [entry["name"] for entry in data[enemy].get("counterPicks", [])]
            multiplier = 1
            if char in enemy_counters:
                if enemy_role == "Strategist" and role != "Strategist":
                    multiplier = 0.4
                score += 1.25 * multiplier
                tally_countering += 1.25 * multiplier
            enemy_category = data[enemy]["category"]
            pos, neg = get_matchup_score(category, enemy_category)
            tally_category_pos += pos
            tally_category_neg += neg
            score += pos - neg
            total_pos = tally_category_pos + tally_countering
            total_neg = tally_category_neg + tally_countered
            entry = {
                        enemy: {
                            "scored": score,
                            "enemy_role": enemy_role,
                            "enemy_category": enemy_category,
                        }
                    }
            score_dictionary[key][char]["red_matchup"].update(entry)

        entry = {
            "score_total": total_pos - total_neg,
            "score_pos": total_pos,
            "score_neg": total_neg,
            "countered": tally_countered,
            "countering": tally_countering,
            "category_pos": tally_category_pos,
            "category_neg": tally_category_neg,
            "role": role,
            "category": category,
            }
        existing = score_dictionary[key][char]

        # New ordered dict with 'entry' fields first
        score_dictionary[key][char] = {
            **entry,  # inserts all keys from `entry` first
            "red_matchup": existing["red_matchup"]
        }
    
    #print(json.dumps(score_dictionary, indent=4))
    return score_dictionary

def homemade_scoring(red,blue):
    score_dictionary = {"Blue":{}, "Red": {}, "Suggestions":{}}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matchup_path = os.path.join(script_dir, "type_matchup.json")
    #matchup_path = os.path.join(script_dir, "dexerto_matchup2.json")
    character_pool = load_characters(matchup_path)
    print(matchup_path)
    save = os.path.join(script_dir,"editmatchup.json")
    with open(matchup_path, encoding="utf-8") as f:
        data = json.load(f)
    unused = [item for item in character_pool if item not in blue]
    score_dictionary = score_logic(blue, red, "Blue",data, score_dictionary)
    score_dictionary = score_logic(unused, red, "Suggestions",data, score_dictionary)
    return score_dictionary

    # for char in blue:

    #     score_dictionary["Blue"][char] = {}
    #     score_dictionary["Blue"][char]["red_matchup"] = {}
    #     tally_countering = 0
    #     tally_countered = 0
    #     tally_category_pos = 0
    #     tally_category_neg = 0
    #     blue_counters = data[char]["counterPicks"]
    #     blue_counters = [entry["name"] for entry in data[char].get("counterPicks", [])]
    #     role = data[char]["role"]
    #     category = data[char]["category"]
    #     for enemy in red:
    #         score = 0
    #         multiplier = 1
    #         enemy_role = data[enemy]["role"]
    #         if enemy in blue_counters:
    #             if role == "Strategist" and enemy_role != "Strategist":
    #                 multiplier = 0.75
    #             score -= 1 * multiplier
    #             tally_countered += 1 * multiplier
    #         enemy_counters = data[enemy]["counterPicks"]
    #         enemy_counters = [entry["name"] for entry in data[enemy].get("counterPicks", [])]
    #         multiplier = 1
    #         if char in enemy_counters:
    #             if enemy_role == "Strategist" and role != "Strategist":
    #                 multiplier = 0.75
    #             score += 1 * multiplier
    #             tally_countering += 1 * multiplier
    #         enemy_category = data[enemy]["category"]
    #         pos, neg = get_matchup_score(category, enemy_category)
    #         tally_category_pos += pos
    #         tally_category_neg += neg
    #         score += pos - neg
    #         total_pos = tally_category_pos + tally_countering
    #         total_neg = tally_category_neg + tally_countered
    #         entry = {
    #                     enemy: {
    #                         "scored": score,
    #                         "enemy_role": enemy_role,
    #                         "enemy_category": enemy_category,
    #                     }
    #                 }
    #         score_dictionary["Blue"][char]["red_matchup"].update(entry)

    #     entry = {
    #         "score_total": total_pos - total_neg,
    #         "score_pos": total_pos,
    #         "score_neg": total_neg,
    #         "countered": tally_countered,
    #         "countering": tally_countering,
    #         "category_pos": tally_category_pos,
    #         "category_neg": tally_category_neg,
    #         "role": role,
    #         "category": category,
    #         }
    #     existing = score_dictionary["Blue"][char]

    #     # New ordered dict with 'entry' fields first
    #     score_dictionary["Blue"][char] = {
    #         **entry,  # inserts all keys from `entry` first
    #         "red_matchup": existing["red_matchup"]
    #     }
    
    # print(json.dumps(score_dictionary, indent=4))
    # return score_dictionary



# stored_list = []
# combined_list =[]
# for item in red:
#     counert = data[item]["counterPicks"]
#     for items in counert:
#         char = items["name"]
#         print(f"Name: {char}")
#         stored_list.append(char)
        
# # Example lists
# print(stored_list)

# # Combine all lists into one
# #combined = list1 + list2 + list3

# # Count the occurrences of each string
# counts = Counter(stored_list)
# negative_list = []
# for item in counts:
#     counert = data[item]["counterPicks"]
#     for items in counert:
#         char = items["name"]
#         if char in red:
#             negative_list.append(item)
# negative_count = Counter(negative_list)
# negative_count = Counter({k: -v for k, v in negative_count.items()})
# print(negative_count)
# result = negative_count + counts
# all_keys = set(counts) | set(negative_count)
# combined = {k: counts.get(k, 0) + negative_count.get(k, 0) for k in all_keys}

# sorted_results = result.most_common()
# sorted_counts = counts.most_common()
# sorted_negative = negative_count.most_common()
# print("/n")
# for item in sorted_counts:
#     print(f"Positive Print: {item}")
# print("/n")
# for item in sorted_negative:
#     print(f"Negative Print: {item}")
# print("/n")
# for item in sorted_results:
#     print(f"Combined Print: {item}")
# print(combined)
# # Print results
# #print(counts)
# sorted_counts = counts.most_common()
# for item in sorted_counts:
#     name, count = item
#     #print(f"Printout:{name}")
def add_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    type_path = os.path.join(script_dir, "type_matchup.json")
    dex_path = os.path.join(script_dir, "dexerto_matchup.json")
    dex_path2 = os.path.join(script_dir, "dexerto_matchup2.json")
    with open(type_path, encoding="utf-8") as f:
        dict = json.load(f)
    with open(dex_path, encoding="utf-8") as f:
        dex = json.load(f)
    for key in dict:
        if key == "Ultron":
            ultron = dict[key]
            dex[key] = ultron
        else:
            typ = dict[key]["category"]
            dex[key]["category"] = typ
    with open(dex_path2, 'w', encoding='utf-8') as f:
        json.dump(dex, f, indent=4, ensure_ascii=False)
    
#add_data()
red = ["Venom", "Peni Parker", "Hawkeye", "Black Panther", "Luna Snow", "Loki"]
blue = ["Iron Man", "Mister Fantastic", "Doctor Strange", "Thor", "Mantis", "Loki"]
score_dict = homemade_scoring(red, blue)
script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "debug","counter_output_dex2.json")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(score_dict, f, indent=4, ensure_ascii=False)
