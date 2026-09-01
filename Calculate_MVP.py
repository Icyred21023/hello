import json
import helpers

p = helpers.create_path("hero_data_keys.json")
data = helpers.load_json(p)
data = data['data']['items']
p = helpers.create_path("mvp_index.json")
mvp_index = helpers.load_json(p)
mvp_dict = mvp_index[0]['Rows']['mvp_index']
kill_weight = mvp_dict['Kill']
death_weight = mvp_dict['Death']
assist_weight = mvp_dict['Assist']
damage_weight = mvp_dict['HeroDamage']
healing_weight = mvp_dict['HeroHeal']
damage_taken_weight = mvp_dict['SummonerDamageTaken']
final_hit_weight = mvp_dict['LastKill']
default_standard = mvp_dict['DefaultStandardScore']
standard_list = mvp_dict['StandardScore']

jsons = {
    "namor": {
        "kills":31,
        "deaths":9,
        "assists": 2,
        "damage": 31157,
        "healing": 0,
        "damage_taken": 10624,
        "final_hits": 20
    },
    "wolverine": {
        "kills": 38,
        "deaths": 9,
        "assists": 0,
        "damage": 26119,
        "healing": 470,
        "damage_taken": 10624,
        "final_hits": 17
        }
        }
for player in jsons:
    hero_key = None
    for dict in data:
        name = dict["name"]
        name = name.lower()
        if player == name:
            hero_key = dict["key"]
            break
    if hero_key is None:
        print(f"Hero key not found for player: {player}")
        break
    else:
        standard_score = None
        for standard in standard_list:
            if standard['Key'] == hero_key:
                standard_score = standard['Value']
                break
        if standard_score is None:
            print(f"Standard score not found for hero key: {hero_key}")
            standard_score = default_standard

            
    kills = jsons[player]['kills']  * standard_score *kill_weight
    deaths = jsons[player]['deaths'] * standard_score * death_weight
    assists = jsons[player]['assists'] *  standard_score * assist_weight
    damage = jsons[player]['damage'] *  damage_weight
    healing = jsons[player]['healing'] *  healing_weight
    damage_taken = jsons[player]['damage_taken'] * damage_taken_weight
    final_hits = jsons[player]['final_hits'] *  standard_score * final_hit_weight
    mvp_score = kills +  assists + damage + healing + damage_taken + final_hits - deaths
    print(f"\n{player} MVP Score: {mvp_score}")
            